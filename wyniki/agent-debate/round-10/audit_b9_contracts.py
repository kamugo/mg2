"""Reproduce Agent B round-9 legal split and two scorer-contract limits.

The audit reads Agent B's implementation and split artifact from one immutable
Git object.  Legal source texts stay local; the output contains only aggregate
counts, identifiers of missed candidate pairs, hashes, and timings.
"""

from __future__ import annotations

import argparse
import hashlib
import itertools
import json
import subprocess
import sys
import tempfile
import time
import types
from collections import Counter, defaultdict
from pathlib import Path


B_SHA = "c58d6534cf368cafe6cf78ff0c78212177d681fa"
RAW_MANIFEST_SHA256 = "c9248430310a4a3ba8a1c9b3bff997aba5c8baf468f238642cbbc24c18a19973"
DEDUP_SCRIPT_SHA256 = "a60147ecb1c942ea5f9b1eeeb81ac3e34052a95cd61cfc9cfc02953b8c40c67f"


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def git_blob(repo: Path, path: str) -> bytes:
    completed = subprocess.run(
        ["git", "-C", str(repo), "show", f"{B_SHA}:{path}"],
        check=True,
        capture_output=True,
    )
    return completed.stdout


def module_from_blob(name: str, value: bytes) -> types.ModuleType:
    module = types.ModuleType(name)
    module.__file__ = f"{name}.git-blob.py"
    sys.modules[name] = module
    exec(compile(value, module.__file__, "exec"), module.__dict__)
    return module


def write_conllu(path: Path, *, doc_id: str, sent_id: str, empty_id: str) -> None:
    empty_base = empty_id.split(".", 1)[0]
    empty_row = (
        f"{empty_id}\tpro\t_\tPRON\t_\t_\t_\t_\t{empty_base}:dep\t_\n"
    )
    token_rows = "1\tA\t_\tX\t_\t_\t0\troot\t_\t_\n"
    if empty_base == "1":
        token_rows += empty_row
    token_rows += "2\tB\t_\tX\t_\t_\t1\tdep\t_\t_\n"
    if empty_base == "2":
        token_rows += empty_row
    path.write_text(
        f"# newdoc id = {doc_id}\n"
        f"# sent_id = {sent_id}\n"
        f"{token_rows}\n",
        encoding="utf-8",
        newline="\n",
    )


def audit(args: argparse.Namespace) -> dict[str, object]:
    agent_b_root = args.agent_b_root.resolve()
    source_manifest = args.source_manifest.resolve()
    dedup_blob = git_blob(agent_b_root, "kod/scripts/dedup_split_manifest.py")
    scorer_blob = git_blob(agent_b_root, "kod/scripts/score_official.py")
    tracked_blob = git_blob(
        agent_b_root, "kod/data/legal-audit/round-9/eli_split_manifest.json"
    )
    if sha256_bytes(dedup_blob) != DEDUP_SCRIPT_SHA256:
        raise RuntimeError("Agent B dedup script hash differs from the audited blob")
    source_bytes = source_manifest.read_bytes()
    if sha256_bytes(source_bytes) != RAW_MANIFEST_SHA256:
        raise RuntimeError("Legal source manifest hash differs from the audited input")

    dedup = module_from_blob("agent_b_round9_dedup", dedup_blob)
    scorer = module_from_blob("agent_b_round9_scorer", scorer_blob)
    source = json.loads(source_bytes.decode("utf-8"))
    tracked = json.loads(tracked_blob.decode("utf-8"))
    records = source["records"]
    records_by_id = {str(record["doc_id"]): record for record in records}
    tracked_by_id = {str(record["doc_id"]): record for record in tracked["records"]}
    if len(records_by_id) != len(records):
        raise RuntimeError("Source manifest has duplicate doc_id values")

    fingerprints = {}
    text_hashes = {}
    invalid_hashes = []
    for doc_id, record in records_by_id.items():
        data = (source_manifest.parent / str(record["file"])).read_bytes()
        actual_hash = sha256_bytes(data)
        if actual_hash != record["sha256"]:
            invalid_hashes.append(doc_id)
        text_hashes[doc_id] = actual_hash
        fingerprints[doc_id] = dedup._fingerprint(data.decode("utf-8", errors="strict"))

    union = dedup.UnionFind(records_by_id)
    exact_groups = defaultdict(list)
    for doc_id, digest in text_hashes.items():
        exact_groups[digest].append(doc_id)
    for members in exact_groups.values():
        for other in members[1:]:
            union.union(members[0], other)
    exact_duplicate_pairs = sum(
        len(members) * (len(members) - 1) // 2
        for members in exact_groups.values()
    )

    candidate_pairs = 0
    accepted_filtered = []
    accepted_without_filter = []
    start = time.perf_counter()
    for left_id, right_id in itertools.combinations(sorted(records_by_id), 2):
        if text_hashes[left_id] == text_hashes[right_id]:
            continue
        left = fingerprints[left_id]
        right = fingerprints[right_id]
        hamming = (left.simhash ^ right.simhash).bit_count()
        jaccard, containment = dedup._near_score(left.shingles, right.shingles)
        similarity = max(jaccard, containment)
        if hamming <= 12:
            candidate_pairs += 1
            if similarity >= 0.90:
                union.union(left_id, right_id)
                accepted_filtered.append((left_id, right_id))
        if similarity >= 0.90:
            accepted_without_filter.append({
                "left": left_id,
                "right": right_id,
                "simhash_hamming": hamming,
                "jaccard_5gram": jaccard,
                "shorter_containment_5gram": containment,
                "splits": [
                    tracked_by_id[left_id]["split"],
                    tracked_by_id[right_id]["split"],
                ],
            })
    elapsed_seconds = time.perf_counter() - start

    grouped = defaultdict(list)
    for doc_id in sorted(records_by_id):
        grouped[union.find(doc_id)].append(doc_id)
    groups = sorted((sorted(members) for members in grouped.values()), key=lambda x: x[0])
    assignment = dedup._assign_groups(records_by_id, groups, 20260904)
    calculated_group = {
        doc_id: dedup._group_id(group) for group in groups for doc_id in group
    }
    split_mismatches = [
        doc_id
        for doc_id in records_by_id
        if tracked_by_id[doc_id]["split"] != assignment[doc_id]
    ]
    group_mismatches = [
        doc_id
        for doc_id in records_by_id
        if tracked_by_id[doc_id]["dedup_group"] != calculated_group[doc_id]
    ]
    missed = [pair for pair in accepted_without_filter if pair["simhash_hamming"] > 12]

    with tempfile.TemporaryDirectory() as temporary:
        temporary_path = Path(temporary)
        gold = temporary_path / "gold.conllu"
        wrong_id = temporary_path / "wrong-empty-id.conllu"
        wrong_scope = temporary_path / "wrong-doc-and-sentence.conllu"
        write_conllu(gold, doc_id="gold-doc", sent_id="gold-s1", empty_id="1.1")
        write_conllu(wrong_id, doc_id="gold-doc", sent_id="gold-s1", empty_id="2.1")
        write_conllu(
            wrong_scope, doc_id="other-doc", sent_id="other-s9", empty_id="2.1"
        )
        scope = {"zeros": "gold_nodes_predicted_labels"}
        zero_results = {
            "different_empty_id": scorer.validate_zeros_scope(
                scope, str(gold), str(wrong_id)
            ),
            "different_document_sentence_and_empty_id": scorer.validate_zeros_scope(
                scope, str(gold), str(wrong_scope)
            ),
        }

    return {
        "schema_version": "agent-a-round-10-audit-1.0",
        "agent_b_sha": B_SHA,
        "inputs": {
            "source_manifest": str(source_manifest),
            "source_manifest_sha256": sha256_bytes(source_bytes),
            "agent_b_dedup_script_sha256": sha256_bytes(dedup_blob),
            "agent_b_split_artifact_sha256": sha256_bytes(tracked_blob),
        },
        "legal_split_reproduction": {
            "records": len(records_by_id),
            "invalid_source_hashes": invalid_hashes,
            "unique_exact_hashes": len(exact_groups),
            "exact_duplicate_groups": sum(len(values) > 1 for values in exact_groups.values()),
            "exact_duplicate_records": sum(
                len(values) for values in exact_groups.values() if len(values) > 1
            ),
            "simhash_candidate_pairs_hamming_le_12": candidate_pairs,
            "accepted_near_pairs_hamming_le_12": len(accepted_filtered),
            "final_groups": len(groups),
            "split_counts": dict(sorted(Counter(assignment.values()).items())),
            "split_mismatches_against_tracked": split_mismatches,
            "group_mismatches_against_tracked": group_mismatches,
        },
        "exhaustive_pair_scan": {
            "all_possible_pairs": len(records_by_id) * (len(records_by_id) - 1) // 2,
            "exact_duplicate_pairs_skipped": exact_duplicate_pairs,
            "different_hash_pairs_scored": (
                len(records_by_id) * (len(records_by_id) - 1) // 2
                - exact_duplicate_pairs
            ),
            "accepted_near_pairs_with_different_exact_hash_without_simhash_filter": len(
                accepted_without_filter
            ),
            "missed_by_hamming_le_12": missed,
            "elapsed_seconds": elapsed_seconds,
        },
        "zero_scope_counterexamples": zero_results,
        "interpretation": {
            "split_pass_scope": "zero crossings only among groups detected by the published filter",
            "model_or_checkpoint": "not applicable; text-similarity and scorer-contract audit",
            "training_or_inference": "none",
            "text_redistributed": False,
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--agent-b-root", type=Path, required=True)
    parser.add_argument("--source-manifest", type=Path, required=True)
    args = parser.parse_args()
    print(json.dumps(audit(args), ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

"""Audit Agent B round-10 public-release claims without printing legal texts."""

from __future__ import annotations

import argparse
import copy
import hashlib
import json
import subprocess
import sys
import types
from collections import Counter, defaultdict
from pathlib import Path, PurePosixPath


B_SHA = "4c2e45ba06a4ef152cddd04204896e39851d6192"
B9_SHA = "c58d6534cf368cafe6cf78ff0c78212177d681fa"
A_REPLY_SHA = "34ff9b4551be5418b82b2dbdbb81cb785a746420"


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def git_blob(repo: Path, revision: str, path: str) -> bytes:
    return subprocess.run(
        ["git", "-C", str(repo), "show", f"{revision}:{path}"],
        check=True,
        capture_output=True,
    ).stdout


def module_from_blob(name: str, value: bytes) -> types.ModuleType:
    module = types.ModuleType(name)
    module.__file__ = f"{name}.git-blob.py"
    sys.modules[name] = module
    exec(compile(value, module.__file__, "exec"), module.__dict__)
    return module


def gate_result(gate: types.ModuleType, value: object, mode: str) -> dict[str, object]:
    try:
        gate.check_release(value, mode)
    except gate.ReleaseGateError as error:
        return {"accepted": False, "error_type": type(error).__name__}
    return {"accepted": True, "error_type": None}


def tree_rows(repo: Path) -> list[dict[str, object]]:
    output = subprocess.run(
        ["git", "-C", str(repo), "ls-tree", "-r", "-l", B_SHA, "--", "kod/data"],
        check=True,
        capture_output=True,
        text=True,
        encoding="utf-8",
    ).stdout
    rows = []
    for line in output.splitlines():
        metadata, path = line.split("\t", 1)
        mode, object_type, object_id, size = metadata.split()
        if object_type != "blob":
            continue
        rows.append({
            "mode": mode,
            "object_id": object_id,
            "bytes": int(size),
            "path": path,
        })
    return rows


def summarize_rows(rows: list[dict[str, object]]) -> dict[str, object]:
    top_level: dict[str, dict[str, int]] = defaultdict(lambda: {"files": 0, "bytes": 0})
    suffixes = Counter()
    selected_prefixes = {
        "kod/data/saos2015/txt/": "saos2015_raw_text",
        "kod/data/silver/review/": "silver_review_text",
        "kod/data/silver_corpipe/review/": "silver_corpipe_review_text",
        "kod/data/pilot/": "pilot_all",
        "kod/data/przeglad50/": "przeglad50_all",
    }
    selected = {
        name: {"files": 0, "bytes": 0} for name in selected_prefixes.values()
    }
    for row in rows:
        path = str(row["path"])
        size = int(row["bytes"])
        parts = PurePosixPath(path).parts
        bucket = parts[2] if len(parts) > 2 else "_"
        top_level[bucket]["files"] += 1
        top_level[bucket]["bytes"] += size
        suffixes[PurePosixPath(path).suffix.casefold() or "<none>"] += 1
        for prefix, name in selected_prefixes.items():
            if path.startswith(prefix):
                selected[name]["files"] += 1
                selected[name]["bytes"] += size
    return {
        "top_level": dict(sorted(top_level.items())),
        "selected_legal_artifact_prefixes": selected,
        "suffix_counts": dict(sorted(suffixes.items())),
    }


def audit(args: argparse.Namespace) -> dict[str, object]:
    repo = args.agent_b_root.resolve()
    agent_a_root = args.agent_a_root.resolve()
    gate_blob = git_blob(repo, B_SHA, "kod/scripts/legal_release_gate.py")
    public_blob = git_blob(
        repo, B_SHA, "kod/data/legal-audit/round-10/public_summary.json"
    )
    verify9_blob = git_blob(repo, B_SHA, "kod/scripts/verify_round9.py")
    private_blob = git_blob(
        repo, B9_SHA, "kod/data/legal-audit/round-9/eli_split_manifest.json"
    )
    gate = module_from_blob("agent_b_round10_release_gate", gate_blob)
    baseline = json.loads(public_blob.decode("utf-8"))

    unknown = copy.deepcopy(baseline)
    unknown["payload"] = "synthetic"
    nan_fraction = copy.deepcopy(baseline)
    nan_fraction["split"]["fractions"]["train"] = float("nan")
    impossible_exact = copy.deepcopy(baseline)
    impossible_exact["population"].update(
        exact_duplicate_groups=0, exact_duplicate_records=0
    )
    zero_groups = copy.deepcopy(baseline)
    zero_groups["population"]["final_groups"] = 0
    controlled_unknown_content = {
        "records": [{"doc_id": "synthetic", "fullText": "SYNTHETIC_SECRET"}]
    }

    rows = tree_rows(repo)
    adjudication_paths = [
        str(row["path"])
        for row in rows
        if str(row["path"]).startswith("kod/data/pilot/adjudykacja/")
        and str(row["path"]).endswith(".jsonl")
    ]
    adjudication_keys = Counter()
    adjudication_records = 0
    for path in adjudication_paths:
        for line in git_blob(repo, B_SHA, path).decode("utf-8").splitlines():
            if not line.strip():
                continue
            record = json.loads(line)
            adjudication_records += 1
            adjudication_keys.update(record.keys())
    content_or_identifier_keys = sorted(
        set(adjudication_keys)
        & {
            "id",
            "doc",
            "surface_text",
            "context",
            "char_segments",
            "gold_cluster",
            "comment",
        }
    )
    pilot_input = git_blob(repo, B_SHA, "kod/data/pilot/pilot_input.conllu")
    pilot_token_rows = sum(
        bool(line) and not line.startswith(b"#") and b"\t" in line
        for line in pilot_input.splitlines()
    )

    private = json.loads(private_blob.decode("utf-8"))
    private_branch_evidence = {
        "schema_version": private.get("schema_version"),
        "dedup": private["dedup"],
    }
    current_a_origin = subprocess.run(
        ["git", "-C", str(agent_a_root), "rev-parse", "origin/main"],
        check=True,
        capture_output=True,
        text=True,
        encoding="utf-8",
    ).stdout.strip()

    return {
        "schema_version": "agent-a-round-11-release-audit-1.0",
        "agent_b_sha": B_SHA,
        "inputs": {
            "release_gate_sha256": sha256_bytes(gate_blob),
            "public_summary_sha256": sha256_bytes(public_blob),
            "verify_round9_sha256": sha256_bytes(verify9_blob),
            "historical_private_manifest_sha256": sha256_bytes(private_blob),
        },
        "public_gate_mutations": {
            "baseline": gate_result(gate, baseline, "public_aggregate"),
            "unknown_top_level_payload": gate_result(
                gate, unknown, "public_aggregate"
            ),
            "nan_train_fraction": gate_result(
                gate, nan_fraction, "public_aggregate"
            ),
            "inconsistent_exact_counters": gate_result(
                gate, impossible_exact, "public_aggregate"
            ),
            "zero_final_groups_for_nonempty_population": gate_result(
                gate, zero_groups, "public_aggregate"
            ),
            "controlled_manifest_unknown_full_text_key": gate_result(
                gate, controlled_unknown_content, "controlled_manifest"
            ),
        },
        "tracked_tree_inventory": {
            **summarize_rows(rows),
            "pilot_input_token_rows": pilot_token_rows,
            "pilot_adjudication_jsonl_files": len(adjudication_paths),
            "pilot_adjudication_records": adjudication_records,
            "pilot_adjudication_sensitive_field_names": content_or_identifier_keys,
            "note": "counts and field names only; no legal text is emitted",
        },
        "verify_round9_private_branch": {
            "private_path_is_preferred_when_present": (
                "if not split_path.is_file():" in verify9_blob.decode("utf-8")
            ),
            "whole_private_dedup_object_is_copied": (
                '"dedup": split["dedup"]' in verify9_blob.decode("utf-8")
            ),
            "near_pairs_copied": len(
                private_branch_evidence["dedup"].get("near_pairs", [])
            ),
            "contains_per_document_ids": bool(
                private_branch_evidence["dedup"].get("near_pairs")
            ),
        },
        "verify_round10_temporal_condition": {
            "historical_reply_to_sha": A_REPLY_SHA,
            "current_agent_a_origin_main": current_a_origin,
            "equality_condition_currently_true": current_a_origin == A_REPLY_SHA,
            "interpretation": "current remote movement must not invalidate historical provenance",
        },
        "interpretation": {
            "new_public_summary_contains_per_document_material": False,
            "repository_tip_matches_documented_aggregate_only_policy": False,
            "model_or_checkpoint": "not applicable; release-contract audit",
            "training_or_inference": "none",
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--agent-b-root", type=Path, required=True)
    parser.add_argument("--agent-a-root", type=Path, required=True)
    args = parser.parse_args()
    print(json.dumps(audit(args), ensure_ascii=False, indent=2, allow_nan=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

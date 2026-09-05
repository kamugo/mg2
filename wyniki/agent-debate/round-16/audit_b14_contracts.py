"""Audyt kontraktow B14 na przypietych blobach i syntetycznych kontrprobach.

Audyt nie czyta working tree Agenta B ani korpusu. Kod, manifest, ledger i
publiczny agregat sa pobierane wylacznie z finalnego drzewa B14, a wszystkie
pliki CoNLL-U oraz repozytoria uzywane w kontrprobach sa tymczasowe.
"""

from __future__ import annotations

import argparse
import ast
import copy
import hashlib
import inspect
import json
import posixpath
import subprocess
import sys
import tempfile
import types
from pathlib import Path
from typing import Any


B14_SHA = "65bbd965d62d3f4d374b6b31754c0d898a493d59"
PRE_FINAL_B14_SHA = "7d9a7f85f6288bbc5ff37598b54f607752140275"
STATUS_KEYS = (
    "reuse_basis",
    "annotation_rights",
    "privacy_review",
    "controlled_copy_status",
    "history_status",
)
PATHS = {
    "manifest": "kod/data/agent-debate/round-14/MANIFEST.json",
    "verification": "kod/data/agent-debate/round-14/verification.json",
    "generator": "kod/scripts/verify_round14.py",
    "artifact_provenance": "kod/scripts/artifact_provenance.py",
    "score_official": "kod/scripts/score_official.py",
    "legal_release_gate": "kod/scripts/legal_release_gate.py",
    "legal_tree_gate": "kod/scripts/legal_tree_gate.py",
    "release_ledger": "kod/data/legal-audit/round-12/RELEASE_LEDGER.json",
    "public_summary": "kod/data/legal-audit/round-11/public_summary.json",
}


def _git(
    repo: Path, arguments: list[str], *, text: bool = True, check: bool = True
) -> subprocess.CompletedProcess:
    return subprocess.run(
        ["git", "-C", str(repo), *arguments],
        check=check,
        capture_output=True,
        text=text,
        encoding="utf-8" if text else None,
        errors="strict" if text else None,
    )


def _git_text(repo: Path, *arguments: str) -> str:
    return _git(repo, list(arguments)).stdout.strip()


def _git_blob(repo: Path, path: str) -> bytes:
    return _git(repo, ["show", f"{B14_SHA}:{path}"], text=False).stdout


def _sha256(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _module(name: str, value: bytes) -> types.ModuleType:
    module = types.ModuleType(name)
    module.__file__ = f"{name}.git-blob.py"
    previous = sys.modules.get(name)
    sys.modules[name] = module
    try:
        exec(compile(value, module.__file__, "exec"), module.__dict__)
    finally:
        if previous is None:
            del sys.modules[name]
        else:
            sys.modules[name] = previous
    return module


def _load_gates(
    release_blob: bytes, tree_blob: bytes
) -> tuple[types.ModuleType, types.ModuleType]:
    release_gate = _module("agent_b14_legal_release_gate", release_blob)
    previous = sys.modules.get("legal_release_gate")
    sys.modules["legal_release_gate"] = release_gate
    try:
        tree_gate = _module("agent_b14_legal_tree_gate", tree_blob)
    finally:
        if previous is None:
            del sys.modules["legal_release_gate"]
        else:
            sys.modules["legal_release_gate"] = previous
    return release_gate, tree_gate


def _manifest_git_path(name: str) -> str:
    normalized = posixpath.normpath(posixpath.join("kod", name))
    if normalized == ".." or normalized.startswith("../"):
        raise ValueError(f"Sciezka manifestu wychodzi poza repozytorium: {name!r}")
    return normalized


def _audit_manifest(repo: Path, manifest: dict[str, Any]) -> dict[str, Any]:
    records: list[dict[str, Any]] = []
    for section in ("inputs", "outputs"):
        for name, expected in manifest[section].items():
            git_path = _manifest_git_path(name)
            blob = _git_blob(repo, git_path)
            if expected["mode"] == "text_lf":
                normalized = blob.replace(b"\r\n", b"\n")
                actual = {
                    "mode": "text_lf",
                    "sha256_lf": _sha256(normalized),
                    "bytes_lf": len(normalized),
                }
            else:
                actual = {
                    "mode": "binary",
                    "sha256": _sha256(blob),
                    "bytes": len(blob),
                }
            records.append(
                {
                    "section": section,
                    "manifest_path": name,
                    "git_path": git_path,
                    "matches": actual == expected,
                    "expected": expected,
                    "actual": actual,
                }
            )
    mismatches = [record["manifest_path"] for record in records if not record["matches"]]
    return {
        "entry_count": len(records),
        "matched_blob_count": sum(record["matches"] for record in records),
        "mismatches": mismatches,
        "all_entries_match_final_b14": len(records) == 16 and not mismatches,
        "entries": records,
    }


def _calls_describe_artifact_with_root_default(generator_source: str) -> bool:
    tree = ast.parse(generator_source)
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        if not isinstance(node.func, ast.Name) or node.func.id != "describe_artifact":
            continue
        if not node.args or not any(
            isinstance(item, ast.Name) and item.id == "ROOT" for item in ast.walk(node.args[0])
        ):
            continue
        if all(keyword.arg != "revision" for keyword in node.keywords):
            return True
    return False


def _audit_committed_provenance(
    generator_blob: bytes,
    provenance_blob: bytes,
    verification: dict[str, Any],
) -> dict[str, Any]:
    generator_source = generator_blob.decode("utf-8")
    helper = _module("agent_b14_artifact_provenance", provenance_blob)
    revision_default = inspect.signature(helper.describe_artifact).parameters[
        "revision"
    ].default
    mismatches = sorted(
        path
        for path, record in verification["artifacts"].items()
        if (
            record["canonical_lf"]["sha256"] != record["git_blob"].get("sha256")
            or record["canonical_lf"]["bytes"] != record["git_blob"].get("bytes")
        )
    )
    revisions = sorted(
        {
            record["git_blob"].get("revision")
            for record in verification["artifacts"].values()
        }
    )
    passed_independently = bool(
        mismatches
        and verification["passed"]
        and all(verification["checks"].values())
    )
    return {
        "reported_passed": verification["passed"],
        "reported_checks": verification["checks"],
        "artifact_mismatch_paths": mismatches,
        "artifact_git_revisions": revisions,
        "expected_pre_final_revision_confirmed": revisions == [PRE_FINAL_B14_SHA],
        "artifact_equality_is_a_pass_check": not passed_independently,
        "passed_despite_artifact_mismatches": passed_independently,
        "generator_contains_final_b14_sha": B14_SHA in generator_source,
        "generator_asserts_final_b14_revision": (
            B14_SHA in generator_source and "rev-parse" in generator_source
        ),
        "main_artifacts_use_default_revision": (
            _calls_describe_artifact_with_root_default(generator_source)
        ),
        "describe_artifact_default_revision": revision_default,
    }


def _gate_accepts(release_gate: types.ModuleType, value: dict[str, Any]) -> bool:
    try:
        release_gate.check_release(value, "public_aggregate")
    except release_gate.ReleaseGateError:
        return False
    return True


def _gate_result(
    release_gate: types.ModuleType, value: dict[str, Any]
) -> dict[str, Any]:
    try:
        release_gate.check_release(value, "public_aggregate")
    except release_gate.ReleaseGateError as exc:
        return {"accepted": False, "rejection": str(exc)}
    return {"accepted": True, "rejection": None}


def _audit_release_gate(
    release_gate: types.ModuleType, public_summary_blob: bytes
) -> dict[str, Any]:
    baseline = json.loads(public_summary_blob)
    near = copy.deepcopy(baseline)
    population = near["population"]
    population["accepted_near_pairs"] = 1
    population["accepted_pairs_outside_simhash_filter"] = 0
    population["final_groups"] = population["unique_exact_hashes"]
    population["group_size_histogram"] = {"1": 1989, "11": 1}
    near["split"]["group_counts"] = {"train": 1597, "dev": 200, "test": 193}

    split = copy.deepcopy(baseline)
    split["split"]["counts"] = {"train": 1795, "dev": 200, "test": 5}
    split["split"]["group_counts"] = {"train": 1775, "dev": 198, "test": 1}
    histogram_sizes = sorted(split["population"]["group_size_histogram"], key=int)
    near_result = _gate_result(release_gate, near)
    return {
        "baseline_accepted": _gate_accepts(release_gate, baseline),
        "accepted_near_pairs_with_f_equals_u": {
            **near_result,
            "accepted_near_pairs": population["accepted_near_pairs"],
            "final_groups": population["final_groups"],
            "unique_exact_hashes": population["unique_exact_hashes"],
            "b14_closes_a14_residual": not near_result["accepted"],
            "interpretation": (
                "With F=U every exact class needs a separate final-group bin; "
                "B14 exact-pair feasibility rejects the contradictory near edge."
            ),
        },
        "split_five_records_one_group_without_size_five": {
            "accepted": _gate_accepts(release_gate, split),
            "split": "test",
            "split_record_count": split["split"]["counts"]["test"],
            "split_group_count": split["split"]["group_counts"]["test"],
            "global_histogram_sizes": histogram_sizes,
        },
    }


def _commit(repo: Path, message: str) -> str:
    _git_text(repo, "add", "--all")
    _git_text(repo, "commit", "--quiet", "--no-verify", "--no-gpg-sign", "-m", message)
    return _git_text(repo, "rev-parse", "HEAD")


def _audit_candidate_race(
    tree_gate: types.ModuleType, ledger_blob: bytes
) -> dict[str, Any]:
    with tempfile.TemporaryDirectory(prefix="agent-a-b14-head-race-") as temporary:
        root = Path(temporary)
        repo = root / "repo"
        repo.mkdir()
        _git_text(repo, "init", "--quiet")
        _git_text(repo, "config", "user.name", "Synthetic Audit")
        _git_text(repo, "config", "user.email", "synthetic-audit@example.invalid")
        (repo / "README.synthetic").write_text("clean\n", encoding="utf-8", newline="\n")
        clean_sha = _commit(repo, "clean candidate")
        controlled = repo / "kod/data/saos2015"
        controlled.mkdir(parents=True)
        (controlled / "synthetic-marker").write_text(
            "synthetic marker\n", encoding="utf-8", newline="\n"
        )
        violating_sha = _commit(repo, "controlled path")
        _git_text(repo, "checkout", "--quiet", "--detach", clean_sha)
        ledger_path = root / "RELEASE_LEDGER.json"
        ledger_path.write_bytes(ledger_blob)

        original_run_git = tree_gate._run_git
        moved = False

        def move_after_resolve(candidate_repo: Path, argv: list[str]):
            nonlocal moved
            completed = original_run_git(candidate_repo, argv)
            if not moved and argv and argv[0] == "rev-parse" and completed.returncode == 0:
                _git_text(candidate_repo, "update-ref", "HEAD", violating_sha)
                moved = True
            return completed

        tree_gate._run_git = move_after_resolve
        try:
            result = tree_gate.check_tree(repo, ledger_path, "HEAD")
        finally:
            tree_gate._run_git = original_run_git
        scanned_sha = _git_text(repo, "rev-parse", "HEAD")
        reproduced = bool(
            moved
            and result["resolved_candidate"] == clean_sha
            and scanned_sha == violating_sha
            and result["tracked_controlled_files"] == 1
            and result["pass"] is False
        )
        return {
            "reproduced": reproduced,
            "candidate": result["candidate"],
            "resolved_candidate": result["resolved_candidate"],
            "scanned_candidate": scanned_sha,
            "tracked_controlled_files": result["tracked_controlled_files"],
            "pass": result["pass"],
            "move_timing": "after rev-parse returned and before first ls-tree",
        }


def _object_exists(repo: Path, oid: str) -> bool:
    return _git(repo, ["cat-file", "-e", oid], check=False).returncode == 0


def _audit_fake_ledger(
    repo: Path, tree_gate: types.ModuleType, ledger_blob: bytes
) -> dict[str, Any]:
    value = json.loads(ledger_blob)
    fake_revision = "f" * 40
    fake_oids: list[str] = []
    expected_counts: list[tuple[int, int]] = []
    for index, entry in enumerate(value["directories"], start=1):
        fake_oid = str(index) * 40
        fake_oids.append(fake_oid)
        entry["baseline_tree_oid"] = fake_oid
        entry["baseline_tracked_files"] = 10_000 + index
        entry["baseline_tracked_bytes"] = 10**12 + index
        expected_counts.append((10_000 + index, 10**12 + index))
        for key in STATUS_KEYS:
            entry[key] = f"fictional_{key}_{index}"
    value["audit_revision"] = fake_revision

    with tempfile.TemporaryDirectory(prefix="agent-a-b14-ledger-") as temporary:
        path = Path(temporary) / "synthetic-ledger.json"
        path.write_text(json.dumps(value), encoding="utf-8", newline="\n")
        loaded = tree_gate.load_ledger(path)
    entries = loaded["directories"]
    return {
        "accepted": True,
        "fake_revision_preserved": loaded["audit_revision"] == fake_revision,
        "fake_tree_oids_preserved": [entry["baseline_tree_oid"] for entry in entries]
        == fake_oids,
        "fake_counts_preserved": [
            (entry["baseline_tracked_files"], entry["baseline_tracked_bytes"])
            for entry in entries
        ]
        == expected_counts,
        "fake_statuses_preserved": all(
            entry[key] == f"fictional_{key}_{index}"
            for index, entry in enumerate(entries, start=1)
            for key in STATUS_KEYS
        ),
        "fake_objects_absent_from_git": not any(
            _object_exists(repo, oid) for oid in [fake_revision, *fake_oids]
        ),
    }


def _conllu(document: str, sentence: str, rows: list[list[str]]) -> str:
    lines = [f"# newdoc id = {document}", f"# sent_id = {sentence}"]
    lines.extend("\t".join(row) for row in rows)
    return "\n".join(lines) + "\n\n"


def _write(path: Path, value: str) -> None:
    path.write_text(value, encoding="utf-8", newline="\n")


def _alignment(
    score: types.ModuleType,
    split_file: Path,
    original_gold: Path,
    gold_subtoken: Path,
    original_rows: list[list[str]],
    subtoken_rows: list[list[str]],
    partition_sizes: list[int],
) -> dict[str, Any]:
    cursor = 0
    nodes = []
    for source_ordinal, size in enumerate(partition_sizes):
        pieces = []
        for target_ordinal in range(cursor, cursor + size):
            target = subtoken_rows[target_ordinal]
            pieces.append(
                {
                    "ordinal": target_ordinal,
                    "id": target[0],
                    "form": target[1],
                    "empty": False,
                }
            )
        source = original_rows[source_ordinal]
        nodes.append(
            {
                "original": {
                    "ordinal": source_ordinal,
                    "id": source[0],
                    "form": source[1],
                    "empty": False,
                },
                "subtokens": pieces,
            }
        )
        cursor += size
    return {
        "schema_version": "corefseg-original-to-subtoken-v1",
        "source_split_sha256": score.sha256(split_file),
        "original_gold_sha256": score.sha256(original_gold),
        "gold_subtoken_sha256": score.sha256(gold_subtoken),
        "documents": [
            {
                "original": {"ordinal": 0, "id": "d1"},
                "subtoken": {"ordinal": 0, "id": "d1-sub"},
                "sentences": [
                    {
                        "original": {"ordinal": 0, "id": "d1-s1"},
                        "subtoken": {"ordinal": 0, "id": "d1-sub-s1"},
                        "nodes": nodes,
                    }
                ],
            }
        ],
    }


def _structures(score: types.ModuleType, paths: dict[str, Path]) -> dict[str, Any]:
    return {
        name: score.inspect_conllu_structure(path)
        for name, path in paths.items()
        if name != "split_file"
    }


def _validate(
    score: types.ModuleType,
    root: Path,
    paths: dict[str, Path],
    alignment: dict[str, Any],
) -> dict[str, Any]:
    evaluation = {
        "n_documents": 1,
        "split_file": str(paths["split_file"]),
        "task_scope": {"doc_range": [0, 1]},
        "per_document": {"d1": {}},
        "original_to_subtoken_alignment": alignment,
    }
    return score.validate_evaluation_contract(
        evaluation, root / "eval.json", _structures(score, paths), paths
    )


def _audit_alignment_ambiguity(score: types.ModuleType) -> dict[str, Any]:
    original_rows = [
        ["1", "Alpha", "_", "NOUN", "_", "_", "0", "root", "0:root", "_"],
        ["2", "Beta", "_", "NOUN", "_", "_", "1", "dep", "1:dep", "_"],
    ]
    subtoken_rows = [
        ["1", "al", "_", "NOUN", "_", "_", "0", "root", "0:root", "_"],
        ["2", "pha", "_", "NOUN", "_", "_", "1", "dep", "1:dep", "_"],
        ["3", "beta", "_", "NOUN", "_", "_", "2", "dep", "2:dep", "_"],
    ]
    with tempfile.TemporaryDirectory(prefix="agent-a-b14-alignment-") as temporary:
        root = Path(temporary)
        paths = {name: root / f"{name}.conllu" for name in (
            "split_file", "original_gold", "pred_on_original",
            "gold_subtoken", "pred_subtoken",
        )}
        original = _conllu("d1", "d1-s1", original_rows)
        subtoken = _conllu("d1-sub", "d1-sub-s1", subtoken_rows)
        for name in ("split_file", "original_gold", "pred_on_original"):
            _write(paths[name], original)
        for name in ("gold_subtoken", "pred_subtoken"):
            _write(paths[name], subtoken)

        results = []
        for sizes in ([1, 2], [2, 1]):
            mapping = _alignment(
                score,
                paths["split_file"],
                paths["original_gold"],
                paths["gold_subtoken"],
                original_rows,
                subtoken_rows,
                list(sizes),
            )
            results.append(_validate(score, root, paths, mapping))
    return {
        "partition_sizes": [[1, 2], [2, 1]],
        "accepted": [True, True],
        "coverage_complete": [
            result["original_to_subtoken_alignment"]["coverage_complete"]
            for result in results
        ],
        "alignment_sha256": [
            result["original_to_subtoken_alignment"]["sha256"] for result in results
        ],
        "does_not_prove_tokenizer_boundary_authenticity": True,
        "interpretation": (
            "The validator proves explicit endpoint/order/coverage consistency, "
            "not that the partition came from the claimed tokenizer run."
        ),
    }


def _head_deps(rows: list[list[str]]) -> list[tuple[str, str, str]]:
    return [(row[6], row[7], row[8]) for row in rows]


def _audit_source_slice_gap(score: types.ModuleType) -> dict[str, Any]:
    source_rows = [
        [
            "1", "Alpha", "_", "NOUN", "_", "_", "0", "root", "0:root",
            "Entity=(gold-x-1",
        ],
        [
            "2", "Beta", "_", "NOUN", "_", "_", "1", "dep", "1:dep",
            "Entity=gold-x-1)",
        ],
    ]
    fabricated_rows = [
        [
            "1", "Alpha", "_", "NOUN", "_", "_", "2", "dep", "2:dep",
            "_",
        ],
        [
            "2", "Beta", "_", "NOUN", "_", "_", "0", "root", "0:root",
            "Entity=(fabricated-x-1)",
        ],
    ]
    with tempfile.TemporaryDirectory(prefix="agent-a-b14-source-slice-") as temporary:
        root = Path(temporary)
        paths = {name: root / f"{name}.conllu" for name in (
            "split_file", "original_gold", "pred_on_original",
            "gold_subtoken", "pred_subtoken",
        )}
        _write(paths["split_file"], _conllu("d1", "d1-s1", source_rows))
        for name in ("original_gold", "pred_on_original"):
            _write(paths[name], _conllu("d1", "d1-s1", fabricated_rows))
        for name in ("gold_subtoken", "pred_subtoken"):
            _write(paths[name], _conllu("d1-sub", "d1-sub-s1", fabricated_rows))
        mapping = _alignment(
            score,
            paths["split_file"],
            paths["original_gold"],
            paths["gold_subtoken"],
            fabricated_rows,
            fabricated_rows,
            [1, 1],
        )
        checked = _validate(score, root, paths, mapping)
        refreshed = mapping["original_gold_sha256"] == score.sha256(
            paths["original_gold"]
        )
    source_misc = [row[9] for row in source_rows]
    fabricated_misc = [row[9] for row in fabricated_rows]
    return {
        "accepted": True,
        "source_slice_semantics_agree": checked["source_slice_semantics_agree"],
        "source_vs_original_head_deps_equal": (
            _head_deps(source_rows) == _head_deps(fabricated_rows)
        ),
        "source_vs_original_gold_misc_equal": source_misc == fabricated_misc,
        "source_vs_original_entity_spans_equal": False,
        "source_entity_token_ids": [[1, 2]],
        "original_gold_entity_token_ids": [[2]],
        "original_gold_and_pred_use_fabricated_entity": any(
            "fabricated" in value for value in fabricated_misc
        ),
        "alignment_original_gold_hash_refreshed": refreshed,
        "scorer_invocations": 0,
        "ignored_source_fields": ["HEAD", "DEPREL", "DEPS", "MISC.Entity"],
        "severity": "HIGH",
    }


def audit(agent_b_root: Path) -> dict[str, Any]:
    repo = agent_b_root.resolve()
    if _git_text(repo, "rev-parse", f"{B14_SHA}^{{commit}}") != B14_SHA:
        raise RuntimeError(f"Nie mozna rozstrzygnac przypietego B14: {B14_SHA}")
    blobs = {name: _git_blob(repo, path) for name, path in PATHS.items()}
    manifest = json.loads(blobs["manifest"])
    verification = json.loads(blobs["verification"])
    release_gate, tree_gate = _load_gates(
        blobs["legal_release_gate"], blobs["legal_tree_gate"]
    )
    score = _module("agent_b14_score_official", blobs["score_official"])
    return {
        "schema_version": "agent-a-round-16-b14-contract-audit-1.0",
        "agent_b_sha": B14_SHA,
        "scope": "pinned final B14 Git blobs and synthetic temporary fixtures only",
        "inputs": {
            name: {
                "path": PATHS[name],
                "sha256": _sha256(blob),
                "bytes": len(blob),
            }
            for name, blob in blobs.items()
        },
        "manifest_provenance": _audit_manifest(repo, manifest),
        "committed_verification_provenance": _audit_committed_provenance(
            blobs["generator"], blobs["artifact_provenance"], verification
        ),
        "release_gate_residuals": _audit_release_gate(
            release_gate, blobs["public_summary"]
        ),
        "tree_gate_candidate_race": _audit_candidate_race(
            tree_gate, blobs["release_ledger"]
        ),
        "tree_gate_ledger_validation": _audit_fake_ledger(
            repo, tree_gate, blobs["release_ledger"]
        ),
        "alignment_tokenizer_proof_boundary": _audit_alignment_ambiguity(score),
        "source_slice_semantic_gap": _audit_source_slice_gap(score),
        "limitations": [
            "No corpus, legal annotation, model, checkpoint, training or inference is read.",
            "Synthetic alignment acceptance proves a validator boundary, not tokenizer output.",
            "The score-contract counterexample invokes no scorer.",
            "The Agent B working tree is never read; only pinned Git objects are used.",
        ],
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--agent-b-root", required=True, type=Path)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    result = audit(args.agent_b_root)
    serialized = json.dumps(result, ensure_ascii=False, indent=2) + "\n"
    if args.output:
        args.output.write_text(serialized, encoding="utf-8", newline="\n")
    else:
        print(serialized, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

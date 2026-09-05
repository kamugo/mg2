"""Audit residual release-contract gaps in pinned Agent B round 12 blobs.

The audit reads implementation, ledger, and public summaries only through the
pinned B12 Git tree.  It uses synthetic temporary files and repositories; it
never reads legal corpus contents from the Agent B working tree.
"""

from __future__ import annotations

import argparse
import copy
import hashlib
import json
import subprocess
import sys
import tempfile
import types
from pathlib import Path
from typing import Any


B12_SHA = "73b7a5e0e9988bf267fdfa736aafb72175b7ff52"
B11_SHA = "81eeb3a4aec0908975bfc42a41161955d9bf38ba"
DECLARED_DIRECTORIES = (
    "kod/data/saos2015",
    "kod/data/silver",
    "kod/data/silver_corpipe",
    "kod/data/pilot",
    "kod/data/przeglad50",
)
STATUS_KEYS = (
    "reuse_basis",
    "annotation_rights",
    "privacy_review",
    "controlled_copy_status",
    "history_status",
)


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
    return _git(repo, ["show", f"{B12_SHA}:{path}"], text=False).stdout


def _sha256(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _module(name: str, value: bytes) -> types.ModuleType:
    module = types.ModuleType(name)
    module.__file__ = f"{name}.git-blob.py"
    exec(compile(value, module.__file__, "exec"), module.__dict__)
    return module


def _load_gates(release_blob: bytes, tree_blob: bytes) -> tuple[types.ModuleType, types.ModuleType]:
    release_gate = _module("agent_b12_legal_release_gate", release_blob)
    previous = sys.modules.get("legal_release_gate")
    sys.modules["legal_release_gate"] = release_gate
    try:
        tree_gate = _module("agent_b12_legal_tree_gate", tree_blob)
    finally:
        if previous is None:
            del sys.modules["legal_release_gate"]
        else:
            sys.modules["legal_release_gate"] = previous
    return release_gate, tree_gate


def _commit(repo: Path, message: str) -> str:
    _git_text(repo, "add", "--all")
    _git_text(repo, "commit", "--quiet", "--no-verify", "--no-gpg-sign", "-m", message)
    return _git_text(repo, "rev-parse", "HEAD")


def _audit_candidate_race(tree_gate: types.ModuleType, ledger_blob: bytes) -> dict[str, Any]:
    with tempfile.TemporaryDirectory(prefix="agent-a-b12-head-race-") as temporary:
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
        (controlled / "audit-marker").write_text(
            "synthetic marker\n", encoding="utf-8", newline="\n"
        )
        violating_sha = _commit(repo, "synthetic controlled path")
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
        reproduced = (
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


def _audit_ledger(
    repo: Path, tree_gate: types.ModuleType, ledger_blob: bytes
) -> dict[str, Any]:
    value = json.loads(ledger_blob)
    fake_revision = "f" * 40
    value["audit_revision"] = fake_revision
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

    with tempfile.TemporaryDirectory(prefix="agent-a-b12-ledger-") as temporary:
        path = Path(temporary) / "synthetic-ledger.json"
        path.write_text(json.dumps(value), encoding="utf-8", newline="\n")
        loaded = tree_gate.load_ledger(path)

    entries = loaded["directories"]
    actual_counts = [
        (entry["baseline_tracked_files"], entry["baseline_tracked_bytes"])
        for entry in entries
    ]
    return {
        "accepted": True,
        "fake_revision_preserved": loaded["audit_revision"] == fake_revision,
        "fake_tree_oids_preserved": [entry["baseline_tree_oid"] for entry in entries]
        == fake_oids,
        "fake_counts_preserved": actual_counts == expected_counts,
        "fake_statuses_preserved": all(
            entry[key] == f"fictional_{key}_{index}"
            for index, entry in enumerate(entries, start=1)
            for key in STATUS_KEYS
        ),
        "fake_objects_absent_from_git": not any(
            _object_exists(repo, oid) for oid in [fake_revision, *fake_oids]
        ),
        "interpretation": "load_ledger validates shapes, not Git objects or status vocabularies",
    }


def _gate_accepts(release_gate: types.ModuleType, value: dict[str, Any]) -> bool:
    try:
        release_gate.check_release(value, "public_aggregate")
    except release_gate.ReleaseGateError:
        return False
    return True


def _audit_release_gate(
    release_gate: types.ModuleType, public_v1_blob: bytes, public_v2_blob: bytes
) -> dict[str, Any]:
    public_v1 = json.loads(public_v1_blob)
    baseline = json.loads(public_v2_blob)

    no_reduction = copy.deepcopy(baseline)
    population = no_reduction["population"]
    population["accepted_near_pairs"] = 1
    population["accepted_pairs_outside_simhash_filter"] = 0
    population["final_groups"] = population["unique_exact_hashes"]
    population["group_size_histogram"] = {"1": 1989, "11": 1}
    no_reduction["split"]["group_counts"] = {
        "train": 1597,
        "dev": 200,
        "test": 193,
    }

    absent_size = copy.deepcopy(baseline)
    absent_size["split"]["counts"] = {"train": 1795, "dev": 200, "test": 5}
    absent_size["split"]["group_counts"] = {"train": 1775, "dev": 198, "test": 1}
    histogram_sizes = sorted(absent_size["population"]["group_size_histogram"], key=int)

    return {
        "baseline_summaries_accepted": {
            "legal-public-aggregate-1.0": _gate_accepts(release_gate, public_v1),
            "legal-public-aggregate-1.1": _gate_accepts(release_gate, baseline),
        },
        "accepted_near_with_no_group_reduction": {
            "accepted": _gate_accepts(release_gate, no_reduction),
            "accepted_near_pairs": population["accepted_near_pairs"],
            "final_groups": population["final_groups"],
            "unique_exact_hashes": population["unique_exact_hashes"],
        },
        "split_group_size_absent_from_histogram": {
            "accepted": _gate_accepts(release_gate, absent_size),
            "split": "test",
            "split_record_count": absent_size["split"]["counts"]["test"],
            "split_group_count": absent_size["split"]["group_counts"]["test"],
            "histogram_sizes": histogram_sizes,
        },
    }


def _tree_count(repo: Path, revision: str, path: str) -> int:
    output = _git(
        repo,
        ["ls-tree", "-r", "-z", "--name-only", revision, "--", path],
        text=False,
    ).stdout
    return len([item for item in output.split(b"\0") if item])


def _audit_tree_deletions(repo: Path, ledger_blob: bytes) -> dict[str, Any]:
    ledger = json.loads(ledger_blob)
    b11_counts = {path: _tree_count(repo, B11_SHA, path) for path in DECLARED_DIRECTORIES}
    b12_counts = {path: _tree_count(repo, B12_SHA, path) for path in DECLARED_DIRECTORIES}
    deleted_output = _git(
        repo,
        ["diff", "--diff-filter=D", "--name-only", "-z", B11_SHA, B12_SHA, "--"],
        text=False,
    ).stdout
    deleted = [item.decode("utf-8", errors="strict") for item in deleted_output.split(b"\0") if item]
    outside = [
        path
        for path in deleted
        if not any(path == root or path.startswith(root + "/") for root in DECLARED_DIRECTORIES)
    ]
    ledger_counts = {
        entry["path"]: entry["baseline_tracked_files"] for entry in ledger["directories"]
    }
    return {
        "declared_directories": list(DECLARED_DIRECTORIES),
        "b11_tree_counts": b11_counts,
        "b12_tree_counts": b12_counts,
        "b11_total": sum(b11_counts.values()),
        "b12_total": sum(b12_counts.values()),
        "deleted_files": len(deleted),
        "deleted_outside_declared_directories": len(outside),
        "ledger_baseline_matches_b11": ledger_counts == b11_counts,
        "individual_file_names_or_contents_published": False,
    }


def audit(agent_b_root: Path) -> dict[str, Any]:
    repo = agent_b_root.resolve()
    if _git_text(repo, "rev-parse", f"{B12_SHA}^{{commit}}") != B12_SHA:
        raise RuntimeError(f"Nie mozna rozstrzygnac przypietego B12: {B12_SHA}")
    if _git(repo, ["merge-base", "--is-ancestor", B11_SHA, B12_SHA], check=False).returncode:
        raise RuntimeError("B11 nie jest przodkiem B12")

    paths = {
        "legal_release_gate": "kod/scripts/legal_release_gate.py",
        "legal_tree_gate": "kod/scripts/legal_tree_gate.py",
        "release_ledger": "kod/data/legal-audit/round-12/RELEASE_LEDGER.json",
        "public_summary_v1": "kod/data/legal-audit/round-10/public_summary.json",
        "public_summary_v2": "kod/data/legal-audit/round-11/public_summary.json",
    }
    blobs = {name: _git_blob(repo, path) for name, path in paths.items()}
    release_gate, tree_gate = _load_gates(
        blobs["legal_release_gate"], blobs["legal_tree_gate"]
    )
    return {
        "schema_version": "agent-a-round-14-b12-release-audit-1.0",
        "agent_b_sha": B12_SHA,
        "agent_b_parent_audited": B11_SHA,
        "scope": "pinned Git blobs, tree names/counts, and synthetic temporary fixtures only",
        "inputs": {
            name: {"path": paths[name], "sha256": _sha256(blob), "bytes": len(blob)}
            for name, blob in blobs.items()
        },
        "candidate_race": _audit_candidate_race(tree_gate, blobs["release_ledger"]),
        "ledger_validation": _audit_ledger(repo, tree_gate, blobs["release_ledger"]),
        "release_gate_residuals": _audit_release_gate(
            release_gate, blobs["public_summary_v1"], blobs["public_summary_v2"]
        ),
        "tree_deletions": _audit_tree_deletions(repo, blobs["release_ledger"]),
        "limitations": [
            "The deletion audit is scoped to Git tree names and counts, not file contents.",
            "The synthetic counterexamples do not constitute legal or privacy review.",
            "No legal corpus working-tree file, training job, inference, or model is used.",
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

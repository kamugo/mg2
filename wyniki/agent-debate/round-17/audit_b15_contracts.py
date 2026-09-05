"""Portable, Git-pinned audit of Agent B round 15 contracts.

The Agent B repository is used only as a Git object database.  The optional
isolated clone check reads Git metadata only.  All executable reproductions
use pinned blobs in caller-owned temporary directories and synthetic data.
"""

from __future__ import annotations

import argparse
import ast
from collections import Counter
from contextlib import redirect_stdout
import copy
import hashlib
import importlib.util
from io import StringIO
from itertools import product
import json
import os
from pathlib import Path, PurePosixPath
import subprocess
import sys
import tempfile
import types
from typing import Any
from unittest.mock import patch


B15_SHA = "32a564cdc3c6b6301897df094ee062019b7b5705"
IMPLEMENTATION_SHA = "20e05853bf85147466bf8c5874ba29f6bdb6bed4"
MANIFEST_PATH = "kod/data/agent-debate/round-15/MANIFEST.json"
RECEIPT_PATH = "kod/data/agent-debate/round-15/manifest_receipt.json"
VERIFICATION_PATH = "kod/data/agent-debate/round-15/verification.json"
GENERATOR_PATH = "kod/scripts/verify_round15.py"
TEXT_SUFFIXES = {".conllu", ".json", ".log", ".md", ".py", ".yaml", ".yml", ".txt", ".csv"}
TEXT_FILENAMES = {".gitattributes", ".gitignore"}


def _run(repo: Path, *args: str, text: bool = False) -> subprocess.CompletedProcess:
    return subprocess.run(
        ["git", "-C", str(repo), *args], capture_output=True, check=False,
        text=text, encoding="utf-8" if text else None,
        errors="replace" if text else None,
    )


def _git_text(repo: Path, *args: str) -> str:
    result = _run(repo, *args, text=True)
    if result.returncode:
        raise RuntimeError(f"git {' '.join(args)}: {result.stderr.strip()}")
    return result.stdout


def _blob(repo: Path, revision: str, path: str) -> bytes:
    result = _run(repo, "show", f"{revision}:{path}")
    if result.returncode:
        raise RuntimeError(
            f"Brak przypietego blobu {revision}:{path}: "
            + result.stderr.decode("utf-8", errors="replace").strip()
        )
    return result.stdout


def _json_blob(repo: Path, revision: str, path: str) -> dict[str, Any]:
    value = json.loads(_blob(repo, revision, path).decode("utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"{path}: oczekiwano obiektu JSON")
    return value


def _sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _canonical(path: str, data: bytes) -> dict[str, Any]:
    candidate = Path(path)
    if candidate.name.lower() in TEXT_FILENAMES or candidate.suffix.lower() in TEXT_SUFFIXES:
        normalized = data.replace(b"\r\n", b"\n")
        return {"mode": "text_lf", "sha256_lf": _sha(normalized), "bytes_lf": len(normalized)}
    return {"mode": "binary", "sha256": _sha(data), "bytes": len(data)}


def _manifest_git_path(name: str) -> str:
    path = PurePosixPath("kod") / PurePosixPath(name)
    parts: list[str] = []
    for part in path.parts:
        if part == "..":
            if not parts:
                raise ValueError(f"Sciezka wychodzi poza repozytorium: {name}")
            parts.pop()
        elif part not in {"", "."}:
            parts.append(part)
    return PurePosixPath(*parts).as_posix()


def _load_module(name: str, source: bytes, injected: dict[str, types.ModuleType] | None = None):
    temporary = tempfile.NamedTemporaryFile(prefix=name + "-", suffix=".py", delete=False)
    path = Path(temporary.name)
    try:
        temporary.write(source)
        temporary.close()
        spec = importlib.util.spec_from_file_location(name, path)
        if spec is None or spec.loader is None:
            raise RuntimeError(f"Nie mozna zaladowac {name}")
        module = importlib.util.module_from_spec(spec)
        saved = {key: sys.modules.get(key) for key in (injected or {})}
        sys.modules[name] = module
        for key, value in (injected or {}).items():
            sys.modules[key] = value
        try:
            spec.loader.exec_module(module)
        finally:
            for key, old in saved.items():
                if old is None:
                    sys.modules.pop(key, None)
                else:
                    sys.modules[key] = old
        return module
    finally:
        path.unlink(missing_ok=True)


def _final_manifest(repo: Path) -> tuple[dict[str, Any], dict[str, Any]]:
    raw = _blob(repo, B15_SHA, MANIFEST_PATH)
    manifest = json.loads(raw.decode("utf-8"))
    mismatches: list[dict[str, Any]] = []
    matched = 0
    for section in ("inputs", "outputs"):
        for name, expected in manifest.get(section, {}).items():
            path = _manifest_git_path(name)
            actual = _canonical(name, _blob(repo, B15_SHA, path))
            if actual == expected:
                matched += 1
            else:
                mismatches.append({"path": path, "expected": expected, "actual": actual})
    entry_count = sum(len(manifest.get(section, {})) for section in ("inputs", "outputs"))
    receipt = _json_blob(repo, B15_SHA, RECEIPT_PATH)
    return (
        {
            "entry_count": entry_count,
            "matched_blob_count": matched,
            "mismatches": mismatches,
            "implementation_commit": manifest.get("implementation_commit"),
        },
        {
            "manifest_sha256": receipt.get("manifest_sha256"),
            "actual_manifest_sha256": _sha(raw),
            "manifest_sha256_matches": receipt.get("manifest_sha256") == _sha(raw),
            "manifest_passed": receipt.get("manifest_passed") is True,
            "passed": receipt.get("passed") is True,
            "result": receipt.get("result"),
        },
    )


def _verification_provenance(repo: Path) -> dict[str, Any]:
    report = _json_blob(repo, B15_SHA, VERIFICATION_PATH)
    mismatches: list[dict[str, Any]] = []
    revisions: set[str] = set()
    for name, recorded in report["artifacts"].items():
        git_record = recorded["git_blob"]
        revision = git_record.get("revision")
        revisions.add(revision)
        git_path = git_record.get("path")
        actual_blob = _blob(repo, IMPLEMENTATION_SHA, git_path)
        actual_object_id = _git_text(
            repo, "rev-parse", "--verify", f"{IMPLEMENTATION_SHA}:{git_path}"
        ).strip()
        canonical = actual_blob.replace(b"\r\n", b"\n")
        expected = {
            "status": "AVAILABLE",
            "revision": IMPLEMENTATION_SHA,
            "path": git_path,
            "object_id": actual_object_id,
            "sha256": _sha(actual_blob),
            "bytes": len(actual_blob),
            "canonical_sha256": _sha(canonical),
            "canonical_bytes": len(canonical),
        }
        actual = {
            "status": git_record.get("status"),
            "revision": revision,
            "path": git_path,
            "object_id": git_record.get("object_id"),
            "sha256": git_record.get("sha256"),
            "bytes": git_record.get("bytes"),
            "canonical_sha256": recorded["canonical_lf"].get("sha256"),
            "canonical_bytes": recorded["canonical_lf"].get("bytes"),
        }
        if actual != expected:
            mismatches.append({"artifact": name, "expected": expected, "actual": actual})
    clean = report["commands"]["clean_tested_revision"]
    clean_stdout = (IMPLEMENTATION_SHA + "\n").encode("utf-8")
    return {
        "artifact_count": len(report["artifacts"]),
        "mismatches": mismatches,
        "revisions": sorted(revisions),
        "all_checks_true": bool(report["checks"]) and all(value is True for value in report["checks"].values()),
        "core_checks_passed": report.get("core_checks_passed") is True,
        "clean_revision_output_hash_matches": (
            clean.get("stdout_sha256") == _sha(clean_stdout)
            and clean.get("stdout_bytes") == len(clean_stdout)
        ),
    }


def _git(repo: Path, *args: str) -> str:
    result = subprocess.run(["git", *args], cwd=repo, capture_output=True, text=True,
                            encoding="utf-8", errors="replace", check=False)
    if result.returncode:
        raise RuntimeError(f"synthetic git {' '.join(args)}: {result.stderr.strip()}")
    return result.stdout.strip()


def _write_json(path: Path, value: Any) -> None:
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _tree_gate_fixes(repo: Path) -> dict[str, Any]:
    release = _load_module("a17_tree_release", _blob(repo, B15_SHA, "kod/scripts/legal_release_gate.py"))
    alias = types.ModuleType("legal_release_gate")
    alias.ReleaseGateError = release.ReleaseGateError
    alias.dumps_strict_json = release.dumps_strict_json
    alias.loads_strict_json = release.loads_strict_json
    gate = _load_module(
        "a17_tree_gate", _blob(repo, B15_SHA, "kod/scripts/legal_tree_gate.py"),
        {"legal_release_gate": alias},
    )
    with tempfile.TemporaryDirectory(prefix="a17-tree-") as directory:
        synthetic = Path(directory)
        _git(synthetic, "init", "-q")
        _git(synthetic, "config", "user.email", "a17@example.invalid")
        _git(synthetic, "config", "user.name", "A17 synthetic")
        controlled = synthetic / "kod/data/synthetic-controlled"
        controlled.mkdir(parents=True)
        payload = b"synthetic controlled bytes\n"
        (controlled / "fixture.bin").write_bytes(payload)
        _git(synthetic, "add", "--", "kod/data/synthetic-controlled/fixture.bin")
        _git(synthetic, "commit", "-q", "-m", "audit baseline")
        audit_oid = _git(synthetic, "rev-parse", "HEAD")
        tree_oid = _git(synthetic, "rev-parse", f"{audit_oid}:kod/data/synthetic-controlled")
        ledger = {
            "schema_version": "legal-release-ledger-1.0",
            "policy_id": "aggregate-only-pending-review",
            "audit_revision": audit_oid,
            "scope": {
                "kind": "declared_controlled_directories",
                "claim": "scoped_gate_only_not_repo_wide_clearance",
                "paths": ["kod/data/synthetic-controlled"],
            },
            "directories": [{
                "path": "kod/data/synthetic-controlled",
                "baseline_tracked_files": 1,
                "baseline_tracked_bytes": len(payload),
                "baseline_tree_oid": tree_oid,
                "classification": "controlled",
                "public_tip_disposition": "remove_from_tip",
                "public_exceptions": [],
                "reuse_basis": "not_verified",
                "annotation_rights": "not_verified",
                "privacy_review": "not_completed",
                "controlled_copy_status": "not_verified",
                "history_status": "present_in_history",
            }],
            "limitations": ["synthetic scope only"],
        }
        ledger_path = synthetic / "ledger.json"
        _write_json(ledger_path, ledger)
        _git(synthetic, "rm", "-q", "kod/data/synthetic-controlled/fixture.bin")
        _git(synthetic, "commit", "-q", "-m", "clean candidate")
        clean_oid = _git(synthetic, "rev-parse", "HEAD")
        _git(synthetic, "branch", "candidate", clean_oid)
        controlled.mkdir(parents=True)
        (controlled / "violation.bin").write_bytes(b"violation\n")
        _git(synthetic, "add", "--", "kod/data/synthetic-controlled/violation.bin")
        _git(synthetic, "commit", "-q", "-m", "violating candidate")
        violating_oid = _git(synthetic, "rev-parse", "HEAD")

        original_run_git = gate._run_git
        moved = False

        def move_after_resolution(repo_path: Path, argv: list[str]):
            nonlocal moved
            result = original_run_git(repo_path, argv)
            if not moved and argv[-1] == "candidate^{commit}":
                moved = True
                subprocess.run(
                    ["git", "update-ref", "refs/heads/candidate", violating_oid],
                    cwd=repo_path, capture_output=True, check=True,
                )
            return result

        gate._run_git = move_after_resolution
        try:
            ref_result = gate.check_tree(synthetic, ledger_path, "candidate")
        finally:
            gate._run_git = original_run_git
        moved_ref_oid = _git(synthetic, "rev-parse", "candidate")

        _git(synthetic, "checkout", "-q", "--detach", clean_oid)
        mutated_index_oid = ""
        injected = synthetic / "kod/data/synthetic-controlled/index.bin"
        index_mutated = False

        def mutate_after_write_tree(repo_path: Path, argv: list[str]):
            nonlocal index_mutated, mutated_index_oid
            result = original_run_git(repo_path, argv)
            if not index_mutated and argv == ["write-tree"]:
                index_mutated = True
                injected.parent.mkdir(parents=True, exist_ok=True)
                injected.write_bytes(b"index mutation\n")
                subprocess.run(
                    ["git", "add", "--", "kod/data/synthetic-controlled/index.bin"],
                    cwd=repo_path, capture_output=True, check=True,
                )
                mutated_index_oid = _git(repo_path, "write-tree")
            return result

        gate._run_git = mutate_after_write_tree
        try:
            index_result = gate.check_tree(synthetic, ledger_path, "INDEX")
        finally:
            gate._run_git = original_run_git

        baseline = gate.check_tree(synthetic, ledger_path, clean_oid)
        mutations = {
            "audit_revision": ("audit_revision", "0" * 40),
            "tree_oid": ("baseline_tree_oid", "0" * 40),
            "file_count": ("baseline_tracked_files", 2),
            "byte_count": ("baseline_tracked_bytes", len(payload) + 1),
            "status": ("reuse_basis", "verified"),
        }
        rejected: dict[str, bool] = {}
        for name, (key, value) in mutations.items():
            changed = copy.deepcopy(ledger)
            if key == "audit_revision":
                changed[key] = value
            else:
                changed["directories"][0][key] = value
            changed_path = synthetic / f"ledger-{name}.json"
            _write_json(changed_path, changed)
            try:
                gate.check_tree(synthetic, changed_path, clean_oid)
            except gate.TreeGateError:
                rejected[name] = True
            else:
                rejected[name] = False
        return {
            "ref_snapshot": {
                "reproduced": moved and ref_result["resolved_candidate"] == clean_oid,
                "resolved_oid": ref_result["resolved_candidate"],
                "moved_ref_oid": moved_ref_oid,
                "passed_clean_snapshot": ref_result["pass"] is True,
                "tracked_files": ref_result["tracked_controlled_files"],
            },
            "index_snapshot": {
                "reproduced": index_mutated and index_result["pass"] is True,
                "scanned_tree_oid": index_result["resolved_candidate"],
                "mutated_index_oid": mutated_index_oid,
                "tracked_files": index_result["tracked_controlled_files"],
            },
            "ledger": {
                "baseline_accepted": baseline["pass"] is True,
                "mutation_rejected": rejected,
            },
        }


def _compositions(total: int):
    for first in range(total + 1):
        for second in range(total - first + 1):
            yield first, second, total - first - second


def _synthetic_v2(gate: Any) -> dict[str, Any]:
    return {
        "schema_version": "legal-public-aggregate-1.1",
        "source_private_manifest_sha256": "a" * 64,
        "raw_source_manifest_sha256": "b" * 64,
        "population": {
            "record_count": 6, "unique_exact_hashes": 6,
            "exact_duplicate_groups": 0, "exact_duplicate_records": 0,
            "simhash_candidate_pairs": 3, "accepted_near_pairs": 3,
            "final_groups": 3, "possible_pairs": 15, "exact_pairs_skipped": 0,
            "different_hash_pairs_scored": 15,
            "accepted_pairs_outside_simhash_filter": 0,
            "group_size_histogram": {"1": 1, "2": 1, "3": 1},
        },
        "dedup_definition": dict(gate.PUBLIC_DEDUP_DEFINITION_V2),
        "split": {
            "seed": 1, "fractions": {"train": 1 / 3, "dev": 1 / 3, "test": 1 / 3},
            "strategy": gate.PUBLIC_SPLIT_STRATEGY,
            "counts": {"train": 3, "dev": 2, "test": 1},
            "cross_split_dedup_groups": 0, "verification": "PASS",
            "group_counts": {"train": 1, "dev": 1, "test": 1},
        },
        "release": {
            "mode": "public_aggregate",
            "contains_document_ids_urls_or_per_document_hashes": False,
            "contains_text_tokens_or_annotations": False,
            "legal_clearance": "not_obtained", "pii_review": "not_completed",
            "warning": gate.PUBLIC_WARNING,
        },
    }


def _rejected(gate: Any, value: dict[str, Any]) -> bool:
    try:
        gate.check_release(value, "public_aggregate")
    except gate.ReleaseGateError:
        return True
    return False


def _release_gate_fixes(repo: Path) -> dict[str, Any]:
    gate = _load_module("a17_release_gate", _blob(repo, B15_SHA, "kod/scripts/legal_release_gate.py"))
    v1 = _json_blob(repo, B15_SHA, "kod/data/legal-audit/round-10/public_summary.json")
    v2 = _json_blob(repo, B15_SHA, "kod/data/legal-audit/round-11/public_summary.json")
    gate.check_release(v1, "public_aggregate")
    gate.check_release(v2, "public_aggregate")
    near_results = []
    for baseline in (v1, v2):
        bad = copy.deepcopy(baseline)
        bad["population"]["accepted_near_pairs"] = 1
        bad["population"]["final_groups"] = bad["population"]["unique_exact_hashes"]
        near_results.append(_rejected(gate, bad))
    joint = _synthetic_v2(gate)
    gate.check_release(joint, "public_aggregate")
    bad_joint = copy.deepcopy(joint)
    bad_joint["split"]["counts"] = {"train": 2, "dev": 2, "test": 2}
    joint_rejected = _rejected(gate, bad_joint)

    checked = 0
    discrepancies = 0
    splits = ("train", "dev", "test")
    for sizes in ((), (1,), (2, 2), (1, 2, 3), (1, 1, 2, 4), (2, 3, 4)):
        feasible = set()
        for destinations in product(range(3), repeat=len(sizes)):
            records, groups = [0, 0, 0], [0, 0, 0]
            for size, destination in zip(sizes, destinations):
                records[destination] += size
                groups[destination] += 1
            feasible.add((tuple(records), tuple(groups)))
        for records in _compositions(sum(sizes)):
            for groups in _compositions(len(sizes)):
                actual = gate._split_histogram_feasible(
                    histogram=dict(Counter(sizes)),
                    records=dict(zip(splits, records)), groups=dict(zip(splits, groups)),
                )
                expected = (records, groups) in feasible
                discrepancies += int(actual != expected)
                checked += 1
    return {
        "baseline_v1_accepted": True,
        "baseline_v2_accepted": True,
        "near_no_reduction_rejected_v1": near_results[0],
        "near_no_reduction_rejected_v2": near_results[1],
        "joint_split_allocation_rejected": joint_rejected,
        "split_oracle_cases": checked,
        "split_oracle_discrepancies": discrepancies,
    }


def _record(argv: list[Any], cwd: Path, stdout: str = "", exit_code: int = 0) -> tuple[dict[str, Any], str]:
    data = stdout.encode("utf-8")
    empty = _sha(b"")
    return ({
        "argv": list(map(str, argv)), "cwd": str(cwd), "exit_code": exit_code,
        "elapsed_seconds": 0.0, "stdout_sha256": _sha(data), "stdout_bytes": len(data),
        "stderr_sha256": empty, "stderr_bytes": 0,
    }, stdout)


def _generator_toctou(repo: Path) -> dict[str, Any]:
    generator_source = _blob(repo, B15_SHA, GENERATOR_PATH)
    ast.parse(generator_source.decode("utf-8"), filename=GENERATOR_PATH)
    manifest_module = _load_module(
        "a17_manifest", _blob(repo, B15_SHA, "kod/scripts/manifest.py")
    )
    fake_provenance = types.ModuleType("artifact_provenance")
    fake_provenance.describe_artifact = lambda *args, **kwargs: None
    fake_provenance.extract_pinned_git_file = lambda *args, **kwargs: None
    generator = _load_module(
        "a17_verify_round15", generator_source,
        {"artifact_provenance": fake_provenance, "manifest": manifest_module},
    )
    initial = b"implementation bytes\n"
    mutated = b"bytes mutated after the initial provenance check\n"
    with tempfile.TemporaryDirectory(prefix="a17-toctou-") as directory:
        repo_root = Path(directory)
        root = repo_root / "kod"
        (root / "scripts").mkdir(parents=True)
        (root / "tests").mkdir()
        (root / "scripts/manifest.py").write_bytes(
            _blob(repo, B15_SHA, "kod/scripts/manifest.py")
        )
        tracked = root / "tracked.py"
        tracked.write_bytes(initial)
        output_dir = root / "data/agent-debate/round-15"
        generator.ROOT = root
        generator.REPO = repo_root
        generator.FILES = ["tracked.py"]
        generator.manifest = manifest_module
        state = {"described": False, "mutated": False}

        def describe(path: Path, *, repo: Path, git_path: str, revision: str):
            data = Path(path).read_bytes()
            state["described"] = True
            digest = _sha(data.replace(b"\r\n", b"\n"))
            return {
                "path": str(path),
                "raw_checkout": {"sha256": _sha(data), "bytes": len(data)},
                "canonical_lf": {"sha256": digest, "bytes": len(data), "normalization": "crlf_to_lf"},
                "git_blob": {
                    "status": "AVAILABLE", "repository": str(repo), "revision": revision,
                    "path": git_path, "object_id": "1" * 40,
                    "sha256": digest, "bytes": len(data),
                },
            }

        def extract(_repo: Path, _revision: str, _git_path: str, destination: Path):
            Path(destination).write_bytes(b"pinned synthetic helper\n")
            return {"source": {"revision": generator.A_SHA}, "path": str(destination)}

        def fake_run(argv: list[Any], *, cwd=root, env=None):
            strings = list(map(str, argv))
            if state["described"] and not state["mutated"]:
                tracked.write_bytes(mutated)
                state["mutated"] = True
            if "--output" in strings and any("audit_b12_release.py" in item for item in strings):
                historical = Path(strings[strings.index("--output") + 1])
                _write_json(historical, {
                    "candidate_race": {"reproduced": True},
                    "ledger_validation": {"accepted": True},
                })
            if strings[:2] == ["git", "rev-parse"]:
                return _record(strings, Path(cwd), IMPLEMENTATION_SHA + "\n")
            if "tests/run_all.py" in strings:
                return _record(strings, Path(cwd), "synthetic suite\n21 tests passed\n")
            if "legal_tree_gate.py" in " ".join(strings):
                return _record(strings, Path(cwd), json.dumps({
                    "pass": True, "tracked_controlled_files": 0,
                }) + "\n")
            if "scripts/manifest.py" in strings and "verify" in strings:
                manifest_path = strings[strings.index("--manifest") + 1]
                previous = Path.cwd()
                capture = StringIO()
                try:
                    os.chdir(root)
                    with redirect_stdout(capture):
                        exit_code = manifest_module.verify(manifest_path)
                finally:
                    os.chdir(previous)
                return _record(strings, Path(cwd), capture.getvalue(), exit_code)
            return _record(strings, Path(cwd))

        generator.describe_artifact = describe
        generator.extract_pinned_git_file = extract
        generator.run = fake_run
        argv = [
            "verify_round15.py", "--implementation", IMPLEMENTATION_SHA,
            "--repo-a", str(repo_root / "unused-a"), "--output-dir", str(output_dir),
        ]
        capture = StringIO()
        with patch.object(sys, "argv", argv), redirect_stdout(capture):
            exit_code = generator.main()
        report = json.loads((output_dir / "verification.json").read_text(encoding="utf-8"))
        manifest = json.loads((output_dir / "MANIFEST.json").read_text(encoding="utf-8"))
        receipt = json.loads((output_dir / "manifest_receipt.json").read_text(encoding="utf-8"))
        manifest_digest = manifest["inputs"]["tracked.py"]["sha256_lf"]

    source_text = generator_source.decode("utf-8")
    after_build = source_text.split("built = manifest.build", 1)[1]
    before_receipt = after_build.split("receipt =", 1)[0]
    post_comparison = "describe_artifact" in before_receipt or "git_blob" in before_receipt
    reproduced = (
        exit_code == 0 and state["mutated"]
        and manifest_digest == _sha(mutated) and manifest_digest != _sha(initial)
        and report["core_checks_passed"] is True and receipt["passed"] is True
        and not post_comparison
    )
    return {
        "reproduced": reproduced,
        "method": "pinned generator with deterministic system-boundary monkeypatch; synthetic files only",
        "initial_candidate_matches_implementation": True,
        "mutation_after_initial_check": state["mutated"],
        "implementation_sha256": _sha(initial),
        "mutated_sha256": _sha(mutated),
        "manifest_sha256": manifest_digest,
        "reported_core_checks": report["core_checks_passed"] is True,
        "manifest_verification_passed": receipt["manifest_passed"] is True,
        "receipt_passed": receipt["passed"] is True,
        "post_manifest_final_blob_comparison": post_comparison,
        "boundary": (
            "This proves the generator control-flow gap under a controlled boundary mutation; "
            "it does not claim that the historical B15 run was actually raced."
        ),
    }


def audit(agent_b_root: Path, isolated_clone: Path) -> dict[str, Any]:
    """Run all checks without reading Agent B checkout files or legal corpus bytes."""

    repo = Path(agent_b_root).resolve()
    final = _git_text(repo, "rev-parse", "--verify", B15_SHA + "^{commit}").strip()
    if final != B15_SHA:
        raise ValueError("Final B15 commit is unavailable")
    clone = Path(isolated_clone).resolve()
    clone_head = _git_text(clone, "rev-parse", "HEAD").strip()
    clone_status = _git_text(clone, "status", "--porcelain=v1")
    manifest, receipt = _final_manifest(repo)
    result = {
        "schema_version": "agent-a-round-17-b15-contract-audit-1.0",
        "target_revision": B15_SHA,
        "implementation_revision": IMPLEMENTATION_SHA,
        "input_boundary": {
            "agent_b_access": "pinned Git objects only",
            "isolated_clone": {
                "path": str(clone), "head": clone_head,
                "clean": clone_head == B15_SHA and clone_status == "",
                "status_scope": "full porcelain status; corpus contents were not opened",
            },
            "synthetic_mutations_only": True,
        },
        "final_manifest": manifest,
        "final_receipt": receipt,
        "verification_provenance": _verification_provenance(repo),
        "tree_gate_fixes": _tree_gate_fixes(repo),
        "release_gate_fixes": _release_gate_fixes(repo),
        "generator_toctou": _generator_toctou(repo),
    }
    result["passed"] = (
        result["input_boundary"]["isolated_clone"]["clean"]
        and not manifest["mismatches"] and manifest["entry_count"] == 33
        and receipt["manifest_sha256_matches"] and receipt["passed"]
        and not result["verification_provenance"]["mismatches"]
        and result["release_gate_fixes"]["split_oracle_discrepancies"] == 0
        and result["generator_toctou"]["reproduced"]
    )
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--agent-b-root", required=True, type=Path)
    parser.add_argument("--isolated-clone", required=True, type=Path)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    result = audit(args.agent_b_root, args.isolated_clone)
    serialized = json.dumps(result, ensure_ascii=False, indent=2, allow_nan=False) + "\n"
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(serialized, encoding="utf-8", newline="\n")
    print(serialized, end="")
    return 0 if result["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())

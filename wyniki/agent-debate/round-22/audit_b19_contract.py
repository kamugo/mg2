"""Audit B19's invariant and post-publication receipt contracts.

Agent B evidence is read from immutable Git blobs in a caller-supplied clean
checkout at the exact final revision.  One deliberately invalid, synthetic
mode call executes the checkout's script after its bytes have been matched to
the target blob.  The report stores no CoNLL-U content or subprocess output.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import ntpath
import os
from pathlib import Path, PurePosixPath
import subprocess
import sys
from typing import Any


B18_SHA = "e1d9d4ba94c9bdc52553bb14cc7f01d7113f0101"
PROTOCOL_SHA = "18c21b1c868f7f06bdc98097da8c24501b4e14b4"
IMPLEMENTATION_SHA = "09d7cfb9136403dba1f78ebe7cf48cda2eb08fe0"
PUBLICATION_SHA = "1d3ba1abcc1eb0112433e73701da88576f73ba17"
B19_FINAL_SHA = "03befe9585fe8fa7b7704f91b547a17999ac9268"

MANIFEST_PATH = "kod/data/agent-debate/round-19/MANIFEST.json"
PREPUBLICATION_RECEIPT_PATH = (
    "kod/data/agent-debate/round-19/manifest_receipt.json"
)
RECEIPT_PATH = "kod/data/agent-debate/round-19/publication_receipt.json"
VERIFICATION_PATH = "kod/data/agent-debate/round-19/verification.json"
VERIFY_SCRIPT_PATH = "kod/scripts/verify_round19.py"
INVARIANT_SCRIPT_PATH = "kod/scripts/reexport_invariants.py"


def _git(repo: Path, *args: str, text: bool = False) -> subprocess.CompletedProcess:
    """Run a noninteractive Git query against the supplied repository."""

    return subprocess.run(
        ["git", "-C", str(repo), *args],
        capture_output=True,
        check=False,
        text=text,
        encoding="utf-8" if text else None,
        errors="replace" if text else None,
    )


def _git_text(repo: Path, *args: str) -> str:
    result = _git(repo, *args, text=True)
    if result.returncode:
        raise RuntimeError(f"git {' '.join(args)}: exit {result.returncode}")
    return result.stdout


def _blob_optional(repo: Path, revision: str, path: str) -> bytes | None:
    result = _git(repo, "cat-file", "blob", f"{revision}:{path}")
    return result.stdout if result.returncode == 0 else None


def _blob(repo: Path, revision: str, path: str) -> bytes:
    data = _blob_optional(repo, revision, path)
    if data is None:
        raise RuntimeError(f"Brak przypietego blobu {revision}:{path}")
    return data


def _json_blob(repo: Path, revision: str, path: str) -> dict[str, Any]:
    value = json.loads(_blob(repo, revision, path).decode("utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"{path}: oczekiwano obiektu JSON")
    return value


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _exact_revision(repo: Path, revision: str) -> bool:
    result = _git(repo, "rev-parse", "--verify", revision + "^{commit}", text=True)
    return result.returncode == 0 and result.stdout.strip() == revision


def _repository_state(repo: Path) -> tuple[str, bool]:
    head = _git_text(repo, "rev-parse", "HEAD").strip()
    status = _git_text(
        repo, "status", "--porcelain=v1", "--untracked-files=all"
    )
    return head, status == ""


def _manifest_git_path(name: str) -> str:
    parts: list[str] = []
    for part in (PurePosixPath("kod") / PurePosixPath(name)).parts:
        if part == "..":
            if not parts:
                raise ValueError(f"Sciezka wychodzi poza repozytorium: {name}")
            parts.pop()
        elif part not in {"", "."}:
            parts.append(part)
    return PurePosixPath(*parts).as_posix()


def _canonical_descriptor(data: bytes, expected: dict[str, Any]) -> dict[str, Any]:
    mode = expected.get("mode")
    if mode == "text_lf":
        normalized = data.replace(b"\r\n", b"\n")
        return {
            "mode": "text_lf",
            "sha256_lf": _sha256(normalized),
            "bytes_lf": len(normalized),
        }
    if mode == "binary":
        return {"mode": "binary", "sha256": _sha256(data), "bytes": len(data)}
    raise ValueError(f"Nieznany tryb manifestu: {mode!r}")


def _independent_receipt_audit(repo: Path) -> dict[str, Any]:
    receipt_bytes = _blob(repo, B19_FINAL_SHA, RECEIPT_PATH)
    receipt = json.loads(receipt_bytes.decode("utf-8"))
    if not isinstance(receipt, dict):
        raise ValueError("Receipt nie jest obiektem JSON")
    manifest_bytes = _blob(repo, PUBLICATION_SHA, MANIFEST_PATH)
    manifest = json.loads(manifest_bytes.decode("utf-8"))
    pre_receipt = _json_blob(repo, PUBLICATION_SHA, PREPUBLICATION_RECEIPT_PATH)
    if not isinstance(manifest, dict):
        raise ValueError("Manifest nie jest obiektem JSON")
    sections = ("inputs", "outputs")
    entries: dict[str, dict[str, Any]] = {}
    for section in sections:
        values = manifest.get(section)
        if not isinstance(values, dict):
            raise ValueError(f"Manifest: brak mapy {section}")
        for name, descriptor in values.items():
            if name in entries or not isinstance(descriptor, dict):
                raise ValueError(f"Manifest: niejednoznaczny wpis {name}")
            entries[name] = descriptor
    partitions = manifest.get("provenance_partitions")
    if not isinstance(partitions, dict):
        raise ValueError("Manifest: brak provenance_partitions")
    implementation = partitions.get("implementation_inputs")
    generated = partitions.get("generated_outputs")
    if not isinstance(implementation, dict) or not isinstance(generated, dict):
        raise ValueError("Manifest: bledne partycje")
    implementation_paths = implementation.get("paths")
    generated_paths = generated.get("paths")
    if not isinstance(implementation_paths, list) or not isinstance(generated_paths, list):
        raise ValueError("Manifest: partycje nie sa listami")
    implementation_set = set(implementation_paths)
    generated_set = set(generated_paths)
    complete_and_disjoint = (
        len(implementation_set) == len(implementation_paths)
        and len(generated_set) == len(generated_paths)
        and not implementation_set & generated_set
        and implementation_set | generated_set == set(entries)
    )
    implementation_mismatches: list[str] = []
    generated_present: list[str] = []
    publication_mismatches: list[str] = []
    for name, expected in entries.items():
        git_path = _manifest_git_path(name)
        publication_data = _blob_optional(repo, PUBLICATION_SHA, git_path)
        if (
            publication_data is None
            or _canonical_descriptor(publication_data, expected) != expected
        ):
            publication_mismatches.append(name)
        implementation_data = _blob_optional(repo, IMPLEMENTATION_SHA, git_path)
        if name in implementation_set:
            if (
                implementation_data is None
                or _canonical_descriptor(implementation_data, expected) != expected
                or implementation_data != publication_data
            ):
                implementation_mismatches.append(name)
        elif name in generated_set and implementation_data is not None:
            generated_present.append(name)
    target_paths = sorted(
        line for line in _git_text(
            repo, "diff-tree", "--no-commit-id", "--name-only", "-r", B19_FINAL_SHA
        ).splitlines() if line
    )
    checks = receipt.get("checks")
    if not isinstance(checks, dict):
        checks = {}
    receipt_partitions = receipt.get("provenance_partitions")
    if not isinstance(receipt_partitions, dict):
        receipt_partitions = {}
    receipt_impl = receipt_partitions.get("implementation_inputs")
    receipt_generated = receipt_partitions.get("generated_outputs")
    receipt_impl_count = receipt_impl.get("count") if isinstance(receipt_impl, dict) else None
    receipt_generated_count = (
        receipt_generated.get("count") if isinstance(receipt_generated, dict) else None
    )
    attestation = receipt.get("attestation_scope")
    if not isinstance(attestation, dict):
        attestation = {}
    independent_partitions = {
        "manifest_entry_count": len(entries),
        "implementation_count": len(implementation_paths),
        "generated_count": len(generated_paths),
        "complete_and_disjoint": complete_and_disjoint,
        "implementation_mismatches": sorted(implementation_mismatches),
        "generated_present_at_implementation": sorted(generated_present),
        "publication_mismatches": sorted(publication_mismatches),
    }
    result = {
        "final_blob_is_json": True,
        "final_blob_sha256": _sha256(receipt_bytes),
        "target_commit_added_paths": target_paths,
        "receipt_present_at_publication": (
            _blob_optional(repo, PUBLICATION_SHA, RECEIPT_PATH) is not None
        ),
        "receipt_present_at_final": True,
        "declared_publication_commit": receipt.get("publication_commit"),
        "declared_attested_commit": attestation.get("attested_commit"),
        "final_receipt_commit": B19_FINAL_SHA,
        "attestation_blob_in_attested_commit": attestation.get(
            "attestation_blob_in_attested_commit"
        ),
        "own_future_commit_intentionally_excluded": attestation.get(
            "own_future_commit_intentionally_excluded"
        ),
        "check_count": len(checks),
        "true_check_count": sum(value is True for value in checks.values()),
        "declared_passed": receipt.get("passed") is True and receipt.get("status") == "PASS",
        "manifest_sha_matches_prepublication_receipt": (
            pre_receipt.get("manifest_sha256") == _sha256(manifest_bytes)
            and pre_receipt.get("passed") is True
        ),
        "receipt_partition_counts": {
            "implementation": receipt_impl_count,
            "generated": receipt_generated_count,
        },
        "independent_partitions": independent_partitions,
    }
    result["independent_structure_passed"] = (
        target_paths == [RECEIPT_PATH]
        and not result["receipt_present_at_publication"]
        and result["declared_publication_commit"] == PUBLICATION_SHA
        and result["declared_attested_commit"] == PUBLICATION_SHA
        and result["attestation_blob_in_attested_commit"] is False
        and result["own_future_commit_intentionally_excluded"] is True
        and result["check_count"] == result["true_check_count"] == 10
        and result["declared_passed"]
        and result["manifest_sha_matches_prepublication_receipt"]
        and independent_partitions["manifest_entry_count"] == 124
        and independent_partitions["implementation_count"] == receipt_impl_count == 104
        and independent_partitions["generated_count"] == receipt_generated_count == 20
        and complete_and_disjoint
        and not implementation_mismatches
        and not generated_present
        and not publication_mismatches
    )
    return result


def _process_record(process: subprocess.CompletedProcess[str]) -> dict[str, Any]:
    stdout = process.stdout.encode("utf-8")
    stderr = process.stderr.encode("utf-8")
    return {
        "exit_code": process.returncode,
        "stdout_sha256": _sha256(stdout),
        "stdout_bytes": len(stdout),
        "stderr_sha256": _sha256(stderr),
        "stderr_bytes": len(stderr),
    }


def _invalid_mode_probe(repo: Path) -> dict[str, Any]:
    checkout_script = repo / PurePosixPath(INVARIANT_SCRIPT_PATH)
    blob = _blob(repo, B19_FINAL_SHA, INVARIANT_SCRIPT_PATH)
    script_matches = (
        checkout_script.is_file() and checkout_script.read_bytes() == blob
    )
    if not script_matches:
        raise ValueError("Wykonywany skrypt nie odpowiada finalnemu blobowi Git")
    source = (
        "import json\n"
        "from scripts.reexport_invariants import _zrodlo_syntetyczne, sprawdz_invariant\n"
        "data = _zrodlo_syntetyczne()\n"
        "r = sprawdz_invariant(data, data, 'bogus')\n"
        "print(json.dumps({'accepted': r.get('passed') is True, "
        "'reported_mode': r.get('mode')}, sort_keys=True))\n"
    )
    environment = dict(os.environ)
    environment["PYTHONDONTWRITEBYTECODE"] = "1"
    process = subprocess.run(
        [sys.executable, "-B", "-c", source],
        cwd=repo / "kod",
        env=environment,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        check=False,
    )
    try:
        observed = json.loads(process.stdout)
    except json.JSONDecodeError as exc:
        raise RuntimeError(
            f"Probe nie zwrocil JSON; stdout sha256={_sha256(process.stdout.encode('utf-8'))}"
        ) from exc
    if not isinstance(observed, dict):
        raise ValueError("Probe nie zwrocil obiektu JSON")
    result = {
        "requested_mode": "bogus",
        "executed_source_matches_target_blob": script_matches,
        "executed_source_sha256": _sha256(blob),
        "process": _process_record(process),
        "observed": {
            "accepted": observed.get("accepted") is True,
            "reported_mode": observed.get("reported_mode"),
        },
        "expected_safe_contract": {
            "accepted": False,
            "reject_unknown_mode": True,
            "nonzero_or_exception": True,
        },
    }
    result["gap_reproduced"] = (
        process.returncode == 0
        and result["observed"] == {"accepted": True, "reported_mode": "eid-neutral"}
    )
    return result


def _is_within_windows(child: str, parent: str) -> bool:
    try:
        child_norm = ntpath.normcase(ntpath.abspath(child))
        parent_norm = ntpath.normcase(ntpath.abspath(parent))
        return ntpath.commonpath([child_norm, parent_norm]) == parent_norm
    except ValueError:
        return False


def _line_number(text: str, needle: str) -> int | None:
    for number, line in enumerate(text.splitlines(), 1):
        if needle in line:
            return number
    return None


def _mutable_output_static_probe(repo: Path) -> dict[str, Any]:
    verification = _json_blob(repo, B19_FINAL_SHA, VERIFICATION_PATH)
    commands = verification.get("commands")
    synthetic = verification.get("synthetic")
    if not isinstance(commands, dict) or not isinstance(synthetic, dict):
        raise ValueError("Verification B19 nie zawiera wymaganych sekcji")
    export_command = commands.get("synthetic_export")
    clone_status = commands.get("implementation_clone_after_status")
    paths = synthetic.get("paths")
    if (
        not isinstance(export_command, dict)
        or not isinstance(clone_status, dict)
        or not isinstance(paths, dict)
    ):
        raise ValueError("Verification B19 nie zawiera sciezek wykonania")
    argv = export_command.get("argv")
    export_cwd = export_command.get("cwd")
    clone_root = clone_status.get("cwd")
    if (
        not isinstance(argv, list)
        or not argv
        or not isinstance(export_cwd, str)
        or not isinstance(clone_root, str)
        or not all(isinstance(value, str) for value in paths.values())
    ):
        raise ValueError("Verification B19 ma niepoprawny rekord polecenia")
    try:
        output_index = argv.index("--output-directory") + 1
        output_directory = argv[output_index]
    except (ValueError, IndexError) as exc:
        raise ValueError("Brak --output-directory w rekordzie B19") from exc
    if not isinstance(output_directory, str):
        raise ValueError("Niepoprawny output-directory")
    script = _blob(repo, B19_FINAL_SHA, VERIFY_SCRIPT_PATH).decode("utf-8")
    line_evidence = {
        "mutable_output_root": _line_number(
            script, 'output = ROOT / "data/agent-debate/round-19"'
        ),
        "detached_child_with_external_output": _line_number(
            script, '"--output-directory", synthetic_dir'
        ),
        "parent_report_read": _line_number(
            script, 'synthetic = json.loads((synthetic_dir / "report.json")'
        ),
        "manifest_from_mutable_output": _line_number(
            script, "generated += sorted(path.relative_to(ROOT).as_posix()"
        ),
    }
    recorded_paths = list(paths.values())
    outputs_outside = (
        not _is_within_windows(output_directory, clone_root)
        and all(not _is_within_windows(value, clone_root) for value in recorded_paths)
    )
    detached_execution = _is_within_windows(export_cwd, clone_root)
    parent_reads = line_evidence["parent_report_read"] is not None
    manifest_from_mutable = line_evidence["manifest_from_mutable_output"] is not None
    pre_receipt = _json_blob(repo, B19_FINAL_SHA, PREPUBLICATION_RECEIPT_PATH)
    static_proven = (
        detached_execution
        and outputs_outside
        and parent_reads
        and manifest_from_mutable
        and all(value is not None for value in line_evidence.values())
        and pre_receipt.get("local_worktree_clean") is False
    )
    return {
        "status": "PARTIAL_STATIC_EVIDENCE" if static_proven else "INSUFFICIENT",
        "evidence_kind": "PINNED_GIT_BLOB_AND_RECORDED_PATH_CLASSIFICATION",
        "verify_script_sha256": _sha256(script.encode("utf-8")),
        "line_evidence": line_evidence,
        "detached_code_execution": detached_execution,
        "recorded_output_path_count": len(recorded_paths) + 1,
        "all_recorded_outputs_outside_detached_clone": outputs_outside,
        "parent_reads_report_from_mutable_output": parent_reads,
        "manifest_built_from_mutable_output": manifest_from_mutable,
        "prepublication_checkout_reported_clean": pre_receipt.get(
            "local_worktree_clean"
        ),
        "prepublication_status_stdout_bytes": (
            pre_receipt.get("final_status_command", {}).get("stdout_bytes")
            if isinstance(pre_receipt.get("final_status_command"), dict) else None
        ),
        "dynamic_mutation_attempted": False,
        "limitation": (
            "Dowod statyczny wykazuje rozdzielenie pinned code i mutable I/O; "
            "nie twierdzi, ze w historycznym przebiegu wystapila mutacja."
        ),
        "expected_safe_contract": {
            "all_experiment_io_inside_detached_sandbox": True,
            "reject_hash_change_before_manifest": True,
            "receipt_passed_on_mismatch": False,
            "final_outputs_on_mismatch": False,
        },
    }


def audit(agent_b_root: Path) -> dict[str, Any]:
    """Run the bounded audit and distinguish audit success from subject safety."""

    repo = Path(agent_b_root).resolve()
    revisions = (
        B18_SHA, PROTOCOL_SHA, IMPLEMENTATION_SHA, PUBLICATION_SHA, B19_FINAL_SHA
    )
    if not all(_exact_revision(repo, revision) for revision in revisions):
        raise ValueError("Repozytorium nie zawiera wszystkich przypietych rewizji B19")
    initial_head, initial_clean = _repository_state(repo)
    if initial_head != B19_FINAL_SHA or not initial_clean:
        raise ValueError("--agent-b-root musi byc czystym checkoutem finalnego B19")
    logical_commits = _git_text(
        repo, "rev-list", "--reverse", f"{B18_SHA}..{B19_FINAL_SHA}"
    ).splitlines()
    receipt = _independent_receipt_audit(repo)
    invalid_mode = _invalid_mode_probe(repo)
    mutable_output = _mutable_output_static_probe(repo)
    final_head, final_clean = _repository_state(repo)
    result = {
        "schema_version": "agent-a-round-22-b19-contract-audit-1.0",
        "target_revision": B19_FINAL_SHA,
        "publication_revision": PUBLICATION_SHA,
        "implementation_revision": IMPLEMENTATION_SHA,
        "protocol_revision": PROTOCOL_SHA,
        "base_revision": B18_SHA,
        "lineage": {"logical_commits": logical_commits},
        "input_boundary": {
            "agent_b_artifact_access": "pinned Git blobs only",
            "single_executed_probe": "verified clean-checkout synthetic code",
            "initial_head_is_target": initial_head == B19_FINAL_SHA,
            "initial_worktree_clean": initial_clean,
            "final_head_is_target": final_head == B19_FINAL_SHA,
            "final_worktree_clean": final_clean,
            "network_real_data_scorer_model_or_gpu_used": False,
            "raw_conllu_content_persisted_or_displayed": False,
        },
        "invalid_mode_probe": invalid_mode,
        "publication_receipt": receipt,
        "mutable_output_probe": mutable_output,
        "b19_contract_status": "FAIL",
    }
    expected_lineage = [
        PROTOCOL_SHA, IMPLEMENTATION_SHA, PUBLICATION_SHA, B19_FINAL_SHA
    ]
    result["audit_status"] = "PASS" if (
        logical_commits == expected_lineage
        and invalid_mode["gap_reproduced"]
        and receipt["independent_structure_passed"]
        and mutable_output["status"] == "PARTIAL_STATIC_EVIDENCE"
        and final_head == initial_head == B19_FINAL_SHA
        and initial_clean and final_clean
    ) else "FAIL"
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--agent-b-root", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    result = audit(args.agent_b_root)
    serialized = json.dumps(result, ensure_ascii=False, indent=2, allow_nan=False) + "\n"
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(serialized, encoding="utf-8", newline="\n")
    print(serialized, end="")
    return 0 if result["audit_status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())

"""Audit B20's pinned-snapshot and publication-receipt contracts.

The caller supplies a clean checkout at the exact final B20 revision.  All
repository evidence is read as immutable Git blobs.  The only executed B20
code is extracted from pinned blobs into temporary directories and operates on
the tiny synthetic fixture shipped in B20's test.  The JSON report contains
only hashes, counts and contract flags, never CoNLL-U bytes or scorer output.
"""

from __future__ import annotations

import argparse
from contextlib import contextmanager, redirect_stderr, redirect_stdout
import hashlib
import importlib.util
from io import StringIO
import json
import os
from pathlib import Path, PurePosixPath
import subprocess
import sys
import tempfile
from typing import Any, Iterator, Mapping, Sequence
from unittest.mock import patch


B19_FINAL_SHA = "03befe9585fe8fa7b7704f91b547a17999ac9268"
PROTOCOL_SHA = "119dc6d2281da90e651bbc929be74b66b97c3d97"
IMPLEMENTATION_SHA = "48358712e8bbd4bf3af8d88235cedaacb4e97999"
PUBLICATION_SHA = "272a5c807e7bb562d4b35272ab320ff04e6a87a9"
B20_FINAL_SHA = "b21a7c15cb0b8523a57683306d817664518355c0"

MANIFEST_PATH = "kod/data/agent-debate/round-20/MANIFEST.json"
PREPUBLICATION_RECEIPT_PATH = (
    "kod/data/agent-debate/round-20/manifest_receipt.json"
)
RECEIPT_PATH = "kod/data/agent-debate/round-20/publication_receipt.json"
POSTEP_PATH = "POSTEP.md"
FIXTURE_PATH = "kod/tests/test_scoring_snapshot.py"
RUNTIME_PATHS = (
    FIXTURE_PATH,
    "kod/scripts/score_official.py",
    "kod/scripts/scoring_snapshot.py",
    "kod/src/eval/alignment_provenance.py",
)


def _git(repo: Path, *args: str, text: bool = False) -> subprocess.CompletedProcess:
    """Run one noninteractive, read-only Git query."""

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


def _file_sha256(path: Path) -> str:
    return _sha256(path.read_bytes())


def _exact_revision(repo: Path, revision: str) -> bool:
    result = _git(repo, "rev-parse", "--verify", revision + "^{commit}", text=True)
    return result.returncode == 0 and result.stdout.strip() == revision


def _repository_state(repo: Path) -> tuple[str, bool]:
    head = _git_text(repo, "rev-parse", "HEAD").strip()
    status = _git_text(repo, "status", "--porcelain=v1", "--untracked-files=all")
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


def _canonical_descriptor(data: bytes, expected: Mapping[str, Any]) -> dict[str, Any]:
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
    receipt_bytes = _blob(repo, B20_FINAL_SHA, RECEIPT_PATH)
    receipt = json.loads(receipt_bytes.decode("utf-8"))
    manifest_bytes = _blob(repo, PUBLICATION_SHA, MANIFEST_PATH)
    manifest = json.loads(manifest_bytes.decode("utf-8"))
    pre_receipt = _json_blob(repo, PUBLICATION_SHA, PREPUBLICATION_RECEIPT_PATH)
    if not isinstance(receipt, dict) or not isinstance(manifest, dict):
        raise ValueError("Manifest lub receipt nie jest obiektem JSON")

    entries: dict[str, Mapping[str, Any]] = {}
    for section in ("inputs", "outputs"):
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
        if publication_data is None or _canonical_descriptor(publication_data, expected) != expected:
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
            repo, "diff-tree", "--no-commit-id", "--name-only", "-r", B20_FINAL_SHA
        ).splitlines() if line
    )
    checks = receipt.get("checks")
    if not isinstance(checks, dict):
        checks = {}
    attestation = receipt.get("attestation_scope")
    if not isinstance(attestation, dict):
        attestation = {}
    receipt_partitions = receipt.get("provenance_partitions")
    if not isinstance(receipt_partitions, dict):
        receipt_partitions = {}
    receipt_impl = receipt_partitions.get("implementation_inputs")
    receipt_generated = receipt_partitions.get("generated_outputs")
    receipt_impl_count = receipt_impl.get("count") if isinstance(receipt_impl, dict) else None
    receipt_generated_count = (
        receipt_generated.get("count") if isinstance(receipt_generated, dict) else None
    )
    independent = {
        "manifest_entry_count": len(entries),
        "implementation_count": len(implementation_paths),
        "generated_count": len(generated_paths),
        "complete_and_disjoint": complete_and_disjoint,
        "implementation_mismatches": sorted(implementation_mismatches),
        "generated_present_at_implementation": sorted(generated_present),
        "publication_mismatches": sorted(publication_mismatches),
    }
    result = {
        "final_blob_sha256": _sha256(receipt_bytes),
        "target_commit_added_paths": target_paths,
        "receipt_present_at_publication": (
            _blob_optional(repo, PUBLICATION_SHA, RECEIPT_PATH) is not None
        ),
        "receipt_present_at_final": True,
        "declared_publication_commit": receipt.get("publication_commit"),
        "declared_attested_commit": attestation.get("attested_commit"),
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
        "independent_partitions": independent,
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
        and independent["manifest_entry_count"] == 112
        and independent["implementation_count"] == receipt_impl_count == 109
        and independent["generated_count"] == receipt_generated_count == 3
        and complete_and_disjoint
        and not implementation_mismatches
        and not generated_present
        and not publication_mismatches
    )
    return result


@contextmanager
def _pinned_fixture_module(repo: Path) -> Iterator[tuple[Any, dict[str, str]]]:
    """Extract and import the exact B20 runtime blobs without touching its checkout."""

    with tempfile.TemporaryDirectory(prefix="a23-b20-pinned-") as directory:
        root = Path(directory)
        hashes: dict[str, str] = {}
        for relative in RUNTIME_PATHS:
            data = _blob(repo, B20_FINAL_SHA, relative)
            target = root / PurePosixPath(relative)
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(data)
            hashes[relative] = _sha256(data)
        module_path = root / PurePosixPath(FIXTURE_PATH)
        module_name = f"_a23_b20_fixture_{id(root)}"
        specification = importlib.util.spec_from_file_location(module_name, module_path)
        if specification is None or specification.loader is None:
            raise RuntimeError("Nie mozna zaladowac przypietego fixture B20")
        module = importlib.util.module_from_spec(specification)
        before_modules = set(sys.modules)
        old_path = list(sys.path)
        old_no_bytecode = sys.dont_write_bytecode
        sys.path.insert(0, str(root / "kod"))
        sys.dont_write_bytecode = True
        sys.modules[module_name] = module
        try:
            specification.loader.exec_module(module)
            yield module, hashes
        finally:
            sys.path[:] = old_path
            sys.dont_write_bytecode = old_no_bytecode
            for name in set(sys.modules) - before_modules:
                loaded = sys.modules.get(name)
                loaded_file = getattr(loaded, "__file__", None)
                if name == module_name or (
                    loaded_file is not None
                    and str(Path(loaded_file).resolve()).startswith(str(root.resolve()))
                ):
                    sys.modules.pop(name, None)


def _report_inputs(fixture_module: Any, report: Mapping[str, Any]) -> Mapping[str, Any]:
    return fixture_module._snapshot_report(report)


def _unpinned_prediction_probe(fixture_module: Any) -> dict[str, Any]:
    with tempfile.TemporaryDirectory(prefix="a23-b20-unpinned-pred-") as directory:
        fixture = fixture_module._make_fixture(Path(directory))
        anchor_before = _file_sha256(fixture.anchor)
        pred_before = _file_sha256(fixture.pred_original)
        original = fixture.pred_original.read_bytes()
        marker = b"Entity=(e1-person-1)"
        if marker not in original:
            raise AssertionError("Syntetyczny fixture B20 nie zawiera oczekiwanej Entity")
        fixture.pred_original.write_bytes(original.replace(marker, b"_", 1))
        pred_after = _file_sha256(fixture.pred_original)
        trace = fixture_module._invoke(fixture, fixture_module._base_argv(fixture))
        if not fixture.output.is_file():
            raise AssertionError("B20 nie utworzyl raportu dla kontrproby")
        report = json.loads(fixture.output.read_text(encoding="utf-8"))
        report_inputs = _report_inputs(fixture_module, report)
        checked = report.get("input_anchor", {}).get("checked_inputs", {})
        if not isinstance(checked, dict):
            raise ValueError("Raport B20 nie zawiera input_anchor.checked_inputs")
        result = {
            "synthetic_fixture": True,
            "anchor_sha256_before": anchor_before,
            "anchor_sha256_after": _file_sha256(fixture.anchor),
            "pred_original_sha256_before": pred_before,
            "pred_original_sha256_after": pred_after,
            "report_pred_original_sha256": report_inputs["pred_on_original"][
                "scored_sha256"
            ],
            "anchor_checked_input_keys": sorted(checked),
            "main_return_value": trace["main_return_value"],
            "raised_type": (
                None if trace["raised"] is None else trace["raised"]["type"]
            ),
            "scorer_call_count": trace["scorer_calls"],
            "alignment_provenance_status": report.get(
                "alignment_provenance", {}
            ).get("status"),
            "main_table_eligible": report.get("main_table_eligible"),
            "final_output_created": fixture.output.is_file(),
            "private_snapshot_cleaned": trace["snapshot_cleaned"],
            "subject_main_table_contract": "FAIL",
            "expected_safe_contract": {
                "reject_unpinned_prediction": True,
                "scorer_call_count": 0,
                "main_table_eligible": False,
                "final_output_created": False,
            },
        }
        result["gap_reproduced"] = (
            pred_before != pred_after
            and result["anchor_sha256_before"] == result["anchor_sha256_after"]
            and result["main_return_value"] == 0
            and result["raised_type"] is None
            and result["scorer_call_count"] == 8
            and result["alignment_provenance_status"]
            == "VERIFIED_RECORDED_PROVENANCE"
            and result["main_table_eligible"] is True
            and result["report_pred_original_sha256"] == pred_after
            and "pred_on_original_sha256" not in checked
            and "eval_json_sha256" not in checked
        )
        return result


def _transient_child_read_probe(fixture_module: Any) -> dict[str, Any]:
    """Let the mocked fifth child observe transient bytes restored before return."""

    with tempfile.TemporaryDirectory(prefix="a23-b20-transient-read-") as directory:
        fixture = fixture_module._make_fixture(Path(directory))
        real_snapshot_context = fixture_module.score_official.scoring_input_snapshot
        captured: dict[str, Any] = {}
        scorer_calls = 0
        observed_sha256: str | None = None
        restored_sha256: str | None = None
        mutated_path_in_child_argv = False

        @contextmanager
        def capture_snapshot(*args: object, **kwargs: object) -> Iterator[object]:
            with real_snapshot_context(*args, **kwargs) as snapshot:
                captured["paths"] = fixture_module._paths_from_snapshot(snapshot)
                captured["record"] = snapshot.record()
                yield snapshot
                captured["cleaned_paths"] = tuple(snapshot.paths.values())

        def child(
            command: Sequence[object], **kwargs: object
        ) -> subprocess.CompletedProcess[str]:
            nonlocal scorer_calls, observed_sha256, restored_sha256
            nonlocal mutated_path_in_child_argv
            command_strings = [os.fspath(value) for value in command]
            is_version = bool(command_strings and command_strings[-1] == "--version")
            if not is_version:
                scorer_calls += 1
                if scorer_calls == 5:
                    target = captured["paths"]["gold_subtoken"]
                    mutated_path_in_child_argv = str(target) in command_strings
                    stable = target.read_bytes()
                    target.write_bytes(stable + b"# transient-synthetic-byte\n")
                    observed_sha256 = _file_sha256(target)
                    target.write_bytes(stable)
                    restored_sha256 = _file_sha256(target)
            return fixture_module._completed(command_strings)

        stdout = StringIO()
        stderr = StringIO()
        main_return_value: int | None = None
        raised_type: str | None = None
        with fixture_module._cwd(fixture.root), patch.object(
            sys, "argv", fixture_module._base_argv(fixture)
        ), patch.object(
            fixture_module.score_official,
            "scoring_input_snapshot",
            capture_snapshot,
        ), patch.object(
            fixture_module.score_official.subprocess, "run", side_effect=child
        ), redirect_stdout(stdout), redirect_stderr(stderr):
            try:
                main_return_value = fixture_module.score_official.main()
            except (Exception, SystemExit) as error:
                raised_type = type(error).__name__

        if not fixture.output.is_file():
            raise AssertionError("B20 nie utworzyl raportu transient probe")
        report = json.loads(fixture.output.read_text(encoding="utf-8"))
        inputs = _report_inputs(fixture_module, report)
        report_sha256 = inputs["gold_subtoken"]["scored_sha256"]
        cleaned_paths = captured.get("cleaned_paths", ())
        result = {
            "classification": "ACKNOWLEDGED_POINT_CHECK_LIMITATION",
            "claimed_undisclosed_by_agent_b": False,
            "synthetic_mocked_child": True,
            "mutated_at_scorer_call": 5,
            "mutated_role": "gold_subtoken",
            "mutated_path_in_child_argv": mutated_path_in_child_argv,
            "child_observed_sha256": observed_sha256,
            "restored_snapshot_sha256": restored_sha256,
            "report_scored_sha256": report_sha256,
            "main_return_value": main_return_value,
            "raised_type": raised_type,
            "scorer_call_count": scorer_calls,
            "main_table_eligible": report.get("main_table_eligible"),
            "final_output_created": fixture.output.is_file(),
            "private_snapshot_cleaned": bool(cleaned_paths) and all(
                not Path(path).exists() for path in cleaned_paths
            ),
            "expected_safe_contract": {
                "reject_child_digest_mismatch": True,
                "scorer_call_count_before_rejection": 5,
                "main_table_eligible": False,
                "final_output_created": False,
            },
        }
        result["gap_reproduced"] = (
            observed_sha256 is not None
            and mutated_path_in_child_argv
            and restored_sha256 == report_sha256
            and observed_sha256 != report_sha256
            and main_return_value == 0
            and raised_type is None
            and scorer_calls == 8
            and result["main_table_eligible"] is True
        )
        return result


def _postep_static_audit(repo: Path) -> dict[str, Any]:
    text = _blob(repo, B20_FINAL_SHA, POSTEP_PATH).decode("utf-8")
    lines = text.splitlines()

    def locate(needle: str) -> int | None:
        return next((number for number, line in enumerate(lines, 1) if needle in line), None)

    heading = locate("## [B20] Snapshot wejść scorera")
    in_progress = locate("(implementacja w toku)")
    open_tests = locate("Otwarte: test mutacji oryginału/kopii")
    next_step = locate("Następny krok: zakończyć weryfikację B20")
    return {
        "postep_blob_sha256": _sha256(text.encode("utf-8")),
        "b20_heading_found": heading is not None,
        "b20_heading_line": heading,
        "implementation_in_progress_marker_found": in_progress is not None,
        "implementation_in_progress_marker_line": in_progress,
        "open_tests_marker_found": open_tests is not None,
        "open_tests_marker_line": open_tests,
        "finish_verification_next_step_found": next_step is not None,
        "finish_verification_next_step_line": next_step,
        "stale_final_status_reproduced": all(
            value is not None for value in (heading, in_progress, open_tests, next_step)
        ),
    }


def audit(agent_b_root: Path) -> dict[str, Any]:
    """Run the bounded audit and separate successful diagnosis from B20 safety."""

    repo = Path(agent_b_root).resolve()
    revisions = (
        B19_FINAL_SHA, PROTOCOL_SHA, IMPLEMENTATION_SHA, PUBLICATION_SHA, B20_FINAL_SHA
    )
    if not all(_exact_revision(repo, revision) for revision in revisions):
        raise ValueError("Repozytorium nie zawiera wszystkich przypietych rewizji B20")
    initial_head, initial_clean = _repository_state(repo)
    if initial_head != B20_FINAL_SHA or not initial_clean:
        raise ValueError("--agent-b-root musi byc czystym checkoutem finalnego B20")

    lineage = _git_text(
        repo, "rev-list", "--reverse", f"{B19_FINAL_SHA}..{B20_FINAL_SHA}"
    ).splitlines()
    receipt = _independent_receipt_audit(repo)
    postep = _postep_static_audit(repo)
    with _pinned_fixture_module(repo) as (fixture_module, runtime_hashes):
        unpinned = _unpinned_prediction_probe(fixture_module)
        transient = _transient_child_read_probe(fixture_module)

    final_head, final_clean = _repository_state(repo)
    result = {
        "schema_version": "agent-a-round-23-b20-snapshot-audit-1.0",
        "target_revision": B20_FINAL_SHA,
        "publication_revision": PUBLICATION_SHA,
        "implementation_revision": IMPLEMENTATION_SHA,
        "protocol_revision": PROTOCOL_SHA,
        "base_revision": B19_FINAL_SHA,
        "lineage": {"logical_commits": lineage},
        "input_boundary": {
            "agent_b_artifact_access": "pinned Git blobs only",
            "executed_runtime": "pinned blobs extracted to temporary directory",
            "executed_runtime_sha256": runtime_hashes,
            "initial_head_is_target": initial_head == B20_FINAL_SHA,
            "initial_worktree_clean": initial_clean,
            "final_head_is_target": final_head == B20_FINAL_SHA,
            "final_worktree_clean": final_clean,
            "network_real_data_scorer_model_or_gpu_used": False,
            "raw_conllu_content_persisted_or_displayed": False,
        },
        "publication_receipt": receipt,
        "unpinned_prediction_probe": unpinned,
        "transient_child_read_probe": transient,
        "postep_static_audit": postep,
        "b20_main_table_contract_status": "FAIL",
    }
    expected_lineage = [
        PROTOCOL_SHA, IMPLEMENTATION_SHA, PUBLICATION_SHA, B20_FINAL_SHA
    ]
    result["audit_status"] = "PASS" if (
        lineage == expected_lineage
        and receipt["independent_structure_passed"]
        and unpinned["gap_reproduced"]
        and transient["gap_reproduced"]
        and postep["stale_final_status_reproduced"]
        and initial_head == final_head == B20_FINAL_SHA
        and initial_clean and final_clean
    ) else "FAIL"
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--agent-b-root", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    args.output.unlink(missing_ok=True)
    result = audit(args.agent_b_root)
    serialized = json.dumps(result, ensure_ascii=False, indent=2, allow_nan=False) + "\n"
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(serialized, encoding="utf-8", newline="\n")
    print(serialized, end="")
    return 0 if result["audit_status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())

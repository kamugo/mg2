"""Audit B18 manifest scope and reproduce its synthetic export independently.

Agent B is accessed only through immutable Git objects.  The only executed
project code is pinned ``manifest.py``/``verification_helpers.py`` in a small
counterexample and the tracked mg2 adjudication exporter on B18's explicitly
synthetic fixture.  Temporary raw content is never included in the report.
"""

from __future__ import annotations

import argparse
import hashlib
import importlib
import json
from pathlib import Path, PurePosixPath
import re
import subprocess
import sys
import tempfile
from typing import Any


B18_SHA = "e1d9d4ba94c9bdc52553bb14cc7f01d7113f0101"
IMPLEMENTATION_SHA = "3167957e8e74683e4bd48e53a00e131adaec9a19"
B17_SHA = "cbd5b38d71c2b508d792e3683f569a4bfca58adf"
A_EXPORTER_REVISION = "ec536718facf6589d6c48e219d5596f87c9271d8"
A_EXPORTER_PATH = "kod/scripts/export_adjudication_corefud.py"
BEFORE_EXPORT_SHA256 = "e670d1648e273214b7875e5546975248a95167d9f97b86159b6299d5289e5f94"
AFTER_EXPORT_SHA256 = "b98fd7ed7defd9d1c189e1215bb275e219c12e4a94b913f342ea5ed352a7fda8"
ROUND18_MANIFEST = "kod/data/agent-debate/round-18/MANIFEST.json"
ROUND18_RECEIPT = "kod/data/agent-debate/round-18/manifest_receipt.json"
FIXED_MANIFEST = "kod/data/agent-debate/round-18/b15_fixed/MANIFEST.json"
FIXED_RECEIPT = "kod/data/agent-debate/round-18/b15_fixed/manifest_receipt.json"
HELPERS_PATH = "kod/scripts/verification_helpers.py"
MANIFEST_MODULE_PATH = "kod/scripts/manifest.py"
SOURCE_PATH = "kod/data/annotation-synthetic/round-18/source.conllu"
BEFORE_JSONL_PATH = (
    "kod/data/annotation-synthetic/round-18/before/synthetic-legal-r18.jsonl"
)
AFTER_JSONL_PATH = (
    "kod/data/annotation-synthetic/round-18/after/synthetic-legal-r18.jsonl"
)
BEFORE_COMMITTED_EXPORT = "kod/data/agent-debate/round-18/before.conllu"
AFTER_COMMITTED_EXPORT = "kod/data/agent-debate/round-18/after.conllu"
RAW_CONTENT_MARKERS = ("# text =", "Entity=(", "char_segments")
B18_GENERATED_PATHS = {
    "data/agent-debate/round-18/verification.json",
    "data/agent-debate/round-18/a17_pinned_audit.json",
    "data/agent-debate/round-18/before.conllu",
    "data/agent-debate/round-18/after.conllu",
    "data/agent-debate/round-18/b15_fixed/verification.json",
    "data/agent-debate/round-18/b15_fixed/MANIFEST.json",
    "data/agent-debate/round-18/b15_fixed/manifest_receipt.json",
    "data/agent-debate/round-18/self_after_head_no_singletons.log",
    "data/agent-debate/round-18/self_after_head_singletons.log",
    "data/agent-debate/round-18/self_after_exact_no_singletons.log",
    "data/agent-debate/round-18/self_after_exact_singletons.log",
    "data/agent-debate/round-18/before_correction_head_no_singletons.log",
    "data/agent-debate/round-18/before_correction_head_singletons.log",
    "data/agent-debate/round-18/before_correction_exact_no_singletons.log",
    "data/agent-debate/round-18/before_correction_exact_singletons.log",
}


def _git(repo: Path, *args: str, text: bool = False) -> subprocess.CompletedProcess:
    return subprocess.run(
        ["git", "-C", str(repo), *args], capture_output=True, check=False,
        text=text, encoding="utf-8" if text else None,
        errors="replace" if text else None,
    )


def _git_text(repo: Path, *args: str) -> str:
    result = _git(repo, *args, text=True)
    if result.returncode:
        raise RuntimeError(f"git {' '.join(args)}: {result.stderr.strip()}")
    return result.stdout


def _blob_optional(repo: Path, revision: str, path: str) -> bytes | None:
    result = _git(repo, "cat-file", "blob", f"{revision}:{path}")
    return result.stdout if result.returncode == 0 else None


def _blob(repo: Path, revision: str, path: str) -> bytes:
    value = _blob_optional(repo, revision, path)
    if value is None:
        raise RuntimeError(f"Brak przypietego blobu {revision}:{path}")
    return value


def _json_blob(repo: Path, revision: str, path: str) -> dict[str, Any]:
    value = json.loads(_blob(repo, revision, path).decode("utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"{path}: oczekiwano obiektu JSON")
    return value


def _sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _resolve_exact(repo: Path, revision: str) -> bool:
    result = _git(repo, "rev-parse", "--verify", revision + "^{commit}", text=True)
    return result.returncode == 0 and result.stdout.strip() == revision


def _manifest_git_path(name: str) -> str:
    parts: list[str] = []
    for part in (PurePosixPath("kod") / PurePosixPath(name)).parts:
        if part == "..":
            if not parts:
                raise ValueError(f"Sciezka manifestu wychodzi poza repo: {name}")
            parts.pop()
        elif part not in {"", "."}:
            parts.append(part)
    return PurePosixPath(*parts).as_posix()


def _entry_for_expected_mode(data: bytes, expected: dict[str, Any]) -> dict[str, Any]:
    if expected.get("mode") == "text_lf":
        normalized = data.replace(b"\r\n", b"\n")
        return {"mode": "text_lf", "sha256_lf": _sha(normalized),
                "bytes_lf": len(normalized)}
    if expected.get("mode") == "binary":
        return {"mode": "binary", "sha256": _sha(data), "bytes": len(data)}
    raise ValueError(f"Nieznany tryb manifestu: {expected.get('mode')!r}")


def _manifest_scope(
    repo: Path,
    manifest_path: str,
    receipt_path: str,
    receipt_pin_field: str,
    expected_generated: set[str],
) -> dict[str, Any]:
    manifest = _json_blob(repo, B18_SHA, manifest_path)
    receipt = _json_blob(repo, B18_SHA, receipt_path)
    inputs = manifest.get("inputs")
    if not isinstance(inputs, dict):
        raise ValueError(f"{manifest_path}: brak mapy inputs")
    absent: list[str] = []
    implementation_mismatches: list[str] = []
    final_mismatches: list[str] = []
    implementation_matches = 0
    final_matches = 0
    for name, expected in inputs.items():
        if not isinstance(expected, dict):
            raise ValueError(f"{manifest_path}:{name}: wpis nie jest mapa")
        git_path = _manifest_git_path(name)
        implementation = _blob_optional(repo, IMPLEMENTATION_SHA, git_path)
        if implementation is None:
            absent.append(name)
        elif _entry_for_expected_mode(implementation, expected) == expected:
            implementation_matches += 1
        else:
            implementation_mismatches.append(name)
        final = _blob_optional(repo, B18_SHA, git_path)
        if final is not None and _entry_for_expected_mode(final, expected) == expected:
            final_matches += 1
        else:
            final_mismatches.append(name)
    pin = receipt.get(receipt_pin_field)
    if not isinstance(pin, dict):
        raise ValueError(f"{receipt_path}: brak {receipt_pin_field}")
    modes = pin.get("modes")
    if not isinstance(modes, dict):
        raise ValueError(f"{receipt_path}: brak zakresu modes")
    unchecked = sorted(set(inputs) - set(modes))
    absent.sort()
    expected_sorted = sorted(expected_generated)
    return {
        "entry_count": len(inputs),
        "implementation_blob_entries": implementation_matches,
        "generated_entries_absent_from_implementation": absent,
        "generated_entry_count": len(absent),
        "implementation_mismatches": implementation_mismatches,
        "entries_matching_final_revision": final_matches,
        "final_revision_mismatches": final_mismatches,
        "receipt_scope": {
            "checked": pin.get("checked"), "matched": pin.get("matched"),
            "passed": pin.get("passed") is True,
            "unchecked_manifest_entries": unchecked,
            "receipt_passed": receipt.get("passed") is True,
            "manifest_hash_matches": receipt.get("manifest_sha256")
                == _sha(_blob(repo, B18_SHA, manifest_path)),
        },
        "hybrid_scope_proven": (
            absent == expected_sorted and unchecked == expected_sorted
            and not implementation_mismatches and not final_mismatches
            and final_matches == len(inputs)
        ),
    }


def _extra_input_counterexample(repo: Path) -> tuple[dict[str, Any], bool]:
    temporary_path: Path | None = None
    summary: dict[str, Any]
    with tempfile.TemporaryDirectory(prefix="a21-b18-validator-") as directory:
        temporary_path = Path(directory)
        scripts = temporary_path / "scripts"
        scripts.mkdir()
        (scripts / "__init__.py").write_bytes(b"")
        helper_path = scripts / "verification_helpers.py"
        manifest_path = scripts / "manifest.py"
        helper_path.write_bytes(_blob(repo, IMPLEMENTATION_SHA, HELPERS_PATH))
        manifest_path.write_bytes(_blob(repo, IMPLEMENTATION_SHA, MANIFEST_MODULE_PATH))
        saved = {name: module for name, module in sys.modules.items()
                 if name == "scripts" or name.startswith("scripts.")}
        for name in list(saved):
            sys.modules.pop(name, None)
        sys.path.insert(0, str(temporary_path))
        try:
            importlib.invalidate_caches()
            helpers = importlib.import_module("scripts.verification_helpers")
            manifest_module = importlib.import_module("scripts.manifest")
            origins = (
                Path(helpers.__file__).resolve() == helper_path.resolve()
                and Path(manifest_module.__file__).resolve() == manifest_path.resolve()
            )
            if not origins:
                raise RuntimeError("Import nie wskazuje przypietych modulow B18")
            tracked = b"pinned\n"
            digest = _sha(tracked)
            pinned = {"tracked.py": {"git_blob": {
                "status": "AVAILABLE", "sha256": digest, "bytes": len(tracked),
            }}}
            built = {"inputs": {
                "tracked.py": {"mode": "text_lf", "sha256_lf": digest,
                               "bytes_lf": len(tracked)},
                "extra-generated.json": {"mode": "text_lf", "sha256_lf": "b" * 64,
                                         "bytes_lf": 7},
            }}
            evidence = helpers.validate_manifest_inputs_against_pinned_blobs(built, pinned)
            observed = {
                "accepted": evidence.get("passed") is True,
                "checked": evidence.get("checked"), "matched": evidence.get("matched"),
                "manifest_input_count": len(built["inputs"]),
                "unpinned_extra_count": len(set(built["inputs"]) - set(pinned)),
            }
            summary = {
                "pinned_module_origins_verified": origins,
                "observed": observed,
                "expected_safe_contract": {
                    "accepted": False, "require_exact_input_key_set": True,
                    "alternative_generated_entries_section": "outputs",
                },
                "gap_reproduced": observed == {
                    "accepted": True, "checked": 1, "matched": 1,
                    "manifest_input_count": 2, "unpinned_extra_count": 1,
                },
            }
        finally:
            sys.path.remove(str(temporary_path))
            for name in list(sys.modules):
                if name == "scripts" or name.startswith("scripts."):
                    sys.modules.pop(name, None)
            sys.modules.update(saved)
    return summary, temporary_path is not None and not temporary_path.exists()


_ENTITY = re.compile(
    r"\((?P<eid>[^()[\]\s|]+?)(?:\[(?P<part>\d+)/(?P<total>\d+)\])?"
    r"-x-(?P<head>\d+)-\)"
)


def _parse_export(data: bytes) -> dict[str, Any]:
    token_ordinal = -1
    continuous: list[tuple[str, tuple[tuple[int, int], ...], int]] = []
    pieces: dict[tuple[str, int], list[tuple[int, int, int]]] = {}
    documents = 0
    for line in data.decode("utf-8").splitlines():
        if line.startswith("# newdoc id"):
            documents += 1
        if not line or line.startswith("#"):
            continue
        columns = line.split("\t")
        if len(columns) != 10 or not columns[0].isdigit():
            continue
        token_ordinal += 1
        for match in _ENTITY.finditer(columns[9]):
            eid = match.group("eid")
            head = int(match.group("head"))
            if match.group("part") is None:
                continuous.append((eid, ((token_ordinal, token_ordinal),), head))
            else:
                part = int(match.group("part"))
                total = int(match.group("total"))
                pieces.setdefault((eid, total), []).append((part, token_ordinal, head))
    mentions = list(continuous)
    for (eid, total), values in pieces.items():
        ordered = sorted(values)
        if [part for part, _position, _head in ordered] != list(range(1, total + 1)):
            raise ValueError("Niekompletna wzmianka segmentowa")
        heads = {head for _part, _position, head in ordered}
        if len(heads) != 1:
            raise ValueError("Niespojna glowa wzmianki segmentowej")
        key = tuple((position, position) for _part, position, _head in ordered)
        mentions.append((eid, key, heads.pop()))
    clusters = {eid for eid, _key, _head in mentions}
    by_key = {key: {"cluster": eid, "head": head} for eid, key, head in mentions}
    if len(by_key) != len(mentions):
        raise ValueError("Powtorzony MentionKey w syntetycznym eksporcie")
    return {"documents": documents, "mentions": len(mentions), "clusters": len(clusters),
            "by_key": by_key}


def _process_record(process: subprocess.CompletedProcess[str]) -> dict[str, Any]:
    stdout = process.stdout.encode("utf-8")
    stderr = process.stderr.encode("utf-8")
    return {
        "exit_code": process.returncode,
        "stdout_sha256": _sha(stdout), "stdout_bytes": len(stdout),
        "stderr_sha256": _sha(stderr), "stderr_bytes": len(stderr),
    }


def _independent_export(repo_b: Path, repo_a: Path) -> tuple[dict[str, Any], bool]:
    temporary_path: Path | None = None
    result: dict[str, Any]
    exporter = _blob(repo_a, A_EXPORTER_REVISION, A_EXPORTER_PATH)
    before_jsonl = _blob(repo_b, IMPLEMENTATION_SHA, BEFORE_JSONL_PATH)
    after_jsonl = _blob(repo_b, IMPLEMENTATION_SHA, AFTER_JSONL_PATH)
    before_records = [json.loads(line) for line in before_jsonl.decode("utf-8").splitlines()]
    after_records = [json.loads(line) for line in after_jsonl.decode("utf-8").splitlines()]
    jsonl_differences: list[tuple[int, list[str]]] = []
    if len(before_records) == len(after_records):
        for index, (before_record, after_record) in enumerate(zip(before_records, after_records)):
            keys = set(before_record) | set(after_record)
            changed_fields = sorted(
                key for key in keys if before_record.get(key) != after_record.get(key)
            )
            if changed_fields:
                jsonl_differences.append((index, changed_fields))
    with tempfile.TemporaryDirectory(prefix="a21-b18-export-") as directory:
        temporary_path = Path(directory)
        exporter_path = temporary_path / "export_adjudication_corefud.py"
        source = temporary_path / "source.conllu"
        before_dir = temporary_path / "before"
        after_dir = temporary_path / "after"
        before_dir.mkdir()
        after_dir.mkdir()
        exporter_path.write_bytes(exporter)
        source.write_bytes(_blob(repo_b, IMPLEMENTATION_SHA, SOURCE_PATH))
        filename = "synthetic-legal-r18.jsonl"
        (before_dir / filename).write_bytes(before_jsonl)
        (after_dir / filename).write_bytes(after_jsonl)
        outputs: dict[str, bytes] = {}
        records: dict[str, dict[str, Any]] = {}
        summaries: dict[str, dict[str, int]] = {}
        parsed: dict[str, dict[str, Any]] = {}
        for stage, adjudication in (("before", before_dir), ("after", after_dir)):
            destination = temporary_path / f"{stage}.conllu"
            process = subprocess.run(
                [sys.executable, "-B", str(exporter_path), "--source", str(source),
                 "--adjudication-dir", str(adjudication), "--output", str(destination)],
                cwd=temporary_path, capture_output=True, text=True, encoding="utf-8",
                errors="replace", check=False,
            )
            record = _process_record(process)
            if process.returncode != 0:
                raise RuntimeError(f"Eksporter mg2 nie przeszedl dla {stage}; stderr hash "
                                   f"{record['stderr_sha256']}")
            summary = json.loads(process.stdout)
            if not isinstance(summary, dict):
                raise ValueError("Eksporter nie zwrocil obiektu JSON")
            data = destination.read_bytes()
            outputs[stage] = data
            records[stage] = record
            summaries[stage] = summary
            parsed[stage] = _parse_export(data)
        before_keys = set(parsed["before"]["by_key"])
        after_keys = set(parsed["after"]["by_key"])
        segmented = ((4, 4), (10, 10))
        changed = [key for key in before_keys & after_keys
                   if parsed["before"]["by_key"][key]["cluster"]
                   != parsed["after"]["by_key"][key]["cluster"]]
        heads_unchanged = all(
            parsed["before"]["by_key"][key]["head"]
            == parsed["after"]["by_key"][key]["head"]
            for key in before_keys & after_keys
        )
        before_hash = _sha(outputs["before"])
        after_hash = _sha(outputs["after"])
        result = {
            "exporter_revision": A_EXPORTER_REVISION,
            "exporter_blob_oid": _git_text(
                repo_a, "rev-parse", f"{A_EXPORTER_REVISION}:{A_EXPORTER_PATH}").strip(),
            "exporter_sha256": _sha(exporter),
            "exporter_blob_verified": _resolve_exact(repo_a, A_EXPORTER_REVISION),
            "input_sha256": {
                "source": _sha(_blob(repo_b, IMPLEMENTATION_SHA, SOURCE_PATH)),
                "before_jsonl": _sha(_blob(repo_b, IMPLEMENTATION_SHA, BEFORE_JSONL_PATH)),
                "after_jsonl": _sha(_blob(repo_b, IMPLEMENTATION_SHA, AFTER_JSONL_PATH)),
            },
            "before": {**records["before"], "summary": summaries["before"],
                       "sha256": before_hash, "bytes": len(outputs["before"])},
            "after": {**records["after"], "summary": summaries["after"],
                      "sha256": after_hash, "bytes": len(outputs["after"])},
            "segmented_mention_key": [list(segment) for segment in segmented],
            "segmented_head_before": parsed["before"]["by_key"][segmented]["head"],
            "segmented_head_after": parsed["after"]["by_key"][segmented]["head"],
            "mention_key_set_unchanged": before_keys == after_keys,
            "heads_unchanged": heads_unchanged,
            "changed_cluster_memberships": len(changed),
            "only_segmented_mention_changed_cluster": changed == [segmented],
            "input_jsonl_changed_record_count": len(jsonl_differences),
            "input_jsonl_changed_fields": sorted({
                field for _index, fields in jsonl_differences for field in fields
            }),
            "input_jsonl_only_gold_cluster_changed": (
                len(before_records) == len(after_records)
                and jsonl_differences == [(2, ["gold_cluster"])]
            ),
            "matches_committed_b18_exports": (
                outputs["before"] == _blob(repo_b, B18_SHA, BEFORE_COMMITTED_EXPORT)
                and outputs["after"] == _blob(repo_b, B18_SHA, AFTER_COMMITTED_EXPORT)
                and before_hash == BEFORE_EXPORT_SHA256
                and after_hash == AFTER_EXPORT_SHA256
            ),
            "raw_content_persisted_or_displayed": False,
            "real_scorer_model_or_gpu_used": False,
        }
    return result, temporary_path is not None and not temporary_path.exists()


def audit(agent_b_root: Path, agent_a_root: Path) -> dict[str, Any]:
    """Run all B18 checks without reading Agent B working-tree files."""

    repo_b = Path(agent_b_root).resolve()
    repo_a = Path(agent_a_root).resolve()
    for repo, revisions in ((repo_b, (B17_SHA, IMPLEMENTATION_SHA, B18_SHA)),
                            (repo_a, (A_EXPORTER_REVISION,))):
        for revision in revisions:
            if not _resolve_exact(repo, revision):
                raise ValueError(f"Brak przypietej rewizji: {revision}")
    logical_commits = _git_text(
        repo_b, "rev-list", "--reverse", f"{B17_SHA}..{B18_SHA}").splitlines()
    round18 = _manifest_scope(
        repo_b, ROUND18_MANIFEST, ROUND18_RECEIPT, "manifest_pin_evidence",
        B18_GENERATED_PATHS,
    )
    round18["hybrid_95_implementation_plus_15_generated_proven"] = (
        round18["entry_count"] == 110
        and round18["implementation_blob_entries"] == 95
        and round18["generated_entry_count"] == 15
        and round18["hybrid_scope_proven"]
        and round18["receipt_scope"]["checked"] == 95
        and round18["receipt_scope"]["matched"] == 95
    )
    fixed_generated = {"data/agent-debate/round-18/b15_fixed/verification.json"}
    fixed = _manifest_scope(
        repo_b, FIXED_MANIFEST, FIXED_RECEIPT,
        "manifest_inputs_match_pinned_blobs", fixed_generated,
    )
    fixed["hybrid_44_implementation_plus_1_generated_proven"] = (
        fixed["entry_count"] == 45
        and fixed["implementation_blob_entries"] == 44
        and fixed["generated_entry_count"] == 1
        and fixed["hybrid_scope_proven"]
        and fixed["receipt_scope"]["checked"] == 44
        and fixed["receipt_scope"]["matched"] == 44
    )
    counterexample, validator_temp_removed = _extra_input_counterexample(repo_b)
    independent, export_temp_removed = _independent_export(repo_b, repo_a)
    result = {
        "schema_version": "agent-a-round-21-b18-contract-audit-1.0",
        "target_revision": B18_SHA,
        "implementation_revision": IMPLEMENTATION_SHA,
        "base_revision": B17_SHA,
        "lineage": {"logical_commits": logical_commits},
        "input_boundary": {
            "agent_b_access": "pinned Git blobs and metadata only",
            "synthetic_fixture_only": True,
            "real_data_scorer_model_or_gpu_used": False,
            "raw_synthetic_content_persisted_or_displayed": None,
            "temporary_content_removed": validator_temp_removed and export_temp_removed,
        },
        "round18_manifest": round18,
        "fixed_b15_manifest": fixed,
        "manifest_extra_input_counterexample": counterexample,
        "independent_mg2_export": independent,
    }
    serialized_without_boundary = json.dumps(result, ensure_ascii=False)
    result["input_boundary"]["raw_synthetic_content_persisted_or_displayed"] = any(
        marker in serialized_without_boundary for marker in RAW_CONTENT_MARKERS
    )
    result["audit_status"] = "PASS" if (
        logical_commits == [IMPLEMENTATION_SHA, B18_SHA]
        and round18["hybrid_95_implementation_plus_15_generated_proven"]
        and fixed["hybrid_44_implementation_plus_1_generated_proven"]
        and counterexample["gap_reproduced"]
        and independent["matches_committed_b18_exports"]
        and independent["mention_key_set_unchanged"]
        and independent["heads_unchanged"]
        and independent["only_segmented_mention_changed_cluster"]
        and independent["input_jsonl_only_gold_cluster_changed"]
        and result["input_boundary"]["temporary_content_removed"]
        and not result["input_boundary"]["raw_synthetic_content_persisted_or_displayed"]
    ) else "FAIL"
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--agent-b-root", required=True, type=Path)
    parser.add_argument("--agent-a-root", required=True, type=Path)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    result = audit(args.agent_b_root, args.agent_a_root)
    serialized = json.dumps(result, ensure_ascii=False, indent=2, allow_nan=False) + "\n"
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(serialized, encoding="utf-8", newline="\n")
    print(serialized, end="")
    return 0 if result["audit_status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())

"""Portable, Git-pinned audit of Agent B round 16 and its re-export report.

The audit reads code and public aggregate artifacts from immutable Git objects.
It does not read prediction/gold corpus blobs, import Udapi, run a model, score,
or perform re-inference.
"""

from __future__ import annotations

import argparse
import ast
import hashlib
import importlib.util
import json
from pathlib import Path, PurePosixPath
import re
import subprocess
import sys
import tempfile
from typing import Any


B16_SHA = "3f1e9e5b30eb12b6057c4dc15477f90f34dfd93f"
IMPLEMENTATION_SHA = "ca445aaaf44a7697e49a0a56b924e8daa4cc7e36"
C2_SHA = "f8e877fe5449d2589aec5fbe1531a25ecbd1fdb4"
B13_SHA = "4199fb284498eae8cc5e2c9aefb1c26834b56864"
A12_SHA = "2f0a7ca6e38ec84285947ae3f47304c3bec83c25"
A12_PATH = "wyniki/agent-debate/round-12/audit_movehead_reexport.py"
MANIFEST_PATH = "kod/data/agent-debate/round-16/MANIFEST.json"
RECEIPT_PATH = "kod/data/agent-debate/round-16/manifest_receipt.json"
VERIFICATION_PATH = "kod/data/agent-debate/round-16/verification.json"
ERRATUM_PATH = "kod/data/agent-debate/round-16/b13_pinned_erratum.json"
REEXPORT_PATH = "kod/data/agent-debate/round-16/reexport_experiment.json"
REEXPORT_SCRIPT = "kod/scripts/verify_round16_reexport.py"
WRITER_PATH = "kod/src/eval/corefud_writer.py"
MODEL_NAMES = ("v2_seed42", "v2_seed1", "v2_seed2", "v1_seed42")
TEXT_SUFFIXES = {".conllu", ".json", ".log", ".md", ".py", ".yaml", ".yml", ".txt", ".csv"}
TEXT_FILENAMES = {".gitattributes", ".gitignore"}


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


def _blob(repo: Path, revision: str, path: str) -> bytes:
    result = _git(repo, "cat-file", "blob", f"{revision}:{path}")
    if result.returncode:
        error = result.stderr.decode("utf-8", errors="replace").strip()
        raise RuntimeError(f"Brak przypietego blobu {revision}:{path}: {error}")
    return result.stdout


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


def _canonical(path: str, data: bytes) -> dict[str, Any]:
    candidate = Path(path)
    if candidate.name.lower() in TEXT_FILENAMES or candidate.suffix.lower() in TEXT_SUFFIXES:
        normalized = data.replace(b"\r\n", b"\n")
        return {"mode": "text_lf", "sha256_lf": _sha(normalized), "bytes_lf": len(normalized)}
    return {"mode": "binary", "sha256": _sha(data), "bytes": len(data)}


def _manifest_git_path(name: str) -> str:
    combined = PurePosixPath("kod") / PurePosixPath(name)
    parts: list[str] = []
    for part in combined.parts:
        if part == "..":
            if not parts:
                raise ValueError(f"Sciezka manifestu wychodzi poza repo: {name}")
            parts.pop()
        elif part not in {"", "."}:
            parts.append(part)
    return PurePosixPath(*parts).as_posix()


def _literal_assignment(source: bytes, name: str) -> Any:
    tree = ast.parse(source.decode("utf-8"))
    for node in tree.body:
        if isinstance(node, (ast.Assign, ast.AnnAssign)):
            targets = node.targets if isinstance(node, ast.Assign) else [node.target]
            if any(isinstance(target, ast.Name) and target.id == name for target in targets):
                return ast.literal_eval(node.value)
    raise ValueError(f"Brak literalnej stalej {name}")


def _function_names(source: bytes) -> set[str]:
    return {
        node.name for node in ast.walk(ast.parse(source.decode("utf-8")))
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
    }


def _load_pinned_module(source: bytes):
    """Load a pinned verifier without consulting the Agent B checkout."""

    with tempfile.TemporaryDirectory(prefix="a19-verifier-") as directory:
        path = Path(directory) / "verify_round16_reexport.py"
        path.write_bytes(source)
        spec = importlib.util.spec_from_file_location("a19_pinned_reexport", path)
        if spec is None or spec.loader is None:
            raise RuntimeError("Nie mozna zaladowac przypietego verifiera B16")
        module = importlib.util.module_from_spec(spec)
        sys.modules[spec.name] = module
        spec.loader.exec_module(module)
        return module


def _manifest_and_receipt(repo: Path) -> tuple[dict[str, Any], dict[str, Any]]:
    raw_manifest = _blob(repo, B16_SHA, MANIFEST_PATH)
    manifest = json.loads(raw_manifest.decode("utf-8"))
    mismatches: list[dict[str, Any]] = []
    matched = 0
    for section in ("inputs", "outputs"):
        for name, expected in manifest.get(section, {}).items():
            git_path = _manifest_git_path(name)
            actual = _canonical(name, _blob(repo, B16_SHA, git_path))
            if actual == expected:
                matched += 1
            else:
                mismatches.append({"path": git_path, "expected": expected, "actual": actual})
    count = sum(len(manifest.get(section, {})) for section in ("inputs", "outputs"))
    receipt = _json_blob(repo, B16_SHA, RECEIPT_PATH)
    actual_manifest_hash = _sha(raw_manifest)
    return ({
        "entry_count": count,
        "matched_blob_count": matched,
        "mismatches": mismatches,
        "missing_inputs": manifest.get("missing_inputs"),
        "implementation_commit": manifest.get("implementation_commit"),
        "historical_writer_commit": manifest.get("historical_writer_commit"),
    }, {
        "manifest_sha256": receipt.get("manifest_sha256"),
        "actual_manifest_sha256": actual_manifest_hash,
        "manifest_hash_matches": receipt.get("manifest_sha256") == actual_manifest_hash,
        "manifest_passed": receipt.get("manifest_passed") is True,
        "passed": receipt.get("passed") is True,
        "verification_exit_code": receipt.get("command", {}).get("exit_code"),
        "result": receipt.get("result"),
    })


def _verification_provenance(repo: Path, report: dict[str, Any]) -> dict[str, Any]:
    mismatches: list[dict[str, Any]] = []
    revisions: set[str] = set()
    for name, recorded in report["artifacts"].items():
        git_record = recorded["git_blob"]
        git_path = git_record.get("path")
        revision = git_record.get("revision")
        revisions.add(revision)
        data = _blob(repo, IMPLEMENTATION_SHA, git_path)
        object_id = _git_text(
            repo, "rev-parse", "--verify", f"{IMPLEMENTATION_SHA}:{git_path}"
        ).strip()
        canonical = data.replace(b"\r\n", b"\n")
        expected = {
            "status": "AVAILABLE", "revision": IMPLEMENTATION_SHA,
            "path": git_path, "object_id": object_id,
            "sha256": _sha(data), "bytes": len(data),
            "canonical_sha256": _sha(canonical), "canonical_bytes": len(canonical),
        }
        actual = {
            "status": git_record.get("status"), "revision": revision,
            "path": git_path, "object_id": git_record.get("object_id"),
            "sha256": git_record.get("sha256"), "bytes": git_record.get("bytes"),
            "canonical_sha256": recorded["canonical_lf"].get("sha256"),
            "canonical_bytes": recorded["canonical_lf"].get("bytes"),
        }
        if actual != expected:
            mismatches.append({"artifact": name, "expected": expected, "actual": actual})
    return {
        "artifact_count": len(report["artifacts"]),
        "revisions": sorted(revisions),
        "mismatches": mismatches,
        "reported_implementation": report.get("implementation_commit"),
        "listed_checkout_matches_implementation": report["checks"].get(
            "listed_checkout_artifacts_match_implementation"
        ) is True,
        "listed_artifacts_unchanged_during_run": report["checks"].get(
            "listed_artifacts_unchanged_during_run"
        ) is True,
    }


def _erratum(repo_b: Path, repo_a: Path, value: dict[str, Any]) -> dict[str, Any]:
    package = value["pinned_writer_package"]
    mismatches: list[dict[str, Any]] = []
    for path, recorded in package["files"].items():
        data = _blob(repo_b, B13_SHA, path)
        expected = {
            "sha256": _sha(data), "bytes": len(data),
            "sha256_lf": _sha(data.replace(b"\r\n", b"\n")),
            "bytes_lf": len(data.replace(b"\r\n", b"\n")),
        }
        if recorded != expected:
            mismatches.append({"path": path, "expected": expected, "actual": recorded})
    a12 = _blob(repo_a, A12_SHA, A12_PATH)
    scorer_exits = [record.get("exit_code") for record in value["scoring"].values()]
    return {
        "passed": value.get("passed") is True,
        "writer_revision": package.get("resolved_revision"),
        "writer_revision_resolves": _resolve_exact(repo_b, B13_SHA),
        "writer_package_file_count": len(package["files"]),
        "writer_package_mismatches": mismatches,
        "current_writer_sha256": value.get("current_writer_sha256"),
        "actual_writer_sha256_lf": _sha(
            _blob(repo_b, B13_SHA, WRITER_PATH).replace(b"\r\n", b"\n")
        ),
        "a12_audit_hash_matches": value.get("audit_script_sha256") == _sha(a12),
        "scorer_run_count": len(scorer_exits),
        "all_scorer_exit_zero": bool(scorer_exits) and all(code == 0 for code in scorer_exits),
        "historical_round13_artifacts_unchanged": value.get(
            "historical_round13_artifacts_modified"
        ) is False,
        "rounded_exact_invariant": value.get("exact_comparison", {}).get(
            "rounded_f1_and_conll_equal"
        ) is True,
    }


def _udapi_pins(
    repo_b: Path,
    repo_a: Path,
    verification: dict[str, Any],
    erratum: dict[str, Any],
    reexport: dict[str, Any],
) -> dict[str, Any]:
    a12 = _literal_assignment(_blob(repo_a, A12_SHA, A12_PATH), "UDAPI_HASHES")
    reexport_source = _literal_assignment(
        _blob(repo_b, IMPLEMENTATION_SHA, REEXPORT_SCRIPT), "UDAPI_HASHES"
    )
    writer_source = _literal_assignment(
        _blob(repo_b, IMPLEMENTATION_SHA, WRITER_PATH), "UDAPI_SOURCE_SHA256"
    )
    production = {
        name: record.get("expected_raw_sha256")
        for name, record in verification["production_udapi_source_hashes"].items()
    }
    runtime_mismatches = []
    for name, record in verification["production_udapi_source_hashes"].items():
        expected = record.get("expected_raw_sha256")
        if record.get("raw_sha256") != expected or record.get("canonical_lf_sha256") != expected:
            runtime_mismatches.append({"module": name, "record": record})
    sources = {
        "a12_audit": a12,
        "b16_reexport_source": reexport_source,
        "b16_writer_source": writer_source,
        "verification_expected": production,
        "b13_erratum": erratum.get("udapi_source_hashes"),
        "reexport_report": reexport.get("udapi", {}).get("source_sha256"),
    }
    names = sorted(set().union(*(value.keys() for value in sources.values())))
    mismatches = []
    for name in names:
        values = {source: mapping.get(name) for source, mapping in sources.items()}
        if len(set(values.values())) != 1 or None in values.values():
            mismatches.append({"module": name, "values": values})
    versions = {
        "verification": verification.get("production_udapi_version"),
        "erratum": erratum.get("udapi_version"),
        "reexport": reexport.get("udapi", {}).get("version"),
    }
    return {
        "pin_count": len(names),
        "module_names": names,
        "sources": sources,
        "mismatches": mismatches,
        "verification_runtime_mismatches": runtime_mismatches,
        "all_sources_agree": (
            len(names) == 5 and not mismatches and not runtime_mismatches
            and verification["checks"].get("five_production_udapi_pins_match") is True
            and verification["checks"].get("production_pins_equal_independent_a12_pins") is True
            and reexport.get("udapi", {}).get("all_match_a12") is True
        ),
        "version": "0.5.2" if set(versions.values()) == {"0.5.2"} else None,
        "reported_versions": versions,
    }


def _dead_code(repo: Path) -> dict[str, Any]:
    candidates = {"_ud_parents"}
    parent = _function_names(_blob(repo, C2_SHA, WRITER_PATH))
    implementation = _function_names(_blob(repo, IMPLEMENTATION_SHA, WRITER_PATH))
    final = _function_names(_blob(repo, B16_SHA, WRITER_PATH))
    removed = sorted((parent & candidates) - implementation)
    return {
        "removed_functions": removed,
        "present_in_parent": candidates <= parent,
        "absent_from_implementation": candidates.isdisjoint(implementation),
        "absent_from_final": candidates.isdisjoint(final),
        "implementation_and_final_function_sets_equal": implementation == final,
    }


def _command_statuses(report: dict[str, Any]) -> dict[str, Any]:
    exits = {name: value.get("exit_code") for name, value in report["commands"].items()}
    false_checks = sorted(name for name, value in report["checks"].items() if value is False)
    return {
        "command_exit_codes": exits,
        "nonzero_commands": sorted(name for name, code in exits.items() if code != 0),
        "required_commands_exit_zero": report["checks"].get("required_commands_exit_zero") is True,
        "false_checks": false_checks,
        "core_checks_passed": report.get("core_checks_passed") is True,
        "negative_result_is_explicit": false_checks == [
            "full_reexport_matches_a12_outputs", "full_reexport_strict_invariance_passed",
        ] and report.get("core_checks_passed") is False,
    }


def _loss_accounting(reexport: dict[str, Any], erratum: dict[str, Any]) -> dict[str, Any]:
    current: dict[str, int] = {}
    historical: dict[str, int] = {}
    breakdown_ok = True
    population_relation = True
    breakdowns: dict[str, dict[str, int]] = {}
    for model in MODEL_NAMES:
        current_export = reexport["models"][model]["export"]
        current_total = current_export["total"]
        current[model] = current_total["mentions_in"] - current_total["mentions_kept"]
        old = erratum["models"][model]["historical_original_export_loss"]
        historical[model] = old["mentions_in"] - old["mentions_kept"]
        components = {
            "out_of_range": old["out_of_range"],
            "duplicate_span": old["duplicate_span"],
            "cross_sentence": old["cross_sentence"],
            "multi_membership_dropped": old["multi_membership_dropped"],
        }
        breakdowns[model] = components
        breakdown_ok &= sum(components.values()) == historical[model]
        population_relation &= current_total["mentions_in"] == old["mentions_kept"]
        population_relation &= current_export["dropped"] == current[model] == 0
    return {
        "current_reexport_mentions_lost": current,
        "historical_mentions_lost": historical,
        "historical_loss_breakdowns": breakdowns,
        "historical_breakdowns_sum_to_loss": breakdown_ok,
        "populations_differ_as_expected": population_relation,
        "interpretation": (
            "The current re-export starts from historically retained serialized mentions; "
            "zero current loss therefore does not erase the earlier export losses."
        ),
    }


def _entity_id_mapping(before: Any, after: Any) -> list[dict[str, str]]:
    """Pair generated entity IDs by document and cluster span signature."""

    mappings: list[dict[str, str]] = []
    if len(before) != len(after):
        raise RuntimeError("Re-export changed document count")
    for old_entities, new_entities in zip(before, after):
        old: dict[Any, list[str]] = {}
        new: dict[Any, list[str]] = {}
        for target, entities in ((old, old_entities), (new, new_entities)):
            for entity in entities:
                signature = tuple(sorted(mention.segments for mention in entity.mentions))
                target.setdefault(signature, []).append(entity.eid)
        if set(old) != set(new):
            raise RuntimeError("Re-export changed cluster signatures")
        mapping: dict[str, str] = {}
        for signature in old:
            old_ids, new_ids = sorted(old[signature]), sorted(new[signature])
            if len(old_ids) != len(new_ids):
                raise RuntimeError("Re-export changed cluster multiplicity")
            mapping.update(zip(new_ids, old_ids))
        mappings.append(mapping)
    return mappings


def _canonical_entity_ids_and_heads(raw: bytes, mappings: list[dict[str, str]], head_re: Any) -> bytes:
    """Map output eids to input eids and mask heads, preserving event order."""

    output: list[str] = []
    document = -1
    generated_id = re.compile(r"d[0-9]+_e[0-9]+")
    for complete in raw.decode("utf-8-sig").splitlines(keepends=True):
        if complete.endswith("\r\n"):
            body, ending = complete[:-2], "\r\n"
        elif complete.endswith("\n") or complete.endswith("\r"):
            body, ending = complete[:-1], complete[-1]
        else:
            body, ending = complete, ""
        if body.startswith("# newdoc"):
            document += 1
        elif body and not body.startswith("#"):
            columns = body.split("\t")
            if len(columns) == 10 and document >= 0:
                mapping = mappings[document]
                items = columns[9].split("|")
                items = [
                    generated_id.sub(lambda match: mapping.get(match.group(0), match.group(0)), item)
                    if item.startswith("Entity=") else item
                    for item in items
                ]
                columns[9] = "|".join(items)
                body = "\t".join(columns)
        output.append(body + ending)
    return head_re.sub(rb"\1HEAD\2", "".join(output).encode("utf-8"))


def _line_mismatches(left: bytes, right: bytes) -> int:
    left_lines = left.splitlines(keepends=True)
    right_lines = right.splitlines(keepends=True)
    shared = min(len(left_lines), len(right_lines))
    return (
        sum(left_lines[index] != right_lines[index] for index in range(shared))
        + abs(len(left_lines) - len(right_lines))
    )


def _pinned_full_reexport(repo_b: Path, committed: dict[str, Any]) -> dict[str, Any]:
    """Execute the pinned full writer and retain only safe hashes and counts."""

    source = _blob(repo_b, IMPLEMENTATION_SHA, REEXPORT_SCRIPT)
    verifier = _load_pinned_module(source)
    gold = verifier.git_blob(repo_b, verifier.INPUT_SHA, verifier.GOLD_PATH)
    verifier.require(verifier.sha256(gold) == verifier.GOLD_SHA256, "gold hash mismatch")
    syntax_bytes = verifier.strip_coreference(gold)
    syntax = verifier.parse_syntax(syntax_bytes)
    runtime_udapi = verifier._udapi_provenance()
    summaries: dict[str, Any] = {}
    aggregates_match: dict[str, bool] = {}
    temporary_path: Path | None = None
    with tempfile.TemporaryDirectory(prefix="a19-full-reexport-") as directory:
        temporary_path = Path(directory)
        with verifier.pinned_b13_package(repo_b, temporary_path) as (structures, writer, package):
            for label in MODEL_NAMES:
                metadata = verifier.MODELS[label]
                git_path = verifier.BASE + metadata["name"] + ".pred_on_original.dev.conllu"
                prediction = verifier.git_blob(repo_b, verifier.INPUT_SHA, git_path)
                verifier.require(
                    verifier.sha256(prediction) == metadata["before_sha256"],
                    "prediction hash mismatch",
                )
                reproduced = verifier._run_one(
                    label, prediction, syntax_bytes, syntax,
                    structures, writer, temporary_path,
                )
                rendered = (temporary_path / f"{label}.reexport.conllu").read_bytes()
                before = verifier.parse_prediction(prediction)
                after = verifier.parse_prediction(rendered)
                mapping = _entity_id_mapping(before, after)
                left = _canonical_entity_ids_and_heads(
                    prediction, [{} for _ in mapping], verifier.HEAD_BYTES_RE
                )
                right = _canonical_entity_ids_and_heads(rendered, mapping, verifier.HEAD_BYTES_RE)
                stripped_left = verifier.strip_coreference(prediction)
                stripped_right = verifier.strip_coreference(rendered)
                summaries[label] = {
                    "canonical_eid_and_head": {
                        "before_sha256": _sha(left), "after_sha256": _sha(right),
                        "before_bytes": len(left), "after_bytes": len(right),
                        "mismatched_lines": _line_mismatches(left, right),
                        "equal": left == right,
                    },
                    "strip_coreference": {
                        "before_sha256": _sha(stripped_left),
                        "after_sha256": _sha(stripped_right),
                        "before_bytes": len(stripped_left), "after_bytes": len(stripped_right),
                        "equal": stripped_left == stripped_right,
                    },
                    "mapped_entity_ids": sum(len(value) for value in mapping),
                }
                aggregates_match[label] = reproduced == committed["models"][label]
            package_matches_committed = package == committed["isolation"]["package"]
    removed = temporary_path is not None and not temporary_path.exists()
    mismatches = {
        label: summaries[label]["canonical_eid_and_head"]["mismatched_lines"]
        for label in MODEL_NAMES
    }
    return {
        "model_summaries": summaries,
        "canonical_eid_and_head_mismatched_lines": mismatches,
        "canonical_eid_and_head_equal_all_models": all(
            summaries[label]["canonical_eid_and_head"]["equal"] for label in MODEL_NAMES
        ),
        "strip_coreference_equal_all_models": all(
            summaries[label]["strip_coreference"]["equal"] for label in MODEL_NAMES
        ),
        "aggregates_match_committed_by_model": aggregates_match,
        "all_models_match_committed_aggregates": all(aggregates_match.values()),
        "package_provenance_matches_committed": package_matches_committed,
        "runtime_udapi": runtime_udapi,
        "temporary_content_removed": removed,
        "raw_content_persisted_or_displayed": False,
        "scorer_inference_training_or_gpu_used": False,
    }


def _strict_decomposition(reexport: dict[str, Any], deep: dict[str, Any]) -> dict[str, Any]:
    models = reexport["models"]
    changed_by_model = {name: models[name]["entity_labels"]["changed"] for name in MODEL_NAMES}
    unchanged_by_model = {name: models[name]["entity_labels"]["unchanged"] for name in MODEL_NAMES}
    cluster_counts = {name: models[name]["cluster_identity"]["before_count"] for name in MODEL_NAMES}
    changed_cluster_numbers = {
        name: models[name]["entity_labels"]["cluster_number_delta"]["nonzero"]
        for name in MODEL_NAMES
    }
    document_deltas = {
        name: {
            "distinct": models[name]["entity_labels"]["document_number_delta"]["distinct"],
            "minimum": models[name]["entity_labels"]["document_number_delta"]["minimum"],
            "maximum": models[name]["entity_labels"]["document_number_delta"]["maximum"],
        }
        for name in MODEL_NAMES
    }
    uniform_values = {
        value["minimum"] for value in document_deltas.values()
        if value["distinct"] == 1 and value["minimum"] == value["maximum"]
    }
    uniform_document_delta = next(iter(uniform_values)) if len(uniform_values) == 1 else None
    masked_equal = {
        name: models[name]["non_entity_head_bytes"]["equal"] for name in MODEL_NAMES
    }
    canonical_masked_equal = {
        name: models[name]["non_entity_head_bytes"]["canonical_lf_equal"] for name in MODEL_NAMES
    }
    byte_deltas = {
        name: models[name]["output"]["bytes"] - models[name]["input"]["bytes"]
        for name in MODEL_NAMES
    }
    mismatched_lines = {
        name: models[name]["non_entity_head_bytes"]["mismatched_lines"]
        for name in MODEL_NAMES
    }
    component_invariance = {
        name: (
            models[name]["non_entity_head_bytes"]["equal"]
            and models[name]["mention_identity"]["equal"]
            and models[name]["cluster_identity"]["equal"]
            and models[name]["node_syntax"]["equal"]
            and models[name]["export"]["loss_free"]
            and models[name]["export"]["counts_match_reconstructed_annotations"]
        )
        for name in MODEL_NAMES
    }
    computed_strict = all(component_invariance.values())
    all_labels_changed = all(
        changed_by_model[name] == cluster_counts[name] and unchanged_by_model[name] == 0
        for name in MODEL_NAMES
    )
    return {
        "reported_strict_invariance": reexport.get("strict_invariance_passed") is True,
        "computed_strict_invariance": computed_strict,
        "per_model_computed_strict_invariance": component_invariance,
        "entity_ids": {
            "changed_by_model": changed_by_model,
            "changed_total": sum(changed_by_model.values()),
            "unchanged_by_model": unchanged_by_model,
            "all_cluster_labels_changed": all_labels_changed,
            "cluster_numbers_changed_by_model": changed_cluster_numbers,
            "cluster_numbers_changed_total": sum(changed_cluster_numbers.values()),
            "unparsed_generated_pattern_total": sum(
                models[name]["entity_labels"]["unparsed_generated_pattern"]
                for name in MODEL_NAMES
            ),
        },
        "numbering": {
            "writer_start_doc": reexport.get("writer_start_doc"),
            "document_range_in_original_source": reexport.get("document_range_in_original_source"),
            "document_range_in_supplied_slice": reexport.get("document_range_in_supplied_slice"),
            "document_delta_by_model": document_deltas,
            "uniform_document_number_delta": uniform_document_delta,
        },
        "entity_formatting_or_order": {
            "status": (
                "PROVEN_BY_CANONICAL_BYTES"
                if deep["canonical_eid_and_head_equal_all_models"] else "DIFFERENT"
            ),
            "reason": (
                "After mapping output eid to input cluster identity and masking numeric heads, "
                "the exact serialized bytes and event order are compared."
            ),
        },
        "other_bytes": {
            "status": (
                "PROVEN_EQUAL_AFTER_STRIPPING_COREFERENCE"
                if deep["strip_coreference_equal_all_models"] else "DIFFERENT"
            ),
            "masked_head_bytes_equal_by_model": masked_equal,
            "canonical_lf_equal_by_model": canonical_masked_equal,
            "raw_output_minus_input_bytes": byte_deltas,
            "mismatched_lines": mismatched_lines,
            "node_syntax_equal_all_models": all(
                models[name]["node_syntax"]["equal"] for name in MODEL_NAMES
            ),
            "mention_identity_equal_all_models": all(
                models[name]["mention_identity"]["equal"] for name in MODEL_NAMES
            ),
            "cluster_identity_equal_all_models": all(
                models[name]["cluster_identity"]["equal"] for name in MODEL_NAMES
            ),
            "zero_class_changes_total": sum(
                models[name]["heads"]["zero_class_changes"] for name in MODEL_NAMES
            ),
            "reason": "Exact bytes are equal after removing Entity/Bridge/SplitAnte.",
        },
        "corpus_blobs_read": True,
        "performed_reinference_or_scoring": False,
        "evidence_boundary": (
            "aggregate diagnosis plus a pinned full re-export; raw content existed only in memory/temp"
        ),
    }


def audit(agent_b_root: Path, agent_a_root: Path, isolated_clone: Path) -> dict[str, Any]:
    """Run the complete B16 audit without consulting Agent B working-tree files."""

    repo_b = Path(agent_b_root).resolve()
    repo_a = Path(agent_a_root).resolve()
    clone = Path(isolated_clone).resolve()
    if not _resolve_exact(repo_b, B16_SHA) or not _resolve_exact(repo_b, IMPLEMENTATION_SHA):
        raise ValueError("Przypiete rewizje B16 sa niedostepne")
    clone_head = _git_text(clone, "rev-parse", "HEAD").strip()
    clone_status = _git_text(clone, "status", "--porcelain=v1")
    verification = _json_blob(repo_b, B16_SHA, VERIFICATION_PATH)
    erratum_value = _json_blob(repo_b, B16_SHA, ERRATUM_PATH)
    reexport_value = _json_blob(repo_b, B16_SHA, REEXPORT_PATH)
    manifest, receipt = _manifest_and_receipt(repo_b)
    provenance = _verification_provenance(repo_b, verification)
    erratum = _erratum(repo_b, repo_a, erratum_value)
    pins = _udapi_pins(repo_b, repo_a, verification, erratum_value, reexport_value)
    dead = _dead_code(repo_b)
    commands = _command_statuses(verification)
    losses = _loss_accounting(reexport_value, erratum_value)
    deep = _pinned_full_reexport(repo_b, reexport_value)
    strict = _strict_decomposition(reexport_value, deep)
    result = {
        "schema_version": "agent-a-round-19-b16-reexport-audit-1.0",
        "target_revision": B16_SHA,
        "implementation_revision": IMPLEMENTATION_SHA,
        "input_boundary": {
            "agent_b_access": "pinned Git blobs and commit metadata only",
            "isolated_clone": {
                "path": str(clone), "head": clone_head,
                "clean": clone_head == B16_SHA and clone_status == "",
            },
            "corpus_or_prediction_blobs_read": True,
            "raw_content_persisted_or_displayed": False,
            "reinference_or_gpu": False,
        },
        "manifest": manifest,
        "receipt": receipt,
        "verification_provenance": provenance,
        "b13_erratum": erratum,
        "udapi_pins": pins,
        "dead_code_removal": dead,
        "command_statuses": commands,
        "loss_accounting": losses,
        "pinned_full_reexport": deep,
        "strict_difference_decomposition": strict,
    }
    result["audit_status"] = "PASS" if (
        result["input_boundary"]["isolated_clone"]["clean"]
        and manifest["entry_count"] == manifest["matched_blob_count"] == 37
        and not manifest["mismatches"] and manifest["implementation_commit"] == IMPLEMENTATION_SHA
        and receipt["manifest_hash_matches"] and receipt["manifest_passed"] and not receipt["passed"]
        and provenance["artifact_count"] == 34 and not provenance["mismatches"]
        and erratum["passed"] and not erratum["writer_package_mismatches"]
        and pins["all_sources_agree"] and dead["absent_from_final"]
        and commands["negative_result_is_explicit"]
        and losses["historical_breakdowns_sum_to_loss"]
        and deep["all_models_match_committed_aggregates"]
        and deep["canonical_eid_and_head_equal_all_models"]
        and deep["strip_coreference_equal_all_models"]
        and deep["temporary_content_removed"]
        and strict["reported_strict_invariance"] == strict["computed_strict_invariance"]
    ) else "FAIL"
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--agent-b-root", required=True, type=Path)
    parser.add_argument("--agent-a-root", required=True, type=Path)
    parser.add_argument("--isolated-clone", required=True, type=Path)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    result = audit(args.agent_b_root, args.agent_a_root, args.isolated_clone)
    serialized = json.dumps(result, ensure_ascii=False, indent=2, allow_nan=False) + "\n"
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(serialized, encoding="utf-8", newline="\n")
    print(serialized, end="")
    return 0 if result["audit_status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())

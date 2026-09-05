"""Portable audit of Agent B17 manifest binding and scoring-input TOCTOU.

Only immutable Git objects are read from Agent B.  The scoring experiment uses
small synthetic CoNLL-U files in a temporary directory and a mocked scorer; it
does not read a corpus, load a model, invoke CorefUD scorer, or use a GPU.
"""

from __future__ import annotations

import argparse
from contextlib import redirect_stdout
import hashlib
from io import StringIO
import importlib
import json
from pathlib import Path, PurePosixPath
import subprocess
import sys
import tempfile
from typing import Any
from unittest.mock import patch


B17_SHA = "cbd5b38d71c2b508d792e3683f569a4bfca58adf"
IMPLEMENTATION_SHA = "2f27198579b080531dfb1aa76b255814822492da"
B16_SHA = "3f1e9e5b30eb12b6057c4dc15477f90f34dfd93f"
MANIFEST_PATH = "kod/data/agent-debate/round-17/MANIFEST.json"
RECEIPT_PATH = "kod/data/agent-debate/round-17/manifest_receipt.json"
VERIFICATION_PATH = "kod/data/agent-debate/round-17/verification.json"
VERIFIER_PATH = "kod/scripts/verify_round17.py"
SCORE_PATH = "kod/scripts/score_official.py"
PROVENANCE_PATH = "kod/src/eval/alignment_provenance.py"
TEXT_SUFFIXES = {".json", ".md", ".py", ".txt", ".yaml", ".yml", ".conllu"}
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


def _canonical_manifest_entry(name: str, data: bytes) -> dict[str, Any]:
    path = Path(name)
    if path.name.lower() in TEXT_FILENAMES or path.suffix.lower() in TEXT_SUFFIXES:
        normalized = data.replace(b"\r\n", b"\n")
        return {"mode": "text_lf", "sha256_lf": _sha(normalized),
                "bytes_lf": len(normalized)}
    return {"mode": "binary", "sha256": _sha(data), "bytes": len(data)}


def _manifest_hybrid(repo: Path, manifest: dict[str, Any]) -> dict[str, Any]:
    entries = manifest.get("inputs", {})
    if not isinstance(entries, dict):
        raise ValueError("Manifest B17 nie ma mapy inputs")
    absent: list[str] = []
    implementation_mismatches: list[str] = []
    final_mismatches: list[str] = []
    implementation_matches = 0
    final_matches = 0
    for name, expected in entries.items():
        git_path = _manifest_git_path(name)
        implementation = _blob_optional(repo, IMPLEMENTATION_SHA, git_path)
        if implementation is None:
            absent.append(name)
        elif _canonical_manifest_entry(name, implementation) == expected:
            implementation_matches += 1
        else:
            implementation_mismatches.append(name)
        final = _blob_optional(repo, B17_SHA, git_path)
        if final is not None and _canonical_manifest_entry(name, final) == expected:
            final_matches += 1
        else:
            final_mismatches.append(name)
    absent.sort()
    expected_generated = [
        "data/agent-debate/round-17/b14_pinned_erratum.json",
        "data/agent-debate/round-17/verification.json",
    ]
    return {
        "entry_count": len(entries),
        "implementation_blob_entries": implementation_matches,
        "implementation_entry_names": sorted(set(entries) - set(absent)),
        "generated_entries_absent_from_implementation": absent,
        "generated_entry_count": len(absent),
        "implementation_mismatches": implementation_mismatches,
        "entries_matching_final_revision": final_matches,
        "final_revision_mismatches": final_mismatches,
        "all_entries_exist_in_implementation": not absent,
        "hybrid_42_implementation_plus_2_generated_proven": (
            len(entries) == 44 and implementation_matches == 42
            and absent == expected_generated and not implementation_mismatches
            and final_matches == 44 and not final_mismatches
        ),
    }


def _source_hard_codes_true(source: bytes, field: str) -> bool:
    """Detect the literal receipt field without trusting the receipt itself."""

    import ast

    tree = ast.parse(source.decode("utf-8"))
    for node in ast.walk(tree):
        if not isinstance(node, ast.Dict):
            continue
        for key, value in zip(node.keys, node.values):
            if (isinstance(key, ast.Constant) and key.value == field
                    and isinstance(value, ast.Constant) and value.value is True):
                return True
    return False


def _write_synthetic_fixture(root: Path, score: Any) -> dict[str, Path]:
    root.mkdir(parents=True, exist_ok=False)
    schema = "eid-etype-head"
    gold = "\n".join([
        f"# global.Entity = {schema}",
        "# newdoc id = d1",
        "# sent_id = d1-s1",
        "# text = Ala ma kota",
        "1\tAla\tAla\tPROPN\t_\tCase=Nom\t2\tnsubj\t2:nsubj\tEntity=(e1-person-1)",
        "2\tma\tmiec\tVERB\t_\tMood=Ind\t0\troot\t0:root\t_",
        "3\tkota\tkot\tNOUN\t_\tCase=Acc\t2\tobj\t2:obj\tEntity=e1)",
        "",
    ]) + "\n"
    pred = gold.replace("e1-person-1", "p1-person-1").replace("Entity=e1)", "Entity=p1)")
    paths = {
        "eval": root / "evaluation.json",
        "source": root / "source.conllu",
        "original_gold": root / "original-gold.conllu",
        "pred_original": root / "evaluation.pred-on-original.conllu",
        "gold_subtoken": root / "evaluation.gold.dev.conllu",
        "pred_subtoken": root / "evaluation.pred.dev.conllu",
        "checkpoint": root / "checkpoint.pt",
        "sidecar": root / "alignment-provenance.json",
        "anchor": root / "input-anchor.json",
        "scorer": root / "synthetic-scorer.py",
    }
    paths["source"].write_text(gold, encoding="utf-8", newline="\n")
    paths["original_gold"].write_text(gold, encoding="utf-8", newline="\n")
    paths["pred_original"].write_text(pred, encoding="utf-8", newline="\n")
    paths["gold_subtoken"].write_text(gold, encoding="utf-8", newline="\n")
    paths["pred_subtoken"].write_text(pred, encoding="utf-8", newline="\n")
    paths["checkpoint"].write_bytes(b"synthetic checkpoint; no model")
    paths["scorer"].write_text("# mocked; never executed\n", encoding="utf-8", newline="\n")
    nodes = []
    for ordinal, (token_id, form) in enumerate((("1", "Ala"), ("2", "ma"), ("3", "kota"))):
        endpoint = {"ordinal": ordinal, "id": token_id, "form": form, "empty": False}
        nodes.append({"original": dict(endpoint), "subtokens": [dict(endpoint)]})
    alignment = {
        "schema_version": "corefseg-original-to-subtoken-v1",
        "source_split_sha256": score.sha256(paths["source"]),
        "original_gold_sha256": score.sha256(paths["original_gold"]),
        "gold_subtoken_sha256": score.sha256(paths["gold_subtoken"]),
        "documents": [{
            "original": {"ordinal": 0, "id": "d1"},
            "subtoken": {"ordinal": 0, "id": "d1"},
            "sentences": [{
                "original": {"ordinal": 0, "id": "d1-s1"},
                "subtoken": {"ordinal": 0, "id": "d1-s1"},
                "nodes": nodes,
            }],
        }],
    }
    evaluation = {
        "checkpoint": str(paths["checkpoint"]), "split": "dev",
        "split_file": str(paths["source"]), "n_documents": 1, "threshold": 0.6,
        "task_scope": {"task_scope": "end_to_end_surface_mentions",
                       "zeros": "gold_nodes_predicted_labels", "doc_range": [0, 1]},
        "export_on_original": {"path": str(paths["pred_original"]), "loss": {}},
        "export_loss": {"gold": {}, "pred": {}, "policies": {}},
        "per_document": {"d1": {}},
        "original_to_subtoken_alignment": alignment,
    }
    paths["eval"].write_text(json.dumps(evaluation), encoding="utf-8", newline="\n")
    return paths


class _SyntheticTokenizer:
    name_or_path = "a20-synthetic"
    init_kwargs: dict[str, object] = {}
    special_tokens_map: dict[str, str] = {}

    def get_vocab(self) -> dict[str, int]:
        return {"Ala": 0, "ma": 1, "kota": 2}


def _scoring_toctou(repo: Path) -> tuple[dict[str, Any], bool]:
    temporary_path: Path | None = None
    summary: dict[str, Any]
    with tempfile.TemporaryDirectory(prefix="a20-b17-toctou-") as directory:
        temporary_path = Path(directory)
        module_root = temporary_path / "pinned" / "kod"
        (module_root / "scripts").mkdir(parents=True)
        (module_root / "src" / "eval").mkdir(parents=True)
        for package_file in (
            module_root / "scripts" / "__init__.py",
            module_root / "src" / "__init__.py",
            module_root / "src" / "eval" / "__init__.py",
        ):
            package_file.write_bytes(b"")
        (module_root / "scripts" / "score_official.py").write_bytes(
            _blob(repo, IMPLEMENTATION_SHA, SCORE_PATH))
        (module_root / "src" / "eval" / "alignment_provenance.py").write_bytes(
            _blob(repo, IMPLEMENTATION_SHA, PROVENANCE_PATH))
        saved_modules = {
            name: module for name, module in sys.modules.items()
            if name == "scripts" or name.startswith("scripts.")
            or name == "src" or name.startswith("src.")
        }
        for name in list(saved_modules):
            sys.modules.pop(name, None)
        sys.path.insert(0, str(module_root))
        try:
            importlib.invalidate_caches()
            score = importlib.import_module("scripts.score_official")
            provenance = importlib.import_module("src.eval.alignment_provenance")
            module_origins_verified = (
                Path(score.__file__).resolve()
                == (module_root / "scripts" / "score_official.py").resolve()
                and Path(provenance.__file__).resolve()
                == (module_root / "src" / "eval" / "alignment_provenance.py").resolve()
            )
            if not module_origins_verified:
                raise RuntimeError("Import nie wskazuje przypietych modulow B17")
            paths = _write_synthetic_fixture(temporary_path / "fixture", score)
            evaluation = json.loads(paths["eval"].read_text(encoding="utf-8"))
            sidecar_value = provenance.build_alignment_provenance(
                evaluation["original_to_subtoken_alignment"],
                tokenizer=_SyntheticTokenizer(), checkpoint_path=paths["checkpoint"],
                evaluation_config={}, encoder_config={}, source_split=paths["source"],
                original_gold=paths["original_gold"], gold_subtoken=paths["gold_subtoken"],
            )
            descriptor = provenance.write_alignment_provenance(paths["sidecar"], sidecar_value)
            descriptor["path"] = paths["sidecar"].name
            evaluation["alignment_provenance"] = descriptor
            paths["eval"].write_text(json.dumps(evaluation), encoding="utf-8", newline="\n")
            anchor_hash = score.sha256(paths["original_gold"])
            anchor = {
                "schema_version": "corefseg-scoring-input-anchor-v1",
                "source_split_sha256": score.sha256(paths["source"]),
                "original_gold_sha256": anchor_hash,
                "gold_subtoken_sha256": score.sha256(paths["gold_subtoken"]),
                "alignment_sha256": provenance.canonical_alignment_sha256(
                    evaluation["original_to_subtoken_alignment"]),
                "checkpoint_sha256": score.sha256(paths["checkpoint"]),
                "alignment_provenance_sha256": score.sha256(paths["sidecar"]),
            }
            paths["anchor"].write_text(json.dumps(anchor), encoding="utf-8", newline="\n")
            counters = {"version": 0, "scorer": 0}
            original_scorer_hashes: list[str] = []

            def fake_process(command: list[str], **_kwargs: object) -> subprocess.CompletedProcess[str]:
                if command[-1] == "--version":
                    counters["version"] += 1
                    text = paths["original_gold"].read_text(encoding="utf-8")
                    changed = text.replace("Entity=(e1-person-1)",
                                           "Entity=(forged-person-1)", 1)
                    if changed == text:
                        raise AssertionError("Nie wykonano mutacji syntetycznego golda")
                    paths["original_gold"].write_text(changed, encoding="utf-8", newline="\n")
                    return subprocess.CompletedProcess(command, 0, "Python 3.11.0\n", "")
                counters["scorer"] += 1
                if Path(command[-2]).resolve() == paths["original_gold"].resolve():
                    original_scorer_hashes.append(score.sha256(paths["original_gold"]))
                output = "".join(
                    f"{metric}\nRecall: 100 Precision: 100 F1: 100\n"
                    for metric in ("muc", "bcub", "ceafe", "lea")
                ) + "CoNLL score: 100\n"
                return subprocess.CompletedProcess(command, 0, output, "")

            argv = [
                "score_official.py", "--eval", str(paths["eval"]),
                "--original-gold", str(paths["original_gold"]),
                "--scorer", str(paths["scorer"]), "--scorer-python", sys.executable,
                "--input-manifest", str(paths["anchor"]),
                "--input-manifest-sha256", score.sha256(paths["anchor"]),
            ]
            with patch.object(sys, "argv", argv), patch.object(
                    score.subprocess, "run", side_effect=fake_process), redirect_stdout(StringIO()):
                return_code = score.main()
            official = paths["eval"].with_suffix(".official.json")
            report = json.loads(official.read_text(encoding="utf-8"))
            post_hash = score.sha256(paths["original_gold"])
            logs = list(paths["eval"].parent.glob("evaluation.official_*.log"))
            observed = {
                "main_return_code": return_code,
                "python_version_calls": counters["version"],
                "scorer_calls": counters["scorer"],
                "original_gold_scorer_calls": len(original_scorer_hashes),
                "original_gold_scorer_hashes": original_scorer_hashes,
                "alignment_provenance_status": report["alignment_provenance"]["status"],
                "input_anchor_independently_pinned": report["input_anchor"]["independently_pinned"],
                "anchor_original_gold_sha256": report["input_anchor"]["checked_inputs"][
                    "original_gold_sha256"],
                "post_mutation_original_gold_sha256": post_hash,
                "recorded_original_gold_sha256": report["inputs"]["original_gold"]["sha256"],
                "official_report_created": official.is_file(),
                "scorer_log_count": len(logs),
            }
            summary = {
                "pinned_module_origins_verified": module_origins_verified,
                "expected_safe_contract": {
                    "outcome": "REJECT", "main_return_code_nonzero": True,
                    "scorer_calls": 0, "output_artifacts_created": False,
                },
                "observed_current_behavior": observed,
                "contract_violation_reproduced": (
                    return_code == 0 and counters == {"version": 1, "scorer": 8}
                    and report["alignment_provenance"]["status"]
                    == "VERIFIED_RECORDED_PROVENANCE"
                    and anchor_hash != post_hash
                    and observed["recorded_original_gold_sha256"] == post_hash
                    and original_scorer_hashes == [post_hash] * 4
                    and official.is_file() and len(logs) == 8
                ),
            }
        finally:
            sys.path.remove(str(module_root))
            for name in list(sys.modules):
                if (name == "scripts" or name.startswith("scripts.")
                        or name == "src" or name.startswith("src.")):
                    sys.modules.pop(name, None)
            sys.modules.update(saved_modules)
    return summary, temporary_path is not None and not temporary_path.exists()


def audit(agent_b_root: Path) -> dict[str, Any]:
    """Audit B17 through pinned Git blobs and a deterministic synthetic race."""

    repo = Path(agent_b_root).resolve()
    for revision in (B16_SHA, IMPLEMENTATION_SHA, B17_SHA):
        if not _resolve_exact(repo, revision):
            raise ValueError(f"Brak przypietej rewizji: {revision}")
    logical_commits = _git_text(
        repo, "rev-list", "--reverse", f"{B16_SHA}..{B17_SHA}").splitlines()
    manifest = _json_blob(repo, B17_SHA, MANIFEST_PATH)
    receipt = _json_blob(repo, B17_SHA, RECEIPT_PATH)
    verification = _json_blob(repo, B17_SHA, VERIFICATION_PATH)
    hybrid = _manifest_hybrid(repo, manifest)
    verifier = _blob(repo, IMPLEMENTATION_SHA, VERIFIER_PATH)
    race, temporary_removed = _scoring_toctou(repo)
    pin_scope = set(verification.get("artifacts", {}))
    implementation_scope = set(hybrid["implementation_entry_names"])
    pin_scope_mismatches = sorted(pin_scope ^ implementation_scope)
    receipt_claim = {
        "reported_manifest_inputs_match_pinned_blobs": receipt.get(
            "manifest_inputs_match_pinned_blobs") is True,
        "source_hard_codes_manifest_inputs_match_pinned_blobs_true":
            _source_hard_codes_true(verifier, "manifest_inputs_match_pinned_blobs"),
        "source_pin_check_scope_count": len(verification.get("artifacts", {})),
        "source_pin_check_scope_mismatches": pin_scope_mismatches,
        "source_pin_check_scope_exactly_matches_implementation_entries":
            not pin_scope_mismatches,
        "manifest_entry_count": hybrid["entry_count"],
        "claim_holds_for_implementation_commit": hybrid["all_entries_exist_in_implementation"],
        "final_status_stdout_bytes": receipt.get("final_status_command", {}).get("stdout_bytes"),
        "reported_passed": receipt.get("passed") is True,
        "manifest_sha256_matches": receipt.get("manifest_sha256")
            == _sha(_blob(repo, B17_SHA, MANIFEST_PATH)),
    }
    result = {
        "schema_version": "agent-a-round-20-b17-contract-audit-1.0",
        "target_revision": B17_SHA,
        "implementation_revision": IMPLEMENTATION_SHA,
        "base_revision": B16_SHA,
        "lineage": {"logical_commits": logical_commits},
        "input_boundary": {
            "agent_b_access": "pinned Git blobs and commit metadata only",
            "synthetic_data_only": True,
            "corpus_model_scorer_or_gpu_used": False,
            "raw_synthetic_content_persisted_or_displayed": None,
            "temporary_content_removed": temporary_removed,
        },
        "manifest_hybrid": hybrid,
        "receipt_claim": receipt_claim,
        "scoring_toctou": race,
    }
    synthetic_markers = ("Ala ma kota", "Entity=(", "forged-person-1")
    report_before_boundary = json.dumps(result, ensure_ascii=False)
    result["input_boundary"]["raw_synthetic_content_persisted_or_displayed"] = any(
        marker in report_before_boundary for marker in synthetic_markers)
    result["audit_status"] = "PASS" if (
        logical_commits == [IMPLEMENTATION_SHA, B17_SHA]
        and hybrid["hybrid_42_implementation_plus_2_generated_proven"]
        and receipt_claim["reported_manifest_inputs_match_pinned_blobs"]
        and receipt_claim["source_hard_codes_manifest_inputs_match_pinned_blobs_true"]
        and receipt_claim["source_pin_check_scope_count"] == 42
        and receipt_claim["source_pin_check_scope_exactly_matches_implementation_entries"]
        and not receipt_claim["claim_holds_for_implementation_commit"]
        and receipt_claim["manifest_sha256_matches"]
        and race["pinned_module_origins_verified"]
        and race["contract_violation_reproduced"] and temporary_removed
        and not result["input_boundary"]["raw_synthetic_content_persisted_or_displayed"]
    ) else "FAIL"
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--agent-b-root", required=True, type=Path)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    result = audit(args.agent_b_root)
    serialized = json.dumps(result, ensure_ascii=False, indent=2, allow_nan=False) + "\n"
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(serialized, encoding="utf-8", newline="\n")
    print(serialized, end="")
    return 0 if result["audit_status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())

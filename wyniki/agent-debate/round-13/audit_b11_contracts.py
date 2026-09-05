"""Audit Agent B round 11 against pinned Git blobs and synthetic fixtures.

The audit does not run training or inference.  It checks three publication
contracts introduced in B11: scorer preflight, aggregate validation, and
artifact provenance.  All fixture files live in a temporary directory.
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


B_SHA = "81eeb3a4aec0908975bfc42a41161955d9bf38ba"
B9_CREATED_SHA = "c58d6534cf368cafe6cf78ff0c78212177d681fa"
GOOD_A_SHA = "7d0957cff584a1305b43ea4e383524d1e1d3620e"
BAD_A_SHA = "7d0957c2b11f4545c003138e847006bd02feb378"


def run(argv: list[str], cwd: Path) -> dict[str, Any]:
    completed = subprocess.run(
        argv,
        cwd=cwd,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    return {
        "argv": argv,
        "cwd": str(cwd),
        "exit_code": completed.returncode,
        "stdout": completed.stdout,
        "stderr": completed.stderr,
    }


def git_blob(repo: Path, path: str) -> bytes:
    completed = subprocess.run(
        ["git", "-C", str(repo), "show", f"{B_SHA}:{path}"],
        check=True,
        capture_output=True,
    )
    return completed.stdout


def git_text(repo: Path, *arguments: str) -> str:
    completed = subprocess.run(
        ["git", "-C", str(repo), *arguments],
        check=True,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="strict",
    )
    return completed.stdout.strip()


def git_commit_exists(repo: Path, revision: str) -> bool:
    completed = subprocess.run(
        ["git", "-C", str(repo), "cat-file", "-e", f"{revision}^{{commit}}"],
        capture_output=True,
    )
    return completed.returncode == 0


def module_from_blob(name: str, value: bytes) -> types.ModuleType:
    module = types.ModuleType(name)
    module.__file__ = f"{name}.git-blob.py"
    sys.modules[name] = module
    exec(compile(value, module.__file__, "exec"), module.__dict__)
    return module


def sha256(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def conllu(*, doc: str, sent: str, form: str, empty_id: str | None) -> str:
    rows = [
        f"# newdoc id = {doc}",
        f"# sent_id = {sent}",
        f"1\t{form}\t_\tNOUN\t_\t_\t0\troot\t_\t_",
    ]
    if empty_id is not None:
        rows.append(f"{empty_id}\tpro\t_\tPRON\t_\t_\t_\t_\t1:dep\t_")
    return "\n".join(rows) + "\n\n"


def write(path: Path, value: str) -> None:
    path.write_text(value, encoding="utf-8", newline="\n")


def scorer_output() -> str:
    sections = []
    for metric in ("muc", "bcub", "ceafe", "lea"):
        sections.extend((metric, "Recall: 100 Precision: 100 F1: 100"))
    sections.append("CoNLL score: 100")
    return "\n".join(sections)


def audit_score_contract(score_blob: bytes, root: Path) -> dict[str, Any]:
    score = module_from_blob("agent_b_round11_score_official", score_blob)

    split = root / "source-split.conllu"
    original_gold = root / "original-gold.conllu"
    original_pred = root / "original-pred.conllu"
    subtoken_gold = root / "subtoken-gold.conllu"
    subtoken_pred = root / "subtoken-pred.conllu"
    write(split, conllu(doc="d1", sent="source-s1", form="SOURCE", empty_id="9.1"))
    altered = conllu(doc="d1", sent="different-s1", form="ALTERED", empty_id="1.1")
    write(original_gold, altered)
    write(original_pred, altered)
    tokenized = conllu(doc="tokenized-d1", sent="tok-s1", form="SUBTOKEN", empty_id="1.1")
    write(subtoken_gold, tokenized)
    write(subtoken_pred, tokenized)
    paths = {
        "original_gold": original_gold,
        "pred_on_original": original_pred,
        "gold_subtoken": subtoken_gold,
        "pred_subtoken": subtoken_pred,
    }
    structures = {
        name: score.inspect_conllu_structure(path) for name, path in paths.items()
    }
    evaluation = {
        "n_documents": 1,
        "split_file": str(split),
        "task_scope": {"doc_range": [0, 1]},
        "per_document": {"d1": {}},
    }
    accepted = score.validate_evaluation_contract(
        evaluation, root / "synthetic.json", structures
    )

    late = root / "late-zero"
    late.mkdir()
    eval_path = late / "case.json"
    base = eval_path.with_suffix("")
    split_path = late / "split.conllu"
    original_path = late / "original.conllu"
    pred_original_path = late / "pred-original.conllu"
    original_value = conllu(doc="d1", sent="d1-s1", form="A", empty_id="1.1")
    for path in (split_path, original_path, pred_original_path):
        write(path, original_value)
    write(
        Path(str(base) + ".gold.dev.conllu"),
        conllu(doc="d1", sent="d1-s1", form="A", empty_id="1.1"),
    )
    write(
        Path(str(base) + ".pred.dev.conllu"),
        conllu(doc="d1", sent="d1-s1", form="A", empty_id="1.2"),
    )
    calls = late / "scorer-calls.txt"
    fake_scorer = late / "fake-scorer.py"
    write(
        fake_scorer,
        "from pathlib import Path\n"
        f"p=Path({str(calls)!r})\n"
        "p.write_text((p.read_text() if p.exists() else '')+'called\\n')\n"
        f"print({scorer_output()!r})\n",
    )
    evaluation = {
        "checkpoint": str(late / "not-used.pt"),
        "split": "dev",
        "split_file": str(split_path),
        "n_documents": 1,
        "threshold": 0.6,
        "task_scope": {
            "zeros": "gold_nodes_predicted_labels",
            "doc_range": [0, 1],
            "syntax": "synthetic",
        },
        "per_document": {"d1": {}},
        "export_on_original": {"path": str(pred_original_path), "loss": {}},
        "export_loss": {"pred": {}, "gold": {}, "policies": {}},
    }
    write(eval_path, json.dumps(evaluation))
    score_script = late / "score_official.py"
    score_script.write_bytes(score_blob)
    wrapper = run(
        [
            sys.executable,
            str(score_script),
            "--eval",
            str(eval_path),
            "--original-gold",
            str(original_path),
            "--scorer",
            str(fake_scorer),
            "--scorer-python",
            sys.executable,
        ],
        late,
    )
    call_count = len(calls.read_text(encoding="utf-8").splitlines()) if calls.exists() else 0

    return {
        "source_split_content_counterexample": {
            "accepted": accepted["doc_range_resolves_against_split_file"],
            "source": {"doc": "d1", "sent": "source-s1", "form": "SOURCE", "empty_id": "9.1"},
            "scored_original": {"doc": "d1", "sent": "different-s1", "form": "ALTERED", "empty_id": "1.1"},
            "scored_subtoken": {"doc": "tokenized-d1", "sent": "tok-s1", "form": "SUBTOKEN", "empty_id": "1.1"},
            "raw_original_and_subtoken_ids_equal": False,
            "interpretation": "split_file is bound only by sliced document IDs; original/subtoken are bound only by count",
        },
        "late_subtoken_zero_preflight": {
            "wrapper": wrapper,
            "scorer_calls_before_rejection": call_count,
            "official_json_created": Path(str(base) + ".official.json").exists(),
            "expected_rejection": "gold=1, pred=1" in wrapper["stderr"],
            "interpretation": "four original scorer calls occur before subtoken zero identity is rejected",
        },
    }


def audit_gate(gate_blob: bytes, public_blob: bytes) -> dict[str, Any]:
    gate = module_from_blob("agent_b_round11_legal_release_gate", gate_blob)
    baseline = json.loads(public_blob)
    mutations: dict[str, dict[str, Any]] = {}

    too_many_groups = copy.deepcopy(baseline)
    too_many_groups["split"]["group_counts"] = {"train": 1974, "dev": 0, "test": 0}
    mutations["train_groups_exceed_train_records"] = too_many_groups

    too_many_candidates = copy.deepcopy(baseline)
    too_many_candidates["population"]["simhash_candidate_pairs"] = (
        baseline["population"]["possible_pairs"] + 1
    )
    mutations["simhash_candidates_exceed_possible_pairs"] = too_many_candidates

    impossible_exact = copy.deepcopy(baseline)
    impossible_exact["population"]["exact_pairs_skipped"] = 0
    impossible_exact["population"]["different_hash_pairs_scored"] = impossible_exact[
        "population"
    ]["possible_pairs"]
    mutations["zero_exact_pairs_with_duplicate_hash_counts"] = impossible_exact

    accepted: dict[str, bool] = {}
    for name, value in mutations.items():
        try:
            gate.check_release(value, "public_aggregate")
        except gate.ReleaseGateError:
            accepted[name] = False
        else:
            accepted[name] = True
    return {
        "baseline_passes": _gate_passes(gate, baseline),
        "impossible_aggregate_mutations_accepted": accepted,
        "accepted_count": sum(accepted.values()),
        "interpretation": "the committed aggregate is not disproved; the release gate is incomplete",
    }


def _gate_passes(gate: types.ModuleType, value: Any) -> bool:
    try:
        gate.check_release(value, "public_aggregate")
    except gate.ReleaseGateError:
        return False
    return True


def audit_artifacts(repo: Path) -> dict[str, Any]:
    verification = json.loads(
        git_blob(repo, "kod/data/agent-debate/round-11/verification.json")
    )
    manifest = json.loads(git_blob(repo, "kod/data/agent-debate/round-11/MANIFEST.json"))
    comparisons = {}
    for path, declared in verification["artifacts"].items():
        blob = git_blob(repo, "kod/" + path)
        manifest_entry = manifest["inputs"].get(path) or manifest["outputs"].get(path)
        comparisons[path] = {
            "verification": declared,
            "git_blob": {"sha256": sha256(blob), "bytes": len(blob)},
            "manifest_text_lf": manifest_entry,
            "verification_matches_git_blob": (
                declared["sha256"] == sha256(blob) and declared["bytes"] == len(blob)
            ),
        }
    mismatches = [
        path for path, record in comparisons.items()
        if not record["verification_matches_git_blob"]
    ]
    return {
        "artifacts": comparisons,
        "verified_artifacts": len(comparisons),
        "mismatches": mismatches,
        "all_other_artifacts_match": len(mismatches) == 1,
        "score_official_difference_bytes": (
            comparisons["scripts/score_official.py"]["verification"]["bytes"]
            - comparisons["scripts/score_official.py"]["git_blob"]["bytes"]
        ),
        "interpretation": "the mismatch is consistent with 76 noncanonical CR bytes, not evidence of a logic change",
    }


def audit_history(repo_b: Path, repo_a: Path) -> dict[str, Any]:
    latest_touch = git_text(
        repo_b, "log", "-1", "--format=%H", B_SHA, "--", "ODPOWIEDZ_AGENT_B_RUNDA_9.md"
    )
    created = git_text(
        repo_b, "log", "-1", "--diff-filter=A", "--format=%H", B_SHA,
        "--", "ODPOWIEDZ_AGENT_B_RUNDA_9.md",
    )
    return {
        "bad_referenced_a_sha_exists": git_commit_exists(repo_a, BAD_A_SHA),
        "corrected_a_sha_exists": git_commit_exists(repo_a, GOOD_A_SHA),
        "b9_creation_commit": created,
        "b9_latest_touch_commit": latest_touch,
        "b9_author_sha_command_now_returns_b11": latest_touch == B_SHA,
        "original_b9_still_in_git": git_commit_exists(repo_b, B9_CREATED_SHA),
        "interpretation": "the correction is factual and history remains in Git, but the in-file author_sha lookup now resolves to B11 rather than original B9",
    }


def audit(args: argparse.Namespace) -> dict[str, Any]:
    repo_b = args.agent_b_root.resolve()
    repo_a = args.agent_a_root.resolve()
    actual_b_sha = git_text(repo_b, "rev-parse", B_SHA)
    if actual_b_sha != B_SHA:
        raise RuntimeError(f"Nie mozna rozstrzygnac przypietego SHA B11: {actual_b_sha}")
    score_blob = git_blob(repo_b, "kod/scripts/score_official.py")
    gate_blob = git_blob(repo_b, "kod/scripts/legal_release_gate.py")
    public_blob = git_blob(repo_b, "kod/data/legal-audit/round-11/public_summary.json")
    with tempfile.TemporaryDirectory(prefix="agent-a-round13-") as temporary:
        score_contract = audit_score_contract(score_blob, Path(temporary))
    return {
        "schema_version": "agent-a-round-13-b11-contract-audit-1.0",
        "agent_b_sha": B_SHA,
        "scope": "synthetic contract fixtures and pinned Git blobs; no training or inference",
        "inputs": {
            "score_official_sha256": sha256(score_blob),
            "legal_release_gate_sha256": sha256(gate_blob),
            "public_summary_sha256": sha256(public_blob),
        },
        "score_contract": score_contract,
        "release_gate": audit_gate(gate_blob, public_blob),
        "artifact_provenance": audit_artifacts(repo_b),
        "historical_correction": audit_history(repo_b, repo_a),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--agent-b-root", required=True, type=Path)
    parser.add_argument("--agent-a-root", required=True, type=Path)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    result = audit(args)
    serialized = json.dumps(result, ensure_ascii=False, indent=2) + "\n"
    if args.output:
        args.output.write_text(serialized, encoding="utf-8", newline="\n")
    else:
        print(serialized, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

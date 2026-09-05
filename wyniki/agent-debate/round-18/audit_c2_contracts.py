"""Git-pinned, corpus-free audit of Reviewer C2's executable contracts.

Only pinned Git blobs and commit metadata are read from Agent B.  Executable
counterexamples use synthetic files or monkeypatched process boundaries.
"""

from __future__ import annotations

import argparse
from contextlib import redirect_stdout
from datetime import datetime
import hashlib
import importlib.util
from io import StringIO
import json
import math
from pathlib import Path
import subprocess
import sys
import tempfile
from typing import Any
from unittest.mock import patch


C2_SHA = "f8e877fe5449d2589aec5fbe1531a25ecbd1fdb4"
B15_SHA = "32a564cdc3c6b6301897df094ee062019b7b5705"
B15_IMPLEMENTATION_SHA = "20e05853bf85147466bf8c5874ba29f6bdb6bed4"
B14_SHA = "65bbd965d62d3f4d374b6b31754c0d898a493d59"
A14_SHA = "3e40fa5edae5364af58506b7704e5bba074d22c1"
AUDIT_PATH = "recenzje/skrypty/audyt_c02.py"
RESULT_PATH = "recenzje/wyniki/RECENZJA_C_02.json"
REVIEW_PATH = "recenzje/RECENZJA_C_02.md"
EXPECTED_CHANGED_PATHS = [
    "POSTEP.md",
    "recenzje/OS_CZASU.md",
    REVIEW_PATH,
    "recenzje/REJESTR_REKOMENDACJI.md",
    AUDIT_PATH,
    RESULT_PATH,
]


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
        stderr = result.stderr.decode("utf-8", errors="replace").strip()
        raise RuntimeError(f"Brak przypietego blobu {revision}:{path}: {stderr}")
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


def _commit(repo: Path, revision: str) -> dict[str, Any]:
    raw = _git_text(repo, "show", "-s", "--format=%H%x00%P%x00%aI%x00%cI", revision).strip()
    commit, parents, authored, committed = raw.split("\0")
    return {
        "commit": commit,
        "parents": parents.split() if parents else [],
        "authored_at": authored,
        "committed_at": committed,
    }


def _load_c2(source: bytes):
    with tempfile.TemporaryDirectory(prefix="a18-load-") as directory:
        path = Path(directory) / "audyt_c02.py"
        path.write_bytes(source)
        spec = importlib.util.spec_from_file_location("a18_pinned_audyt_c02", path)
        if spec is None or spec.loader is None:
            raise RuntimeError("Nie mozna zaladowac przypietego audyt_c02.py")
        module = importlib.util.module_from_spec(spec)
        sys.modules[spec.name] = module
        spec.loader.exec_module(module)
        return module


def _committed_artifacts(repo_b: Path, repo_a: Path) -> tuple[dict[str, Any], dict[str, Any]]:
    changed = [
        line.strip()
        for line in _git_text(
            repo_b, "diff-tree", "--no-commit-id", "--name-only", "-r",
            C2_SHA + "^", C2_SHA,
        ).splitlines()
        if line.strip()
    ]
    hashes: dict[str, dict[str, Any]] = {}
    missing: list[str] = []
    for path in changed:
        try:
            data = _blob(repo_b, C2_SHA, path)
        except RuntimeError:
            missing.append(path)
        else:
            hashes[path] = {"sha256": _sha(data), "bytes": len(data)}
    result = _json_blob(repo_b, C2_SHA, RESULT_PATH)
    pin_b = result.get("pins", {}).get("sha_b", {})
    pin_a = result.get("pins", {}).get("sha_a", {})
    exact = (
        changed == EXPECTED_CHANGED_PATHS
        and pin_b.get("status") == "PASS"
        and pin_b.get("resolved") == B14_SHA
        and _resolve_exact(repo_b, B14_SHA)
        and pin_a.get("status") == "PASS"
        and pin_a.get("resolved") == A14_SHA
        and _resolve_exact(repo_a, A14_SHA)
    )
    return ({
        "changed_paths": changed,
        "changed_path_count": len(changed),
        "expected_changed_paths": EXPECTED_CHANGED_PATHS,
        "missing_paths": missing,
        "blob_provenance": hashes,
        "result_schema": result.get("schema"),
        "result_status": result.get("status"),
        "recorded_sha_b": pin_b.get("resolved"),
        "recorded_sha_a": pin_a.get("resolved"),
        "recorded_pins_resolve_exactly": exact,
    }, result)


_SYNTHETIC_WRAPPER = b'''from pathlib import Path
import argparse
import sys
p = argparse.ArgumentParser()
p.add_argument("--eval")
p.add_argument("--original-gold")
p.add_argument("--scorer")
p.add_argument("--scorer-python")
a = p.parse_args()
if not Path(a.original_gold).is_file():
    print("missing synthetic original-gold in cwd", file=sys.stderr)
    raise SystemExit(4)
print("ValueError: Eval JSON jest rekordem legacy bez synthetic alignment", file=sys.stderr)
raise SystemExit(1)
'''


def _synthetic_blob(_repo: Path, _sha: str, path: str) -> bytes | None:
    if path.endswith("kod/scripts/score_official.py"):
        return _SYNTHETIC_WRAPPER
    if path.endswith("kod/src/eval/alignment.py"):
        return b"# synthetic alignment marker\n"
    if path.endswith((".json", ".pred.dev.conllu", ".gold.dev.conllu")):
        return b"synthetic record bytes\n"
    return None


def _legacy_contracts(module: Any, source_text: str) -> tuple[dict[str, Any], dict[str, Any]]:
    with tempfile.TemporaryDirectory(prefix="a18-legacy-") as directory:
        base = Path(directory)
        synthetic_repo = base / "repo-b"
        (synthetic_repo / "kod").mkdir(parents=True)
        with patch.object(module, "blob", _synthetic_blob):
            without_file = module.check_legacy_record(
                synthetic_repo, "f" * 40, base / "without"
            )
            original = synthetic_repo / "kod/runs/dev61_183_original.conllu"
            original.parent.mkdir(parents=True)
            original.write_bytes(b"synthetic original only\n")
            with_file = module.check_legacy_record(
                synthetic_repo, "f" * 40, base / "with"
            )

            def unexpected_run(argv: list[str], cwd: Path, env: dict | None = None):
                return {
                    "argv": list(map(str, argv)), "cwd": str(cwd), "exit": 127,
                    "seconds": 0.0, "stdout_tail": "", "stderr_tail": "synthetic unexpected command",
                }

            with patch.object(module, "run", unexpected_run):
                unexpected = module.check_legacy_record(
                    synthetic_repo, "f" * 40, base / "unexpected"
                )
    dependency = {
        "reproduced": (
            without_file["exit"] == 4
            and without_file["rejected_as_legacy"] is False
            and with_file["exit"] == 1
            and with_file["rejected_as_legacy"] is True
        ),
        "uses_repo_b_kod_as_cwd": 'kod = repo_b / "kod"' in source_text,
        "unextracted_relative_path": "runs/dev61_183_original.conllu",
        "without_file": {
            "status": without_file["status"], "exit": without_file["exit"],
            "rejected_as_legacy": without_file["rejected_as_legacy"],
        },
        "with_file": {
            "status": with_file["status"], "exit": with_file["exit"],
            "rejected_as_legacy": with_file["rejected_as_legacy"],
        },
        "fixture_scope": "synthetic paths and bytes only; no R7 or corpus blob was read",
    }
    predicate = {
        "missing_dependency_status": without_file["status"],
        "missing_dependency_rejected_as_legacy": without_file["rejected_as_legacy"],
        "unexpected_command_exit": unexpected["exit"],
        "unexpected_command_rejected_as_legacy": unexpected["rejected_as_legacy"],
        "unexpected_command_status": unexpected["status"],
        "has_effective_acceptance_predicate": not (
            without_file["status"] == "PASS" and not without_file["rejected_as_legacy"]
            and unexpected["status"] == "PASS" and unexpected["exit"] == 127
        ),
    }
    return dependency, predicate


def _main_status_aggregation(module: Any) -> dict[str, Any]:
    fail = {"status": "FAIL", "reason": "synthetic failure"}
    skipped = {"status": "SKIPPED", "reason": "synthetic missing dependency"}
    passed = {"status": "PASS"}
    with tempfile.TemporaryDirectory(prefix="a18-main-") as directory:
        root = Path(directory)
        repo_b = root / "repo-b"
        repo_a = root / "repo-a"
        repo_b.mkdir()
        repo_a.mkdir()
        output = root / "result.json"
        argv = [
            "audyt_c02.py", "--repo-b", str(repo_b), "--repo-a", str(repo_a),
            "--sha-b", "b" * 40, "--sha-a", "a" * 40, "--out", str(output),
        ]
        with (
            patch.object(module, "resolve_commit", return_value={"status": "PASS", "resolved": "synthetic"}),
            patch.object(module, "check_tree_gate", return_value=fail),
            patch.object(module, "check_manifest_gitignore", return_value=skipped),
            patch.object(module, "check_legacy_record", return_value=passed),
            patch.object(module, "check_b13_writer_provenance", return_value=passed),
            patch.object(module, "check_thesis", return_value=passed),
            patch.object(module, "check_movehead", return_value=passed),
            patch.object(sys, "argv", argv),
            redirect_stdout(StringIO()),
        ):
            exit_code = module.main()
        report = json.loads(output.read_text(encoding="utf-8"))
    statuses = [value["status"] for value in report["checks"].values()]
    return {
        "reproduced": exit_code == 0 and report["status"] == "OK" and "FAIL" in statuses and "SKIPPED" in statuses,
        "main_exit": exit_code,
        "report_status": report["status"],
        "child_statuses": statuses,
        "all_child_checks_pass": all(status == "PASS" for status in statuses),
    }


def _stats(values: list[float]) -> dict[str, float]:
    mean = sum(values) / len(values)
    sd = math.sqrt(sum((value - mean) ** 2 for value in values) / len(values))
    return {"mean": round(mean, 3), "sd_pop": round(sd, 3)}


def _movehead_claims(result: dict[str, Any]) -> dict[str, Any]:
    check = result["checks"]["movehead_erratum_via_pinned_a12"]
    scores = check["scores"]
    models = ("v2_seed42", "v2_seed1", "v2_seed2")
    before_values = [scores[f"{model}/before/head"] for model in models]
    after_values = [scores[f"{model}/after/head"] for model in models]
    before = _stats(before_values)
    after = _stats(after_values)
    invariant = all(
        scores[f"{model}/before/exact"] == scores[f"{model}/after/exact"]
        for model in (*models, "v1_seed42")
    )
    return {
        "source": RESULT_PATH + " at " + C2_SHA,
        "score_count": len(scores),
        "v2_head_before_values": before_values,
        "v2_head_after_values": after_values,
        "v2_head_before": before,
        "v2_head_after": after,
        "published_v2_head_before": check["v2_head_before"],
        "published_v2_head_after": check["v2_head_after"],
        "published_summary_matches_recalculation": (
            before == check["v2_head_before"] and after == check["v2_head_after"]
        ),
        "two_decimal_claim_matches": round(after["mean"], 2) == 54.50 and round(after["sd_pop"], 2) == 0.49,
        "all_exact_scores_invariant": invariant and check.get("exact_invariant") is True,
        "performed_reinference": False,
        "evidence_boundary": "arithmetic over the committed public C2 result only",
    }


def _chronology(repo_b: Path, result: dict[str, Any], review_text: str) -> dict[str, Any]:
    b14 = _commit(repo_b, B14_SHA)
    implementation = _commit(repo_b, B15_IMPLEMENTATION_SHA)
    b15 = _commit(repo_b, B15_SHA)
    c2 = _commit(repo_b, C2_SHA)
    created = datetime.fromisoformat(result["created_utc"])
    implementation_time = datetime.fromisoformat(implementation["committed_at"])
    b15_time = datetime.fromisoformat(b15["committed_at"])
    c2_time = datetime.fromisoformat(c2["committed_at"])
    claim_present = "A15 i B15 w toku, niecommitowane" in review_text
    return {
        "b14_commit": b14["commit"],
        "b15_implementation": implementation["commit"],
        "b15_final": b15["commit"],
        "c2_commit": c2["commit"],
        "c2_parent": c2["parents"][0] if len(c2["parents"]) == 1 else None,
        "report_created_utc": result["created_utc"],
        "report_created_before_b15_implementation": created < implementation_time,
        "b15_final_precedes_c2_commit": b15_time < c2_time,
        "c2_directly_descends_from_b15": c2["parents"] == [B15_SHA],
        "review_contains_in_progress_claim": claim_present,
        "review_snapshot_claim_is_historical": (
            claim_present and created < implementation_time and c2["parents"] == [B15_SHA]
        ),
        "narrowed_interpretation": (
            "The claim can describe the report-generation instant, but not the committed C2 snapshot: "
            "the published C2 commit directly follows final B15."
        ),
        "a15_state_claim": "NOT_PROVABLE_FROM_PINNED_C2_ARTIFACTS",
    }


def audit(agent_b_root: Path, agent_a_root: Path, isolated_clone: Path) -> dict[str, Any]:
    """Audit C2 from pinned objects and corpus-free executable fixtures."""

    repo_b = Path(agent_b_root).resolve()
    repo_a = Path(agent_a_root).resolve()
    clone = Path(isolated_clone).resolve()
    if not _resolve_exact(repo_b, C2_SHA):
        raise ValueError("Reviewer C2 commit is unavailable")
    clone_head = _git_text(clone, "rev-parse", "HEAD").strip()
    clone_status = _git_text(clone, "status", "--porcelain=v1")
    audit_source = _blob(repo_b, C2_SHA, AUDIT_PATH)
    review_text = _blob(repo_b, C2_SHA, REVIEW_PATH).decode("utf-8")
    artifacts, committed_result = _committed_artifacts(repo_b, repo_a)
    c2_module = _load_c2(audit_source)
    dependency, predicate = _legacy_contracts(c2_module, audit_source.decode("utf-8"))
    aggregation = _main_status_aggregation(c2_module)
    movehead = _movehead_claims(committed_result)
    chronology = _chronology(repo_b, committed_result, review_text)
    result = {
        "schema_version": "agent-a-round-18-reviewer-c2-contract-audit-1.0",
        "target_revision": C2_SHA,
        "input_boundary": {
            "agent_b_access": "pinned Git blobs and commit metadata only",
            "isolated_clone": {
                "path": str(clone), "head": clone_head,
                "clean": clone_head == C2_SHA and clone_status == "",
            },
            "corpus_blobs_read": False,
            "executable_fixtures": "synthetic or monkeypatched only",
        },
        "committed_artifacts": artifacts,
        "legacy_cwd_dependency": dependency,
        "legacy_acceptance_predicate": predicate,
        "main_status_aggregation": aggregation,
        "movehead_public_claims": movehead,
        "chronology": chronology,
    }
    result["audit_status"] = "PASS" if (
        result["input_boundary"]["isolated_clone"]["clean"]
        and artifacts["recorded_pins_resolve_exactly"]
        and dependency["reproduced"]
        and predicate["has_effective_acceptance_predicate"] is False
        and aggregation["reproduced"]
        and movehead["published_summary_matches_recalculation"]
        and chronology["review_snapshot_claim_is_historical"]
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

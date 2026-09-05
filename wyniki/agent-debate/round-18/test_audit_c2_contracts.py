"""Regression tests for the pinned Reviewer C2 contract audit."""

from __future__ import annotations

import argparse
import importlib.util
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


SCRIPT = Path(__file__).with_name("audit_c2_contracts.py")
SPEC = importlib.util.spec_from_file_location("audit_c2_contracts", SCRIPT)
if SPEC is None or SPEC.loader is None:
    raise RuntimeError(f"Nie mozna zaladowac {SCRIPT}")
AUDIT = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = AUDIT
SPEC.loader.exec_module(AUDIT)


class AuditC2ContractsTest(unittest.TestCase):
    result: dict

    @classmethod
    def setUpClass(cls) -> None:
        cls.result = AUDIT.audit(
            ARGS.agent_b_root, ARGS.agent_a_root, ARGS.isolated_clone
        )

    def test_target_snapshot_and_committed_artifacts_are_git_bound(self) -> None:
        boundary = self.result["input_boundary"]
        self.assertEqual(boundary["isolated_clone"]["head"], AUDIT.C2_SHA)
        self.assertTrue(boundary["isolated_clone"]["clean"])
        artifacts = self.result["committed_artifacts"]
        self.assertEqual(artifacts["changed_path_count"], 6)
        self.assertEqual(artifacts["missing_paths"], [])
        self.assertEqual(artifacts["result_schema"], "recenzja-c-02-audyt-1.0")
        self.assertEqual(artifacts["result_status"], "OK")
        self.assertTrue(artifacts["recorded_pins_resolve_exactly"])

    def test_legacy_check_depends_on_a_file_it_does_not_extract(self) -> None:
        proof = self.result["legacy_cwd_dependency"]
        self.assertTrue(proof["reproduced"])
        self.assertTrue(proof["uses_repo_b_kod_as_cwd"])
        self.assertEqual(
            proof["unextracted_relative_path"], "runs/dev61_183_original.conllu"
        )
        self.assertEqual(proof["without_file"]["exit"], 4)
        self.assertFalse(proof["without_file"]["rejected_as_legacy"])
        self.assertEqual(proof["with_file"]["exit"], 1)
        self.assertTrue(proof["with_file"]["rejected_as_legacy"])
        self.assertNotEqual(proof["without_file"], proof["with_file"])

    def test_legacy_check_labels_false_and_unexpected_results_pass(self) -> None:
        proof = self.result["legacy_acceptance_predicate"]
        self.assertEqual(proof["missing_dependency_status"], "PASS")
        self.assertFalse(proof["missing_dependency_rejected_as_legacy"])
        self.assertEqual(proof["unexpected_command_exit"], 127)
        self.assertFalse(proof["unexpected_command_rejected_as_legacy"])
        self.assertEqual(proof["unexpected_command_status"], "PASS")
        self.assertFalse(proof["has_effective_acceptance_predicate"])

    def test_main_can_publish_ok_when_child_checks_fail_or_skip(self) -> None:
        proof = self.result["main_status_aggregation"]
        self.assertTrue(proof["reproduced"])
        self.assertEqual(proof["main_exit"], 0)
        self.assertEqual(proof["report_status"], "OK")
        self.assertIn("FAIL", proof["child_statuses"])
        self.assertIn("SKIPPED", proof["child_statuses"])
        self.assertFalse(proof["all_child_checks_pass"])

    def test_movehead_claims_follow_committed_public_numbers(self) -> None:
        movehead = self.result["movehead_public_claims"]
        self.assertEqual(movehead["score_count"], 16)
        self.assertEqual(movehead["v2_head_before"], {"mean": 54.48, "sd_pop": 0.503})
        self.assertEqual(movehead["v2_head_after"], {"mean": 54.503, "sd_pop": 0.493})
        self.assertTrue(movehead["published_summary_matches_recalculation"])
        self.assertTrue(movehead["two_decimal_claim_matches"])
        self.assertTrue(movehead["all_exact_scores_invariant"])
        self.assertFalse(movehead["performed_reinference"])

    def test_chronology_narrows_snapshot_claim(self) -> None:
        chronology = self.result["chronology"]
        self.assertEqual(chronology["c2_parent"], AUDIT.B15_SHA)
        self.assertTrue(chronology["report_created_before_b15_implementation"])
        self.assertTrue(chronology["b15_final_precedes_c2_commit"])
        self.assertTrue(chronology["c2_directly_descends_from_b15"])
        self.assertTrue(chronology["review_snapshot_claim_is_historical"])
        self.assertEqual(
            chronology["a15_state_claim"], "NOT_PROVABLE_FROM_PINNED_C2_ARTIFACTS"
        )

    def test_cli_emits_valid_json(self) -> None:
        with tempfile.TemporaryDirectory(prefix="a18-cli-") as directory:
            output = Path(directory) / "audit.json"
            completed = subprocess.run(
                [
                    sys.executable,
                    "-B",
                    str(SCRIPT),
                    "--agent-b-root",
                    str(ARGS.agent_b_root),
                    "--agent-a-root",
                    str(ARGS.agent_a_root),
                    "--isolated-clone",
                    str(ARGS.isolated_clone),
                    "--output",
                    str(output),
                ],
                check=False,
                capture_output=True,
                text=True,
            )
            self.assertEqual(completed.returncode, 0, completed.stderr)
            stdout_result = json.loads(completed.stdout)
            file_result = json.loads(output.read_text(encoding="utf-8"))
            self.assertEqual(stdout_result, file_result)
            self.assertEqual(stdout_result["target_revision"], AUDIT.C2_SHA)
            self.assertEqual(stdout_result["audit_status"], "PASS")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--agent-b-root", required=True, type=Path)
    parser.add_argument("--agent-a-root", required=True, type=Path)
    parser.add_argument("--isolated-clone", required=True, type=Path)
    return parser.parse_args()


if __name__ == "__main__":
    ARGS = parse_args()
    unittest.main(argv=[sys.argv[0]], verbosity=2)

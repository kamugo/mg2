"""Regression checks for the portable B11 contract audit."""

from __future__ import annotations

import argparse
import importlib.util
import sys
import unittest
from pathlib import Path


SCRIPT = Path(__file__).with_name("audit_b11_contracts.py")
SPEC = importlib.util.spec_from_file_location("audit_b11_contracts", SCRIPT)
if SPEC is None or SPEC.loader is None:
    raise RuntimeError(f"Nie mozna zaladowac {SCRIPT}")
AUDIT = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = AUDIT
SPEC.loader.exec_module(AUDIT)


class AuditB11ContractsTest(unittest.TestCase):
    result: dict

    @classmethod
    def setUpClass(cls) -> None:
        cls.result = AUDIT.audit(ARGS)

    def test_score_source_and_subtoken_counterexample(self) -> None:
        case = self.result["score_contract"]["source_split_content_counterexample"]
        self.assertTrue(case["accepted"])
        self.assertFalse(case["raw_original_and_subtoken_ids_equal"])

    def test_all_zero_checks_do_not_precede_all_scorer_calls(self) -> None:
        case = self.result["score_contract"]["late_subtoken_zero_preflight"]
        self.assertEqual(case["wrapper"]["exit_code"], 1)
        self.assertEqual(case["scorer_calls_before_rejection"], 4)
        self.assertTrue(case["expected_rejection"])
        self.assertFalse(case["official_json_created"])

    def test_release_gate_accepts_three_impossible_aggregates(self) -> None:
        gate = self.result["release_gate"]
        self.assertTrue(gate["baseline_passes"])
        self.assertEqual(gate["accepted_count"], 3)
        self.assertTrue(all(gate["impossible_aggregate_mutations_accepted"].values()))

    def test_artifact_and_history_provenance(self) -> None:
        artifacts = self.result["artifact_provenance"]
        self.assertEqual(artifacts["mismatches"], ["scripts/score_official.py"])
        self.assertEqual(artifacts["score_official_difference_bytes"], 76)
        history = self.result["historical_correction"]
        self.assertFalse(history["bad_referenced_a_sha_exists"])
        self.assertTrue(history["corrected_a_sha_exists"])
        self.assertTrue(history["b9_author_sha_command_now_returns_b11"])


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--agent-b-root", required=True, type=Path)
    parser.add_argument("--agent-a-root", required=True, type=Path)
    return parser.parse_args()


if __name__ == "__main__":
    ARGS = parse_args()
    unittest.main(argv=[sys.argv[0]], verbosity=2)

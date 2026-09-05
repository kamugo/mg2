"""Regression checks for the pinned, synthetic Agent B round-12 audit."""

from __future__ import annotations

import argparse
import importlib.util
import sys
import unittest
from pathlib import Path


SCRIPT = Path(__file__).with_name("audit_b12_release.py")
SPEC = importlib.util.spec_from_file_location("audit_b12_release", SCRIPT)
if SPEC is None or SPEC.loader is None:
    raise RuntimeError(f"Nie mozna zaladowac {SCRIPT}")
AUDIT = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = AUDIT
SPEC.loader.exec_module(AUDIT)


class AuditB12ReleaseTest(unittest.TestCase):
    result: dict

    @classmethod
    def setUpClass(cls) -> None:
        cls.result = AUDIT.audit(ARGS.agent_b_root)

    def test_head_is_reresolved_after_reported_sha(self) -> None:
        race = self.result["candidate_race"]
        self.assertTrue(race["reproduced"])
        self.assertEqual(race["candidate"], "HEAD")
        self.assertNotEqual(race["resolved_candidate"], race["scanned_candidate"])
        self.assertEqual(race["tracked_controlled_files"], 1)
        self.assertFalse(race["pass"])

    def test_ledger_accepts_shape_only_fake_provenance(self) -> None:
        ledger = self.result["ledger_validation"]
        self.assertTrue(ledger["accepted"])
        self.assertTrue(ledger["fake_revision_preserved"])
        self.assertTrue(ledger["fake_tree_oids_preserved"])
        self.assertTrue(ledger["fake_counts_preserved"])
        self.assertTrue(ledger["fake_statuses_preserved"])
        self.assertTrue(ledger["fake_objects_absent_from_git"])

    def test_release_gate_accepts_two_residual_impossibilities(self) -> None:
        cases = self.result["release_gate_residuals"]
        self.assertTrue(cases["accepted_near_with_no_group_reduction"]["accepted"])
        self.assertGreater(
            cases["accepted_near_with_no_group_reduction"]["accepted_near_pairs"], 0
        )
        self.assertEqual(
            cases["accepted_near_with_no_group_reduction"]["final_groups"],
            cases["accepted_near_with_no_group_reduction"]["unique_exact_hashes"],
        )
        split_case = cases["split_group_size_absent_from_histogram"]
        self.assertTrue(split_case["accepted"])
        self.assertEqual(split_case["split_group_count"], 1)
        self.assertNotIn(str(split_case["split_record_count"]), split_case["histogram_sizes"])

    def test_deletions_are_exactly_scoped_to_five_directories(self) -> None:
        tree = self.result["tree_deletions"]
        expected = {
            "kod/data/saos2015": 43,
            "kod/data/silver": 403,
            "kod/data/silver_corpipe": 43,
            "kod/data/pilot": 23,
            "kod/data/przeglad50": 165,
        }
        self.assertEqual(tree["b11_tree_counts"], expected)
        self.assertEqual(tree["b12_tree_counts"], {path: 0 for path in expected})
        self.assertEqual(tree["b11_total"], 677)
        self.assertEqual(tree["b12_total"], 0)
        self.assertEqual(tree["deleted_files"], 677)
        self.assertEqual(tree["deleted_outside_declared_directories"], 0)
        self.assertTrue(tree["ledger_baseline_matches_b11"])


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--agent-b-root", required=True, type=Path)
    return parser.parse_args()


if __name__ == "__main__":
    ARGS = parse_args()
    unittest.main(argv=[sys.argv[0]], verbosity=2)

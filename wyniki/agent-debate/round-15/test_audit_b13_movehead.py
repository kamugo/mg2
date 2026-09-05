"""Regression checks for the portable Agent B round-13 MoveHead audit."""

from __future__ import annotations

import argparse
import importlib.util
import sys
import unittest
from pathlib import Path


SCRIPT = Path(__file__).with_name("audit_b13_movehead.py")
SPEC = importlib.util.spec_from_file_location("audit_b13_movehead", SCRIPT)
if SPEC is None or SPEC.loader is None:
    raise RuntimeError(f"Nie mozna zaladowac {SCRIPT}")
AUDIT = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = AUDIT
SPEC.loader.exec_module(AUDIT)


class AuditB13MoveHeadTest(unittest.TestCase):
    result: dict

    @classmethod
    def setUpClass(cls) -> None:
        cls.result = AUDIT.audit(ARGS.agent_b_root)

    def test_final_writer_hash_disagrees_with_committed_verification(self) -> None:
        provenance = self.result["writer_provenance"]
        final_hash = "4a8eb82841e35b285cda80659c5259ec99b1ab5269e9671c7384e96d75b48226"
        stale_hash = "3fefde186bd486f1749f8597a96cf9e3f09cce1644dc04411cfc146b445dd022"
        self.assertEqual(provenance["final_git_blob_sha256_lf"], final_hash)
        self.assertEqual(provenance["manifest_sha256_lf"], final_hash)
        self.assertEqual(provenance["git_blob_runtime_sha256"], final_hash)
        self.assertEqual(provenance["committed_verification_current_writer_sha256"], stale_hash)
        self.assertTrue(provenance["committed_verification_mismatch"])

    def test_report_and_generator_do_not_pin_b13(self) -> None:
        pin = self.result["b13_revision_pin"]
        self.assertEqual(pin["report_b_sha"], "4c2e45ba06a4ef152cddd04204896e39851d6192")
        self.assertNotEqual(pin["report_b_sha"], self.result["agent_b_sha"])
        self.assertFalse(pin["generator_contains_b13_sha"])
        self.assertFalse(pin["generator_asserts_b13_revision"])
        self.assertTrue(pin["generator_hashes_mutable_worktree_writer"])

    def test_exact_vectors_contain_only_rounded_f1(self) -> None:
        exact = self.result["exact_metric_evidence"]
        self.assertEqual(exact["exact_run_count"], 8)
        self.assertEqual(exact["metric_keys"], ["bcub", "ceafe", "lea", "muc"])
        self.assertTrue(exact["all_metric_values_rounded_to_two_decimals"])
        self.assertTrue(exact["conll_is_separate_and_rounded"])
        self.assertFalse(exact["precision_recall_present"])
        self.assertFalse(exact["raw_counts_present"])
        self.assertTrue(exact["generator_compares_metrics_dict_only"])

    def test_production_pin_is_narrower_than_a12_audit_pin(self) -> None:
        pin = self.result["udapi_pin_scope"]
        self.assertEqual(pin["production_hashed_modules"], ["udapi.block.corefud.movehead"])
        self.assertEqual(pin["production_imported_but_unhashed_modules"], ["udapi.core.document"])
        self.assertEqual(pin["production_udapi_version"], "0.5.2")
        self.assertEqual(pin["a12_audit_hashed_module_count"], 5)
        self.assertEqual(len(pin["a12_audit_hashed_modules"]), 5)

    def test_synthetic_write_on_original_round_trip(self) -> None:
        case = self.result["synthetic_round_trip"]
        self.assertTrue(case["passed"])
        self.assertEqual(case["head_position_in_mention"], 2)
        self.assertEqual(case["entity_count"], 1)
        self.assertEqual(case["mention_count"], 1)
        self.assertTrue(case["used_second_enhanced_parent"])
        self.assertTrue(case["gold_coreference_removed"])
        self.assertEqual(case["head_udapi_version"], "0.5.2")
        self.assertEqual(
            case["head_movehead_sha256"],
            "0bd50896d39dcc4ef472c0414ab150cf6e587af88e0159c4b146c748409449e1",
        )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--agent-b-root", required=True, type=Path)
    return parser.parse_args()


if __name__ == "__main__":
    ARGS = parse_args()
    unittest.main(argv=[sys.argv[0]], verbosity=2)

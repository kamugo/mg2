"""Regression checks for the portable, pinned Agent B round-14 audit."""

from __future__ import annotations

import argparse
import importlib.util
import sys
import unittest
from pathlib import Path


SCRIPT = Path(__file__).with_name("audit_b14_contracts.py")
SPEC = importlib.util.spec_from_file_location("audit_b14_contracts", SCRIPT)
if SPEC is None or SPEC.loader is None:
    raise RuntimeError(f"Nie mozna zaladowac {SCRIPT}")
AUDIT = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = AUDIT
SPEC.loader.exec_module(AUDIT)


class AuditB14ContractsTest(unittest.TestCase):
    result: dict

    @classmethod
    def setUpClass(cls) -> None:
        cls.result = AUDIT.audit(ARGS.agent_b_root)

    def test_final_manifest_binds_all_sixteen_blobs(self) -> None:
        manifest = self.result["manifest_provenance"]
        self.assertEqual(manifest["entry_count"], 16)
        self.assertEqual(manifest["matched_blob_count"], 16)
        self.assertEqual(manifest["mismatches"], [])
        self.assertTrue(manifest["all_entries_match_final_b14"])

    def test_committed_report_passes_despite_two_pre_final_mismatches(self) -> None:
        provenance = self.result["committed_verification_provenance"]
        self.assertTrue(provenance["reported_passed"])
        self.assertEqual(
            provenance["artifact_mismatch_paths"],
            ["src/eval/alignment.py", "tests/test_evaluation_alignment.py"],
        )
        self.assertEqual(
            provenance["artifact_git_revisions"],
            ["7d9a7f85f6288bbc5ff37598b54f607752140275"],
        )
        self.assertFalse(provenance["artifact_equality_is_a_pass_check"])
        self.assertFalse(provenance["generator_contains_final_b14_sha"])
        self.assertFalse(provenance["generator_asserts_final_b14_revision"])
        self.assertTrue(provenance["main_artifacts_use_default_revision"])
        self.assertEqual(provenance["describe_artifact_default_revision"], "HEAD")

    def test_b14_closes_near_residual_but_keeps_split_residual(self) -> None:
        cases = self.result["release_gate_residuals"]
        near = cases["accepted_near_pairs_with_f_equals_u"]
        self.assertFalse(near["accepted"])
        self.assertGreater(near["accepted_near_pairs"], 0)
        self.assertEqual(near["final_groups"], near["unique_exact_hashes"])
        self.assertIn("exact_pairs_skipped", near["rejection"])
        self.assertTrue(near["b14_closes_a14_residual"])
        split = cases["split_five_records_one_group_without_size_five"]
        self.assertTrue(split["accepted"])
        self.assertEqual(split["split_record_count"], 5)
        self.assertEqual(split["split_group_count"], 1)
        self.assertNotIn("5", split["global_histogram_sizes"])

    def test_tree_gate_race_and_shape_only_ledger_remain_reproducible(self) -> None:
        race = self.result["tree_gate_candidate_race"]
        self.assertTrue(race["reproduced"])
        self.assertNotEqual(race["resolved_candidate"], race["scanned_candidate"])
        self.assertEqual(race["tracked_controlled_files"], 1)
        ledger = self.result["tree_gate_ledger_validation"]
        self.assertTrue(ledger["accepted"])
        self.assertTrue(ledger["fake_revision_preserved"])
        self.assertTrue(ledger["fake_tree_oids_preserved"])
        self.assertTrue(ledger["fake_counts_preserved"])
        self.assertTrue(ledger["fake_statuses_preserved"])
        self.assertTrue(ledger["fake_objects_absent_from_git"])

    def test_validator_accepts_two_ambiguous_complete_partitions(self) -> None:
        ambiguity = self.result["alignment_tokenizer_proof_boundary"]
        self.assertEqual(ambiguity["partition_sizes"], [[1, 2], [2, 1]])
        self.assertEqual(ambiguity["accepted"], [True, True])
        self.assertEqual(ambiguity["coverage_complete"], [True, True])
        self.assertNotEqual(ambiguity["alignment_sha256"][0], ambiguity["alignment_sha256"][1])
        self.assertTrue(ambiguity["does_not_prove_tokenizer_boundary_authenticity"])

    def test_source_slice_ignores_syntax_and_gold_misc(self) -> None:
        case = self.result["source_slice_semantic_gap"]
        self.assertTrue(case["accepted"])
        self.assertTrue(case["source_slice_semantics_agree"])
        self.assertFalse(case["source_vs_original_head_deps_equal"])
        self.assertFalse(case["source_vs_original_gold_misc_equal"])
        self.assertFalse(case["source_vs_original_entity_spans_equal"])
        self.assertEqual(case["source_entity_token_ids"], [[1, 2]])
        self.assertEqual(case["original_gold_entity_token_ids"], [[2]])
        self.assertTrue(case["original_gold_and_pred_use_fabricated_entity"])
        self.assertTrue(case["alignment_original_gold_hash_refreshed"])
        self.assertEqual(case["scorer_invocations"], 0)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--agent-b-root", required=True, type=Path)
    return parser.parse_args()


if __name__ == "__main__":
    ARGS = parse_args()
    unittest.main(argv=[sys.argv[0]], verbosity=2)

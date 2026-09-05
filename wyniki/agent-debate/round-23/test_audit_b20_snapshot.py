"""Regression tests for the Git-pinned Agent B round-20 snapshot audit."""

from __future__ import annotations

import argparse
import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest


SCRIPT = Path(__file__).with_name("audit_b20_snapshot.py")
SPEC = importlib.util.spec_from_file_location("audit_b20_snapshot", SCRIPT)
if SPEC is None or SPEC.loader is None:
    raise RuntimeError(f"Nie mozna zaladowac {SCRIPT}")
AUDIT = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = AUDIT
SPEC.loader.exec_module(AUDIT)


class AuditB20SnapshotTest(unittest.TestCase):
    result: dict

    @classmethod
    def setUpClass(cls) -> None:
        cls.result = AUDIT.audit(ARGS.agent_b_root)

    def test_final_clean_revision_and_lineage_are_pinned(self) -> None:
        self.assertEqual(self.result["target_revision"], AUDIT.B20_FINAL_SHA)
        self.assertEqual(self.result["implementation_revision"], AUDIT.IMPLEMENTATION_SHA)
        self.assertEqual(self.result["publication_revision"], AUDIT.PUBLICATION_SHA)
        self.assertEqual(self.result["lineage"]["logical_commits"], [
            AUDIT.PROTOCOL_SHA,
            AUDIT.IMPLEMENTATION_SHA,
            AUDIT.PUBLICATION_SHA,
            AUDIT.B20_FINAL_SHA,
        ])
        boundary = self.result["input_boundary"]
        self.assertTrue(boundary["initial_worktree_clean"])
        self.assertTrue(boundary["final_worktree_clean"])
        self.assertTrue(boundary["final_head_is_target"])
        self.assertFalse(boundary["network_real_data_scorer_model_or_gpu_used"])
        self.assertFalse(boundary["raw_conllu_content_persisted_or_displayed"])

    def test_receipt_and_manifest_partitions_are_independently_verified(self) -> None:
        receipt = self.result["publication_receipt"]
        self.assertEqual(receipt["target_commit_added_paths"], [AUDIT.RECEIPT_PATH])
        self.assertFalse(receipt["receipt_present_at_publication"])
        self.assertEqual(receipt["declared_attested_commit"], AUDIT.PUBLICATION_SHA)
        self.assertFalse(receipt["attestation_blob_in_attested_commit"])
        self.assertTrue(receipt["own_future_commit_intentionally_excluded"])
        self.assertEqual(receipt["check_count"], 10)
        self.assertEqual(receipt["true_check_count"], 10)
        partitions = receipt["independent_partitions"]
        self.assertEqual(partitions["manifest_entry_count"], 112)
        self.assertEqual(partitions["implementation_count"], 109)
        self.assertEqual(partitions["generated_count"], 3)
        self.assertTrue(partitions["complete_and_disjoint"])
        self.assertEqual(partitions["implementation_mismatches"], [])
        self.assertEqual(partitions["generated_present_at_implementation"], [])
        self.assertEqual(partitions["publication_mismatches"], [])
        self.assertTrue(receipt["independent_structure_passed"])

    def test_unpinned_prediction_is_accepted_as_main_table_evidence(self) -> None:
        probe = self.result["unpinned_prediction_probe"]
        self.assertNotEqual(probe["pred_original_sha256_before"],
                            probe["pred_original_sha256_after"])
        self.assertEqual(probe["anchor_sha256_before"], probe["anchor_sha256_after"])
        self.assertEqual(probe["main_return_value"], 0)
        self.assertEqual(probe["scorer_call_count"], 8)
        self.assertEqual(probe["alignment_provenance_status"],
                         "VERIFIED_RECORDED_PROVENANCE")
        self.assertTrue(probe["main_table_eligible"])
        self.assertEqual(probe["report_pred_original_sha256"],
                         probe["pred_original_sha256_after"])
        self.assertNotIn("pred_on_original_sha256", probe["anchor_checked_input_keys"])
        self.assertNotIn("eval_json_sha256", probe["anchor_checked_input_keys"])
        self.assertTrue(probe["gap_reproduced"])
        self.assertEqual(probe["subject_main_table_contract"], "FAIL")
        self.assertEqual(probe["expected_safe_contract"], {
            "reject_unpinned_prediction": True,
            "scorer_call_count": 0,
            "main_table_eligible": False,
            "final_output_created": False,
        })

    def test_transient_child_read_gap_is_labelled_acknowledged(self) -> None:
        probe = self.result["transient_child_read_probe"]
        self.assertEqual(probe["classification"],
                         "ACKNOWLEDGED_POINT_CHECK_LIMITATION")
        self.assertEqual(probe["mutated_at_scorer_call"], 5)
        self.assertEqual(probe["mutated_role"], "gold_subtoken")
        self.assertTrue(probe["mutated_path_in_child_argv"])
        self.assertEqual(probe["scorer_call_count"], 8)
        self.assertEqual(probe["main_return_value"], 0)
        self.assertNotEqual(probe["child_observed_sha256"],
                            probe["report_scored_sha256"])
        self.assertEqual(probe["restored_snapshot_sha256"],
                         probe["report_scored_sha256"])
        self.assertTrue(probe["main_table_eligible"])
        self.assertTrue(probe["gap_reproduced"])
        self.assertFalse(probe["claimed_undisclosed_by_agent_b"])
        self.assertEqual(probe["expected_safe_contract"], {
            "reject_child_digest_mismatch": True,
            "scorer_call_count_before_rejection": 5,
            "main_table_eligible": False,
            "final_output_created": False,
        })

    def test_final_progress_log_is_statically_stale(self) -> None:
        progress = self.result["postep_static_audit"]
        self.assertTrue(progress["b20_heading_found"])
        self.assertTrue(progress["implementation_in_progress_marker_found"])
        self.assertTrue(progress["open_tests_marker_found"])
        self.assertTrue(progress["finish_verification_next_step_found"])
        self.assertTrue(progress["stale_final_status_reproduced"])
        self.assertNotIn("line_text", progress)

    def test_cli_writes_passed_audit_with_separate_failed_subject_contract(self) -> None:
        with tempfile.TemporaryDirectory(prefix="a23-b20-cli-") as directory:
            output = Path(directory) / "audit.json"
            completed = subprocess.run(
                [sys.executable, "-B", str(SCRIPT),
                 "--agent-b-root", str(ARGS.agent_b_root), "--output", str(output)],
                check=False,
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
            )
            self.assertEqual(completed.returncode, 0, completed.stderr)
            stdout_result = json.loads(completed.stdout)
            file_result = json.loads(output.read_text(encoding="utf-8"))
            self.assertEqual(stdout_result, file_result)
            self.assertEqual(stdout_result["audit_status"], "PASS")
            self.assertEqual(stdout_result["b20_main_table_contract_status"], "FAIL")

    def test_cli_removes_stale_output_before_failed_audit(self) -> None:
        with tempfile.TemporaryDirectory(prefix="a23-b20-cli-fail-") as directory:
            root = Path(directory)
            output = root / "audit.json"
            output.write_text('{"audit_status":"PASS"}\n', encoding="utf-8")
            completed = subprocess.run(
                [sys.executable, "-B", str(SCRIPT),
                 "--agent-b-root", str(root), "--output", str(output)],
                check=False,
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
            )
            self.assertNotEqual(completed.returncode, 0)
            self.assertFalse(output.exists(), "stary PASS nie moze przezyc bledu audytu")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--agent-b-root", required=True, type=Path)
    return parser.parse_args()


if __name__ == "__main__":
    ARGS = parse_args()
    unittest.main(argv=[sys.argv[0]], verbosity=2)

"""Regression tests for the Git-pinned Agent B round-19 contract audit."""

from __future__ import annotations

import argparse
import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest


SCRIPT = Path(__file__).with_name("audit_b19_contract.py")
SPEC = importlib.util.spec_from_file_location("audit_b19_contract", SCRIPT)
if SPEC is None or SPEC.loader is None:
    raise RuntimeError(f"Nie mozna zaladowac {SCRIPT}")
AUDIT = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = AUDIT
SPEC.loader.exec_module(AUDIT)


class AuditB19ContractTest(unittest.TestCase):
    result: dict

    @classmethod
    def setUpClass(cls) -> None:
        cls.result = AUDIT.audit(ARGS.agent_b_root)

    def test_final_clean_revision_and_lineage_are_pinned(self) -> None:
        self.assertEqual(self.result["target_revision"], AUDIT.B19_FINAL_SHA)
        self.assertEqual(self.result["publication_revision"], AUDIT.PUBLICATION_SHA)
        self.assertEqual(self.result["implementation_revision"], AUDIT.IMPLEMENTATION_SHA)
        self.assertEqual(self.result["base_revision"], AUDIT.B18_SHA)
        self.assertEqual(self.result["lineage"]["logical_commits"], [
            AUDIT.PROTOCOL_SHA,
            AUDIT.IMPLEMENTATION_SHA,
            AUDIT.PUBLICATION_SHA,
            AUDIT.B19_FINAL_SHA,
        ])
        boundary = self.result["input_boundary"]
        self.assertTrue(boundary["initial_head_is_target"])
        self.assertTrue(boundary["initial_worktree_clean"])
        self.assertTrue(boundary["final_head_is_target"])
        self.assertTrue(boundary["final_worktree_clean"])
        self.assertEqual(boundary["agent_b_artifact_access"], "pinned Git blobs only")
        self.assertFalse(boundary["network_real_data_scorer_model_or_gpu_used"])

    def test_unknown_mode_fail_open_is_reproduced(self) -> None:
        probe = self.result["invalid_mode_probe"]
        self.assertTrue(probe["executed_source_matches_target_blob"])
        self.assertEqual(probe["process"]["exit_code"], 0)
        self.assertTrue(probe["observed"]["accepted"])
        self.assertEqual(probe["observed"]["reported_mode"], "eid-neutral")
        self.assertEqual(probe["requested_mode"], "bogus")
        self.assertTrue(probe["gap_reproduced"])
        self.assertEqual(probe["expected_safe_contract"], {
            "accepted": False,
            "reject_unknown_mode": True,
            "nonzero_or_exception": True,
        })

    def test_receipt_independently_binds_publication_but_not_itself(self) -> None:
        receipt = self.result["publication_receipt"]
        self.assertTrue(receipt["final_blob_is_json"])
        self.assertEqual(receipt["target_commit_added_paths"], [AUDIT.RECEIPT_PATH])
        self.assertFalse(receipt["receipt_present_at_publication"])
        self.assertTrue(receipt["receipt_present_at_final"])
        self.assertEqual(receipt["declared_publication_commit"], AUDIT.PUBLICATION_SHA)
        self.assertEqual(receipt["declared_attested_commit"], AUDIT.PUBLICATION_SHA)
        self.assertEqual(receipt["final_receipt_commit"], AUDIT.B19_FINAL_SHA)
        self.assertFalse(receipt["attestation_blob_in_attested_commit"])
        self.assertTrue(receipt["own_future_commit_intentionally_excluded"])
        self.assertEqual(receipt["check_count"], 10)
        self.assertEqual(receipt["true_check_count"], 10)
        self.assertTrue(receipt["declared_passed"])
        self.assertTrue(receipt["manifest_sha_matches_prepublication_receipt"])
        partitions = receipt["independent_partitions"]
        self.assertEqual(partitions["manifest_entry_count"], 124)
        self.assertEqual(partitions["implementation_count"], 104)
        self.assertEqual(partitions["generated_count"], 20)
        self.assertTrue(partitions["complete_and_disjoint"])
        self.assertEqual(partitions["implementation_mismatches"], [])
        self.assertEqual(partitions["generated_present_at_implementation"], [])
        self.assertEqual(partitions["publication_mismatches"], [])
        self.assertTrue(receipt["independent_structure_passed"])

    def test_mutable_output_gap_has_static_partial_evidence(self) -> None:
        probe = self.result["mutable_output_probe"]
        self.assertEqual(probe["status"], "PARTIAL_STATIC_EVIDENCE")
        self.assertTrue(probe["detached_code_execution"])
        self.assertTrue(probe["all_recorded_outputs_outside_detached_clone"])
        self.assertTrue(probe["parent_reads_report_from_mutable_output"])
        self.assertTrue(probe["manifest_built_from_mutable_output"])
        self.assertEqual(probe["dynamic_mutation_attempted"], False)
        self.assertEqual(probe["expected_safe_contract"], {
            "all_experiment_io_inside_detached_sandbox": True,
            "reject_hash_change_before_manifest": True,
            "receipt_passed_on_mismatch": False,
            "final_outputs_on_mismatch": False,
        })

    def test_cli_writes_same_pass_audit_and_separate_failed_contract(self) -> None:
        with tempfile.TemporaryDirectory(prefix="a22-b19-cli-") as directory:
            output = Path(directory) / "audit.json"
            completed = subprocess.run(
                [sys.executable, "-B", str(SCRIPT),
                 "--agent-b-root", str(ARGS.agent_b_root), "--output", str(output)],
                check=False, capture_output=True, text=True, encoding="utf-8",
                errors="replace",
            )
            self.assertEqual(completed.returncode, 0, completed.stderr)
            stdout_result = json.loads(completed.stdout)
            file_result = json.loads(output.read_text(encoding="utf-8"))
            self.assertEqual(stdout_result, file_result)
            self.assertEqual(stdout_result["audit_status"], "PASS")
            self.assertEqual(stdout_result["b19_contract_status"], "FAIL")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--agent-b-root", required=True, type=Path)
    return parser.parse_args()


if __name__ == "__main__":
    ARGS = parse_args()
    unittest.main(argv=[sys.argv[0]], verbosity=2)

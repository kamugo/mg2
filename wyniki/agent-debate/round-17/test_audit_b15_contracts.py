"""Regression checks for the portable, pinned Agent B round-15 audit."""

from __future__ import annotations

import argparse
import importlib.util
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


SCRIPT = Path(__file__).with_name("audit_b15_contracts.py")
SPEC = importlib.util.spec_from_file_location("audit_b15_contracts", SCRIPT)
if SPEC is None or SPEC.loader is None:
    raise RuntimeError(f"Nie mozna zaladowac {SCRIPT}")
AUDIT = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = AUDIT
SPEC.loader.exec_module(AUDIT)


class AuditB15ContractsTest(unittest.TestCase):
    result: dict

    @classmethod
    def setUpClass(cls) -> None:
        cls.result = AUDIT.audit(ARGS.agent_b_root, ARGS.isolated_clone)

    def test_final_manifest_receipt_and_clone_are_pinned(self) -> None:
        clone = self.result["input_boundary"]["isolated_clone"]
        self.assertEqual(clone["head"], AUDIT.B15_SHA)
        self.assertTrue(clone["clean"])
        manifest = self.result["final_manifest"]
        self.assertEqual(manifest["entry_count"], 33)
        self.assertEqual(manifest["matched_blob_count"], 33)
        self.assertEqual(manifest["mismatches"], [])
        receipt = self.result["final_receipt"]
        self.assertTrue(receipt["manifest_sha256_matches"])
        self.assertTrue(receipt["manifest_passed"])
        self.assertTrue(receipt["passed"])

    def test_all_reported_provenance_is_bound_to_implementation(self) -> None:
        provenance = self.result["verification_provenance"]
        self.assertEqual(provenance["artifact_count"], 32)
        self.assertEqual(provenance["mismatches"], [])
        self.assertEqual(provenance["revisions"], [AUDIT.IMPLEMENTATION_SHA])
        self.assertTrue(provenance["all_checks_true"])
        self.assertTrue(provenance["clean_revision_output_hash_matches"])

    def test_tree_snapshot_and_ledger_fixes_are_reproduced(self) -> None:
        tree = self.result["tree_gate_fixes"]
        self.assertTrue(tree["ref_snapshot"]["reproduced"])
        self.assertTrue(tree["ref_snapshot"]["passed_clean_snapshot"])
        self.assertNotEqual(
            tree["ref_snapshot"]["resolved_oid"],
            tree["ref_snapshot"]["moved_ref_oid"],
        )
        self.assertTrue(tree["index_snapshot"]["reproduced"])
        self.assertNotEqual(
            tree["index_snapshot"]["scanned_tree_oid"],
            tree["index_snapshot"]["mutated_index_oid"],
        )
        self.assertTrue(tree["ledger"]["baseline_accepted"])
        self.assertTrue(all(tree["ledger"]["mutation_rejected"].values()))

    def test_release_gate_fixes_are_reproduced(self) -> None:
        release = self.result["release_gate_fixes"]
        self.assertTrue(release["baseline_v1_accepted"])
        self.assertTrue(release["baseline_v2_accepted"])
        self.assertTrue(release["near_no_reduction_rejected_v1"])
        self.assertTrue(release["near_no_reduction_rejected_v2"])
        self.assertTrue(release["joint_split_allocation_rejected"])
        self.assertEqual(release["split_oracle_cases"], 1605)
        self.assertEqual(release["split_oracle_discrepancies"], 0)

    def test_controlled_toctou_proves_receipt_can_cover_mutated_bytes(self) -> None:
        proof = self.result["generator_toctou"]
        self.assertTrue(proof["reproduced"])
        self.assertTrue(proof["initial_candidate_matches_implementation"])
        self.assertTrue(proof["mutation_after_initial_check"])
        self.assertNotEqual(proof["implementation_sha256"], proof["mutated_sha256"])
        self.assertEqual(proof["manifest_sha256"], proof["mutated_sha256"])
        self.assertTrue(proof["reported_core_checks"])
        self.assertTrue(proof["manifest_verification_passed"])
        self.assertTrue(proof["receipt_passed"])
        self.assertFalse(proof["post_manifest_final_blob_comparison"])

    def test_cli_emits_the_same_json_contract(self) -> None:
        with tempfile.TemporaryDirectory(prefix="a17-cli-") as temp_dir:
            output = Path(temp_dir) / "audit.json"
            completed = subprocess.run(
                [
                    sys.executable,
                    str(SCRIPT),
                    "--agent-b-root",
                    str(ARGS.agent_b_root),
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
            self.assertEqual(stdout_result["target_revision"], AUDIT.B15_SHA)
            self.assertTrue(stdout_result["generator_toctou"]["reproduced"])


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--agent-b-root", required=True, type=Path)
    parser.add_argument("--isolated-clone", required=True, type=Path)
    return parser.parse_args()


if __name__ == "__main__":
    ARGS = parse_args()
    unittest.main(argv=[sys.argv[0]], verbosity=2)

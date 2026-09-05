"""Regression tests for the portable, Git-pinned Agent B round-17 audit."""

from __future__ import annotations

import argparse
import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest


SCRIPT = Path(__file__).with_name("audit_b17_contracts.py")
SPEC = importlib.util.spec_from_file_location("audit_b17_contracts", SCRIPT)
if SPEC is None or SPEC.loader is None:
    raise RuntimeError(f"Nie mozna zaladowac {SCRIPT}")
AUDIT = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = AUDIT
SPEC.loader.exec_module(AUDIT)


class AuditB17ContractsTest(unittest.TestCase):
    result: dict

    @classmethod
    def setUpClass(cls) -> None:
        cls.result = AUDIT.audit(ARGS.agent_b_root)

    def test_lineage_and_input_boundary_are_explicit(self) -> None:
        self.assertEqual(self.result["target_revision"], AUDIT.B17_SHA)
        self.assertEqual(self.result["implementation_revision"], AUDIT.IMPLEMENTATION_SHA)
        self.assertEqual(self.result["base_revision"], AUDIT.B16_SHA)
        self.assertEqual(
            self.result["lineage"]["logical_commits"],
            [AUDIT.IMPLEMENTATION_SHA, AUDIT.B17_SHA],
        )
        boundary = self.result["input_boundary"]
        self.assertEqual(boundary["agent_b_access"], "pinned Git blobs and commit metadata only")
        self.assertTrue(boundary["synthetic_data_only"])
        self.assertFalse(boundary["corpus_model_scorer_or_gpu_used"])
        self.assertFalse(boundary["raw_synthetic_content_persisted_or_displayed"])
        self.assertTrue(boundary["temporary_content_removed"])
        serialized = json.dumps(self.result, ensure_ascii=False)
        for marker in ("Ala ma kota", "Entity=(", "forged-person-1"):
            self.assertNotIn(marker, serialized)

    def test_manifest_hybrid_is_reproduced_from_independent_git_objects(self) -> None:
        manifest = self.result["manifest_hybrid"]
        self.assertEqual(manifest["entry_count"], 44)
        self.assertEqual(manifest["implementation_blob_entries"], 42)
        self.assertEqual(manifest["generated_entries_absent_from_implementation"], [
            "data/agent-debate/round-17/b14_pinned_erratum.json",
            "data/agent-debate/round-17/verification.json",
        ])
        self.assertEqual(manifest["generated_entry_count"], 2)
        self.assertEqual(manifest["implementation_mismatches"], [])
        self.assertEqual(manifest["final_revision_mismatches"], [])
        self.assertEqual(manifest["entries_matching_final_revision"], 44)
        self.assertFalse(manifest["all_entries_exist_in_implementation"])
        self.assertTrue(manifest["hybrid_42_implementation_plus_2_generated_proven"])

    def test_receipt_claim_is_literal_true_but_broader_than_the_pin_check(self) -> None:
        receipt = self.result["receipt_claim"]
        self.assertTrue(receipt["reported_manifest_inputs_match_pinned_blobs"])
        self.assertTrue(receipt["source_hard_codes_manifest_inputs_match_pinned_blobs_true"])
        self.assertEqual(receipt["source_pin_check_scope_count"], 42)
        self.assertEqual(receipt["source_pin_check_scope_mismatches"], [])
        self.assertTrue(receipt[
            "source_pin_check_scope_exactly_matches_implementation_entries"])
        self.assertEqual(receipt["manifest_entry_count"], 44)
        self.assertFalse(receipt["claim_holds_for_implementation_commit"])
        self.assertEqual(receipt["final_status_stdout_bytes"], 1063)
        self.assertTrue(receipt["reported_passed"])

    def test_toctou_mutates_pinned_gold_after_preflight_and_still_scores(self) -> None:
        race = self.result["scoring_toctou"]
        self.assertTrue(race["pinned_module_origins_verified"])
        expected = race["expected_safe_contract"]
        self.assertEqual(expected, {
            "outcome": "REJECT",
            "main_return_code_nonzero": True,
            "scorer_calls": 0,
            "output_artifacts_created": False,
        })
        observed = race["observed_current_behavior"]
        self.assertEqual(observed["main_return_code"], 0)
        self.assertEqual(observed["python_version_calls"], 1)
        self.assertEqual(observed["scorer_calls"], 8)
        self.assertEqual(observed["alignment_provenance_status"],
                         "VERIFIED_RECORDED_PROVENANCE")
        self.assertTrue(observed["input_anchor_independently_pinned"])
        self.assertNotEqual(observed["anchor_original_gold_sha256"],
                            observed["post_mutation_original_gold_sha256"])
        self.assertEqual(observed["recorded_original_gold_sha256"],
                         observed["post_mutation_original_gold_sha256"])
        self.assertEqual(observed["original_gold_scorer_calls"], 4)
        self.assertEqual(observed["original_gold_scorer_hashes"],
                         [observed["post_mutation_original_gold_sha256"]] * 4)
        self.assertTrue(observed["official_report_created"])
        self.assertEqual(observed["scorer_log_count"], 8)
        self.assertTrue(race["contract_violation_reproduced"])

    def test_cli_emits_the_same_valid_json(self) -> None:
        with tempfile.TemporaryDirectory(prefix="a20-b17-cli-") as directory:
            output = Path(directory) / "audit.json"
            completed = subprocess.run(
                [sys.executable, "-B", str(SCRIPT),
                 "--agent-b-root", str(ARGS.agent_b_root), "--output", str(output)],
                check=False, capture_output=True, text=True, encoding="utf-8",
            )
            self.assertEqual(completed.returncode, 0, completed.stderr)
            stdout_result = json.loads(completed.stdout)
            file_result = json.loads(output.read_text(encoding="utf-8"))
            self.assertEqual(stdout_result, file_result)
            self.assertEqual(stdout_result["audit_status"], "PASS")
            self.assertTrue(stdout_result["scoring_toctou"]["contract_violation_reproduced"])


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--agent-b-root", required=True, type=Path)
    return parser.parse_args()


if __name__ == "__main__":
    ARGS = parse_args()
    unittest.main(argv=[sys.argv[0]], verbosity=2)

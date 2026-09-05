"""Regression tests for the portable, pinned Agent B round-16 audit."""

from __future__ import annotations

import argparse
import importlib.util
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


SCRIPT = Path(__file__).with_name("audit_b16_reexport.py")
SPEC = importlib.util.spec_from_file_location("audit_b16_reexport", SCRIPT)
if SPEC is None or SPEC.loader is None:
    raise RuntimeError(f"Nie mozna zaladowac {SCRIPT}")
AUDIT = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = AUDIT
SPEC.loader.exec_module(AUDIT)


class AuditB16ReexportTest(unittest.TestCase):
    result: dict

    @classmethod
    def setUpClass(cls) -> None:
        cls.result = AUDIT.audit(
            ARGS.agent_b_root, ARGS.agent_a_root, ARGS.isolated_clone
        )

    def test_manifest_receipt_and_provenance_are_git_bound(self) -> None:
        clone = self.result["input_boundary"]["isolated_clone"]
        self.assertEqual(clone["head"], AUDIT.B16_SHA)
        self.assertTrue(clone["clean"])
        manifest = self.result["manifest"]
        self.assertEqual(manifest["entry_count"], 37)
        self.assertEqual(manifest["matched_blob_count"], 37)
        self.assertEqual(manifest["mismatches"], [])
        provenance = self.result["verification_provenance"]
        self.assertEqual(provenance["artifact_count"], 34)
        self.assertEqual(provenance["revisions"], [AUDIT.IMPLEMENTATION_SHA])
        self.assertEqual(provenance["reported_implementation"], AUDIT.IMPLEMENTATION_SHA)
        self.assertEqual(provenance["mismatches"], [])
        receipt = self.result["receipt"]
        self.assertTrue(receipt["manifest_hash_matches"])
        self.assertTrue(receipt["manifest_passed"])
        self.assertFalse(receipt["passed"])

    def test_b13_erratum_is_pinned_without_rewriting_history(self) -> None:
        erratum = self.result["b13_erratum"]
        self.assertTrue(erratum["passed"])
        self.assertEqual(erratum["writer_revision"], AUDIT.B13_SHA)
        self.assertEqual(erratum["writer_package_file_count"], 5)
        self.assertEqual(erratum["writer_package_mismatches"], [])
        self.assertTrue(erratum["a12_audit_hash_matches"])
        self.assertEqual(erratum["scorer_run_count"], 16)
        self.assertTrue(erratum["all_scorer_exit_zero"])
        self.assertTrue(erratum["historical_round13_artifacts_unchanged"])

    def test_all_five_udapi_pins_agree_across_independent_artifacts(self) -> None:
        pins = self.result["udapi_pins"]
        self.assertEqual(pins["pin_count"], 5)
        self.assertEqual(pins["mismatches"], [])
        self.assertEqual(pins["verification_runtime_mismatches"], [])
        self.assertTrue(pins["all_sources_agree"])
        self.assertEqual(pins["version"], "0.5.2")

    def test_dead_historical_helpers_were_removed_from_production(self) -> None:
        dead = self.result["dead_code_removal"]
        self.assertEqual(dead["removed_functions"], ["_ud_parents"])
        self.assertTrue(dead["present_in_parent"])
        self.assertTrue(dead["absent_from_implementation"])
        self.assertTrue(dead["absent_from_final"])

    def test_command_statuses_preserve_the_negative_top_level_result(self) -> None:
        commands = self.result["command_statuses"]
        self.assertEqual(commands["nonzero_commands"], [])
        self.assertTrue(commands["required_commands_exit_zero"])
        self.assertEqual(
            commands["false_checks"],
            ["full_reexport_matches_a12_outputs", "full_reexport_strict_invariance_passed"],
        )
        self.assertFalse(commands["core_checks_passed"])
        self.assertFalse(self.result["receipt"]["passed"])

    def test_current_zero_loss_is_not_historical_loss(self) -> None:
        losses = self.result["loss_accounting"]
        self.assertEqual(losses["current_reexport_mentions_lost"], {
            "v2_seed42": 0, "v2_seed1": 0, "v2_seed2": 0, "v1_seed42": 0,
        })
        self.assertEqual(losses["historical_mentions_lost"], {
            "v2_seed42": 27, "v2_seed1": 33, "v2_seed2": 20, "v1_seed42": 91,
        })
        self.assertTrue(losses["historical_breakdowns_sum_to_loss"])
        self.assertTrue(losses["populations_differ_as_expected"])

    def test_strict_difference_decomposition_respects_evidence_boundary(self) -> None:
        strict = self.result["strict_difference_decomposition"]
        self.assertFalse(strict["reported_strict_invariance"])
        self.assertFalse(strict["computed_strict_invariance"])
        self.assertEqual(strict["entity_ids"]["changed_total"], 29378)
        self.assertTrue(strict["entity_ids"]["all_cluster_labels_changed"])
        self.assertEqual(strict["entity_ids"]["cluster_numbers_changed_total"], 9405)
        self.assertEqual(strict["numbering"]["writer_start_doc"], 0)
        self.assertEqual(strict["numbering"]["uniform_document_number_delta"], 60)
        self.assertEqual(
            strict["entity_formatting_or_order"]["status"], "PROVEN_BY_CANONICAL_BYTES"
        )
        self.assertEqual(
            strict["other_bytes"]["status"], "PROVEN_EQUAL_AFTER_STRIPPING_COREFERENCE"
        )
        self.assertTrue(strict["other_bytes"]["node_syntax_equal_all_models"])
        self.assertTrue(strict["corpus_blobs_read"])
        self.assertFalse(strict["performed_reinference_or_scoring"])
        deep = self.result["pinned_full_reexport"]
        self.assertTrue(deep["all_models_match_committed_aggregates"])
        self.assertEqual(deep["canonical_eid_and_head_mismatched_lines"], {
            "v2_seed42": 0, "v2_seed1": 0, "v2_seed2": 0, "v1_seed42": 0,
        })
        self.assertTrue(deep["canonical_eid_and_head_equal_all_models"])
        self.assertTrue(deep["strip_coreference_equal_all_models"])
        self.assertTrue(deep["temporary_content_removed"])
        self.assertFalse(deep["raw_content_persisted_or_displayed"])

    def test_cli_emits_valid_json(self) -> None:
        with tempfile.TemporaryDirectory(prefix="a19-cli-") as directory:
            output = Path(directory) / "audit.json"
            completed = subprocess.run(
                [
                    sys.executable, "-B", str(SCRIPT),
                    "--agent-b-root", str(ARGS.agent_b_root),
                    "--agent-a-root", str(ARGS.agent_a_root),
                    "--isolated-clone", str(ARGS.isolated_clone),
                    "--output", str(output),
                ],
                check=False, capture_output=True, text=True,
            )
            self.assertEqual(completed.returncode, 0, completed.stderr)
            stdout_result = json.loads(completed.stdout)
            file_result = json.loads(output.read_text(encoding="utf-8"))
            self.assertEqual(stdout_result, file_result)
            self.assertEqual(stdout_result["target_revision"], AUDIT.B16_SHA)
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

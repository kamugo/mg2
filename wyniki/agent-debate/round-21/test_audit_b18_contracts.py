"""Regression tests for the portable, Git-pinned Agent B round-18 audit."""

from __future__ import annotations

import argparse
import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest


SCRIPT = Path(__file__).with_name("audit_b18_contracts.py")
SPEC = importlib.util.spec_from_file_location("audit_b18_contracts", SCRIPT)
if SPEC is None or SPEC.loader is None:
    raise RuntimeError(f"Nie mozna zaladowac {SCRIPT}")
AUDIT = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = AUDIT
SPEC.loader.exec_module(AUDIT)


class AuditB18ContractsTest(unittest.TestCase):
    result: dict

    @classmethod
    def setUpClass(cls) -> None:
        cls.result = AUDIT.audit(ARGS.agent_b_root, ARGS.agent_a_root)

    def test_lineage_and_data_boundary_are_explicit(self) -> None:
        self.assertEqual(self.result["target_revision"], AUDIT.B18_SHA)
        self.assertEqual(self.result["implementation_revision"], AUDIT.IMPLEMENTATION_SHA)
        self.assertEqual(self.result["base_revision"], AUDIT.B17_SHA)
        self.assertEqual(self.result["lineage"]["logical_commits"],
                         [AUDIT.IMPLEMENTATION_SHA, AUDIT.B18_SHA])
        boundary = self.result["input_boundary"]
        self.assertEqual(boundary["agent_b_access"], "pinned Git blobs and metadata only")
        self.assertTrue(boundary["synthetic_fixture_only"])
        self.assertFalse(boundary["real_data_scorer_model_or_gpu_used"])
        self.assertFalse(boundary["raw_synthetic_content_persisted_or_displayed"])
        self.assertTrue(boundary["temporary_content_removed"])
        serialized = json.dumps(self.result, ensure_ascii=False)
        for marker in AUDIT.RAW_CONTENT_MARKERS:
            self.assertNotIn(marker, serialized)

    def test_round18_manifest_is_95_implementation_plus_15_generated(self) -> None:
        manifest = self.result["round18_manifest"]
        self.assertEqual(manifest["entry_count"], 110)
        self.assertEqual(manifest["implementation_blob_entries"], 95)
        self.assertEqual(manifest["generated_entry_count"], 15)
        self.assertEqual(manifest["generated_entries_absent_from_implementation"],
                         sorted(AUDIT.B18_GENERATED_PATHS))
        self.assertEqual(manifest["implementation_mismatches"], [])
        self.assertEqual(manifest["final_revision_mismatches"], [])
        self.assertEqual(manifest["entries_matching_final_revision"], 110)
        self.assertTrue(manifest["hybrid_95_implementation_plus_15_generated_proven"])
        scope = manifest["receipt_scope"]
        self.assertEqual(scope["checked"], 95)
        self.assertEqual(scope["matched"], 95)
        self.assertTrue(scope["passed"])
        self.assertEqual(scope["unchecked_manifest_entries"], sorted(AUDIT.B18_GENERATED_PATHS))
        self.assertTrue(scope["receipt_passed"])

    def test_fixed_b15_manifest_is_44_implementation_plus_one_generated(self) -> None:
        manifest = self.result["fixed_b15_manifest"]
        self.assertEqual(manifest["entry_count"], 45)
        self.assertEqual(manifest["implementation_blob_entries"], 44)
        self.assertEqual(manifest["generated_entries_absent_from_implementation"],
                         ["data/agent-debate/round-18/b15_fixed/verification.json"])
        self.assertEqual(manifest["generated_entry_count"], 1)
        self.assertEqual(manifest["entries_matching_final_revision"], 45)
        self.assertEqual(manifest["final_revision_mismatches"], [])
        self.assertTrue(manifest["hybrid_44_implementation_plus_1_generated_proven"])
        self.assertEqual(manifest["receipt_scope"]["checked"], 44)
        self.assertEqual(manifest["receipt_scope"]["matched"], 44)
        self.assertEqual(manifest["receipt_scope"]["unchecked_manifest_entries"],
                         ["data/agent-debate/round-18/b15_fixed/verification.json"])

    def test_validator_accepts_an_extra_unpinned_input(self) -> None:
        counterexample = self.result["manifest_extra_input_counterexample"]
        self.assertTrue(counterexample["pinned_module_origins_verified"])
        self.assertTrue(counterexample["observed"]["accepted"])
        self.assertEqual(counterexample["observed"]["checked"], 1)
        self.assertEqual(counterexample["observed"]["matched"], 1)
        self.assertEqual(counterexample["observed"]["manifest_input_count"], 2)
        self.assertEqual(counterexample["observed"]["unpinned_extra_count"], 1)
        self.assertEqual(counterexample["expected_safe_contract"], {
            "accepted": False,
            "require_exact_input_key_set": True,
            "alternative_generated_entries_section": "outputs",
        })
        self.assertTrue(counterexample["gap_reproduced"])

    def test_tracked_mg2_exporter_reproduces_segmented_cluster_only_change(self) -> None:
        exported = self.result["independent_mg2_export"]
        self.assertTrue(exported["exporter_blob_verified"])
        self.assertEqual(exported["before"]["sha256"], AUDIT.BEFORE_EXPORT_SHA256)
        self.assertEqual(exported["after"]["sha256"], AUDIT.AFTER_EXPORT_SHA256)
        for stage in ("before", "after"):
            self.assertEqual(exported[stage]["summary"],
                             {"documents": 1, "mentions": 3, "clusters": 2})
            self.assertEqual(exported[stage]["exit_code"], 0)
        self.assertEqual(exported["segmented_mention_key"], [[4, 4], [10, 10]])
        self.assertEqual(exported["segmented_head_before"], 2)
        self.assertEqual(exported["segmented_head_after"], 2)
        self.assertTrue(exported["mention_key_set_unchanged"])
        self.assertTrue(exported["heads_unchanged"])
        self.assertEqual(exported["changed_cluster_memberships"], 1)
        self.assertTrue(exported["only_segmented_mention_changed_cluster"])
        self.assertEqual(exported["input_jsonl_changed_record_count"], 1)
        self.assertEqual(exported["input_jsonl_changed_fields"], ["gold_cluster"])
        self.assertTrue(exported["input_jsonl_only_gold_cluster_changed"])
        self.assertTrue(exported["matches_committed_b18_exports"])
        self.assertFalse(exported["raw_content_persisted_or_displayed"])

    def test_cli_emits_the_same_valid_json(self) -> None:
        with tempfile.TemporaryDirectory(prefix="a21-b18-cli-") as directory:
            output = Path(directory) / "audit.json"
            completed = subprocess.run(
                [sys.executable, "-B", str(SCRIPT),
                 "--agent-b-root", str(ARGS.agent_b_root),
                 "--agent-a-root", str(ARGS.agent_a_root), "--output", str(output)],
                check=False, capture_output=True, text=True, encoding="utf-8",
            )
            self.assertEqual(completed.returncode, 0, completed.stderr)
            stdout_result = json.loads(completed.stdout)
            file_result = json.loads(output.read_text(encoding="utf-8"))
            self.assertEqual(stdout_result, file_result)
            self.assertEqual(stdout_result["audit_status"], "PASS")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--agent-b-root", required=True, type=Path)
    parser.add_argument("--agent-a-root", required=True, type=Path)
    return parser.parse_args()


if __name__ == "__main__":
    ARGS = parse_args()
    unittest.main(argv=[sys.argv[0]], verbosity=2)

"""Synthetic regressions; set COREFUD_SCORER to enable real-scorer checks."""

from __future__ import annotations

import importlib.util
import os
import sys
import tempfile
import unittest
from pathlib import Path

MODULE = Path(__file__).with_name("audit_movehead_reexport.py")
spec = importlib.util.spec_from_file_location("audit_movehead_reexport", MODULE)
audit = importlib.util.module_from_spec(spec)
spec.loader.exec_module(audit)

SOURCE = (
    "# newdoc id = synthetic\n"
    "# global.Entity = eid-etype-head-other\n"
    "# sent_id = synthetic-s1\n"
    "1\tA\t_\tNOUN\t_\t_\t3\tdep\t_\tEntity=(e-x-1-|Other=keep\n"
    "2\tB\t_\tVERB\t_\t_\t0\troot\t_\tEntity=e)\n"
    "3\tC\t_\tNOUN\t_\t_\t2\tdep\t_\t_\n"
    "4\tD\t_\tNOUN\t_\t_\t2\tdep\t_\tEntity=(e-x-1-)\n\n"
).encode("utf-8")


class MoveHeadAuditTest(unittest.TestCase):
    def test_unparsed_entity_and_discontinuous_input_are_rejected(self):
        for bad in (
            SOURCE.replace(b"Entity=e)", b"Entity=missing)"),
            SOURCE.replace(b"(e-x-1-", b"(e[1/2]-x-1-"),
        ):
            with self.assertRaises(audit.AuditError):
                audit.opening_slots(bad)

    def test_hash_mismatch_is_rejected(self):
        with self.assertRaises(audit.AuditError):
            audit.verify_hash(SOURCE, "0" * 64, "synthetic")

    def test_output_inside_input_repository_is_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp)
            with self.assertRaises(audit.AuditError):
                audit.prepare_output(repo / "outputs", repo)

    def test_gappy_head_only_change_preserves_spans_clusters_and_bytes(self):
        backend = audit.load_backend()
        with tempfile.TemporaryDirectory() as tmp:
            changed, report = audit.transform_heads(SOURCE, Path(tmp), backend)
        expected = SOURCE.replace(b"Entity=(e-x-1-", b"Entity=(e-x-2-", 1)
        self.assertEqual(changed, expected)
        self.assertEqual(report["changed_mention_heads"], 1)
        self.assertEqual(report["changed_Entity_head_fields"], 1)
        self.assertEqual(report["changed_categories"], {"gappy": 1})
        self.assertEqual(report["mentions_before"], report["mentions_after"])
        self.assertEqual(report["zero_class_changes"], 0)
        self.assertEqual(report["losses"]["mentions_removed"], 0)

    def test_policy_disagreement_is_rejected_before_scoring(self):
        ambiguous = SOURCE.replace(b"Entity=(e-x-1-", b"Entity=(e-x-2-", 1)
        ambiguous = ambiguous.replace(b"2\tB\t_\tVERB\t_\t_\t0\troot", b"2\tB\t_\tVERB\t_\t_\t3\tdep")
        ambiguous = ambiguous.replace(b"3\tC\t_\tNOUN\t_\t_\t2\tdep", b"3\tC\t_\tNOUN\t_\t_\t0\troot")
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaisesRegex(audit.AuditError, "policies disagree"):
                audit.transform_heads(ambiguous, Path(tmp), audit.load_backend())

    @unittest.skipUnless(os.environ.get("COREFUD_SCORER"), "COREFUD_SCORER not configured")
    def test_real_scorer_exact_is_invariant_and_head_is_corrected(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            changed, _ = audit.transform_heads(SOURCE, root, audit.load_backend())
            before, after = root / "before.conllu", root / "after.conllu"
            reference = root / "reference.conllu"
            before.write_bytes(SOURCE)
            after.write_bytes(changed)
            reference.write_bytes(SOURCE.replace(b"Entity=(e-x-1-", b"Entity=(e-x-2-", 1))
            scorer = Path(os.environ["COREFUD_SCORER"])
            python = Path(os.environ.get("COREFUD_SCORER_PYTHON", sys.executable))
            scores = {}
            for name, path in (("before", before), ("after", after)):
                for mode in ("head", "exact"):
                    scores[name, mode] = audit.score(python, scorer, reference, path, mode, root)
                    self.assertEqual(scores[name, mode]["exit_code"], 0)
                    self.assertEqual(scores[name, mode]["stderr_bytes"], 0)
            self.assertEqual(scores["before", "exact"]["conll"], 100.0)
            self.assertEqual(scores["after", "exact"]["conll"], 100.0)
            self.assertEqual(scores["before", "head"]["conll"], 25.0)
            self.assertEqual(scores["after", "head"]["conll"], 100.0)


if __name__ == "__main__":
    unittest.main()

"""Regression checks for synthetic count aggregation and paired bootstrap."""

import argparse
import importlib.util
import math
from pathlib import Path
import sys
import unittest

SCRIPT = Path(__file__).with_name("audit_bootstrap_counts.py")
SPEC = importlib.util.spec_from_file_location("audit_bootstrap_counts", SCRIPT)
AUDIT = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(AUDIT)


class BootstrapCountsTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.result = AUDIT.audit(ARGS.scorer_root)

    def test_macro_is_not_corpus(self):
        self.assertAlmostEqual(self.result["macro_document_f1_a"], 0.5166666666666667)
        self.assertAlmostEqual(self.result["corpus_f1"]["a"], 10 / 13)
        self.assertEqual(f'{self.result["macro_document_f1_a"]:.6f}', "0.516667")
        self.assertEqual(f'{self.result["corpus_f1"]["a"]:.6f}', "0.769231")

    def test_ten_thousand_paired_draws(self):
        bootstrap = self.result["paired_bootstrap"]
        self.assertEqual(bootstrap["samples"], 10000)
        self.assertTrue(bootstrap["same_document_indices_for_both_systems"])
        self.assertTrue(bootstrap["all_count_reference_checks_passed"])
        self.assertLess(bootstrap["max_f1_reference_error"], 1e-14)
        self.assertGreater(bootstrap["percentile_95_delta_order_statistics"][0], 0)
        self.assertEqual(AUDIT.audit(ARGS.scorer_root)["paired_bootstrap"], bootstrap)

    def test_fractional_counts_and_repeated_documents(self):
        evaluator, _, _ = AUDIT.load_scorer(ARGS.scorer_root)
        selected = (0, 0, 2)
        counts, score = AUDIT.aggregate(evaluator, AUDIT.SYSTEM_A, selected)
        reference = tuple(math.fsum(AUDIT.SYSTEM_A[i][j] for i in selected) for j in range(4))
        for actual, expected in zip(counts, reference):
            self.assertAlmostEqual(actual, expected, places=14)
        self.assertAlmostEqual(score, AUDIT.independent_f1(reference), places=14)
        rounded = tuple(sum(round(AUDIT.SYSTEM_A[i][j], 2) for i in selected) for j in range(4))
        self.assertGreater(abs(score - AUDIT.independent_f1(rounded)), 1e-6)

    def test_zero_denominators(self):
        evaluator, _, _ = AUDIT.load_scorer(ARGS.scorer_root)
        counts, score = AUDIT.aggregate(evaluator, ((0, 0, 0, 0),), (0, 0, 0))
        self.assertEqual(counts, (0, 0, 0, 0))
        self.assertEqual(score, 0)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--scorer-root", type=Path, required=True)
    ARGS = parser.parse_args()
    unittest.main(argv=[sys.argv[0]], verbosity=2)

"""Smoke tests for internal metrics, bootstrap, parsers, and baselines."""

from __future__ import annotations

import unittest

from src.baselines.head_match import HeadMatchBaseline
from src.baselines.mention_pair import MentionPairLogisticBaseline
from src.eval.istotnosc import bootstrap_score
from src.eval.metrics import evaluate_partition
from src.eval.official import parse_mention_output, parse_official_output


class EvaluationTest(unittest.TestCase):
    def test_identical_partition_scores_one(self) -> None:
        clusters = [["a", "b"], ["c", "d"]]
        scores = evaluate_partition(clusters, clusters)
        for name in ("muc", "b_cubed", "ceafe", "lea", "blanc"):
            self.assertAlmostEqual(scores[name]["f1"], 1.0)
        self.assertAlmostEqual(scores["conll_f1"], 1.0)

    def test_bootstrap_is_deterministic(self) -> None:
        documents = [
            {"gold_clusters": [["a", "b"]], "predicted_clusters": [["a", "b"]]},
            {"gold_clusters": [["a", "b"]], "predicted_clusters": [["a"], ["b"]]},
        ]
        metric = lambda docs: float(
            sum(len(doc["predicted_clusters"][0]) > 1 for doc in docs) / len(docs)
        )
        first = bootstrap_score(documents, metric, samples=100, seed=7)
        second = bootstrap_score(documents, metric, samples=100, seed=7)
        self.assertEqual(first, second)

    def test_official_output_parser(self) -> None:
        output = "\n".join(
            [
                "muc", "Recall: 80.00  Precision: 70.00  F1: 74.67",
                "bcub", "Recall: 81.00  Precision: 71.00  F1: 75.67",
                "ceafe", "Recall: 82.00  Precision: 72.00  F1: 76.67",
                "lea", "Recall: 83.00  Precision: 73.00  F1: 77.67",
                "blanc", "Recall: 84.00  Precision: 74.00  F1: 78.67",
                "CoNLL score: 75.67",
            ]
        )
        parsed = parse_official_output(output)
        self.assertAlmostEqual(parsed["conll_f1"], 0.7567)
        mention = parse_mention_output("mention\nRecall: 90.00  Precision: 80.00  F1: 84.71")
        self.assertAlmostEqual(mention["f1"], 0.8471)

    def test_rule_and_logistic_baselines(self) -> None:
        mentions = [
            {"id": "m1", "lemma": "sąd", "head": "Sąd", "index": 0, "sentence": 0},
            {"id": "m2", "lemma": "sąd", "head": "sądu", "index": 3, "sentence": 1},
            {"id": "m3", "lemma": "powód", "head": "powód", "index": 5, "sentence": 1},
        ]
        self.assertEqual(HeadMatchBaseline().predict(mentions)[0], ["m1", "m2"])
        pairs = [
            (mentions[0], mentions[1]),
            (mentions[0], mentions[2]),
            (mentions[1], mentions[2]),
        ]
        model = MentionPairLogisticBaseline(threshold=0.4).fit(pairs, [1, 0, 0])
        predicted = model.predict(mentions)
        self.assertEqual({item for cluster in predicted for item in cluster}, {"m1", "m2", "m3"})


if __name__ == "__main__":
    unittest.main()

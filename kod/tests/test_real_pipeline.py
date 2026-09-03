"""Small deterministic checks for the real-data pipeline."""

from __future__ import annotations

import unittest

import torch

from scripts.evaluate_corefud_model import clusters_from_probabilities, pairwise_score
from src.data.tensorization import split_training_documents


class RealPipelineTest(unittest.TestCase):
    def test_document_split_has_no_overlap(self) -> None:
        documents = [{"doc_id": f"d{index}"} for index in range(20)]
        train, calibration = split_training_documents(documents, 0.2, 17)
        train_ids = {item["doc_id"] for item in train}
        calibration_ids = {item["doc_id"] for item in calibration}
        self.assertFalse(train_ids & calibration_ids)
        self.assertEqual(len(calibration_ids), 4)

    def test_antecedent_decoding_links_only_above_threshold(self) -> None:
        probabilities = torch.tensor(
            [[1.0, 0.9, 0.1], [0.9, 1.0, 0.2], [0.1, 0.2, 1.0]]
        )
        self.assertEqual(clusters_from_probabilities(probabilities, 0.5), [[0, 1], [2]])

    def test_pairwise_score_is_exact_for_matching_partition(self) -> None:
        probabilities = [
            torch.tensor([[1.0, 0.9, 0.1], [0.9, 1.0, 0.2], [0.1, 0.2, 1.0]])
        ]
        metadata = [{"mentions": [{"entity_id": "a"}, {"entity_id": "a"}, {"entity_id": "b"}]}]
        score = pairwise_score(probabilities, metadata, 0.5)
        self.assertEqual(score["f1"], 1.0)


if __name__ == "__main__":
    unittest.main()

"""Smoke tests for all trainable architecture components."""

from __future__ import annotations

import math
import tempfile
import unittest
from pathlib import Path

import torch
import yaml

from src.models import CoreferenceModel, HybridSelector
from train import run_training


class ModelSmokeTest(unittest.TestCase):
    """Exercise model shapes and a 20-example training run."""

    def test_all_variants_preserve_pair_shape(self) -> None:
        batch, mentions, dimension = 2, 7, 32
        mention_embeddings = torch.randn(batch, mentions, dimension)
        pair_features = torch.randn(batch, 3, mentions, mentions)
        matrix_features = torch.randn(batch, 3, mentions, mentions)
        for variant in ("baseline", "dae", "matrix"):
            model = CoreferenceModel(
                variant=variant,
                input_dim=dimension,
                latent_dim=8,
                hidden_dim=16,
                pair_feature_dim=3,
                matrix_channels=3,
                unet_base_channels=8,
            )
            output = model(mention_embeddings, pair_features, matrix_features)
            self.assertEqual(output["logits"].shape, (batch, mentions, mentions))
            self.assertTrue(
                torch.allclose(
                    output["logits"], output["logits"].transpose(1, 2), atol=1e-6
                )
            )

    def test_hybrid_selector_respects_limit(self) -> None:
        logits = torch.zeros(1, 6, 6)
        errors = torch.arange(6, dtype=torch.float32).unsqueeze(0)
        valid = torch.ones(1, 6, dtype=torch.bool)
        selected = HybridSelector(0.2, max_candidates=3).select(logits, errors, valid)
        self.assertEqual(len(selected), 3)

    def test_hybrid_selector_accepts_high_reconstruction_error(self) -> None:
        logits = torch.tensor(
            [[[0.0, 0.0, 0.0], [2.0, 0.0, 0.0], [2.0, 0.0, 0.0]]]
        )
        errors = torch.tensor([[0.0, 0.1, 0.9]])
        valid = torch.ones(1, 3, dtype=torch.bool)
        selected = HybridSelector(
            margin_threshold=0.2,
            max_candidates=3,
            reconstruction_threshold=0.8,
        ).select(logits, errors, valid)
        self.assertEqual([(item.document, item.mention) for item in selected], [(0, 2)])

    def test_training_on_twenty_synthetic_examples(self) -> None:
        config_path = Path(__file__).parents[1] / "configs" / "smoke.yaml"
        config = yaml.safe_load(config_path.read_text(encoding="utf-8"))
        with tempfile.TemporaryDirectory() as temporary:
            output = Path(temporary)
            summary = run_training(config, output)
            self.assertEqual(summary.examples, 20)
            self.assertEqual(summary.variant, "dae")
            self.assertTrue(math.isfinite(summary.final_loss))
            self.assertTrue((output / "model.pt").exists())
            self.assertTrue((output / "summary.json").exists())
            self.assertTrue((output / "train.jsonl").exists())


if __name__ == "__main__":
    unittest.main()

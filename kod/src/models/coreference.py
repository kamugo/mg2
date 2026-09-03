"""Autoencoder-based models for mention-pair coreference experiments."""

from __future__ import annotations

from dataclasses import dataclass

import torch
from torch import Tensor, nn
from torch.nn import functional as F


class DenoisingAutoencoder(nn.Module):
    """Compress mention embeddings and reconstruct their clean representation."""

    def __init__(
        self,
        input_dim: int = 768,
        hidden_dim: int = 384,
        latent_dim: int = 128,
        dropout: float = 0.1,
    ) -> None:
        super().__init__()
        self.encoder = nn.Sequential(
            nn.Linear(input_dim, hidden_dim),
            nn.LayerNorm(hidden_dim),
            nn.GELU(),
            nn.Dropout(dropout),
            nn.Linear(hidden_dim, latent_dim),
            nn.LayerNorm(latent_dim),
        )
        self.decoder = nn.Sequential(
            nn.Linear(latent_dim, hidden_dim),
            nn.LayerNorm(hidden_dim),
            nn.GELU(),
            nn.Dropout(dropout),
            nn.Linear(hidden_dim, input_dim),
        )

    def corrupt(
        self,
        embeddings: Tensor,
        mask_probability: float,
        noise_std: float,
    ) -> Tensor:
        """Apply feature masking and Gaussian noise during training only."""
        if not self.training:
            return embeddings
        keep = torch.rand_like(embeddings) >= mask_probability
        noise = torch.randn_like(embeddings) * noise_std
        return embeddings * keep + noise

    def forward(
        self,
        embeddings: Tensor,
        mask_probability: float = 0.15,
        noise_std: float = 0.01,
    ) -> tuple[Tensor, Tensor]:
        corrupted = self.corrupt(embeddings, mask_probability, noise_std)
        latent = self.encoder(corrupted)
        reconstruction = self.decoder(latent)
        return latent, reconstruction


class PairwiseScorer(nn.Module):
    """Score all mention pairs from latent embeddings and optional pair features."""

    def __init__(self, embedding_dim: int, pair_feature_dim: int, hidden_dim: int) -> None:
        super().__init__()
        input_dim = embedding_dim * 4 + pair_feature_dim
        self.network = nn.Sequential(
            nn.Linear(input_dim, hidden_dim),
            nn.GELU(),
            nn.Dropout(0.1),
            nn.Linear(hidden_dim, 1),
        )

    def forward(self, embeddings: Tensor, pair_features: Tensor) -> Tensor:
        batch, mentions, _ = embeddings.shape
        left = embeddings.unsqueeze(2).expand(-1, -1, mentions, -1)
        right = embeddings.unsqueeze(1).expand(-1, mentions, -1, -1)
        features = pair_features.permute(0, 2, 3, 1)
        pair_repr = torch.cat(
            [left, right, left * right, torch.abs(left - right), features], dim=-1
        )
        logits = self.network(pair_repr).squeeze(-1)
        return (logits + logits.transpose(1, 2)) / 2


class ConvBlock(nn.Module):
    """Two convolutional layers used by the compact U-Net."""

    def __init__(self, input_channels: int, output_channels: int) -> None:
        super().__init__()
        self.layers = nn.Sequential(
            nn.Conv2d(input_channels, output_channels, 3, padding=1),
            nn.GroupNorm(min(8, output_channels), output_channels),
            nn.GELU(),
            nn.Conv2d(output_channels, output_channels, 3, padding=1),
            nn.GroupNorm(min(8, output_channels), output_channels),
            nn.GELU(),
        )

    def forward(self, inputs: Tensor) -> Tensor:
        return self.layers(inputs)


class MatrixUNet(nn.Module):
    """Segment a mention-by-mention feature matrix into coreference edges."""

    def __init__(self, input_channels: int = 8, base_channels: int = 32) -> None:
        super().__init__()
        self.down1 = ConvBlock(input_channels, base_channels)
        self.down2 = ConvBlock(base_channels, base_channels * 2)
        self.bridge = ConvBlock(base_channels * 2, base_channels * 4)
        self.up2 = nn.ConvTranspose2d(
            base_channels * 4, base_channels * 2, kernel_size=2, stride=2
        )
        self.decode2 = ConvBlock(base_channels * 4, base_channels * 2)
        self.up1 = nn.ConvTranspose2d(
            base_channels * 2, base_channels, kernel_size=2, stride=2
        )
        self.decode1 = ConvBlock(base_channels * 2, base_channels)
        self.output = nn.Conv2d(base_channels, 1, kernel_size=1)

    def forward(self, matrix_features: Tensor) -> Tensor:
        size = matrix_features.shape[-1]
        if matrix_features.shape[-2] != size:
            raise ValueError("MatrixUNet requires square mention matrices")
        pad = (-size) % 4
        if pad:
            matrix_features = F.pad(matrix_features, (0, pad, 0, pad))
        level1 = self.down1(matrix_features)
        level2 = self.down2(F.max_pool2d(level1, 2))
        bridge = self.bridge(F.max_pool2d(level2, 2))
        decoded2 = self.decode2(torch.cat([self.up2(bridge), level2], dim=1))
        decoded1 = self.decode1(torch.cat([self.up1(decoded2), level1], dim=1))
        logits = self.output(decoded1)[:, 0, :size, :size]
        return (logits + logits.transpose(1, 2)) / 2


class CoreferenceModel(nn.Module):
    """Run baseline, denoising-autoencoder, or matrix-segmentation variants."""

    def __init__(
        self,
        variant: str,
        input_dim: int,
        latent_dim: int,
        hidden_dim: int,
        pair_feature_dim: int,
        matrix_channels: int,
        unet_base_channels: int = 32,
    ) -> None:
        super().__init__()
        if variant not in {"baseline", "dae", "matrix"}:
            raise ValueError(f"Unsupported variant: {variant}")
        self.variant = variant
        if variant == "matrix":
            self.matrix_model = MatrixUNet(matrix_channels, unet_base_channels)
            self.dae = None
            self.projection = None
            self.scorer = None
        else:
            self.matrix_model = None
            self.dae = (
                DenoisingAutoencoder(input_dim, hidden_dim, latent_dim)
                if variant == "dae"
                else None
            )
            self.projection = (
                None
                if variant == "dae"
                else nn.Sequential(
                    nn.Linear(input_dim, latent_dim),
                    nn.LayerNorm(latent_dim),
                    nn.GELU(),
                )
            )
            self.scorer = PairwiseScorer(latent_dim, pair_feature_dim, hidden_dim)

    def forward(
        self,
        mention_embeddings: Tensor,
        pair_features: Tensor,
        matrix_features: Tensor,
        mask_probability: float = 0.15,
        noise_std: float = 0.01,
    ) -> dict[str, Tensor | None]:
        if self.variant == "matrix":
            return {
                "logits": self.matrix_model(matrix_features),
                "latent": None,
                "reconstruction": None,
            }
        if self.dae is not None:
            latent, reconstruction = self.dae(
                mention_embeddings, mask_probability, noise_std
            )
        else:
            latent = self.projection(mention_embeddings)
            reconstruction = None
        return {
            "logits": self.scorer(latent, pair_features),
            "latent": latent,
            "reconstruction": reconstruction,
        }


@dataclass(frozen=True)
class Selection:
    """Indices selected for an external LLM decision."""

    document: int
    mention: int
    score_margin: float
    reconstruction_error: float


class HybridSelector:
    """Select a bounded number of uncertain mentions without calling an LLM."""

    def __init__(
        self,
        margin_threshold: float,
        max_candidates: int,
        reconstruction_threshold: float | None = None,
    ) -> None:
        self.margin_threshold = margin_threshold
        self.max_candidates = max_candidates
        self.reconstruction_threshold = reconstruction_threshold

    def select(
        self, logits: Tensor, reconstruction_errors: Tensor, valid_mentions: Tensor
    ) -> list[Selection]:
        selections: list[Selection] = []
        for batch_index in range(logits.shape[0]):
            candidates: list[Selection] = []
            mention_count = int(valid_mentions[batch_index].sum().item())
            for mention_index in range(1, mention_count):
                values = logits[batch_index, mention_index, :mention_index]
                top = torch.topk(values, k=min(2, values.numel())).values
                margin = float(top[0] - top[1]) if top.numel() == 2 else float("inf")
                error = float(reconstruction_errors[batch_index, mention_index])
                high_reconstruction_error = (
                    self.reconstruction_threshold is not None
                    and error > self.reconstruction_threshold
                )
                if margin < self.margin_threshold or high_reconstruction_error:
                    candidates.append(
                        Selection(batch_index, mention_index, margin, error)
                    )
            candidates.sort(key=lambda item: (item.score_margin, -item.reconstruction_error))
            selections.extend(candidates[: self.max_candidates])
        return selections

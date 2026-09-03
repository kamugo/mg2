"""Train comparable coreference variants from a YAML configuration."""

from __future__ import annotations

import argparse
import json
import logging
import os
import random
import time
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

import numpy as np
import torch
import yaml
from torch import Tensor
from torch.nn import functional as F
from torch.utils.data import DataLoader, Dataset

from src.models import CoreferenceModel


LOGGER = logging.getLogger("train")


def set_seed(seed: int, deterministic: bool = True) -> None:
    """Seed Python, NumPy, and PyTorch RNGs."""
    if deterministic:
        os.environ.setdefault("CUBLAS_WORKSPACE_CONFIG", ":4096:8")
    random.seed(seed)
    np.random.seed(seed)
    torch.manual_seed(seed)
    torch.cuda.manual_seed_all(seed)
    if deterministic:
        torch.use_deterministic_algorithms(True, warn_only=True)
        torch.backends.cudnn.benchmark = False


class SyntheticCoreferenceDataset(Dataset[dict[str, Tensor]]):
    """Generate small clustered mention tensors for smoke testing only."""

    def __init__(
        self,
        examples: int,
        max_mentions: int,
        input_dim: int,
        pair_feature_dim: int,
        matrix_channels: int,
        seed: int,
    ) -> None:
        generator = torch.Generator().manual_seed(seed)
        self.items: list[dict[str, Tensor]] = []
        for _ in range(examples):
            mention_count = int(
                torch.randint(4, max_mentions + 1, (1,), generator=generator).item()
            )
            cluster_count = max(2, mention_count // 3)
            labels = torch.randint(
                cluster_count, (mention_count,), generator=generator
            )
            prototypes = torch.randn(cluster_count, input_dim, generator=generator)
            embeddings = torch.zeros(max_mentions, input_dim)
            embeddings[:mention_count] = (
                prototypes[labels]
                + 0.15 * torch.randn(mention_count, input_dim, generator=generator)
            )
            valid = torch.zeros(max_mentions, dtype=torch.bool)
            valid[:mention_count] = True
            target = torch.zeros(max_mentions, max_mentions)
            target[:mention_count, :mention_count] = (
                labels[:, None] == labels[None, :]
            ).float()
            pair_features = torch.randn(
                pair_feature_dim, max_mentions, max_mentions, generator=generator
            ) * 0.1
            similarity = F.cosine_similarity(
                embeddings.unsqueeze(1), embeddings.unsqueeze(0), dim=-1
            )
            if pair_feature_dim:
                pair_features[0] = similarity
            matrix_features = torch.randn(
                matrix_channels, max_mentions, max_mentions, generator=generator
            ) * 0.1
            matrix_features[0] = similarity
            self.items.append({
                "mention_embeddings": embeddings,
                "pair_features": pair_features,
                "matrix_features": matrix_features,
                "target": target,
                "valid_mentions": valid,
            })

    def __len__(self) -> int:
        return len(self.items)

    def __getitem__(self, index: int) -> dict[str, Tensor]:
        return self.items[index]


class TensorFileDataset(Dataset[dict[str, Tensor]]):
    """Load precomputed document tensors from a trusted local PyTorch file."""

    def __init__(self, path: Path) -> None:
        data = torch.load(path, map_location="cpu", weights_only=True)
        if not isinstance(data, list) or not data:
            raise ValueError("Tensor dataset must be a non-empty list of dictionaries")
        self.items = data

    def __len__(self) -> int:
        return len(self.items)

    def __getitem__(self, index: int) -> dict[str, Tensor]:
        return self.items[index]


def pair_mask(valid_mentions: Tensor) -> Tensor:
    """Return valid non-diagonal unordered mention pairs."""
    count = valid_mentions.shape[1]
    lower = torch.tril(
        torch.ones(count, count, dtype=torch.bool, device=valid_mentions.device),
        diagonal=-1,
    )
    return (
        valid_mentions.unsqueeze(2)
        & valid_mentions.unsqueeze(1)
        & lower.unsqueeze(0)
    )


def edge_loss(logits: Tensor, targets: Tensor, mask: Tensor, positive_weight: float) -> Tensor:
    """Compute weighted binary cross entropy over valid mention pairs."""
    if not mask.any():
        raise ValueError("A batch contains no valid mention pairs")
    weights = torch.where(
        targets[mask] > 0,
        torch.full_like(targets[mask], positive_weight),
        torch.ones_like(targets[mask]),
    )
    return F.binary_cross_entropy_with_logits(
        logits[mask], targets[mask], weight=weights
    )


def dice_loss(logits: Tensor, targets: Tensor, mask: Tensor) -> Tensor:
    """Compute soft Dice loss over valid mention pairs."""
    probabilities = torch.sigmoid(logits[mask])
    gold = targets[mask]
    numerator = 2 * (probabilities * gold).sum() + 1.0
    denominator = probabilities.sum() + gold.sum() + 1.0
    return 1 - numerator / denominator


def transitivity_loss(logits: Tensor, valid_mentions: Tensor) -> Tensor:
    """Penalize soft two-edge paths whose closing edge is unlikely."""
    probabilities = torch.sigmoid(logits)
    path = probabilities.unsqueeze(3) * probabilities.unsqueeze(1)
    violation = path * (1 - probabilities.unsqueeze(2))
    triple_mask = (
        valid_mentions[:, :, None, None]
        & valid_mentions[:, None, :, None]
        & valid_mentions[:, None, None, :]
    )
    return violation[triple_mask].mean()


def reconstruction_loss(
    reconstruction: Tensor, embeddings: Tensor, valid_mentions: Tensor
) -> Tensor:
    """Combine L1 and cosine reconstruction losses over real mentions."""
    valid = valid_mentions.unsqueeze(-1).expand_as(embeddings)
    l1 = F.l1_loss(reconstruction[valid], embeddings[valid])
    cosine = 1 - F.cosine_similarity(reconstruction, embeddings, dim=-1)
    return l1 + cosine[valid_mentions].mean()


def build_dataset(config: dict[str, Any]) -> Dataset[dict[str, Tensor]]:
    data = config["data"]
    model = config["model"]
    if data.get("synthetic", False):
        return SyntheticCoreferenceDataset(
            examples=int(data["examples"]),
            max_mentions=int(data["max_mentions"]),
            input_dim=int(model["input_dim"]),
            pair_feature_dim=int(model["pair_feature_dim"]),
            matrix_channels=int(model["matrix_channels"]),
            seed=int(data.get("seed", config["seed"])),
        )
    path = Path(data["tensor_file"])
    return TensorFileDataset(path)


@dataclass
class TrainingSummary:
    """Persisted measurements from a completed training run."""

    variant: str
    seed: int
    examples: int
    epochs: int
    trainable_parameters: int
    final_loss: float
    device: str
    peak_gpu_memory_bytes: int | None
    synthetic_data: bool
    elapsed_seconds: float


def run_training(config: dict[str, Any], output_dir: Path | None = None) -> TrainingSummary:
    """Train one configured variant and persist logs plus a checkpoint."""
    started_at = time.perf_counter()
    set_seed(int(config["seed"]), bool(config.get("deterministic", True)))
    requested_device = str(config["training"].get("device", "auto"))
    use_cuda = torch.cuda.is_available() and requested_device in {"auto", "cuda"}
    device = torch.device("cuda" if use_cuda else "cpu")
    if use_cuda:
        torch.cuda.reset_peak_memory_stats(device)

    model_config = config["model"]
    model = CoreferenceModel(
        variant=str(model_config["variant"]),
        input_dim=int(model_config["input_dim"]),
        latent_dim=int(model_config["latent_dim"]),
        hidden_dim=int(model_config["hidden_dim"]),
        pair_feature_dim=int(model_config["pair_feature_dim"]),
        matrix_channels=int(model_config["matrix_channels"]),
        unet_base_channels=int(model_config.get("unet_base_channels", 32)),
    ).to(device)
    trainable = sum(parameter.numel() for parameter in model.parameters() if parameter.requires_grad)
    dataset = build_dataset(config)
    generator = torch.Generator().manual_seed(int(config["seed"]))
    loader = DataLoader(
        dataset,
        batch_size=int(config["training"]["batch_size"]),
        shuffle=True,
        generator=generator,
        num_workers=0,
    )
    optimizer = torch.optim.AdamW(
        model.parameters(),
        lr=float(config["training"]["learning_rate"]),
        weight_decay=float(config["training"].get("weight_decay", 0.0)),
    )
    amp_enabled = use_cuda and bool(config["training"].get("mixed_precision", True))
    scaler = torch.amp.GradScaler("cuda", enabled=amp_enabled)
    accumulation = int(config["training"].get("gradient_accumulation", 1))
    epochs = int(config["training"]["epochs"])
    losses: list[float] = []
    target_dir = output_dir or Path(config["output_dir"])
    target_dir.mkdir(parents=True, exist_ok=True)
    log_path = target_dir / "train.jsonl"
    optimizer.zero_grad(set_to_none=True)

    with log_path.open("w", encoding="utf-8") as log_file:
        for epoch in range(epochs):
            model.train()
            for step, batch in enumerate(loader):
                batch = {
                    key: value.to(
                        device=device,
                        dtype=torch.float32 if value.is_floating_point() else value.dtype,
                    )
                    for key, value in batch.items()
                }
                mask = pair_mask(batch["valid_mentions"])
                with torch.amp.autocast("cuda", enabled=amp_enabled):
                    output = model(
                        batch["mention_embeddings"],
                        batch["pair_features"],
                        batch["matrix_features"],
                        float(config["loss"].get("mask_probability", 0.15)),
                        float(config["loss"].get("noise_std", 0.01)),
                    )
                    logits = output["logits"]
                    loss = edge_loss(
                        logits,
                        batch["target"],
                        mask,
                        float(config["loss"].get("positive_weight", 2.0)),
                    )
                    if model.variant == "matrix":
                        loss = (
                            loss
                            + float(config["loss"].get("dice_weight", 0.2))
                            * dice_loss(logits, batch["target"], mask)
                            + float(config["loss"].get("transitivity_weight", 0.05))
                            * transitivity_loss(logits, batch["valid_mentions"])
                        )
                    if output["reconstruction"] is not None:
                        loss = loss + float(config["loss"].get("reconstruction_weight", 0.1)) * reconstruction_loss(
                            output["reconstruction"],
                            batch["mention_embeddings"],
                            batch["valid_mentions"],
                        )
                    scaled_loss = loss / accumulation
                scaler.scale(scaled_loss).backward()
                if (step + 1) % accumulation == 0 or step + 1 == len(loader):
                    scaler.unscale_(optimizer)
                    torch.nn.utils.clip_grad_norm_(
                        model.parameters(),
                        float(config["training"].get("max_grad_norm", 1.0)),
                    )
                    scaler.step(optimizer)
                    scaler.update()
                    optimizer.zero_grad(set_to_none=True)
                value = float(loss.detach().cpu())
                losses.append(value)
                record = {"epoch": epoch + 1, "step": step + 1, "loss": value}
                log_file.write(json.dumps(record) + "\n")
                LOGGER.info("epoch=%s step=%s loss=%.6f", epoch + 1, step + 1, value)

    checkpoint = {
        "model_state": model.state_dict(),
        "model_config": model_config,
        "seed": int(config["seed"]),
    }
    torch.save(checkpoint, target_dir / "model.pt")
    summary = TrainingSummary(
        variant=model.variant,
        seed=int(config["seed"]),
        examples=len(dataset),
        epochs=epochs,
        trainable_parameters=trainable,
        final_loss=losses[-1],
        device=str(device),
        peak_gpu_memory_bytes=(
            int(torch.cuda.max_memory_allocated(device)) if use_cuda else None
        ),
        synthetic_data=bool(config["data"].get("synthetic", False)),
        elapsed_seconds=time.perf_counter() - started_at,
    )
    (target_dir / "summary.json").write_text(
        json.dumps(asdict(summary), ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    return summary


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, required=True)
    args = parser.parse_args()
    config = yaml.safe_load(args.config.read_text(encoding="utf-8"))
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
    )
    summary = run_training(config)
    print(json.dumps(asdict(summary), ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

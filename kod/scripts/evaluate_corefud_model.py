"""Tune antecedent threshold and score a trained model on held-out CorefUD windows."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

import torch
from torch.utils.data import DataLoader

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.eval.official import run_official_scorer  # noqa: E402
from src.models import CoreferenceModel  # noqa: E402
from train import TensorFileDataset  # noqa: E402


class UnionFind:
    def __init__(self, size: int) -> None:
        self.parent = list(range(size))

    def find(self, item: int) -> int:
        while self.parent[item] != item:
            self.parent[item] = self.parent[self.parent[item]]
            item = self.parent[item]
        return item

    def union(self, first: int, second: int) -> None:
        left, right = self.find(first), self.find(second)
        if left != right:
            self.parent[right] = left


def read_metadata(path: Path) -> list[dict[str, Any]]:
    with path.open(encoding="utf-8") as source:
        return [json.loads(line) for line in source if line.strip()]


def load_model(checkpoint_path: Path, device: torch.device) -> CoreferenceModel:
    checkpoint = torch.load(checkpoint_path, map_location="cpu", weights_only=True)
    config = checkpoint["model_config"]
    model = CoreferenceModel(
        variant=str(config["variant"]),
        input_dim=int(config["input_dim"]),
        latent_dim=int(config["latent_dim"]),
        hidden_dim=int(config["hidden_dim"]),
        pair_feature_dim=int(config["pair_feature_dim"]),
        matrix_channels=int(config["matrix_channels"]),
        unet_base_channels=int(config.get("unet_base_channels", 32)),
    )
    model.load_state_dict(checkpoint["model_state"])
    return model.to(device).eval()


@torch.inference_mode()
def predict_probabilities(
    model: CoreferenceModel, tensor_path: Path, device: torch.device, batch_size: int
) -> list[torch.Tensor]:
    loader = DataLoader(TensorFileDataset(tensor_path), batch_size=batch_size, shuffle=False)
    result: list[torch.Tensor] = []
    amp = device.type == "cuda"
    for batch in loader:
        batch = {
            key: value.to(
                device=device,
                dtype=torch.float32 if value.is_floating_point() else value.dtype,
            )
            for key, value in batch.items()
        }
        with torch.amp.autocast("cuda", enabled=amp):
            output = model(
                batch["mention_embeddings"],
                batch["pair_features"],
                batch["matrix_features"],
                0.0,
                0.0,
            )
        probabilities = torch.sigmoid(output["logits"]).float().cpu()
        counts = batch["valid_mentions"].sum(dim=1).cpu().tolist()
        result.extend(probabilities[row, :count, :count] for row, count in enumerate(counts))
    return result


def clusters_from_probabilities(probabilities: torch.Tensor, threshold: float) -> list[list[int]]:
    """Link every mention to at most one earlier antecedent and take transitive closure."""
    count = probabilities.shape[0]
    union_find = UnionFind(count)
    for later in range(1, count):
        scores = probabilities[later, :later]
        best = int(torch.argmax(scores))
        if float(scores[best]) >= threshold:
            union_find.union(later, best)
    grouped: dict[int, list[int]] = {}
    for mention in range(count):
        grouped.setdefault(union_find.find(mention), []).append(mention)
    return list(grouped.values())


def _links(clusters: list[list[int]]) -> set[tuple[int, int]]:
    return {
        (left, right)
        for cluster in clusters
        for offset, left in enumerate(cluster)
        for right in cluster[offset + 1 :]
    }


def pairwise_score(
    probabilities: list[torch.Tensor], metadata: list[dict[str, Any]], threshold: float
) -> dict[str, float | int]:
    true_positive = false_positive = false_negative = 0
    for matrix, item in zip(probabilities, metadata, strict=True):
        gold_by_entity: dict[str, list[int]] = {}
        for index, mention in enumerate(item["mentions"]):
            gold_by_entity.setdefault(str(mention["entity_id"]), []).append(index)
        gold = _links(list(gold_by_entity.values()))
        predicted = _links(clusters_from_probabilities(matrix, threshold))
        true_positive += len(gold & predicted)
        false_positive += len(predicted - gold)
        false_negative += len(gold - predicted)
    precision = true_positive / (true_positive + false_positive) if true_positive + false_positive else 0.0
    recall = true_positive / (true_positive + false_negative) if true_positive + false_negative else 0.0
    f1 = 2 * precision * recall / (precision + recall) if precision + recall else 0.0
    return {
        "precision": precision,
        "recall": recall,
        "f1": f1,
        "true_positive": true_positive,
        "false_positive": false_positive,
        "false_negative": false_negative,
    }


def tune_threshold(
    probabilities: list[torch.Tensor], metadata: list[dict[str, Any]]
) -> tuple[float, list[dict[str, Any]]]:
    results: list[dict[str, Any]] = []
    thresholds = [integer / 100 for integer in range(20, 86, 5)] + [
        0.90,
        0.92,
        0.94,
        0.96,
        0.98,
    ]
    for threshold in thresholds:
        score = pairwise_score(probabilities, metadata, threshold)
        results.append({"threshold": threshold, **score})
    best = max(results, key=lambda item: (float(item["f1"]), float(item["threshold"])))
    return float(best["threshold"]), results


def write_pseudo_corefud(
    path: Path,
    metadata: list[dict[str, Any]],
    probabilities: list[torch.Tensor] | None,
    threshold: float | None,
) -> None:
    """Write one single-token mention per pseudo-token for official cluster scoring."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="\n") as target:
        for item_index, item in enumerate(metadata):
            mentions = item["mentions"]
            if probabilities is None:
                by_entity: dict[str, list[int]] = {}
                for index, mention in enumerate(mentions):
                    by_entity.setdefault(str(mention["entity_id"]), []).append(index)
                clusters = list(by_entity.values())
            else:
                if threshold is None:
                    raise ValueError("A threshold is required for system output")
                clusters = clusters_from_probabilities(probabilities[item_index], threshold)
            owner = {
                mention: cluster_index + 1
                for cluster_index, cluster in enumerate(clusters)
                for mention in cluster
            }
            doc_id = f"window-{item_index:05d}"
            target.write(f"# newdoc id = {doc_id}\n")
            target.write("# global.Entity = eid-etype-head-other\n")
            target.write(f"# sent_id = {doc_id}-1\n")
            for index, mention in enumerate(mentions, start=1):
                entity = owner[index - 1]
                form = str(mention.get("text", f"M{index}")).replace("\t", " ").replace("\n", " ")
                if not form or form == "_":
                    form = f"M{index}"
                annotation = f"Entity=(e{entity}-entity-1-)"
                target.write(f"{index}\t{form}\t_\tNOUN\t_\t_\t0\tdep\t_\t{annotation}\n")
            target.write("\n")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--checkpoint", type=Path, required=True)
    parser.add_argument("--data-dir", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--batch-size", type=int, default=16)
    parser.add_argument("--device", choices=("auto", "cuda", "cpu"), default="auto")
    args = parser.parse_args()
    use_cuda = torch.cuda.is_available() and args.device in {"auto", "cuda"}
    device = torch.device("cuda" if use_cuda else "cpu")
    model = load_model(args.checkpoint.resolve(), device)
    data_dir, output = args.data_dir.resolve(), args.output.resolve()
    output.mkdir(parents=True, exist_ok=True)

    calibration_metadata = read_metadata(data_dir / "calibration.metadata.jsonl")
    calibration_probabilities = predict_probabilities(
        model, data_dir / "calibration.pt", device, args.batch_size
    )
    threshold, curve = tune_threshold(calibration_probabilities, calibration_metadata)

    dev_metadata = read_metadata(data_dir / "dev.metadata.jsonl")
    dev_probabilities = predict_probabilities(model, data_dir / "dev.pt", device, args.batch_size)
    pairwise = pairwise_score(dev_probabilities, dev_metadata, threshold)
    key_path, system_path = output / "dev.gold.conllu", output / "dev.system.conllu"
    write_pseudo_corefud(key_path, dev_metadata, None, None)
    write_pseudo_corefud(system_path, dev_metadata, dev_probabilities, threshold)
    official, raw = run_official_scorer(
        key_path, system_path, ROOT / "vendor" / "corefud-scorer", match="head"
    )
    (output / "official-scorer.txt").write_text(raw, encoding="utf-8")
    payload = {
        "checkpoint": str(args.checkpoint.resolve()),
        "variant": model.variant,
        "threshold_selected_on_calibration": threshold,
        "calibration_pairwise_curve": curve,
        "dev_pairwise": pairwise,
        "dev_official": official,
        "dev_windows": len(dev_metadata),
        "evaluation_scope": {
            "mention_boundaries": "gold",
            "documents": "non-overlapping windows of at most 48 mentions",
            "official_scorer": "CorefUD scorer on a mention-level projection",
            "domain": "general Polish-PCC, not legal gold",
        },
    }
    (output / "results.json").write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

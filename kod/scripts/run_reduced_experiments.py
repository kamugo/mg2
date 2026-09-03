"""Run E1-E5 on a small synthetic benchmark and score with CorefUD scorer."""

from __future__ import annotations

import argparse
import copy
import json
import os
import platform
import statistics
import sys
import time
from dataclasses import asdict
from pathlib import Path
from typing import Any

import numpy as np
import torch
import yaml

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.baselines import HeadMatchBaseline, MentionPairLogisticBaseline
from src.eval.official import run_official_scorer
from src.models import CoreferenceModel
from train import SyntheticCoreferenceDataset, run_training, set_seed

SEEDS = [20260903, 20260917, 20261001, 20261015, 20261029]


class UnionFind:
    """Minimal deterministic disjoint-set structure for threshold decoding."""

    def __init__(self, size: int) -> None:
        self.parent = list(range(size))

    def find(self, item: int) -> int:
        while self.parent[item] != item:
            self.parent[item] = self.parent[self.parent[item]]
            item = self.parent[item]
        return item

    def union(self, first: int, second: int) -> None:
        first_root, second_root = self.find(first), self.find(second)
        if first_root != second_root:
            self.parent[second_root] = first_root


def target_clusters(target: torch.Tensor, count: int) -> list[list[str]]:
    """Convert a gold adjacency matrix to mention clusters."""
    union_find = UnionFind(count)
    for first in range(count):
        for second in range(first):
            if float(target[first, second]) > 0.5:
                union_find.union(first, second)
    grouped: dict[int, list[str]] = {}
    for index in range(count):
        grouped.setdefault(union_find.find(index), []).append(f"m{index}")
    return list(grouped.values())


def decode_logits(logits: torch.Tensor, count: int, threshold: float = 0.5) -> list[list[str]]:
    """Decode pair probabilities to clusters with transitive closure."""
    probabilities = torch.sigmoid(logits)
    union_find = UnionFind(count)
    for first in range(count):
        for second in range(first):
            if float(probabilities[first, second]) >= threshold:
                union_find.union(first, second)
    grouped: dict[int, list[str]] = {}
    for index in range(count):
        grouped.setdefault(union_find.find(index), []).append(f"m{index}")
    return list(grouped.values())


def dataset(config: dict[str, Any], seed: int, examples: int) -> SyntheticCoreferenceDataset:
    """Build the shared synthetic tensor dataset."""
    model = config["model"]
    return SyntheticCoreferenceDataset(
        examples=examples,
        max_mentions=int(config["data"]["max_mentions"]),
        input_dim=int(model["input_dim"]),
        pair_feature_dim=int(model["pair_feature_dim"]),
        matrix_channels=int(model["matrix_channels"]),
        seed=seed,
    )


def documents_from_dataset(data: SyntheticCoreferenceDataset) -> list[dict[str, object]]:
    """Extract document identifiers, mention counts, and gold partitions."""
    documents = []
    for index, item in enumerate(data.items):
        count = int(item["valid_mentions"].sum())
        documents.append(
            {
                "id": f"synthetic-{index}",
                "count": count,
                "gold_clusters": target_clusters(item["target"], count),
            }
        )
    return documents


def mention_metadata(
    documents: list[dict[str, object]], seed: int, noise: float = 0.3
) -> list[list[dict[str, object]]]:
    """Create reproducible lexical features correlated imperfectly with gold entities."""
    generator = np.random.default_rng(seed)
    all_mentions = []
    for doc_index, document in enumerate(documents):
        owner = {
            mention: cluster_index
            for cluster_index, cluster in enumerate(document["gold_clusters"])
            for mention in cluster
        }
        mentions = []
        for mention_index in range(int(document["count"])):
            mention_id = f"m{mention_index}"
            cluster = owner[mention_id]
            base = f"entity_{cluster}"
            lemma = base if generator.random() >= noise else f"surface_{doc_index}_{mention_index}"
            head = base if generator.random() >= noise else f"head_{doc_index}_{mention_index}"
            mentions.append(
                {
                    "id": mention_id,
                    "lemma": lemma,
                    "head": head,
                    "gender": "m" if cluster % 2 else "f",
                    "number": "sg" if cluster % 3 else "pl",
                    "index": mention_index,
                    "sentence": mention_index // 4,
                }
            )
        all_mentions.append(mentions)
    return all_mentions


def fit_pair_baseline(
    documents: list[dict[str, object]],
    metadata: list[list[dict[str, object]]],
) -> MentionPairLogisticBaseline:
    """Fit E2 from all mention pairs in the synthetic training split."""
    pairs = []
    labels = []
    for document, mentions in zip(documents, metadata):
        owner = {
            mention: cluster_index
            for cluster_index, cluster in enumerate(document["gold_clusters"])
            for mention in cluster
        }
        for later in range(1, len(mentions)):
            for earlier in range(later):
                pairs.append((mentions[earlier], mentions[later]))
                labels.append(int(owner[f"m{earlier}"] == owner[f"m{later}"]))
    return MentionPairLogisticBaseline(threshold=0.5, seed=SEEDS[0]).fit(pairs, labels)


def write_conllu(
    path: Path,
    documents: list[dict[str, object]],
    partition_key: str,
) -> None:
    """Serialize single-token synthetic mentions as aligned CorefUD documents."""
    lines: list[str] = []
    for doc_index, document in enumerate(documents):
        clusters = document[partition_key]
        owner = {
            mention: cluster_index
            for cluster_index, cluster in enumerate(clusters)
            for mention in cluster
        }
        lines.extend(
            [
                f"# newdoc id = reduced-{doc_index}",
                "# global.Entity = eid-etype-head-other",
                f"# sent_id = reduced-{doc_index}-1",
                "# text = " + " ".join(f"m{i}" for i in range(int(document["count"]))),
            ]
        )
        for mention_index in range(int(document["count"])):
            mention_id = f"m{mention_index}"
            cluster_id = owner[mention_id]
            misc = f"Entity=(e{cluster_id}-x-1-)"
            lines.append(
                f"{mention_index + 1}\t{mention_id}\t_\tNOUN\t_\t_\t0\t_\t_\t{misc}"
            )
        lines.append("")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def score_documents(
    experiment: str,
    run_name: str,
    documents: list[dict[str, object]],
    output_root: Path,
    scorer_dir: Path,
) -> dict[str, object]:
    """Persist aligned files and invoke the authoritative scorer."""
    conllu_dir = output_root / "s08-runs" / experiment / run_name
    key_path = conllu_dir / "gold.conllu"
    system_path = conllu_dir / "system.conllu"
    write_conllu(key_path, documents, "gold_clusters")
    write_conllu(system_path, documents, "predicted_clusters")
    scores, raw = run_official_scorer(
        key_path, system_path, scorer_dir, match="head", keep_singletons=False
    )
    return {"scores": scores, "scorer_output": raw}


def classical_experiments(
    train_documents: list[dict[str, object]],
    test_documents: list[dict[str, object]],
    output_root: Path,
    scorer_dir: Path,
) -> list[dict[str, object]]:
    """Run E1 and E2 once because their implementations are deterministic."""
    train_metadata = mention_metadata(train_documents, SEEDS[0])
    test_metadata = mention_metadata(test_documents, SEEDS[0] + 1)
    results = []
    for experiment in ("E1", "E2"):
        start = time.perf_counter()
        if experiment == "E1":
            model = HeadMatchBaseline()
        else:
            model = fit_pair_baseline(train_documents, train_metadata)
        predictions = [model.predict(mentions) for mentions in test_metadata]
        elapsed = time.perf_counter() - start
        evaluated = copy.deepcopy(test_documents)
        for document, predicted in zip(evaluated, predictions):
            document["predicted_clusters"] = predicted
        scored = score_documents(
            experiment, "seed-20260903", evaluated, output_root, scorer_dir
        )
        results.append(
            {
                "experiment": experiment,
                "seed": SEEDS[0],
                "training_and_inference_seconds": elapsed,
                "synthetic_data": True,
                **scored,
            }
        )
    return results


def load_model(config: dict[str, Any], checkpoint_path: Path) -> CoreferenceModel:
    """Restore a trained coreference model from its local checkpoint."""
    model_config = config["model"]
    model = CoreferenceModel(
        variant=str(model_config["variant"]),
        input_dim=int(model_config["input_dim"]),
        latent_dim=int(model_config["latent_dim"]),
        hidden_dim=int(model_config["hidden_dim"]),
        pair_feature_dim=int(model_config["pair_feature_dim"]),
        matrix_channels=int(model_config["matrix_channels"]),
        unet_base_channels=int(model_config.get("unet_base_channels", 32)),
    )
    checkpoint = torch.load(checkpoint_path, map_location="cpu", weights_only=True)
    model.load_state_dict(checkpoint["model_state"])
    model.eval()
    return model


def neural_experiment(
    experiment: str,
    config_path: Path,
    output_root: Path,
    scorer_dir: Path,
) -> list[dict[str, object]]:
    """Run one neural variant for all frozen seeds and score a held-out split."""
    base_config = yaml.safe_load(config_path.read_text(encoding="utf-8"))
    runs = []
    for seed in SEEDS:
        config = copy.deepcopy(base_config)
        config["seed"] = seed
        run_dir = output_root / "s08-runs" / experiment / f"seed-{seed}"
        start = time.perf_counter()
        summary = run_training(config, run_dir)
        training_seconds = time.perf_counter() - start
        model = load_model(config, run_dir / "model.pt")
        test_data = dataset(config, 700002, examples=12)
        test_documents = documents_from_dataset(test_data)
        inference_start = time.perf_counter()
        with torch.inference_mode():
            for document, item in zip(test_documents, test_data.items):
                count = int(document["count"])
                output = model(
                    item["mention_embeddings"].unsqueeze(0),
                    item["pair_features"].unsqueeze(0),
                    item["matrix_features"].unsqueeze(0),
                    0.0,
                    0.0,
                )
                document["predicted_clusters"] = decode_logits(
                    output["logits"][0], count
                )
        inference_seconds = time.perf_counter() - inference_start
        scored = score_documents(
            experiment, f"seed-{seed}", test_documents, output_root, scorer_dir
        )
        runs.append(
            {
                "experiment": experiment,
                "seed": seed,
                "training_seconds": training_seconds,
                "inference_seconds": inference_seconds,
                "training": asdict(summary),
                "synthetic_data": True,
                **scored,
            }
        )
    return runs


def aggregate(experiment: str, runs: list[dict[str, object]]) -> dict[str, object]:
    """Aggregate only values actually emitted by completed runs."""
    conll = [float(run["scores"]["conll_f1"]) for run in runs]
    lea = [float(run["scores"]["lea"]["f1"]) for run in runs]
    return {
        "experiment": experiment,
        "completed_runs": len(runs),
        "conll_f1_mean": statistics.fmean(conll),
        "conll_f1_std": statistics.stdev(conll) if len(conll) > 1 else 0.0,
        "lea_f1_mean": statistics.fmean(lea),
        "lea_f1_std": statistics.stdev(lea) if len(lea) > 1 else 0.0,
    }


def main() -> int:
    """Run and persist the reduced experiment suite."""
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-root", type=Path, default=Path("../wyniki"))
    args = parser.parse_args()
    root = PROJECT_ROOT
    output_root = (root / args.output_root).resolve()
    scorer_dir = root / "vendor" / "corefud-scorer"
    e3_config = yaml.safe_load((root / "configs" / "reduced-e3.yaml").read_text(encoding="utf-8"))
    train_data = dataset(e3_config, 700001, examples=24)
    test_data = dataset(e3_config, 700002, examples=12)
    train_documents = documents_from_dataset(train_data)
    test_documents = documents_from_dataset(test_data)

    all_results: dict[str, list[dict[str, object]]] = {"E1": [], "E2": [], "E3": [], "E4": [], "E5": []}
    classical = classical_experiments(
        train_documents, test_documents, output_root, scorer_dir
    )
    for run in classical:
        all_results[str(run["experiment"])].append(run)
    for experiment, filename in (
        ("E3", "reduced-e3.yaml"),
        ("E4", "reduced-e4.yaml"),
        ("E5", "reduced-e5.yaml"),
    ):
        all_results[experiment] = neural_experiment(
            experiment, root / "configs" / filename, output_root, scorer_dir
        )

    environment = {
        "python": platform.python_version(),
        "platform": platform.platform(),
        "torch": torch.__version__,
        "cuda_available": torch.cuda.is_available(),
        "cuda": torch.version.cuda,
        "gpu": torch.cuda.get_device_name(0) if torch.cuda.is_available() else None,
        "seeds": SEEDS,
        "train_data_seed": 700001,
        "test_data_seed": 700002,
        "train_documents": 24,
        "test_documents": 12,
        "synthetic_data": True,
        "cublas_workspace_config": os.environ.get("CUBLAS_WORKSPACE_CONFIG"),
        "corefud_scorer_revision": "4fd7b0e0c661aeeff88bc60c19ef507b84d1b590",
    }
    for experiment, runs in all_results.items():
        payload = {
            "environment": environment,
            "aggregate": aggregate(experiment, runs),
            "runs": runs,
        }
        path = output_root / f"{experiment}-reduced.json"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
    combined = {
        "environment": environment,
        "aggregates": [
            aggregate(experiment, runs) for experiment, runs in all_results.items()
        ],
    }
    (output_root / "s08-reduced-summary.json").write_text(
        json.dumps(combined, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(combined, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

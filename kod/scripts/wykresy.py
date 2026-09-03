"""Create thesis figures only from persisted reduced-run artifacts.

Every output carries an explicit synthetic-data warning.  The script does not
download data and does not turn smoke-test measurements into research claims.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import torch
import yaml
from sklearn.manifold import TSNE


PROJECT_ROOT = Path(__file__).resolve().parents[1]
REPOSITORY_ROOT = PROJECT_ROOT.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from scripts.run_reduced_experiments import dataset, load_model


def save_figure(figure: plt.Figure, output_dir: Path, stem: str) -> list[str]:
    """Save an editable PDF and a review-friendly PNG."""
    output_dir.mkdir(parents=True, exist_ok=True)
    paths = []
    for extension in ("pdf", "png"):
        path = output_dir / f"{stem}.{extension}"
        figure.savefig(path, dpi=220, bbox_inches="tight")
        paths.append(str(path.resolve()))
    plt.close(figure)
    return paths


def quality_plot(summary_path: Path, output_dir: Path) -> dict[str, object]:
    """Show that autoencoder variants did not beat E3 in the synthetic check."""
    payload = json.loads(summary_path.read_text(encoding="utf-8"))
    selected = [
        row for row in payload["aggregates"] if row["experiment"] in {"E3", "E4", "E5"}
    ]
    labels = [row["experiment"] for row in selected]
    means = np.array([row["conll_f1_mean"] for row in selected]) * 100
    errors = np.array([row["conll_f1_std"] for row in selected]) * 100

    figure, axis = plt.subplots(figsize=(7.2, 4.5))
    colors = ["#4c78a8", "#f58518", "#54a24b"]
    bars = axis.bar(labels, means, yerr=errors, capsize=5, color=colors)
    axis.set_ylabel("CoNLL F1 [%], średnia z 5 seedów")
    axis.set_ylim(70, 100)
    axis.set_title("Na teście syntetycznym E4 i E5 nie przewyższają kontroli E3")
    axis.grid(axis="y", alpha=0.25)
    for bar, value in zip(bars, means):
        axis.text(bar.get_x() + bar.get_width() / 2, value + 1.0, f"{value:.2f}", ha="center")
    figure.text(0.5, 0.01, "DANE SYNTETYCZNE — test integracyjny, nie wynik badawczy", ha="center", color="#9c2f2f")
    figure.tight_layout(rect=(0, 0.05, 1, 1))
    return {
        "thesis": "Na wspólnym teście syntetycznym warianty E4 i E5 nie przewyższają E3.",
        "synthetic_data": True,
        "files": save_figure(figure, output_dir, "s13-jakosc-syntetyczna"),
    }


def entity_labels(target: torch.Tensor, mention_count: int) -> np.ndarray:
    """Recover deterministic entity identifiers from a gold adjacency matrix."""
    representatives = []
    for mention in range(mention_count):
        linked = torch.nonzero(target[mention, :mention_count] > 0.5).flatten()
        representatives.append(int(linked.min().item()))
    unique = {value: index for index, value in enumerate(sorted(set(representatives)))}
    return np.array([unique[value] for value in representatives])


def latent_plot(config_path: Path, checkpoint_path: Path, output_dir: Path) -> dict[str, object]:
    """Visualize DAE codes for one reproducible synthetic document with t-SNE."""
    config = yaml.safe_load(config_path.read_text(encoding="utf-8"))
    model = load_model(config, checkpoint_path)
    test_data = dataset(config, seed=700002, examples=12)
    item = max(test_data.items, key=lambda row: int(row["valid_mentions"].sum()))
    mention_count = int(item["valid_mentions"].sum())
    with torch.inference_mode():
        output = model(
            item["mention_embeddings"].unsqueeze(0),
            item["pair_features"].unsqueeze(0),
            item["matrix_features"].unsqueeze(0),
            0.0,
            0.0,
        )
    latent = output["latent"][0, :mention_count].numpy()
    labels = entity_labels(item["target"], mention_count)
    perplexity = max(2.0, min(5.0, float(mention_count - 1) / 2))
    projection = TSNE(
        n_components=2,
        perplexity=perplexity,
        init="pca",
        learning_rate="auto",
        random_state=20260903,
    ).fit_transform(latent)

    figure, axis = plt.subplots(figsize=(6.2, 5.2))
    scatter = axis.scatter(projection[:, 0], projection[:, 1], c=labels, cmap="tab10", s=75)
    for index, (x_coord, y_coord) in enumerate(projection):
        axis.annotate(f"m{index}", (x_coord, y_coord), xytext=(4, 4), textcoords="offset points")
    axis.set_title("t-SNE kodów DAE zachowuje rozróżnienie encji w wybranym dokumencie")
    axis.set_xlabel("wymiar t-SNE 1")
    axis.set_ylabel("wymiar t-SNE 2")
    axis.grid(alpha=0.18)
    legend = axis.legend(*scatter.legend_elements(), title="Złota encja", loc="best")
    axis.add_artist(legend)
    figure.text(0.5, 0.01, "DANE SYNTETYCZNE — jeden dokument, seed danych 700002", ha="center", color="#9c2f2f")
    figure.tight_layout(rect=(0, 0.05, 1, 1))
    return {
        "thesis": "W wybranym dokumencie syntetycznym kody DAE zachowują rozróżnienie złotych encji.",
        "synthetic_data": True,
        "mentions": mention_count,
        "entities": int(len(set(labels.tolist()))),
        "perplexity": perplexity,
        "files": save_figure(figure, output_dir, "s13-tsne-latent-syntetyczny"),
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--summary", type=Path, default=REPOSITORY_ROOT / "wyniki" / "s08-reduced-summary.json")
    parser.add_argument("--config", type=Path, default=PROJECT_ROOT / "configs" / "reduced-e4.yaml")
    parser.add_argument(
        "--checkpoint",
        type=Path,
        default=REPOSITORY_ROOT / "wyniki" / "s08-runs" / "E4" / "seed-20260903" / "model.pt",
    )
    parser.add_argument("--output-dir", type=Path, default=REPOSITORY_ROOT / "praca" / "rysunki")
    parser.add_argument("--report", type=Path, default=REPOSITORY_ROOT / "wyniki" / "s13-wykresy.json")
    args = parser.parse_args()

    report = {
        "quality": quality_plot(args.summary.resolve(), args.output_dir.resolve()),
        "latent": latent_plot(args.config.resolve(), args.checkpoint.resolve(), args.output_dir.resolve()),
    }
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

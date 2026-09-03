"""Evaluate CorefUD files officially or run a self-contained consistency smoke test."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import yaml

from src.eval.istotnosc import bootstrap_score
from src.eval.metrics import evaluate_documents
from src.eval.official import run_official_scorer


def _synthetic_documents() -> list[dict[str, object]]:
    return [
        {
            "id": "d1",
            "gold_clusters": [["a", "b"], ["c", "d"]],
            "predicted_clusters": [["a", "b", "d"], ["c"]],
        },
        {
            "id": "d2",
            "gold_clusters": [["a", "c"], ["b", "d"]],
            "predicted_clusters": [["a", "c"], ["b"], ["d"]],
        },
        {
            "id": "d3",
            "gold_clusters": [["a", "b", "c"], ["d", "e"]],
            "predicted_clusters": [["a", "b"], ["c"], ["d", "e"]],
        },
    ]


def _write_json(path: Path, payload: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def run(config_path: Path) -> dict[str, object]:
    """Run evaluation selected by a YAML configuration."""
    config = yaml.safe_load(config_path.read_text(encoding="utf-8"))
    root = Path(__file__).resolve().parent
    output_path = (root / config["output"]).resolve()
    mode = config.get("mode", "synthetic")
    if mode == "official":
        scores, raw = run_official_scorer(
            (root / config["key"]).resolve(),
            (root / config["system"]).resolve(),
            (root / config.get("scorer_dir", "vendor/corefud-scorer")).resolve(),
            match=config.get("match", "head"),
            keep_singletons=bool(config.get("keep_singletons", False)),
        )
        payload: dict[str, object] = {
            "authoritative": "official-corefud-scorer",
            "scores": scores,
            "raw_output": raw,
            "config": config,
        }
    elif mode == "synthetic":
        documents = _synthetic_documents()
        scores = evaluate_documents(documents)
        samples = int(config.get("bootstrap_samples", 1000))
        bootstrap = bootstrap_score(
            documents,
            lambda docs: float(evaluate_documents(docs)["conll_f1"]),
            samples=samples,
            seed=int(config.get("seed", 20260903)),
        )
        payload = {
            "authoritative": "internal-consistency-check-only",
            "synthetic_data": True,
            "documents": len(documents),
            "scores": scores,
            "bootstrap_conll_f1": bootstrap,
            "config": config,
        }
    else:
        raise ValueError(f"Unsupported evaluation mode: {mode}")
    _write_json(output_path, payload)
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    return payload


def main() -> int:
    """Parse command-line arguments and execute evaluation."""
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", type=Path, required=True)
    args = parser.parse_args()
    run(args.config)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

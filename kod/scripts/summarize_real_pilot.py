"""Aggregate the immutable artifacts of the real Polish-PCC pilot."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


def load(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--experiment-dir", type=Path, required=True)
    parser.add_argument("--tensor-manifest", type=Path, required=True)
    args = parser.parse_args()
    root = args.experiment_dir.resolve()
    baseline = load(root / "baseline" / "evaluation" / "results.json")
    dae = load(root / "dae" / "evaluation" / "results.json")
    baseline_train = load(root / "baseline" / "summary.json")
    dae_train = load(root / "dae" / "summary.json")
    legal_dae = load(root / "legal" / "DU-2024-1984-dae.json")
    legal_baseline = load(root / "legal" / "DU-2024-1984-baseline.json")
    names = ("muc", "b_cubed", "ceafe", "lea", "blanc")
    differences = {
        "pairwise_f1": dae["dev_pairwise"]["f1"] - baseline["dev_pairwise"]["f1"],
        "conll_f1": dae["dev_official"]["conll_f1"] - baseline["dev_official"]["conll_f1"],
        **{
            f"{name}_f1": dae["dev_official"][name]["f1"]
            - baseline["dev_official"][name]["f1"]
            for name in names
        },
    }
    payload = {
        "status": "completed_real_data_pilot",
        "tensor_manifest": load(args.tensor_manifest.resolve()),
        "training": {"baseline": baseline_train, "dae": dae_train},
        "evaluation": {
            "baseline": {
                "threshold": baseline["threshold_selected_on_calibration"],
                "pairwise": baseline["dev_pairwise"],
                "official": baseline["dev_official"],
            },
            "dae": {
                "threshold": dae["threshold_selected_on_calibration"],
                "pairwise": dae["dev_pairwise"],
                "official": dae["dev_official"],
            },
            "dae_minus_baseline": differences,
            "scope": dae["evaluation_scope"],
        },
        "legal_transfer": {
            "document": "Dz.U. 2024 poz. 1984",
            "dae_non_singleton_chains": legal_dae["non_singleton_chains"],
            "baseline_non_singleton_chains": legal_baseline["non_singleton_chains"],
            "detector": legal_dae["detector"],
            "status": legal_dae["status"],
        },
    }
    target = root / "summary.json"
    target.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

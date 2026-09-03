"""Adapter for the unmodified official CorefUD scorer."""

from __future__ import annotations

import os
import re
import subprocess
import sys
from pathlib import Path

METRIC_NAMES = {
    "muc": "muc",
    "bcub": "b_cubed",
    "ceafe": "ceafe",
    "lea": "lea",
    "blanc": "blanc",
    "mention": "mention_detection",
}


def parse_official_output(output: str) -> dict[str, object]:
    """Parse the stable textual report emitted by the official scorer."""
    scores: dict[str, object] = {}
    current: str | None = None
    score_pattern = re.compile(
        r"Recall:\s*([0-9.]+)\s+Precision:\s*([0-9.]+)\s+F1:\s*([0-9.]+)"
    )
    for line in output.splitlines():
        stripped = line.strip()
        if stripped in METRIC_NAMES:
            current = METRIC_NAMES[stripped]
            continue
        match = score_pattern.search(stripped)
        if match and current:
            recall, precision, f1 = (float(value) / 100.0 for value in match.groups())
            scores[current] = {"precision": precision, "recall": recall, "f1": f1}
            current = None
        if stripped.startswith("CoNLL score:"):
            scores["conll_f1"] = float(stripped.split(":", 1)[1].strip()) / 100.0
    required = {"muc", "b_cubed", "ceafe", "lea", "blanc", "conll_f1"}
    missing = required - set(scores)
    if missing:
        raise ValueError(f"Official scorer output misses fields: {sorted(missing)}")
    return scores


def run_official_scorer(
    key_file: Path,
    system_file: Path,
    scorer_dir: Path,
    match: str = "head",
    keep_singletons: bool = False,
) -> tuple[dict[str, object], str]:
    """Run the pinned official script without importing or modifying its code."""
    script = scorer_dir / "corefud-scorer.py"
    if not script.is_file():
        raise FileNotFoundError(
            f"Missing official scorer at {script}. Run scripts/pobierz_scorer.py."
        )
    command = [
        sys.executable,
        str(script),
        str(key_file),
        str(system_file),
        "-m",
        "muc",
        "bcub",
        "ceafe",
        "lea",
        "blanc",
        "-a",
        match,
    ]
    if keep_singletons:
        command.append("-s")
    completed = subprocess.run(
        command,
        cwd=scorer_dir,
        check=True,
        capture_output=True,
        text=True,
        encoding="utf-8",
        env={**os.environ, "PYTHONIOENCODING": "utf-8"},
    )
    scores = parse_official_output(completed.stdout)
    mention_runner = Path(__file__).with_name("ua_mention_runner.py")
    mention_command = [
        sys.executable,
        str(mention_runner),
        str(scorer_dir),
        str(key_file),
        str(system_file),
        "--match",
        match,
    ]
    mention_command.append("--keep-singletons")
    mention_completed = subprocess.run(
        mention_command,
        cwd=scorer_dir,
        check=True,
        capture_output=True,
        text=True,
        encoding="utf-8",
        env={**os.environ, "PYTHONIOENCODING": "utf-8"},
    )
    mention_scores = parse_mention_output(mention_completed.stdout)
    scores["mention_detection"] = mention_scores
    raw = completed.stdout + "\n--- mention detection ---\n" + mention_completed.stdout
    return scores, raw


def parse_mention_output(output: str) -> dict[str, float]:
    """Parse mention detection emitted by the scorer's UA entry point."""
    pattern = re.compile(
        r"Recall:\s*([0-9.]+)\s+Precision:\s*([0-9.]+)\s+F1:\s*([0-9.]+)"
    )
    match = pattern.search(output)
    if not match:
        raise ValueError("Official scorer output misses mention detection.")
    recall, precision, f1 = (float(value) / 100.0 for value in match.groups())
    return {"precision": precision, "recall": recall, "f1": f1}

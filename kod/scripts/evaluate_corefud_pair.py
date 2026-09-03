"""Evaluate two CorefUD files with the vendored official scorer and save provenance."""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from datetime import UTC, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.eval.official import run_official_scorer


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("key", type=Path)
    parser.add_argument("system", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument("--scorer", type=Path, default=Path("vendor/corefud-scorer"))
    parser.add_argument("--match", choices=("head", "exact", "partial"), default="head")
    parser.add_argument("--keep-singletons", action="store_true")
    parser.add_argument(
        "--interpretation",
        default="Evaluation against a gold key.",
        help="Required semantic caveat stored next to the scores.",
    )
    args = parser.parse_args()
    scores, raw = run_official_scorer(
        args.key.resolve(),
        args.system.resolve(),
        args.scorer.resolve(),
        match=args.match,
        keep_singletons=args.keep_singletons,
    )
    args.output.mkdir(parents=True, exist_ok=True)
    result = {
        "created_at": datetime.now(UTC).isoformat(),
        "key": str(args.key.resolve()),
        "key_sha256": sha256(args.key),
        "system": str(args.system.resolve()),
        "system_sha256": sha256(args.system),
        "match": args.match,
        "keep_singletons": args.keep_singletons,
        "interpretation": args.interpretation,
        "scores": scores,
    }
    (args.output / "results.json").write_text(
        json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    (args.output / "official-scorer.txt").write_text(raw, encoding="utf-8")
    print(json.dumps(scores, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

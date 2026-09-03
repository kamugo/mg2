"""Build frozen-HerBERT mention tensors for a real Polish-PCC experiment."""

from __future__ import annotations

import argparse
import json
import sys
from datetime import UTC, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.data.tensorization import (  # noqa: E402
    HerbertMentionEncoder,
    file_sha256,
    read_jsonl,
    save_tensor_split,
    split_training_documents,
)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--train", type=Path, required=True)
    parser.add_argument("--dev", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--model", default="allegro/herbert-base-cased")
    parser.add_argument("--seed", type=int, default=20260903)
    parser.add_argument("--calibration-fraction", type=float, default=0.15)
    parser.add_argument("--max-mentions", type=int, default=48)
    parser.add_argument("--words-per-segment", type=int, default=192)
    parser.add_argument("--segment-stride", type=int, default=176)
    parser.add_argument("--encoder-batch-size", type=int, default=8)
    parser.add_argument("--document-batch-size", type=int, default=32)
    parser.add_argument("--device", choices=("auto", "cuda", "cpu"), default="auto")
    args = parser.parse_args()

    train_path, dev_path = args.train.resolve(), args.dev.resolve()
    output = args.output.resolve()
    output.mkdir(parents=True, exist_ok=True)
    all_train = read_jsonl(train_path)
    train, calibration = split_training_documents(
        all_train, args.calibration_fraction, args.seed
    )
    dev = read_jsonl(dev_path)
    encoder = HerbertMentionEncoder(
        args.model,
        device=args.device,
        words_per_segment=args.words_per_segment,
        segment_stride=args.segment_stride,
        batch_size=args.encoder_batch_size,
    )
    summaries: dict[str, dict[str, int]] = {}
    for name, documents in (("train", train), ("calibration", calibration), ("dev", dev)):
        summaries[name] = save_tensor_split(
            documents,
            encoder,
            output / f"{name}.pt",
            output / f"{name}.metadata.jsonl",
            args.max_mentions,
            args.document_batch_size,
        )
        print(name, summaries[name], flush=True)
    manifest = {
        "created_at": datetime.now(UTC).isoformat(),
        "seed": args.seed,
        "calibration_fraction": args.calibration_fraction,
        "max_mentions": args.max_mentions,
        "words_per_segment": args.words_per_segment,
        "segment_stride": args.segment_stride,
        "encoder_batch_size": args.encoder_batch_size,
        "document_batch_size": args.document_batch_size,
        "encoder": args.model,
        "encoder_revision": encoder.revision,
        "encoder_frozen": True,
        "input_sha256": {
            "train": file_sha256(train_path),
            "dev": file_sha256(dev_path),
        },
        "splits": summaries,
        "evaluation_scope": "gold mentions; clustering in non-overlapping mention windows",
    }
    (output / "manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(json.dumps(manifest, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

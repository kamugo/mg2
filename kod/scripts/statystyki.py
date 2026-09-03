"""Compute corpus statistics from the project's document-level JSONL format."""

from __future__ import annotations

import argparse
import json
import statistics
from collections import Counter
from pathlib import Path
from typing import Iterable


def iter_documents(paths: Iterable[Path]) -> Iterable[dict[str, object]]:
    """Yield JSON objects from one or more JSONL files."""
    for path in paths:
        with path.open("r", encoding="utf-8") as stream:
            for line_number, line in enumerate(stream, start=1):
                if line.strip():
                    try:
                        yield json.loads(line)
                    except json.JSONDecodeError as exc:
                        raise ValueError(f"{path}:{line_number}: invalid JSON") from exc


def compute(paths: list[Path]) -> dict[str, object]:
    """Aggregate counts without inventing values for absent data."""
    docs = list(iter_documents(paths))
    if not docs:
        raise ValueError("No documents found; provide non-empty JSONL files")
    token_counts = [len(doc.get("tokens", [])) for doc in docs]
    mention_counts = [len(doc.get("mentions", [])) for doc in docs]
    clusters_per_doc: list[int] = []
    zero_mentions = 0
    sources: Counter[str] = Counter()
    for doc in docs:
        mentions = doc.get("mentions", [])
        entity_ids = {
            mention.get("entity_id")
            for mention in mentions
            if isinstance(mention, dict) and mention.get("entity_id") is not None
        }
        clusters_per_doc.append(len(entity_ids))
        zero_mentions += sum(
            bool(mention.get("is_empty"))
            for mention in mentions
            if isinstance(mention, dict)
        )
        sources[str(doc.get("source", "unknown"))] += 1
    return {
        "files": [str(path) for path in paths],
        "documents": len(docs),
        "tokens": sum(token_counts),
        "mentions": sum(mention_counts),
        "clusters": sum(clusters_per_doc),
        "zero_mentions": zero_mentions,
        "mean_tokens_per_document": statistics.fmean(token_counts),
        "median_tokens_per_document": statistics.median(token_counts),
        "mean_mentions_per_document": statistics.fmean(mention_counts),
        "documents_by_source": dict(sorted(sources.items())),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("inputs", type=Path, nargs="+")
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    stats = compute(args.inputs)
    rendered = json.dumps(stats, ensure_ascii=False, indent=2)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(rendered + "\n", encoding="utf-8")
    print(rendered)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

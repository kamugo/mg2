"""Create split/review artifacts and audit the completed legal silver corpus."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import sys
from collections import Counter
from datetime import UTC, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.prepare_corpipe_legal_pilot import document_blocks
from src.data.konwersja import parse_conllu


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("directory", type=Path, nargs="?", default=Path("data/processed/legal-silver-400"))
    parser.add_argument("--corpus-name", default="legal-silver-400")
    parser.add_argument("--expected-documents", type=int, default=400)
    args = parser.parse_args()
    root = args.directory.resolve()
    jsonl_path = root / f"{args.corpus_name}.jsonl"
    conllu_path = root / f"{args.corpus_name}.conllu"
    documents = [
        json.loads(line)
        for line in jsonl_path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    blocks = document_blocks(conllu_path.read_text(encoding="utf-8"))
    doc_ids = [str(document["doc_id"]) for document in documents]
    if (
        len(documents) != args.expected_documents
        or len(set(doc_ids)) != args.expected_documents
        or set(doc_ids) != set(blocks)
    ):
        raise RuntimeError(
            f"Expected the same {args.expected_documents} unique documents in JSONL and CoNLL-U"
        )

    parsed = list(parse_conllu(conllu_path.open(encoding="utf-8"), args.corpus_name))
    surface_mentions = sum(
        sum(not bool(mention["is_zero"]) for mention in document["mentions"])
        for document in documents
    )
    parsed_mentions = sum(len(document["mentions"]) for document in parsed)
    if len(parsed) != args.expected_documents or parsed_mentions != surface_mentions:
        raise RuntimeError(
            f"CoNLL-U round-trip mismatch: docs={len(parsed)}, mentions={parsed_mentions}/{surface_mentions}"
        )

    split_dir = root / "splits"
    split_dir.mkdir(parents=True, exist_ok=True)
    split_counts: Counter[str] = Counter()
    for split in ("train", "dev", "test"):
        selected = [document for document in documents if document["split"] == split]
        split_counts[split] = len(selected)
        (split_dir / f"{split}.jsonl").write_text(
            "".join(json.dumps(document, ensure_ascii=False) + "\n" for document in selected),
            encoding="utf-8",
        )
        (split_dir / f"{split}.conllu").write_text(
            "".join(blocks[str(document["doc_id"])] for document in selected),
            encoding="utf-8",
        )
    if sum(split_counts.values()) != args.expected_documents or not all(
        split_counts[split] for split in ("train", "dev", "test")
    ):
        raise RuntimeError(f"Unexpected split: {dict(split_counts)}")

    mention_rows: list[dict[str, object]] = []
    split_order = {"test": 0, "dev": 1, "train": 2}
    for document in sorted(documents, key=lambda item: (split_order[str(item["split"])], str(item["doc_id"]))):
        clusters = {cluster["cluster_id"]: cluster for cluster in document["clusters"]}
        text = str(document["text"])
        for mention in document["mentions"]:
            start = mention["start_char"]
            end = mention["end_char"]
            if start is None:
                context = "[ZERO]"
            else:
                left, right = max(0, int(start) - 90), min(len(text), int(end) + 90)
                context = ("…" if left else "") + " ".join(text[left:right].split()) + ("…" if right < len(text) else "")
            cluster = clusters[str(mention["cluster_id"])]
            mention_rows.append({
                "doc_id": document["doc_id"],
                "split": document["split"],
                "mention_id": mention["mention_id"],
                "proposed_cluster_id": mention["cluster_id"],
                "cluster_size": len(cluster["mention_ids"]),
                "review_priority_band": cluster["review_priority_band"],
                "text": mention["text"],
                "start_token": mention["start_token"],
                "end_token": mention["end_token"],
                "start_char": start,
                "end_char": end,
                "context": context,
                "mention_valid": "",
                "corrected_cluster_id": "",
                "corrected_start_token": "",
                "corrected_end_token": "",
                "reviewer_note": "",
            })
    mention_path = root / "review_mentions.csv"
    with mention_path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(mention_rows[0]))
        writer.writeheader()
        writer.writerows(mention_rows)

    validation = {
        "created_at": datetime.now(UTC).isoformat(),
        "status": "passed",
        "documents": len(documents),
        "unique_document_ids": len(set(doc_ids)),
        "split_documents": dict(split_counts),
        "sentences": sum(int(document["stats"]["sentences"]) for document in documents),
        "tokens": sum(int(document["stats"]["tokens"]) for document in documents),
        "clusters": sum(int(document["stats"]["clusters"]) for document in documents),
        "mentions": sum(int(document["stats"]["mentions"]) for document in documents),
        "surface_mentions": surface_mentions,
        "zero_mentions": sum(int(document["stats"]["zero_mentions"]) for document in documents),
        "conllu_roundtrip_mentions": parsed_mentions,
        "replacement_characters": sum(str(document["text"]).count("\ufffd") for document in documents),
    }
    (root / "validation.json").write_text(
        json.dumps(validation, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )

    manifest_path = root / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    artifacts = [
        jsonl_path, conllu_path, mention_path, root / "review_chains.csv",
        root / "review_documents.csv", root / "validation.json",
        *(split_dir / f"{split}.{extension}" for split in ("train", "dev", "test") for extension in ("jsonl", "conllu")),
    ]
    corpipe_output = root / "corpipe26" / "corpipe26-silver.conllu"
    if corpipe_output.exists():
        artifacts.append(corpipe_output)
    manifest["finalized_at"] = datetime.now(UTC).isoformat()
    manifest["validation"] = validation
    manifest["outputs"] = [
        {
            "file": str(path.relative_to(root)).replace("\\", "/"),
            "bytes": path.stat().st_size,
            "sha256": sha256(path),
        }
        for path in artifacts
    ]
    manifest_path.write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(json.dumps(validation, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

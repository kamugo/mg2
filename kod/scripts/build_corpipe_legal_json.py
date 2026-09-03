"""Enrich CorPipe legal predictions and calculate per-chain Stanza agreement."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import sys
from collections import defaultdict
from datetime import UTC, datetime
from itertools import combinations
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.prepare_corpipe_legal_pilot import document_blocks
from src.data.konwersja import parse_conllu


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def coordinate(document: dict[str, Any], mention: dict[str, Any]) -> tuple[int, str, str]:
    start = document["tokens"][int(mention["start"])]
    end = document["tokens"][int(mention["end"]) - 1]
    return int(start["sentence_id"]), str(start["conllu_id"]), str(end["conllu_id"])


def surface_text(document: dict[str, Any], mention: dict[str, Any]) -> str:
    return " ".join(
        str(token["form"])
        for token in document["tokens"][int(mention["start"]):int(mention["end"])]
        if not token["is_empty"]
    ) or "_"


def agreement_band(overlap: float, pair_agreement: float | None, size: int) -> str:
    if size == 1:
        return "singleton-supported" if overlap == 1.0 else "singleton-unsupported"
    if overlap >= 0.999 and (pair_agreement is None or pair_agreement >= 0.999):
        return "high"
    if overlap >= 0.5 and (pair_agreement is None or pair_agreement >= 0.5):
        return "medium"
    return "low"


def write_csv(path: Path, rows: list[dict[str, object]]) -> None:
    with path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def review_sample(rows: list[dict[str, object]], per_band: int = 20) -> list[dict[str, object]]:
    result: list[dict[str, object]] = []
    global_seen_docs: set[str] = set()
    for band in ("low", "medium", "high", "singleton-unsupported", "singleton-supported"):
        candidates = [row for row in rows if row["agreement_band"] == band]
        chosen: list[dict[str, object]] = []
        seen_docs: set[str] = set()
        for row in candidates:
            doc_id = str(row["doc_id"])
            if doc_id not in seen_docs and doc_id not in global_seen_docs:
                chosen.append(row)
                seen_docs.add(doc_id)
                global_seen_docs.add(doc_id)
            if len(chosen) == per_band:
                break
        if len(chosen) < per_band:
            used = {(row["doc_id"], row["cluster_id"]) for row in chosen}
            chosen.extend(
                row for row in candidates
                if (row["doc_id"], row["cluster_id"]) not in used
            )
        result.extend(chosen[:per_band])
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--corpipe", type=Path, required=True)
    parser.add_argument("--stanza", type=Path, required=True)
    parser.add_argument("--stanza-jsonl", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--model", type=Path, required=True)
    parser.add_argument("--segment", type=int, default=1024)
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=True)

    corpipe_docs = {
        str(doc["doc_id"]): doc
        for doc in parse_conllu(args.corpipe.open(encoding="utf-8"), "CorPipe 26")
    }
    stanza_docs = {
        str(doc["doc_id"]): doc
        for doc in parse_conllu(args.stanza.open(encoding="utf-8"), "Stanza")
    }
    rich_docs = {
        str(doc["doc_id"]): doc
        for doc in (
            json.loads(line)
            for line in args.stanza_jsonl.read_text(encoding="utf-8").splitlines()
            if line.strip()
        )
    }
    if not corpipe_docs or not (set(corpipe_docs) == set(stanza_docs) == set(rich_docs)):
        raise RuntimeError(
            "CorPipe, Stanza and rich JSONL must contain the same non-empty set of documents"
        )

    output_docs: list[dict[str, Any]] = []
    chain_rows: list[dict[str, object]] = []
    mention_rows: list[dict[str, object]] = []
    band_counts: defaultdict[str, int] = defaultdict(int)
    total_cp_surface = total_stanza = total_common = 0
    agreed_pairs = comparable_pairs = 0
    split_order = {"test": 0, "dev": 1, "train": 2}

    for doc_id, rich in sorted(rich_docs.items(), key=lambda item: (split_order[item[1]["split"]], item[0])):
        cp = corpipe_docs[doc_id]
        stanza = stanza_docs[doc_id]
        stanza_entities = {
            coordinate(stanza, mention): str(mention["entity_id"])
            for mention in stanza["mentions"]
            if not mention["is_empty"]
        }
        total_stanza += len(stanza_entities)
        cp_groups: dict[str, list[dict[str, Any]]] = defaultdict(list)

        rich_coord = {
            (int(token["sentence_index"]) + 1, str(token["id_in_sentence"])): token
            for token in rich["tokens"]
        }
        enriched_tokens: list[dict[str, Any]] = []
        for token in cp["tokens"]:
            info = rich_coord.get((int(token["sentence_id"]), str(token["conllu_id"])))
            enriched_tokens.append({
                **token,
                "token_index": token["index"],
                "sentence_index": int(token["sentence_id"]) - 1,
                "start_char": info.get("start_char") if info else None,
                "end_char": info.get("end_char") if info else None,
            })

        enriched_mentions: list[dict[str, Any]] = []
        for mention in cp["mentions"]:
            coord = coordinate(cp, mention)
            supported = not mention["is_empty"] and coord in stanza_entities
            tokens = cp["tokens"][int(mention["start"]):int(mention["end"])]
            start_info = rich_coord.get((coord[0], coord[1]))
            end_info = rich_coord.get((coord[0], coord[2]))
            enriched = {
                **mention,
                "cluster_id": mention["entity_id"],
                "start_token": mention["start"],
                "end_token": mention["end"],
                "sentence_index": coord[0] - 1,
                "start_char": start_info.get("start_char") if start_info else None,
                "end_char": end_info.get("end_char") if end_info else None,
                "text": surface_text(cp, mention),
                "is_zero": mention["is_empty"],
                "supported_by_stanza_exact_span": supported,
            }
            enriched_mentions.append(enriched)
            cp_groups[str(mention["entity_id"])].append(enriched)
            if not mention["is_empty"]:
                total_cp_surface += 1
                total_common += int(supported)

        clusters: list[dict[str, Any]] = []
        for cluster_id, mentions in cp_groups.items():
            surface = [mention for mention in mentions if not mention["is_empty"]]
            common = [mention for mention in surface if mention["supported_by_stanza_exact_span"]]
            overlap = len(common) / len(surface) if surface else 0.0
            pair_values: list[bool] = []
            for left, right in combinations(common, 2):
                left_entity = stanza_entities[coordinate(cp, left)]
                right_entity = stanza_entities[coordinate(cp, right)]
                pair_values.append(left_entity == right_entity)
            pair_agreement = sum(pair_values) / len(pair_values) if pair_values else None
            agreed_pairs += sum(pair_values)
            comparable_pairs += len(pair_values)
            band = agreement_band(overlap, pair_agreement, len(surface))
            band_counts[band] += 1
            cluster = {
                "cluster_id": cluster_id,
                "mention_ids": [mention["mention_id"] for mention in mentions],
                "surface_size": len(surface),
                "zero_size": len(mentions) - len(surface),
                "exact_span_overlap_with_stanza": overlap,
                "shared_span_pair_agreement": pair_agreement,
                "agreement_band": band,
            }
            clusters.append(cluster)
            contexts = []
            for mention in mentions:
                start, end = int(mention["start"]), int(mention["end"])
                left, right = max(0, start - 12), min(len(cp["tokens"]), end + 12)
                contexts.append(" ".join(str(token["form"]) for token in cp["tokens"][left:right]))
                mention_rows.append({
                    "doc_id": doc_id,
                    "split": rich["split"],
                    "mention_id": mention["mention_id"],
                    "proposed_cluster_id": cluster_id,
                    "agreement_band": band,
                    "supported_by_stanza_exact_span": mention["supported_by_stanza_exact_span"],
                    "text": mention["text"],
                    "start_token": mention["start"],
                    "end_token": mention["end"],
                    "context": contexts[-1],
                    "mention_valid": "",
                    "corrected_cluster_id": "",
                    "corrected_start_token": "",
                    "corrected_end_token": "",
                    "reviewer_note": "",
                })
            chain_rows.append({
                "doc_id": doc_id,
                "split": rich["split"],
                "cluster_id": cluster_id,
                "surface_size": len(surface),
                "zero_size": len(mentions) - len(surface),
                "agreement_band": band,
                "exact_span_overlap_with_stanza": f"{overlap:.4f}",
                "shared_span_pair_agreement": "" if pair_agreement is None else f"{pair_agreement:.4f}",
                "mentions": " || ".join(str(mention["text"]) for mention in mentions),
                "contexts": " || ".join(contexts),
                "decision": "",
                "corrected_mentions": "",
                "reviewer_note": "",
            })

        output_docs.append({
            "schema_version": "legal-coref-silver-1.0",
            "annotation_status": "silver-unreviewed",
            "annotation_source": "CorPipe26:onestage:corefud1.4:base-260702",
            "doc_id": doc_id,
            "split": rich["split"],
            "source": rich["source"],
            "text": rich["text"],
            "tokens": enriched_tokens,
            "mentions": enriched_mentions,
            "clusters": clusters,
            "stats": {
                "tokens_including_empty": len(enriched_tokens),
                "mentions": len(enriched_mentions),
                "surface_mentions": sum(not mention["is_empty"] for mention in enriched_mentions),
                "clusters": len(clusters),
            },
        })

    jsonl_path = args.output / "corpipe26-silver.jsonl"
    jsonl_path.write_text(
        "".join(json.dumps(document, ensure_ascii=False) + "\n" for document in output_docs),
        encoding="utf-8",
    )
    write_csv(args.output / "review_corpipe_chains.csv", chain_rows)
    write_csv(args.output / "review_corpipe_mentions.csv", mention_rows)
    sample_path = args.output / "review_sample_100.csv"
    write_csv(sample_path, review_sample(chain_rows))
    blocks = document_blocks(args.corpipe.read_text(encoding="utf-8"))
    split_dir = args.output / "splits"
    split_dir.mkdir(exist_ok=True)
    for split in ("train", "dev", "test"):
        selected = [document for document in output_docs if document["split"] == split]
        (split_dir / f"{split}.jsonl").write_text(
            "".join(json.dumps(document, ensure_ascii=False) + "\n" for document in selected),
            encoding="utf-8",
        )
        (split_dir / f"{split}.conllu").write_text(
            "".join(blocks[str(document["doc_id"])] for document in selected), encoding="utf-8"
        )

    summary = {
        "created_at": datetime.now(UTC).isoformat(),
        "documents": len(output_docs),
        "corpipe_surface_mentions": total_cp_surface,
        "stanza_surface_mentions": total_stanza,
        "exact_common_spans": total_common,
        "exact_span_precision_vs_stanza": total_common / total_cp_surface,
        "exact_span_recall_vs_stanza": total_common / total_stanza,
        "shared_span_pair_agreement": agreed_pairs / comparable_pairs if comparable_pairs else None,
        "comparable_within_cluster_pairs": comparable_pairs,
        "agreement_bands": dict(sorted(band_counts.items())),
        "model": {
            "name": "ufal/corpipe26-onestage-corefud1.4-base-260702",
            "segment": args.segment,
            "checkpoint_sha256": sha256(args.model),
            "license": "CC BY-NC-SA 4.0",
        },
        "inputs": {
            "corpipe_conllu_sha256": sha256(args.corpipe),
            "stanza_conllu_sha256": sha256(args.stanza),
            "stanza_jsonl_sha256": sha256(args.stanza_jsonl),
        },
        "interpretation": "Agreement between two automatic systems on unreviewed legal text; not accuracy.",
    }
    (args.output / "agreement-summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    manifest_path = args.output / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8")) if manifest_path.exists() else {}
    artifact_paths = [
        args.corpipe,
        args.stanza,
        jsonl_path,
        args.output / "review_corpipe_chains.csv",
        args.output / "review_corpipe_mentions.csv",
        sample_path,
        args.output / "agreement-summary.json",
        *(split_dir / f"{split}.{extension}" for split in ("train", "dev", "test") for extension in ("jsonl", "conllu")),
    ]
    manifest.update({
        "finalized_at": datetime.now(UTC).isoformat(),
        "annotation_status": "silver-unreviewed",
        "primary_annotation": summary["model"],
        "agreement": summary,
        "outputs": [
            {
                "file": str(path.resolve().relative_to(args.output.resolve())).replace("\\", "/"),
                "bytes": path.stat().st_size,
                "sha256": sha256(path),
            }
            for path in artifact_paths
        ],
    })
    manifest_path.write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

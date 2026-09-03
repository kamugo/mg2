"""Turn CorefUD documents into fixed-size mention-pair tensors."""

from __future__ import annotations

import hashlib
import json
import math
import random
from collections.abc import Iterable, Iterator, Sequence
from pathlib import Path
from typing import Any

import torch
from torch import Tensor
from torch.nn import functional as F
from transformers import AutoModel, AutoTokenizer


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    """Read a document JSONL file produced by the CorefUD converter."""
    with path.open(encoding="utf-8") as source:
        return [json.loads(line) for line in source if line.strip()]


def file_sha256(path: Path) -> str:
    """Calculate a file hash without loading the whole file into memory."""
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for block in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def split_training_documents(
    documents: Sequence[dict[str, Any]], calibration_fraction: float, seed: int
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """Create a deterministic document-level train/calibration split."""
    indices = list(range(len(documents)))
    random.Random(seed).shuffle(indices)
    calibration_size = max(1, round(len(indices) * calibration_fraction))
    calibration = set(indices[:calibration_size])
    return (
        [document for index, document in enumerate(documents) if index not in calibration],
        [document for index, document in enumerate(documents) if index in calibration],
    )


def _feature_value(feats: str, name: str) -> str | None:
    for item in feats.split("|"):
        key, separator, value = item.partition("=")
        if separator and key == name:
            return value
    return None


def _mention_head(document: dict[str, Any], mention: dict[str, Any]) -> int:
    tokens = document["tokens"]
    start, end = int(mention["start"]), int(mention["end"])
    candidates = [
        index
        for index in range(start, min(end, len(tokens)))
        if str(tokens[index].get("upos", "")) in {"NOUN", "PROPN", "PRON", "DET"}
    ]
    return candidates[-1] if candidates else max(start, min(end - 1, len(tokens) - 1))


class HerbertMentionEncoder:
    """Frozen HerBERT encoder with word-aligned contextual representations."""

    def __init__(
        self,
        model_name: str = "allegro/herbert-base-cased",
        device: str = "auto",
        words_per_segment: int = 192,
        segment_stride: int = 176,
        batch_size: int = 8,
    ) -> None:
        use_cuda = torch.cuda.is_available() and device in {"auto", "cuda"}
        self.device = torch.device("cuda" if use_cuda else "cpu")
        self.model_name = model_name
        self.tokenizer = AutoTokenizer.from_pretrained(model_name, use_fast=True)
        self.model = AutoModel.from_pretrained(model_name).to(self.device).eval()
        self.hidden_size = int(self.model.config.hidden_size)
        self.revision = str(getattr(self.model.config, "_commit_hash", None) or "unknown")
        self.words_per_segment = words_per_segment
        self.segment_stride = segment_stride
        self.batch_size = batch_size

    @torch.inference_mode()
    def encode_word_lists(self, word_lists: Sequence[Sequence[str]]) -> list[Tensor]:
        """Encode several documents while batching their segments globally."""
        segments: list[tuple[int, int, list[str]]] = []
        for document_index, words in enumerate(word_lists):
            start = 0
            while start < len(words):
                segments.append(
                    (document_index, start, list(words[start : start + self.words_per_segment]))
                )
                if start + self.words_per_segment >= len(words):
                    break
                start += self.segment_stride

        sums = [torch.zeros(len(words), self.hidden_size, dtype=torch.float32) for words in word_lists]
        counts = [torch.zeros(len(words), dtype=torch.float32) for words in word_lists]
        amp = self.device.type == "cuda"
        for offset in range(0, len(segments), self.batch_size):
            batch = segments[offset : offset + self.batch_size]
            encoded = self.tokenizer(
                [segment for _, _, segment in batch],
                is_split_into_words=True,
                padding=True,
                truncation=True,
                max_length=min(512, int(self.model.config.max_position_embeddings)),
                return_tensors="pt",
            )
            model_inputs = {key: value.to(self.device) for key, value in encoded.items()}
            with torch.amp.autocast("cuda", enabled=amp):
                hidden = self.model(**model_inputs).last_hidden_state
            for row, (document_index, segment_start, _) in enumerate(batch):
                word_ids = encoded.word_ids(batch_index=row)
                grouped: dict[int, list[int]] = {}
                for token_index, word_id in enumerate(word_ids):
                    if word_id is not None:
                        grouped.setdefault(word_id, []).append(token_index)
                for word_id, token_indices in grouped.items():
                    absolute = segment_start + word_id
                    vector = hidden[row, token_indices].mean(dim=0).float().cpu()
                    sums[document_index][absolute] += vector
                    counts[document_index][absolute] += 1
        result: list[Tensor] = []
        for document_index, document_counts in enumerate(counts):
            if not bool((document_counts > 0).all()):
                missing = int((document_counts == 0).sum())
                raise RuntimeError(f"HerBERT produced no subwords for {missing} input words")
            result.append(sums[document_index] / document_counts.unsqueeze(1))
        return result

    def encode_words(self, words: Sequence[str]) -> Tensor:
        """Encode every input word once and return CPU float32 vectors."""
        if not words:
            return torch.empty(0, self.hidden_size)
        return self.encode_word_lists([words])[0]

    def _pool_mentions(
        self, document: dict[str, Any], word_vectors: Tensor
    ) -> tuple[Tensor, list[dict[str, Any]]]:
        tokens = document["tokens"]
        words = [str(token.get("form", "_") or "_") for token in tokens]
        vectors: list[Tensor] = []
        metadata: list[dict[str, Any]] = []
        for mention_index, mention in enumerate(document["mentions"]):
            if bool(mention.get("is_empty", False)):
                continue
            if mention.get("start") is None or mention.get("end") is None:
                continue
            start, end = int(mention["start"]), int(mention["end"])
            if not 0 <= start < end <= len(tokens):
                continue
            head = _mention_head(document, mention)
            token = tokens[head]
            vector = word_vectors[start:end].mean(dim=0)
            vectors.append(vector)
            metadata.append({
                "id": str(mention.get("mention_id", f"m{mention_index}")),
                "entity_id": str(mention["entity_id"]),
                "start": start,
                "end": end,
                "head": head,
                "text": " ".join(words[start:end]),
                "form": str(token.get("form", "_")),
                "lemma": str(token.get("lemma", "_")),
                "upos": str(token.get("upos", "_")),
                "gender": _feature_value(str(token.get("feats", "_")), "Gender"),
                "number": _feature_value(str(token.get("feats", "_")), "Number"),
                "sentence": int(token.get("sentence_id", 0)),
                "is_empty": bool(mention.get("is_empty", False)),
            })
        return torch.stack(vectors) if vectors else torch.empty(0, self.hidden_size), metadata

    def encode_mentions(self, document: dict[str, Any]) -> tuple[Tensor, list[dict[str, Any]]]:
        """Pool contextual word vectors over every gold mention span."""
        words = [str(token.get("form", "_") or "_") for token in document["tokens"]]
        return self._pool_mentions(document, self.encode_words(words))

    def encode_documents(
        self, documents: Sequence[dict[str, Any]]
    ) -> list[tuple[Tensor, list[dict[str, Any]]]]:
        """Encode a document batch with full GPU utilization across short documents."""
        word_lists = [
            [str(token.get("form", "_") or "_") for token in document["tokens"]]
            for document in documents
        ]
        vectors = self.encode_word_lists(word_lists)
        return [
            self._pool_mentions(document, word_vectors)
            for document, word_vectors in zip(documents, vectors, strict=True)
        ]


def build_pair_features(embeddings: Tensor, mentions: Sequence[dict[str, Any]]) -> Tensor:
    count = len(mentions)
    normalized = F.normalize(embeddings.float(), dim=1)
    cosine = normalized @ normalized.T
    features = torch.zeros(8, count, count, dtype=torch.float32)
    features[0] = cosine
    for left in range(count):
        for right in range(left, count):
            first, second = mentions[left], mentions[right]
            token_distance = abs(int(first["head"]) - int(second["head"]))
            sentence_distance = abs(int(first["sentence"]) - int(second["sentence"]))
            values = (
                float(str(first["lemma"]).casefold() == str(second["lemma"]).casefold()),
                float(first["gender"] is not None and first["gender"] == second["gender"]),
                float(first["number"] is not None and first["number"] == second["number"]),
                math.exp(-token_distance / 50.0),
                float(sentence_distance == 0),
                math.exp(-sentence_distance / 5.0),
                float(first["upos"] in {"PRON", "DET"} or second["upos"] in {"PRON", "DET"}),
            )
            for channel, value in enumerate(values, start=1):
                features[channel, left, right] = value
                features[channel, right, left] = value
    return features


def tensorize_document(
    document: dict[str, Any],
    encoder: HerbertMentionEncoder,
    max_mentions: int,
) -> Iterator[tuple[dict[str, Tensor], dict[str, Any]]]:
    """Yield non-overlapping fixed-size mention windows from one document."""
    embeddings, mentions = encoder.encode_mentions(document)
    yield from tensorize_encoded_document(document, embeddings, mentions, max_mentions)


def tensorize_encoded_document(
    document: dict[str, Any],
    embeddings: Tensor,
    mentions: list[dict[str, Any]],
    max_mentions: int,
) -> Iterator[tuple[dict[str, Tensor], dict[str, Any]]]:
    """Yield windows when contextual mention embeddings are already available."""
    for window_index, start in enumerate(range(0, len(mentions), max_mentions)):
        window_mentions = mentions[start : start + max_mentions]
        if len(window_mentions) < 2:
            continue
        count = len(window_mentions)
        window_embeddings = embeddings[start : start + count]
        pair_features = build_pair_features(window_embeddings, window_mentions)
        target = torch.zeros(max_mentions, max_mentions, dtype=torch.float32)
        entity_ids = [mention["entity_id"] for mention in window_mentions]
        for left in range(count):
            for right in range(count):
                target[left, right] = float(entity_ids[left] == entity_ids[right])
        padded_embeddings = torch.zeros(max_mentions, embeddings.shape[1], dtype=torch.float32)
        padded_embeddings[:count] = window_embeddings
        padded_features = torch.zeros(8, max_mentions, max_mentions, dtype=torch.float32)
        padded_features[:, :count, :count] = pair_features
        valid = torch.zeros(max_mentions, dtype=torch.bool)
        valid[:count] = True
        shared_features = padded_features.half()
        yield (
            {
                "mention_embeddings": padded_embeddings.half(),
                "pair_features": shared_features,
                "matrix_features": shared_features,
                "target": target.half(),
                "valid_mentions": valid,
            },
            {
                "window_id": f"{document['doc_id']}::w{window_index}",
                "source_doc_id": document["doc_id"],
                "mention_count": count,
                "mentions": window_mentions,
            },
        )


def save_tensor_split(
    documents: Iterable[dict[str, Any]],
    encoder: HerbertMentionEncoder,
    tensor_path: Path,
    metadata_path: Path,
    max_mentions: int,
    document_batch_size: int = 32,
) -> dict[str, int]:
    """Tensorize, persist and summarize one data split."""
    items: list[dict[str, Tensor]] = []
    metadata_path.parent.mkdir(parents=True, exist_ok=True)
    document_count = mention_count = 0
    document_list = list(documents)
    with metadata_path.open("w", encoding="utf-8") as metadata_file:
        for batch_start in range(0, len(document_list), document_batch_size):
            batch = document_list[batch_start : batch_start + document_batch_size]
            encoded_batch = encoder.encode_documents(batch)
            for document, (embeddings, mentions) in zip(batch, encoded_batch, strict=True):
                document_count += 1
                for item, metadata in tensorize_encoded_document(
                    document, embeddings, mentions, max_mentions
                ):
                    items.append(item)
                    mention_count += int(metadata["mention_count"])
                    metadata_file.write(json.dumps(metadata, ensure_ascii=False) + "\n")
            print(f"tensorized documents={document_count} windows={len(items)}", flush=True)
    if not items:
        raise ValueError("No mention windows were produced")
    tensor_path.parent.mkdir(parents=True, exist_ok=True)
    torch.save(items, tensor_path)
    return {"documents": document_count, "windows": len(items), "mentions": mention_count}

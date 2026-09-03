"""Run a trained Polish-PCC model on automatically detected legal-text mentions."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

import torch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from scripts.evaluate_corefud_model import (  # noqa: E402
    clusters_from_probabilities,
    load_model,
)
from src.data.tensorization import HerbertMentionEncoder, build_pair_features  # noqa: E402


RELATIVE_LEMMAS = {"który", "jaki", "ten", "on", "ona", "ono", "oni", "one", "się", "siebie"}


def stanza_document(text: str, max_sentences: int) -> tuple[dict[str, Any], dict[str, Any]]:
    """Create CorefUD-like tokens and conservative nominal mention candidates."""
    import stanza

    pipeline = stanza.Pipeline(
        "pl",
        processors="tokenize,mwt,pos,lemma",
        use_gpu=False,
        verbose=False,
    )
    parsed = pipeline(text)
    tokens: list[dict[str, Any]] = []
    sentence_ranges: list[tuple[int, int]] = []
    for sentence_index, sentence in enumerate(parsed.sentences[:max_sentences], start=1):
        start = len(tokens)
        for word in sentence.words:
            tokens.append({
                "index": len(tokens),
                "conllu_id": str(word.id),
                "form": word.text,
                "lemma": word.lemma or word.text,
                "upos": word.upos or "_",
                "feats": word.feats or "_",
                "sentence_id": sentence_index,
                "is_empty": False,
            })
        sentence_ranges.append((start, len(tokens)))

    mentions: list[dict[str, Any]] = []
    for sentence_start, sentence_end in sentence_ranges:
        index = sentence_start
        while index < sentence_end:
            token = tokens[index]
            if token["upos"] == "PROPN":
                end = index + 1
                while end < sentence_end and tokens[end]["upos"] == "PROPN":
                    end += 1
            elif token["upos"] in {"NOUN", "PRON"} or str(token["lemma"]).casefold() in RELATIVE_LEMMAS:
                end = index + 1
            else:
                index += 1
                continue
            mentions.append({
                "mention_id": f"legal:m{len(mentions)}",
                "entity_id": f"candidate-{len(mentions)}",
                "start": index,
                "end": end,
                "descriptor": "automatic-stanza-candidate",
                "is_empty": False,
            })
            index = end
    document = {
        "doc_id": "legal-eli",
        "source": "ELI",
        "tokens": tokens,
        "mentions": mentions,
    }
    detector = {
        "sentences": len(sentence_ranges),
        "tokens": len(tokens),
        "mention_candidates": len(mentions),
        "rule": "Stanza: contiguous PROPN groups plus NOUN/PRON and selected relative/demonstrative lemmas",
    }
    return document, detector


@torch.inference_mode()
def predict(
    checkpoint: Path,
    text_path: Path,
    threshold: float,
    output_path: Path,
    max_sentences: int,
    max_mentions: int,
) -> dict[str, Any]:
    use_cuda = torch.cuda.is_available()
    device = torch.device("cuda" if use_cuda else "cpu")
    document, detector = stanza_document(text_path.read_text(encoding="utf-8"), max_sentences)
    encoder = HerbertMentionEncoder(device=str(device), batch_size=8)
    embeddings, mentions = encoder.encode_mentions(document)
    model = load_model(checkpoint, device)
    chains: list[dict[str, Any]] = []
    window_count = 0
    for start in range(0, len(mentions), max_mentions):
        window_mentions = mentions[start : start + max_mentions]
        if len(window_mentions) < 2:
            continue
        window_count += 1
        window_embeddings = embeddings[start : start + len(window_mentions)]
        pair_features = build_pair_features(window_embeddings, window_mentions)
        size = len(window_mentions)
        model_embeddings = torch.zeros(1, max_mentions, embeddings.shape[1], device=device)
        model_pairs = torch.zeros(1, 8, max_mentions, max_mentions, device=device)
        model_embeddings[0, :size] = window_embeddings.to(device)
        model_pairs[0, :, :size, :size] = pair_features.to(device)
        with torch.amp.autocast("cuda", enabled=use_cuda):
            logits = model(model_embeddings, model_pairs, model_pairs, 0.0, 0.0)["logits"]
        probabilities = torch.sigmoid(logits[0, :size, :size]).float().cpu()
        for cluster in clusters_from_probabilities(probabilities, threshold):
            if len(cluster) < 2:
                continue
            pair_scores = [
                float(probabilities[right, left])
                for offset, left in enumerate(cluster)
                for right in cluster[offset + 1 :]
            ]
            chains.append({
                "window": window_count,
                "mean_pair_probability": sum(pair_scores) / len(pair_scores),
                "mentions": [window_mentions[index] for index in cluster],
            })
    chains.sort(key=lambda item: (-len(item["mentions"]), -item["mean_pair_probability"]))
    payload = {
        "source_file": str(text_path),
        "checkpoint": str(checkpoint),
        "threshold_from_general_domain_calibration": threshold,
        "detector": detector,
        "windows": window_count,
        "non_singleton_chains": len(chains),
        "chains": chains,
        "status": "qualitative-domain-transfer-only; no legal gold annotations",
    }
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return payload


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--checkpoint", type=Path, required=True)
    parser.add_argument("--text", type=Path, required=True)
    parser.add_argument("--threshold", type=float, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--max-sentences", type=int, default=80)
    parser.add_argument("--max-mentions", type=int, default=48)
    args = parser.parse_args()
    payload = predict(
        args.checkpoint.resolve(),
        args.text.resolve(),
        args.threshold,
        args.output.resolve(),
        args.max_sentences,
        args.max_mentions,
    )
    summary = {key: payload[key] for key in ("detector", "windows", "non_singleton_chains", "status")}
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

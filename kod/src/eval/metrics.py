"""Transparent coreference metrics used only for consistency checks.

The official CorefUD scorer remains authoritative for reported experiments.
This module operates on exact, hashable mention identifiers and is useful for
unit tests, document-level bootstrap resampling, and detecting pipeline bugs.
"""

from __future__ import annotations

from itertools import combinations
from typing import Hashable, Iterable, Mapping, Sequence

import numpy as np
from scipy.optimize import linear_sum_assignment

Mention = Hashable
Cluster = set[Mention]


def _safe_f1(precision: float, recall: float) -> float:
    if precision + recall == 0:
        return 0.0
    return 2.0 * precision * recall / (precision + recall)


def _score(precision: float, recall: float) -> dict[str, float]:
    return {"precision": precision, "recall": recall, "f1": _safe_f1(precision, recall)}


def _clusters(raw: Iterable[Iterable[Mention]]) -> list[Cluster]:
    result = [set(cluster) for cluster in raw if cluster]
    flattened = [mention for cluster in result for mention in cluster]
    if len(flattened) != len(set(flattened)):
        raise ValueError("A mention may occur in only one cluster per partition.")
    return result


def _owner_map(clusters: Sequence[Cluster]) -> dict[Mention, int]:
    return {mention: index for index, cluster in enumerate(clusters) for mention in cluster}


def _muc_side(source: Sequence[Cluster], target: Sequence[Cluster]) -> tuple[float, float]:
    target_owner = _owner_map(target)
    numerator = 0.0
    denominator = 0.0
    for cluster in source:
        if len(cluster) < 2:
            continue
        partitions = {target_owner[m] for m in cluster if m in target_owner}
        missing = sum(m not in target_owner for m in cluster)
        numerator += len(cluster) - len(partitions) - missing
        denominator += len(cluster) - 1
    return numerator, denominator


def muc(gold: Sequence[Cluster], predicted: Sequence[Cluster]) -> dict[str, float]:
    """Compute MUC precision, recall, and F1."""
    recall_num, recall_den = _muc_side(gold, predicted)
    precision_num, precision_den = _muc_side(predicted, gold)
    precision = precision_num / precision_den if precision_den else 0.0
    recall = recall_num / recall_den if recall_den else 0.0
    return _score(precision, recall)


def b_cubed(gold: Sequence[Cluster], predicted: Sequence[Cluster]) -> dict[str, float]:
    """Compute mention-weighted B-cubed with exact mention identity."""
    gold_owner = _owner_map(gold)
    pred_owner = _owner_map(predicted)
    precision_sum = 0.0
    for mention, pred_index in pred_owner.items():
        if mention in gold_owner:
            overlap = predicted[pred_index] & gold[gold_owner[mention]]
            precision_sum += len(overlap) / len(predicted[pred_index])
    recall_sum = 0.0
    for mention, gold_index in gold_owner.items():
        if mention in pred_owner:
            overlap = gold[gold_index] & predicted[pred_owner[mention]]
            recall_sum += len(overlap) / len(gold[gold_index])
    precision = precision_sum / len(pred_owner) if pred_owner else 0.0
    recall = recall_sum / len(gold_owner) if gold_owner else 0.0
    return _score(precision, recall)


def ceafe(gold: Sequence[Cluster], predicted: Sequence[Cluster]) -> dict[str, float]:
    """Compute entity-based CEAF using optimal bipartite alignment."""
    if not gold or not predicted:
        return _score(0.0, 0.0)
    similarities = np.zeros((len(gold), len(predicted)), dtype=np.float64)
    for gold_index, gold_cluster in enumerate(gold):
        for pred_index, pred_cluster in enumerate(predicted):
            similarities[gold_index, pred_index] = (
                2.0 * len(gold_cluster & pred_cluster) / (len(gold_cluster) + len(pred_cluster))
            )
    rows, columns = linear_sum_assignment(-similarities)
    similarity = float(similarities[rows, columns].sum())
    return _score(similarity / len(predicted), similarity / len(gold))


def _pair_links(clusters: Sequence[Cluster]) -> set[frozenset[Mention]]:
    return {
        frozenset(pair)
        for cluster in clusters
        for pair in combinations(sorted(cluster, key=str), 2)
    }


def blanc(gold: Sequence[Cluster], predicted: Sequence[Cluster]) -> dict[str, float]:
    """Compute BLANC as the mean F1 of coreference and non-coreference links."""
    mentions = set(_owner_map(gold)) | set(_owner_map(predicted))
    all_pairs = {frozenset(pair) for pair in combinations(sorted(mentions, key=str), 2)}
    gold_coref = _pair_links(gold)
    pred_coref = _pair_links(predicted)
    gold_noncoref = all_pairs - gold_coref
    pred_noncoref = all_pairs - pred_coref

    def link_score(expected: set[frozenset[Mention]], actual: set[frozenset[Mention]]) -> dict[str, float]:
        if not expected and not actual:
            return _score(1.0, 1.0)
        true_positive = len(expected & actual)
        precision = true_positive / len(actual) if actual else 0.0
        recall = true_positive / len(expected) if expected else 0.0
        return _score(precision, recall)

    coref = link_score(gold_coref, pred_coref)
    noncoref = link_score(gold_noncoref, pred_noncoref)
    return {
        "precision": (coref["precision"] + noncoref["precision"]) / 2.0,
        "recall": (coref["recall"] + noncoref["recall"]) / 2.0,
        "f1": (coref["f1"] + noncoref["f1"]) / 2.0,
    }


def _lea_side(source: Sequence[Cluster], target: Sequence[Cluster]) -> tuple[float, float]:
    target_links = _pair_links(target)
    numerator = 0.0
    denominator = 0.0
    target_owner = _owner_map(target)
    for cluster in source:
        weight = float(len(cluster))
        if len(cluster) == 1:
            mention = next(iter(cluster))
            resolution = float(
                mention in target_owner and len(target[target_owner[mention]]) == 1
            )
        else:
            links = {frozenset(pair) for pair in combinations(sorted(cluster, key=str), 2)}
            resolution = len(links & target_links) / len(links)
        numerator += weight * resolution
        denominator += weight
    return numerator, denominator


def lea(gold: Sequence[Cluster], predicted: Sequence[Cluster]) -> dict[str, float]:
    """Compute link-based entity-aware precision, recall, and F1."""
    recall_num, recall_den = _lea_side(gold, predicted)
    precision_num, precision_den = _lea_side(predicted, gold)
    precision = precision_num / precision_den if precision_den else 0.0
    recall = recall_num / recall_den if recall_den else 0.0
    return _score(precision, recall)


def mention_detection(gold: Sequence[Cluster], predicted: Sequence[Cluster]) -> dict[str, float]:
    """Compute exact mention detection precision, recall, and F1."""
    gold_mentions = set(_owner_map(gold))
    pred_mentions = set(_owner_map(predicted))
    overlap = len(gold_mentions & pred_mentions)
    precision = overlap / len(pred_mentions) if pred_mentions else 0.0
    recall = overlap / len(gold_mentions) if gold_mentions else 0.0
    return _score(precision, recall)


def evaluate_partition(
    gold_raw: Iterable[Iterable[Mention]], predicted_raw: Iterable[Iterable[Mention]]
) -> dict[str, dict[str, float] | float]:
    """Evaluate a single aggregate partition."""
    gold = _clusters(gold_raw)
    predicted = _clusters(predicted_raw)
    scores: dict[str, dict[str, float] | float] = {
        "muc": muc(gold, predicted),
        "b_cubed": b_cubed(gold, predicted),
        "ceafe": ceafe(gold, predicted),
        "lea": lea(gold, predicted),
        "blanc": blanc(gold, predicted),
        "mention_detection": mention_detection(gold, predicted),
    }
    scores["conll_f1"] = sum(
        float(scores[name]["f1"]) for name in ("muc", "b_cubed", "ceafe")  # type: ignore[index]
    ) / 3.0
    return scores


def evaluate_documents(
    documents: Sequence[Mapping[str, object]],
) -> dict[str, dict[str, float] | float]:
    """Evaluate documents after prefixing identifiers to prevent collisions."""
    gold: list[list[tuple[int, Mention]]] = []
    predicted: list[list[tuple[int, Mention]]] = []
    for doc_index, document in enumerate(documents):
        for cluster in document["gold_clusters"]:  # type: ignore[union-attr]
            gold.append([(doc_index, mention) for mention in cluster])
        for cluster in document["predicted_clusters"]:  # type: ignore[union-attr]
            predicted.append([(doc_index, mention) for mention in cluster])
    return evaluate_partition(gold, predicted)

"""Supervised mention-pair logistic regression baseline."""

from __future__ import annotations

from collections.abc import Mapping, Sequence

import numpy as np
from sklearn.linear_model import LogisticRegression


class _UnionFind:
    def __init__(self, size: int) -> None:
        self.parent = list(range(size))

    def find(self, item: int) -> int:
        while self.parent[item] != item:
            self.parent[item] = self.parent[self.parent[item]]
            item = self.parent[item]
        return item

    def union(self, first: int, second: int) -> None:
        first_root, second_root = self.find(first), self.find(second)
        if first_root != second_root:
            self.parent[second_root] = first_root


class MentionPairLogisticBaseline:
    """Fit logistic regression on explicit pair features and close links transitively."""

    def __init__(self, threshold: float = 0.5, seed: int = 20260903) -> None:
        self.threshold = threshold
        self.classifier = LogisticRegression(
            class_weight="balanced", max_iter=1000, random_state=seed
        )

    @staticmethod
    def pair_features(
        first: Mapping[str, object], second: Mapping[str, object]
    ) -> np.ndarray:
        """Create transparent lexical, morphosyntactic, and distance features."""
        first_index = int(first.get("index", 0))
        second_index = int(second.get("index", 0))
        return np.asarray(
            [
                str(first.get("lemma", "")).casefold() == str(second.get("lemma", "")).casefold(),
                str(first.get("head", "")).casefold() == str(second.get("head", "")).casefold(),
                first.get("gender") == second.get("gender") and first.get("gender") is not None,
                first.get("number") == second.get("number") and first.get("number") is not None,
                abs(first_index - second_index),
                abs(int(first.get("sentence", 0)) - int(second.get("sentence", 0))),
            ],
            dtype=np.float64,
        )

    def fit(
        self,
        pairs: Sequence[tuple[Mapping[str, object], Mapping[str, object]]],
        labels: Sequence[int],
    ) -> "MentionPairLogisticBaseline":
        """Fit the classifier from labeled mention pairs."""
        features = np.stack([self.pair_features(first, second) for first, second in pairs])
        self.classifier.fit(features, np.asarray(labels, dtype=np.int64))
        return self

    def predict(self, mentions: Sequence[Mapping[str, object]]) -> list[list[str]]:
        """Predict pair links and convert their transitive closure to clusters."""
        union_find = _UnionFind(len(mentions))
        for later in range(1, len(mentions)):
            candidates = [
                self.pair_features(mentions[earlier], mentions[later])
                for earlier in range(later)
            ]
            probabilities = self.classifier.predict_proba(np.stack(candidates))[:, 1]
            best = int(np.argmax(probabilities))
            if float(probabilities[best]) >= self.threshold:
                union_find.union(later, best)
        grouped: dict[int, list[str]] = {}
        for index, mention in enumerate(mentions):
            grouped.setdefault(union_find.find(index), []).append(str(mention["id"]))
        return list(grouped.values())

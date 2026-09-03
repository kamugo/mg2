"""Deterministic lemma and head matching baseline."""

from __future__ import annotations

import re
from collections.abc import Mapping, Sequence


def _normalise(value: object) -> str:
    return re.sub(r"[^\wąćęłńóśźż]+", "", str(value).casefold())


class HeadMatchBaseline:
    """Cluster mentions with an equal normalized lemma or syntactic head."""

    def predict(self, mentions: Sequence[Mapping[str, object]]) -> list[list[str]]:
        """Return mention identifier clusters in input order."""
        clusters: list[list[str]] = []
        key_to_cluster: dict[str, int] = {}
        for mention in mentions:
            mention_id = str(mention["id"])
            keys = {
                key
                for key in (
                    _normalise(mention.get("lemma", "")),
                    _normalise(mention.get("head", "")),
                )
                if key
            }
            matches = sorted({key_to_cluster[key] for key in keys if key in key_to_cluster})
            if matches:
                cluster_index = matches[0]
                clusters[cluster_index].append(mention_id)
            else:
                cluster_index = len(clusters)
                clusters.append([mention_id])
            for key in keys:
                key_to_cluster[key] = cluster_index
        return clusters

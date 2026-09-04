"""Niezależny audyt puli SAOS ``przeglad50`` z commita Agenta B.

Skrypt nie zmienia żadnego repozytorium. Korzysta z czytnika i dokładnego mapowania
offsetów znakowych Agenta B, aby kontrola dotyczyła tej samej reprezentacji danych.
"""

from __future__ import annotations

import argparse
import csv
import json
import re
import statistics
import sys
from collections import Counter
from itertools import combinations
from pathlib import Path


def _pair_prf(tp: int, predicted: int, reference: int) -> dict[str, float | int]:
    precision = tp / predicted if predicted else 0.0
    recall = tp / reference if reference else 0.0
    f1 = 2 * precision * recall / (precision + recall) if precision + recall else 0.0
    return {
        "true_positive": tp,
        "predicted_positive": predicted,
        "reference_positive": reference,
        "precision": precision,
        "recall": recall,
        "f1": f1,
    }


def _head_positions(path: Path, model: str) -> Counter[str]:
    positions: Counter[str] = Counter()
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line or line.startswith("#"):
            continue
        cols = line.split("\t")
        if len(cols) < 10 or "Entity=" not in cols[9]:
            continue
        value = cols[9].split("Entity=", 1)[1]
        for fragment in re.findall(r"\(([^()]*)", value):
            pattern = r"-x-(\d+)-" if model == "v2" else r"--(\d+)(?:-|\)|$)"
            match = re.search(pattern, fragment)
            if match:
                positions[match.group(1)] += 1
    return positions


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--agent-b-root", type=Path, required=True)
    args = parser.parse_args()
    kod = args.agent_b_root.resolve() / "kod"
    sys.path.insert(0, str(kod))

    from scripts.przeglad50 import _spany, _tekst, _zera  # type: ignore
    from src.data.corefud_reader import read_corefud  # type: ignore

    data = kod / "data" / "przeglad50"
    v2 = {d.doc_id: d for d in read_corefud(str(data / "v2.pred_on_original.test.conllu"))}
    corpipe = {d.doc_id: d for d in read_corefud(str(data / "corpipe_pred.conllu"))}

    all_pairs = v2_positive = corpipe_positive = positive_intersection = 0
    local_pairs = local_agree = local_v2_positive = local_corpipe_positive = local_tp = 0
    common_mentions = zero_v2 = zero_corpipe = identical_texts = 0
    local_accuracy_per_doc: list[float] = []

    for doc_id in sorted(set(v2) & set(corpipe)):
        a, b = v2[doc_id], corpipe[doc_id]
        spans_a, spans_b = _spany(a), _spany(b)
        shared = sorted(set(spans_a) & set(spans_b))
        common_mentions += len(shared)
        zero_v2 += _zera(a)
        zero_corpipe += _zera(b)
        identical_texts += int(_tekst(a) == _tekst(b))

        clusters_a: dict[int, list[tuple]] = {}
        clusters_b: dict[int, list[tuple]] = {}
        for span in shared:
            clusters_a.setdefault(spans_a[span], []).append(span)
            clusters_b.setdefault(spans_b[span], []).append(span)
        pairs_a = {
            tuple(sorted(pair))
            for members in clusters_a.values()
            for pair in combinations(members, 2)
        }
        pairs_b = {
            tuple(sorted(pair))
            for members in clusters_b.values()
            for pair in combinations(members, 2)
        }
        v2_positive += len(pairs_a)
        corpipe_positive += len(pairs_b)
        positive_intersection += len(pairs_a & pairs_b)
        all_pairs += len(shared) * (len(shared) - 1) // 2

        agree = compared = 0
        for i in range(len(shared)):
            for j in range(i + 1, min(len(shared), i + 200)):
                same_a = spans_a[shared[i]] == spans_a[shared[j]]
                same_b = spans_b[shared[i]] == spans_b[shared[j]]
                compared += 1
                agree += int(same_a == same_b)
                local_v2_positive += int(same_a)
                local_corpipe_positive += int(same_b)
                local_tp += int(same_a and same_b)
        local_pairs += compared
        local_agree += agree
        if compared:
            local_accuracy_per_doc.append(agree / compared)

    lista = json.loads((data / "lista.json").read_text(encoding="utf-8"))["dokumenty"]
    summary = json.loads((data / "porownanie_podsumowanie.json").read_text(encoding="utf-8"))
    eval_json = json.loads((data / "v2.json").read_text(encoding="utf-8"))
    population = list(
        csv.DictReader((kod / "data" / "silver" / "indeks.csv").open(encoding="utf-8"), delimiter=";")
    )
    review_stats = []
    for path in (data / "review").glob("*.txt"):
        lines = path.read_text(encoding="utf-8").splitlines()
        review_stats.append((len(lines), max(map(len, lines), default=0)))

    result = {
        "documents": {
            "v2": len(v2),
            "corpipe": len(corpipe),
            "identical_text_after_whitespace_removal": identical_texts,
        },
        "mentions": {
            "v2_after_export": summary["spany_v2"],
            "corpipe_surface": summary["spany_corpipe"],
            "shared": common_mentions,
            "only_v2": summary["tylko_v2"],
            "only_corpipe": summary["tylko_corpipe"],
            "jaccard": summary["jaccard_spanow"],
            "minimum_checks_disagreements_plus_10pct_shared": (
                summary["tylko_v2"] + summary["tylko_corpipe"] + round(0.1 * common_mentions)
            ),
        },
        "zeros": {"v2": zero_v2, "corpipe": zero_corpipe},
        "clustering_on_shared_mentions": {
            "all_pairs": all_pairs,
            "positive_pair_prf_v2_vs_corpipe": _pair_prf(
                positive_intersection, v2_positive, corpipe_positive
            ),
            "all_different_baseline_accuracy_vs_corpipe": 1 - corpipe_positive / all_pairs,
            "agent_b_local_199_successor_pairs": {
                "pairs": local_pairs,
                "pooled_accuracy": local_agree / local_pairs,
                "median_accuracy_per_document": statistics.median(local_accuracy_per_doc),
                "positive_pair_prf_v2_vs_corpipe": _pair_prf(
                    local_tp, local_v2_positive, local_corpipe_positive
                ),
                "all_different_baseline_accuracy_vs_corpipe": 1 - local_corpipe_positive / local_pairs,
            },
        },
        "sample": {
            "population_documents": len(population),
            "sample_documents": len(lista),
            "population_tokens": sum(int(row["tokeny"]) for row in population),
            "sample_tokens": sum(int(row["tokeny"]) for row in lista),
            "court_population": dict(Counter(row["courtType"] for row in population)),
            "court_sample": dict(Counter(row["courtType"] for row in lista)),
            "year_min": min(int(row["rok"]) for row in lista),
            "year_max": max(int(row["rok"]) for row in lista),
            "documents_2015_2024": sum(2015 <= int(row["rok"]) <= 2024 for row in lista),
            "documents_800_5000_tokens": sum(800 <= int(row["tokeny"]) <= 5000 for row in lista),
            "duplicate_text_hashes": len(lista) - len({row["text_sha256"] for row in lista}),
        },
        "review_format": {
            "files": len(review_stats),
            "all_files_three_lines": all(lines == 3 for lines, _ in review_stats),
            "median_max_line_chars": statistics.median(length for _, length in review_stats),
            "max_line_chars": max(length for _, length in review_stats),
        },
        "task_scope": {
            "recorded_zeros": eval_json["task_scope"]["zeros"],
            "actual_input_empty_nodes": zero_v2,
        },
        "v2_original_export_loss": eval_json["export_on_original"]["loss"],
        "head_positions": {
            "v2": dict(_head_positions(data / "v2.pred_on_original.test.conllu", "v2")),
            "corpipe": dict(_head_positions(data / "corpipe_pred.conllu", "corpipe")),
        },
    }
    print(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()

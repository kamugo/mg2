"""Niezależny audyt pilota prawnego z rundy 8 Agenta B.

Skrypt jest tylko do odczytu. Sprawdza liczby porównania, rekordy adjudykacji,
drzewa zależności, głowy zapisane w CorefUD oraz kompletność manifestu względem
plików śledzonych przez Git.
"""

from __future__ import annotations

import argparse
import csv
import json
import re
import subprocess
import sys
from collections import Counter
from itertools import combinations
from pathlib import Path
from typing import Any


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


def _head_positions(path: Path, model: str) -> dict[str, dict[str, int]]:
    pattern = re.compile(r"-x-(\d+)-") if model == "v2" else re.compile(
        r"--(\d+)(?:-|$)"
    )
    surface: Counter[str] = Counter()
    empty: Counter[str] = Counter()
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line or line.startswith("#"):
            continue
        cols = line.split("\t")
        if len(cols) < 10 or "Entity=" not in cols[9]:
            continue
        target = empty if "." in cols[0] else surface
        for opening in re.findall(r"\(([^()]*)", cols[9]):
            match = pattern.search(opening)
            if match:
                target[match.group(1)] += 1
    return {"surface": dict(surface), "empty_nodes": dict(empty)}


def _tree_audit(path: Path) -> dict[str, Any]:
    sentences: list[tuple[str, list[tuple[int, int]]]] = []
    current: list[tuple[int, int]] = []
    sent_id = ""
    for line in path.read_text(encoding="utf-8").splitlines() + [""]:
        if not line:
            if current:
                sentences.append((sent_id, current))
                current = []
            continue
        if line.startswith("# sent_id ="):
            sent_id = line.split("=", 1)[1].strip()
            continue
        if line.startswith("#"):
            continue
        cols = line.split("\t")
        if len(cols) < 8 or not cols[0].isdigit():
            continue
        try:
            current.append((int(cols[0]), int(cols[6])))
        except ValueError:
            current.append((int(cols[0]), -1))

    root_counts: Counter[int] = Counter()
    invalid_heads = self_heads = cycle_sentences = 0
    lengths: Counter[int] = Counter()
    invalid_root_sentences: list[dict[str, int | str]] = []
    for current_sent_id, sent in sentences:
        n = len(sent)
        lengths[n] += 1
        parents = {idx: head for idx, head in sent}
        roots = sum(head == 0 for _, head in sent)
        root_counts[roots] += 1
        if roots != 1:
            invalid_root_sentences.append(
                {"sent_id": current_sent_id, "tokens": n, "roots": roots}
            )
        invalid_heads += sum(head < 0 or head > n for _, head in sent)
        self_heads += sum(idx == head for idx, head in sent)
        has_cycle = False
        for start, _ in sent:
            seen: set[int] = set()
            node = start
            while node and node in parents:
                if node in seen:
                    has_cycle = True
                    break
                seen.add(node)
                node = parents[node]
            if has_cycle:
                break
        cycle_sentences += int(has_cycle)
    return {
        "sentences": len(sentences),
        "root_count_distribution": {str(k): v for k, v in sorted(root_counts.items())},
        "sentences_not_exactly_one_root": sum(v for k, v in root_counts.items() if k != 1),
        "invalid_root_sentences": invalid_root_sentences,
        "invalid_head_indices": invalid_heads,
        "self_heads": self_heads,
        "sentences_with_cycles": cycle_sentences,
        "sentences_length_120": lengths[120],
        "maximum_sentence_length": max(lengths, default=0),
    }


def _tracked_manifest_paths(repo: Path, manifest_path: Path) -> dict[str, Any]:
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    rels = list(manifest.get("inputs", {})) + list(manifest.get("outputs", {}))
    untracked: list[str] = []
    missing: list[str] = []
    for rel in rels:
        repo_rel = f"kod/{rel}".replace("\\", "/")
        if not (repo / repo_rel).exists():
            missing.append(rel)
        result = subprocess.run(
            ["git", "ls-files", "--error-unmatch", "--", repo_rel],
            cwd=repo,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            check=False,
        )
        if result.returncode:
            untracked.append(rel)
    return {
        "declared_paths": len(rels),
        "missing_locally": missing,
        "not_tracked_by_git": untracked,
    }


def _adjudication_audit(adjudication_dir: Path) -> dict[str, Any]:
    statuses: Counter[str] = Counter()
    head_positions = {"v2": Counter(), "corpipe": Counter()}
    gold_fields_filled: Counter[str] = Counter()
    window_ranges: dict[str, list[tuple[int, int]]] = {}
    span_records = windows = contexts_with_whitespace = 0
    for path in sorted(adjudication_dir.glob("*.jsonl")):
        for line in path.read_text(encoding="utf-8").splitlines():
            record = json.loads(line)
            status = record["status"]
            statuses[status] += 1
            if status == "random_window":
                windows += 1
                start, end_inclusive = record["token_range"]
                window_ranges.setdefault(record["doc"], []).append((start, end_inclusive + 1))
                continue
            span_records += 1
            contexts_with_whitespace += int(any(ch.isspace() for ch in record["context"]))
            for system in ("v2", "corpipe"):
                value = record[f"head_pos_{system}"]
                if value is not None:
                    head_positions[system][str(value)] += 1
            for field in ("gold_span", "gold_cluster", "gold_head"):
                gold_fields_filled[field] += int(record[field] is not None)

    overlap_by_doc: dict[str, int] = {}
    nominal_tokens = unique_tokens = 0
    for doc, ranges in window_ranges.items():
        nominal = sum(end - start for start, end in ranges)
        covered = set()
        for start, end in ranges:
            covered.update(range(start, end))
        nominal_tokens += nominal
        unique_tokens += len(covered)
        overlap_by_doc[doc] = nominal - len(covered)
    return {
        "span_records": span_records,
        "windows": windows,
        "status_counts": dict(statuses),
        "recorded_head_positions": {
            system: dict(values) for system, values in head_positions.items()
        },
        "gold_fields_filled": dict(gold_fields_filled),
        "contexts_with_whitespace": contexts_with_whitespace,
        "window_tokens_nominal": nominal_tokens,
        "window_tokens_unique_within_documents": unique_tokens,
        "window_overlap_tokens_by_document": overlap_by_doc,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--agent-b-root", type=Path, required=True)
    args = parser.parse_args()
    repo = args.agent_b_root.resolve()
    kod = repo / "kod"
    data = kod / "data" / "pilot"
    sys.path.insert(0, str(kod))

    from evaluate import detect_input_syntax  # type: ignore
    from scripts.przeglad50 import _spany, _tekst, _zera  # type: ignore
    from src.data.corefud_reader import read_corefud  # type: ignore

    v2_path = data / "v2.pred_on_original.test.conllu"
    corpipe_path = data / "corpipe_pred.conllu"
    v2 = {doc.doc_id: doc for doc in read_corefud(str(v2_path))}
    corpipe = {doc.doc_id: doc for doc in read_corefud(str(corpipe_path))}

    per_document: dict[str, Any] = {}
    pooled_a = pooled_b = pooled_intersection = 0
    identical_texts = zeros_v2 = zeros_corpipe = 0
    for doc_id in sorted(set(v2) & set(corpipe)):
        a, b = v2[doc_id], corpipe[doc_id]
        spans_a, spans_b = _spany(a), _spany(b)
        shared = set(spans_a) & set(spans_b)
        clusters_a: dict[int, list[tuple]] = {}
        clusters_b: dict[int, list[tuple]] = {}
        for span in shared:
            clusters_a.setdefault(spans_a[span], []).append(span)
            clusters_b.setdefault(spans_b[span], []).append(span)
        pairs_a = {
            tuple(sorted(pair))
            for mentions in clusters_a.values()
            for pair in combinations(mentions, 2)
        }
        pairs_b = {
            tuple(sorted(pair))
            for mentions in clusters_b.values()
            for pair in combinations(mentions, 2)
        }
        intersection = len(pairs_a & pairs_b)
        pooled_a += len(pairs_a)
        pooled_b += len(pairs_b)
        pooled_intersection += intersection
        per_document[doc_id] = {
            "v2_mentions": len(spans_a),
            "corpipe_surface_mentions": len(spans_b),
            "shared_mentions": len(shared),
            "positive_pair_prf_v2_vs_corpipe": _pair_prf(
                intersection, len(pairs_a), len(pairs_b)
            ),
        }
        identical_texts += int(_tekst(a) == _tekst(b))
        zeros_v2 += _zera(a)
        zeros_corpipe += _zera(b)

    csv_rows = list(
        csv.DictReader((data / "porownanie.csv").open(encoding="utf-8"), delimiter=";")
    )
    sample = [
        json.loads(line)
        for line in (kod / "data" / "saos2015" / "meta.jsonl").read_text(
            encoding="utf-8"
        ).splitlines()
        if line.strip()
    ]
    classified_sample = json.loads(
        (kod / "data" / "saos2015" / "lista.json").read_text(encoding="utf-8")
    )["dokumenty"]
    pilot_ids = {
        row["id"]
        for row in json.loads(
            (kod / "data" / "saos2015" / "pilot_lista.json").read_text(encoding="utf-8")
        )["dokumenty"]
    }
    provenance = json.loads(
        (kod / "runs" / "reinf_r6" / "corpipe" / "PROVENANCE.json").read_text(
            encoding="utf-8"
        )
    )
    result = {
        "agent_b_sha": subprocess.check_output(
            ["git", "rev-parse", "HEAD"], cwd=repo, text=True
        ).strip(),
        "documents": {
            "v2": len(v2),
            "corpipe": len(corpipe),
            "identical_text_after_whitespace_removal": identical_texts,
        },
        "zeros": {"v2": zeros_v2, "corpipe": zeros_corpipe},
        "per_document": per_document,
        "pooled_positive_pair_prf_v2_vs_corpipe": _pair_prf(
            pooled_intersection, pooled_a, pooled_b
        ),
        "reported_csv_rows": csv_rows,
        "adjudication": _adjudication_audit(data / "adjudykacja"),
        "encoded_head_positions": {
            "v2": _head_positions(v2_path, "v2"),
            "corpipe": _head_positions(corpipe_path, "corpipe"),
        },
        "syntax": {
            "detect_input_syntax": detect_input_syntax(str(data / "pilot_input.conllu")),
            "basic_tree_audit": _tree_audit(data / "pilot_input.conllu"),
        },
        "saos2015_sample": {
            "documents": len(sample),
            "date_min": min(row["judgmentDate"] for row in sample),
            "date_max": max(row["judgmentDate"] for row in sample),
            "years": dict(Counter(row["judgmentDate"][:4] for row in sample)),
            "court_types": dict(Counter(row["courtType"] for row in sample)),
            "within_800_5000_whitespace_tokens": sum(
                800 <= row["tokens_ws"] <= 5000 for row in sample
            ),
            "domains": dict(Counter(row["dziedzina"] for row in classified_sample)),
            "domains_after_excluding_pilot": dict(
                Counter(
                    row["dziedzina"]
                    for row in classified_sample
                    if row["id"] not in pilot_ids
                )
            ),
        },
        "manifest": _tracked_manifest_paths(repo, data / "MANIFEST.json"),
        "corpipe_provenance": {
            "hf_revision": provenance["hf_model"]["revision"],
            "model_sha256": provenance["hf_model"]["files"]["model.pt"]["sha256"],
            "executed_run_count": len(provenance["executed_runs"]),
            "has_pilot_run": any(
                "pilot" in (run.get("command", "") + run.get("output", ""))
                for run in provenance["executed_runs"]
            ),
        },
    }
    print(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()

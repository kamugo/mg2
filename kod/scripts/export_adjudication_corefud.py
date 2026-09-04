"""Eksport ukończonej adjudykacji JSONL Agenta B do CorefUD CoNLL-U.

Kontrakt jest celowo rygorystyczny: żaden brak decyzji nie jest automatycznie
uznawany za zgodę systemów. Dla rekordu spanu ``gold_span`` ma wartość:

* ``false`` — kandydat odrzucony;
* ``true`` — zaakceptowano bieżące ``char_segments``;
* ``[[start, end], ...]`` — ręcznie poprawione segmenty w kanonicznych offsetach
  tekstu bez białych znaków, używanych przez ``scripts/przeglad50.py`` Agenta B.

Każda zaakceptowana wzmianka wymaga ``gold_cluster`` i ``gold_head`` (pozycja
głowy 1..N wśród tokenów wzmianki). Rekord ``random_window`` wymaga listy
``gold_mentions``; pusta lista oznacza, że okno sprawdzono i nie znaleziono
dodatkowych wzmianek. Sampling okien nie gwarantuje jednak kompletności golda.
Każdy dokument wymaga dodatkowo rekordu ``status=full_document_review`` z listą
wszystkich wzmianek pominiętych przez unię systemów (także pustą). Dopiero taki
komplet może zostać wyeksportowany.
"""

from __future__ import annotations

import argparse
import json
import re
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable

_RANGE_ID = re.compile(r"^\d+-\d+$")
_EMPTY_ID = re.compile(r"^\d+\.\d+$")
_SAFE_CLUSTER = re.compile(r"^[A-Za-z0-9_.:]+$")
_COREF_KEYS = ("Entity=", "Bridge=", "SplitAnte=")


class AdjudicationError(ValueError):
    """Błąd niekompletnej albo niespójnej adjudykacji."""


@dataclass(frozen=True)
class TokenRef:
    line_index: int
    sentence_id: str
    start: int
    end: int


@dataclass(frozen=True)
class GoldMention:
    cluster: str
    segments: tuple[tuple[int, int], ...]
    token_segments: tuple[tuple[int, int], ...]
    head: int


def _documents(lines: list[str]) -> dict[str, list[TokenRef]]:
    documents: dict[str, list[TokenRef]] = defaultdict(list)
    doc_id = ""
    sent_id = ""
    char_pos = 0
    for line_index, line in enumerate(lines):
        if line.startswith("# newdoc"):
            if "=" not in line:
                raise AdjudicationError(f"Linia {line_index + 1}: newdoc bez identyfikatora")
            doc_id = line.split("=", 1)[1].strip()
            sent_id = ""
            char_pos = 0
            continue
        if line.startswith("# sent_id"):
            sent_id = line.split("=", 1)[1].strip()
            continue
        if not line or line.startswith("#"):
            continue
        cols = line.split("\t")
        if len(cols) < 10 or _RANGE_ID.match(cols[0]):
            continue
        if not doc_id:
            raise AdjudicationError(f"Linia {line_index + 1}: token przed nagłówkiem newdoc")
        if _EMPTY_ID.match(cols[0]):
            continue
        start = char_pos
        char_pos += len(cols[1])
        documents[doc_id].append(TokenRef(line_index, sent_id, start, char_pos))
    return dict(documents)


def _segments(value: Any, record_id: str) -> tuple[tuple[int, int], ...]:
    if not isinstance(value, list) or not value:
        raise AdjudicationError(f"{record_id}: segmenty muszą być niepustą listą [start, end]")
    result: list[tuple[int, int]] = []
    for raw in value:
        if (
            not isinstance(raw, list)
            or len(raw) != 2
            or not all(isinstance(item, int) for item in raw)
        ):
            raise AdjudicationError(f"{record_id}: niepoprawny segment {raw!r}")
        start, end = raw
        if start < 0 or end <= start:
            raise AdjudicationError(f"{record_id}: niepoprawny zakres [{start}, {end}]")
        if result and start <= result[-1][1]:
            raise AdjudicationError(f"{record_id}: segmenty nie są rozłączne i rosnące")
        result.append((start, end))
    return tuple(result)


def _accepted_candidate(record: dict[str, Any], record_id: str) -> tuple[tuple[int, int], ...] | None:
    decision = record.get("gold_span")
    if decision is None:
        raise AdjudicationError(f"{record_id}: brak decyzji gold_span")
    if decision is False:
        return None
    if decision is True:
        return _segments(record.get("char_segments"), record_id)
    return _segments(decision, record_id)


def _gold_payload(
    record: dict[str, Any], segments: tuple[tuple[int, int], ...], record_id: str
) -> tuple[str, tuple[tuple[int, int], ...], int]:
    cluster = record.get("gold_cluster")
    if cluster is None or not str(cluster).strip():
        raise AdjudicationError(f"{record_id}: zaakceptowany span nie ma gold_cluster")
    cluster = str(cluster).strip()
    if not _SAFE_CLUSTER.fullmatch(cluster):
        raise AdjudicationError(f"{record_id}: niedozwolony gold_cluster={cluster!r}")
    head = record.get("gold_head")
    if isinstance(head, bool) or not isinstance(head, int) or head < 1:
        raise AdjudicationError(f"{record_id}: gold_head musi być dodatnią liczbą całkowitą")
    return cluster, segments, head


def _read_adjudication(
    paths: Iterable[Path],
) -> tuple[
    dict[str, list[tuple[str, tuple[tuple[int, int], ...], int]]],
    set[str],
]:
    by_doc: dict[str, list[tuple[str, tuple[tuple[int, int], ...], int]]] = defaultdict(list)
    fully_reviewed: set[str] = set()
    for path in paths:
        for line_number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
            if not line.strip():
                continue
            record = json.loads(line)
            record_id = str(record.get("id") or f"{path.name}:{line_number}")
            doc_id = str(record.get("doc") or "")
            if not doc_id:
                raise AdjudicationError(f"{record_id}: brak doc")
            status = record.get("status")
            if status in {"random_window", "full_document_review"}:
                additions = record.get("gold_mentions")
                if not isinstance(additions, list):
                    raise AdjudicationError(
                        f"{record_id}: gold_mentions musi być listą (także pustą po kontroli)"
                    )
                for index, mention in enumerate(additions, start=1):
                    if not isinstance(mention, dict):
                        raise AdjudicationError(f"{record_id}: gold_mentions[{index}] nie jest obiektem")
                    child_id = f"{record_id}/gold_mentions/{index}"
                    segments = _segments(mention.get("char_segments"), child_id)
                    by_doc[doc_id].append(_gold_payload(mention, segments, child_id))
                if status == "full_document_review":
                    fully_reviewed.add(doc_id)
                continue
            segments = _accepted_candidate(record, record_id)
            if segments is not None:
                by_doc[doc_id].append(_gold_payload(record, segments, record_id))
    return dict(by_doc), fully_reviewed


def _map_mentions(
    documents: dict[str, list[TokenRef]],
    annotations: dict[str, list[tuple[str, tuple[tuple[int, int], ...], int]]],
    fully_reviewed: set[str],
) -> dict[str, list[GoldMention]]:
    unknown = sorted(set(annotations) - set(documents))
    if unknown:
        raise AdjudicationError(f"Adjudykacja zawiera dokumenty nieobecne w CoNLL-U: {unknown}")
    incomplete = sorted(set(documents) - fully_reviewed)
    if incomplete:
        raise AdjudicationError(
            "Brak rekordu full_document_review dla dokumentów: " + ", ".join(incomplete)
        )
    mapped: dict[str, list[GoldMention]] = {}
    for doc_id, tokens in documents.items():
        starts = {token.start: index for index, token in enumerate(tokens)}
        ends = {token.end: index for index, token in enumerate(tokens)}
        seen: set[tuple[tuple[int, int], ...]] = set()
        mentions: list[GoldMention] = []
        for cluster, segments, head in annotations.get(doc_id, []):
            token_segments: list[tuple[int, int]] = []
            token_count = 0
            for start, end in segments:
                if start not in starts or end not in ends:
                    raise AdjudicationError(
                        f"{doc_id}: segment [{start}, {end}] nie trafia w granice tokenów"
                    )
                first, last = starts[start], ends[end]
                if first > last or tokens[first].sentence_id != tokens[last].sentence_id:
                    raise AdjudicationError(
                        f"{doc_id}: segment [{start}, {end}] przecina granicę zdania"
                    )
                token_segments.append((first, last))
                token_count += last - first + 1
            key = tuple(token_segments)
            if key in seen:
                raise AdjudicationError(f"{doc_id}: ta sama wzmianka występuje więcej niż raz: {segments}")
            if head > token_count:
                raise AdjudicationError(
                    f"{doc_id}: gold_head={head} przekracza {token_count} tokenów wzmianki"
                )
            seen.add(key)
            mentions.append(GoldMention(cluster, segments, key, head))
        mapped[doc_id] = mentions
    return mapped


def _entity_marks(mentions: list[GoldMention], n_tokens: int) -> list[list[str]]:
    opens: list[list[tuple[int, int, str, int]]] = [[] for _ in range(n_tokens)]
    closes: list[list[tuple[int, int, str]]] = [[] for _ in range(n_tokens)]
    for mention in mentions:
        part_count = len(mention.token_segments)
        eid = f"gold_{mention.cluster}"
        for part, (start, end) in enumerate(mention.token_segments, start=1):
            label = f"{eid}[{part}/{part_count}]" if part_count > 1 else eid
            opens[start].append((start, end, label, mention.head))
            if start != end:
                closes[end].append((start, end, label))
    marks: list[list[str]] = [[] for _ in range(n_tokens)]
    for token_index in range(n_tokens):
        for start, _end, label in sorted(
            closes[token_index], key=lambda item: (-item[0], item[2])
        ):
            marks[token_index].append(f"{label})")
        for start, end, label, head in sorted(
            opens[token_index], key=lambda item: (-item[1], item[2])
        ):
            if start == end:
                marks[token_index].append(f"({label}-x-{head}-)")
            else:
                marks[token_index].append(f"({label}-x-{head}-")
    return marks


def export_adjudication(source: Path, adjudication_dir: Path, output: Path) -> dict[str, int]:
    lines = source.read_text(encoding="utf-8-sig").splitlines()
    documents = _documents(lines)
    paths = sorted(adjudication_dir.glob("*.jsonl"))
    if not paths:
        raise AdjudicationError(f"Brak plików JSONL w {adjudication_dir}")
    annotations, fully_reviewed = _read_adjudication(paths)
    mapped = _map_mentions(documents, annotations, fully_reviewed)
    marks_by_line: dict[int, list[str]] = {}
    for doc_id, tokens in documents.items():
        marks = _entity_marks(mapped[doc_id], len(tokens))
        for token, token_marks in zip(tokens, marks):
            marks_by_line[token.line_index] = token_marks

    output_lines: list[str] = []
    for line_index, line in enumerate(lines):
        if line_index not in marks_by_line:
            output_lines.append(line)
            continue
        cols = line.split("\t")
        misc = [
            item
            for item in cols[9].split("|")
            if item and item != "_" and not item.startswith(_COREF_KEYS)
        ]
        if marks_by_line[line_index]:
            misc.append("Entity=" + "".join(marks_by_line[line_index]))
        cols[9] = "|".join(misc) if misc else "_"
        output_lines.append("\t".join(cols))

    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text("\n".join(output_lines).rstrip("\n") + "\n\n", encoding="utf-8", newline="\n")
    return {
        "documents": len(documents),
        "mentions": sum(len(items) for items in mapped.values()),
        "clusters": len({(doc_id, mention.cluster) for doc_id, items in mapped.items() for mention in items}),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--adjudication-dir", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    summary = export_adjudication(args.source, args.adjudication_dir, args.output)
    print(json.dumps(summary, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

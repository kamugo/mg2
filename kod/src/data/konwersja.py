"""Convert CorefUD CoNLL-U files to the project's document-level JSONL schema."""

from __future__ import annotations

import argparse
import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Iterable, Iterator


@dataclass
class Document:
    """Mutable representation of one document during CoNLL-U parsing."""

    doc_id: str
    source: str
    tokens: list[dict[str, object]] = field(default_factory=list)
    mentions: list[dict[str, object]] = field(default_factory=list)
    open_mentions: dict[str, list[tuple[int, str]]] = field(default_factory=dict)
    sentence_id: int = 0

    def close_open_mentions(self) -> None:
        if self.open_mentions:
            dangling = ", ".join(sorted(self.open_mentions))
            raise ValueError(f"{self.doc_id}: unclosed Entity annotations: {dangling}")

    def as_json(self) -> dict[str, object]:
        self.close_open_mentions()
        forms = [str(token["form"]) for token in self.tokens if not token["is_empty"]]
        return {
            "schema_version": "1.0",
            "doc_id": self.doc_id,
            "source": self.source,
            "text": " ".join(forms),
            "tokens": self.tokens,
            "mentions": sorted(
                self.mentions, key=lambda mention: (mention["start"], mention["end"])
            ),
        }


def _parse_misc(misc: str) -> dict[str, str]:
    if misc == "_":
        return {}
    values: dict[str, str] = {}
    for part in misc.split("|"):
        key, separator, value = part.partition("=")
        if separator:
            values[key] = value
    return values


def _entity_id(payload: str) -> str:
    """Return the CorefUD entity id, leaving descriptive suffixes out."""
    return payload.split("-")[0].split("[")[0].strip()


def _mention_key(payload: str) -> str:
    """Return the event key, preserving a discontinuous-part marker."""
    return payload.split("-")[0].strip()


def _consume_entity(doc: Document, value: str, token_index: int) -> None:
    """Convert bracketed CorefUD Entity values to half-open mention spans."""
    def close(mention_key: str) -> None:
        stack = doc.open_mentions.get(mention_key)
        if not stack:
            raise ValueError(
                f"{doc.doc_id}: closing Entity={mention_key} without an opening"
            )
        start, descriptor = stack.pop()
        if not stack:
            doc.open_mentions.pop(mention_key, None)
        doc.mentions.append({
            "mention_id": f"{doc.doc_id}:m{len(doc.mentions)}",
            "entity_id": _entity_id(descriptor),
            "start": start,
            "end": token_index + 1,
            "descriptor": descriptor,
            "is_empty": bool(doc.tokens[token_index]["is_empty"]),
        })

    # CorefUD concatenates events without separators, e.g.
    # ``(e19--1-id:x)e17)e16)``.  A regular expression that waits for the
    # next opening parenthesis silently swallows the adjacent close events.
    position = 0
    while position < len(value):
        if value[position] == "(":
            next_open = value.find("(", position + 1)
            next_close = value.find(")", position + 1)
            singleton = next_close >= 0 and (next_open < 0 or next_close < next_open)
            boundary = next_close if singleton else next_open
            if boundary < 0:
                boundary = len(value)
            payload = value[position + 1 : boundary].strip()
            if not payload:
                raise ValueError(f"{doc.doc_id}: empty Entity opening in {value!r}")
            mention_key = _mention_key(payload)
            doc.open_mentions.setdefault(mention_key, []).append((token_index, payload))
            if singleton:
                close(mention_key)
                position = boundary + 1
            else:
                position = boundary
            continue

        next_close = value.find(")", position)
        if next_close < 0:
            raise ValueError(f"{doc.doc_id}: malformed Entity value {value!r}")
        mention_key = value[position:next_close].strip()
        if not mention_key:
            raise ValueError(f"{doc.doc_id}: empty Entity closing in {value!r}")
        close(mention_key)
        position = next_close + 1


def parse_conllu(lines: Iterable[str], source: str) -> Iterator[dict[str, object]]:
    """Yield documents from a CoNLL-U/CorefUD stream."""
    document: Document | None = None
    auto_id = 0
    for line_number, raw_line in enumerate(lines, start=1):
        line = raw_line.rstrip("\n")
        if line.startswith("# newdoc id ="):
            if document and document.tokens:
                yield document.as_json()
            document = Document(doc_id=line.split("=", 1)[1].strip(), source=source)
            continue
        if line.startswith("# sent_id"):
            if document is None:
                document = Document(doc_id=f"doc-{auto_id}", source=source)
                auto_id += 1
            document.sentence_id += 1
            continue
        if not line or line.startswith("#"):
            continue
        columns = line.split("\t")
        if len(columns) != 10:
            raise ValueError(f"line {line_number}: expected 10 columns, got {len(columns)}")
        token_id = columns[0]
        if "-" in token_id:
            continue
        if document is None:
            document = Document(doc_id=f"doc-{auto_id}", source=source)
            auto_id += 1
        token_index = len(document.tokens)
        misc = _parse_misc(columns[9])
        document.tokens.append({
            "index": token_index,
            "conllu_id": token_id,
            "form": columns[1],
            "lemma": columns[2],
            "upos": columns[3],
            "feats": columns[5],
            "sentence_id": document.sentence_id,
            "is_empty": "." in token_id,
        })
        entity = misc.get("Entity")
        if entity:
            _consume_entity(document, entity, token_index)
    if document and document.tokens:
        yield document.as_json()


def convert_file(input_path: Path, output_path: Path, source: str) -> int:
    """Convert one file and return the number of emitted documents."""
    output_path.parent.mkdir(parents=True, exist_ok=True)
    count = 0
    with input_path.open("r", encoding="utf-8") as source_file, output_path.open(
        "w", encoding="utf-8"
    ) as target:
        for document in parse_conllu(source_file, source):
            target.write(json.dumps(document, ensure_ascii=False) + "\n")
            count += 1
    return count


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument("--source", default="CorefUD")
    args = parser.parse_args()
    count = convert_file(args.input, args.output, args.source)
    print(f"Converted {count} documents to {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

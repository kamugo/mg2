"""Build a reproducible silver Polish legal coreference corpus from Sejm ELI.

The canonical interchange file is CorefUD-style CoNLL-U.  A richer JSONL file
keeps character offsets and provenance, while CSV files support human review.
Annotations are predictions of Stanza's Polish coreference model and must not be
described as gold labels until they have been manually verified.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import io
import json
import random
import re
import sys
import unicodedata
import urllib.error
import urllib.request
from collections import Counter, defaultdict, deque
from dataclasses import dataclass
from datetime import UTC, datetime
from html.parser import HTMLParser
from pathlib import Path
from typing import Any, Iterable
from urllib.parse import urlparse


USER_AGENT = "mg2-legal-coreference-silver-corpus/1.0"
SCHEMA_VERSION = "legal-coref-silver-1.0"
DEFAULT_YEARS = tuple(range(2017, 2025))
DEFAULT_PUBLISHERS = ("DU", "MP")

# Avoid the ELI series dominated by lists of named private persons.  The corpus
# is meant to model legal drafting, not to collect personal data.
PERSONAL_TITLE_PATTERNS = (
    "nadania order",
    "nadania odznacze",
    "nadania obywatelstwa",
    "powołania do pełnienia urzędu na stanowisku sędziego",
    "odwołania konsula",
    "mianowania ambasadora",
)


class _TextExtractor(HTMLParser):
    BLOCK_TAGS = {
        "article", "blockquote", "br", "div", "h1", "h2", "h3", "h4",
        "li", "ol", "p", "section", "table", "td", "th", "tr", "ul",
    }

    def __init__(self) -> None:
        super().__init__()
        self.parts: list[str] = []
        self.ignored_depth = 0

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        del attrs
        tag = tag.casefold()
        if tag in {"script", "style", "noscript"}:
            self.ignored_depth += 1
        elif tag in self.BLOCK_TAGS and self.parts and self.parts[-1] != "\n":
            self.parts.append("\n")

    def handle_endtag(self, tag: str) -> None:
        tag = tag.casefold()
        if tag in {"script", "style", "noscript"} and self.ignored_depth:
            self.ignored_depth -= 1
        elif tag in self.BLOCK_TAGS and not self.ignored_depth:
            self.parts.append("\n")

    def handle_data(self, data: str) -> None:
        if not self.ignored_depth and data.strip():
            self.parts.append(data)


def _request(url: str, timeout: int = 60, attempts: int = 4) -> bytes:
    if urlparse(url).scheme != "https":
        raise ValueError(f"Only HTTPS URLs are accepted: {url}")
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    error: Exception | None = None
    for _ in range(attempts):
        try:
            with urllib.request.urlopen(request, timeout=timeout) as response:
                return response.read()
        except (urllib.error.URLError, TimeoutError) as exc:
            error = exc
    raise RuntimeError(f"Download failed for {url}: {error}")


def _sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _sha256_file(path: Path) -> str:
    return _sha256_bytes(path.read_bytes())


def _safe_text(value: object) -> str:
    return "" if value is None else str(value)


def html_to_text(data: bytes) -> str:
    parser = _TextExtractor()
    parser.feed(data.decode("utf-8", errors="replace"))
    lines: list[str] = []
    for line in "".join(parser.parts).splitlines():
        normalized = re.sub(r"\s+", " ", line.replace("\xa0", " ")).strip()
        if normalized:
            lines.append(normalized)
    # Newlines in ELI HTML mostly reflect visual layout, not linguistic units.
    return re.sub(r"\s+", " ", " ".join(lines)).strip()


def truncate_at_boundary(text: str, max_words: int) -> tuple[str, bool]:
    matches = list(re.finditer(r"\S+", text))
    if len(matches) <= max_words:
        return text.strip(), False
    hard_end = matches[max_words - 1].end()
    search_start = matches[max(int(max_words * 0.65), 1) - 1].start()
    window = text[search_start:hard_end]
    boundaries = list(re.finditer(r"[.!?](?:[\"”»)]*)\s+", window))
    end = search_start + boundaries[-1].end() if boundaries else hard_end
    return text[:end].strip(), True


def _is_personal_title(title: str) -> bool:
    folded = title.casefold()
    return any(pattern in folded for pattern in PERSONAL_TITLE_PATTERNS)


def _load_eli_list(publisher: str, year: int, timeout: int) -> list[dict[str, Any]]:
    url = f"https://api.sejm.gov.pl/eli/acts/{publisher}/{year}"
    payload = json.loads(_request(url, timeout=timeout).decode("utf-8"))
    items = payload.get("items", []) if isinstance(payload, dict) else payload
    if not isinstance(items, list):
        raise RuntimeError(f"Unexpected ELI response shape: {url}")
    return [item for item in items if isinstance(item, dict)]


def _round_robin_candidates(
    items: Iterable[dict[str, Any]], seed: int
) -> list[dict[str, Any]]:
    groups: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for item in items:
        if not (item.get("textHTML") or item.get("textPDF")) or item.get("pos") is None:
            continue
        title = _safe_text(item.get("title"))
        if _is_personal_title(title):
            continue
        groups[_safe_text(item.get("type")) or "inne"].append(item)
    rng = random.Random(seed)
    queues: dict[str, deque[dict[str, Any]]] = {}
    for act_type, group in groups.items():
        rng.shuffle(group)
        queues[act_type] = deque(group)
    result: list[dict[str, Any]] = []
    # Prefer rare types first in every round so laws do not drown out decrees.
    type_order = sorted(queues, key=lambda key: (len(queues[key]), key.casefold()))
    while type_order:
        next_order: list[str] = []
        for act_type in type_order:
            queue = queues[act_type]
            if queue:
                result.append(queue.popleft())
            if queue:
                next_order.append(act_type)
        type_order = next_order
    return result


def split_for_rank(stratum_index: int, rank: int) -> str:
    """Return an exact 320/40/40 split for 16 strata of 25 documents."""
    if rank < 20:
        return "train"
    if stratum_index % 2 == 0:
        return "dev" if rank < 23 else "test"
    return "dev" if rank < 22 else "test"


def collect_documents(args: argparse.Namespace) -> list[dict[str, Any]]:
    raw_dir = args.raw_dir.resolve()
    docs_dir = raw_dir / "documents"
    docs_dir.mkdir(parents=True, exist_ok=True)
    records: list[dict[str, Any]] = []
    strata = [(publisher, year) for year in args.years for publisher in args.publishers]

    for stratum_index, (publisher, year) in enumerate(strata):
        print(f"Collecting {publisher}/{year} ...", flush=True)
        items = _load_eli_list(publisher, year, args.timeout)
        candidates = _round_robin_candidates(
            items, seed=args.seed + year * 31 + sum(map(ord, publisher))
        )
        accepted = 0
        for item in candidates:
            if accepted >= args.per_stratum:
                break
            position = int(item["pos"])
            doc_id = f"{publisher}-{year}-{position}"
            source_format = "html" if item.get("textHTML") else "pdf"
            url = f"https://api.sejm.gov.pl/eli/acts/{publisher}/{year}/{position}/text.{source_format}"
            try:
                source_bytes = _request(url, timeout=args.timeout)
                if source_format == "html":
                    full_text = html_to_text(source_bytes)
                else:
                    from pypdf import PdfReader

                    reader = PdfReader(io.BytesIO(source_bytes))
                    page_text = [page.extract_text() or "" for page in reader.pages]
                    full_text = re.sub(
                        r"\s+", " ", "\n".join(page_text).replace("\xa0", " ")
                    ).strip()
            except RuntimeError as exc:
                print(f"  skip {doc_id}: {exc}", file=sys.stderr, flush=True)
                continue
            except Exception as exc:
                print(f"  skip {doc_id}: PDF/text extraction failed: {exc}", file=sys.stderr, flush=True)
                continue
            excerpt, truncated = truncate_at_boundary(full_text, args.max_words)
            if len(excerpt) < args.min_chars:
                continue
            split = split_for_rank(stratum_index, accepted)
            text_path = docs_dir / f"{doc_id}.txt"
            metadata_path = docs_dir / f"{doc_id}.metadata.json"
            text_path.write_text(excerpt + "\n", encoding="utf-8")
            enriched = {
                "doc_id": doc_id,
                "split": split,
                "source": "Sejm ELI",
                "source_url": url,
                "source_format": source_format,
                "source_sha256": _sha256_bytes(source_bytes),
                "publisher": publisher,
                "year": year,
                "position": position,
                "act_type": _safe_text(item.get("type")) or "inne",
                "title": _safe_text(item.get("title")),
                "promulgation": item.get("promulgation"),
                "eli": item.get("ELI"),
                "is_excerpt": truncated,
                "excerpt_policy": f"start of act, at most {args.max_words} whitespace tokens, closed at sentence boundary when available",
                "source_metadata": item,
            }
            metadata_path.write_text(
                json.dumps(enriched, ensure_ascii=False, indent=2) + "\n",
                encoding="utf-8",
            )
            records.append({
                **{key: enriched[key] for key in (
                "doc_id", "split", "source_url", "publisher", "year",
                    "position", "act_type", "title", "is_excerpt",
                )},
                "file": str(text_path.relative_to(raw_dir)).replace("\\", "/"),
                "metadata_file": str(metadata_path.relative_to(raw_dir)).replace("\\", "/"),
                "characters": len(excerpt),
                "whitespace_tokens": len(excerpt.split()),
                "sha256": _sha256_file(text_path),
                "source_format": source_format,
                "source_sha256": _sha256_bytes(source_bytes),
            })
            accepted += 1
        if accepted != args.per_stratum:
            raise RuntimeError(
                f"Could only collect {accepted}/{args.per_stratum} usable documents for {publisher}/{year}"
            )

    expected = len(strata) * args.per_stratum
    if len(records) != expected:
        raise AssertionError(f"Expected {expected} documents, got {len(records)}")
    manifest = {
        "schema_version": SCHEMA_VERSION,
        "created_at": datetime.now(UTC).isoformat(),
        "selection": {
            "years": args.years,
            "publishers": args.publishers,
            "per_stratum": args.per_stratum,
            "seed": args.seed,
            "max_words": args.max_words,
            "personal_title_exclusions": PERSONAL_TITLE_PATTERNS,
        },
        "license_note": "Official acts from Sejm ELI; verify the current reuse rules and personal-data policy before redistribution.",
        "records": records,
    }
    (raw_dir / "manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    return records


def load_records(raw_dir: Path) -> list[dict[str, Any]]:
    manifest_path = raw_dir.resolve() / "manifest.json"
    payload = json.loads(manifest_path.read_text(encoding="utf-8"))
    records = payload.get("records")
    if not isinstance(records, list):
        raise RuntimeError(f"No records in {manifest_path}")
    return records


def normalize_mention(text: str) -> str:
    folded = unicodedata.normalize("NFKC", text).casefold()
    return re.sub(r"\W+", " ", folded, flags=re.UNICODE).strip()


def confidence_band(mention_texts: list[str]) -> str:
    """Heuristic review priority, deliberately not a model probability."""
    normalized = [normalize_mention(text) for text in mention_texts if text != "_"]
    if len(mention_texts) == 1:
        return "singleton"
    counts = Counter(value for value in normalized if value)
    if len(counts) == 1 and normalized:
        return "high"
    if any(count > 1 for count in counts.values()):
        return "medium"
    return "low"


def _context(text: str, start: int | None, end: int | None, radius: int = 90) -> str:
    if start is None or end is None:
        return "[ZERO]"
    left = max(0, start - radius)
    right = min(len(text), end + radius)
    snippet = re.sub(r"\s+", " ", text[left:right]).strip()
    return ("…" if left else "") + snippet + ("…" if right < len(text) else "")


@dataclass(frozen=True)
class SurfaceMention:
    mention_id: str
    cluster_id: str
    sentence_index: int
    start_word: int
    end_word: int


def _entity_misc(
    sentence_index: int,
    word_index: int,
    mentions: list[SurfaceMention],
) -> str:
    starts = [m for m in mentions if m.sentence_index == sentence_index and m.start_word == word_index]
    ends = [m for m in mentions if m.sentence_index == sentence_index and m.end_word - 1 == word_index]
    single = {m.mention_id for m in starts if m.end_word - m.start_word == 1}
    opens = sorted(
        (m for m in starts if m.mention_id not in single),
        key=lambda m: (-(m.end_word - m.start_word), m.cluster_id, m.mention_id),
    )
    singles = sorted(
        (m for m in starts if m.mention_id in single),
        key=lambda m: (m.cluster_id, m.mention_id),
    )
    closes = sorted(
        (m for m in ends if m.mention_id not in single),
        key=lambda m: (-m.start_word, m.cluster_id, m.mention_id),
    )
    # A mention that ends on the same token on which another multi-token
    # mention begins is a boundary crossing, not nesting.  Close it before the
    # new opening; otherwise ``(new...old)`` is parsed as a singleton ``new``.
    # A singleton on the closing token is nested and must precede the close.
    chunks: list[str] = []
    if opens:
        chunks.extend(f"{m.cluster_id})" for m in closes)
        closes = []
    chunks.extend(f"({m.cluster_id}--1-id:{m.mention_id}" for m in opens)
    chunks.extend(f"({m.cluster_id}--1-id:{m.mention_id})" for m in singles)
    chunks.extend(f"{m.cluster_id})" for m in closes)
    return "".join(chunks) or "_"


def _coerce_word_index(value: object) -> int | None:
    return value if isinstance(value, int) else None


def annotate_document(
    nlp: Any,
    record: dict[str, Any],
    raw_dir: Path,
) -> tuple[dict[str, Any], str, list[dict[str, str]]]:
    text_path = raw_dir / str(record["file"])
    text_value = text_path.read_text(encoding="utf-8").strip()
    document = nlp(text_value)
    sentences = list(document.sentences)

    tokens: list[dict[str, Any]] = []
    sentence_offsets: list[int] = []
    global_index = 0
    for sent_index, sentence in enumerate(sentences):
        sentence_offsets.append(global_index)
        for word_index, word in enumerate(sentence.words):
            tokens.append({
                "index": global_index,
                "token_index": global_index,
                "sentence_id": sent_index,
                "sentence_index": sent_index,
                "word_index": word_index,
                "id_in_sentence": word_index + 1,
                "form": word.text,
                "lemma": "_",
                "upos": "_",
                "feats": "_",
                "start_char": getattr(word, "start_char", None),
                "end_char": getattr(word, "end_char", None),
            })
            global_index += 1

    all_mentions: list[dict[str, Any]] = []
    clusters: list[dict[str, Any]] = []
    surface_mentions: list[SurfaceMention] = []
    review_rows: list[dict[str, str]] = []
    chain_source = getattr(document, "coref_chains", None)
    if chain_source is None:
        chain_source = getattr(document, "coref", [])

    for chain_number, chain in enumerate(chain_source, start=1):
        cluster_id = f"e{chain_number}"
        chain_mentions = list(getattr(chain, "mentions", chain))
        mention_ids: list[str] = []
        mention_texts: list[str] = []
        contexts: list[str] = []
        for mention_number, mention in enumerate(chain_mentions, start=1):
            mention_id = f"{record['doc_id']}-m{len(all_mentions) + 1:04d}"
            sent_index = int(getattr(mention, "sentence"))
            raw_start = getattr(mention, "start_word")
            raw_end = getattr(mention, "end_word")
            start_word = _coerce_word_index(raw_start)
            end_word = _coerce_word_index(raw_end)
            is_zero = start_word is None or end_word is None
            if not is_zero:
                words = sentences[sent_index].words[start_word:end_word]
                mention_text = " ".join(word.text for word in words)
                start_char = getattr(words[0], "start_char", None) if words else None
                end_char = getattr(words[-1], "end_char", None) if words else None
                start_token = sentence_offsets[sent_index] + start_word
                end_token = sentence_offsets[sent_index] + end_word
                surface_mentions.append(SurfaceMention(
                    mention_id, cluster_id, sent_index, start_word, end_word
                ))
                zero_anchor = None
            else:
                mention_text = "_"
                start_char = end_char = start_token = end_token = None
                zero_anchor = list(raw_start) if isinstance(raw_start, tuple) else raw_start
            mention_ids.append(mention_id)
            mention_texts.append(mention_text)
            contexts.append(_context(text_value, start_char, end_char))
            all_mentions.append({
                "mention_id": mention_id,
                "entity_id": cluster_id,
                "cluster_id": cluster_id,
                "sentence_index": sent_index,
                "start_word": start_word,
                "end_word": end_word,
                "start_token": start_token,
                "end_token": end_token,
                "start": start_token,
                "end": end_token,
                "start_char": start_char,
                "end_char": end_char,
                "text": mention_text,
                "is_zero": is_zero,
                "is_empty": is_zero,
                "zero_anchor": zero_anchor,
                "is_representative": mention_number - 1 == getattr(chain, "representative_index", -1),
                "source": "stanza:pl:udcoref_xlm-roberta-lora",
            })
        band = confidence_band(mention_texts)
        representative = _safe_text(getattr(chain, "representative_text", ""))
        clusters.append({
            "cluster_id": cluster_id,
            "mention_ids": mention_ids,
            "representative": representative,
            "review_priority_band": band,
        })
        review_rows.append({
            "doc_id": str(record["doc_id"]),
            "split": str(record["split"]),
            "cluster_id": cluster_id,
            "chain_size": str(len(mention_ids)),
            "review_priority_band": band,
            "representative": representative,
            "mentions": " || ".join(mention_texts),
            "contexts": " || ".join(contexts),
            "decision": "",
            "corrected_mentions": "",
            "reviewer_note": "",
        })

    conllu: list[str] = [
        f"# newdoc id = {record['doc_id']}",
        "# global.Entity = eid-etype-head-other",
        "# annotation_status = silver-unreviewed",
        "# annotation_source = stanza:pl:udcoref_xlm-roberta-lora",
        f"# source_url = {record['source_url']}",
    ]
    for sent_index, sentence in enumerate(sentences):
        conllu.append(f"# sent_id = {record['doc_id']}-{sent_index + 1}")
        sentence_text = _safe_text(getattr(sentence, "text", "")).replace("\n", " ")
        conllu.append(f"# text = {sentence_text}")
        for word_index, word in enumerate(sentence.words):
            misc = _entity_misc(sent_index, word_index, surface_mentions)
            form = word.text.replace("\t", " ").replace("\n", " ")
            conllu.append(
                f"{word_index + 1}\t{form}\t_\t_\t_\t_\t_\t_\t_\t"
                + (f"Entity={misc}" if misc != "_" else "_")
            )
        conllu.append("")

    zero_count = sum(1 for mention in all_mentions if mention["is_zero"])
    payload = {
        "schema_version": SCHEMA_VERSION,
        "annotation_status": "silver-unreviewed",
        "annotation_source": "stanza:pl:udcoref_xlm-roberta-lora",
        "review_priority_note": "Heuristic band, not calibrated model probability.",
        "doc_id": record["doc_id"],
        "split": record["split"],
        "source": {
            key: record[key] for key in (
                "source_url", "publisher", "year", "position", "act_type", "title", "is_excerpt"
            )
        },
        "text": text_value,
        "tokens": tokens,
        "mentions": all_mentions,
        "clusters": clusters,
        "stats": {
            "sentences": len(sentences),
            "tokens": len(tokens),
            "mentions": len(all_mentions),
            "clusters": len(clusters),
            "zero_mentions": zero_count,
        },
    }
    return payload, "\n".join(conllu).rstrip() + "\n\n", review_rows


def _write_csv(path: Path, rows: list[dict[str, str]], fieldnames: list[str]) -> None:
    with path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def annotate_documents(args: argparse.Namespace, records: list[dict[str, Any]]) -> None:
    try:
        import stanza
        from stanza.pipeline.core import DownloadMethod
    except ImportError as exc:
        raise RuntimeError("Install requirements and the Polish Stanza coref model first") from exc

    raw_dir = args.raw_dir.resolve()
    processed_dir = args.processed_dir.resolve()
    processed_dir.mkdir(parents=True, exist_ok=True)
    print("Loading Stanza Polish coreference model ...", flush=True)
    nlp = stanza.Pipeline(
        "pl",
        processors="tokenize,coref",
        use_gpu=not args.cpu,
        verbose=False,
        download_method=DownloadMethod.REUSE_RESOURCES,
    )

    jsonl_path = processed_dir / "legal-silver-400.jsonl"
    conllu_path = processed_dir / "legal-silver-400.conllu"
    review_rows: list[dict[str, str]] = []
    document_rows: list[dict[str, str]] = []
    totals: Counter[str] = Counter()
    by_split: Counter[str] = Counter()
    by_band: Counter[str] = Counter()
    with jsonl_path.open("w", encoding="utf-8") as jsonl, conllu_path.open("w", encoding="utf-8") as conllu:
        for index, record in enumerate(records, start=1):
            payload, conllu_block, rows = annotate_document(nlp, record, raw_dir)
            jsonl.write(json.dumps(payload, ensure_ascii=False) + "\n")
            conllu.write(conllu_block)
            review_rows.extend(rows)
            by_split[str(record["split"])] += 1
            for key, value in payload["stats"].items():
                totals[key] += int(value)
            for row in rows:
                by_band[row["review_priority_band"]] += 1
            document_rows.append({
                "doc_id": str(record["doc_id"]),
                "split": str(record["split"]),
                "publisher": str(record["publisher"]),
                "year": str(record["year"]),
                "act_type": str(record["act_type"]),
                "title": str(record["title"]),
                "clusters": str(payload["stats"]["clusters"]),
                "mentions": str(payload["stats"]["mentions"]),
                "review_status": "unreviewed",
                "reviewer": "",
                "reviewer_note": "",
            })
            print(
                f"[{index:03d}/{len(records)}] {record['doc_id']}: "
                f"{payload['stats']['tokens']} tokens, {payload['stats']['clusters']} chains",
                flush=True,
            )

    review_fields = [
        "doc_id", "split", "cluster_id", "chain_size", "review_priority_band",
        "representative", "mentions", "contexts", "decision", "corrected_mentions",
        "reviewer_note",
    ]
    _write_csv(processed_dir / "review_chains.csv", review_rows, review_fields)
    document_fields = [
        "doc_id", "split", "publisher", "year", "act_type", "title", "clusters",
        "mentions", "review_status", "reviewer", "reviewer_note",
    ]
    _write_csv(processed_dir / "review_documents.csv", document_rows, document_fields)

    type_counts = Counter(str(record["act_type"]) for record in records)
    publisher_counts = Counter(str(record["publisher"]) for record in records)
    year_counts = Counter(str(record["year"]) for record in records)
    model_path = Path(stanza.resources.common.DEFAULT_MODEL_DIR) / "pl" / "coref" / "udcoref_xlm-roberta-lora.pt"
    output_files = [jsonl_path, conllu_path, processed_dir / "review_chains.csv", processed_dir / "review_documents.csv"]
    manifest = {
        "schema_version": SCHEMA_VERSION,
        "created_at": datetime.now(UTC).isoformat(),
        "annotation_status": "silver-unreviewed",
        "documents": len(records),
        "split_documents": dict(sorted(by_split.items())),
        "publishers": dict(sorted(publisher_counts.items())),
        "years": dict(sorted(year_counts.items())),
        "act_types": dict(sorted(type_counts.items())),
        "annotation": {
            "library": "stanza",
            "library_version": stanza.__version__,
            "language": "pl",
            "processors": "tokenize,coref",
            "coref_package": "udcoref_xlm-roberta-lora",
            "model_sha256": _sha256_file(model_path) if model_path.exists() else None,
            "device": "cpu" if args.cpu else "cuda-if-available",
            "confidence_disclaimer": "review_priority_band is heuristic and is not a calibrated model probability",
        },
        "totals": dict(sorted(totals.items())),
        "review_priority_bands": dict(sorted(by_band.items())),
        "outputs": [
            {"file": path.name, "bytes": path.stat().st_size, "sha256": _sha256_file(path)}
            for path in output_files
        ],
    }
    (processed_dir / "manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--stage", choices=("collect", "annotate", "all"), default="all")
    parser.add_argument("--raw-dir", type=Path, default=Path("data/raw/legal-silver-400"))
    parser.add_argument("--processed-dir", type=Path, default=Path("data/processed/legal-silver-400"))
    parser.add_argument("--years", nargs="+", type=int, default=list(DEFAULT_YEARS))
    parser.add_argument("--publishers", nargs="+", default=list(DEFAULT_PUBLISHERS))
    parser.add_argument("--per-stratum", type=int, default=25)
    parser.add_argument("--seed", type=int, default=20260903)
    parser.add_argument("--max-words", type=int, default=900)
    parser.add_argument("--min-chars", type=int, default=700)
    parser.add_argument("--timeout", type=int, default=60)
    parser.add_argument("--cpu", action="store_true")
    return parser


def main() -> int:
    args = build_parser().parse_args()
    if args.per_stratum < 1 or args.max_words < 100 or args.min_chars < 1:
        raise ValueError("Invalid positive corpus-size constraints")
    if args.stage in {"collect", "all"}:
        records = collect_documents(args)
    else:
        records = load_records(args.raw_dir)
    if args.stage in {"annotate", "all"}:
        annotate_documents(args, records)
    print("Done.", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

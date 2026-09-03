"""Select balanced legal documents and remove Stanza labels for CorPipe input."""

from __future__ import annotations

import argparse
import hashlib
import json
from collections import defaultdict
from datetime import UTC, datetime
from pathlib import Path


def document_blocks(text: str) -> dict[str, str]:
    blocks: dict[str, str] = {}
    current: list[str] = []
    doc_id: str | None = None
    for line in text.splitlines():
        if line.startswith("# newdoc id ="):
            if doc_id is not None:
                blocks[doc_id] = "\n".join(current).rstrip() + "\n\n"
            doc_id = line.split("=", 1)[1].strip()
            current = [line]
        elif doc_id is not None:
            current.append(line)
    if doc_id is not None:
        blocks[doc_id] = "\n".join(current).rstrip() + "\n\n"
    return blocks


def remove_coreference(block: str) -> str:
    output: list[str] = []
    for line in block.splitlines():
        if line.startswith(("# annotation_status", "# annotation_source")):
            continue
        if not line or line.startswith("#"):
            output.append(line)
            continue
        columns = line.split("\t")
        if len(columns) != 10:
            raise ValueError(f"Expected 10 columns, got {len(columns)}: {line!r}")
        misc = [] if columns[9] == "_" else columns[9].split("|")
        misc = [item for item in misc if not item.startswith("Entity=")]
        columns[9] = "|".join(misc) or "_"
        if columns[6] == "_":
            columns[6] = "0"
        output.append("\t".join(columns))
    return "\n".join(output).rstrip() + "\n\n"


def balanced_ids(records: list[dict[str, object]], limit: int) -> list[str]:
    groups: dict[tuple[str, int], list[dict[str, object]]] = defaultdict(list)
    for record in records:
        groups[(str(record["publisher"]), int(record["year"]))].append(record)
    keys = sorted(groups, key=lambda value: (value[1], value[0]))
    selected: list[str] = []
    rank = 0
    while len(selected) < limit:
        progressed = False
        for key in keys:
            group = groups[key]
            if rank < len(group) and len(selected) < limit:
                selected.append(str(group[rank]["doc_id"]))
                progressed = True
        if not progressed:
            break
        rank += 1
    if len(selected) != limit:
        raise ValueError(f"Requested {limit} documents, found {len(selected)}")
    return selected


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--stanza-conllu", type=Path,
        default=Path("data/processed/legal-silver-400/legal-silver-400.conllu"),
    )
    parser.add_argument(
        "--raw-manifest", type=Path,
        default=Path("data/raw/legal-silver-400/manifest.json"),
    )
    parser.add_argument("--output", type=Path, default=Path("data/processed/corpipe26-pilot/legal-20"))
    parser.add_argument("--limit", type=int, default=20)
    parser.add_argument("--doc-ids", nargs="+", help="Explicit document ids instead of balanced selection")
    args = parser.parse_args()

    records = json.loads(args.raw_manifest.read_text(encoding="utf-8"))["records"]
    ids = list(args.doc_ids) if args.doc_ids else balanced_ids(records, args.limit)
    blocks = document_blocks(args.stanza_conllu.read_text(encoding="utf-8"))
    missing = [doc_id for doc_id in ids if doc_id not in blocks]
    if missing:
        raise RuntimeError(f"Stanza output is missing selected documents: {missing}")
    args.output.mkdir(parents=True, exist_ok=True)
    key_path = args.output / "stanza-silver.conllu"
    input_path = args.output / "input.conllu"
    key_path.write_text("".join(blocks[doc_id] for doc_id in ids), encoding="utf-8")
    input_path.write_text(
        "".join(remove_coreference(blocks[doc_id]) for doc_id in ids), encoding="utf-8"
    )
    record_by_id = {str(record["doc_id"]): record for record in records}
    manifest = {
        "created_at": datetime.now(UTC).isoformat(),
        "purpose": "Model-agreement pilot; Stanza silver is not a gold reference.",
        "selection": "round-robin over 16 publisher/year strata",
        "documents": [
            {
                "doc_id": doc_id,
                "publisher": record_by_id[doc_id]["publisher"],
                "year": record_by_id[doc_id]["year"],
                "act_type": record_by_id[doc_id]["act_type"],
            }
            for doc_id in ids
        ],
        "files": {
            key_path.name: sha256(key_path),
            input_path.name: sha256(input_path),
        },
    }
    (args.output / "manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(f"Prepared {len(ids)} documents in {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

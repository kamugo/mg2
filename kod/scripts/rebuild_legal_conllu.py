"""Rebuild CorefUD CoNLL-U from the rich legal JSONL without rerunning a model."""

from __future__ import annotations

import argparse
import json
from collections import defaultdict
from pathlib import Path

from build_legal_silver_corpus import SurfaceMention, _entity_misc


def conllu_document(document: dict[str, object]) -> str:
    doc_id = str(document["doc_id"])
    source = dict(document["source"])
    tokens = list(document["tokens"])
    mentions = [
        SurfaceMention(
            str(mention["mention_id"]),
            str(mention["cluster_id"]),
            int(mention["sentence_index"]),
            int(mention["start_word"]),
            int(mention["end_word"]),
        )
        for mention in document["mentions"]
        if not mention["is_zero"]
    ]
    by_sentence: dict[int, list[dict[str, object]]] = defaultdict(list)
    for token in tokens:
        by_sentence[int(token["sentence_index"])].append(token)
    lines = [
        f"# newdoc id = {doc_id}",
        "# global.Entity = eid-etype-head-other",
        "# annotation_status = silver-unreviewed",
        f"# annotation_source = {document['annotation_source']}",
        f"# source_url = {source['source_url']}",
    ]
    for sentence_index in sorted(by_sentence):
        sentence_tokens = by_sentence[sentence_index]
        lines.append(f"# sent_id = {doc_id}-{sentence_index + 1}")
        lines.append("# text = " + " ".join(str(token["form"]) for token in sentence_tokens))
        for token in sentence_tokens:
            word_index = int(token["word_index"])
            form = str(token["form"]).replace("\t", " ").replace("\n", " ")
            entity = _entity_misc(sentence_index, word_index, mentions)
            misc = f"Entity={entity}" if entity != "_" else "_"
            lines.append(
                f"{int(token['id_in_sentence'])}\t{form}\t_\t_\t_\t_\t_\t_\t_\t{misc}"
            )
        lines.append("")
    return "\n".join(lines).rstrip() + "\n\n"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("jsonl", type=Path)
    parser.add_argument("conllu", type=Path)
    args = parser.parse_args()
    count = 0
    with args.jsonl.open(encoding="utf-8") as source, args.conllu.open("w", encoding="utf-8") as target:
        for line in source:
            if line.strip():
                target.write(conllu_document(json.loads(line)))
                count += 1
    print(f"Rebuilt {count} documents in {args.conllu}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

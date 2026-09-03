"""Invoke the official UA scorer's mention metric despite its disabled CLI evaluate call."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path


def main() -> int:
    """Load the unmodified scorer module and call its public evaluation functions."""
    parser = argparse.ArgumentParser()
    parser.add_argument("scorer_dir", type=Path)
    parser.add_argument("key_file", type=Path)
    parser.add_argument("system_file", type=Path)
    parser.add_argument("--match", default="head")
    parser.add_argument("--keep-singletons", action="store_true")
    cli = parser.parse_args()
    scorer_dir = cli.scorer_dir.resolve()
    sys.path.insert(0, str(scorer_dir))
    from scorer.corefud.reader import CorefUDReader

    arguments = {
        "key_file": str(cli.key_file.resolve()),
        "sys_file": str(cli.system_file.resolve()),
        "format": "corefud",
        "keep_singletons": cli.keep_singletons,
        "keep_split_antecedents": False,
        "keep_zeros": True,
        "zero_match_method": "dependent",
        "match": cli.match,
        "evaluate_discourse_deixis": False,
        "only_split_antecedent": False,
        "allow_boundary_crossing": False,
        "np_only": False,
        "remove_nested_mentions": False,
    }
    reader = CorefUDReader(**arguments)
    reader.get_coref_infos(arguments["key_file"], arguments["sys_file"])
    correct = sum(len(alignments) for alignments in reader.doc_mention_aligns.values())
    gold = sum(
        sum(len(cluster) for cluster in coref_info[0])
        for coref_info in reader.doc_coref_infos.values()
    )
    predicted = sum(
        sum(len(cluster) for cluster in coref_info[1])
        for coref_info in reader.doc_coref_infos.values()
    )
    recall = correct / gold if gold else 0.0
    precision = correct / predicted if predicted else 0.0
    f1 = 2 * precision * recall / (precision + recall) if precision + recall else 0.0
    print("mention")
    print(
        f"Recall: {recall * 100:.2f}  Precision: {precision * 100:.2f}  "
        f"F1: {f1 * 100:.2f}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

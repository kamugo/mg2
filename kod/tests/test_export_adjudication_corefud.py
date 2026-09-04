"""Testy rygorystycznego eksportu adjudykacji do CorefUD."""

from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from scripts.export_adjudication_corefud import AdjudicationError, export_adjudication
from src.data.konwersja import parse_conllu


SOURCE = """# newdoc id = d1
# global.Entity = eid-etype-head-other
# sent_id = d1-s1
1\tAla\t_\tPROPN\t_\t_\t2\tnsubj\t_\t_
2\tma\t_\tVERB\t_\t_\t0\troot\t_\t_
3\tkota\t_\tNOUN\t_\t_\t2\tobj\t_\t_

"""


class ExportAdjudicationCorefudTest(unittest.TestCase):
    def _run(self, records: list[dict]) -> tuple[dict[str, int], str]:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = root / "source.conllu"
            adjudication = root / "adjudication"
            output = root / "gold.conllu"
            adjudication.mkdir()
            source.write_text(SOURCE, encoding="utf-8")
            (adjudication / "d1.jsonl").write_text(
                "".join(json.dumps(record) + "\n" for record in records), encoding="utf-8"
            )
            summary = export_adjudication(source, adjudication, output)
            return summary, output.read_text(encoding="utf-8")

    def test_exports_only_explicitly_completed_decisions(self) -> None:
        summary, text = self._run(
            [
                {
                    "id": "d1#1",
                    "doc": "d1",
                    "status": "shared",
                    "char_segments": [[0, 3]],
                    "gold_span": True,
                    "gold_cluster": "person",
                    "gold_head": 1,
                },
                {
                    "id": "d1#2",
                    "doc": "d1",
                    "status": "only_v2",
                    "char_segments": [[3, 5]],
                    "gold_span": False,
                },
                {
                    "id": "d1#3",
                    "doc": "d1",
                    "status": "only_corpipe",
                    "char_segments": [[5, 9]],
                    "gold_span": [[3, 9]],
                    "gold_cluster": "person",
                    "gold_head": 2,
                },
                {
                    "id": "d1#full-review",
                    "doc": "d1",
                    "status": "full_document_review",
                    "gold_mentions": [],
                },
            ]
        )
        self.assertEqual(summary, {"documents": 1, "mentions": 2, "clusters": 1})
        self.assertIn("Entity=(gold_person-x-1-)", text)
        self.assertIn("Entity=(gold_person-x-2-", text)
        self.assertIn("Entity=gold_person)", text)
        parsed = list(parse_conllu(text.splitlines(keepends=True), "test"))
        self.assertEqual(len(parsed), 1)
        self.assertEqual(
            [(mention["entity_id"], mention["start"], mention["end"]) for mention in parsed[0]["mentions"]],
            [("gold_person", 0, 1), ("gold_person", 1, 3)],
        )

    def test_refuses_unreviewed_candidate(self) -> None:
        with self.assertRaisesRegex(AdjudicationError, "brak decyzji gold_span"):
            self._run(
                [
                    {
                        "id": "d1#1",
                        "doc": "d1",
                        "status": "shared",
                        "char_segments": [[0, 3]],
                        "gold_span": None,
                    }
                ]
            )

    def test_refuses_unreviewed_random_window(self) -> None:
        with self.assertRaisesRegex(AdjudicationError, "gold_mentions musi być listą"):
            self._run(
                [
                    {
                        "id": "d1#window1",
                        "doc": "d1",
                        "status": "random_window",
                        "gold_mentions": None,
                    }
                ]
            )

    def test_random_windows_do_not_claim_exhaustive_gold(self) -> None:
        with self.assertRaisesRegex(AdjudicationError, "Brak rekordu full_document_review"):
            self._run(
                [
                    {
                        "id": "d1#1",
                        "doc": "d1",
                        "status": "shared",
                        "char_segments": [[0, 3]],
                        "gold_span": True,
                        "gold_cluster": "person",
                        "gold_head": 1,
                    },
                    {
                        "id": "d1#window1",
                        "doc": "d1",
                        "status": "random_window",
                        "gold_mentions": [],
                    },
                ]
            )


if __name__ == "__main__":
    unittest.main()

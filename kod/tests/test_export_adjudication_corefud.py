"""Testy rygorystycznego eksportu adjudykacji do CorefUD."""

from __future__ import annotations

import hashlib
import json
import tempfile
import unittest
from pathlib import Path

from scripts.export_adjudication_corefud import (
    AdjudicationError,
    export_adjudication,
)
from src.data.konwersja import parse_conllu


SOURCE = """# newdoc id = d1
# global.Entity = eid-etype-head-other
# sent_id = d1-s1
1\tAla\t_\tPROPN\t_\t_\t2\tnsubj\t_\t_
2\tma\t_\tVERB\t_\t_\t0\troot\t_\t_
3\tkota\t_\tNOUN\t_\t_\t2\tobj\t_\t_

"""


class ExportAdjudicationCorefudTest(unittest.TestCase):
    @staticmethod
    def _manifest(
        doc_id: str, candidate_ids: list[str], window_ids: list[str] | None = None
    ) -> dict:
        windows = window_ids or []
        candidate_digest = hashlib.sha256(
            "\n".join(sorted(candidate_ids)).encode("utf-8")
        ).hexdigest()
        window_digest = hashlib.sha256(
            "\n".join(sorted(windows)).encode("utf-8")
        ).hexdigest()
        return {
            "id": f"{doc_id}#manifest",
            "doc": doc_id,
            "status": "adjudication_manifest",
            "candidate_count": len(candidate_ids),
            "candidate_ids_sha256": candidate_digest,
            "random_window_count": len(windows),
            "random_window_ids_sha256": window_digest,
        }

    def _run(self, records: list[dict], source_text: str = SOURCE) -> tuple[dict[str, int], str]:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = root / "source.conllu"
            adjudication = root / "adjudication"
            output = root / "gold.conllu"
            adjudication.mkdir()
            source.write_text(source_text, encoding="utf-8")
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
                self._manifest("d1", ["d1#1", "d1#2", "d1#3"]),
            ]
        )
        self.assertEqual(summary, {"documents": 1, "mentions": 2, "clusters": 1})
        self.assertIn("Entity=(d1_gold_person-x-1-)", text)
        self.assertIn("Entity=(d1_gold_person-x-2-", text)
        self.assertIn("Entity=d1_gold_person)", text)
        parsed = list(parse_conllu(text.splitlines(keepends=True), "test"))
        self.assertEqual(len(parsed), 1)
        self.assertEqual(
            [(mention["entity_id"], mention["start"], mention["end"]) for mention in parsed[0]["mentions"]],
            [("d1_gold_person", 0, 1), ("d1_gold_person", 1, 3)],
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

    def test_refuses_crossing_mentions_of_the_same_cluster(self) -> None:
        records = [
            {
                "id": "d1#1",
                "doc": "d1",
                "status": "shared",
                "char_segments": [[0, 5]],
                "gold_span": True,
                "gold_cluster": "c",
                "gold_head": 1,
            },
            {
                "id": "d1#2",
                "doc": "d1",
                "status": "only_v2",
                "char_segments": [[3, 9]],
                "gold_span": True,
                "gold_cluster": "c",
                "gold_head": 1,
            },
            {
                "id": "d1#full-review",
                "doc": "d1",
                "status": "full_document_review",
                "gold_mentions": [],
            },
            self._manifest("d1", ["d1#1", "d1#2"]),
        ]
        with self.assertRaisesRegex(AdjudicationError, "krzyżujące się wzmianki"):
            self._run(records)

    def test_refuses_crossing_parts_with_nested_mention_envelopes(self) -> None:
        source = """# newdoc id = d1
# global.Entity = eid-etype-head-other
# sent_id = d1-s1
1\tA\t_\tNOUN\t_\t_\t0\troot\t_\t_
2\tB\t_\tNOUN\t_\t_\t1\tdep\t_\t_
3\tC\t_\tNOUN\t_\t_\t1\tdep\t_\t_
4\tD\t_\tNOUN\t_\t_\t1\tdep\t_\t_
5\tE\t_\tNOUN\t_\t_\t1\tdep\t_\t_
6\tF\t_\tNOUN\t_\t_\t1\tdep\t_\t_
7\tG\t_\tNOUN\t_\t_\t1\tdep\t_\t_
8\tH\t_\tNOUN\t_\t_\t1\tdep\t_\t_
9\tI\t_\tNOUN\t_\t_\t1\tdep\t_\t_

"""
        records = [
            {
                "id": "d1#1",
                "doc": "d1",
                "status": "shared",
                "char_segments": [[0, 3], [7, 9]],
                "gold_span": True,
                "gold_cluster": "c",
                "gold_head": 1,
            },
            {
                "id": "d1#2",
                "doc": "d1",
                "status": "only_corpipe",
                "char_segments": [[1, 4], [6, 8]],
                "gold_span": True,
                "gold_cluster": "c",
                "gold_head": 1,
            },
            {
                "id": "d1#full-review",
                "doc": "d1",
                "status": "full_document_review",
                "gold_mentions": [],
            },
            self._manifest("d1", ["d1#1", "d1#2"]),
        ]
        with self.assertRaisesRegex(AdjudicationError, "obwiednie nieciągłych wzmianek"):
            self._run(records, source)

    def test_refuses_ambiguous_nested_discontinuous_mentions(self) -> None:
        source = """# newdoc id = d1
# global.Entity = eid-etype-head-other
# sent_id = d1-s1
1\tA\t_\tNOUN\t_\t_\t0\troot\t_\t_
2\tB\t_\tNOUN\t_\t_\t1\tdep\t_\t_
3\tC\t_\tNOUN\t_\t_\t1\tdep\t_\t_
4\tD\t_\tNOUN\t_\t_\t1\tdep\t_\t_
5\tE\t_\tNOUN\t_\t_\t1\tdep\t_\t_
6\tF\t_\tNOUN\t_\t_\t1\tdep\t_\t_
7\tG\t_\tNOUN\t_\t_\t1\tdep\t_\t_

"""
        records = [
            {
                "id": "d1#1",
                "doc": "d1",
                "status": "shared",
                "char_segments": [[0, 1], [6, 7]],
                "gold_span": True,
                "gold_cluster": "c",
                "gold_head": 1,
            },
            {
                "id": "d1#2",
                "doc": "d1",
                "status": "only_v2",
                "char_segments": [[2, 3], [4, 5]],
                "gold_span": True,
                "gold_cluster": "c",
                "gold_head": 1,
            },
            {
                "id": "d1#full-review",
                "doc": "d1",
                "status": "full_document_review",
                "gold_mentions": [],
            },
            self._manifest("d1", ["d1#1", "d1#2"]),
        ]
        with self.assertRaisesRegex(AdjudicationError, "obwiednie nieciągłych wzmianek"):
            self._run(records, source)

    def test_refuses_crossing_continuous_and_discontinuous_mentions(self) -> None:
        source = """# newdoc id = d1
# global.Entity = eid-etype-head-other
# sent_id = d1-s1
1\tA\t_\tNOUN\t_\t_\t0\troot\t_\t_
2\tB\t_\tNOUN\t_\t_\t1\tdep\t_\t_
3\tC\t_\tNOUN\t_\t_\t1\tdep\t_\t_
4\tD\t_\tNOUN\t_\t_\t1\tdep\t_\t_
5\tE\t_\tNOUN\t_\t_\t1\tdep\t_\t_

"""
        records = [
            {
                "id": "d1#1",
                "doc": "d1",
                "status": "shared",
                "char_segments": [[0, 3], [4, 5]],
                "gold_span": True,
                "gold_cluster": "c",
                "gold_head": 1,
            },
            {
                "id": "d1#2",
                "doc": "d1",
                "status": "only_corpipe",
                "char_segments": [[1, 4]],
                "gold_span": True,
                "gold_cluster": "c",
                "gold_head": 1,
            },
            {
                "id": "d1#full-review",
                "doc": "d1",
                "status": "full_document_review",
                "gold_mentions": [],
            },
            self._manifest("d1", ["d1#1", "d1#2"]),
        ]
        with self.assertRaisesRegex(AdjudicationError, "krzyżujące się wzmianki"):
            self._run(records, source)

    def test_sanitizes_coreference_from_empty_nodes(self) -> None:
        source = """# newdoc id = d1
# global.Entity = eid-etype-head-other
# sent_id = d1-s1
1\tAla\t_\tPROPN\t_\t_\t0\troot\t_\tKeep=1|Entity=(stale-x-1-)
1.1\t_\t_\tPRON\t_\t_\t_\t_\t1:dep\tEntity=(leaked-x-1-)|Bridge=leaked<other|SplitAnte=leaked<other

"""
        records = [
            {
                "id": "d1#full-review",
                "doc": "d1",
                "status": "full_document_review",
                "gold_mentions": [],
            },
            self._manifest("d1", []),
        ]
        summary, text = self._run(records, source)
        self.assertEqual(summary, {"documents": 1, "mentions": 0, "clusters": 0})
        self.assertNotIn("leaked", text)
        self.assertNotIn("stale", text)
        self.assertNotIn("Bridge=", text)
        self.assertNotIn("SplitAnte=", text)
        self.assertIn("Keep=1", text)
        self.assertIn("1.1\t_\t_\tPRON\t_\t_\t_\t_\t1:dep\t_", text)
        parsed = list(parse_conllu(text.splitlines(keepends=True), "test"))
        self.assertEqual(parsed[0]["mentions"], [])

    def test_refuses_manifest_that_hides_a_missing_candidate(self) -> None:
        records = [
            {
                "id": "d1#1",
                "doc": "d1",
                "status": "shared",
                "char_segments": [[0, 3]],
                "gold_span": False,
            },
            {
                "id": "d1#full-review",
                "doc": "d1",
                "status": "full_document_review",
                "gold_mentions": [],
            },
            {
                **self._manifest("d1", ["d1#1", "d1#missing"]),
                "candidate_ids_sha256": hashlib.sha256(b"d1#1").hexdigest(),
            },
        ]
        with self.assertRaisesRegex(AdjudicationError, "candidate_count=2, oczekiwano 1"):
            self._run(records)
        records[-1] = {
            **self._manifest("d1", ["d1#other"]),
            "candidate_count": 1,
        }
        with self.assertRaisesRegex(AdjudicationError, "candidate_ids_sha256"):
            self._run(records)

    def test_refuses_boolean_manifest_counts(self) -> None:
        manifest = self._manifest("d1", [])
        manifest["candidate_count"] = False
        records = [
            {
                "id": "d1#full-review",
                "doc": "d1",
                "status": "full_document_review",
                "gold_mentions": [],
            },
            manifest,
        ]
        with self.assertRaisesRegex(AdjudicationError, "candidate_count musi być"):
            self._run(records)

    def test_namespaces_cluster_ids_between_documents(self) -> None:
        source = """# newdoc id = d1
# global.Entity = eid-etype-head-other
# sent_id = d1-s1
1\tA\t_\tNOUN\t_\t_\t0\troot\t_\t_

# newdoc id = d2
# global.Entity = eid-etype-head-other
# sent_id = d2-s1
1\tB\t_\tNOUN\t_\t_\t0\troot\t_\t_

"""
        records: list[dict] = []
        for doc_id in ("d1", "d2"):
            candidate_id = f"{doc_id}#1"
            records.extend(
                [
                    {
                        "id": candidate_id,
                        "doc": doc_id,
                        "status": "shared",
                        "char_segments": [[0, 1]],
                        "gold_span": True,
                        "gold_cluster": "1",
                        "gold_head": 1,
                    },
                    {
                        "id": f"{doc_id}#full-review",
                        "doc": doc_id,
                        "status": "full_document_review",
                        "gold_mentions": [],
                    },
                    self._manifest(doc_id, [candidate_id]),
                ]
            )
        summary, text = self._run(records, source)
        self.assertEqual(summary, {"documents": 2, "mentions": 2, "clusters": 2})
        self.assertIn("Entity=(d1_gold_1-x-1-)", text)
        self.assertIn("Entity=(d2_gold_1-x-1-)", text)
        parsed = list(parse_conllu(text.splitlines(keepends=True), "test"))
        self.assertEqual(
            [document["mentions"][0]["entity_id"] for document in parsed],
            ["d1_gold_1", "d2_gold_1"],
        )

    def test_refuses_missing_or_incompatible_entity_schema_per_document(self) -> None:
        missing_second = """# newdoc id = d1
# global.Entity = eid-etype-head-other
# sent_id = d1-s1
1\tA\t_\tNOUN\t_\t_\t0\troot\t_\t_

# newdoc id = d2
# sent_id = d2-s1
1\tB\t_\tNOUN\t_\t_\t0\troot\t_\t_

"""
        with self.assertRaisesRegex(AdjudicationError, "d2: brak deklaracji"):
            self._run([], missing_second)
        incompatible = SOURCE.replace("eid-etype-head-other", "eid-head")
        with self.assertRaisesRegex(AdjudicationError, "nieobsługiwany schemat"):
            self._run([], incompatible)
        duplicated = SOURCE.replace(
            "# global.Entity = eid-etype-head-other",
            "# global.Entity = eid-etype-head-other\n"
            "# global.Entity = eid-etype-head-other",
        )
        with self.assertRaisesRegex(AdjudicationError, "oczekiwano jednej deklaracji"):
            self._run([], duplicated)

    def test_refuses_duplicate_document_ids(self) -> None:
        duplicate = SOURCE + SOURCE
        with self.assertRaisesRegex(AdjudicationError, "Powtórzony identyfikator # newdoc: d1"):
            self._run([], duplicate)

    def test_requires_unique_sentence_ids_for_surface_tokens(self) -> None:
        without_sent_id = SOURCE.replace("# sent_id = d1-s1\n", "")
        with self.assertRaisesRegex(AdjudicationError, "token powierzchniowy bez"):
            self._run([], without_sent_id)
        repeated = SOURCE + """# sent_id = d1-s1
1\tOla\t_\tPROPN\t_\t_\t0\troot\t_\t_

"""
        with self.assertRaisesRegex(AdjudicationError, "powtórzony sent_id"):
            self._run([], repeated)

    def test_refuses_discontinuous_mention_across_sentences(self) -> None:
        source = """# newdoc id = d1
# global.Entity = eid-etype-head-other
# sent_id = d1-s1
1\tA\t_\tNOUN\t_\t_\t0\troot\t_\t_

# sent_id = d1-s2
1\tX\t_\tNOUN\t_\t_\t0\troot\t_\t_
2\tB\t_\tNOUN\t_\t_\t1\tdep\t_\t_

"""
        records = [
            {
                "id": "d1#1",
                "doc": "d1",
                "status": "shared",
                "char_segments": [[0, 1], [2, 3]],
                "gold_span": True,
                "gold_cluster": "c",
                "gold_head": 1,
            },
            {
                "id": "d1#full-review",
                "doc": "d1",
                "status": "full_document_review",
                "gold_mentions": [],
            },
            self._manifest("d1", ["d1#1"]),
        ]
        with self.assertRaisesRegex(AdjudicationError, "więcej niż jednego zdania"):
            self._run(records, source)

    def test_requires_exactly_ten_conllu_columns(self) -> None:
        eleven_columns = SOURCE.replace(
            "1\tAla\t_\tPROPN\t_\t_\t2\tnsubj\t_\t_",
            "1\tAla\t_\tPROPN\t_\t_\t2\tnsubj\t_\t_\textra",
        )
        with self.assertRaisesRegex(AdjudicationError, "oczekiwano 10 kolumn"):
            self._run([], eleven_columns)

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

from __future__ import annotations

import unittest

from scripts.build_legal_silver_corpus import (
    SurfaceMention,
    _entity_misc,
    confidence_band,
    html_to_text,
    split_for_rank,
    truncate_at_boundary,
)


class LegalSilverCorpusTest(unittest.TestCase):
    def test_exact_document_split_for_default_strata(self) -> None:
        counts = {
            split: sum(
                split_for_rank(stratum, rank) == split
                for stratum in range(16)
                for rank in range(25)
            )
            for split in ("train", "dev", "test")
        }
        self.assertEqual(counts, {"train": 320, "dev": 40, "test": 40})

    def test_truncation_prefers_complete_sentence(self) -> None:
        text, truncated = truncate_at_boundary(
            "Ala ma kota. Kot ma Alę. Trzecie zdanie jest dłuższe.", max_words=6
        )
        self.assertTrue(truncated)
        self.assertEqual(text, "Ala ma kota.")

    def test_html_extraction_removes_code_and_normalizes_layout(self) -> None:
        html = "<html><style>bad</style><p>Art. 1.</p><p>Treść&nbsp;aktu.</p></html>"
        self.assertEqual(html_to_text(html.encode("utf-8")), "Art. 1. Treść aktu.")

    def test_corefud_entity_brackets_keep_nested_mentions(self) -> None:
        mentions = [
            SurfaceMention("m1", "e1", 0, 0, 3),
            SurfaceMention("m2", "e2", 0, 1, 2),
        ]
        self.assertEqual(_entity_misc(0, 0, mentions), "(e1--1-id:m1")
        self.assertEqual(_entity_misc(0, 1, mentions), "(e2--1-id:m2)")
        self.assertEqual(_entity_misc(0, 2, mentions), "e1)")

    def test_crossing_boundary_closes_before_new_opening(self) -> None:
        mentions = [
            SurfaceMention("old", "e1", 0, 0, 2),
            SurfaceMention("new", "e2", 0, 1, 3),
        ]
        self.assertEqual(_entity_misc(0, 1, mentions), "e1)(e2--1-id:new")

    def test_review_band_is_explicitly_heuristic(self) -> None:
        self.assertEqual(confidence_band(["Ustawa", "ustawa"]), "high")
        self.assertEqual(confidence_band(["minister", "on"]), "low")
        self.assertEqual(confidence_band(["organ"]), "singleton")

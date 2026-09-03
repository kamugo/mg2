"""Regression tests for CorefUD conversion."""

from __future__ import annotations

import unittest

from src.data.konwersja import parse_conllu
from scripts.pobierz_dane import _html_to_text


class CorefUDConversionTest(unittest.TestCase):
    def test_eli_extractor_ignores_script_payload(self) -> None:
        html = '<p>Tekst ustawy</p><script>var tree = [{"id": "para_1"}];</script>'
        self.assertEqual(_html_to_text(html.encode("utf-8")), "Tekst ustawy")

    def test_adjacent_nested_entity_events_are_not_swallowed(self) -> None:
        rows = [
            "# newdoc id = nested\n",
            "# sent_id = nested-1\n",
            "1\tA\ta\tNOUN\t_\t_\t0\troot\t_\tEntity=(e1--1-id:a(e2--1-id:b)\n",
            "2\tB\tb\tNOUN\t_\t_\t1\tnmod\t_\tEntity=(e3--1-id:c)e1)e4)\n",
        ]
        # e4 is deliberately unopened: reaching its close proves that e1 and
        # the preceding singleton were parsed as separate adjacent events.
        with self.assertRaisesRegex(ValueError, "closing Entity=e4"):
            list(parse_conllu(rows, "test"))

    def test_multiple_adjacent_closes(self) -> None:
        rows = [
            "# newdoc id = nested\n",
            "# sent_id = nested-1\n",
            "1\tA\ta\tNOUN\t_\t_\t0\troot\t_\tEntity=(e1--1-id:a(e2--1-id:b\n",
            "2\tB\tb\tNOUN\t_\t_\t1\tnmod\t_\tEntity=e2)e1)\n",
        ]
        document = list(parse_conllu(rows, "test"))[0]
        spans = [(item["entity_id"], item["start"], item["end"]) for item in document["mentions"]]
        self.assertEqual(spans, [("e2", 0, 2), ("e1", 0, 2)])

    def test_discontinuous_parts_share_the_underlying_entity(self) -> None:
        rows = [
            "# newdoc id = discontinuous\n",
            "# sent_id = discontinuous-1\n",
            "1\tA\ta\tNOUN\t_\t_\t0\troot\t_\tEntity=(e7[1/2]--1-id:a)\n",
            "2\tB\tb\tNOUN\t_\t_\t1\tdep\t_\tEntity=(e7[2/2]--1-id:a)\n",
        ]
        document = list(parse_conllu(rows, "test"))[0]
        self.assertEqual([item["entity_id"] for item in document["mentions"]], ["e7", "e7"])


if __name__ == "__main__":
    unittest.main()

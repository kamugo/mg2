from __future__ import annotations

import hashlib
import json
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from scripts.build_legal_silver_corpus import (
    SurfaceMention,
    _canonical_text_bytes,
    _load_exclusion_index,
    _entity_misc,
    _read_verified_raw_text,
    _raw_manifest_provenance,
    _round_robin_candidates,
    _selection_strata,
    _stored_text_bytes,
    _verify_raw_manifest_unchanged,
    collect_documents,
    confidence_band,
    html_to_text,
    split_for_rank,
    truncate_at_boundary,
)


class LegalSilverCorpusTest(unittest.TestCase):
    def test_exclusion_index_rejects_manifest_without_records(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            manifest = Path(tmp) / "processed.json"
            manifest.write_text(
                json.dumps({"documents": 2000, "outputs": []}),
                encoding="utf-8",
            )
            with self.assertRaisesRegex(RuntimeError, "No records list"):
                _load_exclusion_index([manifest])

    def test_exclusion_index_rejects_record_without_document_id(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            manifest = Path(tmp) / "raw.json"
            manifest.write_text(
                json.dumps({
                    "records": [{
                        "file": "heldout.txt",
                        "sha256": "a" * 64,
                    }]
                }),
                encoding="utf-8",
            )
            with self.assertRaisesRegex(RuntimeError, "invalid doc_id"):
                _load_exclusion_index([manifest])

    def test_collection_deduplicates_canonical_text_and_backfills_stratum(self) -> None:
        def item(position: int) -> dict[str, object]:
            return {
                "pos": position,
                "textHTML": True,
                "type": "test",
                "title": f"Akt {position}",
            }

        candidates = {
            ("DU", 2020): [item(1), item(2)],
            ("MP", 2020): [item(1), item(2), item(3)],
        }
        bodies = {
            "DU-2020-1": b"<p>Akt A.</p>",
            "DU-2020-2": b"<p>Akt B.</p>",
            "MP-2020-1": b"<p>Akt C.</p>",
            # Different source bytes, identical canonical stored text to DU-2020-1.
            "MP-2020-2": b"<div>Akt&nbsp;A.</div>",
            "MP-2020-3": b"<p>Akt D.</p>",
        }

        def request(url: str, timeout: int) -> bytes:
            del timeout
            publisher, year, position = url.split("/")[-4:-1]
            return bodies[f"{publisher}-{year}-{position}"]

        with tempfile.TemporaryDirectory() as tmp, patch(
            "scripts.build_legal_silver_corpus._load_eli_list",
            side_effect=lambda publisher, year, timeout: candidates[(publisher, year)],
        ), patch(
            "scripts.build_legal_silver_corpus._round_robin_candidates",
            side_effect=lambda items, seed: items,
        ), patch(
            "scripts.build_legal_silver_corpus._request",
            side_effect=request,
        ):
            raw_dir = Path(tmp)
            args = SimpleNamespace(
                raw_dir=raw_dir,
                years=[2020],
                publishers=["DU", "MP"],
                timeout=1,
                seed=7,
                exclude_manifest=[],
                per_stratum=2,
                max_words=100,
                min_chars=1,
            )
            records = collect_documents(args)
            manifest = json.loads(
                (raw_dir / "manifest.json").read_text(encoding="utf-8")
            )
            actual_hashes = {
                record["doc_id"]: hashlib.sha256(
                    (raw_dir / record["file"]).read_bytes()
                ).hexdigest()
                for record in records
            }

        self.assertEqual(
            [record["doc_id"] for record in records],
            ["DU-2020-1", "DU-2020-2", "MP-2020-1", "MP-2020-3"],
        )
        self.assertEqual(len({record["sha256"] for record in records}), 4)
        self.assertEqual(
            actual_hashes,
            {record["doc_id"]: record["sha256"] for record in records},
        )
        self.assertEqual(
            [record["split"] for record in records],
            ["train", "dev", "train", "test"],
        )
        self.assertEqual(manifest["deduplication"]["duplicates_skipped_count"], 1)
        skipped = manifest["deduplication"]["duplicates_skipped"]
        self.assertEqual(skipped[0]["doc_id"], "MP-2020-2")
        self.assertEqual(skipped[0]["duplicate_of_doc_id"], "DU-2020-1")

    def test_collection_deduplicates_against_exclusion_manifest_hash(self) -> None:
        candidates = [
            {"pos": 1, "textHTML": True, "type": "test", "title": "Duplikat"},
            {"pos": 2, "textHTML": True, "type": "test", "title": "Nowy"},
        ]
        bodies = {
            "1": b"<p>Tekst znany.</p>",
            "2": b"<p>Tekst nowy.</p>",
        }

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            exclusion = root / "exclude.json"
            exclusion.write_text(
                json.dumps({
                    "records": [{
                        "doc_id": "OLD-1",
                        "sha256": hashlib.sha256(
                            _stored_text_bytes("Tekst znany.")
                        ).hexdigest(),
                    }]
                }),
                encoding="utf-8",
            )
            args = SimpleNamespace(
                raw_dir=root / "new",
                years=[2020],
                publishers=["DU"],
                timeout=1,
                seed=7,
                exclude_manifest=[exclusion],
                per_stratum=1,
                max_words=100,
                min_chars=1,
            )
            with patch(
                "scripts.build_legal_silver_corpus._load_eli_list",
                return_value=candidates,
            ), patch(
                "scripts.build_legal_silver_corpus._round_robin_candidates",
                side_effect=lambda items, seed: items,
            ), patch(
                "scripts.build_legal_silver_corpus._request",
                side_effect=lambda url, timeout: bodies[url.split("/")[-2]],
            ):
                records = collect_documents(args)
            manifest = json.loads(
                (args.raw_dir / "manifest.json").read_text(encoding="utf-8")
            )

        self.assertEqual([record["doc_id"] for record in records], ["DU-2020-2"])
        self.assertEqual(manifest["deduplication"]["excluded_hashes_loaded"], 1)
        self.assertFalse(
            manifest["deduplication"]["exclusion_hash_coverage_complete"]
        )
        duplicate = manifest["deduplication"]["duplicates_skipped"][0]
        self.assertEqual(duplicate["doc_id"], "DU-2020-1")
        self.assertEqual(duplicate["duplicate_of_doc_id"], "OLD-1")
        self.assertEqual(duplicate["duplicate_source"], "exclusion_manifest")

    def test_exclusion_manifest_without_hash_keeps_legacy_id_exclusion(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            exclusion = root / "exclude.json"
            exclusion.write_text(
                json.dumps({"records": [{"doc_id": "DU-2020-1"}]}),
                encoding="utf-8",
            )
            args = SimpleNamespace(
                raw_dir=root / "new",
                years=[2020],
                publishers=["DU"],
                timeout=1,
                seed=7,
                exclude_manifest=[exclusion],
                per_stratum=1,
                max_words=100,
                min_chars=1,
            )
            candidates = [
                {"pos": 1, "textHTML": True, "type": "test", "title": "Stary"},
                {"pos": 2, "textHTML": True, "type": "test", "title": "Nowy"},
            ]
            with patch(
                "scripts.build_legal_silver_corpus._load_eli_list",
                return_value=candidates,
            ), patch(
                "scripts.build_legal_silver_corpus._round_robin_candidates",
                side_effect=lambda items, seed: items,
            ), patch(
                "scripts.build_legal_silver_corpus._request",
                return_value=b"<p>Nowy tekst.</p>",
            ):
                records = collect_documents(args)
            manifest = json.loads(
                (args.raw_dir / "manifest.json").read_text(encoding="utf-8")
            )

        self.assertEqual([record["doc_id"] for record in records], ["DU-2020-2"])
        dedup = manifest["deduplication"]
        self.assertFalse(dedup["exclusion_hash_coverage_complete"])
        self.assertEqual(
            dedup["exclusion_hash_stats"]["excluded_records_without_usable_hash"],
            1,
        )

    def test_collection_snapshots_exclusion_manifest_provenance_once(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            exclusion = root / "exclude.json"
            original_bytes = json.dumps({"records": []}).encode("utf-8")
            exclusion.write_bytes(original_bytes)
            args = SimpleNamespace(
                raw_dir=root / "new",
                years=[2020],
                publishers=["DU"],
                timeout=1,
                seed=7,
                exclude_manifest=[exclusion],
                per_stratum=1,
                max_words=100,
                min_chars=1,
            )

            def request(url: str, timeout: int) -> bytes:
                del url, timeout
                exclusion.write_text(
                    json.dumps({"records": [{"doc_id": "changed"}]}),
                    encoding="utf-8",
                )
                return b"<p>Nowy tekst.</p>"

            with patch(
                "scripts.build_legal_silver_corpus._load_eli_list",
                return_value=[{
                    "pos": 1,
                    "textHTML": True,
                    "type": "test",
                    "title": "Nowy",
                }],
            ), patch(
                "scripts.build_legal_silver_corpus._round_robin_candidates",
                side_effect=lambda items, seed: items,
            ), patch(
                "scripts.build_legal_silver_corpus._request",
                side_effect=request,
            ):
                collect_documents(args)
            manifest = json.loads(
                (args.raw_dir / "manifest.json").read_text(encoding="utf-8")
            )

        exclusion_entry = manifest["selection"]["exclusion_manifests"][0]
        self.assertEqual(
            exclusion_entry["sha256"], hashlib.sha256(original_bytes).hexdigest()
        )

    def test_candidate_order_is_independent_of_eli_response_order(self) -> None:
        act_types = ("Ustawa", "ustawa", "Rozporządzenie", "rozporządzenie")
        items = [
            {
                "pos": position,
                "textHTML": True,
                "type": act_types[(position - 1) % len(act_types)],
                "title": f"Akt {position}",
            }
            for position in range(1, 9)
        ]
        forward = _round_robin_candidates(items, seed=17)
        reversed_input = _round_robin_candidates(reversed(items), seed=17)
        self.assertEqual(
            [item["pos"] for item in forward],
            [item["pos"] for item in reversed_input],
        )

    def test_strata_order_is_canonical_and_rejects_unsafe_publishers(self) -> None:
        self.assertEqual(
            _selection_strata([2021, 2020, 2021], ["MP", "DU", "MP"]),
            [("DU", 2020), ("MP", 2020), ("DU", 2021), ("MP", 2021)],
        )
        with self.assertRaisesRegex(ValueError, "Unsafe ELI publisher"):
            _selection_strata([2020], ["../../outside"])

    def test_canonical_text_hash_input_is_platform_independent(self) -> None:
        self.assertEqual(_canonical_text_bytes("A\r\nB\r\n"), b"A\nB\n")
        self.assertEqual(_canonical_text_bytes("A\nB\n"), b"A\nB\n")

    def test_processed_provenance_binds_exact_raw_manifest(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            raw_dir = root / "raw"
            processed_dir = root / "processed"
            raw_dir.mkdir()
            processed_dir.mkdir()
            manifest_path = raw_dir / "manifest.json"
            manifest_path.write_text(
                json.dumps({
                    "schema_version": "test-v1",
                    "deduplication": {
                        "policy_version": 1,
                        "duplicates_skipped_count": 1,
                        "duplicates_skipped": [{"doc_id": "duplicate"}],
                    },
                    "records": [{"doc_id": "d1"}],
                }),
                encoding="utf-8",
            )
            expected_sha256 = hashlib.sha256(manifest_path.read_bytes()).hexdigest()
            provenance = _raw_manifest_provenance(raw_dir, processed_dir)

        self.assertEqual(provenance["path"], "../raw/manifest.json")
        self.assertEqual(provenance["records"], 1)
        self.assertEqual(provenance["schema_version"], "test-v1")
        self.assertEqual(provenance["sha256"], expected_sha256)
        self.assertEqual(provenance["deduplication"]["duplicates_skipped_count"], 1)
        self.assertNotIn("duplicates_skipped", provenance["deduplication"])

    def test_processed_provenance_rejects_raw_manifest_change(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            raw_dir = Path(tmp) / "raw"
            raw_dir.mkdir()
            manifest_path = raw_dir / "manifest.json"
            manifest_path.write_text(
                json.dumps({"records": [{"doc_id": "d1"}]}),
                encoding="utf-8",
            )
            expected_sha256 = hashlib.sha256(manifest_path.read_bytes()).hexdigest()
            manifest_path.write_text(
                json.dumps({"records": [{"doc_id": "d2"}]}),
                encoding="utf-8",
            )
            with self.assertRaisesRegex(RuntimeError, "changed during annotation"):
                _verify_raw_manifest_unchanged(raw_dir, expected_sha256)

    def test_annotation_reads_only_raw_text_matching_manifest_hash(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            raw_dir = Path(tmp)
            text_path = raw_dir / "documents" / "d1.txt"
            text_path.parent.mkdir()
            text_path.write_bytes(b"Pierwsza wersja.\n")
            record = {
                "doc_id": "d1",
                "file": "documents/d1.txt",
                "sha256": hashlib.sha256(text_path.read_bytes()).hexdigest(),
            }
            self.assertEqual(
                _read_verified_raw_text(raw_dir, record), "Pierwsza wersja."
            )
            text_path.write_bytes(b"Zmieniona wersja.\n")
            with self.assertRaisesRegex(RuntimeError, "sha256 mismatch"):
                _read_verified_raw_text(raw_dir, record)

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

    def test_exact_document_split_for_two_thousand_documents(self) -> None:
        counts = {
            split: sum(
                split_for_rank(stratum, rank, 50) == split
                for stratum in range(40)
                for rank in range(50)
            )
            for split in ("train", "dev", "test")
        }
        self.assertEqual(counts, {"train": 1600, "dev": 200, "test": 200})

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

"""Verify batch PDF Bronze publication safeguards, provenance and prechecks."""

import hashlib
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import duckdb

from explore_2023_season import build_pdf_bronze_batch


class PdfPitStopBronzeBatchTests(unittest.TestCase):
    def test_missing_later_input_prevents_any_bronze_publication(self):
        """A single missing PDF must abort the batch before creating any output."""
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            first_pdf = root / "data" / "raw" / "source-a" / "report.pdf"
            first_pdf.parent.mkdir(parents=True)
            first_pdf.write_bytes(b"%PDF-1.4 mock")

            catalog = {
                "season": 2023,
                "events": [
                    {"event_id": "course-a", "pdf_path": str(first_pdf.relative_to(root))},
                    {"event_id": "course-b", "pdf_path": "data/raw/source-b/report.pdf"},
                ],
            }

            with self.assertRaises(FileNotFoundError):
                build_pdf_bronze_batch(root, catalog)

            # Verification that no bronze directory was created
            self.assertFalse((root / "data" / "bronze").exists())

    def test_rejects_duplicate_source_ids(self):
        """Duplicate source directory names must be rejected before execution."""
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            pdf = root / "data" / "raw" / "source-a" / "report.pdf"
            pdf.parent.mkdir(parents=True)
            pdf.write_bytes(b"%PDF-1.4 mock")

            catalog_duplicate_sources = {
                "season": 2023,
                "events": [
                    {"event_id": "course-1", "pdf_path": str(pdf.relative_to(root))},
                    {"event_id": "course-2", "pdf_path": str(pdf.relative_to(root))},
                ],
            }
            with self.assertRaisesRegex(ValueError, "duplicate source IDs"):
                build_pdf_bronze_batch(root, catalog_duplicate_sources)

    def test_rejects_duplicate_event_ids(self):
        """Duplicate event IDs with distinct sources must be rejected before execution."""
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            pdf_1 = root / "data" / "raw" / "source-a" / "report.pdf"
            pdf_1.parent.mkdir(parents=True)
            pdf_1.write_bytes(b"%PDF-1.4 mock")

            pdf_2 = root / "data" / "raw" / "source-b" / "report.pdf"
            pdf_2.parent.mkdir(parents=True)
            pdf_2.write_bytes(b"%PDF-1.4 mock")

            catalog_duplicate_events = {
                "season": 2023,
                "events": [
                    {"event_id": "same-event", "pdf_path": str(pdf_1.relative_to(root))},
                    {"event_id": "same-event", "pdf_path": str(pdf_2.relative_to(root))},
                ],
            }
            with self.assertRaisesRegex(ValueError, "duplicate event IDs"):
                build_pdf_bronze_batch(root, catalog_duplicate_events)

    def test_builds_bronze_per_event_with_exact_schema_and_provenance(self):
        """Batch creates separate Bronze Parquet files with 9 raw columns and SHA-256."""
        mock_record = {
            "car_number": "24",
            "pit_number": 1,
            "pit_time_raw": "1:28.481",
            "page_number": 1,
            "column_number": 1,
            "block_line_number": 2,
            "source_line": "1 10:00:00 10:01:28 1:28.481",
        }

        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            events = []
            for event_id in ("daytona", "sebring"):
                source_id = f"imsa-2023-{event_id}-race-pit-stops"
                pdf = root / "data" / "raw" / source_id / "report.pdf"
                pdf.parent.mkdir(parents=True)
                pdf.write_bytes(f"%PDF-1.4 content {event_id}".encode("utf-8"))
                events.append({
                    "event_id": event_id,
                    "pdf_path": str(pdf.relative_to(root)),
                })

            catalog = {"season": 2023, "events": events}

            with patch("moto_sport_bmw_pipeline.bronze.extract_stops", return_value=[mock_record]):
                results = build_pdf_bronze_batch(root, catalog)

            self.assertEqual(len(results), 2)
            for res in results:
                self.assertEqual(res["stops"], 1)

            # Verify on disk schema and content
            for event in events:
                source_id = Path(event["pdf_path"]).parent.name
                bronze_path = root / "data" / "bronze" / source_id / "document.parquet"
                self.assertTrue(bronze_path.is_file())

                with duckdb.connect() as conn:
                    saved = conn.read_parquet(str(bronze_path))
                    self.assertEqual(len(saved.columns), 9)
                    self.assertNotIn("pit_time_seconds", saved.columns)
                    row = saved.fetchone()
                    self.assertEqual(row[0], source_id)
                    self.assertEqual(row[2], "24")
                    self.assertEqual(row[4], "1:28.481")
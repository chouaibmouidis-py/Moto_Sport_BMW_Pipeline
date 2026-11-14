"""Verify multi-event CSV publication and complete-input prechecks."""

import hashlib
from pathlib import Path
import tempfile
import unittest

import duckdb

from explore_2023_season import build_classification_batch


class ClassificationCsvBatchTests(unittest.TestCase):
    def test_separates_event_outputs_and_preserves_provenance(self):
        sql_path = (
            Path(__file__).resolve().parent.parent
            / "sql" / "33_silver_classification_csv.sql"
        )
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "sql").mkdir()
            (root / "sql" / sql_path.name).write_bytes(sql_path.read_bytes())
            events = []
            for event_id in ("course-a", "course-b"):
                source_id = f"test-2023-{event_id}-classification"
                source = root / "data" / "raw" / source_id / "report.csv"
                source.parent.mkdir(parents=True)
                source.write_text(
                    "NUMBER;VEHICLE;POSITION;CLASS;STATUS;IMSA_ManufacturerId\n"
                    " 01 ; BMW M4 GT3 ;inconnue; GTD ; Not started ; 74 \n",
                    encoding="utf-8",
                )
                events.append({
                    "event_id": event_id,
                    "classification_path": str(source.relative_to(root)),
                })
            reference = root / "data" / "current.json"
            reference.write_bytes(b'{"run_id":"previous-run"}')
            results = build_classification_batch(root, {"season": 2023, "events": events})
            self.assertEqual([row["participants"] for row in results], [1, 1])
            self.assertEqual([row["missing_positions"] for row in results], [1, 1])
            for event in events:
                source_id = Path(event["classification_path"]).parent.name
                bronze = root / "data" / "bronze" / source_id / "document.parquet"
                output = (
                    root / "data" / "exploration" / f"{event['event_id']}-2023"
                    / "silver" / "classification.parquet"
                )
                with duckdb.connect() as connection:
                    rows = connection.read_parquet(str(output)).project(
                        "source_id, bronze_sha256, car_number, overall_position, classification_status"
                    ).fetchall()
                self.assertEqual(rows, [(
                    source_id, hashlib.sha256(bronze.read_bytes()).hexdigest(),
                    "01", None, "Not started",
                )])
            self.assertEqual(reference.read_bytes(), b'{"run_id":"previous-run"}')

    def test_missing_later_input_prevents_any_publication(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            first = root / "data" / "raw" / "source-a" / "report.csv"
            first.parent.mkdir(parents=True)
            first.write_text("NUMBER\n24\n", encoding="utf-8")
            catalog = {"season": 2023, "events": [
                {"event_id": "course-a", "classification_path": str(first.relative_to(root))},
                {"event_id": "course-b", "classification_path": "data/raw/source-b/report.csv"},
            ]}
            with self.assertRaises(FileNotFoundError):
                build_classification_batch(root, catalog)
            self.assertFalse((root / "data" / "bronze").exists())
            self.assertFalse((root / "data" / "exploration").exists())

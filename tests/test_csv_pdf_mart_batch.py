"""Verify multi-event mart isolation, input prechecks and failure preservation."""

import shutil
from pathlib import Path
import tempfile
import unittest

import duckdb

from explore_2023_season import build_mart_batch


class CsvPdfMartBatchTests(unittest.TestCase):
    def prepare_inputs(self, root):
        project = Path(__file__).resolve().parent.parent
        (root / "sql").mkdir()
        for filename in (
            "06_pit_stop_summary.sql",
            "28_pit_stop_counts_by_car.sql",
            "29_classification_pit_stop_sources.sql",
            "35_csv_pdf_race_summary.sql",
        ):
            shutil.copyfile(project / "sql" / filename, root / "sql" / filename)
        events = []
        for name, stop_count in (("a", 2), ("b", 1)):
            event = {
                "event_id": name, "session_id": f"session-{name}",
                "classification_path": f"data/raw/class-{name}/report.csv",
                "pdf_path": f"data/raw/pits-{name}/report.pdf",
            }
            events.append(event)
            directory = root / "data" / "exploration" / f"{name}-2023" / "silver"
            directory.mkdir(parents=True)
            with duckdb.connect() as connection:
                connection.sql("""
                    SELECT ? AS source_id, ? AS bronze_sha256,
                           car_number, 'BMW M Hybrid V8' AS car_model
                    FROM (VALUES ('24'), ('57')) AS t(car_number)
                """, params=[f"class-{name}", f"class-version-{name}"]).write_parquet(
                    str(directory / "classification.parquet")
                )
                connection.sql("""
                    SELECT ? AS source_id, ? AS bronze_sha256, ? AS pdf_sha256,
                           '24' AS car_number,
                           range + 1 AS pit_number,
                           60.0 AS pit_time_in_seconds
                    FROM range(?)
                """, params=[
                    f"pits-{name}", f"pit-version-{name}", f"pdf-{name}", stop_count,
                ]).write_parquet(str(directory / "pit_stops.parquet"))
        return {"championship": "test-championship", "season": 2023, "events": events}

    def test_same_car_in_two_events_keeps_its_own_counts_and_versions(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            catalog = self.prepare_inputs(root)
            current = root / "data" / "current.json"
            current.write_bytes(b'{"run_id":"previous-run"}')
            results = build_mart_batch(root, catalog)
            self.assertEqual(
                [(r["event_id"], r["participants"], r["observed_stops"]) for r in results],
                [("a", 2, 2), ("b", 2, 1)],
            )
            for name, count in (("a", 2), ("b", 1)):
                path = root / "data/exploration" / f"{name}-2023/marts/race_car_summary.parquet"
                with duckdb.connect() as connection:
                    rows = connection.read_parquet(str(path)).project("""
                        event_id, session_id, source_id, bronze_sha256, car_number,
                        pit_stop_source_id, pit_stop_bronze_sha256,
                        observed_pit_stop_count, reported_pit_stop_count, stop_detail_status
                    """).order("car_number").fetchall()
                self.assertEqual(rows, [
                    (name, f"session-{name}", f"class-{name}", f"class-version-{name}",
                     "24", f"pits-{name}", f"pit-version-{name}", count, None, "available"),
                    (name, f"session-{name}", f"class-{name}", f"class-version-{name}",
                     "57", f"pits-{name}", f"pit-version-{name}", None, None, "no_stop_details"),
                ])
            self.assertEqual(current.read_bytes(), b'{"run_id":"previous-run"}')

    def test_missing_later_silver_prevents_any_mart_publication(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            catalog = self.prepare_inputs(root)
            (root / "data/exploration/b-2023/silver/pit_stops.parquet").unlink()
            with self.assertRaises(FileNotFoundError):
                build_mart_batch(root, catalog)
            for name in ("a", "b"):
                self.assertFalse((root / "data/exploration" / f"{name}-2023/marts").exists())

    def test_misplaced_source_preserves_existing_mart(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            catalog = self.prepare_inputs(root)
            shutil.copyfile(
                root / "data/exploration/b-2023/silver/pit_stops.parquet",
                root / "data/exploration/a-2023/silver/pit_stops.parquet",
            )
            output = root / "data/exploration/a-2023/marts/race_car_summary.parquet"
            output.parent.mkdir()
            output.write_bytes(b"previous mart")
            with self.assertRaisesRegex(ValueError, "stops without classification"):
                build_mart_batch(root, catalog)
            self.assertEqual(output.read_bytes(), b"previous mart")

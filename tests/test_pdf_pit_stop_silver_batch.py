"""Verify batch PDF Silver transformation safeguards and complete-input prechecks."""

from pathlib import Path
import tempfile
import unittest
import duckdb
from explore_2023_season import build_pdf_silver_batch
import hashlib



class PdfPitStopSilverBatchTests(unittest.TestCase):
    def test_missing_bronze_input_prevents_any_silver_publication(self):
        """If one Bronze parquet is missing, abort before publishing any Silver."""
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)

            bronze_a = root / "data" / "bronze" / "source-a" / "document.parquet"
            bronze_a.parent.mkdir(parents=True)
            bronze_a.write_bytes(b"fake bronze")

            catalog = {
            "season": 2023,
            "events": [
                {"event_id": "course-a", "pdf_path": "data/raw/source-a/report.pdf"},
                {"event_id": "course-b", "pdf_path": "data/raw/source-b/report.pdf"},
            ],
                        }
            with self.assertRaises(FileNotFoundError):
                build_pdf_silver_batch(root, catalog)

            self.assertFalse((root / "data" / "exploration").exists())

    def test_builds_silver_per_event_and_converts_durations(self):
        """Keep each event's stops and Bronze fingerprint separate."""
        project_root = Path(__file__).resolve().parent.parent

        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "sql").mkdir()

            for sql_name in (
                "21_create_duration_parser.sql",
                "34_silver_pdf_pit_stops.sql",
            ):
                (root / "sql" / sql_name).write_bytes(
                    (project_root / "sql" / sql_name).read_bytes()
                )

            cases = [
                ("course-a", "source-a", "1:04.099", 64.099),
                ("course-b", "source-b", "1:30.000", 90.0),
            ]
            events = []
            expected_hashes = {}

            for event_id, source_id, raw_duration, _ in cases:
                bronze_path = (
                    root / "data" / "bronze"
                    / source_id / "document.parquet"
                )
                bronze_path.parent.mkdir(parents=True)

                with duckdb.connect() as connection:
                    connection.sql("""
                        SELECT
                            ? AS source_id,
                            'test-pdf-hash' AS pdf_sha256,
                            '24' AS car_number,
                            1 AS pit_number,
                            ? AS pit_time_raw,
                            1 AS page_number,
                            1 AS column_number,
                            2 AS block_line_number,
                            'synthetic stop line' AS source_line
                    """, params=[source_id, raw_duration]).write_parquet(
                        str(bronze_path)
                    )

                expected_hashes[source_id] = hashlib.sha256(
                    bronze_path.read_bytes()
                ).hexdigest()

                events.append({
                    "event_id": event_id,
                    "pdf_path": f"data/raw/{source_id}/report.pdf",
                })

            results = build_pdf_silver_batch(
                root,
                {"season": 2023, "events": events},
            )

            self.assertCountEqual(
                [
                    (row["event_id"], row["stops"], row["invalid_duration"])
                    for row in results
                ],
                [("course-a", 1, 0), ("course-b", 1, 0)],
            )

            for event_id, source_id, raw_duration, seconds in cases:
                silver_path = (
                    root / "data" / "exploration"
                    / f"{event_id}-2023" / "silver" / "pit_stops.parquet"
                )

                with duckdb.connect() as connection:
                    rows = connection.read_parquet(
                        str(silver_path)
                    ).project("""
                        source_id,
                        bronze_sha256,
                        car_number,
                        pit_number,
                        pit_time_raw,
                        pit_time_in_seconds
                    """).fetchall()

                self.assertEqual(
                    rows,
                    [(
                        source_id,
                        expected_hashes[source_id],
                        "24",
                        1,
                        raw_duration,
                        seconds,
                    )],
                )

    def test_rejects_duplicate_source_ids(self):
        """Duplicate source directory names must be rejected before execution."""
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            bronze = root / "data" / "bronze" / "source-a" / "document.parquet"
            bronze.parent.mkdir(parents=True)
            bronze.write_bytes(b"fake bronze")

            catalog_duplicate_sources = {
                "season": 2023,
                "events": [
                    {"event_id": "course-1", "pdf_path": "data/raw/source-a/report.pdf"},
                    {"event_id": "course-2", "pdf_path": "data/raw/source-a/report.pdf"},
                ],
            }
            with self.assertRaisesRegex(ValueError, "duplicate source IDs"):
                build_pdf_silver_batch(root, catalog_duplicate_sources)

    def test_rejects_duplicate_event_ids(self):
        """Duplicate event IDs with distinct sources must be rejected before execution."""

        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            bronze_1 = root / "data" / "bronze" / "source-a" / "document.parquet"
            bronze_1.parent.mkdir(parents=True)
            bronze_1.write_bytes(b"fake bronze")

            bronze_2 = root / "data" / "bronze" / "source-b" / "document.parquet"
            bronze_2.parent.mkdir(parents=True)
            bronze_2.write_bytes(b"fake bronze")

            catalog_duplicate_events = {
                "season": 2023,
                "events": [
                    {"event_id": "same-event", "pdf_path": "data/raw/source-a/report.pdf"},
                    {"event_id": "same-event", "pdf_path": "data/raw/source-b/report.pdf"},
                ],
            }
            with self.assertRaisesRegex(ValueError, "duplicate event IDs"):
                build_pdf_silver_batch(root, catalog_duplicate_events)

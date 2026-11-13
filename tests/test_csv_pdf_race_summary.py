"""Verify session-specific Silver joins, missing-detail preservation and version guards."""

from pathlib import Path
import unittest

import duckdb

from moto_sport_bmw_pipeline.marts import build_csv_pdf_race_summary
from moto_sport_bmw_pipeline.source_loading import load_exploration_source_sessions


class CsvPdfRaceSummaryTests(unittest.TestCase):
    def prepare_inputs(self, connection):
        catalog = {
            "championship": "test-championship", "season": 2023,
            "events": [
                {
                    "event_id": event, "session_id": f"session-{event}",
                    "classification_path": f"data/raw/class-{event}/report.csv",
                    "pdf_path": f"data/raw/pits-{event}/report.pdf",
                }
                for event in ("a", "b")
            ],
        }
        load_exploration_source_sessions(connection, catalog)
        connection.execute("""
            CREATE TEMP TABLE silver_classification_csv AS
            SELECT * FROM (VALUES
                ('class-a', 'class-version-a', '24'),
                ('class-a', 'class-version-a', '57'),
                ('class-b', 'class-version-b', '24')
            ) AS t(source_id, bronze_sha256, car_number)
        """)
        connection.execute("""
            CREATE TEMP TABLE silver_pdf_pit_stops AS
            SELECT * FROM (VALUES
                ('pits-a', 'pit-version-a', 'pdf-a', '24', 1),
                ('pits-a', 'pit-version-a', 'pdf-a', '24', 2),
                ('pits-b', 'pit-version-b', 'pdf-b', '24', 1)
            ) AS t(source_id, bronze_sha256, pdf_sha256, car_number, pit_number)
        """)

    def test_preserves_participants_and_keeps_sessions_and_versions_separate(self):
        with duckdb.connect() as connection:
            self.prepare_inputs(connection)
            result = build_csv_pdf_race_summary(
                connection, Path(__file__).resolve().parent.parent,
            )
            rows = result.project("""
                event_id, source_id, bronze_sha256, car_number,
                pit_stop_source_id, pit_stop_bronze_sha256, pdf_sha256,
                reported_pit_stop_count, observed_pit_stop_count,
                comparison_status, stop_detail_status
            """).order("event_id, car_number").fetchall()
            self.assertEqual(rows, [
                ('a', 'class-a', 'class-version-a', '24', 'pits-a', 'pit-version-a',
                 'pdf-a', None, 2, 'unavailable_reported_count', 'available'),
                ('a', 'class-a', 'class-version-a', '57', 'pits-a', 'pit-version-a',
                 'pdf-a', None, None, 'unavailable_reported_count', 'no_stop_details'),
                ('b', 'class-b', 'class-version-b', '24', 'pits-b', 'pit-version-b',
                 'pdf-b', None, 1, 'unavailable_reported_count', 'available'),
            ])

    def test_rejects_two_loaded_versions_of_the_same_pdf_source(self):
        with duckdb.connect() as connection:
            self.prepare_inputs(connection)
            connection.execute("""
                INSERT INTO silver_pdf_pit_stops
                VALUES ('pits-a', 'other-version', 'other-pdf', '24', 1)
            """)
            with self.assertRaisesRegex(ValueError, 'multiple source versions'):
                build_csv_pdf_race_summary(
                    connection, Path(__file__).resolve().parent.parent,
                )

    def test_rejects_stops_without_a_participant_in_the_paired_classification(self):
        with duckdb.connect() as connection:
            self.prepare_inputs(connection)
            connection.execute("""
                INSERT INTO silver_pdf_pit_stops
                VALUES ('pits-a', 'pit-version-a', 'pdf-a', '99', 1)
            """)
            with self.assertRaisesRegex(ValueError, 'stops without classification'):
                build_csv_pdf_race_summary(
                    connection, Path(__file__).resolve().parent.parent,
                )

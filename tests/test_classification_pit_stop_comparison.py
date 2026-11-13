"""Verify stop-count comparison statuses and preservation of unmatched participants."""

import unittest
from pathlib import Path

import duckdb


class ClassificationPitStopComparisonTests(unittest.TestCase):
    def test_keeps_participant_without_observed_stops(self):
        with duckdb.connect() as connection:
            connection.execute("""
                CREATE TEMP VIEW silver_classification AS
                SELECT 'classification-a' AS source_id, *
                FROM (VALUES
                    ('24', 3),
                    ('25', 3),
                    ('26', 1),
                    ('70', 0)
                ) AS t(car_number, reported_pit_stop_count)
            """)

            connection.execute("""
                CREATE TEMP VIEW classification_pit_stop_sources AS
                SELECT
                    'classification-a' AS classification_source_id,
                    'pits-a' AS pit_stop_source_id
            """)

            connection.execute("""
                CREATE TEMP VIEW bronze_document AS
                SELECT
                    'pits-a' AS source_id,
                    'version-1' AS bronze_sha256
            """)

            connection.execute("""
                CREATE TEMP VIEW pit_stop_counts_by_car AS
                SELECT 'pits-a' AS source_id, *
                FROM (VALUES
                    ('version-1', '24', 3),
                    ('version-1', '25', 2),
                    ('version-2', '24', 99)
                ) AS t(
                    bronze_sha256,
                    car_number,
                    observed_pit_stop_count
                )
            """)

            query_path = (
                Path(__file__).resolve().parent.parent
                / "sql"
                / "30_classification_pit_stop_comparison.sql"
            )

            query = query_path.read_text(encoding="utf-8")
            comparison = connection.sql(query)

            rows = comparison.project("""
                car_number,
                reported_pit_stop_count,
                observed_pit_stop_count,
                comparison_status
            """).fetchall()

            self.assertCountEqual(
                rows,
                [
                    ("24", 3, 3, "matched"),
                    ("25", 3, 2, "count_mismatch"),
                    ("26", 1, None, "missing_stop_details"),
                    ("70", 0, None, "zero_reported_no_detail"),
                ],
            )

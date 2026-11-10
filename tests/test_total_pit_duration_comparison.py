import unittest
from pathlib import Path

import duckdb


class TotalPitDurationComparisonTests(unittest.TestCase):
    def test_combines_entries_and_uses_last_pit_number(self):
        with duckdb.connect() as connection:
            connection.execute("""
                CREATE TEMP VIEW silver_pit_stops AS
                SELECT
                    'test-source' AS source_id,
                    'version-1' AS bronze_sha256,
                    '24' AS car_number,
                    *
                FROM (VALUES
                    ('1', 3, 50.0, 180.0),
                    ('0', 1, 60.0, 60.0),
                    ('1', 2, 70.0, 130.0)
                ) AS t(
                    source_entry_index,
                    pit_number,
                    pit_time_in_seconds,
                    total_pit_time_seconds
                )
            """)

            query_path = (
                Path(__file__).resolve().parent.parent
                / "sql"
                / "24_compare_total_pit_durations.sql"
            )

            rows = connection.sql(
                query_path.read_text(encoding="utf-8")
            ).fetchall()

            self.assertEqual(
                rows,
                [
                    (
                        "test-source",
                        "version-1",
                        "24",
                        3,
                        3,
                        180.0,
                        3,
                        180.0,
                        "matched",
                    )
                ],
            )


    def test_identifies_partial_sum_when_duration_is_null(self):
        with duckdb.connect() as connection:
            connection.execute("""
                CREATE TEMP VIEW silver_pit_stops AS
                SELECT
                    'test-source' AS source_id,
                    'version-1' AS bronze_sha256,
                    '24' AS car_number,
                    *
                FROM (VALUES
                    ('0', 1, 60.0, 60.0),
                    ('1', 2, NULL, 130.0)
                ) AS t(
                    source_entry_index,
                    pit_number,
                    pit_time_in_seconds,
                    total_pit_time_seconds
                )
            """)

            query_path = (
                Path(__file__).resolve().parent.parent
                / "sql"
                / "24_compare_total_pit_durations.sql"
            )

            rows = connection.sql(
                query_path.read_text(encoding="utf-8")
            ).fetchall()

            self.assertEqual(
                rows,
                [
                    (
                        "test-source",
                        "version-1",
                        "24",
                        2,
                        1,
                        60.0,
                        2,
                        130.0,
                        "incomplete",
                    )
                ],
            )


    def test_detects_mismatch_with_complete_durations(self):
        with duckdb.connect() as connection:
            connection.execute("""
                CREATE TEMP VIEW silver_pit_stops AS
                SELECT
                    'test-source' AS source_id,
                    'version-1' AS bronze_sha256,
                    '24' AS car_number,
                    *
                FROM (VALUES
                    ('0', 1, 60.0, 60.0),
                    ('1', 2, 70.0, 150.0)
                    ) AS t(
                    source_entry_index,
                    pit_number,
                    pit_time_in_seconds,
                    total_pit_time_seconds
                )
            """)

            query_path = (
                Path(__file__).resolve().parent.parent
                / "sql"
                / "24_compare_total_pit_durations.sql"
            )

            rows = connection.sql(
                query_path.read_text(encoding="utf-8")
            ).fetchall()

            self.assertEqual(
                rows,
                [
                    (
                        "test-source",
                        "version-1",
                        "24",
                        2,
                        2,
                        130.0,
                        2,
                        150.0,
                        "mismatch",
                    )
                ],
            )

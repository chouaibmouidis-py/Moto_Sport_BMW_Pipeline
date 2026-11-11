import unittest
from pathlib import Path

import duckdb
from analyze_bronze import validate_race_car_summary


class RaceCarSummaryTests(unittest.TestCase):
    def test_keeps_participant_without_stop_summary(self):
        with duckdb.connect() as connection:
            connection.execute("""
                CREATE TEMP VIEW classification_pit_stop_comparison AS
                SELECT *
                FROM (VALUES
                    ('pits-a', 'version-1', '24'),
                    ('pits-a', 'version-1', '70')
                ) AS t(
                    pit_stop_source_id,
                    pit_stop_bronze_sha256,
                    car_number
                )
            """)

            connection.execute("""
                CREATE TEMP VIEW pit_stop_summary AS
                SELECT *
                FROM (VALUES
                    ('pits-a', 'version-1', '24', 2, 0, 70.0, 100.0),
                    ('pits-a', 'version-2', '24', 2, 0, 999.0, 100.0),
                    ('pits-b', 'version-1', '24', 2, 0, 500.0, 100.0)
                ) AS t(
                    source_id,
                    bronze_sha256,
                    car_number,
                    valid_duration_count,
                    invalid_duration_count,
                    average_pit_time_seconds,
                    duration_coverage_percent
                )
            """)
            query_path = (
                Path(__file__).resolve().parent.parent
                / "sql"
                / "31_race_car_summary.sql"
            )

            rows = connection.sql(
                query_path.read_text(encoding="utf-8")
            ).project("""
                car_number,
                average_pit_time_seconds
            """).fetchall()

            expected = [
                ("24", 70.0),
                ("70", None),
            ]
            self.assertCountEqual(rows, expected)

    def test_rejects_missing_participant(self):
        with duckdb.connect() as connection:
            connection.execute("""
                CREATE TEMP VIEW silver_classification AS
                SELECT *
                FROM (VALUES
                    ('classification-a', 'version-1', '24'),
                    ('classification-a', 'version-1', '70')
                ) AS t(source_id, bronze_sha256, car_number)
            """)

            connection.execute("""
                CREATE TEMP VIEW race_car_summary AS
                SELECT *
                FROM (VALUES
                    ('classification-a', 'version-1', '24')
                ) AS t(source_id, bronze_sha256, car_number)
            """)

            with self.assertRaisesRegex(
                ValueError,
                "participant keys differ",
            ):
                validate_race_car_summary(connection)


    def test_rejects_replaced_participant(self):
        with duckdb.connect() as connection:
            connection.execute("""
                CREATE TEMP VIEW silver_classification AS
                SELECT *
                FROM (VALUES
                    ('classification-a', 'version-1', '24'),
                    ('classification-a', 'version-1', '70')
                ) AS t(source_id, bronze_sha256, car_number)
            """)

            connection.execute("""
                CREATE TEMP VIEW race_car_summary AS
                SELECT *
                FROM (VALUES
                    ('classification-a', 'version-1', '24'),
                    ('classification-a', 'version-1', '99')
                ) AS t(source_id, bronze_sha256, car_number)
            """)

            with self.assertRaisesRegex(
                ValueError,
                "participant keys differ",
            ):
                validate_race_car_summary(connection)

    def test_rejects_missing_key(self):
        with duckdb.connect() as connection:
            connection.execute("""
                CREATE TEMP VIEW race_car_summary AS
                SELECT
                    'classification-a' AS source_id,
                    'version-1' AS bronze_sha256,
                    NULL::VARCHAR AS car_number
            """)

            with self.assertRaisesRegex(
                ValueError,
                "missing key values",
            ):
                validate_race_car_summary(connection)

    def test_rejects_duplicate_keys(self):
        with duckdb.connect() as connection:
            connection.execute("""
                CREATE TEMP VIEW race_car_summary AS
                SELECT *
                FROM (VALUES
                    ('classification-a', 'version-1', '24'),
                    ('classification-a', 'version-1', '24')
                ) AS t(source_id, bronze_sha256, car_number)
            """)

            with self.assertRaisesRegex(
                ValueError,
                "duplicate keys",
            ):
                validate_race_car_summary(connection)

    def test_accepts_matching_participants(self):
        with duckdb.connect() as connection:
            connection.execute("""
                CREATE TEMP VIEW silver_classification AS
                SELECT *
                FROM (VALUES
                    ('classification-a', 'version-1', '24'),
                    ('classification-a', 'version-1', '70')
                ) AS t(source_id, bronze_sha256, car_number)
            """)

            connection.execute("""
                CREATE TEMP VIEW race_car_summary AS
                SELECT *
                FROM silver_classification
            """)

            validate_race_car_summary(connection)
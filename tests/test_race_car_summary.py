"""Verify race summaries preserve participants and use the correct versioned statistics."""

import unittest
from pathlib import Path

import duckdb
from analyze_bronze import validate_race_car_summary


class RaceCarSummaryTests(unittest.TestCase):
    def test_keeps_participant_without_stop_summary(self):
        with duckdb.connect() as connection:
            connection.execute("""
                CREATE TEMP VIEW classification_pit_stop_comparison AS
                SELECT
                    'classification-a' AS source_id,
                    *
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

            connection.execute("""
                CREATE TEMP VIEW source_sessions AS
                SELECT *
                FROM (VALUES
                    (
                        'classification-a', 'imsa-weathertech', 2024,
                        'road-america', 'test-race', 'classification'
                    ),
                    (
                        'classification-a', 'wrong-championship', 2099,
                        'wrong-event', 'wrong-session', 'pit_stops'
                    )
                ) AS t(
                    source_id,
                    championship,
                    season,
                    event_id,
                    session_id,
                    document_type
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
                average_pit_time_seconds,
                championship,
                season,
                event_id,
                session_id
            """).fetchall()

            expected = [
                ("24", 70.0, "imsa-weathertech", 2024, "road-america", "test-race"),
                ("70", None, "imsa-weathertech", 2024, "road-america", "test-race"),
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
                SELECT
                    *,
                    'imsa-weathertech' AS championship,
                    2024 AS season,
                    'road-america' AS event_id,
                    'test-race' AS session_id
                FROM silver_classification
            """)

            validate_race_car_summary(connection)

    def test_keeps_same_car_separate_between_races(self):
        with duckdb.connect() as connection:
            connection.execute("""
                CREATE TEMP VIEW classification_pit_stop_comparison AS
                SELECT *
                FROM (VALUES
                    ('classification-a', 'pits-a', 'version-a', '24'),
                    ('classification-b', 'pits-b', 'version-b', '24')
                ) AS t(
                    source_id,
                    pit_stop_source_id,
                    pit_stop_bronze_sha256,
                    car_number
                )
            """)

            connection.execute("""
                CREATE TEMP VIEW pit_stop_summary AS
                SELECT *
                FROM (VALUES
                    ('pits-a', 'version-a', '24', 2, 0, 60.0, 100.0),
                    ('pits-b', 'version-b', '24', 3, 0, 90.0, 100.0)
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

            connection.execute("""
                CREATE TEMP VIEW source_sessions AS
                SELECT *
                FROM (VALUES
                    (
                        'classification-a', 'imsa-weathertech', 2024,
                        'road-america', 'race-a', 'classification'
                    ),
                    (
                        'classification-b', 'imsa-weathertech', 2025,
                        'daytona', 'race-b', 'classification'
                    )
                ) AS t(
                    source_id,
                    championship,
                    season,
                    event_id,
                    session_id,
                    document_type
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
                source_id,
                car_number,
                average_pit_time_seconds
            """).fetchall()

            expected =[
                ("classification-a", "24", 60.0),
                ("classification-b", "24", 90.0),
            ]

            self.assertCountEqual(rows, expected)

    def test_rejects_missing_session_context(self):
        with duckdb.connect() as connection:
            connection.execute("""
                CREATE TEMP VIEW silver_classification AS
                SELECT
                    'classification-a' AS source_id,
                    'version-1' AS bronze_sha256,
                    '24' AS car_number
            """)

            connection.execute("""
                CREATE TEMP VIEW race_car_summary AS
                SELECT
                    source_id,
                    bronze_sha256,
                    car_number,
                    'imsa-weathertech' AS championship,
                    2024 AS season,
                    '   ' AS event_id,
                    'test-race' AS session_id
                FROM silver_classification
            """)

            with self.assertRaisesRegex(
                ValueError,
                "missing session context",
            ):
                validate_race_car_summary(connection)
"""Verify classification field normalization, invalid counts and key checks."""

import json
import unittest
from pathlib import Path

import duckdb

class SilverClassificationTests(unittest.TestCase):
    def test_preserves_car_number_and_converts_fields(self):
        participants = [
            {
                "number": " 04 ",
                "manufacturer": " BMW ",
                "imsa_manufacturerid": " 74 ",
                "vehicle": " BMW M4 GT3 EVO ",
                "position": 48,
                "class": " GTD ",
                "pit_stops": "0",
                "not_finished": True,
                "team": " Team Test ",
                "laps": "100",
                "fastest_lap_number": "42",
                "fastest_lap_kph": "219.6",
                "elapsed_time": " 1:00:00.000 ",
                "fastest_lap_time": " 1:30.000 ",
                "gap_first": " +1:17.343 ",
                "gap_previous": " 2 Laps ",
            }
        ]
        with duckdb.connect() as connection:
            connection.execute("""
                CREATE TEMP TABLE bronze_classification (
                    classification JSON,
                    source_id VARCHAR,
                    bronze_sha256 VARCHAR
                )
            """)

            connection.execute(
                "INSERT INTO bronze_classification VALUES (?, ?, ?)",
                [
                    json.dumps(participants),
                    "test-source",
                    "test-bronze-hash",
                ],
            )
            query_path = (
                Path(__file__).resolve().parent.parent
                / "sql"
                / "25_silver_classification.sql"
            )

            query = query_path.read_text(encoding="utf-8")
            parser_path = query_path.parent / "21_create_duration_parser.sql"
            connection.execute(parser_path.read_text(encoding="utf-8"))
            rows = connection.sql(query).fetchall()

            self.assertEqual(
                rows,
                [
                    (
                        "test-source",
                        "test-bronze-hash",
                        "0",
                        "04",
                        "BMW",
                        "74",
                        "BMW M4 GT3 EVO",
                        48,
                        "GTD",
                        "Team Test",
                        100,
                        42,
                        219.6,
                        "1:00:00.000",
                        3600.0,
                        "1:30.000",
                        90.0,
                        "+1:17.343",
                        "2 Laps",
                        "time",
                        77.343,
                        None,
                        "laps",
                        None,
                        2,
                        0,
                        True,
                    )
                ],
            )


    def test_returns_null_for_invalid_pit_stop_count(self):
        participants = [
            {
                "number": " 04 ",
                "position": 48,
                "class": " GTD ",
                "pit_stops": "inconnu",
                "not_finished": True,
            }
        ]
        with duckdb.connect() as connection:
            connection.execute("""
                CREATE TEMP TABLE bronze_classification (
                    classification JSON,
                    source_id VARCHAR,
                    bronze_sha256 VARCHAR
                )
            """)

            connection.execute(
                "INSERT INTO bronze_classification VALUES (?, ?, ?)",
                [
                    json.dumps(participants),
                    "test-source",
                    "test-bronze-hash",
                ],
            )

            query_path = (
                Path(__file__).resolve().parent.parent
                / "sql"
                / "25_silver_classification.sql"
            )

            query = query_path.read_text(encoding="utf-8")
            parser_path = query_path.parent / "21_create_duration_parser.sql"
            connection.execute(parser_path.read_text(encoding="utf-8"))
            rows = connection.sql(query).fetchall()

            self.assertEqual(
                rows,
                [
                    (
                        "test-source",
                        "test-bronze-hash",
                        "0",
                        "04",
                        None,
                        None,
                        None,
                        48,
                        "GTD",
                        None,  # team_name
                        None,  # completed_laps
                        None,  # fastest_lap_number
                        None,  # fastest_lap_speed_kph
                        None,  # total_time_raw
                        None,  # total_time_seconds
                        None,  # fastest_lap_time_raw
                        None,  # fastest_lap_time_seconds
                        None,  # gap_first_raw
                        None,  # gap_previous_raw
                        "missing",  # gap_first_kind
                        None,  # gap_first_seconds
                        None,  # gap_first_laps
                        "missing",  # gap_previous_kind
                        None,  # gap_previous_seconds
                        None,  # gap_previous_laps
                        None,  # reported_pit_stop_count
                        True,
                    )
                ],
            )

    def test_counts_missing_keys(self):
        with duckdb.connect() as connection:
            connection.execute("""
                CREATE TEMP VIEW silver_classification AS
                SELECT *
                FROM (VALUES
                    ('test-source', 'version-1', '0'),
                    (NULL, 'version-1', '1'),
                    ('test-source', NULL, '2'),
                    ('test-source', 'version-1', NULL),
                    (NULL, NULL, NULL)
                ) AS t(
                    source_id,
                    bronze_sha256,
                    source_entry_index
                )
            """)

            missing_keys_path = (
                Path(__file__).resolve().parent.parent
                / "sql"
                / "26_check_missing_classification_keys.sql"
            )

            query = missing_keys_path.read_text(encoding="utf-8")
            missing_keys_count = connection.sql(query).fetchone()[0]

            self.assertEqual(missing_keys_count, 4)

    def test_counts_duplicate_keys(self):
        with duckdb.connect() as connection:
            connection.execute("""
                CREATE TEMP VIEW silver_classification AS
                SELECT *
                FROM (VALUES
                    ('test-source', 'version-1', '0'),
                    ('test-source', 'version-1', '0'),
                    ('test-source', 'version-1', '1'),
                    ('test-source', 'version-2', '0'),
                    ('other-source', 'version-1', '0')
                ) AS t(
                    source_id,
                    bronze_sha256,
                    source_entry_index
                )
            """)

            duplicate_keys_path = (
                Path(__file__).resolve().parent.parent
                / "sql"
                / "27_check_duplicate_classification_keys.sql"
            )

            query = duplicate_keys_path.read_text(encoding="utf-8")
            duplicate_keys_count = connection.sql(query).fetchone()[0]

            self.assertEqual(duplicate_keys_count, 1)

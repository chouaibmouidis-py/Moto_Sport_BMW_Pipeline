import json
import unittest
from pathlib import Path

import duckdb


class SilverCarEntriesTests(unittest.TestCase):
    def test_keeps_separate_entries_with_same_car_number(self):
        cars = [
            {
                "number": "04",
                "vehicle": "BMW M4 GT3 EVO",
                "manufacturer": "BMW",
                "class": "GTD",
                "team": "Test team",
                "group": " Test group ",
                "tires": " Michelin ",
                "pit_stops": [],
            },
            {
                "number": "04",
                "pit_stops": [{"pit_number": 1}],
            },
        ]

        with duckdb.connect() as connection:
            connection.execute("""
                CREATE TEMP TABLE bronze_document (
                    source_id VARCHAR,
                    pit_stop_analysis JSON
                )
            """)

            connection.execute(
                "INSERT INTO bronze_document VALUES (?, ?)",
                ["test-source", json.dumps(cars)],
            )

            connection.execute("""
                ALTER TABLE bronze_document
                ADD COLUMN bronze_sha256 VARCHAR DEFAULT 'test-bronze-hash'
            """)

            query_path = (
                Path(__file__).resolve().parent.parent
                / "sql"
                / "10_silver_car_entries.sql"
            )

            result = connection.sql(
                query_path.read_text(encoding="utf-8")
            )
            result.create_view("silver_car_entries")

            attributes = connection.sql("""
                SELECT car_group, tires
                FROM silver_car_entries
                WHERE source_entry_index = '0'
            """).fetchone()

            self.assertEqual(
                attributes,
                ("Test group", "Michelin"),
            )

            rows = connection.sql("""
                SELECT
                    source_id,
                    source_entry_index,
                    car_number,
                    pit_stop_count
                FROM silver_car_entries
                ORDER BY source_entry_index
            """).fetchall()

            self.assertEqual(
                rows,
                [
                    ("test-source", "0", "04", 0),
                    ("test-source", "1", "04", 1),
                ],
            )

    def test_counts_missing_keys(self):
        with duckdb.connect() as connection:
            connection.execute("""
                CREATE TEMP VIEW silver_car_entries AS
                SELECT *
                FROM (VALUES
                    ('course-a', '0'),
                    (NULL, '1'),
                    ('course-a', NULL),
                    (NULL, NULL)
                ) AS t(source_id, source_entry_index)
            """)

            query_path = (
                Path(__file__).resolve().parent.parent
                / "sql"
                / "11_check_missing_car_entry_keys.sql"
            )

            missing_key_count = connection.sql(
                query_path.read_text(encoding="utf-8")
            ).fetchone()[0]

            self.assertEqual(missing_key_count, 3)

    def test_counts_duplicate_keys(self):
        with duckdb.connect() as connection:
            connection.execute("""
                CREATE TEMP VIEW silver_car_entries AS
                SELECT *
                FROM (VALUES
                    ('course-a', '0'),
                    ('course-a', '0'),
                    ('course-a', '1'),
                    ('course-b', '0')
                ) AS t(source_id, source_entry_index)
            """)

            query_path = (
                Path(__file__).resolve().parent.parent
                / "sql"
                / "12_check_duplicate_car_entry_keys.sql"
            )

            duplicate_key_count = connection.sql(
                query_path.read_text(encoding="utf-8")
            ).fetchone()[0]

            self.assertEqual(duplicate_key_count, 1)
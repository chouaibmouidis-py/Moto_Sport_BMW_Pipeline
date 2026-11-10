import json
import unittest
from pathlib import Path

import duckdb


class SilverDriverEntriesTests(unittest.TestCase):
    def test_extracts_drivers_with_parent_index(self):
        cars = [
            {
                "drivers": [
                    {"number": 1, "firstname": " Alice "},
                    {"number": 2, "firstname": " Bob "},
                ]
            },
            {
                "drivers": [
                    {"number": 1, "firstname": " Charlie "}
                ]
            },
        ]

        with duckdb.connect() as connection:
            connection.execute("""
                CREATE TEMP TABLE bronze_document (
                    source_id VARCHAR,
                    bronze_sha256 VARCHAR,
                    pit_stop_analysis JSON
                )
            """)

            connection.execute(
                "INSERT INTO bronze_document VALUES (?, ?, ?)",
                ["test-source", "test-bronze-hash", json.dumps(cars)],
            )

            query_path = (
                Path(__file__).resolve().parent.parent
                / "sql"
                / "14_silver_driver_entries.sql"
            )

            drivers = connection.sql(
                query_path.read_text(encoding="utf-8")
            )
            drivers.create_view("silver_driver_entries")

            rows = connection.sql("""
                SELECT
                    source_entry_index,
                    source_driver_index,
                    driver_number,
                    first_name
                FROM silver_driver_entries
                ORDER BY source_entry_index, source_driver_index
            """).fetchall()

            self.assertEqual(
                rows,
                [
                    ("0", "0", 1, "Alice"),
                    ("0", "1", 2, "Bob"),
                    ("1", "0", 1, "Charlie"),
                ],
            )
import unittest
from pathlib import Path

import duckdb


class EnrichedPitStopsTests(unittest.TestCase):
    def test_adds_names_and_keeps_stop_without_driver(self):
        with duckdb.connect() as connection:
            connection.execute("""
                CREATE TEMP VIEW silver_pit_stops AS
                SELECT
                    'test-source' AS source_id,
                    'version-1' AS bronze_sha256,
                    '0' AS source_entry_index,
                    *
                FROM (VALUES
                    (1, 1, 2),
                    (2, NULL, NULL)
                ) AS t(
                    pit_number,
                    in_driver_number,
                    out_driver_number
                )
            """)

            connection.execute("""
                CREATE TEMP VIEW silver_driver_entries AS
                SELECT
                    'test-source' AS source_id,
                    '0' AS source_entry_index,
                    *
                FROM (VALUES
                    ('version-1', 1, 'Alice', 'Martin'),
                    ('version-1', 2, 'Bob', 'Bernard'),
                    ('version-2', 1, 'Charlie', 'Durand')
                ) AS t(
                    bronze_sha256,
                    driver_number,
                    first_name,
                    surname
                )
            """)

            query_path = (
                Path(__file__).resolve().parent.parent
                / "sql"
                / "20_enriched_pit_stops.sql"
            )

            enriched = connection.sql(
                query_path.read_text(encoding="utf-8")
            )
            enriched.create_view("enriched_pit_stops")

            rows = connection.sql("""
                SELECT
                    pit_number,
                    in_driver_first_name,
                    in_driver_surname,
                    out_driver_first_name,
                    out_driver_surname
                FROM enriched_pit_stops
                ORDER BY pit_number
            """).fetchall()

            self.assertEqual(
                rows,
                [
                    (1, "Alice", "Martin", "Bob", "Bernard"),
                    (2, None, None, None, None),
                ],
            )
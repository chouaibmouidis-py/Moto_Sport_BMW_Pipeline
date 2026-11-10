import unittest
from pathlib import Path

import duckdb


class PitStopDriverLinksTests(unittest.TestCase):
    def test_identifies_missing_unmatched_and_ambiguous_links(self):
        with duckdb.connect() as connection:
            connection.execute("""
                CREATE TEMP VIEW silver_pit_stops AS
                SELECT
                    'test-source' AS source_id,
                    'version-1' AS bronze_sha256,
                    '0' AS source_entry_index,
                    '24' AS car_number,
                    *
                FROM (VALUES
                    (1, NULL, 1),
                    (2, 99, 1),
                    (3, 2, 1)
                ) AS t(pit_number, in_driver_number, out_driver_number)
            """)

            connection.execute("""
                CREATE TEMP VIEW silver_driver_entries AS
                SELECT
                    'test-source' AS source_id,
                    'version-1' AS bronze_sha256,
                    '0' AS source_entry_index,
                    *
                FROM (VALUES
                    (1),
                    (2),
                    (2)
                ) AS t(driver_number)
            """)

            query_path = (
                Path(__file__).resolve().parent.parent
                / "sql"
                / "19_check_pit_stop_driver_links.sql"
            )

            links = connection.sql(
                query_path.read_text(encoding="utf-8")
            )
            links.create_view("driver_link_issues")

            rows = connection.sql("""
                SELECT pit_number, driver_role, match_count, link_status
                FROM driver_link_issues
                ORDER BY pit_number
            """).fetchall()

            self.assertEqual(
                rows,
                [
                    (1, "in", 0, "missing"),
                    (2, "in", 0, "unmatched"),
                    (3, "in", 2, "ambiguous"),
                ],
            )
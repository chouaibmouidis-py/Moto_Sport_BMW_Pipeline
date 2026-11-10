import unittest
from pathlib import Path

import duckdb


class PitStopEntryJoinTests(unittest.TestCase):
    def test_different_versions_do_not_match(self):
        with duckdb.connect() as connection:
            connection.execute("""
                CREATE TEMP VIEW silver_pit_stops AS
                SELECT
                    'course-a' AS source_id,
                    'version-1' AS bronze_sha256,
                    '0' AS source_entry_index
            """)

            connection.execute("""
                CREATE TEMP VIEW silver_car_entries AS
                SELECT
                    'course-a' AS source_id,
                    'version-2' AS bronze_sha256,
                    '0' AS source_entry_index
            """)

            query_path = (
                Path(__file__).resolve().parent.parent
                / "sql"
                / "13_check_matched_pit_stops.sql"
            )

            matched_count = connection.sql(
                query_path.read_text(encoding="utf-8")
            ).fetchone()[0]

            self.assertEqual(matched_count, 0)


    def test_same_version_matches(self):
        with duckdb.connect() as connection:
            connection.execute("""
                CREATE TEMP VIEW silver_pit_stops AS
                SELECT
                    'course-a' AS source_id,
                    'version-1' AS bronze_sha256,
                    '0' AS source_entry_index
            """)

            connection.execute("""
                CREATE TEMP VIEW silver_car_entries AS
                SELECT
                    'course-a' AS source_id,
                    'version-1' AS bronze_sha256,
                    '0' AS source_entry_index
            """)

            query_path = (
                Path(__file__).resolve().parent.parent
                / "sql"
                / "13_check_matched_pit_stops.sql"
            )

            matched_count = connection.sql(
                query_path.read_text(encoding="utf-8")
            ).fetchone()[0]

            self.assertEqual(matched_count, 1)
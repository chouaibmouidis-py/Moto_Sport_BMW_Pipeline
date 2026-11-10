import unittest
from pathlib import Path

import duckdb


class PitStopKeysTests(unittest.TestCase):
    def test_counts_missing_keys(self):
        with duckdb.connect() as connexion:
            connexion.execute("""
                CREATE TEMP VIEW silver_pit_stops AS
                SELECT *
                FROM (VALUES
                    ('course-a', '24', 1),
                    (NULL,       '24', 2),
                    ('course-a', NULL, 3),
                    (NULL, '25', NULL)
                ) AS t(source_id, car_number, pit_number)
            """)
            query_path = (
                Path(__file__).resolve().parent.parent
                / "sql"
                / "08_check_missing_pit_stop_keys.sql"
            )
            query = query_path.read_text(encoding="utf-8")
            invalid_key_count = connexion.sql(query).fetchone()[0]
            self.assertEqual(invalid_key_count, 3)

    def test_counts_duplicate_keys(self):
        with duckdb.connect() as connexion:
            connexion.execute("""
                CREATE TEMP VIEW silver_pit_stops AS
                SELECT *
                FROM (VALUES
                    ('course-a', '24', 1),
                    ('course-a', '24', 1),
                    ('course-a', '24', 2),
                    ('course-b', '24', 1)
                ) AS t(source_id, car_number, pit_number)
            """)
            query_path = (
                Path(__file__).resolve().parent.parent
                / "sql"
                / "09_check_duplicate_pit_stop_keys.sql"
            )
            query = query_path.read_text(encoding="utf-8")
            duplicate_key_count = connexion.sql(query).fetchone()[0]
            self.assertEqual(duplicate_key_count, 1)

    def test_empty_table_has_no_key_issues(self):
        with duckdb.connect() as connexion:
            connexion.execute("""
                CREATE TEMP TABLE silver_pit_stops (
                    source_id VARCHAR,
                    car_number VARCHAR,
                    pit_number INTEGER
                )
            """)

            query_files = [
                "08_check_missing_pit_stop_keys.sql",
                "09_check_duplicate_pit_stop_keys.sql",
            ]

            for filename in query_files:
                with self.subTest(query_file=filename):
                    query_path = (
                        Path(__file__).resolve().parent.parent
                        / "sql"
                        / filename
                    )

                    issue_count = connexion.sql(
                        query_path.read_text(encoding="utf-8")
                    ).fetchone()[0]

                    self.assertEqual(issue_count, 0)

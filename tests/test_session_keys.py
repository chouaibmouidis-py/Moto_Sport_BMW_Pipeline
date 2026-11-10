import unittest
from pathlib import Path

import duckdb


class SessionKeysTests(unittest.TestCase):
    def test_counts_missing_and_duplicate_keys(self):
        with duckdb.connect() as connection:
            connection.execute("""
                CREATE TEMP VIEW silver_sessions AS
                SELECT *
                FROM (VALUES
                    ('course-a', 'version-1'),
                    ('course-a', 'version-1'),
                    ('course-a', 'version-2'),
                    (NULL, 'version-1'),
                    ('course-b', NULL)
                ) AS t(source_id, bronze_sha256)
            """)

            query_path = (
                Path(__file__).resolve().parent.parent
                / "sql"
                / "17_check_session_keys.sql"
            )

            counts = connection.sql(
                query_path.read_text(encoding="utf-8")
            ).fetchone()

            self.assertEqual(counts, (2, 1))
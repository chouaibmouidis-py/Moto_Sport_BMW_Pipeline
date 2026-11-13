"""Verify missing and invalid cumulative duration counts."""

import unittest
import duckdb
from pathlib import Path


class TotalPitDurationQualityTests(unittest.TestCase):
    def test_counts_missing_and_invalid_duration(self):
        with duckdb.connect() as connection:
            connection.execute("""
                CREATE TEMP VIEW silver_pit_stops AS
                SELECT *
                FROM (VALUES
                    ('test-source', 'version-1', '1:04.099', 64.099),
                    ('test-source', 'version-1', NULL, NULL),
                    ('test-source', 'version-1', 'inconnue', NULL)
                ) AS t(
                    source_id,
                    bronze_sha256,
                    total_pit_time_raw,
                    total_pit_time_seconds
                )
            """)
            query_path = (
                Path(__file__).resolve().parent.parent
                / "sql"
                / "23_total_pit_duration_quality.sql"
            )
            query = query_path.read_text(encoding="utf-8")
            row = connection.sql(query).fetchone()
            self.assertEqual(
                row,
                ("test-source", "version-1", 3, 1, 1),
            )

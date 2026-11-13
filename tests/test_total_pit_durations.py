"""Verify selection and classification of unconverted cumulative durations."""

import unittest
from pathlib import Path
import duckdb

class TotalPitDurationTests(unittest.TestCase):
    def test_selects_unconverted_total_durations(self):
        with duckdb.connect() as connexion:
            connexion.execute("""
                CREATE TEMP VIEW silver_pit_stops AS
                SELECT *
                FROM (VALUES
                    ('test-source', '24', 1, '1:04.099', 64.099),
                    ('test-source', '24', 2, 'inconnue', NULL),
                    ('test-source', '25', 1, NULL, NULL)
                ) AS t(
                    source_id,
                    car_number,
                    pit_number,
                    total_pit_time_raw,
                    total_pit_time_seconds
                )
            """)
            query_path = (
                Path(__file__).resolve().parent.parent
                / "sql"
                / "22_check_missing_total_pit_durations.sql"
            )
            query = query_path.read_text(encoding="utf-8")
            rows = connexion.sql(query).fetchall()
            self.assertCountEqual(
                rows,
                [
                    ("test-source", "24", 2, "inconnue", None, "invalid"),
                    ("test-source", "25", 1, None, None, "missing"),
                ],
            )

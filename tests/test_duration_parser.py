"""Verify valid duration conversions and rejection of invalid formats."""

import unittest
from pathlib import Path

import duckdb


class DurationParserTests(unittest.TestCase):
    def test_converts_valid_durations_and_rejects_invalid_ones(self):
        cases = [
            ("48.019", 48.019),
            ("1:04.099", 64.099),
            ("1:55:57.718", 6957.718),
            ("00:75", None),
            ("1:-5", None),
            ("1:60:00", None),
            ("-5", None),
            ("inconnue", None),
            (None, None),
        ]

        query_path = (
            Path(__file__).resolve().parent.parent
            / "sql"
            / "21_create_duration_parser.sql"
        )

        with duckdb.connect() as connection:
            connection.execute(
                query_path.read_text(encoding="utf-8")
            )

            for raw_duration, expected in cases:
                with self.subTest(raw_duration=raw_duration):
                    actual = connection.sql(
                        "SELECT parse_duration_seconds(?)",
                        params=[raw_duration],
                    ).fetchone()[0]

                    if expected is None:
                        self.assertIsNone(actual)
                    else:
                        self.assertAlmostEqual(
                            actual,
                            expected,
                            places=3,
                        )

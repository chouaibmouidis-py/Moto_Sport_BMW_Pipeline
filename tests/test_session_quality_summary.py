import unittest
from pathlib import Path

import duckdb


class SessionQualitySummaryTests(unittest.TestCase):
    def test_counts_each_air_temperature_status(self):
        with duckdb.connect() as connection:
            connection.execute("""
                CREATE TEMP VIEW silver_sessions AS
                SELECT
                    *,
                    'valid' AS track_temperature_status,
                    'valid' AS session_datetime_status,
                    'valid' AS report_creation_datetime_status
                FROM (VALUES
                    ('source-a', 'version-1', 'valid'),
                    ('source-b', 'version-1', 'missing'),
                    ('source-c', 'version-1', 'invalid')
                ) AS t(
                    source_id,
                    bronze_sha256,
                    air_temperature_status
                )
            """)

            query_path = (
                Path(__file__).resolve().parent.parent
                / "sql"
                / "18_session_quality_summary.sql"
            )

            report = connection.sql(
                query_path.read_text(encoding="utf-8")
            )

            self.assertEqual(report.count("*").fetchone()[0], 12)

            rows = report.filter(
                "field_name = 'air_temperature'"
            ).fetchall()

            self.assertEqual(
                rows,
                [
                    ("source-a", "version-1", "air_temperature", 1, 1, 0, 0),
                    ("source-b", "version-1", "air_temperature", 1, 0, 1, 0),
                    ("source-c", "version-1", "air_temperature", 1, 0, 0, 1),
                ],
            )
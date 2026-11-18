"""Verify session field quality counts for valid, missing and invalid values."""

import unittest
from pathlib import Path

import duckdb


class SessionQualitySummaryTests(unittest.TestCase):
    def test_counts_each_status_for_all_session_fields(self):
        with duckdb.connect() as connection:
            connection.execute("""
                CREATE TEMP VIEW silver_sessions AS
                SELECT *
                FROM (VALUES
                    ('source-a', 'version-1', 'valid', 'missing', 'invalid', 'valid'),
                    ('source-b', 'version-1', 'missing', 'invalid', 'valid', 'missing'),
                    ('source-c', 'version-1', 'invalid', 'valid', 'missing', 'invalid')
                ) AS t(
                    source_id,
                    bronze_sha256,
                    air_temperature_status,
                    track_temperature_status,
                    session_datetime_status,
                    report_creation_datetime_status
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

            self.assertCountEqual(
                report.fetchall(),
                [
                    ("source-a", "version-1", "air_temperature", 1, 1, 0, 0),
                    ("source-a", "version-1", "track_temperature", 1, 0, 1, 0),
                    ("source-a", "version-1", "session_datetime", 1, 0, 0, 1),
                    ("source-a", "version-1", "report_creation_datetime", 1, 1, 0, 0),
                    ("source-b", "version-1", "air_temperature", 1, 0, 1, 0),
                    ("source-b", "version-1", "track_temperature", 1, 0, 0, 1),
                    ("source-b", "version-1", "session_datetime", 1, 1, 0, 0),
                    ("source-b", "version-1", "report_creation_datetime", 1, 0, 1, 0),
                    ("source-c", "version-1", "air_temperature", 1, 0, 0, 1),
                    ("source-c", "version-1", "track_temperature", 1, 1, 0, 0),
                    ("source-c", "version-1", "session_datetime", 1, 0, 1, 0),
                    ("source-c", "version-1", "report_creation_datetime", 1, 0, 0, 1),
                ],
            )

import unittest
from pathlib import Path

import duckdb


class ClassificationCountQualityTests(unittest.TestCase):
    def test_counts_mismatches_separately_by_version(self):
        with duckdb.connect() as connection:
            connection.execute("""
                CREATE TEMP VIEW race_car_summary AS
                SELECT *
                FROM (VALUES
                    ('course-a', 'version-1', 'matched'),
                    ('course-a', 'version-1', 'count_mismatch'),
                    ('course-a', 'version-1', 'zero_reported_no_detail'),
                    ('course-a', 'version-1', 'missing_stop_details'),
                    ('course-a', 'version-2', 'matched')
                ) AS t(
                    source_id,
                    bronze_sha256,
                    comparison_status
                )
            """)

            query_path = (
                Path(__file__).resolve().parent.parent
                / "sql"
                / "32_classification_count_quality.sql"
            )

            rows = connection.sql(
                query_path.read_text(encoding="utf-8")
            ).fetchall()

            expected = [
                ("course-a", "version-1", 4, 1, 25.0),
                ("course-a", "version-2", 1, 0, 0.0),
            ]

            self.assertCountEqual(rows, expected)
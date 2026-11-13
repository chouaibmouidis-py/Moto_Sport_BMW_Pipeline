"""Verify PDF stop duration conversion and preservation of source traceability."""

import unittest
from pathlib import Path

import duckdb

from moto_sport_bmw_pipeline.silver import transform_pdf_pit_stops


class SilverPdfPitStopsTests(unittest.TestCase):
    def test_converts_duration_and_preserves_traceability(self):
        with duckdb.connect() as connection:
            connection.execute("""
                CREATE TEMP VIEW bronze_pdf_pit_stops AS
                SELECT
                    'test-source' AS source_id,
                    'test-pdf-hash' AS pdf_sha256,
                    'test-bronze-hash' AS bronze_sha256,
                    '04' AS car_number,
                    1 AS pit_number,
                    '1:59:53.389' AS pit_time_raw,
                    2 AS page_number,
                    1 AS column_number,
                    3 AS block_line_number,
                    'extracted stop text' AS source_line
            """)

            project_directory = Path(__file__).resolve().parent.parent
            result = transform_pdf_pit_stops(
                connection,
                project_directory,
            )

            self.assertEqual(
                result.fetchall(),
                [(
                    "test-source",
                    "test-pdf-hash",
                    "test-bronze-hash",
                    "04",
                    1,
                    "1:59:53.389",
                    7193.389,
                    2,
                    1,
                    3,
                    "extracted stop text",
                )],
            )

    def test_rejects_duplicate_stop_keys(self):
        with duckdb.connect() as connection:
            connection.execute("""
                CREATE TEMP VIEW bronze_pdf_pit_stops AS
                SELECT
                    'test-source' AS source_id,
                    'test-pdf-hash' AS pdf_sha256,
                    'test-bronze-hash' AS bronze_sha256,
                    '04' AS car_number,
                    pit_number,
                    '1:28.481' AS pit_time_raw,
                    2 AS page_number,
                    1 AS column_number,
                    3 AS block_line_number,
                    'extracted stop text' AS source_line
                FROM (VALUES (1), (1)) AS t(pit_number)
            """)

            project_directory = Path(__file__).resolve().parent.parent

            with self.assertRaisesRegex(
                ValueError,
                "duplicate stop keys",
            ):
                transform_pdf_pit_stops(
                    connection,
                    project_directory,
                )

    def test_rejects_missing_bronze_fingerprint(self):
        with duckdb.connect() as connection:
            connection.execute("""
                CREATE TEMP VIEW bronze_pdf_pit_stops AS
                SELECT
                    'test-source' AS source_id,
                    'test-pdf-hash' AS pdf_sha256,
                    CAST(NULL AS VARCHAR) AS bronze_sha256,
                    '04' AS car_number,
                    1 AS pit_number,
                    '1:28.481' AS pit_time_raw,
                    2 AS page_number,
                    1 AS column_number,
                    3 AS block_line_number,
                    'extracted stop text' AS source_line
            """)

            project_directory = Path(__file__).resolve().parent.parent

            with self.assertRaisesRegex(
                ValueError,
                "missing key or provenance",
            ):
                transform_pdf_pit_stops(
                    connection,
                    project_directory,
                )
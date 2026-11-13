"""Verify publication and validation safeguards for the PDF pit stop pipeline."""

import hashlib
from pathlib import Path
import tempfile
import unittest

import duckdb

from moto_sport_bmw_pipeline.pipeline import publish_pdf_pit_stops_from_bronze


class PdfPitStopsPipelineTests(unittest.TestCase):
    def test_transforms_and_publishes_silver_with_correct_schema(self):
        project_directory = Path(__file__).resolve().parent.parent

        with tempfile.TemporaryDirectory() as directory:
            bronze_path = Path(directory) / "bronze.parquet"
            output_path = Path(directory) / "silver.parquet"

            with duckdb.connect() as connection:
                connection.sql("""
                    SELECT *
                    FROM (VALUES
                        ('source-1', 'pdf-sha', '24', 1, '1:28.481', 1, 1, 2, 'line 1'),
                        ('source-1', 'pdf-sha', '24', 2, '1:22.665', 1, 1, 3, 'line 2')
                    ) AS t(
                        source_id, pdf_sha256, car_number, pit_number,
                        pit_time_raw, page_number, column_number,
                        block_line_number, source_line
                    )
                """).write_parquet(str(bronze_path))

            expected_bronze_sha = hashlib.sha256(bronze_path.read_bytes()).hexdigest()

            result = publish_pdf_pit_stops_from_bronze(
                project_directory,
                bronze_path,
                output_path,
            )
            self.assertEqual(result, output_path)

            with duckdb.connect() as connection:
                saved = connection.read_parquet(str(output_path))
                rows = saved.project(
                    "source_id, pdf_sha256, bronze_sha256, car_number, pit_number, pit_time_raw, pit_time_in_seconds"
                ).fetchall()

            self.assertEqual(rows, [
                ('source-1', 'pdf-sha', expected_bronze_sha, '24', 1, '1:28.481', 88.481),
                ('source-1', 'pdf-sha', expected_bronze_sha, '24', 2, '1:22.665', 82.665),
            ])

    def test_duplicate_stop_keys_preserve_previous_output(self):
        project_directory = Path(__file__).resolve().parent.parent

        with tempfile.TemporaryDirectory() as directory:
            bronze_path = Path(directory) / "bronze.parquet"
            output_path = Path(directory) / "silver.parquet"
            output_path.write_bytes(b"previous version")

            with duckdb.connect() as connection:
                connection.sql("""
                    SELECT *
                    FROM (VALUES
                        ('source-1', 'pdf-sha', '24', 1, '1:28.481', 1, 1, 2, 'line 1'),
                        ('source-1', 'pdf-sha', '24', 1, '1:28.481', 1, 1, 3, 'line 2')
                    ) AS t(
                        source_id, pdf_sha256, car_number, pit_number,
                        pit_time_raw, page_number, column_number,
                        block_line_number, source_line
                    )
                """).write_parquet(str(bronze_path))

            with self.assertRaisesRegex(ValueError, "duplicate stop keys"):
                publish_pdf_pit_stops_from_bronze(
                    project_directory,
                    bronze_path,
                    output_path,
                )

            self.assertEqual(output_path.read_bytes(), b"previous version")

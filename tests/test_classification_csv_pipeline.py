"""Verify publication safeguards for the classification CSV pipeline."""

import tempfile
import unittest
from pathlib import Path

import duckdb

from moto_sport_bmw_pipeline.pipeline import (
    publish_classification_csv_from_bronze,
)


class ClassificationCsvPipelineTests(unittest.TestCase):
    def test_duplicate_numbers_preserve_previous_output(self):
        project_directory = Path(__file__).resolve().parent.parent

        with tempfile.TemporaryDirectory() as directory:
            bronze_path = Path(directory) / "bronze.parquet"
            output_path = Path(directory) / "silver.parquet"
            output_path.write_bytes(b"previous version")

            with duckdb.connect() as connection:
                connection.sql("""
                    SELECT *
                    FROM (VALUES
                        ('24', 'BMW M Hybrid V8', '1', 'GTP', 'Classified'),
                        (' 24 ', 'BMW M Hybrid V8', '2', 'GTP', 'Classified')
                    ) AS t(NUMBER, VEHICLE, POSITION, CLASS, STATUS)
                """).write_parquet(str(bronze_path))

            with self.assertRaisesRegex(
                ValueError,
                "duplicate car numbers",
            ):
                publish_classification_csv_from_bronze(
                    project_directory,
                    bronze_path,
                    "test-source",
                    output_path,
                )

            self.assertEqual(
                output_path.read_bytes(),
                b"previous version",
            )
"""Verify normalization of classification CSV fields from Bronze."""

import unittest
from pathlib import Path
from moto_sport_bmw_pipeline.silver import transform_classification_csv
import duckdb


class SilverClassificationCsvTests(unittest.TestCase):
    def test_normalizes_fields_and_preserves_car_number(self):
        with duckdb.connect() as connection:
            connection.execute("""
                CREATE TEMP VIEW bronze_classification_csv AS
                SELECT
                    'test-source' AS source_id,
                    'test-bronze-hash' AS bronze_sha256,
                    *
                FROM (VALUES
                    (' 04 ', ' BMW M4 GT3 ', '4', ' GTD ', ' Classified ')
                ) AS t(NUMBER, VEHICLE, POSITION, CLASS, STATUS)
            """)

            project_directory = Path(__file__).resolve().parent.parent

            result = transform_classification_csv(
                connection,
                project_directory,
            )
            rows = result.fetchall()

            self.assertEqual(
                rows,
                [("test-source", "test-bronze-hash", "04", "BMW M4 GT3", 4, "GTD", "Classified")],
            )

    def test_keeps_participant_with_invalid_position(self):
        with duckdb.connect() as connection:
            connection.execute("""
                CREATE TEMP VIEW bronze_classification_csv AS
                SELECT
                    'test-source' AS source_id,
                    'test-bronze-hash' AS bronze_sha256,
                    *
                FROM (VALUES
                    ('24', 'BMW M Hybrid V8', 'inconnue', 'GTP', 'Classified')
                ) AS t(NUMBER, VEHICLE, POSITION, CLASS, STATUS)
            """)

            project_directory = Path(__file__).resolve().parent.parent

            result = transform_classification_csv(
                connection,
                project_directory,
            )
            rows = result.fetchall()

            self.assertEqual(
                rows,
                [("test-source", "test-bronze-hash", "24", "BMW M Hybrid V8", None, "GTP", "Classified")],
            )

    def test_rejects_duplicate_car_numbers_before_transformation(self):
        with duckdb.connect() as connection:
            connection.execute("""
                CREATE TEMP VIEW bronze_classification_csv AS
                SELECT
                    'test-source' AS source_id,
                    'test-bronze-hash' AS bronze_sha256,
                    *
                FROM (VALUES
                    ('24', 'BMW M Hybrid V8', '1', 'GTP', 'Classified'),
                    (' 24 ', 'BMW M Hybrid V8', '2', 'GTP', 'Classified')
                ) AS t(NUMBER, VEHICLE, POSITION, CLASS, STATUS)
            """)

            project_directory = Path(__file__).resolve().parent.parent

            with self.assertRaisesRegex(
                ValueError,
                "duplicate car numbers",
            ):
                transform_classification_csv(
                    connection,
                    project_directory,
                )

    def test_rejects_missing_car_number_before_transformation(self):
        with duckdb.connect() as connection:
            connection.execute("""
                CREATE TEMP VIEW bronze_classification_csv AS
                SELECT
                    'test-source' AS source_id,
                    'test-bronze-hash' AS bronze_sha256,
                    *
                FROM (VALUES
                    ('   ', 'BMW M Hybrid V8', '1', 'GTP', 'Classified')
                ) AS t(NUMBER, VEHICLE, POSITION, CLASS, STATUS)
            """)

            project_directory = Path(__file__).resolve().parent.parent

            with self.assertRaisesRegex(
                ValueError,
                "missing car number",
            ):
                transform_classification_csv(
                    connection,
                    project_directory,
                )
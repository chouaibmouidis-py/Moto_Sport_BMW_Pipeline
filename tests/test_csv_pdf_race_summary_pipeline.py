"""Verify publication and validation safeguards for the CSV/PDF race summary Mart pipeline."""

from pathlib import Path
import tempfile
import unittest

import duckdb

from moto_sport_bmw_pipeline.pipeline import publish_csv_pdf_race_summary


class CsvPdfRaceSummaryPipelineTests(unittest.TestCase):
    def prepare_test_data(self, directory: Path):
        classification_silver = directory / "classification.parquet"
        pit_stops_silver = directory / "pit_stops.parquet"
        catalog = {
            "championship": "imsa-weathertech",
            "season": 2023,
            "events": [
                {
                    "event_id": "test-race",
                    "session_id": "20230101-race",
                    "classification_path": "data/raw/class-src/report.csv",
                    "pdf_path": "data/raw/pit-src/report.pdf",
                }
            ],
        }

        with duckdb.connect() as connection:
            connection.sql("""
                SELECT *
                FROM (VALUES
                    ('class-src', 'bronze-hash-c', '24', 'BMW M Hybrid V8', 1, 'GTP', 'Classified'),
                    ('class-src', 'bronze-hash-c', '25', 'BMW M Hybrid V8', 2, 'GTP', 'Classified')
                ) AS t(
                    source_id, bronze_sha256, car_number, car_model,
                    overall_position, car_class, classification_status
                )
            """).write_parquet(str(classification_silver))

            connection.sql("""
                SELECT *
                FROM (VALUES
                    ('pit-src', 'pdf-hash', 'bronze-hash-p', '24', 1, '1:28.481', 88.481, 1, 1, 1, 'line')
                ) AS t(
                    source_id, pdf_sha256, bronze_sha256, car_number,
                    pit_number, pit_time_raw, pit_time_in_seconds,
                    page_number, column_number, block_line_number, source_line
                )
            """).write_parquet(str(pit_stops_silver))

        return catalog, classification_silver, pit_stops_silver

    def test_publishes_mart_summary_preserving_participants(self):
        project_directory = Path(__file__).resolve().parent.parent

        with tempfile.TemporaryDirectory() as directory:
            dir_path = Path(directory)
            catalog, class_silver, pit_silver = self.prepare_test_data(dir_path)
            output_path = dir_path / "race_summary.parquet"

            result = publish_csv_pdf_race_summary(
                project_directory,
                catalog,
                class_silver,
                pit_silver,
                output_path,
            )
            self.assertEqual(result, output_path)

            with duckdb.connect() as connection:
                saved = connection.read_parquet(str(output_path))
                rows = saved.project(
                    "car_number, overall_position, pit_stop_source_id, observed_pit_stop_count, stop_detail_status"
                ).order("car_number").fetchall()

            self.assertEqual(rows, [
                ('24', 1, 'pit-src', 1, 'available'),
                ('25', 2, 'pit-src', None, 'no_stop_details'),
            ])

    def test_orphan_stop_preserves_previous_output(self):
        project_directory = Path(__file__).resolve().parent.parent

        with tempfile.TemporaryDirectory() as directory:
            dir_path = Path(directory)
            catalog, class_silver, pit_silver = self.prepare_test_data(dir_path)
            output_path = dir_path / "race_summary.parquet"
            output_path.write_bytes(b"previous version")

            # Add an orphan stop (car 99 not in classification)
            with duckdb.connect() as connection:
                connection.sql(f"""
                    SELECT * FROM read_parquet('{pit_silver}')
                    UNION ALL
                    SELECT
                        'pit-src', 'pdf-hash', 'bronze-hash-p', '99', 1, '1:28.481', 88.481, 1, 1, 1, 'line'
                """).write_parquet(str(pit_silver))

            with self.assertRaisesRegex(ValueError, "stops without classification"):
                publish_csv_pdf_race_summary(
                    project_directory,
                    catalog,
                    class_silver,
                    pit_silver,
                    output_path,
                )

            self.assertEqual(output_path.read_bytes(), b"previous version")

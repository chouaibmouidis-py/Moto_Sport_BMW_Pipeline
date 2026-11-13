"""Verify validated Parquet replacement and preservation of previous files on failure."""

import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import duckdb

from silver_writer import publish_silver


class SilverWriterTests(unittest.TestCase):
    def test_write_failure_preserves_previous_file(self):
        with tempfile.TemporaryDirectory() as directory:
            output_path = Path(directory) / "pit_stops.parquet"
            output_path.write_bytes(b"previous version")
            with duckdb.connect() as connection:
                converted = connection.sql("""
                    SELECT '24' AS car_number
                """)

                with patch(
                    "duckdb.DuckDBPyRelation.write_parquet",
                    side_effect=OSError("Simulated write failure"),
                ):
                    self.assertRaises(
                        OSError,
                        publish_silver,
                        connection,
                        converted,
                        output_path,
                    )

            self.assertEqual(
                output_path.read_bytes(),
                b"previous version",
            )

    def test_content_mismatch_preserves_previous_file(self):
        with tempfile.TemporaryDirectory() as directory:
            output_path = Path(directory) / "pit_stops.parquet"
            output_path.write_bytes(b"previous version")
            with duckdb.connect() as connection:
                converted = connection.sql("""
                    SELECT '24' AS car_number
                """)
                converted.create_view("silver_pit_stops")

                different_content = connection.sql("""
                    SELECT '25' AS car_number
                """)

                with patch(
                    "duckdb.DuckDBPyConnection.read_parquet",
                    return_value=different_content,
                ):
                    self.assertRaisesRegex(
                        ValueError,
                        "Silver rejected: saved content differs",
                        publish_silver,
                        connection,
                        converted,
                        output_path,
                    )

            self.assertEqual(
                output_path.read_bytes(),
                b"previous version",
            )

    def test_valid_content_replaces_previous_file(self):
        with tempfile.TemporaryDirectory() as directory:
            output_path = Path(directory) / "pit_stops.parquet"
            output_path.write_bytes(b"previous version")

            with duckdb.connect() as connection:
                converted = connection.sql("""
                    SELECT '04' AS car_number
                """)
                converted.create_view("silver_pit_stops")

                publish_silver(connection, converted, output_path)

                saved = connection.read_parquet(str(output_path))
                rows = saved.fetchall()

                self.assertEqual(rows, [("04",)])

    def test_row_count_mismatch_preserves_previous_file(self):
        with tempfile.TemporaryDirectory() as directory:
            output_path = Path(directory) / "pit_stops.parquet"
            output_path.write_bytes(b"previous version")
            with duckdb.connect() as connection:
                converted = connection.sql("""
                    SELECT *
                    FROM (VALUES ('24'), ('25')) AS t(car_number)
                """)
                converted.create_view("silver_pit_stops")

                different_content = connection.sql("""
                    SELECT '25' AS car_number
                """)

                with patch(
                    "duckdb.DuckDBPyConnection.read_parquet",
                    return_value=different_content,
                ):
                    self.assertRaisesRegex(
                        ValueError,
                        "Silver rejected: row count mismatch",
                        publish_silver,
                        connection,
                        converted,
                        output_path,
                    )

            self.assertEqual(
                output_path.read_bytes(),
                b"previous version",
            )

    def test_publishes_car_entries_with_custom_source_view(self):
        with tempfile.TemporaryDirectory() as directory:
            output_path = Path(directory) / "car_entries.parquet"

            with duckdb.connect() as connection:
                car_entries = connection.sql("""
                    SELECT
                        'test-source' AS source_id,
                        '0' AS source_entry_index,
                        '04' AS car_number,
                        0 AS pit_stop_count
                """)
                car_entries.create_view("silver_car_entries")

                publish_silver(
                    connection,
                    car_entries,
                    output_path,
                    source_view="silver_car_entries",
                )

                rows = connection.read_parquet(
                    str(output_path)
                ).fetchall()

                self.assertEqual(
                    rows,
                    [("test-source", "0", "04", 0)],
                )

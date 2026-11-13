"""Demonstrate how separate file publications can expose mixed versions."""

import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import duckdb

from silver_writer import publish_silver


class PublicationConsistencyTests(unittest.TestCase):
    def test_separate_publications_can_leave_mixed_versions(self):
        with tempfile.TemporaryDirectory() as directory:
            first_path = Path(directory) / "first.parquet"
            second_path = Path(directory) / "second.parquet"

            with duckdb.connect() as connection:
                previous = connection.sql("""
                    SELECT 'old' AS version
                """)
                previous.write_parquet(str(first_path))
                previous.write_parquet(str(second_path))

                candidate = connection.sql("""
                    SELECT 'new' AS version
                """)
                candidate.create_view("candidate_data")

                publish_silver(
                    connection,
                    candidate,
                    first_path,
                    source_view="candidate_data",
                )

                with patch(
                    "duckdb.DuckDBPyRelation.write_parquet",
                    side_effect=OSError("Second publication failed"),
                ):
                    with self.assertRaises(OSError):
                        publish_silver(
                            connection,
                            candidate,
                            second_path,
                            source_view="candidate_data",
                        )

                first = connection.read_parquet(
                    str(first_path)
                ).fetchone()

                second = connection.read_parquet(
                    str(second_path)
                ).fetchone()

                self.assertEqual(first, ("new",))
                self.assertEqual(second, ("old",))

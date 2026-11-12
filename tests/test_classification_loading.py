import hashlib
import tempfile
import unittest
from pathlib import Path

import duckdb

from analyze_classification import load_classification_sources


class ClassificationLoadingTests(unittest.TestCase):
    def test_loads_multiple_sources_with_their_hashes(self):
        with tempfile.TemporaryDirectory() as directory:
            project_directory = Path(directory)
            sources = [
                {"source_id": "classification-a"},
                {"source_id": "classification-b"},
            ]
            expected = []

            with duckdb.connect() as connection:
                for source in sources:
                    bronze_path = (
                        project_directory
                        / "data"
                        / "bronze"
                        / source["source_id"]
                        / "document.parquet"
                    )
                    bronze_path.parent.mkdir(parents=True)

                    connection.sql(
                        """
                        SELECT
                            CAST(? AS JSON) AS session,
                            '{}'::JSON AS fastest_lap,
                            '[]'::JSON AS classification
                        """,
                        params=[
                            '{"event_name": "'
                            + source["source_id"]
                            + '"}'
                        ],
                    ).write_parquet(str(bronze_path))

                    expected.append(
                        (
                            source["source_id"],
                            hashlib.sha256(
                                bronze_path.read_bytes()
                            ).hexdigest(),
                        )
                    )

                load_classification_sources(
                    connection,
                    sources,
                    project_directory,
                )

                rows = connection.sql("""
                    SELECT
                        source_id,
                        bronze_sha256
                    FROM bronze_classification
                """).fetchall()

                self.assertCountEqual(rows, expected)

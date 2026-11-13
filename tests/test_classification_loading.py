"""Verify batch classification loading with hashes and missing-file rejection."""

import hashlib
import tempfile
import unittest
from pathlib import Path
from moto_sport_bmw_pipeline.source_loading import load_classification_csv_bronze
import duckdb
from moto_sport_bmw_pipeline.source_loading import load_exploration_source_sessions
from analyze_classification import load_classification_sources
from moto_sport_bmw_pipeline.quality import build_source_pairs


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

    def test_rejects_batch_when_a_bronze_file_is_missing(self):
        with tempfile.TemporaryDirectory() as directory:
            project_directory = Path(directory)
            sources = [
                {"source_id": "classification-a"},
                {"source_id": "classification-b"},
            ]

            bronze_path = (
                project_directory
                / "data"
                / "bronze"
                / "classification-a"
                / "document.parquet"
            )
            bronze_path.parent.mkdir(parents=True)

            with duckdb.connect() as connection:
                connection.sql("""
                    SELECT
                        '{}'::JSON AS session,
                        '{}'::JSON AS fastest_lap,
                        '[]'::JSON AS classification
                """).write_parquet(str(bronze_path))

                with self.assertRaisesRegex(
                    FileNotFoundError,
                    "missing Bronze file for source 'classification-b'",
                ):
                    load_classification_sources(
                        connection,
                        sources,
                        project_directory,
                    )

    def test_loads_csv_bronze_with_source_and_hash(self):
        with tempfile.TemporaryDirectory() as directory:
            bronze_path = Path(directory) / "document.parquet"

            with duckdb.connect() as connection:
                connection.sql("""
                    SELECT *
                    FROM (VALUES ('04'), ('24')) AS t(NUMBER)
                """).write_parquet(str(bronze_path))

                expected_hash = hashlib.sha256(
                    bronze_path.read_bytes()
                ).hexdigest()

                load_classification_csv_bronze(
                    connection,
                    bronze_path,
                    "test-source",
                )

                rows = connection.sql("""
                    SELECT NUMBER, source_id, bronze_sha256
                    FROM bronze_classification_csv
                    ORDER BY NUMBER
                """).fetchall()

                self.assertEqual(
                    rows,
                    [
                        ("04", "test-source", expected_hash),
                        ("24", "test-source", expected_hash),
                    ],
                )

    def test_maps_csv_and_pdf_to_the_same_session(self):
        catalog = {
            "championship": "imsa-weathertech",
            "season": 2023,
            "events": [{
                "event_id": "road-america",
                "session_id": "test-race",
                "classification_path": "data/raw/classification-a/report.csv",
                "pdf_path": "data/raw/pits-a/report.pdf",
            }],
        }

        with duckdb.connect() as connection:
            load_exploration_source_sessions(connection, catalog)

            rows = connection.sql("""
                SELECT
                    source_id,
                    championship,
                    season,
                    event_id,
                    session_id,
                    document_type
                FROM source_sessions
                ORDER BY document_type
            """).fetchall()

            self.assertEqual(
                rows,
                [
                    (
                        "classification-a", "imsa-weathertech", 2023,
                        "road-america", "test-race", "classification",
                    ),
                    (
                        "pits-a", "imsa-weathertech", 2023,
                        "road-america", "test-race", "pit_stops",
                    ),
                ],
            )
            project_directory = Path(__file__).resolve().parent.parent

            pairs = build_source_pairs(
                connection,
                project_directory,
            )

            self.assertEqual(
                pairs.fetchall(),
                [("classification-a", "pits-a")],
            )

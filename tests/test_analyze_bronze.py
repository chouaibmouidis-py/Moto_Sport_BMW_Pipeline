import runpy
import unittest
from pathlib import Path
from unittest.mock import patch
from analyze_bronze import select_pit_stop_sources
import duckdb
from analyze_bronze import load_source_sessions
import hashlib
import tempfile
from analyze_bronze import load_pit_stop_bronze
from analyze_bronze import transform_sessions
from analyze_bronze import transform_driver_entries
from analyze_bronze import validate_entry_links
from analyze_bronze import publish_run_outputs
from analyze_bronze import build_source_pairs


class AnalyzeBronzeTests(unittest.TestCase):
    def test_import_does_not_start_pipeline(self):
        script_path = (
            Path(__file__).resolve().parent.parent
            / "analyze_bronze.py"
        )

        with patch("duckdb.connect") as mocked_connect:
            runpy.run_path(
                str(script_path),
                run_name="analyze_bronze",
            )

        mocked_connect.assert_not_called()

    def test_selects_only_enabled_pit_stop_sources(self):
        documents = [
            {
                "source_id": "enabled-pits",
                "enabled": True,
                "document_type": "pit_stops",
            },
            {
                "source_id": "disabled-pits",
                "enabled": False,
                "document_type": "pit_stops",
            },
            {
                "source_id": "enabled-weather",
                "enabled": True,
                "document_type": "weather",
            },
        ]

        selected = select_pit_stop_sources(documents)
        self.assertEqual(selected, [documents[0]])

    def test_loads_only_enabled_source_sessions(self):
        documents = [
            {
                "source_id": "enabled-source",
                "enabled": True,
                "championship": "imsa-weathertech",
                "season": 2025,
                "event_id": "road-america",
                "session_id": "test-race",
                "document_type": "classification",
            },
            {
                "source_id": "disabled-source",
                "enabled": False,
            },
            {
                "source_id": "source-without-enabled",
            },
        ]

        with duckdb.connect() as connection:
            load_source_sessions(connection, documents)
            rows = connection.sql("""
                SELECT *
                FROM source_sessions
            """).fetchall()

            target =                 [
                    (
                        "enabled-source",
                        "imsa-weathertech",
                        2025,
                        "road-america",
                        "test-race",
                        "classification",
                    )
                ]
            self.assertEqual(rows, target)

    def test_loads_pit_stop_bronze_with_provenance(self):
        with tempfile.TemporaryDirectory() as directory:
            project_directory = Path(directory)
            bronze_path = (
                project_directory
                / "data"
                / "bronze"
                / "test-source"
                / "document.parquet"
            )
            bronze_path.parent.mkdir(parents=True)

            with duckdb.connect() as connection:
                connection.sql("""
                    SELECT
                        '{"event_name": "Test race"}'::JSON AS session,
                        '[]'::JSON AS pit_stop_analysis
                """).write_parquet(str(bronze_path))

                load_pit_stop_bronze(
                    connection,
                    [{"source_id": "test-source"}],
                    project_directory,
                )
                expected_hash = hashlib.sha256(bronze_path.read_bytes()).hexdigest()

                rows = connection.sql("""
                    SELECT
                        source_id,
                        bronze_sha256
                    FROM
                        bronze_document
                """).fetchall()
                self.assertEqual(rows, [("test-source", expected_hash)])

    def test_transform_sessions_rejects_duplicate_keys(self):
        with duckdb.connect() as connection:
            connection.execute("""
                CREATE TEMP VIEW bronze_document AS
                SELECT
                    'test-source' AS source_id,
                    'version-1' AS bronze_sha256,
                    '{}'::JSON AS session
                FROM range(2)
            """)

            project_directory = Path(__file__).resolve().parent.parent
            with self.assertRaisesRegex(ValueError, "duplicate keys"):
                transform_sessions(connection, project_directory)

    def test_transform_drivers_rejects_missing_keys(self):
        with duckdb.connect() as connection:
            connection.execute("""
                CREATE TEMP VIEW bronze_document AS
                SELECT
                    NULL::VARCHAR AS source_id,
                    'version-1' AS bronze_sha256,
                    '[{"drivers": [{"number": 1}]}]'::JSON
                        AS pit_stop_analysis
            """)

            project_directory = Path(__file__).resolve().parent.parent

            with self.assertRaisesRegex(ValueError, "missing key values"):
                transform_driver_entries(connection, project_directory)

    def test_rejects_driver_from_different_version(self):
        with duckdb.connect() as connection:
            connection.execute("""
                CREATE TEMP VIEW silver_car_entries AS
                SELECT
                    'test-source' AS source_id,
                    'version-1' AS bronze_sha256,
                    '0' AS source_entry_index
            """)

            connection.execute("""
                CREATE TEMP VIEW silver_driver_entries AS
                SELECT
                    'test-source' AS source_id,
                    'version-2' AS bronze_sha256,
                    '0' AS source_entry_index
            """)

            project_directory = Path(__file__).resolve().parent.parent

            with self.assertRaisesRegex(
                ValueError,
                "drivers do not match car entries",
            ):
                validate_entry_links(connection, project_directory)

    def test_publication_stops_after_write_failure(self):
        outputs = [
            ("silver/first.parquet", "test_output"),
            ("silver/second.parquet", "test_output"),
            ("silver/third.parquet", "test_output"),
        ]

        with duckdb.connect() as connection:
            connection.sql(
                "SELECT 1 AS value"
            ).create_view("test_output")

            with patch("analyze_bronze.publish_silver") as mocked_publish:
                mocked_publish.side_effect = [
                    None,
                    OSError("Simulated write failure"),
                ]

                with self.assertRaises(OSError):
                    publish_run_outputs(
                        connection,
                        Path("unused-run"),
                        outputs,
                    )

                self.assertEqual(mocked_publish.call_count, 2)

    def test_pairs_only_sources_from_same_session(self):
        with duckdb.connect() as connection:
            connection.execute("""
                CREATE TEMP VIEW source_sessions AS
                SELECT *
                FROM (VALUES
                    ('classification-a', 'imsa', 2025, 'event-a',
                     'race', 'classification'),
                    ('pits-a', 'imsa', 2025, 'event-a',
                     'race', 'pit_stops'),
                    ('pits-other-session', 'imsa', 2025, 'event-a',
                     'practice', 'pit_stops'),
                    ('pits-other-season', 'imsa', 2024, 'event-a',
                     'race', 'pit_stops')
                ) AS t(
                    source_id,
                    championship,
                    season,
                    event_id,
                    session_id,
                    document_type
                )
            """)

            query_path = (
                Path(__file__).resolve().parent.parent
                / "sql"
                /"29_classification_pit_stop_sources.sql"
            )

            rows = connection.sql(
                query_path.read_text(encoding="utf-8")
            ).fetchall()

            self.assertEqual(
                rows,
                [("classification-a", "pits-a")],
            )

    def test_rejects_multiple_pit_stop_reports_for_same_session(self):
        with duckdb.connect() as connection:
            connection.execute("""
                CREATE TEMP VIEW source_sessions AS
                SELECT *
                FROM (VALUES
                    ('classification-a', 'imsa', 2025, 'event-a',
                     'race', 'classification'),
                    ('pits-a', 'imsa', 2025, 'event-a',
                     'race', 'pit_stops'),
                    ('pits-b', 'imsa', 2025, 'event-a',
                     'race', 'pit_stops')
                ) AS t(
                    source_id,
                    championship,
                    season,
                    event_id,
                    session_id,
                    document_type
                )
            """)

            project_directory = Path(__file__).resolve().parent.parent

            with self.assertRaisesRegex(
                ValueError,
                "multiple pit-stop reports",
            ):
                build_source_pairs(connection, project_directory)

    def test_rejects_classification_without_matching_pit_stop_report(self):
        with duckdb.connect() as connection:
            connection.execute("""
                CREATE TEMP VIEW source_sessions AS
                SELECT *
                FROM (VALUES
                    ('classification-a', 'imsa', 2025, 'event-a',
                     'race', 'classification'),
                    ('pits-other-event', 'imsa', 2025, 'event-b',
                     'race', 'pit_stops')
                ) AS t(
                    source_id,
                    championship,
                    season,
                    event_id,
                    session_id,
                    document_type
                )
            """)

            project_directory = Path(__file__).resolve().parent.parent

            with self.assertRaisesRegex(ValueError, "missing pit-stop report"):
                build_source_pairs(connection, project_directory)

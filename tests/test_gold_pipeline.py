"""Test Gold with temporary Silver files and marts, never production data.

prepare_inputs copies the real SQL and writes synthetic Parquet inputs.
Each test then calls the real Gold builder and checks one behavior.
Expected failures are logged by the builder even when the test passes.
"""

import hashlib
import json
from pathlib import Path
import shutil
import tempfile
import unittest
from unittest.mock import patch
import duckdb
from moto_sport_bmw_pipeline.gold import build_gold_candidate, validate_gold_inputs
from moto_sport_bmw_pipeline.publication import publish_silver
from moto_sport_bmw_pipeline.run_reference import get_current_run
from moto_sport_bmw_pipeline.marts import (
    build_manufacturer_reference, enrich_csv_pdf_manufacturers,
    build_gold_race_car_summary,
)


class GoldPipelineTests(unittest.TestCase):
    def prepare_inputs(self, root):
        """Create two Silver inputs, two participant marts and their run descriptor."""
        # 1. Copy real transformation SQL into the temporary project.
        project = Path(__file__).resolve().parent.parent
        (root / "sql").mkdir()
        for name in (
            "36_manufacturer_reference.sql", "37_manufacturer_reference_input.sql",
            "38_enrich_csv_pdf_manufacturers.sql", "39_gold_race_car_summary.sql",
        ):
            shutil.copyfile(project / "sql" / name, root / "sql" / name)
        (root / "config").mkdir()
        # 2. Describe the JSON sources and write their normalized Silver evidence.
        documents = []
        with duckdb.connect() as connection:
            for source_id, document_type, filename in (
                ("class-json", "classification", "classification.parquet"),
                ("pits-json", "pit_stops", "car_entries.parquet"),
            ):
                documents.append({
                    "source_id": source_id,
                    "format": "json",
                    "document_type": document_type,
                    "enabled": True,
                })

                path = root / "data/runs/source-run/silver" / filename

                path.parent.mkdir(parents=True, exist_ok=True)

                connection.sql(
                    """
                    SELECT
                        ? AS source_id,
                        'test-bronze-hash' AS bronze_sha256,
                        '74' AS manufacturer_source_id,
                        'BMW' AS manufacturer
                    """,
                    params=[source_id],
                ).write_parquet(str(path))

            # 3. Build one participant per mart: CSV/PDF 2023 and JSON 2024.
            # These are test data; no Raw or Bronze processing runs here.
            connection.execute("""
                CREATE VIEW common_payload AS SELECT
                    'imsa-weathertech' AS championship, 'road-america' AS event_id,
                    '04' AS car_number, 'BMW M4 GT3' AS car_model,
                    'GTD' AS car_class, 1 AS overall_position,
                    1::BIGINT AS observed_pit_stop_count, 1::BIGINT AS valid_duration_count,
                    0::BIGINT AS invalid_duration_count, 60.0::DOUBLE AS average_pit_time_seconds,
                    100.0::DOUBLE AS duration_coverage_percent,
                    'Team Test' AS team_name,
                    100 AS completed_laps,
                    42 AS fastest_lap_number,
                    219.6::DOUBLE AS fastest_lap_speed_kph,
                    '1:00:00.000' AS total_time_raw,
                    3600.0::DOUBLE AS total_time_seconds,
                    '1:30.000' AS fastest_lap_time_raw,
                    90.0::DOUBLE AS fastest_lap_time_seconds,
                    '+1:17.343' AS gap_first_raw,
                    '2 Laps' AS gap_previous_raw,
                    'time' AS gap_first_kind,
                    77.343::DOUBLE AS gap_first_seconds,
                    CAST(NULL AS INTEGER) AS gap_first_laps,
                    'laps' AS gap_previous_kind,
                    CAST(NULL AS DOUBLE) AS gap_previous_seconds,
                    2::INTEGER AS gap_previous_laps
            """)
            csv_path = root / "data/csv_pdf/road-america-2023/marts/race_car_summary.parquet"
            csv_path.parent.mkdir(parents=True)
            connection.sql("""
                SELECT *, 2023 AS season, 'race-2023' AS session_id,
                    'class-csv' AS source_id, 'csv-version' AS bronze_sha256,
                    '74' AS manufacturer_source_id, 'Classified' AS classification_status,
                    NULL::VARCHAR AS manufacturer, NULL::VARCHAR AS manufacturer_mapping_status,
                    'pits-pdf' AS pit_stop_source_id, 'pdf-version' AS pit_stop_bronze_sha256,
                    'pdf-hash' AS pdf_sha256, NULL::INTEGER AS reported_pit_stop_count,
                    'unavailable_reported_count' AS comparison_status,
                    'available' AS stop_detail_status
                FROM common_payload
            """).write_parquet(str(csv_path))
            json_path = root / "data/runs/source-run/marts/race_car_summary.parquet"
            json_path.parent.mkdir(parents=True)
            connection.sql("""
                SELECT *, 2024 AS season, 'race-2024' AS session_id,
                    'class-json' AS source_id, 'json-version' AS bronze_sha256,
                    'BMW' AS manufacturer, '0' AS source_entry_index,
                    FALSE AS not_finished, 1 AS reported_pit_stop_count,
                    'pits-json' AS pit_stop_source_id, 'pit-version' AS pit_stop_bronze_sha256,
                    'matched' AS comparison_status
                FROM common_payload
            """).write_parquet(str(json_path))
        # 4. Declare the four files and select processing-run as the active input.
        (root / "config/sources.json").write_text(json.dumps({"documents": documents}))
        processing = root / "data/processing/runs/processing-run"
        processing.mkdir(parents=True)
        (processing / "sources.json").write_text(json.dumps({"documents": documents}))
        descriptor = {
            "outputs": [
                {
                    "role": "json_participant_mart",
                    "path": json_path.relative_to(root).as_posix(),
                },
                {
                    "role": "csv_pdf_participant_mart",
                    "path": csv_path.relative_to(root).as_posix(),
                },
                {
                    "role": "json_silver_classification",
                    "path": "data/runs/source-run/silver/classification.parquet",
                },
                {
                    "role": "json_silver_car_entries",
                    "path": "data/runs/source-run/silver/car_entries.parquet",
                },
            ],
            "bronze_hashes": {},
        }
        (processing / "outputs.json").write_text(json.dumps(descriptor))
        (root / "data/processing/current.json").write_text('{"run_id":"processing-run"}')
        (root / "data/current.json").write_text('{"run_id":"source-run"}')

    def test_publishes_reproducible_gold_without_changing_main_reference(self):
        """Publish two participants and record the exact Silver and mart inputs."""
        # Prepare inputs -> build Gold -> check published data and provenance.
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self.prepare_inputs(root)

            # The builder receives the temporary project root, not a data table.
            run = build_gold_candidate(root)
            self.assertEqual(get_current_run(root / "data/gold").resolve(), run)
            self.assertEqual((root / "data/current.json").read_text(), '{"run_id":"source-run"}')
            validate_gold_inputs(run)
            manifest = json.loads((run / "inputs.json").read_text())
            self.assertEqual(manifest["source_run_id"], "processing-run")
            # Gold must copy Silver files, never re-read Bronze files.
            expected_inputs = [
                ("source_manifest", "data/processing/runs/processing-run/sources.json"),
                ("processing_run", "data/processing/runs/processing-run/outputs.json"),
                *[
                    ("transformation_sql", f"sql/{name}")
                    for name in (
                        "36_manufacturer_reference.sql",
                        "37_manufacturer_reference_input.sql",
                        "38_enrich_csv_pdf_manufacturers.sql",
                        "39_gold_race_car_summary.sql",
                    )
                ],
                (
                    "json_silver_classification",
                    "data/runs/source-run/silver/classification.parquet",
                ),
                (
                    "json_silver_car_entries",
                    "data/runs/source-run/silver/car_entries.parquet",
                ),
                ("json_participant_mart", "data/runs/source-run/marts/race_car_summary.parquet"),
                ("csv_pdf_participant_mart", "data/csv_pdf/road-america-2023/marts/race_car_summary.parquet"),
            ]
            self.assertCountEqual(
                [(record["role"], record["source_path"], record["snapshot_path"])
                 for record in manifest["inputs"]],
                [(role, path, f"inputs/{path}") for role, path in expected_inputs],
            )
            for record in manifest["inputs"]:
                snapshot = run / record["snapshot_path"]
                self.assertEqual(hashlib.sha256(snapshot.read_bytes()).hexdigest(), record["sha256"])
            with duckdb.connect() as connection:
                saved = connection.read_parquet(str(run / "race_car_summary.parquet"))
                self.assertEqual(len(saved.columns), 45)
                self.assertEqual(saved.project(
                    "season, manufacturer, manufacturer_origin, not_finished"
                ).order("season").fetchall(), [
                    (2023, "BMW", "reference", None), (2024, "BMW", "source", False),
                ])
                evidence = connection.read_parquet(str(run / "manufacturer_evidence.parquet"))
                self.assertEqual(evidence.project("source_id").distinct().order("source_id").fetchall(),
                                 [("class-json",), ("pits-json",)])

    def test_rebuilds_identical_gold_from_copied_inputs(self):
        """After deleting original inputs, rebuild the same rows from Gold copies."""
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self.prepare_inputs(root)
            run = build_gold_candidate(root)
            manifest = json.loads((run / "inputs.json").read_text())

            # Remove original inputs and rebuild from the frozen tree only.
            for record in manifest["inputs"]:
                (root / record["source_path"]).unlink()
            validate_gold_inputs(run)

            frozen = run / "inputs"

            with duckdb.connect() as connection:
                for role, view in (
                    ("json_silver_classification", "silver_classification"),
                    ("json_silver_car_entries", "silver_car_entries"),
                ):
                    paths = [
                        str(run / record["snapshot_path"])
                        for record in manifest["inputs"]
                        if record["role"] == role
                    ]
                    connection.read_parquet(paths).create_view(view)

                # ID 74 and name BMW come from the two copied Silver files.
                build_manufacturer_reference(connection, frozen)
                for role, view in (
                    ("csv_pdf_participant_mart", "csv_pdf_race_summary"),
                    ("json_participant_mart", "json_race_car_summary"),
                ):
                    paths = [
                        str(run / record["snapshot_path"])
                        for record in manifest["inputs"]
                        if record["role"] == role
                    ]
                    connection.read_parquet(paths).create_view(view)

                # Resolve the CSV/PDF manufacturer, then stack the two marts.
                enrich_csv_pdf_manufacturers(connection, frozen)
                rebuilt = build_gold_race_car_summary(connection, frozen)
                saved = connection.read_parquet(str(run / "race_car_summary.parquet"))
                self.assertEqual(rebuilt.columns, saved.columns)
                self.assertCountEqual(rebuilt.fetchall(), saved.fetchall())


    def test_gold_includes_configured_csv_pdf_seasons(self):
        """A third declared mart must contribute its 2022 participant."""
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self.prepare_inputs(root)
            descriptor_path = root / "data/processing/runs/processing-run/outputs.json"
            descriptor = json.loads(descriptor_path.read_text())
            previous = root / "data/csv_pdf/road-america-2023/marts/race_car_summary.parquet"
            added = root / "data/csv_pdf/road-america-2022/marts/race_car_summary.parquet"
            added.parent.mkdir(parents=True)
            with duckdb.connect() as connection:
                rows = connection.read_parquet(str(previous))
                rows.create_view("previous")
                connection.sql("""
                    SELECT * REPLACE (
                        2022 AS season, 'race-2022' AS session_id,
                        'class-csv-2022' AS source_id,
                        'csv-version-2022' AS bronze_sha256,
                        'pits-pdf-2022' AS pit_stop_source_id
                    ) FROM previous
                """).write_parquet(str(added))
            descriptor["outputs"].append({"role": "csv_pdf_participant_mart", "path": added.relative_to(root).as_posix()})
            descriptor_path.write_text(json.dumps(descriptor))
            run = build_gold_candidate(root)
            with duckdb.connect() as connection:
                self.assertEqual(
                    connection.read_parquet(str(run / "race_car_summary.parquet")).project("season").order("season").fetchall(),
                    [(2022,), (2023,), (2024,)],
                )

    def test_wrong_selection_preserves_gold(self):
        """A different requested selection must not replace the active Gold."""
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self.prepare_inputs(root)
            build_gold_candidate(root)
            reference = root / "data/gold/current.json"
            previous = reference.read_bytes()
            # Expected rejection: the traceback in the log is intentional.
            with self.assertRaisesRegex(ValueError, "selection differs"):
                build_gold_candidate(root, expected_source_ids=["another-source"])
            self.assertEqual(reference.read_bytes(), previous)

    def test_changed_processing_output_preserves_gold(self):
        """A modified input must be rejected before changing the active Gold."""
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self.prepare_inputs(root)
            build_gold_candidate(root)
            reference = root / "data/gold/current.json"
            previous = reference.read_bytes()

            descriptor_path = root / "data/processing/runs/processing-run/outputs.json"
            descriptor = json.loads(descriptor_path.read_text())
            # Record expected bytes before deliberately altering one input.
            for output in descriptor["outputs"]:
                output["sha256"] = hashlib.sha256((root / output["path"]).read_bytes()).hexdigest()
            descriptor_path.write_text(json.dumps(descriptor))
            (root / descriptor["outputs"][0]["path"]).write_bytes(b"changed after processing")
            # Expected rejection: the traceback in the log is intentional.
            with self.assertRaisesRegex(ValueError, "processing output changed"):
                build_gold_candidate(root)
            self.assertEqual(reference.read_bytes(), previous)

    def test_second_output_failure_preserves_previous_gold_reference(self):
        """Fail the second write and keep the previous Gold data and reference."""
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self.prepare_inputs(root)
            previous_run = build_gold_candidate(root)
            reference = root / "data/gold/current.json"
            previous_reference = reference.read_bytes()
            previous_output = (previous_run / "race_car_summary.parquet").read_bytes()
            publication_count = 0

            # Only this test replaces the writer; the second call must fail.
            def fail_second_output(*args, **kwargs):
                nonlocal publication_count
                publication_count += 1
                if publication_count == 2:
                    raise OSError("Simulated publication failure")
                return publish_silver(*args, **kwargs)

            # An OSError and its error log are expected, not a test failure.
            with patch(
                "moto_sport_bmw_pipeline.publication.publish_silver",
                side_effect=fail_second_output,
            ):
                with self.assertRaisesRegex(OSError, "publication failure"):
                    build_gold_candidate(root)
            self.assertEqual(publication_count, 2)
            candidate, = (
                path for path in (root / "data/gold/runs").iterdir()
                if path.resolve() != previous_run
            )
            with duckdb.connect() as connection:
                self.assertEqual(
                    connection.read_parquet(
                        str(candidate / "race_car_summary.parquet")
                    ).project("season").order("season").fetchall(),
                    [(2023,), (2024,)],
                )
            self.assertFalse((candidate / "manufacturer_reference.parquet").exists())
            self.assertFalse((candidate / "manufacturer_evidence.parquet").exists())
            self.assertEqual(reference.read_bytes(), previous_reference)
            self.assertEqual(get_current_run(root / "data/gold").resolve(), previous_run)
            self.assertEqual(
                (previous_run / "race_car_summary.parquet").read_bytes(),
                previous_output,
            )
            self.assertEqual((root / "data/current.json").read_text(), '{"run_id":"source-run"}')

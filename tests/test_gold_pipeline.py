"""Verify isolated Gold snapshots, cross-season publication and activation failures."""

import hashlib
import json
from pathlib import Path
import shutil
import tempfile
import unittest
from unittest.mock import patch

import duckdb

from moto_sport_bmw_pipeline.gold import build_gold_candidate, validate_gold_inputs
from moto_sport_bmw_pipeline.run_reference import get_current_run


class GoldPipelineTests(unittest.TestCase):
    def prepare_inputs(self, root):
        project = Path(__file__).resolve().parent.parent
        (root / "sql").mkdir()
        for name in (
            "36_manufacturer_reference.sql", "37_manufacturer_reference_input.sql",
            "38_enrich_2023_manufacturers.sql", "39_gold_race_car_summary.sql",
        ):
            shutil.copyfile(project / "sql" / name, root / "sql" / name)
        (root / "config").mkdir()
        documents = []
        with duckdb.connect() as connection:
            for source_id, document_type, field in (
                ("class-json", "classification", "classification"),
                ("pits-json", "pit_stops", "pit_stop_analysis"),
            ):
                documents.append({
                    "source_id": source_id, "document_type": document_type, "enabled": True,
                })
                path = root / "data/bronze" / source_id / "document.parquet"
                path.parent.mkdir(parents=True)
                connection.sql(f"""
                    SELECT '{{}}'::JSON AS session, '{{}}'::JSON AS fastest_lap,
                    '[{{"imsa_manufacturerid":"74","manufacturer":"BMW"}}]'::JSON AS {field}
                """).write_parquet(str(path))

            # Common mart payload; each source keeps independent version metadata.
            connection.execute("""
                CREATE VIEW common_payload AS SELECT
                    'imsa-weathertech' AS championship, 'road-america' AS event_id,
                    '04' AS car_number, 'BMW M4 GT3' AS car_model,
                    'GTD' AS car_class, 1 AS overall_position,
                    1::BIGINT AS observed_pit_stop_count, 1::BIGINT AS valid_duration_count,
                    0::BIGINT AS invalid_duration_count, 60.0::DOUBLE AS average_pit_time_seconds,
                    100.0::DOUBLE AS duration_coverage_percent
            """)
            csv_path = root / "data/exploration/road-america-2023/marts/race_car_summary.parquet"
            csv_path.parent.mkdir(parents=True)
            connection.sql("""
                SELECT *, 2023 AS season, 'race-2023' AS session_id,
                    'class-csv' AS source_id, 'csv-version' AS bronze_sha256,
                    '74' AS manufacturer_source_id, 'Classified' AS classification_status,
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
        (root / "config/sources.json").write_text(json.dumps({"documents": documents}))
        (root / "config/exploration_2023.json").write_text(json.dumps({
            "season": 2023, "events": [{"event_id": "road-america"}],
        }))
        (root / "data/current.json").write_text('{"run_id":"source-run"}')

    def test_publishes_reproducible_gold_without_changing_main_reference(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self.prepare_inputs(root)
            run = build_gold_candidate(root)
            self.assertEqual(get_current_run(root / "data/gold").resolve(), run)
            self.assertEqual((root / "data/current.json").read_text(), '{"run_id":"source-run"}')
            validate_gold_inputs(run)
            manifest = json.loads((run / "inputs.json").read_text())
            self.assertEqual(manifest["source_run_id"], "source-run")
            self.assertEqual(len(manifest["inputs"]), 10)
            for record in manifest["inputs"]:
                snapshot = run / record["snapshot_path"]
                self.assertEqual(hashlib.sha256(snapshot.read_bytes()).hexdigest(), record["sha256"])
            with duckdb.connect() as connection:
                saved = connection.read_parquet(str(run / "race_car_summary.parquet"))
                self.assertEqual(len(saved.columns), 29)
                self.assertEqual(saved.project(
                    "season, manufacturer, manufacturer_origin, not_finished"
                ).order("season").fetchall(), [
                    (2023, "BMW", "reference", None), (2024, "BMW", "source", False),
                ])
                evidence = connection.read_parquet(str(run / "manufacturer_evidence.parquet"))
                self.assertEqual(evidence.project("source_id").distinct().order("source_id").fetchall(),
                                 [("class-json",), ("pits-json",)])
            # Remove original inputs and rebuild from the frozen tree only.
            for record in manifest["inputs"]:
                (root / record["source_path"]).unlink()
            validate_gold_inputs(run)
            from moto_sport_bmw_pipeline.source_loading import (
                load_classification_sources, load_pit_stop_bronze,
                select_classification_sources, select_pit_stop_sources,
            )
            from moto_sport_bmw_pipeline.marts import (
                build_manufacturer_reference, enrich_2023_manufacturers,
                build_gold_race_car_summary,
            )
            frozen = run / "inputs"
            sources = json.loads((frozen / "config/sources.json").read_text())["documents"]
            with duckdb.connect() as connection:
                load_pit_stop_bronze(connection, select_pit_stop_sources(sources), frozen)
                load_classification_sources(connection, select_classification_sources(sources), frozen)
                build_manufacturer_reference(connection, frozen)
                for role, view in (
                    ("csv_pdf_participant_mart", "csv_pdf_race_summary"),
                    ("json_participant_mart", "json_race_car_summary"),
                ):
                    paths = [str(run / r["snapshot_path"]) for r in manifest["inputs"] if r["role"] == role]
                    connection.read_parquet(paths).create_view(view)
                enrich_2023_manufacturers(connection, frozen)
                rebuilt = build_gold_race_car_summary(connection, frozen)
                saved = connection.read_parquet(str(run / "race_car_summary.parquet"))
                self.assertEqual(rebuilt.columns, saved.columns)
                self.assertCountEqual(rebuilt.fetchall(), saved.fetchall())

    def test_publication_failure_preserves_previous_gold_reference(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self.prepare_inputs(root)
            reference = root / "data/gold/current.json"
            reference.parent.mkdir(parents=True)
            reference.write_bytes(b'{"run_id":"previous-gold"}')
            with patch(
                "moto_sport_bmw_pipeline.gold.publish_run_outputs",
                side_effect=OSError("Simulated publication failure"),
            ):
                with self.assertRaisesRegex(OSError, "publication failure"):
                    build_gold_candidate(root)
            self.assertEqual(reference.read_bytes(), b'{"run_id":"previous-gold"}')
            self.assertEqual((root / "data/current.json").read_text(), '{"run_id":"source-run"}')

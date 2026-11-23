"""Verify manifest-driven execution, format dispatch and publication isolation."""

import hashlib
import json
import logging
from pathlib import Path
import shutil
import tempfile
import unittest
from unittest.mock import patch

import duckdb
from pypdf import PdfWriter

from moto_sport_bmw_pipeline.manifest import select_documents
from moto_sport_bmw_pipeline.logging_config import RunContextFilter
from moto_sport_bmw_pipeline.orchestration import main, run_stages
from moto_sport_bmw_pipeline.pipeline import build_processing_run
from moto_sport_bmw_pipeline.parquet_writer import publish_parquet
from moto_sport_bmw_pipeline.run_reference import get_current_run


def documents(season=2022, formats=("csv", "pdf")):
    return [{
        "source_id": f"{season}-{role}", "enabled": True,
        "championship": "imsa-weathertech", "season": season,
        "event_id": "daytona", "session_id": f"race-{season}",
        "document_type": role, "format": format,
        "filename": f"report.{format}", "url": "https://example.invalid/report",
    } for role, format in zip(("classification", "pit_stops"), formats)]


class RunPipelineTests(unittest.TestCase):
    def test_csv_pdf_logs_identify_source_and_aggregate_boundaries(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            sources = self.prepare_csv_pdf(root)
            with patch("moto_sport_bmw_pipeline.bronze.extract_stops", return_value=[]):
                with self.assertLogs("moto_sport_bmw_pipeline", level="INFO") as captured:
                    # assertLogs installs its own handler; attach the same context
                    # filter used by normal console/file handlers before execution.
                    handler = logging.getLogger("moto_sport_bmw_pipeline").handlers[0]
                    handler.addFilter(RunContextFilter())
                    run_stages(root, sources)
            records = captured.records
            for stage, source_id in (
                ("raw", "2022-classification"), ("raw", "2022-pit_stops"),
                ("bronze", "2022-classification"), ("bronze", "2022-pit_stops"),
                ("silver", "2022-classification"), ("silver", "2022-pit_stops"),
            ):
                with self.subTest(stage=stage, source_id=source_id):
                    matching = [r for r in records if r.stage == stage and r.source_id == source_id]
                    self.assertTrue(matching)
                    self.assertTrue(all(r.run_id != "-" for r in matching))
            processing = get_current_run(root / "data/processing").name
            gold = get_current_run(root / "data/gold").name
            self.assertTrue(any(r.run_id == processing and r.stage == "process" for r in records))
            self.assertTrue(any(r.run_id == gold and r.stage == "gold_write" and r.source_id == "-" for r in records))

    def test_raw_failure_is_logged_with_source_before_propagation(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            sources = self.prepare_csv_pdf(root)
            sources[0]["expected_sha256"] = "0" * 64
            with self.assertLogs("moto_sport_bmw_pipeline", level="INFO") as captured:
                logging.getLogger("moto_sport_bmw_pipeline").handlers[0].addFilter(RunContextFilter())
                with self.assertRaisesRegex(ValueError, "Raw fingerprint mismatch"):
                    run_stages(root, sources)
            failures = [r for r in captured.records if r.levelno >= logging.ERROR]
            self.assertTrue(any(
                r.stage == "raw" and r.source_id == "2022-classification"
                and r.run_id != "-" and r.exc_info is not None
                for r in failures
            ))
            self.assertFalse((root / "data/processing/current.json").exists())

    def test_manifest_selects_formats_and_season_without_mutating_input(self):
        sources = documents(2022) + documents(2024, ("json", "json"))
        original = json.dumps(sources)
        selected = select_documents({"documents": sources}, season=2022)
        self.assertEqual([s["format"] for s in selected], ["csv", "pdf"])
        self.assertEqual(json.dumps(sources), original)

    def test_duplicate_or_missing_pair_rejected_before_execution(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "config").mkdir()
            for sources, message in ((documents() * 2, "Duplicate source_id"), (documents()[:1], "Missing paired report")):
                (root / "config/sources.json").write_text(json.dumps({"documents": sources}))
                with patch("moto_sport_bmw_pipeline.orchestration.run_stages") as run:
                    with self.assertRaisesRegex(ValueError, message):
                        main([], project_directory=root)
                    run.assert_not_called()

    def test_unsupported_reader_and_unsafe_source_are_rejected(self):
        for field, value, message in (("format", "unknown", "Unsupported report"), ("source_id", "../outside", "Unsafe source_id"), ("format", None, "Invalid format")):
            with self.subTest(field=field, value=value):
                sources = documents()
                sources[0][field] = value
                with self.assertRaisesRegex(ValueError, message):
                    select_documents({"documents": sources})

    def test_pinned_source_mismatch_preserves_existing_raw_and_prevents_download(self):
        from moto_sport_bmw_pipeline.raw_download import prepare_source
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            sources = self.prepare_csv_pdf(root)
            source = sources[0]
            raw = root / "data/raw" / source["source_id"] / source["filename"]
            source["expected_sha256"] = "0" * 64
            previous = raw.read_bytes()
            with patch("moto_sport_bmw_pipeline.raw_download.download") as download:
                with self.assertRaisesRegex(ValueError, "Raw fingerprint mismatch"):
                    prepare_source(root, source)
                download.assert_not_called()
            self.assertEqual(raw.read_bytes(), previous)

    def test_acquisition_failure_prevents_bronze_processing_and_gold(self):
        with patch("moto_sport_bmw_pipeline.orchestration.prepare_source", side_effect=ValueError("invalid source")), patch("moto_sport_bmw_pipeline.orchestration.build_source") as bronze, patch("moto_sport_bmw_pipeline.orchestration.build_processing_run") as process, patch("moto_sport_bmw_pipeline.orchestration.build_gold_candidate") as gold:
            with self.assertRaisesRegex(ValueError, "invalid source"):
                run_stages(Path("."), documents())
            bronze.assert_not_called()
            process.assert_not_called()
            gold.assert_not_called()

    def test_bronze_failure_prevents_processing_and_gold(self):
        with patch("moto_sport_bmw_pipeline.orchestration.prepare_source"), patch("moto_sport_bmw_pipeline.orchestration.build_source", side_effect=OSError("write failed")), patch("moto_sport_bmw_pipeline.orchestration.build_processing_run") as process, patch("moto_sport_bmw_pipeline.orchestration.build_gold_candidate") as gold:
            with self.assertRaisesRegex(OSError, "write failed"):
                run_stages(Path("."), documents())
            process.assert_not_called()
            gold.assert_not_called()

    def prepare_csv_pdf(self, root):
        project = Path(__file__).resolve().parent.parent
        shutil.copytree(project / "sql", root / "sql")
        (root / "config").mkdir()
        sources = documents()
        csv = root / "data/raw" / sources[0]["source_id"] / sources[0]["filename"]
        csv.parent.mkdir(parents=True)
        csv.write_text(
            "NUMBER;VEHICLE;POSITION;CLASS;STATUS;IMSA_ManufacturerId;TEAM;LAPS;FL_LAPNUM;FL_KPH;TOTAL_TIME;FL_TIME;GAP_FIRST;GAP_PREVIOUS\n"
            "01;BMW M4 GT3;1;GTD;Classified;74;Test Team;100;42;219.6;1:00:00.000;1:30.000;pending review;-\n"
        )
        pdf = root / "data/raw" / sources[1]["source_id"] / sources[1]["filename"]
        pdf.parent.mkdir(parents=True)
        writer = PdfWriter()
        writer.add_blank_page(width=600, height=800)
        writer.write(pdf)
        for source in sources:
            raw = root / "data/raw" / source["source_id"] / source["filename"]
            source["expected_sha256"] = hashlib.sha256(raw.read_bytes()).hexdigest()
        (root / "config/sources.json").write_text(json.dumps({"documents": sources}))
        return sources

    def test_csv_pdf_runs_through_common_pipeline_without_json_or_second_catalog(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self.prepare_csv_pdf(root)
            stop = {"car_number": "01", "pit_number": 1, "pit_time_raw": "1:00.000", "page_number": 1, "column_number": 1, "block_line_number": 2, "source_line": "test"}
            with patch("moto_sport_bmw_pipeline.bronze.extract_stops", return_value=[stop]):
                gold_run = main([], project_directory=root)
            processing = get_current_run(root / "data/processing")
            self.assertEqual(get_current_run(root / "data/gold").resolve(), gold_run)
            self.assertFalse((root / "data/current.json").exists())
            with duckdb.connect() as connection:
                saved = connection.read_parquet(str(gold_run / "race_car_summary.parquet"))
                self.assertEqual(saved.project("season, car_number, observed_pit_stop_count").fetchall(), [(2022, "01", 1)])
                report = connection.read_parquet(str(processing / "reports/2022-classification/quality/classification_gap_issues.parquet"))
                self.assertEqual(report.project("field_name, raw_value").fetchall(), [("GAP_FIRST", "pending review")])

    def test_report_write_failure_preserves_previous_processing_and_gold(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            sources = self.prepare_csv_pdf(root)
            with patch("moto_sport_bmw_pipeline.bronze.extract_stops", return_value=[]):
                main([], project_directory=root)
            previous_processing = (root / "data/processing/current.json").read_bytes()
            previous_gold = (root / "data/gold/current.json").read_bytes()
            count = 0
            def fail_report(*args, **kwargs):
                nonlocal count
                count += 1
                if count == 2:
                    raise OSError("report write failed")
                return publish_parquet(*args, **kwargs)
            with patch("moto_sport_bmw_pipeline.pipeline.publish_parquet", side_effect=fail_report):
                with self.assertRaisesRegex(OSError, "report write failed"):
                    build_processing_run(root, sources)
            self.assertEqual((root / "data/processing/current.json").read_bytes(), previous_processing)
            self.assertEqual((root / "data/gold/current.json").read_bytes(), previous_gold)

    def test_json_and_mixed_sources_use_the_same_pipeline(self):
        for mixed in (False, True):
            with self.subTest(mixed=mixed), tempfile.TemporaryDirectory() as directory:
                root = Path(directory)
                csv_sources = self.prepare_csv_pdf(root)
                json_sources = documents(2024, ("json", "json"))
                car = {"number": "24", "vehicle": "BMW M Hybrid V8", "manufacturer": "BMW", "imsa_manufacturerid": "74", "class": "GTP", "position": "1", "pit_stops": "0", "not_finished": False}
                payloads = [
                    {"session": {}, "fastest_lap": {}, "classification": [car]},
                    {"session": {}, "pit_stop_analysis": [{**car, "drivers": [], "pit_stops": []}]},
                ]
                for source, payload in zip(json_sources, payloads):
                    raw = root / "data/raw" / source["source_id"] / source["filename"]
                    raw.parent.mkdir(parents=True)
                    raw.write_text(json.dumps(payload))
                    source["expected_sha256"] = hashlib.sha256(raw.read_bytes()).hexdigest()
                selected = json_sources + csv_sources if mixed else json_sources
                (root / "config/sources.json").write_text(json.dumps({"documents": selected}))
                with patch("moto_sport_bmw_pipeline.bronze.extract_stops", return_value=[]):
                    with patch("moto_sport_bmw_pipeline.orchestration.configure_logging"):
                        with self.assertLogs("moto_sport_bmw_pipeline", level="INFO") as captured:
                            logging.getLogger("moto_sport_bmw_pipeline").handlers[0].addFilter(RunContextFilter())
                            run = main([], project_directory=root)
                with duckdb.connect() as connection:
                    actual = connection.read_parquet(str(run / "race_car_summary.parquet")).project("season").order("season").fetchall()
                self.assertEqual(actual, [(2022,), (2024,)] if mixed else [(2024,)])
                self.assertTrue(any(
                    record.stage == "load_bronze" and record.source_id == "2024-classification"
                    and record.run_id != "-" for record in captured.records
                ))
                self.assertTrue(any(
                    record.stage == "silver" and record.source_id == "-"
                    and record.run_id != "-" for record in captured.records
                ))

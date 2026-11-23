"""Check operational logging and that CLI modules are safe to import."""
import io
import logging
from pathlib import Path
import runpy
import tempfile
import unittest
from unittest.mock import patch

from moto_sport_bmw_pipeline.logging_config import (
    RunContextFilter, configure_logging, log_context, log_operation,
)


class ApplicationLoggingTests(unittest.TestCase):
    def setUp(self):
        self.logger = logging.getLogger("moto_sport_bmw_pipeline")
        self.old_handlers = list(self.logger.handlers)
        self.old_level = self.logger.level
        self.old_propagate = self.logger.propagate
        self.logger.handlers.clear()

    def tearDown(self):
        for handler in self.logger.handlers:
            handler.close()
        self.logger.handlers[:] = self.old_handlers
        self.logger.setLevel(self.old_level)
        self.logger.propagate = self.old_propagate

    def test_configuration_does_not_duplicate_logs_and_preserves_run_context(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "logs" / "pipeline.log"
            stream = io.StringIO()
            with patch.dict("os.environ", {"BMW_LOG_LEVEL": "INFO", "BMW_LOG_FILE": ""}), patch("sys.stderr", stream):
                configure_logging(log_file=path)
                configure_logging(log_file=path)
                child = logging.getLogger("moto_sport_bmw_pipeline.test")
                with log_context("candidate-42"):
                    child.info("Contrôle réussi")
                child.debug("Hidden debug details")
                for handler in self.logger.handlers:
                    handler.flush()
                console = stream.getvalue()
                saved = path.read_text(encoding="utf-8")
                self.assertEqual(console.count("Contrôle réussi"), 1)
                self.assertEqual(saved.count("Contrôle réussi"), 1)
                self.assertIn("run=candidate-42", saved)
                self.assertNotIn("Hidden debug details", console)

    def test_verbose_mode_emits_debug_details(self):
        stream = io.StringIO()
        with patch.dict("os.environ", {"BMW_LOG_LEVEL": "INFO", "BMW_LOG_FILE": ""}), patch("sys.stderr", stream):
            configure_logging(verbose=True)
            logging.getLogger("moto_sport_bmw_pipeline.test").debug("Diagnostic details")
        self.assertIn("DEBUG", stream.getvalue())
        self.assertIn("Diagnostic details", stream.getvalue())

    def test_nested_source_inherits_run_and_stage_then_restores_them(self):
        stream = io.StringIO()
        with patch.dict("os.environ", {"BMW_LOG_LEVEL": "INFO", "BMW_LOG_FILE": ""}), patch("sys.stderr", stream):
            configure_logging()
            child = logging.getLogger("moto_sport_bmw_pipeline.test")
            child.info("Before context")
            with log_context("run-42", stage="bronze"):
                with log_context(source_id="source-a"):
                    child.info("Inside source")
                child.info("After source")
            child.info("After run")

        lines = stream.getvalue().splitlines()
        self.assertIn("run=- | stage=- | source_id=- | Before context", lines[0])
        self.assertIn("run=run-42 | stage=bronze | source_id=source-a | Inside source", lines[1])
        self.assertIn("run=run-42 | stage=bronze | source_id=- | After source", lines[2])
        self.assertIn("run=- | stage=- | source_id=- | After run", lines[3])

    def test_exception_restores_context_and_is_propagated(self):
        context_filter = RunContextFilter()
        with log_context("outer-run", stage="process", source_id="outer-source"):
            with self.assertRaisesRegex(ValueError, "test failure"):
                with log_context("inner-run", stage="gold", source_id="inner-source"):
                    raise ValueError("test failure")
            record = logging.makeLogRecord({})
            context_filter.filter(record)
            self.assertEqual(
                (record.run_id, record.stage, record.source_id),
                ("outer-run", "process", "outer-source"),
            )

        record = logging.makeLogRecord({})
        context_filter.filter(record)
        self.assertEqual((record.run_id, record.stage, record.source_id), ("-", "-", "-"))

    def test_filter_preserves_explicit_fields_and_completes_missing_ones(self):
        with log_context("run-42", stage="bronze", source_id="context-source"):
            record = logging.makeLogRecord({"source_id": "explicit-source"})
            self.assertTrue(RunContextFilter().filter(record))
        self.assertEqual(
            (record.run_id, record.stage, record.source_id),
            ("run-42", "bronze", "explicit-source"),
        )

    def test_operation_success_has_context_and_no_duplicate_messages(self):
        stream = io.StringIO()
        with patch.dict("os.environ", {"BMW_LOG_LEVEL": "INFO", "BMW_LOG_FILE": ""}), patch("sys.stderr", stream):
            configure_logging()
            child = logging.getLogger("moto_sport_bmw_pipeline.test")
            with log_operation(child, "Normalize report", run_id="run-42", stage="silver", source_id="source-a"):
                child.info("Rows validated")
        lines = stream.getvalue().splitlines()
        self.assertEqual(len(lines), 3)
        for line in lines:
            self.assertIn("run=run-42 | stage=silver | source_id=source-a", line)

    def test_failed_operation_output_contains_context_and_propagates(self):
        stream = io.StringIO()
        with patch.dict("os.environ", {"BMW_LOG_LEVEL": "INFO", "BMW_LOG_FILE": ""}), patch("sys.stderr", stream):
            configure_logging()
            child = logging.getLogger("moto_sport_bmw_pipeline.test")
            with self.assertRaisesRegex(ValueError, "invalid input"):
                with log_operation(child, "Normalize report", run_id="run-42", stage="silver", source_id="source-a"):
                    raise ValueError("invalid input")
            child.info("After failure")
        output = stream.getvalue()
        self.assertIn("run=run-42 | stage=silver | source_id=source-a | Failed: Normalize report", output)
        self.assertNotIn("Completed: Normalize report", output)
        self.assertIn("run=- | stage=- | source_id=- | After failure", output)

    def test_workflow_propagates_logging_options_to_common_stages(self):
        from moto_sport_bmw_pipeline.orchestration import main

        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "config").mkdir()
            (root / "config" / "sources.json").write_text(
                '{"documents": []}', encoding="utf-8"
            )
            log_file = root / "logs" / "pipeline.log"
            with patch("moto_sport_bmw_pipeline.orchestration.PROJECT_DIR", root), patch(
                "moto_sport_bmw_pipeline.orchestration.run_stages"
            ) as run, patch("moto_sport_bmw_pipeline.orchestration.select_documents", return_value=[{"source_id": "test"}]), patch("sys.stderr", io.StringIO()):
                main(["--verbose", "--log-file", str(log_file)])
            run.assert_called_once_with(root, [{"source_id": "test"}], stage="all", refresh=False, verbose=True)
            self.assertTrue(log_file.is_file())


class InspectionImportTests(unittest.TestCase):
    def test_package_command_exposes_pipeline_help(self):
        from moto_sport_bmw_pipeline import main

        with patch("sys.argv", ["moto-sport-bmw-pipeline", "--help"]), patch(
            "sys.stdout", io.StringIO()
        ) as output:
            with self.assertRaises(SystemExit) as error:
                main()
        self.assertEqual(error.exception.code, 0)
        self.assertIn("--log-file", output.getvalue())

    def test_import_does_not_read_data_or_start_a_download(self):
        root = Path(__file__).resolve().parent.parent
        with patch("duckdb.connect") as connect, patch("download.download") as download:
            for filename in ("inspect_manifest.py", "inspect_marts.py", "inspect_quality.py"):
                with self.subTest(filename=filename):
                    runpy.run_path(str(root / filename), run_name="inspection_import_check")
            connect.assert_not_called()
            download.assert_not_called()

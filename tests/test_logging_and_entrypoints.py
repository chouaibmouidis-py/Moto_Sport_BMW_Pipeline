"""Check operational logging and that CLI modules are safe to import."""
import io
import logging
from pathlib import Path
import runpy
import tempfile
import unittest
from unittest.mock import patch

from moto_sport_bmw_pipeline.logging_config import configure_logging, log_context


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

    def test_workflow_propagates_logging_options_to_stage_processes(self):
        from moto_sport_bmw_pipeline.orchestration import main

        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "config").mkdir()
            (root / "config" / "sources.json").write_text(
                '{"documents": []}', encoding="utf-8"
            )
            log_file = root / "logs" / "pipeline.log"
            with patch("moto_sport_bmw_pipeline.orchestration.PROJECT_DIR", root), patch(
                "moto_sport_bmw_pipeline.orchestration.subprocess.run"
            ) as run, patch("sys.stderr", io.StringIO()):
                main(["--verbose", "--log-file", str(log_file)])
            self.assertEqual(run.call_count, 5)
            for call in run.call_args_list:
                self.assertTrue(call.kwargs["check"])
                self.assertEqual(call.kwargs["env"]["BMW_LOG_LEVEL"], "DEBUG")
                self.assertEqual(call.kwargs["env"]["BMW_LOG_FILE"], str(log_file.resolve()))
            self.assertEqual(run.call_args_list[-1].args[0][-1], "--verbose")
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

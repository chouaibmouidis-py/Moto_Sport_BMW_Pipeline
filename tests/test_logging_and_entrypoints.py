"""Check operational logging and that CLI modules are safe to import."""

import io
import logging
import runpy
from pathlib import Path
from unittest.mock import patch

import pytest

from moto_sport_bmw_pipeline.logging_config import (
    RunContextFilter,
    configure_logging,
    log_context,
    log_operation,
)


def test_configuration_does_not_duplicate_logs_and_preserves_run_context(
    isolated_logger, tmp_path
):
    directory = tmp_path
    path = Path(directory) / "logs" / "pipeline.log"
    stream = io.StringIO()
    with (
        patch.dict("os.environ", {"BMW_LOG_LEVEL": "INFO", "BMW_LOG_FILE": ""}),
        patch("sys.stderr", stream),
    ):
        configure_logging(log_file=path)
        configure_logging(log_file=path)
        child = logging.getLogger("moto_sport_bmw_pipeline.test")
        with log_context("candidate-42"):
            child.info("Contrôle réussi")
        child.debug("Hidden debug details")
        for handler in isolated_logger.handlers:
            handler.flush()
        console = stream.getvalue()
        saved = path.read_text(encoding="utf-8")
        assert console.count("Contrôle réussi") == 1
        assert saved.count("Contrôle réussi") == 1
        assert "run=candidate-42" in saved
        assert "Hidden debug details" not in console


def test_verbose_mode_emits_debug_details(isolated_logger):
    stream = io.StringIO()
    with (
        patch.dict("os.environ", {"BMW_LOG_LEVEL": "INFO", "BMW_LOG_FILE": ""}),
        patch("sys.stderr", stream),
    ):
        configure_logging(verbose=True)
        logging.getLogger("moto_sport_bmw_pipeline.test").debug("Diagnostic details")
    assert "DEBUG" in stream.getvalue()
    assert "Diagnostic details" in stream.getvalue()


def test_nested_source_inherits_run_and_stage_then_restores_them(isolated_logger):
    stream = io.StringIO()
    with (
        patch.dict("os.environ", {"BMW_LOG_LEVEL": "INFO", "BMW_LOG_FILE": ""}),
        patch("sys.stderr", stream),
    ):
        configure_logging()
        child = logging.getLogger("moto_sport_bmw_pipeline.test")
        child.info("Before context")
        with log_context("run-42", stage="bronze"):
            with log_context(source_id="source-a"):
                child.info("Inside source")
            child.info("After source")
        child.info("After run")

    lines = stream.getvalue().splitlines()
    assert "run=- | stage=- | source_id=- | Before context" in lines[0]
    assert "run=run-42 | stage=bronze | source_id=source-a | Inside source" in lines[1]
    assert "run=run-42 | stage=bronze | source_id=- | After source" in lines[2]
    assert "run=- | stage=- | source_id=- | After run" in lines[3]


def test_exception_restores_context_and_is_propagated(isolated_logger):
    context_filter = RunContextFilter()
    with log_context("outer-run", stage="process", source_id="outer-source"):
        with pytest.raises(ValueError, match="test failure"):
            with log_context("inner-run", stage="gold", source_id="inner-source"):
                raise ValueError("test failure")
        record = logging.makeLogRecord({})
        context_filter.filter(record)
        assert (record.run_id, record.stage, record.source_id) == (
            "outer-run",
            "process",
            "outer-source",
        )

    record = logging.makeLogRecord({})
    context_filter.filter(record)
    assert (record.run_id, record.stage, record.source_id) == ("-", "-", "-")


def test_filter_preserves_explicit_fields_and_completes_missing_ones(isolated_logger):
    with log_context("run-42", stage="bronze", source_id="context-source"):
        record = logging.makeLogRecord({"source_id": "explicit-source"})
        assert RunContextFilter().filter(record)
    assert (record.run_id, record.stage, record.source_id) == (
        "run-42",
        "bronze",
        "explicit-source",
    )


def test_operation_success_has_context_and_no_duplicate_messages(isolated_logger):
    stream = io.StringIO()
    with (
        patch.dict("os.environ", {"BMW_LOG_LEVEL": "INFO", "BMW_LOG_FILE": ""}),
        patch("sys.stderr", stream),
    ):
        configure_logging()
        child = logging.getLogger("moto_sport_bmw_pipeline.test")
        with log_operation(
            child,
            "Normalize report",
            run_id="run-42",
            stage="silver",
            source_id="source-a",
        ):
            child.info("Rows validated")
    lines = stream.getvalue().splitlines()
    assert len(lines) == 3
    for line in lines:
        assert "run=run-42 | stage=silver | source_id=source-a" in line


def test_failed_operation_output_contains_context_and_propagates(isolated_logger):
    stream = io.StringIO()
    with (
        patch.dict("os.environ", {"BMW_LOG_LEVEL": "INFO", "BMW_LOG_FILE": ""}),
        patch("sys.stderr", stream),
    ):
        configure_logging()
        child = logging.getLogger("moto_sport_bmw_pipeline.test")
        with pytest.raises(ValueError, match="invalid input"):
            with log_operation(
                child,
                "Normalize report",
                run_id="run-42",
                stage="silver",
                source_id="source-a",
            ):
                raise ValueError("invalid input")
        child.info("After failure")
    output = stream.getvalue()
    assert (
        "run=run-42 | stage=silver | source_id=source-a | Failed: Normalize report"
        in output
    )
    assert "Completed: Normalize report" not in output
    assert "run=- | stage=- | source_id=- | After failure" in output


def test_workflow_propagates_logging_options_to_common_stages(
    isolated_logger, tmp_path
):
    from moto_sport_bmw_pipeline.orchestration import main

    directory = tmp_path
    root = Path(directory)
    (root / "config").mkdir()
    (root / "config" / "sources.json").write_text('{"documents": []}', encoding="utf-8")
    log_file = root / "logs" / "pipeline.log"
    with (
        patch("moto_sport_bmw_pipeline.orchestration.PROJECT_DIR", root),
        patch("moto_sport_bmw_pipeline.orchestration.run_stages") as run,
        patch(
            "moto_sport_bmw_pipeline.orchestration.select_documents",
            return_value=[{"source_id": "test"}],
        ),
        patch("sys.stderr", io.StringIO()),
    ):
        main(["--verbose", "--log-file", str(log_file)])
    run.assert_called_once_with(
        root, [{"source_id": "test"}], stage="all", refresh=False, verbose=True
    )
    assert log_file.is_file()


def test_package_command_exposes_pipeline_help():
    from moto_sport_bmw_pipeline import main

    with (
        patch("sys.argv", ["moto-sport-bmw-pipeline", "--help"]),
        patch("sys.stdout", io.StringIO()) as output,
    ):
        with pytest.raises(SystemExit) as error:
            main()
    assert error.value.code == 0
    assert "--log-file" in output.getvalue()


def test_import_does_not_read_data_or_start_a_download(subtests):
    root = Path(__file__).resolve().parent.parent
    with patch("duckdb.connect") as connect, patch("download.download") as download:
        for filename in (
            "inspect_manifest.py",
            "inspect_marts.py",
            "inspect_quality.py",
        ):
            with subtests.test(filename=filename):
                runpy.run_path(str(root / filename), run_name="inspection_import_check")
        connect.assert_not_called()
        download.assert_not_called()


@pytest.fixture
def isolated_logger():
    logger = logging.getLogger("moto_sport_bmw_pipeline")
    old_handlers = list(logger.handlers)
    old_level = logger.level
    old_propagate = logger.propagate
    logger.handlers.clear()
    try:
        yield logger
    finally:
        for handler in logger.handlers:
            handler.close()
        logger.handlers[:] = old_handlers
        logger.setLevel(old_level)
        logger.propagate = old_propagate

"""Configure application logs at CLI entry points; imports do not add handlers."""

from contextlib import contextmanager
from contextvars import ContextVar
from pathlib import Path
import logging
import os
import time


_RUN_ID = ContextVar("bmw_run_id", default="-")
_STAGE = ContextVar("bmw_stage", default="-")
_SOURCE_ID = ContextVar("bmw_source_id", default="-")
LOGGER_NAME = "moto_sport_bmw_pipeline"


class RunContextFilter(logging.Filter):
    """Attach missing run, stage and source fields to each log record."""

    def filter(self, record):
        if not hasattr(record, "run_id"):
            record.run_id = _RUN_ID.get()
        if not hasattr(record, "stage"):
            record.stage = _STAGE.get()
        if not hasattr(record, "source_id"):
            record.source_id = _SOURCE_ID.get()
        return True


def configure_logging(*, verbose=False, log_file=None):
    """Install one console handler and an optional UTF-8 file handler."""
    logger = logging.getLogger(LOGGER_NAME)
    for handler in list(logger.handlers):
        if getattr(handler, "_bmw_owned", False):
            logger.removeHandler(handler)
            handler.close()
    level = logging.DEBUG if verbose else logging.INFO
    if os.environ.get("BMW_LOG_LEVEL") == "DEBUG":
        level = logging.DEBUG
    logger.setLevel(level)
    logger.propagate = False
    formatter = logging.Formatter(
        "%(asctime)s | %(levelname)s | %(name)s | "
        "run=%(run_id)s | stage=%(stage)s | source_id=%(source_id)s | %(message)s",
        datefmt="%Y-%m-%dT%H:%M:%SZ",
    )
    formatter.converter = time.gmtime
    handlers = [logging.StreamHandler()]
    destination = log_file or os.environ.get("BMW_LOG_FILE")
    if destination:
        path = Path(destination).expanduser().resolve()
        path.parent.mkdir(parents=True, exist_ok=True)
        handlers.append(logging.FileHandler(path, encoding="utf-8"))
    for handler in handlers:
        handler._bmw_owned = True
        handler.addFilter(RunContextFilter())
        handler.setFormatter(formatter)
        logger.addHandler(handler)


@contextmanager
def log_context(run_id=None, *, stage=None, source_id=None):
    """Set supplied fields, inherit omitted fields, then restore previous values."""
    tokens = []
    try:
        for variable, value in (
            (_RUN_ID, run_id),
            (_STAGE, stage),
            (_SOURCE_ID, source_id),
        ):
            if value is not None:
                token = variable.set(value)
                tokens.append((variable, token))
        yield
    finally:
        for variable, token in reversed(tokens):
            variable.reset(token)


@contextmanager
def log_operation(logger, message, *, run_id=None, stage=None, source_id=None):
    """Log operation boundaries before restoring their diagnostic context."""
    with log_context(run_id, stage=stage, source_id=source_id):
        logger.info("Started: %s", message)
        try:
            yield
        except Exception:
            logger.exception("Failed: %s", message)
            raise
        else:
            logger.info("Completed: %s", message)

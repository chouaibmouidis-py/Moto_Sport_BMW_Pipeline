"""Configure application logs at CLI entry points; imports do not add handlers."""

from contextlib import contextmanager
from contextvars import ContextVar
from pathlib import Path
import logging
import os
import time


_RUN_ID = ContextVar("bmw_run_id", default="-")
LOGGER_NAME = "moto_sport_bmw_pipeline"


class RunContextFilter(logging.Filter):
    """Attach the candidate run identifier to records from helper modules."""

    def filter(self, record):
        if not hasattr(record, "run_id"):
            record.run_id = _RUN_ID.get()
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
        "%(asctime)s | %(levelname)s | %(name)s | run=%(run_id)s | %(message)s",
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
def log_context(run_id):
    """Propagate a run ID during one candidate build, then restore the caller."""
    token = _RUN_ID.set(run_id)
    try:
        yield
    finally:
        _RUN_ID.reset(token)

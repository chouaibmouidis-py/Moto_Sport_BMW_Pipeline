"""Coordinate acquisition, extraction, processing and Gold for all source formats."""

import argparse
import json
import logging
import uuid
from pathlib import Path

from .bronze import build_source
from .gold import build_gold_candidate
from .logging_config import configure_logging, log_operation
from .manifest import select_documents
from .paths import PROJECT_DIR
from .pipeline import build_processing_run
from .raw_download import prepare_source

logger = logging.getLogger(__name__)


def run_stages(project_directory, documents, *, stage="all", refresh=False, verbose=False,
               extension_directory: Path | None = None):
    """Use one sequence for JSON, CSV and PDF; exceptions stop execution."""
    with log_operation(
        logger, "Execute selected pipeline stages",
        run_id=uuid.uuid4().hex, stage="orchestration", source_id="-",
    ):
        if stage in ("raw", "all"):
            for source in documents:
                prepare_source(project_directory, source, refresh=refresh)
        if stage in ("bronze", "all"):
            for source in documents:
                prepare_source(project_directory, source)
            for source in documents:
                if extension_directory is None:
                    build_source(project_directory, source)
                else:
                    build_source(project_directory, source, extension_directory=extension_directory)
        if stage in ("process", "all"):
            options = {} if extension_directory is None else {"extension_directory": extension_directory}
            build_processing_run(project_directory, documents, verbose=verbose, **options)
        if stage in ("gold", "all"):
            return build_gold_candidate(project_directory, expected_source_ids=[source["source_id"] for source in documents])


def main(argv=(), *, project_directory=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--stage", choices=("raw", "bronze", "process", "gold", "all"), default="all")
    parser.add_argument("--season", type=int)
    parser.add_argument("--event")
    parser.add_argument("--refresh", action="store_true")
    parser.add_argument("--verbose", action="store_true")
    parser.add_argument("--log-file", type=Path)
    parser.add_argument("--extension-directory", type=Path,
                        help="Directory containing installed DuckDB extensions (no automatic installation)")
    args = parser.parse_args(argv)
    configure_logging(verbose=args.verbose, log_file=args.log_file)
    project_directory = project_directory or PROJECT_DIR
    manifest = json.loads((project_directory / "config/sources.json").read_text(encoding="utf-8"))
    documents = select_documents(manifest, season=args.season, event_id=args.event)
    logger.info("Selected %s reports", len(documents))
    options = {} if args.extension_directory is None else {"extension_directory": args.extension_directory}
    return run_stages(project_directory, documents, stage=args.stage, refresh=args.refresh, verbose=args.verbose, **options)

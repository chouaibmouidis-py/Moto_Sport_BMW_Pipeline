"""Coordinate the JSON Bronze-to-Silver candidate run and activate only after publication."""

from pathlib import Path
import json
import logging
import uuid

import duckdb

from .diagnostics import show_pipeline_tables
from .duration_quality import build_duration_reports
from .logging_config import log_context
from .marts import build_classification_marts, build_enriched_stops
from .publication import OUTPUT_VIEWS, publish_run_outputs
from .quality import build_session_quality, build_source_pairs
from .run_reference import activate_run
from .silver import (
    transform_car_entries, transform_classification, transform_driver_entries,
    transform_pit_stops, transform_sessions,
)
from .source_loading import (
    load_classification_sources, load_pit_stop_bronze, load_source_sessions,
    select_pit_stop_sources,
    select_classification_sources,
)

logger = logging.getLogger(__name__)


def build_candidate_run(project_directory: Path, *, verbose=False) -> Path:
    """Build all candidate outputs, then update current.json after success."""
    manifest_path = project_directory / "config" / "sources.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    pit_sources = select_pit_stop_sources(manifest["documents"])
    classification_sources = select_classification_sources(manifest["documents"])
    if not classification_sources:
        raise ValueError("Expected at least one enabled classification source")

    run_id = uuid.uuid4().hex
    run_directory = project_directory / "data" / "runs" / run_id
    with log_context(run_id):
        logger.info("Candidate run started; pit-stop sources: %s", len(pit_sources))
        try:
            with duckdb.connect() as connection:
                load_source_sessions(connection, manifest["documents"])
                build_source_pairs(connection, project_directory)
                connection.execute(
                    (project_directory / "sql" / "21_create_duration_parser.sql")
                    .read_text(encoding="utf-8")
                )
                load_pit_stop_bronze(connection, pit_sources, project_directory)
                logger.info("Bronze documents loaded: %s", len(pit_sources))

                logger.info("Building and checking Silver tables")
                transform_sessions(connection, project_directory)
                drivers = transform_driver_entries(connection, project_directory)
                cars = transform_car_entries(connection, project_directory)
                transform_pit_stops(connection, project_directory)
                logger.info("Silver driver entries: %s", drivers.count("*").fetchone()[0])
                logger.info("Silver car entries: %s", cars.count("*").fetchone()[0])

                build_session_quality(connection, project_directory)
                build_duration_reports(connection, project_directory, verbose=verbose)
                build_enriched_stops(connection, project_directory)
                load_classification_sources(connection, classification_sources, project_directory)
                transform_classification(connection, project_directory)
                build_classification_marts(connection, project_directory)
                if verbose:
                    show_pipeline_tables(connection)

                logger.info("Publishing %s candidate outputs", len(OUTPUT_VIEWS))
                publish_run_outputs(
                    connection, run_directory, OUTPUT_VIEWS, verbose=verbose,
                )

            current_path = activate_run(run_directory)
            logger.info("Activated run: %s; reference: %s", run_id, current_path)
        except Exception:
            logger.exception("Candidate run failed; previous current reference retained")
            raise
    return run_directory

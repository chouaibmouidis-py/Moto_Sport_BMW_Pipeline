"""Coordinate the JSON Bronze-to-Silver candidate run and activate only after publication."""

import json
import logging
import uuid
from pathlib import Path

import duckdb

from .bronze import bronze_document_path
from .diagnostics import show_pipeline_tables
from .duration_quality import build_duration_reports
from .integrity import sha256_file
from .logging_config import log_context, log_operation
from .marts import (
    build_classification_marts,
    build_csv_pdf_race_summary,
    build_enriched_stops,
)
from .parquet_writer import publish_parquet
from .publication import OUTPUT_VIEWS, publish_run_outputs
from .quality import (
    build_classification_gap_issues,
    build_session_quality,
    build_source_pairs,
)
from .run_reference import activate_run
from .silver import (
    transform_car_entries,
    transform_classification,
    transform_classification_csv,
    transform_driver_entries,
    transform_pdf_pit_stops,
    transform_pit_stops,
    transform_sessions,
)
from .source_loading import (
    load_classification_csv_bronze,
    load_classification_sources,
    load_csv_pdf_source_sessions,
    load_pdf_pit_stop_bronze,
    load_pit_stop_bronze,
    load_source_sessions,
    select_classification_sources,
    select_pit_stop_sources,
)

logger = logging.getLogger(__name__)


def build_candidate_run(project_directory: Path, *, verbose=False, documents=None, activate=True,
                        extension_directory: Path | None = None) -> Path:
    """Build all candidate outputs, then update current.json after success."""
    manifest_path = project_directory / "config" / "sources.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8")) if documents is None else {"documents": documents}
    manifest["documents"] = [source for source in manifest["documents"] if source.get("format", "json") == "json"]
    pit_sources = select_pit_stop_sources(manifest["documents"])
    classification_sources = select_classification_sources(manifest["documents"])
    if not classification_sources:
        raise ValueError("Expected at least one enabled classification source")

    run_id = uuid.uuid4().hex
    run_directory = project_directory / "data" / "runs" / run_id
    with log_context(run_id, stage="process", source_id="-"):
        logger.info("Candidate run started; pit-stop sources: %s", len(pit_sources))
        try:
            config = {} if extension_directory is None else {"extension_directory": str(extension_directory)}
            with duckdb.connect(config=config) as connection:
                load_source_sessions(connection, manifest["documents"])
                build_source_pairs(connection, project_directory)
                connection.execute(
                    (project_directory / "sql" / "21_create_duration_parser.sql")
                    .read_text(encoding="utf-8")
                )
                load_pit_stop_bronze(connection, pit_sources, project_directory)
                logger.info("Bronze documents loaded: %s", len(pit_sources))

                logger.info("Building and checking Silver tables")
                with log_operation(logger, "Normalize JSON sessions, drivers, cars and stops", stage="silver"):
                    transform_sessions(connection, project_directory)
                    drivers = transform_driver_entries(connection, project_directory)
                    cars = transform_car_entries(connection, project_directory)
                    transform_pit_stops(connection, project_directory)
                    logger.info("Silver driver entries: %s", drivers.count("*").fetchone()[0])
                    logger.info("Silver car entries: %s", cars.count("*").fetchone()[0])

                with log_operation(logger, "Build JSON quality reports and enriched stops", stage="quality"):
                    build_session_quality(connection, project_directory)
                    build_duration_reports(connection, project_directory, verbose=verbose)
                    build_enriched_stops(connection, project_directory)
                load_classification_sources(
                    connection,
                    classification_sources,
                    project_directory,
                )
                with log_operation(logger, "Normalize JSON classifications", stage="silver"):
                    transform_classification(connection, project_directory)
                with log_operation(logger, "Build JSON participant marts", stage="marts"):
                    build_classification_marts(connection, project_directory)
                if verbose:
                    show_pipeline_tables(connection)

                logger.info("Publishing %s candidate outputs", len(OUTPUT_VIEWS))
                publish_run_outputs(
                    connection, run_directory, OUTPUT_VIEWS, verbose=verbose,
                )

            if activate:
                current_path = activate_run(run_directory)
                logger.info("Activated run: %s; reference: %s", run_id, current_path)
        except Exception:
            logger.exception("Candidate run failed; previous current reference retained")
            raise
    return run_directory

def publish_classification_csv_from_bronze(
    project_directory: Path,
    bronze_path: Path,
    source_id: str,
    output_path: Path,
    *,
    quality_output_path: Path | None = None,
    extension_directory: Path | None = None,
) -> Path:
    """Load, validate, transform and publish one classification CSV Bronze."""
    with log_operation(logger, "Normalize classification CSV and write its quality report",
                       stage="silver", source_id=source_id):
        config = {} if extension_directory is None else {"extension_directory": str(extension_directory)}
        with duckdb.connect(config=config) as connection:
            load_classification_csv_bronze(
                connection,
                bronze_path,
                source_id,
            )

            classification = transform_classification_csv(
                connection,
                project_directory,
            )

            gap_issues = build_classification_gap_issues(connection)

            publish_parquet(
                connection,
                classification,
                output_path,
            )

            if quality_output_path is not None:
                publish_parquet(connection, gap_issues, quality_output_path)

        return output_path


def publish_pdf_pit_stops_from_bronze(
    project_directory: Path,
    bronze_path: Path,
    output_path: Path,
    *,
    extension_directory: Path | None = None,
) -> Path:
    """Load, validate, transform and publish one PDF pit stop Bronze."""
    with log_operation(logger, "Normalize PDF pit stops",
                       stage="silver", source_id=bronze_path.parent.name):
        config = {} if extension_directory is None else {"extension_directory": str(extension_directory)}
        with duckdb.connect(config=config) as connection:
            load_pdf_pit_stop_bronze(
                connection,
                bronze_path,
            )

            stops = transform_pdf_pit_stops(
                connection,
                project_directory,
            )

            publish_parquet(
                connection,
                stops,
                output_path,
            )

        return output_path


def publish_csv_pdf_race_summary(
    project_directory: Path,
    catalog: dict,
    classification_silver_path: Path,
    pit_stops_silver_path: Path,
    output_path: Path,
) -> Path:
    """Pair loaded Silver CSV and PDF relations, validate consistency and publish Mart."""
    with log_operation(
        logger, "Build CSV/PDF participant mart", stage="marts",
        source_id=Path(catalog["events"][0]["classification_path"]).parent.name,
    ):
        with duckdb.connect() as connection:
            load_csv_pdf_source_sessions(connection, catalog)

            classification = connection.read_parquet(str(classification_silver_path))
            classification.create_view("silver_classification_csv")

            stops = connection.read_parquet(str(pit_stops_silver_path))
            stops.create_view("silver_pdf_pit_stops")

            summary = build_csv_pdf_race_summary(connection, project_directory)

            publish_parquet(
                connection,
                summary,
                output_path,
            )

        return output_path


def build_processing_run(project_directory: Path, documents: list[dict], *, verbose=False,
                         extension_directory: Path | None = None) -> Path:
    """Activate processing only after all selected report outputs are complete."""
    from .manifest import pair_reports

    pairs = pair_reports(documents)
    run = project_directory / "data/processing/runs" / uuid.uuid4().hex
    run.mkdir(parents=True)
    with log_operation(logger, "Build complete processing run",
                       run_id=run.name, stage="process", source_id="-"):
        hashes = {}
        for source in documents:
            path = bronze_document_path(project_directory, source)
            with log_operation(logger, "Fingerprint Bronze input",
                               stage="verify_inputs", source_id=source["source_id"]):
                hashes[path.relative_to(project_directory).as_posix()] = sha256_file(path)
        json_documents = [source for source in documents if source["format"] == "json"]
        outputs = []
        if json_documents:
            options = {} if extension_directory is None else {"extension_directory": extension_directory}
            json_run = build_candidate_run(project_directory, documents=json_documents, activate=False, verbose=verbose, **options)
            logger.info("JSON adapter run linked to processing run: json_run=%s", json_run.name)
            outputs.extend(
                [{"role": "json_participant_mart", "path": (json_run / "marts/race_car_summary.parquet").relative_to(project_directory).as_posix()},
                {"role": "json_silver_classification", "path": (json_run / "silver/classification.parquet").relative_to(project_directory).as_posix()},
                {"role": "json_silver_car_entries", "path": (json_run / "silver/car_entries.parquet").relative_to(project_directory).as_posix()}]
                )
        for pair in pairs:
            classification, stops = pair["classification"], pair["pit_stops"]
            if classification["format"] == "json":
                continue
            source_id = classification["source_id"]
            directory = run / "reports" / source_id
            classification_path = directory / "silver/classification.parquet"
            stops_path = directory / "silver/pit_stops.parquet"
            publish_classification_csv_from_bronze(
                project_directory,
                bronze_document_path(project_directory, classification),
                source_id, classification_path,
                quality_output_path=directory / "quality/classification_gap_issues.parquet",
                **({} if extension_directory is None else {"extension_directory": extension_directory}),
            )
            outputs.append({"role": "classification_quality_report", "path": (directory / "quality/classification_gap_issues.parquet").relative_to(project_directory).as_posix()})
            publish_pdf_pit_stops_from_bronze(
                project_directory,
                bronze_document_path(project_directory, stops),
                stops_path,
                **({} if extension_directory is None else {"extension_directory": extension_directory}),
            )
            event = {
                "event_id": classification["event_id"], "session_id": classification["session_id"],
                "classification_path": f"data/raw/{source_id}/{classification['filename']}",
                "pdf_path": f"data/raw/{stops['source_id']}/{stops['filename']}",
            }
            catalog = {"championship": classification["championship"], "season": classification["season"], "events": [event]}
            mart_path = directory / "marts/race_car_summary.parquet"
            publish_csv_pdf_race_summary(project_directory, catalog, classification_path, stops_path, mart_path)
            outputs.append({"role": "csv_pdf_participant_mart", "path": mart_path.relative_to(project_directory).as_posix()})
        for relative, expected in hashes.items():
            if sha256_file(project_directory / relative) != expected:
                raise ValueError(f"Processing rejected: Bronze input changed: {relative}")
        for output in outputs:
            path = project_directory / output["path"]
            output["sha256"] = sha256_file(path)
        (run / "sources.json").write_text(json.dumps({"documents": documents}, indent=2), encoding="utf-8")
        (run / "outputs.json").write_text(json.dumps({"outputs": outputs, "bronze_hashes": hashes}, indent=2), encoding="utf-8")
        activate_run(run, required_outputs=("sources.json", "outputs.json"))
        return run

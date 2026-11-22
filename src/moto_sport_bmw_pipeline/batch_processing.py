"""Build CSV/PDF batches for configured races, independently of season."""

from pathlib import Path
import logging
import duckdb
from .bronze import build_classification_csv, build_pdf_pit_stop_bronze
from .pipeline import (
    publish_classification_csv_from_bronze, publish_pdf_pit_stops_from_bronze,
    publish_csv_pdf_race_summary,
)

logger = logging.getLogger(__name__)


def build_classification_batch(project_directory: Path, catalog: dict) -> list[dict]:
    """Build per-event classification Bronze/Silver without activating a main run.

    Source IDs follow the existing Raw directory names. Each output remains
    independent: this batch does not provide atomic season activation.
    """
    inputs = []
    for event in catalog["events"]:
        source_path = project_directory / event["classification_path"]
        if not source_path.is_file():
            raise FileNotFoundError(
                f"Exploration rejected: source file not found: {source_path}"
            )
        inputs.append((event, source_path))

    source_ids = [path.parent.name for _, path in inputs]
    if len(source_ids) != len(set(source_ids)):
        raise ValueError("Classification batch rejected: duplicate source IDs")
    event_ids = [event["event_id"] for event, _ in inputs]
    if len(event_ids) != len(set(event_ids)):
        raise ValueError("Classification batch rejected: duplicate event IDs")

    results = []
    for event, source_path in inputs:
        source_id = source_path.parent.name
        bronze_path = (
            project_directory / "data" / "bronze" / source_id / "document.parquet"
        )
        output_path = (
            project_directory / "data" / "csv_pdf"
            / f"{event['event_id']}-{catalog['season']}"
            / "silver" / "classification.parquet"
        )
        build_classification_csv(source_path, bronze_path)
        publish_classification_csv_from_bronze(
            project_directory, bronze_path, source_id, output_path,
        )
        with duckdb.connect() as connection:
            saved = connection.read_parquet(str(output_path))
            result = {
                "event_id": event["event_id"],
                "participants": saved.count("*").fetchone()[0],
                "bmw_participants": saved.filter(
                    "car_model LIKE 'BMW%'"
                ).count("*").fetchone()[0],
                "missing_positions": saved.filter(
                    "overall_position IS NULL"
                ).count("*").fetchone()[0],
            }
        results.append(result)
        logger.info("Classification batch result: %s", result)
    return results

def build_pdf_bronze_batch(project_directory: Path, catalog: dict) -> list[dict]:
    """Build per-event pit-stop PDF Bronze Parquet without activating a main run.

    Pre-checks all source files first. Preserves raw extracted fields and provenance.
    """
    inputs = []
    for event in catalog["events"]:
        source_path = project_directory / event["pdf_path"]
        if not source_path.is_file():
            raise FileNotFoundError(
                f"Exploration rejected: source file not found: {source_path}"
            )
        inputs.append((event, source_path))

    source_ids = [path.parent.name for _, path in inputs]
    if len(source_ids) != len(set(source_ids)):
        raise ValueError("PDF Bronze batch rejected: duplicate source IDs")
    event_ids = [event["event_id"] for event, _ in inputs]
    if len(event_ids) != len(set(event_ids)):
        raise ValueError("PDF Bronze batch rejected: duplicate event IDs")

    results = []
    for event, source_path in inputs:
        source_id = source_path.parent.name
        bronze_path = (
            project_directory / "data" / "bronze" / source_id / "document.parquet"
        )
        build_pdf_pit_stop_bronze(source_path, bronze_path, source_id)

        with duckdb.connect() as connection:
            saved = connection.read_parquet(str(bronze_path))
            result = {
                "event_id": event["event_id"],
                "source_id": source_id,
                "stops": saved.count("*").fetchone()[0],
            }
        results.append(result)
        logger.info("PDF Bronze batch result: %s", result)
    return results

def build_pdf_silver_batch(project_directory: Path, catalog: dict) -> list[dict]:
    """Publish each event's PDF Silver from prechecked local Bronze files."""
    inputs = []
    for event in catalog["events"]:
        source_id = Path(event["pdf_path"]).parent.name
        bronze_path = project_directory / "data" / "bronze" / source_id / "document.parquet"
        if not bronze_path.is_file():
            raise FileNotFoundError(
                f"PDF Silver batch rejected: Bronze file not found: {bronze_path}"
            )
        inputs.append((event, source_id, bronze_path))

    source_ids = [source_id for _, source_id, _ in inputs]
    if len(source_ids) != len(set(source_ids)):
        raise ValueError("PDF Silver batch rejected: duplicate source IDs")
    event_ids = [event["event_id"] for event, _, _ in inputs]
    if len(event_ids) != len(set(event_ids)):
        raise ValueError("PDF Silver batch rejected: duplicate event IDs")

    results = []
    for event, source_id, bronze_path in inputs:
        output_path = (
            project_directory / "data" / "csv_pdf"
            / f"{event['event_id']}-{catalog['season']}"
            / "silver" / "pit_stops.parquet"
        )
        publish_pdf_pit_stops_from_bronze(project_directory, bronze_path, output_path)

        with duckdb.connect() as connection:
            saved = connection.read_parquet(str(output_path))
            result = {
                "event_id": event["event_id"],
                "source_id": source_id,
                "stops": saved.count("*").fetchone()[0],
                "invalid_duration": saved.filter(
                    "pit_time_in_seconds IS NULL"
                ).count("*").fetchone()[0]
            }
        results.append(result)
        logger.info("PDF Silver batch result: %s", result)
    return results

def build_mart_batch(project_directory: Path, catalog: dict) -> list[dict]:
    """Publish isolated per-event marts from existing CSV and PDF Silver files.

    All paths and catalog identifiers are checked first. Publication is per
    file, not an atomic season activation; current.json is never updated.
    """
    events = catalog["events"]
    event_ids = [event["event_id"] for event in events]
    if len(event_ids) != len(set(event_ids)):
        raise ValueError("Mart batch rejected: duplicate event IDs")
    source_ids = [
        Path(event[field]).parent.name
        for event in events
        for field in ("classification_path", "pdf_path")
    ]
    if len(source_ids) != len(set(source_ids)):
        raise ValueError("Mart batch rejected: duplicate source IDs")

    inputs = []
    for event in events:
        directory = (
            project_directory / "data" / "csv_pdf"
            / f"{event['event_id']}-{catalog['season']}"
        )
        classification_path = directory / "silver" / "classification.parquet"
        stops_path = directory / "silver" / "pit_stops.parquet"
        for path in (classification_path, stops_path):
            if not path.is_file():
                raise FileNotFoundError(f"Mart batch rejected: Silver file not found: {path}")
        inputs.append((event, directory, classification_path, stops_path))

    results = []
    for event, directory, classification_path, stops_path in inputs:
        # Limit context to this event: misplaced files cannot acquire another
        # event's session metadata merely because it exists in the full catalog.
        event_catalog = {**catalog, "events": [event]}
        output_path = directory / "marts" / "race_car_summary.parquet"
        publish_csv_pdf_race_summary(
            project_directory, event_catalog, classification_path,
            stops_path, output_path,
        )
        with duckdb.connect() as connection:
            saved = connection.read_parquet(str(output_path))
            result = {
                "event_id": event["event_id"],
                "participants": saved.count("*").fetchone()[0],
                "bmw_participants": saved.filter(
                    "car_model LIKE 'BMW%'"
                ).count("*").fetchone()[0],
                "observed_stops": saved.aggregate(
                    "SUM(observed_pit_stop_count)"
                ).fetchone()[0] or 0,
                "bmw_stops": saved.filter("car_model LIKE 'BMW%'").aggregate(
                    "SUM(observed_pit_stop_count)"
                ).fetchone()[0] or 0,
                "participants_without_stop_details": saved.filter(
                    "observed_pit_stop_count IS NULL"
                ).count("*").fetchone()[0],
            }
        results.append(result)
        logger.info("Mart batch result: %s", result)
    return results

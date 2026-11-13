"""Build exploratory PDF/CSV summaries or classification Bronze/Silver for 2023.

Sources must already be present locally. No main pipeline run is activated.
"""

from pathlib import Path
import argparse
import json
import logging
from moto_sport_bmw_pipeline.bronze import build_pdf_pit_stop_bronze
import duckdb

from build_classification_bronze import build_classification_csv
from moto_sport_bmw_pipeline.exploration import explore_source_pair
from moto_sport_bmw_pipeline.logging_config import configure_logging
from moto_sport_bmw_pipeline.pipeline import (
    publish_classification_csv_from_bronze,
    publish_pdf_pit_stops_from_bronze,
    publish_csv_pdf_race_summary,
)

logger = logging.getLogger("moto_sport_bmw_pipeline.explore_2023_season")


def build_classification_batch(project_directory: Path, catalog: dict) -> list[dict]:
    """Build per-event classification Bronze/Silver without activating a main run.

    Source IDs follow the existing Raw directory names. Each output remains
    independent: this exploratory batch does not provide atomic season activation.
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
            project_directory / "data" / "exploration"
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
            project_directory / "data" / "exploration"
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
            project_directory / "data" / "exploration"
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


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--verbose", action="store_true", help="Display tables and DEBUG logs.")
    parser.add_argument("--log-file", help="Append UTF-8 operational logs to this file.")
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument(
        "--classification-only", action="store_true",
        help="Build CSV classification Bronze/Silver without reading pit-stop PDFs.",
    )
    mode.add_argument(
        "--pdf-bronze-only", action="store_true",
        help="Build pit-stop PDF Bronze Parquet without Silver or Mart generation.",
    )

    mode.add_argument(
        "--pdf-silver-only", action="store_true",
        help="Build pit-stop PDF Silver Parquet from existing Bronze without Mart generation.",
    )
    mode.add_argument(
        "--mart-only", action="store_true",
        help="Build per-event CSV/PDF marts from existing Silver files.",
    )
    args = parser.parse_args()
    configure_logging(verbose=args.verbose, log_file=args.log_file)
    project_directory = Path(__file__).resolve().parent
    catalog_path = project_directory / "config" / "exploration_2023.json"
    catalog = json.loads(catalog_path.read_text(encoding="utf-8"))
    events = catalog["events"]
    event_ids = [event["event_id"] for event in events]
    if len(event_ids) != len(set(event_ids)):
        raise ValueError("Exploration rejected: duplicate event IDs")

    if args.mart_only:
        results = build_mart_batch(project_directory, catalog)
        fields = (
            "participants", "bmw_participants", "observed_stops", "bmw_stops",
            "participants_without_stop_details",
        )
        logger.info("Mart season totals: %s", {
            field: sum(result[field] for result in results) for field in fields
        })
        logger.info("Main pipeline current.json is unchanged.")
        return

    if args.classification_only:
        results = build_classification_batch(project_directory, catalog)
        totals = {
            field: sum(result[field] for result in results)
            for field in ("participants", "bmw_participants", "missing_positions")
        }
        logger.info("Classification season totals: %s", totals)
        logger.info("Main pipeline current.json is unchanged.")
        return

    if args.pdf_bronze_only:
        results = build_pdf_bronze_batch(project_directory, catalog)
        total_stops = sum(r["stops"] for r in results)
        logger.info("PDF Bronze season total stops: %s across %s events", total_stops, len(results))
        logger.info("Main pipeline current.json is unchanged.")
        return

    if args.pdf_silver_only:
        results = build_pdf_silver_batch(project_directory, catalog)
        total_stops = sum(r["stops"] for r in results)
        total_invalid = sum(r["invalid_duration"] for r in results)
        logger.info(
            "PDF Silver season totals: %s stops, %s invalid durations across %s events",
            total_stops, total_invalid, len(results),
        )
        logger.info("Main pipeline current.json is unchanged.")
        return

    # Check the complete local batch before beginning any extraction.
    for event in events:
        for field in ("pdf_path", "classification_path"):
            path = project_directory / event[field]
            if not path.is_file():
                raise FileNotFoundError(f"Exploration rejected: source file not found: {path}")

    results = []
    for event in events:
        context = {
            "championship": catalog["championship"],
            "season": catalog["season"],
            "event_id": event["event_id"],
            "session_id": event["session_id"],
        }
        output_path = (
            project_directory / "data" / "exploration"
            / f"{event['event_id']}-{catalog['season']}" / "car_summary.parquet"
        )
        result = explore_source_pair(
            project_directory / event["pdf_path"],
            project_directory / event["classification_path"],
            context,
            output_path,
            show_tables=args.verbose,
        )
        results.append(result)
        logger.info('%s', f"{result['event_id']}: {result['participants']} entries, {result['stops']} stops")

    totals = {
        field: sum(result[field] for result in results)
        for field in ("participants", "bmw_participants", "stops", "bmw_stops")
    }
    logger.info('%s %s', "Exploratory season totals:", totals)
    logger.info('%s', "Main pipeline current.json is unchanged.")


if __name__ == "__main__":
    main()

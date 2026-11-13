"""Build exploratory PDF/CSV summaries or classification Bronze/Silver for 2023.

Sources must already be present locally. No main pipeline run is activated.
"""

from pathlib import Path
import argparse
import json
import logging

import duckdb

from build_classification_bronze import build_classification_csv
from moto_sport_bmw_pipeline.exploration import explore_source_pair
from moto_sport_bmw_pipeline.logging_config import configure_logging
from moto_sport_bmw_pipeline.pipeline import publish_classification_csv_from_bronze

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


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--verbose", action="store_true", help="Display tables and DEBUG logs.")
    parser.add_argument("--log-file", help="Append UTF-8 operational logs to this file.")
    parser.add_argument(
        "--classification-only", action="store_true",
        help="Build CSV classification Bronze/Silver without reading pit-stop PDFs.",
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

    if args.classification_only:
        results = build_classification_batch(project_directory, catalog)
        totals = {
            field: sum(result[field] for result in results)
            for field in ("participants", "bmw_participants", "missing_positions")
        }
        logger.info("Classification season totals: %s", totals)
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

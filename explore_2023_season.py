"""Build separate exploratory summaries for the eleven configured 2023 races.

Sources must already be present locally. No main pipeline run is activated.
"""

from pathlib import Path
import argparse
import json
import logging

from moto_sport_bmw_pipeline.exploration import explore_source_pair
from moto_sport_bmw_pipeline.logging_config import configure_logging

logger = logging.getLogger("moto_sport_bmw_pipeline.explore_2023_season")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--verbose", action="store_true", help="Display tables and DEBUG logs.")
    parser.add_argument("--log-file", help="Append UTF-8 operational logs to this file.")
    args = parser.parse_args()
    configure_logging(verbose=args.verbose, log_file=args.log_file)
    project_directory = Path(__file__).resolve().parent
    catalog_path = project_directory / "config" / "exploration_2023.json"
    catalog = json.loads(catalog_path.read_text(encoding="utf-8"))
    events = catalog["events"]
    event_ids = [event["event_id"] for event in events]
    if len(event_ids) != len(set(event_ids)):
        raise ValueError("Exploration rejected: duplicate event IDs")

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

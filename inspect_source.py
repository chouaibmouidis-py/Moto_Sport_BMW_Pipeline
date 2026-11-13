"""Inspect a local pit-stop JSON document without publishing derived data."""

from pathlib import Path
import argparse
import json
import logging

from download import RAW_DIR, SOURCE_FILENAME
from moto_sport_bmw_pipeline.logging_config import configure_logging

logger = logging.getLogger("moto_sport_bmw_pipeline.inspect_source")


def main() -> None:
    configure_logging()
    parser = argparse.ArgumentParser(description="Inspect a locally downloaded IMSA source.")
    parser.add_argument("path", nargs="?", type=Path, default=Path(RAW_DIR) / SOURCE_FILENAME)
    args = parser.parse_args()

    with args.path.open("r", encoding="utf-8-sig") as file:
        data = json.load(file)

    cars = data["pit_stop_analysis"]
    logger.info('%s %s', "event_name:", data["session"]["event_name"])
    logger.info('%s %s', "session_name:", data["session"]["session_name"])
    logger.info('%s %s', "Number of cars:", len(cars))

    for car in cars:
        if car["manufacturer"] == "BMW":
            logger.info('%s %s', "Team:", car["team"])
            logger.info('%s %s', "Car number:", car["number"])


if __name__ == "__main__":
    main()

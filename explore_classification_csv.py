"""Inspect an official classification CSV without publishing pipeline outputs."""

from pathlib import Path
import argparse
import logging

import duckdb

from moto_sport_bmw_pipeline.logging_config import configure_logging

logger = logging.getLogger("moto_sport_bmw_pipeline.explore_classification_csv")


def main() -> None:
    configure_logging()
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source_path", type=Path)
    parser.add_argument("--timing-path", type=Path, help="Optional timing CSV to inspect alongside the classification.")
    args = parser.parse_args()

    if not args.source_path.is_file():
        raise FileNotFoundError(args.source_path)

    with duckdb.connect() as connection:
        classification = connection.read_csv(
            str(args.source_path),
            delimiter=";",
            header=True,
            all_varchar=True,
            # Source rows omit trailing fields present in the header.
            null_padding=True,
        )
        classification.create_view("classification_csv")

        logger.info('%s %s', "Rows:", classification.count("*").fetchone()[0])
        logger.debug('%s %s', "Columns:", classification.columns)
        classification.project("POSITION, NUMBER, VEHICLE, CLASS").limit(5).show()

        connection.sql("""
            SELECT
                NUMBER,
                TRY_CAST(POSITION AS INTEGER) AS POSITION,
                CLASS,
                VEHICLE
            FROM classification_csv
            WHERE VEHICLE LIKE 'BMW%'
            ORDER BY POSITION
        """).show()

        if args.timing_path is None:
            return
        timing = connection.read_csv(
            str(args.timing_path),
            delimiter=";",
            header=True,
            all_varchar=True,
        )

        logger.info('%s %s', "Colonnes des chronos :", timing.columns)

        timing.create_view("timing_csv")

        connection.sql("""
            SELECT
                NUMBER,
                TRY_CAST(LAP_NUMBER AS INTEGER) AS lap_number,
                DRIVER_NAME,
                PIT_TIME
            FROM timing_csv
            WHERE NUMBER = '25'
            ORDER BY lap_number
            LIMIT 5
        """).show()


if __name__ == "__main__":
    main()

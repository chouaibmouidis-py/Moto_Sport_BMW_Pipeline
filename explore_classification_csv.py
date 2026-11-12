"""Inspect an official classification CSV without publishing pipeline outputs."""

import argparse
from pathlib import Path

import duckdb


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source_path", type=Path)
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

        print("Rows:", classification.count("*").fetchone()[0])
        print("Columns:", classification.columns)
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

        timing = connection.read_csv(
            "/tmp/imsa-ra2023-timing.csv",
            delimiter=";",
            header=True,
            all_varchar=True,
        )

        print("Colonnes des chronos :", timing.columns)

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

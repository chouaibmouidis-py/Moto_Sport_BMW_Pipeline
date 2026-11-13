"""Explore one Road America 2023 PDF/CSV pair; preserve historical helper imports."""

from pathlib import Path
import argparse

from moto_sport_bmw_pipeline.exploration import (
    build_pdf_car_summary, compute_source_hash, convert_extracted_stops,
    explore_source_pair, validate_classification_keys, validate_pdf_stop_links,
)
from moto_sport_bmw_pipeline.logging_config import configure_logging
from moto_sport_bmw_pipeline.paths import PROJECT_DIR
from moto_sport_bmw_pipeline.pdf_parser import (
    CAR_HEADER, STOP_CANDIDATE, STOP_ROW, classify_token, extract_selected_stops,
    extract_stops, parse_selected_stops, parse_stop_blocks,
)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source_path", type=Path)
    parser.add_argument("classification_path", type=Path)
    parser.add_argument("--verbose", action="store_true", help="Enable DEBUG diagnostics.")
    parser.add_argument("--log-file", help="Append UTF-8 operational logs to this file.")
    args = parser.parse_args()
    configure_logging(verbose=args.verbose, log_file=args.log_file)
    explore_source_pair(
        args.source_path, args.classification_path,
        {
            "championship": "imsa-weathertech", "season": 2023,
            "event_id": "road-america", "session_id": "202308061010-race",
        },
        PROJECT_DIR / "data" / "exploration" / "road-america-2023" / "car_summary.parquet",
        show_tables=True,
    )


if __name__ == "__main__":
    main()

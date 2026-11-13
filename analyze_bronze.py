"""CLI for JSON candidate runs; implementation lives in moto_sport_bmw_pipeline.

Historical function imports remain available while callers migrate to the package.
"""

import argparse

from moto_sport_bmw_pipeline.logging_config import configure_logging
from moto_sport_bmw_pipeline.paths import PROJECT_DIR
from moto_sport_bmw_pipeline.pipeline import build_candidate_run
from moto_sport_bmw_pipeline.publication import publish_run_outputs
from moto_sport_bmw_pipeline.quality import (
    build_session_quality, build_source_pairs, build_total_duration_quality,
    validate_entry_links, validate_race_car_summary,
)
from moto_sport_bmw_pipeline.silver import (
    transform_car_entries, transform_driver_entries, transform_pit_stops, transform_sessions,
)
from moto_sport_bmw_pipeline.source_loading import (
    load_pit_stop_bronze, load_source_sessions, select_pit_stop_sources,
)


def main():
    parser = argparse.ArgumentParser(description="Build and check the BMW pipeline outputs.")
    parser.add_argument("--verbose", action="store_true", help="Display tables and DEBUG logs.")
    parser.add_argument("--log-file", help="Also append UTF-8 operational logs to this file.")
    args = parser.parse_args()
    configure_logging(verbose=args.verbose, log_file=args.log_file)
    build_candidate_run(PROJECT_DIR, verbose=args.verbose)


if __name__ == "__main__":
    main()

"""Build and activate a separate cross-season Gold run from existing local inputs."""

import argparse

from moto_sport_bmw_pipeline.gold import build_gold_candidate
from moto_sport_bmw_pipeline.logging_config import configure_logging
from moto_sport_bmw_pipeline.paths import PROJECT_DIR


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--verbose", action="store_true", help="Enable DEBUG logs.")
    parser.add_argument("--log-file", help="Append UTF-8 logs to this file.")
    args = parser.parse_args()
    configure_logging(verbose=args.verbose, log_file=args.log_file)
    build_gold_candidate(PROJECT_DIR)


if __name__ == "__main__":
    main()

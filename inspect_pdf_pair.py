"""Inspect a caller-selected PDF/CSV pair with explicit race context."""

from pathlib import Path
import argparse

from moto_sport_bmw_pipeline.pair_diagnostics import inspect_source_pair
from moto_sport_bmw_pipeline.logging_config import configure_logging


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source_path", type=Path)
    parser.add_argument("classification_path", type=Path)
    parser.add_argument("--verbose", action="store_true", help="Enable DEBUG diagnostics.")
    parser.add_argument("--log-file", help="Append UTF-8 operational logs to this file.")
    parser.add_argument("--championship", required=True)
    parser.add_argument("--season", required=True, type=int)
    parser.add_argument("--event-id", required=True)
    parser.add_argument("--session-id", required=True)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    configure_logging(verbose=args.verbose, log_file=args.log_file)
    inspect_source_pair(
        args.source_path, args.classification_path,
        {
            "championship": args.championship, "season": args.season,
            "event_id": args.event_id, "session_id": args.session_id,
        },
        args.output,
        show_tables=True,
    )


if __name__ == "__main__":
    main()

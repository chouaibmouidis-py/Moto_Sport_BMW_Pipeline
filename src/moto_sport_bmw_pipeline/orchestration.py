"""Run the five JSON pipeline stages in order; stop immediately when a stage fails."""

from pathlib import Path
import argparse
import json
import logging
import os
import subprocess
import sys

from .manifest import validate_unique_source_ids
from moto_sport_bmw_pipeline.logging_config import configure_logging
from moto_sport_bmw_pipeline.paths import PROJECT_DIR

logger = logging.getLogger("moto_sport_bmw_pipeline.run_pipeline")


SCRIPTS = (
    "inspect_manifest.py", "build_bronze.py", "inspect_classification.py",
    "build_classification_bronze.py", "analyze_bronze.py",
)


def main(argv=()) -> None:
    """Coordinate stages; argv=() preserves programmatic calls without CLI arguments."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--verbose", action="store_true", help="Enable DEBUG logs and analysis tables.")
    parser.add_argument("--log-file", type=Path, help="Append all stage logs to this UTF-8 file.")
    args = parser.parse_args(argv)
    configure_logging(verbose=args.verbose, log_file=args.log_file)
    manifest_path = PROJECT_DIR / "config" / "sources.json"
    with manifest_path.open("r", encoding="utf-8") as file:
        manifest = json.load(file)
    validate_unique_source_ids(manifest["documents"])

    # Stage processes inherit the same verbosity and optional log destination.
    environment = os.environ.copy()
    environment["BMW_LOG_LEVEL"] = "DEBUG" if args.verbose else environment.get("BMW_LOG_LEVEL", "INFO")
    if args.log_file:
        environment["BMW_LOG_FILE"] = str(args.log_file.expanduser().resolve())
    for script in SCRIPTS:
        command = [sys.executable, str(PROJECT_DIR / script)]
        if args.verbose and script == "analyze_bronze.py":
            command.append("--verbose")
        logger.info("Starting: %s", script)
        try:
            subprocess.run(command, cwd=PROJECT_DIR, env=environment, check=True)
        except subprocess.CalledProcessError:
            logger.exception("Stage failed: %s; remaining stages will not run", script)
            raise
        logger.info("Completed: %s", script)
    logger.info("Pipeline completed successfully.")


if __name__ == "__main__":
    main(None)

"""CLI compatibility entry point for the five-stage JSON workflow."""

from pathlib import Path
import subprocess

from moto_sport_bmw_pipeline.orchestration import PROJECT_DIR, SCRIPTS, main


if __name__ == "__main__":
    main(None)

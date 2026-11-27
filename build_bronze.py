"""Preserve pit-stop JSON roots in Bronze Parquet and verify round-trip content."""

from pathlib import Path
import json
import logging
import uuid

import duckdb
from moto_sport_bmw_pipeline.bronze import build_document, bronze_document_path

from download import RAW_DIR
from file_integrity import verify_local_file
from moto_sport_bmw_pipeline.logging_config import configure_logging

logger = logging.getLogger("moto_sport_bmw_pipeline.build_bronze")


PROJECT_DIR = Path(__file__).resolve().parent


def main(*, extension_directory: Path | None = None) -> None:
    configure_logging()
    manifest_path = PROJECT_DIR / "config" / "sources.json"

    with manifest_path.open("r", encoding="utf-8") as file:
        manifest = json.load(file)

    for source in manifest["documents"]:
        if (
            source.get("enabled", False)
            and source["document_type"] == "pit_stops"
            and source.get("format", "json") == "json"
        ):
            source_path = (
                PROJECT_DIR / RAW_DIR
                / source["source_id"]
                / source["filename"]
            )
            output_path = bronze_document_path(PROJECT_DIR, source)

            logger.info('%s %s', "Processing:", source["source_id"])
            metadata_path = source_path.parent / "metadata.json"

            verify_local_file(source_path, metadata_path)
            build_document(source_path, output_path, extension_directory=extension_directory)
if __name__ == "__main__":
    main()

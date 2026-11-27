"""Preserve classification JSON roots in validated Bronze Parquet."""

from pathlib import Path
import json
import logging
import uuid

import duckdb
from moto_sport_bmw_pipeline.bronze import build_classification_document, bronze_document_path
from moto_sport_bmw_pipeline.bronze import build_classification_csv, read_classification_csv
from file_integrity import verify_local_file
from moto_sport_bmw_pipeline.logging_config import configure_logging
from moto_sport_bmw_pipeline.source_loading import select_classification_sources

logger = logging.getLogger("moto_sport_bmw_pipeline.build_classification_bronze")


def main(*, extension_directory: Path | None = None) -> None:
    configure_logging()
    project_directory = Path(__file__).resolve().parent
    manifest_path = project_directory / "config" / "sources.json"

    with manifest_path.open("r", encoding="utf-8") as file:
        manifest = json.load(file)

    selected_sources = select_classification_sources(manifest["documents"], format="json")

    for source in selected_sources:
        source_id = source["source_id"]

        raw_directory = project_directory / "data" / "raw" / source_id
        source_path = raw_directory / source["filename"]
        metadata_path = raw_directory / "metadata.json"

        output_path = bronze_document_path(project_directory, source)

        verify_local_file(source_path, metadata_path)
        build_classification_document(source_path, output_path, extension_directory=extension_directory)

if __name__ == "__main__":
    main()

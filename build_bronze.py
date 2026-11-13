"""Preserve pit-stop JSON roots in Bronze Parquet and verify round-trip content."""

from pathlib import Path
import json
import logging
import uuid

import duckdb

from download import RAW_DIR, SOURCE_FILENAME
from file_integrity import verify_local_file
from moto_sport_bmw_pipeline.logging_config import configure_logging

logger = logging.getLogger("moto_sport_bmw_pipeline.build_bronze")


PROJECT_DIR = Path(__file__).resolve().parent


def build_document(source_path: Path, output_path: Path) -> None:
    if output_path.suffix != ".parquet":
        raise ValueError(
            f"Unexpected file format {output_path}"
        )
    def count_entries(cars: list) -> tuple[int, int, int]:
        return (
            len(cars),
            sum(len(car["drivers"]) for car in cars),
            sum(len(car["pit_stops"]) for car in cars),
        )

    with source_path.open("r", encoding="utf-8-sig") as file:
        source_data = json.load(file)

    expected = count_entries(source_data["pit_stop_analysis"])
    logger.info('%s %s', "Source JSON counts:", expected)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    run_id = uuid.uuid4().hex
    temporary_path = output_path.with_name(
        f"{output_path.name}.{run_id}.tmp.parquet"
    )
    logger.debug('%s', f"Temporary file for this execution: {temporary_path}")

    with duckdb.connect() as connection:
        document = connection.read_json(
            str(source_path),
            format="unstructured",
            columns={
                "session": "JSON",
                "pit_stop_analysis": "JSON",
            },
        )

        document.write_parquet(str(temporary_path))
        saved = connection.read_parquet(str(temporary_path))

        rows = saved.project(
            "to_json(session), to_json(pit_stop_analysis)"
        ).fetchall()

        if len(rows) != 1:
            raise ValueError(
                f"Expected one document, found {len(rows)} rows"
            )

        saved_session = json.loads(rows[0][0])
        saved_cars = json.loads(rows[0][1])

        if saved_session != source_data["session"]:
            raise ValueError(
                "Session content differs between JSON and Parquet"
            )
        if saved_cars != source_data["pit_stop_analysis"]:
            raise ValueError(
                "Car content differs between JSON and Parquet"
            )
        counts = count_entries(saved_cars)

        if counts != expected:
            raise ValueError(
                f"Unexpected counts: {counts}, expected: {expected}"
            )

    temporary_path.replace(output_path)
    logger.info('%s %s', "Volume check passed:", counts)

def main() -> None:
    configure_logging()
    manifest_path = PROJECT_DIR / "config" / "sources.json"

    with manifest_path.open("r", encoding="utf-8") as file:
        manifest = json.load(file)

    for source in manifest["documents"]:
        if (
            source.get("enabled", False)
            and source["document_type"] == "pit_stops"
        ):
            source_path = (
                PROJECT_DIR / RAW_DIR
                / source["source_id"]
                / SOURCE_FILENAME
            )
            output_path = (
                PROJECT_DIR / "data" / "bronze"
                / source["source_id"]
                / "document.parquet"
            )

            logger.info('%s %s', "Processing:", source["source_id"])
            metadata_path = source_path.parent / "metadata.json"

            verify_local_file(source_path, metadata_path)
            build_document(source_path, output_path)
if __name__ == "__main__":
    main()

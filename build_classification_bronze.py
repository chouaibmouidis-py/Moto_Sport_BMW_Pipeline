"""Preserve classification JSON roots or raw CSV fields in validated Bronze Parquet."""

from pathlib import Path
import json
import logging
import uuid

import duckdb
from moto_sport_bmw_pipeline.parquet_writer import publish_parquet
from file_integrity import verify_local_file
from moto_sport_bmw_pipeline.logging_config import configure_logging
from moto_sport_bmw_pipeline.source_loading import select_classification_sources

logger = logging.getLogger("moto_sport_bmw_pipeline.build_classification_bronze")


def build_classification_document(
    source_path: Path,
    output_path: Path,
) -> None:
    with source_path.open("r", encoding="utf-8-sig") as file:
        source_data = json.load(file)
        logger.info('%s %s', "Classification entries:", len(source_data["classification"]))

    if output_path.suffix != ".parquet":
        raise ValueError(f"Unexpected file format {output_path}")

    output_path.parent.mkdir(parents=True, exist_ok=True)

    run_id = uuid.uuid4().hex
    temporary_path = output_path.with_name(
        f"{output_path.name}.{run_id}.tmp.parquet"
    )

    with duckdb.connect() as connection:
        document = connection.read_json(
            str(source_path),
            format="unstructured",
            columns={
                "session": "JSON",
                "fastest_lap": "JSON",
                "classification": "JSON",
            },
        )

        document.write_parquet(str(temporary_path))

        saved = connection.read_parquet(str(temporary_path))

        rows = saved.project(
            "to_json(session), to_json(fastest_lap), to_json(classification)"
        ).fetchall()

        if len(rows) != 1:
            raise ValueError(
                f"Expected one document, found {len(rows)} rows"
            )

        for column_index, root_name in enumerate(
            ("session", "fastest_lap", "classification")
        ):
            saved_value = json.loads(rows[0][column_index])

            if saved_value != source_data[root_name]:
                raise ValueError(
                    f"Bronze rejected: content differs for {root_name}"
                )

    temporary_path.replace(output_path)
    logger.info('%s %s', "Bronze published:", output_path)

def read_classification_csv(connection, source_path: Path):
    """Read classification CSV fields as text without applying Silver cleaning."""
    return connection.read_csv(
        str(source_path),
        delimiter=";",
        header=True,
        all_varchar=True,
        null_padding=True,
    )

def build_classification_csv(
    source_path: Path,
    output_path: Path,
) -> None:
    """Publish raw classification CSV fields as validated Bronze Parquet."""
    if output_path.suffix != ".parquet":
        raise ValueError(f"Unexpected file format {output_path}")

    with duckdb.connect() as connection:
        document = read_classification_csv(connection, source_path)
        document.create_view("bronze_classification_csv")

        publish_parquet(
            connection,
            document,
            output_path,
            source_view="bronze_classification_csv",
        )

def main() -> None:
    configure_logging()
    project_directory = Path(__file__).resolve().parent
    manifest_path = project_directory / "config" / "sources.json"

    with manifest_path.open("r", encoding="utf-8") as file:
        manifest = json.load(file)

    selected_sources = select_classification_sources(manifest["documents"])

    for source in selected_sources:
        source_id = source["source_id"]

        raw_directory = project_directory / "data" / "raw" / source_id
        source_path = raw_directory / source["filename"]
        metadata_path = raw_directory / "metadata.json"

        output_path = (
            project_directory
            / "data"
            / "bronze"
            / source_id
            / "document.parquet"
        )

        verify_local_file(source_path, metadata_path)
        build_classification_document(source_path, output_path)

if __name__ == "__main__":
    main()

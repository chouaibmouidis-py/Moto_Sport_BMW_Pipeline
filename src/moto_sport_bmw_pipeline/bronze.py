"""Preserve extracted source fields and provenance in validated Bronze Parquet.

Parsing stays in format-specific readers; cleaning and duration conversion belong
to Silver. Raw source documents remain the reference for extraction reviews.
"""

import hashlib
import json
import logging
import uuid
from pathlib import Path

import duckdb

from .parquet_writer import publish_parquet
from .pdf_parser import extract_stops

logger = logging.getLogger(__name__)


def build_source(project_directory: Path, source: dict) -> Path:
    """Extract one source using its declared document role and file format."""
    source_path = project_directory / "data/raw" / source["source_id"] / source["filename"]
    output = project_directory / "data/bronze" / source["source_id"] / "document.parquet"
    key = (source["document_type"], source["format"])
    builders = {
        ("pit_stops", "json"): build_document,
        ("classification", "json"): build_classification_document,
        ("classification", "csv"): build_classification_csv,
    }
    if key == ("pit_stops", "pdf"):
        build_pdf_pit_stop_bronze(source_path, output, source["source_id"])
    elif key in builders:
        builders[key](source_path, output)
    else:
        raise ValueError(f"Unsupported Bronze reader: {key}")
    return output


def build_pdf_pit_stop_bronze(
    source_path: Path,
    output_path: Path,
    source_id: str,
) -> Path:
    """Publish raw extracted stops and their PDF fingerprint and locations.

    This preserves the reader's selected fields, not every element of the PDF.
    Extraction must succeed before an existing output can be replaced.
    """
    if output_path.suffix != ".parquet":
        raise ValueError(f"Unexpected file format {output_path}")
    if not isinstance(source_id, str) or not source_id.strip():
        raise ValueError("PDF Bronze rejected: missing source ID")

    pdf_sha256 = hashlib.sha256(source_path.read_bytes()).hexdigest()
    rows = extract_stops(source_path)
    if hashlib.sha256(source_path.read_bytes()).hexdigest() != pdf_sha256:
        raise ValueError("PDF Bronze rejected: source changed during extraction")

    with duckdb.connect() as connection:
        connection.execute("""
            CREATE TEMP TABLE bronze_pdf_pit_stops (
                source_id VARCHAR,
                pdf_sha256 VARCHAR,
                car_number VARCHAR,
                pit_number INTEGER,
                pit_time_raw VARCHAR,
                page_number INTEGER,
                column_number INTEGER,
                block_line_number INTEGER,
                source_line VARCHAR
            )
        """)
        if rows:
            connection.executemany(
                "INSERT INTO bronze_pdf_pit_stops VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                [
                    (
                        source_id, pdf_sha256, row["car_number"], row["pit_number"],
                        row["pit_time_raw"], row["page_number"], row["column_number"],
                        row["block_line_number"], row["source_line"],
                    )
                    for row in rows
                ],
            )
        document = connection.table("bronze_pdf_pit_stops")
        publish_parquet(
            connection, document, output_path,
        )
    return output_path


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
        )


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

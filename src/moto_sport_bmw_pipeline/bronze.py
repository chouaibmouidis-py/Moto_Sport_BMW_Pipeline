"""Preserve extracted source fields and provenance in validated Bronze Parquet.

Parsing stays in format-specific readers; cleaning and duration conversion belong
to Silver. Raw source documents remain the reference for extraction reviews.
"""

import hashlib
from pathlib import Path

import duckdb

from .parquet_writer import publish_parquet
from .pdf_parser import extract_stops


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
            connection, document, output_path, source_view="bronze_pdf_pit_stops",
        )
    return output_path

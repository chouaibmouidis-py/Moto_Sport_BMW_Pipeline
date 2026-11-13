"""Convert, validate and publish exploratory CSV/PDF pairs outside the active JSON pipeline."""

from pathlib import Path
import hashlib
import logging

import duckdb
from .quality import validate_classification_keys
from .parquet_writer import publish_silver
from .paths import PROJECT_DIR
from .pdf_parser import extract_stops

logger = logging.getLogger(__name__)


def convert_extracted_stops(
    connection: duckdb.DuckDBPyConnection,
    rows: list[dict],
    project_directory: Path,
) -> duckdb.DuckDBPyRelation:
    """Convert durations while preserving all raw stop fields and location metadata."""
    connection.execute("""
        CREATE TEMP TABLE extracted_pit_stops (
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
            "INSERT INTO extracted_pit_stops VALUES (?, ?, ?, ?, ?, ?, ?)",
            [
                (
                    row["car_number"], row["pit_number"], row["pit_time_raw"],
                    row["page_number"], row["column_number"],
                    row["block_line_number"], row["source_line"],
                )
                for row in rows
            ],
        )

    parser_path = project_directory / "sql" / "21_create_duration_parser.sql"
    connection.execute(parser_path.read_text(encoding="utf-8"))

    return connection.sql("""
        SELECT
            car_number,
            pit_number,
            pit_time_raw,
            ROUND(parse_duration_seconds(pit_time_raw), 3) AS pit_time_seconds,
            page_number,
            column_number,
            block_line_number,
            source_line
        FROM extracted_pit_stops
        ORDER BY car_number, pit_number
    """)


def validate_pdf_stop_links(connection):
    unknown_car_count = connection.sql("""
        SELECT COUNT(DISTINCT s.car_number)
        FROM pdf_stops AS s
        LEFT JOIN classification_csv AS c
            ON s.car_number = NULLIF(TRIM(c.NUMBER), '')
        WHERE c.NUMBER IS NULL
    """).fetchone()[0]

    if unknown_car_count > 0:
        raise ValueError(
            "PDF stops rejected: car absent from classification"
        )

def build_pdf_car_summary(
    connection,
    pdf_sha256: str,
    classification_sha256: str,
    source_context: dict,
):

    return connection.sql("""
        WITH stop_counts AS (
            SELECT
                car_number,
                COUNT(*) AS observed_pit_stop_count
            FROM pdf_stops
            GROUP BY car_number
        )
        SELECT
            NULLIF(TRIM(c.NUMBER), '') AS car_number,
            TRY_CAST(c.POSITION AS INTEGER) AS overall_position,
            NULLIF(TRIM(c.VEHICLE), '') AS car_model,
            s.observed_pit_stop_count,
            ? AS pdf_sha256,
            ? AS classification_sha256,
            ? AS championship,
            ? AS season,
            ? AS event_id,
            ? AS session_id,
            NULLIF(TRIM(c.STATUS), '') AS classification_status
        FROM classification_csv AS c
        LEFT JOIN stop_counts AS s
            ON NULLIF(TRIM(c.NUMBER), '') = s.car_number
            ORDER BY overall_position NULLS LAST, car_number
    """, params=[
        pdf_sha256,
        classification_sha256,
        source_context["championship"],
        source_context["season"],
        source_context["event_id"],
        source_context["session_id"],
    ])

def compute_source_hash(source_path: Path) -> str:
    return hashlib.sha256(source_path.read_bytes()).hexdigest()

def explore_source_pair(
    pdf_path: Path,
    classification_path: Path,
    source_context: dict,
    output_path: Path,
    *,
    show_tables: bool = False,
) -> dict:
    """Validate and publish one exploratory pair, without activating a main run."""
    logger.info("Exploring event: %s; session: %s", source_context["event_id"], source_context["session_id"])
    for source_path in (pdf_path, classification_path):
        if not source_path.is_file():
            raise FileNotFoundError(
                f"Exploration rejected: source file not found: {source_path}"
            )

    pdf_sha256 = compute_source_hash(pdf_path)
    classification_sha256 = compute_source_hash(classification_path)

    if show_tables:
        logger.debug("PDF SHA-256: %s", pdf_sha256)
        logger.debug("Classification SHA-256: %s", classification_sha256)

    rows = extract_stops(pdf_path)
    project_directory = PROJECT_DIR

    with duckdb.connect() as connection:
        converted = convert_extracted_stops(connection, rows, project_directory)
        converted.create_view("pdf_stops")

        classification = connection.read_csv(
            str(classification_path),
            delimiter=";",
            header=True,
            all_varchar=True,
            null_padding=True,
        )
        classification.create_view("classification_csv")
        validate_classification_keys(connection)
        if show_tables:
            converted.show()

        validate_pdf_stop_links(connection)
        summary = build_pdf_car_summary(
            connection,
            pdf_sha256,
            classification_sha256,
            source_context=source_context,
        )
        if show_tables:
            summary.show()

        summary.create_view("pdf_car_summary")

        publish_silver(
            connection,
            summary,
            output_path,
            source_view="pdf_car_summary",
        )
        return {
            "event_id": source_context["event_id"],
            "participants": summary.count("*").fetchone()[0],
            "bmw_participants": summary.filter("car_model LIKE 'BMW%'").count("*").fetchone()[0],
            "stops": len(rows),
            "bmw_stops": connection.sql("""
                SELECT COUNT(*) FROM pdf_stops s
                JOIN classification_csv c ON s.car_number = c.NUMBER
                WHERE c.VEHICLE LIKE 'BMW%'
            """).fetchone()[0],
        }

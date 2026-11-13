"""Load manifest session metadata and versioned Bronze documents into DuckDB."""

from pathlib import Path
import hashlib
import logging

logger = logging.getLogger(__name__)


def select_classification_sources(documents):
    selected_sources = []
    for document in documents:
        if document.get("enabled", False) and document["document_type"] == "classification":
            selected_sources.append(document)
    return selected_sources

def load_source_sessions(connection, documents) -> None:

    connection.execute("""
        CREATE TEMP TABLE source_sessions (
            source_id VARCHAR,
            championship VARCHAR,
            season INTEGER,
            event_id VARCHAR,
            session_id VARCHAR,
            document_type VARCHAR
        )
    """)

    for source in documents:
        if not source.get("enabled", False):
            continue

        connection.execute(
            "INSERT INTO source_sessions VALUES (?, ?, ?, ?, ?, ?)",
            [
                source["source_id"],
                source["championship"],
                source["season"],
                source["event_id"],
                source["session_id"],
                source["document_type"],
            ],
        )

def load_pit_stop_bronze(
    connection,
    sources,
    project_directory: Path,
) -> None:

    connection.execute("""
        CREATE TEMP TABLE bronze_document (
            session JSON,
            pit_stop_analysis JSON,
            source_id VARCHAR,
            bronze_sha256 VARCHAR
        )
    """)

    for source in sources:
        bronze_path = (
         project_directory
            / "data"
            / "bronze"
            / source["source_id"]
            / "document.parquet"
        )

        bronze_sha256 = hashlib.sha256(
            bronze_path.read_bytes()
        ).hexdigest()

        connection.execute(
            """
            INSERT INTO bronze_document
            SELECT session, pit_stop_analysis, ?, ?
            FROM read_parquet(?)
            """,
            [
                source["source_id"],
                bronze_sha256,
                str(bronze_path),
            ],
        )

        logger.info("Bronze source loaded: %s", source["source_id"])

def select_pit_stop_sources(documents):
    selected_sources = []
    for document in documents:
        if document.get("enabled", False) and document["document_type"] == "pit_stops":
            selected_sources.append(document)
    return selected_sources

def load_classification_bronze(connection, bronze_path, source_id):
    saved = connection.read_parquet(str(bronze_path))
    bronze_sha256 = hashlib.sha256(
        bronze_path.read_bytes()
    ).hexdigest()

    saved.create_view("bronze_classification_input")

    connection.sql(
        """
        SELECT
            *,
            ? AS source_id,
            ? AS bronze_sha256
        FROM bronze_classification_input
        """,
        params=[source_id, bronze_sha256],
    ).create_view("bronze_classification")

def load_classification_sources(
    connection,
    sources,
    project_directory: Path,
) -> None:

    connection.execute("""
        CREATE TEMP TABLE bronze_classification (
            session JSON,
            fastest_lap JSON,
            classification JSON,
            source_id VARCHAR,
            bronze_sha256 VARCHAR
        )
    """)

    for source in sources:
        bronze_path = (
         project_directory
            / "data"
            / "bronze"
            / source["source_id"]
            / "document.parquet"
        )

        if not bronze_path.is_file():
            raise FileNotFoundError(
                "Classification loading rejected: missing Bronze file "
                f"for source '{source['source_id']}': {bronze_path}"
            )

        bronze_sha256 = hashlib.sha256(
            bronze_path.read_bytes()
        ).hexdigest()

        connection.execute(
            """
            INSERT INTO bronze_classification
            SELECT session, fastest_lap, classification, ?, ?
            FROM read_parquet(?)
            """,
            [
                source["source_id"],
                bronze_sha256,
                str(bronze_path),
            ],
        )

        logger.info("Bronze source loaded: %s", source["source_id"])

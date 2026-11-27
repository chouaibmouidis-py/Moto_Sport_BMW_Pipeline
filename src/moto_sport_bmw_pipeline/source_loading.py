"""Load manifest session metadata and versioned Bronze documents into DuckDB."""

import logging
from pathlib import Path

from .bronze import bronze_document_path
from .bronze_storage import read_bronze
from .integrity import sha256_file
from .logging_config import log_operation

logger = logging.getLogger(__name__)


def select_classification_sources(documents, *, format=None):
    selected_sources = []
    for document in documents:
        if (
            document.get("enabled", False)
            and document["document_type"] == "classification"
            and (format is None or document.get("format", "json") == format)
        ):
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


def load_pit_stop_file(
    connection,
    bronze_path: Path,
    source_id,
    *,
    view_name="bronze_document",
    _read=read_bronze,
):
    """Load one explicit file with its logical schema and provenance.

    Collective production loading and isolated storage experiments share this
    reader; the caller chooses the destination view, not the storage policy.
    """
    saved = _read(
        connection, bronze_path, json_columns=("session", "pit_stop_analysis")
    )
    bronze_sha256 = sha256_file(bronze_path)
    saved.create_view("pit_stop_file_input", replace=True)
    connection.sql(
        "SELECT session, pit_stop_analysis, ? AS source_id, ? AS bronze_sha256 FROM pit_stop_file_input",
        params=[source_id, bronze_sha256],
    ).create_view(view_name, replace=True)


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
        with log_operation(
            logger,
            "Load JSON Bronze report",
            stage="load_bronze",
            source_id=source["source_id"],
        ):
            bronze_path = bronze_document_path(project_directory, source)

            load_pit_stop_file(
                connection,
                bronze_path,
                source["source_id"],
                view_name="pit_stop_source_input",
            )
            connection.execute(
                """
                INSERT INTO bronze_document
                SELECT session, pit_stop_analysis, source_id, bronze_sha256
                FROM pit_stop_source_input
                """,
            )

            logger.info("Bronze source loaded: %s", source["source_id"])


def select_pit_stop_sources(documents, *, format=None):
    selected_sources = []
    for document in documents:
        if (
            document.get("enabled", False)
            and document["document_type"] == "pit_stops"
            and (format is None or document.get("format", "json") == format)
        ):
            selected_sources.append(document)
    return selected_sources


def load_classification_bronze(
    connection, bronze_path, source_id, *, _read=read_bronze
):

    saved = _read(
        connection,
        bronze_path,
        json_columns=("session", "fastest_lap", "classification"),
    )

    bronze_sha256 = sha256_file(bronze_path)

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


def load_classification_sources(connection, sources, project_directory: Path) -> None:

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
        with log_operation(
            logger,
            "Load JSON Bronze report",
            stage="load_bronze",
            source_id=source["source_id"],
        ):
            bronze_path = bronze_document_path(project_directory, source)

            if not bronze_path.is_file():
                raise FileNotFoundError(
                    "Classification loading rejected: missing Bronze file "
                    f"for source '{source['source_id']}': {bronze_path}"
                )

            bronze_sha256 = sha256_file(bronze_path)

            saved = read_bronze(
                connection,
                bronze_path,
                json_columns=("session", "fastest_lap", "classification"),
            )

            saved.create_view("classification_source_input", replace=True)

            connection.execute(
                """
                INSERT INTO bronze_classification
                SELECT session, fastest_lap, classification, ?, ?
                FROM classification_source_input
                """,
                [source["source_id"], bronze_sha256],
            )

            logger.info("Bronze source loaded: %s", source["source_id"])


def load_classification_csv_bronze(
    connection, bronze_path: Path, source_id: str, *, _read=read_bronze
) -> None:
    """Load classification CSV Bronze with its source ID and file fingerprint."""
    bronze_sha256 = sha256_file(bronze_path)

    document = _read(connection, bronze_path)
    document.create_view("classification_csv_input")

    connection.sql(
        """
        SELECT
            *,
            ? AS source_id,
            ? AS bronze_sha256
        FROM classification_csv_input
        """,
        params=[source_id, bronze_sha256],
    ).create_view("bronze_classification_csv")


def load_pdf_pit_stop_bronze(
    connection, bronze_path: Path, *, _read=read_bronze
) -> None:
    """Load extracted PDF stops and identify the exact Bronze file version."""
    bronze_sha256 = sha256_file(bronze_path)

    document = _read(connection, bronze_path)
    document.create_view("pdf_pit_stop_input")

    connection.sql(
        """
        SELECT
            *,
            ? AS bronze_sha256
        FROM pdf_pit_stop_input
        """,
        params=[bronze_sha256],
    ).create_view("bronze_pdf_pit_stops")


def load_csv_pdf_source_sessions(connection, catalog: dict) -> None:
    """Map configured CSV/PDF documents to their declared race sessions."""
    documents = []

    for event in catalog["events"]:
        for path_field, document_type in (
            ("classification_path", "classification"),
            ("pdf_path", "pit_stops"),
        ):
            source_id = Path(event[path_field]).parent.name

            documents.append(
                {
                    "source_id": source_id,
                    "championship": catalog["championship"],
                    "season": catalog["season"],
                    "event_id": event["event_id"],
                    "session_id": event["session_id"],
                    "document_type": document_type,
                    "enabled": True,
                }
            )

    load_source_sessions(connection, documents)

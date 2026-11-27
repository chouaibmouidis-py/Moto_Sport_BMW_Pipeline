"""Extract source-specific fields and publish them through shared Bronze storage.

Cleaning and duration conversion belong to Silver. Raw documents remain the
reference for extraction reviews; publication is independent of source format.
"""

import json
import logging
from pathlib import Path

import duckdb

from .bronze_storage import publish_bronze, read_bronze
from .integrity import sha256_file
from .logging_config import log_operation
from .pdf_parser import iter_stops

logger = logging.getLogger(__name__)


def bronze_document_path(project_directory: Path, source: dict) -> Path:
    """Resolve the single Bronze storage contract, independent of source format."""
    return project_directory / "data/bronze" / source["source_id"] / "document.parquet"


def _connection_config(extension_directory):
    return (
        {}
        if extension_directory is None
        else {"extension_directory": str(extension_directory)}
    )


def _check_output(output_path):
    if output_path.suffix not in {".parquet", ".vortex"}:
        raise ValueError(f"Unexpected file format {output_path}")


def build_source(
    project_directory: Path, source: dict, *, extension_directory: Path | None = None
) -> Path:
    """Dispatch extraction; every builder uses the same publication mechanism."""
    with log_operation(
        logger, "Extract source", stage="bronze", source_id=source["source_id"]
    ):
        source_path = (
            project_directory / "data/raw" / source["source_id"] / source["filename"]
        )
        output = bronze_document_path(project_directory, source)
        key = (source["document_type"], source["format"])
        builders = {
            ("pit_stops", "json"): build_document,
            ("classification", "json"): build_classification_document,
            ("classification", "csv"): build_classification_csv,
        }
        options = (
            {}
            if extension_directory is None
            else {"extension_directory": extension_directory}
        )
        if key == ("pit_stops", "pdf"):
            build_pdf_pit_stop_bronze(
                source_path, output, source["source_id"], **options
            )
        elif key in builders:
            builders[key](source_path, output, **options)
        else:
            raise ValueError(f"Unsupported Bronze reader: {key}")
        return output


def build_pdf_pit_stop_bronze(
    source_path: Path,
    output_path: Path,
    source_id: str,
    *,
    extension_directory: Path | None = None,
    batch_size: int = 500,
) -> Path:
    """Preserve the PDF reader's extracted fields, fingerprint and locations."""
    _check_output(output_path)
    if (
        isinstance(batch_size, bool)
        or not isinstance(batch_size, int)
        or batch_size <= 0
    ):
        raise ValueError("batch_size must be a positive integer")
    if not isinstance(source_id, str) or not source_id.strip():
        raise ValueError("PDF Bronze rejected: missing source ID")
    pdf_sha256 = sha256_file(source_path)
    with duckdb.connect(config=_connection_config(extension_directory)) as connection:
        connection.execute("""
            CREATE TEMP TABLE bronze_pdf_pit_stops (
                source_id VARCHAR, pdf_sha256 VARCHAR, car_number VARCHAR,
                pit_number INTEGER, pit_time_raw VARCHAR, page_number INTEGER,
                column_number INTEGER, block_line_number INTEGER, source_line VARCHAR
            )
        """)
        rows = iter(iter_stops(source_path))
        batch = []
        try:
            for row in rows:
                batch.append(
                    (
                        source_id,
                        pdf_sha256,
                        row["car_number"],
                        row["pit_number"],
                        row["pit_time_raw"],
                        row["page_number"],
                        row["column_number"],
                        row["block_line_number"],
                        row["source_line"],
                    )
                )
                if len(batch) == batch_size:
                    connection.executemany(
                        "INSERT INTO bronze_pdf_pit_stops VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                        batch,
                    )
                    batch.clear()
            if batch:
                connection.executemany(
                    "INSERT INTO bronze_pdf_pit_stops VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                    batch,
                )
                batch.clear()
        finally:
            close = getattr(rows, "close", None)
            if close is not None:
                try:
                    close()
                except Exception:
                    logger.exception(
                        "Could not close PDF stop iterator: %s", source_path
                    )
        if sha256_file(source_path) != pdf_sha256:
            raise ValueError("PDF Bronze rejected: source changed during extraction")

        def validate(saved):
            if sha256_file(source_path) != pdf_sha256:
                raise ValueError(
                    "PDF Bronze rejected: source changed during publication"
                )

        publish_bronze(
            connection,
            connection.table("bronze_pdf_pit_stops"),
            output_path,
            validate=validate,
        )
    return output_path


def read_classification_csv(connection, source_path: Path):
    """Read raw CSV fields as text, without applying Silver cleaning."""
    return connection.read_csv(
        str(source_path),
        delimiter=";",
        header=True,
        all_varchar=True,
        null_padding=True,
    )


def build_classification_csv(
    source_path: Path, output_path: Path, *, extension_directory: Path | None = None
) -> None:
    _check_output(output_path)
    with duckdb.connect(config=_connection_config(extension_directory)) as connection:
        document = read_classification_csv(connection, source_path)
        publish_bronze(connection, document, output_path)


def _publish_json_document(
    source_path, output_path, roots, *, extension_directory=None, classification=False
):
    """Freeze JSON inside DuckDB; return only validation scalars to Python."""
    _check_output(output_path)

    def fingerprint():
        return sha256_file(source_path)

    original_hash = fingerprint()

    with duckdb.connect(config=_connection_config(extension_directory)) as connection:
        try:
            connection.execute(
                "CREATE TEMP TABLE source_json AS SELECT json FROM read_json_objects(?, format='unstructured')",
                [str(source_path)],
            )
        except duckdb.InvalidInputException as error:
            if "Malformed JSON" not in str(error):
                raise
            # Preserve the public malformed-JSON exception type without loading
            # the complete source string into Python. Native details are retained.
            raise json.JSONDecodeError(str(error), "", 0) from error
        source_count = connection.sql("SELECT count(*) FROM source_json").fetchone()[0]
        if source_count != 1:
            raise json.JSONDecodeError(
                f"Expected one JSON document, found {source_count}", "", 0
            )
        if (
            connection.sql("SELECT json_type(json) FROM source_json").fetchone()[0]
            != "OBJECT"
        ):
            raise ValueError("Bronze JSON rejected: expected an object document")
        for root in roots:
            if not connection.sql(
                "SELECT json_exists(json, ?) FROM source_json", params=[f"$.{root}"]
            ).fetchone()[0]:
                raise KeyError(root)
        # These names are internal constants supplied by the two JSON builders.
        projection = ", ".join(
            f"json_extract(json, '$.{root}') AS {root}" for root in roots
        )
        connection.execute(
            f"CREATE TEMP TABLE expected_json AS SELECT {projection} FROM source_json"
        )
        connection.execute("DROP TABLE source_json")
        document = connection.table("expected_json")

        def counts(view):
            array = "classification" if classification else "pit_stop_analysis"
            if connection.sql(
                f"SELECT json_type({array}) IS DISTINCT FROM 'ARRAY' FROM {view}"
            ).fetchone()[0]:
                raise ValueError(f"Bronze JSON rejected: {array} must be an array")
            if classification:
                return connection.sql(
                    f"SELECT json_array_length(classification) FROM {view}"
                ).fetchone()
            invalid = connection.sql(f"""
                SELECT count(*) FROM {view}, json_each(pit_stop_analysis) AS car
                WHERE json_type(car.value, '$.drivers') IS DISTINCT FROM 'ARRAY'
                   OR json_type(car.value, '$.pit_stops') IS DISTINCT FROM 'ARRAY'
            """).fetchone()[0]
            if invalid:
                raise ValueError(
                    "Bronze JSON rejected: drivers and pit_stops must be arrays"
                )
            return connection.sql(f"""
                SELECT json_array_length(pit_stop_analysis),
                    COALESCE((SELECT sum(json_array_length(car.value, '$.drivers'))
                              FROM json_each(pit_stop_analysis) AS car), 0),
                    COALESCE((SELECT sum(json_array_length(car.value, '$.pit_stops'))
                              FROM json_each(pit_stop_analysis) AS car), 0)
                FROM {view}
            """).fetchone()

        expected_counts = counts("expected_json")
        logger.info(
            "Classification entries: %s"
            if classification
            else "Source JSON counts: %s",
            expected_counts[0] if classification else expected_counts,
        )

        def validate(saved):
            if saved.count("*").fetchone()[0] != 1:
                raise ValueError("Expected one document in saved Bronze")
            saved.create_view("saved_json", replace=True)
            for root in roots:
                different = connection.sql(f"""
                    SELECT json(expected.{root}) IS DISTINCT FROM json(saved.{root})
                    FROM expected_json AS expected CROSS JOIN saved_json AS saved
                """).fetchone()[0]
                if different:
                    raise ValueError(f"Bronze rejected: content differs for {root}")
            saved_counts = counts("saved_json")
            if saved_counts != expected_counts:
                raise ValueError(
                    f"Unexpected counts: {saved_counts}, expected: {expected_counts}"
                )
            if fingerprint() != original_hash:
                raise ValueError("Bronze rejected: source changed during publication")

        # Classification callers retain their explicit logical-schema reader.
        reader = (
            read_vortex_classification
            if classification and output_path.suffix == ".vortex"
            else None
        )
        publish_bronze(
            connection, document, output_path, reader=reader, validate=validate
        )


def build_document(
    source_path: Path, output_path: Path, *, extension_directory: Path | None = None
) -> None:
    _publish_json_document(
        source_path,
        output_path,
        ("session", "pit_stop_analysis"),
        extension_directory=extension_directory,
    )


def build_classification_document(
    source_path: Path, output_path: Path, *, extension_directory: Path | None = None
) -> None:
    _publish_json_document(
        source_path,
        output_path,
        ("session", "fastest_lap", "classification"),
        extension_directory=extension_directory,
        classification=True,
    )


def read_vortex_classification(connection, source_path):
    """Compatibility reader: restore classification's logical JSON schema."""
    return read_bronze(
        connection,
        source_path,
        json_columns=("session", "fastest_lap", "classification"),
    )

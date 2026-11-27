"""Shared Bronze storage: write, reread, validate, replace and clean up."""

import logging
import uuid
from pathlib import Path

logger = logging.getLogger(__name__)


def _quoted(name):
    return '"' + name.replace('"', '""') + '"'


def read_bronze(connection, path: Path, *, json_columns=()):
    """Read a storage format and restore explicitly declared logical JSON fields."""
    if path.suffix != ".parquet":
        raise ValueError(f"Unexpected file format {path}")
    return restore_json_columns(connection.read_parquet(str(path)), json_columns)


def restore_json_columns(saved, json_columns):
    missing = set(json_columns) - set(saved.columns)
    if missing:
        raise ValueError(f"Bronze missing JSON columns: {sorted(missing)}")
    if json_columns:
        saved = saved.project(
            ", ".join(
                f"CAST({_quoted(name)} AS JSON) AS {_quoted(name)}"
                if name in json_columns
                else _quoted(name)
                for name in saved.columns
            )
        )
    return saved


def publish_bronze(
    connection, document, output_path: Path, *, reader=None, validate=None
):
    """Publish only after logical schema and exact row-multiset checks succeed.

    Readers extract source fields; an optional validator checks source-specific
    invariants. Publication mechanics are shared by all source formats.
    """
    if output_path.suffix != ".parquet":
        raise ValueError(f"Unexpected file format {output_path}")
    publish_candidate(
        connection,
        document,
        output_path,
        write=_write_parquet,
        read=read_bronze,
        reader=reader,
        validate=validate,
    )


def _write_parquet(connection, document, view, path):
    document.write_parquet(str(path))


def publish_candidate(
    connection, document, output_path, *, write, read, reader=None, validate=None
):
    """Validate and promote a candidate written by the supplied storage adapter."""
    output_path.parent.mkdir(parents=True, exist_ok=True)
    run_id = uuid.uuid4().hex
    temporary = output_path.with_name(
        f"{output_path.stem}.{run_id}.tmp{output_path.suffix}"
    )
    expected_view, saved_view = f"bronze_expected_{run_id}", f"bronze_saved_{run_id}"
    json_columns = [
        name
        for name, dtype in zip(document.columns, document.types)
        if str(dtype) == "JSON"
    ]
    try:
        document.create_view(expected_view)
        write(connection, document, expected_view, temporary)
        saved = (
            reader(connection, temporary)
            if reader
            else read(connection, temporary, json_columns=json_columns)
        )
        if saved.columns != document.columns or saved.types != document.types:
            raise ValueError("Bronze publication rejected: schema differs")
        if validate:
            validate(saved)
        saved.create_view(saved_view)
        differences = connection.sql(f"""
            SELECT count(*) FROM (
                (SELECT * FROM {_quoted(expected_view)} EXCEPT ALL SELECT * FROM {_quoted(saved_view)})
                UNION ALL
                (SELECT * FROM {_quoted(saved_view)} EXCEPT ALL SELECT * FROM {_quoted(expected_view)})
            )
        """).fetchone()[0]
        if differences:
            raise ValueError("Bronze publication rejected: content differs")
        temporary.replace(output_path)
        logger.info("Bronze published: %s", output_path)
    finally:
        try:
            temporary.unlink(missing_ok=True)
        except OSError:
            logger.exception("Could not remove Bronze temporary: %s", temporary)
        for view in (saved_view, expected_view):
            try:
                connection.execute(f"DROP VIEW IF EXISTS {_quoted(view)}")
            except Exception:
                logger.exception("Could not remove Bronze temporary view: %s", view)

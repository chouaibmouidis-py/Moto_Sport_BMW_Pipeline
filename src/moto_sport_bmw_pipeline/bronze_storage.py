"""Shared Bronze storage: write, reread, validate, replace and clean up."""

import logging
import uuid
from pathlib import Path

logger = logging.getLogger(__name__)


def _quoted(name):
    return '"' + name.replace('"', '""') + '"'


def read_bronze(connection, path: Path, *, json_columns=()):
    """Read a storage format and restore explicitly declared logical JSON fields."""
    if path.suffix == ".vortex":
        connection.execute("LOAD vortex")
        saved = connection.sql("SELECT * FROM read_vortex(?)", params=[str(path)])
    elif path.suffix == ".parquet":
        saved = connection.read_parquet(str(path))
    else:
        raise ValueError(f"Unexpected file format {path}")
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
    if output_path.suffix not in {".parquet", ".vortex"}:
        raise ValueError(f"Unexpected file format {output_path}")
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
        if output_path.suffix == ".vortex":
            connection.execute("LOAD vortex")
            connection.execute(
                f"COPY {_quoted(expected_view)} TO ? (FORMAT vortex)", [str(temporary)]
            )
        else:
            document.write_parquet(str(temporary))
        saved = (
            reader(connection, temporary)
            if reader
            else read_bronze(connection, temporary, json_columns=json_columns)
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

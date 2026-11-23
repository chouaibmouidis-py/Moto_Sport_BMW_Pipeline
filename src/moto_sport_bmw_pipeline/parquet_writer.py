"""Write, reread and compare one Parquet candidate before replacing its final path."""

from pathlib import Path
import logging
import uuid

import duckdb

logger = logging.getLogger(__name__)


def publish_parquet(
    connection: duckdb.DuckDBPyConnection,
    converted: duckdb.DuckDBPyRelation,
    silver_output_path: Path,
    *,
    verbose: bool = False,
) -> None:
    silver_output_path.parent.mkdir(parents=True, exist_ok=True)
    run_id = uuid.uuid4().hex
    expected_view = f"_expected_{run_id}"
    saved_view = f"_saved_{run_id}"

    quoted_expected_view = '"' + expected_view.replace('"', '""') + '"'
    quoted_saved_view = '"' + saved_view.replace('"', '""') + '"'
    try:
        converted.create_view(expected_view)
        silver_temporary_path = silver_output_path.with_name(
            f"{silver_output_path.stem}.{run_id}.tmp.parquet"
        )
        if verbose:
            logger.debug('%s %s', "Temporary publication path:", silver_temporary_path)

        converted.write_parquet(str(silver_temporary_path))

        saved_silver = connection.read_parquet(str(silver_temporary_path))
        saved_silver.create_view(saved_view)

        expected_count = converted.count("*").fetchone()[0]
        saved_count = saved_silver.count("*").fetchone()[0]

        if saved_count != expected_count:
            raise ValueError(
                f"Parquet publication rejected: row count mismatch "
                f"(path={silver_output_path}, expected={expected_count}, saved={saved_count})"
            )

        missing_rows = connection.sql(f"""
            SELECT * FROM {quoted_expected_view}
            EXCEPT ALL
            SELECT * FROM {quoted_saved_view}
        """).fetchall()

        if missing_rows:
            raise ValueError(
                f"Parquet publication rejected: saved content differs "
                f"(path={silver_output_path})"
            )

        silver_temporary_path.replace(silver_output_path)
        logger.info('%s', f"Published: {silver_output_path} ({saved_count} rows)")
    finally:
        connection.execute(f"DROP VIEW IF EXISTS {quoted_saved_view}")
        connection.execute(f"DROP VIEW IF EXISTS {quoted_expected_view}")

# Preserve existing imports while callers migrate to the generic name.
publish_silver = publish_parquet

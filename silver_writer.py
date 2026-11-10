from pathlib import Path
import uuid

import duckdb


def publish_silver(
    connection: duckdb.DuckDBPyConnection,
    converted: duckdb.DuckDBPyRelation,
    silver_output_path: Path,
    source_view: str = "silver_pit_stops",
    *,
    verbose: bool = False,
) -> None:
    silver_output_path.parent.mkdir(parents=True, exist_ok=True)
    run_id = uuid.uuid4().hex
    silver_temporary_path = silver_output_path.with_name(
        f"{silver_output_path.stem}.{run_id}.tmp.parquet"
    )
    if verbose:
        print("Temporary publication path:", silver_temporary_path)

    converted.write_parquet(str(silver_temporary_path))

    saved_silver = connection.read_parquet(str(silver_temporary_path))
    saved_silver.create_view("saved_silver_pit_stops")

    expected_count = converted.count("*").fetchone()[0]
    saved_count = saved_silver.count("*").fetchone()[0]

    if saved_count != expected_count:
        raise ValueError("Silver rejected: row count mismatch")

    quoted_source_view = '"' + source_view.replace('"', '""') + '"'

    missing_rows = connection.sql(f"""
        SELECT * FROM {quoted_source_view}
        EXCEPT ALL
        SELECT * FROM saved_silver_pit_stops
    """).fetchall()

    if missing_rows:
        raise ValueError("Silver rejected: saved content differs")

    silver_temporary_path.replace(silver_output_path)
    print(f"Published: {silver_output_path} ({saved_count} rows)")

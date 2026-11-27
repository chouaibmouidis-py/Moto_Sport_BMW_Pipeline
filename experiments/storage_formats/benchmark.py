"""Local synthetic storage comparison; never changes pipeline outputs.

OS caches are not flushed. Scans run after writing and validation, so they are
warm/repeated workload observations, not cold-storage measurements.
"""

import argparse
import json
import logging
import platform
import statistics
import tempfile
from pathlib import Path

import duckdb

from moto_sport_bmw_pipeline.timing import measure_duration

logger = logging.getLogger(__name__)


def run_benchmark(*, rows, pairs, directory, extension_directory):
    if rows <= 0 or pairs <= 0:
        raise ValueError("rows and pairs must be positive")
    directory = Path(directory)
    directory.mkdir(parents=True, exist_ok=True)
    measurements = []
    with duckdb.connect(
        config={
            "extension_directory": str(extension_directory),
            "threads": 2,
            "memory_limit": "512MB",
        }
    ) as connection:
        connection.execute("LOAD vortex")
        connection.execute(
            """
            CREATE TEMP TABLE source AS
            SELECT i AS entry_id,
                lpad(CAST(i % 100 AS VARCHAR), 2, '0') AS car_number,
                CASE WHEN i % 7 = 0 THEN NULL
                     ELSE 150.0 + (i % 1000) / 10.0 END::DOUBLE AS speed,
                CASE WHEN i % 11 = 0 THEN NULL ELSE ' BMW ' END AS team_raw
            FROM range(?) t(i)
        """,
            [rows],
        )
        # Initialize both writers before recording repeated measurements.
        for fmt in ("parquet", "vortex"):
            warmup = directory / f"warmup.{fmt}"
            connection.execute(f"COPY source TO ? (FORMAT {fmt})", [str(warmup)])
            warmup.unlink()
        for pair in range(pairs):
            order = ("parquet", "vortex") if pair % 2 == 0 else ("vortex", "parquet")
            for position, fmt in enumerate(order):
                path = directory / f"pair-{pair}.{fmt}"
                _, write_seconds = measure_duration(
                    connection.execute,
                    f"COPY source TO ? (FORMAT {fmt})",
                    [str(path)],
                )
                try:
                    saved = connection.sql(
                        f"SELECT * FROM read_{fmt}(?)", params=[str(path)]
                    )
                    saved.create_view("saved", replace=True)
                    if (
                        saved.columns != connection.table("source").columns
                        or saved.types != connection.table("source").types
                    ):
                        raise ValueError(f"Schema differs: {fmt}")
                    differences = connection.sql("""
                        SELECT count(*) FROM (
                            (SELECT * FROM source EXCEPT ALL SELECT * FROM saved)
                            UNION ALL
                            (SELECT * FROM saved EXCEPT ALL SELECT * FROM source)
                        )
                    """).fetchone()[0]
                    if differences:
                        raise ValueError(f"Content differs: {fmt}")
                    # Aggregations consume column values without fetching all rows into Python.
                    _, scan_seconds = measure_duration(
                        lambda: connection.sql(
                            "SELECT sum(hash(entry_id, car_number, speed, team_raw)) FROM saved"
                        ).fetchone()
                    )
                    _, filter_seconds = measure_duration(
                        lambda: connection.sql(
                            "SELECT sum(speed) FROM saved WHERE entry_id % 100 = 0"
                        ).fetchone()
                    )
                    record = dict(
                        pair=pair,
                        position=position,
                        format=fmt,
                        rows=rows,
                        write_seconds=write_seconds,
                        scan_seconds=scan_seconds,
                        filter_seconds=filter_seconds,
                        size_bytes=path.stat().st_size,
                        content_verified=True,
                    )
                    measurements.append(record)
                    logger.info("%s", record)
                finally:
                    path.unlink(missing_ok=True)
    summary = {}
    for fmt in ("parquet", "vortex"):
        records = [record for record in measurements if record["format"] == fmt]
        summary[fmt] = {
            key: statistics.median(record[key] for record in records)
            for key in ("write_seconds", "scan_seconds", "filter_seconds", "size_bytes")
        }
    return dict(
        duckdb=duckdb.__version__,
        platform=platform.platform(),
        rows=rows,
        pairs=pairs,
        threads=2,
        memory_limit="512MB",
        cache_policy="writers warmed; scans after validation; OS cache uncontrolled",
        parquet_compression="DuckDB default",
        measurements=measurements,
        summary=summary,
    )


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--rows", type=int, default=100_000)
    parser.add_argument("--pairs", type=int, default=6)
    parser.add_argument(
        "--extension-directory", default="/private/tmp/bmw-vortex-extensions"
    )
    parser.add_argument("--report", type=Path, required=True)
    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    with tempfile.TemporaryDirectory(prefix="bmw-storage-benchmark-") as directory:
        report = run_benchmark(
            rows=args.rows,
            pairs=args.pairs,
            directory=directory,
            extension_directory=args.extension_directory,
        )
    args.report.write_text(json.dumps(report, indent=2), encoding="utf-8")
    logger.info("Medians: %s", report["summary"])
    logger.info("Report: %s", args.report)


if __name__ == "__main__":
    main()

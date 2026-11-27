"""Qualify real local Raw documents in temporary Bronze files; never activate runs."""

import argparse
import hashlib
import json
import logging
import platform
import statistics
import sys
import tempfile
from pathlib import Path

import duckdb

from moto_sport_bmw_pipeline import bronze, source_loading
from moto_sport_bmw_pipeline.bronze_storage import publish_bronze, read_bronze
from moto_sport_bmw_pipeline.timing import measure_duration

logger = logging.getLogger(__name__)


def _fingerprint(path):
    with path.open("rb") as file:
        return hashlib.file_digest(file, "sha256").hexdigest()


def _protected_snapshot(project):
    paths = [
        path
        for name in ("raw", "bronze")
        for path in (project / "data" / name).rglob("*")
        if path.is_file()
    ]
    paths.extend(
        path
        for path in (
            project / "data/current.json",
            project / "data/processing/current.json",
            project / "data/gold/current.json",
        )
        if path.is_file()
    )
    return {path.relative_to(project).as_posix(): _fingerprint(path) for path in paths}


def qualify_source(project, source, work, extension_directory, *, pairs=4):
    if pairs < 1:
        raise ValueError("pairs must be positive")
    raw = project / "data/raw" / source["source_id"] / source["filename"]
    original_hash = _fingerprint(raw)
    if source.get("expected_sha256") and source["expected_sha256"] != original_hash:
        raise ValueError(f"Raw fingerprint mismatch: {source['source_id']}")
    directory = work / "data/bronze" / source["source_id"]
    directory.mkdir(parents=True, exist_ok=True)
    json_columns = ()
    key = (source["document_type"], source["format"])
    if source["format"] == "json":
        json_columns = (
            ("session", "fastest_lap", "classification")
            if key[0] == "classification"
            else ("session", "pit_stop_analysis")
        )
    builders = {
        ("classification", "json"): bronze.build_classification_document,
        ("pit_stops", "json"): bronze.build_document,
        ("classification", "csv"): bronze.build_classification_csv,
        ("pit_stops", "pdf"): bronze.build_pdf_pit_stop_bronze,
    }
    initial = {}
    measurements = []
    paths = {fmt: directory / f"document.{fmt}" for fmt in ("parquet", "vortex")}
    config = {
        "extension_directory": str(extension_directory),
        "threads": 2,
        "memory_limit": "512MB",
        "autoload_known_extensions": False,
        "autoinstall_known_extensions": False,
    }
    try:
        for fmt, path in paths.items():
            args = (
                (raw, path, source["source_id"])
                if key == ("pit_stops", "pdf")
                else (raw, path)
            )
            _, initial[fmt] = measure_duration(
                builders[key], *args, extension_directory=extension_directory
            )
        with duckdb.connect(config=config) as connection:
            expected = read_bronze(
                connection, paths["parquet"], json_columns=json_columns
            )
            saved = read_bronze(connection, paths["vortex"], json_columns=json_columns)
            if expected.columns != saved.columns or expected.types != saved.types:
                raise ValueError(f"Schema differs: {source['source_id']}")
            expected.create_view("expected")
            saved.create_view("saved")
            differences = connection.sql("""
                SELECT count(*) FROM (
                    (SELECT * FROM expected EXCEPT ALL SELECT * FROM saved)
                    UNION ALL
                    (SELECT * FROM saved EXCEPT ALL SELECT * FROM expected)
                )
            """).fetchone()[0]
            if differences:
                raise ValueError(f"Content differs: {source['source_id']}")
            connection.execute("CREATE TEMP TABLE extracted AS SELECT * FROM expected")
            document = connection.table("extracted")
            rows = document.count("*").fetchone()[0]
            expected_types = [str(dtype) for dtype in document.types]
            extension_version = connection.sql(
                "SELECT extension_version FROM duckdb_extensions() WHERE extension_name='vortex'"
            ).fetchone()[0]

            if key == ("classification", "json"):
                source_loading.load_classification_bronze(
                    connection, paths["vortex"], source["source_id"]
                )
                table = "bronze_classification"
            elif key == ("pit_stops", "json"):
                source_loading.load_pit_stop_file(
                    connection, paths["vortex"], source["source_id"]
                )
                table = "bronze_document"
            elif key == ("classification", "csv"):
                source_loading.load_classification_csv_bronze(
                    connection, paths["vortex"], source["source_id"]
                )
                table = "bronze_classification_csv"
            else:
                source_loading.load_pdf_pit_stop_bronze(connection, paths["vortex"])
                table = "bronze_pdf_pit_stops"
            loaded = connection.table(table)
            if loaded.count("*").fetchone()[0] != rows:
                raise ValueError("Loaded Silver input row count differs")
            selected = loaded.project(
                ", ".join(
                    '"' + name.replace('"', '""') + '"' for name in document.columns
                )
            )
            if selected.types != document.types:
                raise ValueError("Loaded Silver input schema differs")
            selected.create_view("loaded_fields")
            if connection.sql("""
                SELECT count(*) FROM (
                    (SELECT * FROM extracted EXCEPT ALL SELECT * FROM loaded_fields)
                    UNION ALL
                    (SELECT * FROM loaded_fields EXCEPT ALL SELECT * FROM extracted)
                )
            """).fetchone()[0]:
                raise ValueError("Loaded Silver input content differs")
            if rows:
                provenance = (
                    loaded.project("source_id, bronze_sha256").distinct().fetchall()
                )
                if provenance != [(source["source_id"], _fingerprint(paths["vortex"]))]:
                    raise ValueError("Loaded Silver input provenance differs")

            # Initialize both storage writers on the same materialized input.
            for fmt in paths:
                warmup = directory / f"warmup.{fmt}"
                try:
                    publish_bronze(connection, document, warmup)
                finally:
                    warmup.unlink(missing_ok=True)
            columns = ", ".join(
                '"' + name.replace('"', '""') + '"' for name in document.columns
            )
            for pair in range(pairs):
                order = (
                    ("parquet", "vortex") if pair % 2 == 0 else ("vortex", "parquet")
                )
                for position, fmt in enumerate(order):
                    sample = directory / f"sample.{fmt}"
                    try:
                        _, seconds = measure_duration(
                            publish_bronze, connection, document, sample
                        )
                        relation = read_bronze(
                            connection, sample, json_columns=json_columns
                        )
                        relation.create_view("scan_input", replace=True)
                        _, scan_seconds = measure_duration(
                            lambda: connection.sql(
                                f"SELECT sum(hash({columns})) FROM scan_input"
                            ).fetchone()
                        )
                        measurements.append(
                            dict(
                                pair=pair,
                                position=position,
                                format=fmt,
                                publish_seconds=seconds,
                                scan_seconds=scan_seconds,
                                size_bytes=sample.stat().st_size,
                            )
                        )
                    finally:
                        sample.unlink(missing_ok=True)
            summary = {
                fmt: {
                    metric: statistics.median(
                        record[metric]
                        for record in measurements
                        if record["format"] == fmt
                    )
                    for metric in ("publish_seconds", "scan_seconds", "size_bytes")
                }
                for fmt in paths
            }
            schema = dict(zip(document.columns, expected_types))
        if _fingerprint(raw) != original_hash:
            raise ValueError(f"Source changed: {source['source_id']}")
        return dict(
            source_id=source["source_id"],
            document_type=key[0],
            source_format=key[1],
            raw_sha256=original_hash,
            raw_size_bytes=raw.stat().st_size,
            rows=rows,
            schema=schema,
            extension_version=extension_version,
            content_verified=True,
            silver_input_verified=True,
            source_unchanged=True,
            initial_build_seconds=initial,
            measurements=measurements,
            summary=summary,
        )
    finally:
        for path in paths.values():
            path.unlink(missing_ok=True)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project", type=Path, default=Path.cwd())
    parser.add_argument("--extension-directory", type=Path, required=True)
    parser.add_argument("--pairs", type=int, default=4)
    parser.add_argument("--report", type=Path, required=True)
    args = parser.parse_args(argv)
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    sources = [
        source
        for source in json.loads(
            (args.project / "config/sources.json").read_text(encoding="utf-8")
        )["documents"]
        if source.get("enabled")
    ]
    protected_before = _protected_snapshot(args.project)
    records = []
    with tempfile.TemporaryDirectory(prefix="bmw-real-bronze-") as directory:
        for index, source in enumerate(sources, 1):
            logger.info(
                "Qualifying %s/%s: %s", index, len(sources), source["source_id"]
            )
            records.append(
                qualify_source(
                    args.project,
                    source,
                    Path(directory),
                    args.extension_directory,
                    pairs=args.pairs,
                )
            )
    if _protected_snapshot(args.project) != protected_before:
        raise ValueError(
            "Qualification rejected: existing inputs or active references changed"
        )
    report = dict(
        duckdb=duckdb.__version__,
        python=sys.version,
        platform=platform.platform(),
        pairs=args.pairs,
        repeated_measurement_threads=2,
        repeated_measurement_memory_limit="512MB",
        protected_files_verified=len(protected_before),
        protocol="Initial builds: extraction plus validation, one observation each; repeated publication: same materialized input, warmed writers, alternating order; scans after validation, OS cache uncontrolled; no RSS measurement",
        records=records,
    )
    args.report.write_text(json.dumps(report, indent=2), encoding="utf-8")
    logger.info("Qualified %s documents; report=%s", len(records), args.report)


if __name__ == "__main__":
    main()

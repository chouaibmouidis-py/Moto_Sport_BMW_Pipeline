"""Compare a complete PDF stored as one BLOB, without extracting its tables."""

import argparse
import hashlib
import json
import logging
import platform
import statistics
import tempfile
from pathlib import Path

import duckdb
from pypdf import PdfReader

from experiments.storage_formats.bronze_adapter import read_bronze
from moto_sport_bmw_pipeline.timing import measure_duration

logger = logging.getLogger(__name__)


def benchmark_pdf(source_path, extension_directory, *, pairs=4):
    if pairs <= 0:
        raise ValueError("pairs must be positive")
    with source_path.open("rb") as file:
        sha256 = hashlib.file_digest(file, "sha256").hexdigest()
    reader = PdfReader(source_path)
    pages = len(reader.pages)
    del reader
    config = {
        "extension_directory": str(extension_directory),
        "threads": 2,
        "memory_limit": "2GB",
        "autoload_known_extensions": False,
        "autoinstall_known_extensions": False,
    }
    measurements = []
    with tempfile.TemporaryDirectory(prefix="bmw-pdf-blob-") as temporary:
        with duckdb.connect(config=config) as connection:
            connection.execute("LOAD vortex")
            version = connection.sql(
                "SELECT extension_version FROM duckdb_extensions() WHERE extension_name='vortex'"
            ).fetchone()[0]
            connection.execute(
                "CREATE TEMP TABLE payload AS SELECT content FROM read_blob(?)",
                [str(source_path)],
            )
            if connection.sql(
                "SELECT octet_length(content), sha256(content) FROM payload"
            ).fetchone() != (source_path.stat().st_size, sha256):
                raise ValueError("Input BLOB differs from source PDF")
            for fmt in ("parquet", "vortex"):
                path = Path(temporary) / f"warmup.{fmt}"
                connection.execute(f"COPY payload TO ? (FORMAT {fmt})", [str(path)])
                path.unlink()
            for pair in range(pairs):
                order = (
                    ("parquet", "vortex") if pair % 2 == 0 else ("vortex", "parquet")
                )
                for position, fmt in enumerate(order):
                    path = Path(temporary) / f"document.{fmt}"
                    try:
                        _, elapsed = measure_duration(
                            connection.execute,
                            f"COPY payload TO ? (FORMAT {fmt})",
                            [str(path)],
                        )
                        saved = read_bronze(connection, path)
                        if saved.columns != ["content"] or [
                            str(dtype) for dtype in saved.types
                        ] != ["BLOB"]:
                            raise ValueError(f"BLOB schema changed: {fmt}")
                        saved.create_view("saved", replace=True)
                        count, length, digest = connection.sql(
                            "SELECT count(*), max(octet_length(content)), max(sha256(content)) FROM saved"
                        ).fetchone()
                        if (count, length, digest) != (
                            1,
                            source_path.stat().st_size,
                            sha256,
                        ):
                            raise ValueError(f"BLOB integrity mismatch: {fmt}")
                        if connection.sql(
                            "SELECT count(*) FROM saved s CROSS JOIN payload p WHERE s.content IS DISTINCT FROM p.content"
                        ).fetchone()[0]:
                            raise ValueError(f"BLOB bytes differ: {fmt}")
                        record = dict(
                            pair=pair,
                            position=position,
                            format=fmt,
                            size_bytes=path.stat().st_size,
                            write_seconds=elapsed,
                            exact_match=True,
                        )
                        measurements.append(record)
                        logger.info("%s", record)
                    finally:
                        path.unlink(missing_ok=True)
    with source_path.open("rb") as file:
        if hashlib.file_digest(file, "sha256").hexdigest() != sha256:
            raise ValueError("Source PDF changed during benchmark")
    return dict(
        input_bytes=source_path.stat().st_size,
        sha256=sha256,
        pages=pages,
        schema={"content": "BLOB"},
        rows=1,
        duckdb=duckdb.__version__,
        vortex_version=version,
        platform=platform.platform(),
        pairs=pairs,
        threads=2,
        memory_limit="2GB",
        settings="Writer defaults; warmed writers; OS cache uncontrolled; no RSS measurement",
        measurements=measurements,
        summary={
            fmt: {
                key: statistics.median(
                    record[key] for record in measurements if record["format"] == fmt
                )
                for key in ("size_bytes", "write_seconds")
            }
            for fmt in ("parquet", "vortex")
        },
    )


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("pdf", type=Path)
    parser.add_argument("--extension-directory", type=Path, required=True)
    parser.add_argument("--pairs", type=int, default=4)
    parser.add_argument("--report", type=Path, required=True)
    parser.add_argument("--source-url")
    args = parser.parse_args(argv)
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    report = benchmark_pdf(args.pdf, args.extension_directory, pairs=args.pairs)
    report["source_url"] = args.source_url
    args.report.write_text(json.dumps(report, indent=2), encoding="utf-8")
    logger.info(
        "Input bytes: %s; summary: %s", report["input_bytes"], report["summary"]
    )


if __name__ == "__main__":
    main()

"""Verify raw PDF extraction provenance and failure-safe Bronze publication."""

import hashlib
from pathlib import Path
from unittest.mock import patch

import pytest

from moto_sport_bmw_pipeline.bronze import build_pdf_pit_stop_bronze
from moto_sport_bmw_pipeline.source_loading import load_pdf_pit_stop_bronze


def test_preserves_raw_duration_text_number_and_pdf_location(tmp_path, connection):
    source_line = "1 10:17:27.494 12:17:20.883 1:59:53.389 1:59:53.389"
    record = {
        "car_number": "04",
        "pit_number": 1,
        "pit_time_raw": "1:59:53.389",
        "page_number": 2,
        "column_number": 1,
        "block_line_number": 3,
        "source_line": source_line,
    }
    directory = tmp_path
    source = Path(directory) / "source.pdf"
    source.write_bytes(b"PDF extraction is mocked")
    output = Path(directory) / "bronze" / "document.parquet"
    with patch(
        "moto_sport_bmw_pipeline.bronze.iter_stops",
        return_value=[record],
    ):
        result = build_pdf_pit_stop_bronze(source, output, "test-source")
    assert result == output
    saved = connection.read_parquet(str(output))
    assert saved.fetchall() == [
        (
            "test-source",
            hashlib.sha256(source.read_bytes()).hexdigest(),
            "04",
            1,
            "1:59:53.389",
            2,
            1,
            3,
            source_line,
        )
    ]
    assert "pit_time_seconds" not in saved.columns
    load_pdf_pit_stop_bronze(connection, output)

    loaded = connection.table("bronze_pdf_pit_stops")
    assert len(loaded.columns) == 10

    provenance = loaded.project("source_id, pdf_sha256, bronze_sha256").fetchall()

    assert provenance == [
        (
            "test-source",
            hashlib.sha256(source.read_bytes()).hexdigest(),
            hashlib.sha256(output.read_bytes()).hexdigest(),
        )
    ]
    assert source.read_bytes() == b"PDF extraction is mocked"


def test_parser_failure_preserves_previous_output(tmp_path):
    directory = tmp_path
    source = Path(directory) / "source.pdf"
    output = Path(directory) / "document.parquet"
    source.write_bytes(b"PDF extraction is mocked")
    output.write_bytes(b"previous version")
    with patch(
        "moto_sport_bmw_pipeline.bronze.iter_stops",
        side_effect=ValueError("unreadable stop row"),
    ):
        with pytest.raises(ValueError, match="unreadable stop row"):
            build_pdf_pit_stop_bronze(source, output, "test-source")
    assert output.read_bytes() == b"previous version"


def test_write_failure_preserves_previous_output(tmp_path):
    directory = tmp_path
    source = Path(directory) / "source.pdf"
    output = Path(directory) / "document.parquet"
    source.write_bytes(b"PDF extraction is mocked")
    output.write_bytes(b"previous version")
    with (
        patch(
            "moto_sport_bmw_pipeline.bronze.iter_stops",
            return_value=[],
        ),
        patch(
            "duckdb.DuckDBPyRelation.write_parquet",
            side_effect=OSError("Simulated write failure"),
        ),
    ):
        with pytest.raises(OSError, match="Simulated write failure"):
            build_pdf_pit_stop_bronze(source, output, "test-source")
    assert output.read_bytes() == b"previous version"


def test_empty_extraction_keeps_typed_schema_without_inventing_stops(
    tmp_path, connection
):
    directory = tmp_path
    source = Path(directory) / "source.pdf"
    output = Path(directory) / "document.parquet"
    source.write_bytes(b"PDF extraction is mocked")
    with patch(
        "moto_sport_bmw_pipeline.bronze.iter_stops",
        return_value=[],
    ):
        build_pdf_pit_stop_bronze(source, output, "test-source")
    saved = connection.read_parquet(str(output))
    assert saved.fetchall() == []
    assert saved.columns == [
        "source_id",
        "pdf_sha256",
        "car_number",
        "pit_number",
        "pit_time_raw",
        "page_number",
        "column_number",
        "block_line_number",
        "source_line",
    ]


def test_source_change_during_extraction_preserves_previous_output(tmp_path):
    directory = tmp_path
    source = Path(directory) / "source.pdf"
    output = Path(directory) / "document.parquet"
    source.write_bytes(b"first version")
    output.write_bytes(b"previous version")

    def change_source(path):
        path.write_bytes(b"second version")
        return []

    with patch(
        "moto_sport_bmw_pipeline.bronze.iter_stops",
        side_effect=change_source,
    ):
        with pytest.raises(ValueError, match="source changed during extraction"):
            build_pdf_pit_stop_bronze(source, output, "test-source")
    assert output.read_bytes() == b"previous version"

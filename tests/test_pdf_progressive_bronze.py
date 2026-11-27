from pathlib import Path
from unittest.mock import Mock

import duckdb
import pytest
from pypdf import PdfWriter

from memory_probe import measure_python_memory
from moto_sport_bmw_pipeline import bronze, pdf_parser


def record(number):
    return {
        "car_number": "04",
        "pit_number": number,
        "pit_time_raw": "1:02.000",
        "page_number": 1,
        "column_number": 1,
        "block_line_number": number,
        "source_line": f"{number:08d} " + "x" * 512,
    }


def test_pdf_hashes_do_not_read_complete_file_into_python(tmp_path, monkeypatch):
    source = tmp_path / "source.pdf"
    writer = PdfWriter()
    writer.add_blank_page(width=100, height=100)
    writer.write(source)

    def forbidden(path):
        raise AssertionError("Full PDF read_bytes is forbidden")

    with monkeypatch.context() as patcher:
        patcher.setattr(Path, "read_bytes", forbidden)
        bronze.build_pdf_pit_stop_bronze(
            source, tmp_path / "document.parquet", "source-a"
        )


def test_pdf_iterator_reads_one_page_and_closes_stream_on_early_stop(
    tmp_path, monkeypatch
):
    source = tmp_path / "source.pdf"
    source.write_bytes(b"reader is simulated")
    visited, streams = [], []

    class Page:
        def __init__(self, number):
            self.number = number

        def extract_text(self, *, visitor_text):
            visited.append(self.number)
            matrix = [1, 0, 0, 1, 0, 0]
            if self.number == 1:
                visitor_text("04", matrix, [1, 0, 0, 1, 65.05, 600], None, 18)
            text = f"{self.number} 10:00:00.000 10:01:02.000 1:02.000 1:02.000"
            visitor_text(text, matrix, [1, 0, 0, 1, 60.45, 590], None, 9)

    def reader(stream):
        assert hasattr(stream, "read"), (
            "Pass a stream, not a filename that pypdf copies"
        )
        streams.append(stream)
        return Mock(pages=[Page(1), Page(2)])

    monkeypatch.setattr(pdf_parser, "PdfReader", reader)
    rows = pdf_parser.iter_stops(source)
    assert next(rows)["pit_number"] == 1
    assert visited == [1]
    rows.close()
    assert streams[0].closed


def test_parser_preserves_sequence_across_lazy_blocks():
    def blocks():
        yield 1, 1, "04\n1 10:00:00.000 10:01:02.000 1:02.000 1:02.000"
        yield 2, 1, "3 10:00:00.000 10:01:02.000 1:02.000 1:02.000"

    rows = pdf_parser.iter_parse_stop_blocks(blocks())
    assert next(rows)["pit_number"] == 1
    with pytest.raises(ValueError, match="expected 2"):
        next(rows)


def test_first_batch_is_inserted_before_requesting_next_record(tmp_path, monkeypatch):
    source = tmp_path / "source.pdf"
    source.write_bytes(b"PDF extraction is simulated")
    connections, batch_lengths = [], []
    original_connect = duckdb.connect
    original_insert = duckdb.DuckDBPyConnection.executemany

    def connect(*args, **kwargs):
        connection = original_connect(*args, **kwargs)
        connections.append(connection)
        return connection

    def insert(connection, query, parameters):
        batch_lengths.append(len(parameters))
        return original_insert(connection, query, parameters)

    def rows(path):
        for number in range(1, 6):
            if number == 3:
                assert (
                    connections[-1]
                    .table("bronze_pdf_pit_stops")
                    .count("*")
                    .fetchone()[0]
                    == 2
                )
            yield record(number)

    monkeypatch.setattr(bronze.duckdb, "connect", connect)
    monkeypatch.setattr(duckdb.DuckDBPyConnection, "executemany", insert)
    monkeypatch.setattr(bronze, "iter_stops", rows)
    output = tmp_path / "document.parquet"
    bronze.build_pdf_pit_stop_bronze(source, output, "source-a", batch_size=2)
    assert batch_lengths == [2, 2, 1]
    with original_connect() as connection:
        assert connection.read_parquet(str(output)).count("*").fetchone()[0] == 5


def test_late_extraction_failure_preserves_previous_output_and_closes_iterator(
    tmp_path, monkeypatch
):
    source = tmp_path / "source.pdf"
    source.write_bytes(b"PDF fixture")
    output = tmp_path / "document.parquet"
    output.write_bytes(b"previous")
    closed = []

    def rows(path):
        try:
            yield record(1)
            yield record(2)
            raise ValueError("Late PDF parse failure")
        finally:
            closed.append(True)

    monkeypatch.setattr(bronze, "iter_stops", rows)
    with pytest.raises(ValueError, match="Late PDF parse failure"):
        bronze.build_pdf_pit_stop_bronze(source, output, "source-a", batch_size=2)
    assert closed == [True]
    assert output.read_bytes() == b"previous"
    assert set(tmp_path.iterdir()) == {source, output}


def test_insert_failure_closes_retained_iterator(tmp_path, monkeypatch):
    source = tmp_path / "source.pdf"
    source.write_bytes(b"PDF fixture")
    output = tmp_path / "document.parquet"
    output.write_bytes(b"previous")
    streams = []

    def rows():
        with source.open("rb") as stream:
            streams.append(stream)
            for number in range(1, 10):
                yield record(number)

    iterator = rows()
    monkeypatch.setattr(bronze, "iter_stops", lambda path: iterator)

    def fail_insert(*args, **kwargs):
        raise OSError("Simulated insert failure")

    monkeypatch.setattr(duckdb.DuckDBPyConnection, "executemany", fail_insert)
    with pytest.raises(OSError, match="Simulated insert failure"):
        bronze.build_pdf_pit_stop_bronze(source, output, "source-a", batch_size=2)
    assert streams[0].closed
    assert output.read_bytes() == b"previous"


def test_source_change_during_write_preserves_previous_pdf_bronze(
    tmp_path, monkeypatch
):
    source = tmp_path / "source.pdf"
    source.write_bytes(b"PDF fixture")
    output = tmp_path / "document.parquet"
    output.write_bytes(b"previous")
    monkeypatch.setattr(bronze, "iter_stops", lambda path: iter([record(1)]))
    original_write = duckdb.DuckDBPyRelation.write_parquet

    def change_source(document, path):
        result = original_write(document, path)
        source.write_bytes(b"changed PDF")
        return result

    monkeypatch.setattr(duckdb.DuckDBPyRelation, "write_parquet", change_source)
    with pytest.raises(ValueError, match="source changed during publication"):
        bronze.build_pdf_pit_stop_bronze(source, output, "source-a", batch_size=2)
    assert output.read_bytes() == b"previous"
    assert set(tmp_path.iterdir()) == {source, output}


@pytest.mark.parametrize("batch_size", [0, -1, True, False, 1.5, "2", None])
def test_invalid_batch_size_fails_before_reading_source(tmp_path, batch_size):
    with pytest.raises(ValueError, match="batch_size must be a positive integer"):
        bronze.build_pdf_pit_stop_bronze(
            tmp_path / "absent.pdf",
            tmp_path / "document.parquet",
            "source-a",
            batch_size=batch_size,
        )
    assert not list(tmp_path.iterdir())


@pytest.mark.parametrize("count", [100, 5_000])
def test_pdf_batch_python_peak_stays_below_two_mib(tmp_path, monkeypatch, count):
    source = tmp_path / "source.pdf"
    source.write_bytes(b"PDF fixture")
    monkeypatch.setattr(
        bronze, "iter_stops", lambda path: (record(i) for i in range(1, 11))
    )
    bronze.build_pdf_pit_stop_bronze(
        source, tmp_path / "warm.parquet", "source-a", batch_size=64
    )
    monkeypatch.setattr(
        bronze, "iter_stops", lambda path: (record(i) for i in range(1, count + 1))
    )
    result = measure_python_memory(
        bronze.build_pdf_pit_stop_bronze,
        source,
        tmp_path / "document.parquet",
        "source-a",
        batch_size=64,
    )
    assert result["peak_bytes"] < 2 * 1024 * 1024
    with duckdb.connect() as connection:
        assert (
            connection.read_parquet(str(tmp_path / "document.parquet"))
            .count("*")
            .fetchone()[0]
            == count
        )


def test_pdf_memory_guard_detects_retained_records(tmp_path, monkeypatch):
    source = tmp_path / "source.pdf"
    source.write_bytes(b"PDF fixture")
    retained = []

    def rows(path):
        for number in range(1, 5_001):
            row = record(number)
            retained.append(row)
            yield row

    monkeypatch.setattr(bronze, "iter_stops", rows)
    result = measure_python_memory(
        bronze.build_pdf_pit_stop_bronze,
        source,
        tmp_path / "document.parquet",
        "source-a",
        batch_size=64,
    )
    assert len(retained) == 5_000
    assert result["peak_bytes"] > 2 * 1024 * 1024

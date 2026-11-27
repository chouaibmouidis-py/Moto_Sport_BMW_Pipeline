import hashlib
from pathlib import Path

import duckdb
import pytest
from vortex_support import VORTEX_EXTENSION_DIRECTORY

from experiments.storage_formats import bronze_adapter
from moto_sport_bmw_pipeline import bronze


@pytest.mark.parametrize(
    "kind, storage_format",
    [
        ("pit_json", "vortex"),
        ("csv", "vortex"),
        ("pdf", "vortex"),
    ],
)
def test_source_loaders_share_storage_reader(
    tmp_path, monkeypatch, storage_format, kind
):
    source = tmp_path / "source"
    output = tmp_path / "data/bronze/source-a" / f"document.{storage_format}"
    extension_directory = Path(str(VORTEX_EXTENSION_DIRECTORY))
    options = {"extension_directory": extension_directory}
    if kind == "pit_json":
        source.write_text(
            '{"session":{},"pit_stop_analysis":[{"number":"04","drivers":[],"pit_stops":[]}]}',
            encoding="utf-8",
        )
        bronze_adapter.build_document(source, output, **options)
    elif kind == "csv":
        source.write_text("NUMBER;VEHICLE\n 04 ; BMW \n", encoding="utf-8")
        bronze_adapter.build_classification_csv(source, output, **options)
    else:
        source.write_bytes(b"PDF fixture")
        monkeypatch.setattr(
            bronze,
            "iter_stops",
            lambda path: [
                {
                    "car_number": "04",
                    "pit_number": 1,
                    "pit_time_raw": "1:02.000",
                    "page_number": 1,
                    "column_number": 2,
                    "block_line_number": 3,
                    "source_line": "raw PDF line",
                }
            ],
        )
        bronze_adapter.build_pdf_pit_stop_bronze(source, output, "source-a", **options)
    expected_hash = hashlib.sha256(output.read_bytes()).hexdigest()
    with duckdb.connect(
        config={
            "extension_directory": str(extension_directory),
            "autoload_known_extensions": False,
            "autoinstall_known_extensions": False,
        }
    ) as connection:
        if kind == "pit_json":
            bronze_adapter.load_pit_stop_file(connection, output, "source-a")
            row = connection.sql(
                "SELECT json_extract_string(pit_stop_analysis, '$[0].number'), source_id, bronze_sha256 FROM bronze_document"
            ).fetchone()
            assert [
                str(dtype) for dtype in connection.table("bronze_document").types
            ] == ["JSON", "JSON", "VARCHAR", "VARCHAR"]
            assert row == ("04", "source-a", expected_hash)
        elif kind == "csv":
            bronze_adapter.load_classification_csv_bronze(
                connection, output, "source-a"
            )
            assert connection.sql(
                "SELECT NUMBER, VEHICLE, source_id, bronze_sha256 FROM bronze_classification_csv"
            ).fetchone() == (" 04 ", " BMW ", "source-a", expected_hash)
        else:
            bronze_adapter.load_pdf_pit_stop_bronze(connection, output)
            assert connection.sql(
                "SELECT car_number, pit_time_raw, source_line, source_id, bronze_sha256, pdf_sha256 FROM bronze_pdf_pit_stops"
            ).fetchone() == (
                "04",
                "1:02.000",
                "raw PDF line",
                "source-a",
                expected_hash,
                hashlib.sha256(b"PDF fixture").hexdigest(),
            )

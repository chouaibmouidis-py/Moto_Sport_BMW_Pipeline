import hashlib
import json
from pathlib import Path

import duckdb
import pytest

from moto_sport_bmw_pipeline import bronze
from moto_sport_bmw_pipeline.bronze import build_classification_document
from moto_sport_bmw_pipeline.source_loading import (
    load_classification_sources,
)


def test_loads_two_classification_sources(tmp_path):
    storage_format = "parquet"

    cases = [
        ("source-a", "04"),
        ("source-b", "24"),
    ]
    sources = []
    expected_rows = []

    for source_id, car_number in cases:
        source_path = tmp_path / f"{source_id}.json"
        bronze_path = (
            tmp_path / "data" / "bronze" / source_id / f"document.{storage_format}"
        )
        document = {
            "session": {},
            "fastest_lap": {},
            "classification": [{"number": car_number}],
        }
        source_path.write_text(json.dumps(document), encoding="utf-8")

        build_classification_document(
            source_path,
            bronze_path,
            extension_directory=Path("extensions"),
        )

        sources.append({"source_id": source_id})

        expected_sha256 = hashlib.sha256(bronze_path.read_bytes()).hexdigest()

        expected_rows.append((source_id, car_number, expected_sha256))

    with duckdb.connect(
        config={
            "extension_directory": str(Path("extensions")),
            "autoload_known_extensions": False,
            "autoinstall_known_extensions": False,
        }
    ) as connection:
        load_classification_sources(
            connection,
            sources,
            tmp_path,
        )

        rows = connection.sql("""
            SELECT
                source_id,
                json_extract_string(classification, '$[0].number') AS car_number,
                bronze_sha256
            FROM bronze_classification
            ORDER BY source_id
        """).fetchall()

    assert rows == expected_rows


@pytest.mark.parametrize("extension_directory", [None, Path("extensions")])
def test_routes_json_classification_to_parquet(
    tmp_path, monkeypatch, extension_directory
):

    source = {
        "source_id": "source-a",
        "document_type": "classification",
        "format": "json",
        "filename": "report.json",
    }
    calls = []

    def record_build(source_path, output_path, *, extension_directory=None):
        calls.append((source_path, output_path, extension_directory))

    monkeypatch.setattr(
        bronze,
        "build_classification_document",
        record_build,
    )

    result = bronze.build_source(
        tmp_path, source, extension_directory=extension_directory
    )

    expected_source = tmp_path / "data/raw/source-a/report.json"
    expected_output = tmp_path / "data/bronze/source-a/document.parquet"

    assert result == expected_output
    assert calls == [(expected_source, expected_output, extension_directory)]


def test_build_source_produces_loadable_parquet_classification(tmp_path):
    source = {
        "source_id": "source-a",
        "document_type": "classification",
        "format": "json",
        "filename": "report.json",
    }
    source_path = tmp_path / "data/raw/source-a/report.json"
    source_path.parent.mkdir(parents=True)
    document = {
        "session": {"event_name": "Test race"},
        "fastest_lap": {},
        "classification": [{"number": "04", "team": " BMW ", "position": None}],
    }
    source_path.write_text(json.dumps(document), encoding="utf-8")
    extension_directory = Path("extensions")

    output = bronze.build_source(
        tmp_path, source, extension_directory=extension_directory
    )

    assert output == tmp_path / "data/bronze/source-a/document.parquet"
    with duckdb.connect(
        config={
            "extension_directory": str(extension_directory),
            "autoload_known_extensions": False,
            "autoinstall_known_extensions": False,
        }
    ) as connection:
        load_classification_sources(connection, [source], tmp_path)
        row = connection.sql(
            "SELECT session, fastest_lap, classification, source_id, bronze_sha256 FROM bronze_classification"
        ).fetchone()
        assert [
            str(dtype) for dtype in connection.table("bronze_classification").types
        ] == [
            "JSON",
            "JSON",
            "JSON",
            "VARCHAR",
            "VARCHAR",
        ]
    assert [json.loads(value) for value in row[:3]] == [
        document["session"],
        document["fastest_lap"],
        document["classification"],
    ]
    assert row[3] == "source-a"
    assert row[4] == hashlib.sha256(output.read_bytes()).hexdigest()
    assert json.loads(source_path.read_text(encoding="utf-8")) == document
    assert {path.name for path in output.parent.iterdir()} == {"document.parquet"}


def test_production_bronze_does_not_require_vortex_installation(tmp_path):
    source = {
        "source_id": "source-a",
        "document_type": "classification",
        "format": "csv",
        "filename": "report.csv",
    }
    raw = tmp_path / "data/raw/source-a/report.csv"
    raw.parent.mkdir(parents=True)
    raw.write_text("NUMBER;VEHICLE\n04; BMW \n", encoding="utf-8")
    output = bronze.build_source(
        tmp_path, source, extension_directory=tmp_path / "empty-extensions"
    )
    assert output == tmp_path / "data/bronze/source-a/document.parquet"
    with duckdb.connect(
        config={
            "autoload_known_extensions": False,
            "autoinstall_known_extensions": False,
        }
    ) as connection:
        assert connection.read_parquet(str(output)).fetchall() == [("04", " BMW ")]
        assert not connection.sql(
            "SELECT loaded FROM duckdb_extensions() WHERE extension_name='vortex'"
        ).fetchone()[0]


def test_production_bronze_rejects_non_parquet_paths(tmp_path, connection):
    from moto_sport_bmw_pipeline.bronze_storage import publish_bronze, read_bronze

    output = tmp_path / "document.vortex"
    with pytest.raises(ValueError, match="Unexpected file format"):
        bronze.build_classification_document(tmp_path / "missing.json", output)
    with pytest.raises(ValueError, match="Unexpected file format"):
        publish_bronze(connection, connection.sql("SELECT 1 AS id"), output)
    with pytest.raises(ValueError, match="Unexpected file format"):
        read_bronze(connection, output)
    assert not output.exists()

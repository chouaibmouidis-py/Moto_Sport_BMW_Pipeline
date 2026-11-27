import json

import duckdb
import pytest
from vortex_support import VORTEX_EXTENSION_DIRECTORY

from memory_probe import measure_python_memory
from moto_sport_bmw_pipeline import bronze


@pytest.fixture(params=["classification", "pit_stops"])
def json_bronze_case(tmp_path, request):
    source = tmp_path / "source.json"
    if request.param == "classification":
        payload = {
            "session": {},
            "fastest_lap": {},
            "classification": [{"number": "04", "position": None}],
        }
        builder = bronze.build_classification_document
    else:
        payload = {
            "session": {},
            "pit_stop_analysis": [{"number": "04", "drivers": [], "pit_stops": []}],
        }
        builder = bronze.build_document
    source.write_text(json.dumps(payload), encoding="utf-8")
    return source, builder


@pytest.mark.parametrize("storage_format", ["parquet", "vortex"])
def test_json_publication_does_not_decode_or_fetch_documents_in_python(
    json_bronze_case, tmp_path, monkeypatch, storage_format
):
    source, builder = json_bronze_case
    output = tmp_path / f"document.{storage_format}"

    def forbidden(*args, **kwargs):
        raise AssertionError("Full JSON documents must stay inside DuckDB")

    with monkeypatch.context() as patcher:
        patcher.setattr(json, "load", forbidden)
        patcher.setattr(json, "loads", forbidden)
        patcher.setattr(duckdb.DuckDBPyRelation, "fetchall", forbidden)
        builder(source, output, extension_directory=VORTEX_EXTENSION_DIRECTORY)
    assert output.is_file()
    assert not list(tmp_path.glob("*.tmp.*"))


def test_json_source_change_during_write_is_rejected(
    json_bronze_case, tmp_path, monkeypatch
):
    source, builder = json_bronze_case
    output = tmp_path / "document.parquet"
    output.write_bytes(b"previous version")
    original_write = duckdb.DuckDBPyRelation.write_parquet

    def change_source(document, path):
        result = original_write(document, path)
        with source.open("ab") as file:
            file.write(b"\n")
        return result

    monkeypatch.setattr(duckdb.DuckDBPyRelation, "write_parquet", change_source)
    with pytest.raises(
        ValueError, match="Bronze rejected: source changed during publication"
    ):
        builder(source, output)
    assert output.read_bytes() == b"previous version"
    assert set(tmp_path.iterdir()) == {source, output}


@pytest.fixture(params=["classification", "pit_stop_analysis"])
def large_json_case(tmp_path, request):
    source = tmp_path / "large.json"
    root = request.param
    record = {"number": "04", "team": "BMW" * 64, "position": None}
    if root == "pit_stop_analysis":
        record.update(drivers=[], pit_stops=[])
    entry = json.dumps(record)
    with source.open("w", encoding="utf-8") as file:
        file.write('{"session":{},"fastest_lap":{},"' + root + '":[')
        for index in range(20_000):
            if index:
                file.write(",")
            file.write(entry)
        file.write("]}")
    builder = (
        bronze.build_classification_document
        if root == "classification"
        else bronze.build_document
    )
    return source, builder, root


def test_json_python_peak_stays_below_two_mib(large_json_case, tmp_path):
    source, builder, root = large_json_case
    warm = tmp_path / "warm.json"
    warm.write_text(
        json.dumps({"session": {}, "fastest_lap": {}, root: []}), encoding="utf-8"
    )
    builder(warm, tmp_path / "warm.parquet")
    measurement = measure_python_memory(
        builder,
        source,
        tmp_path / "large.parquet",
    )
    assert measurement["peak_bytes"] < 2 * 1024 * 1024
    with duckdb.connect() as connection:
        assert (
            connection.read_parquet(str(tmp_path / "large.parquet"))
            .project(f"json_array_length({root})")
            .fetchone()[0]
            == 20_000
        )


def test_memory_guard_detects_retained_python_payload(
    large_json_case, tmp_path, monkeypatch
):
    source, builder, _ = large_json_case
    retained = []
    original_publish = bronze.publish_bronze

    def retain_payload(*args, **kwargs):
        retained.append(source.read_bytes())
        return original_publish(*args, **kwargs)

    monkeypatch.setattr(bronze, "publish_bronze", retain_payload)
    measurement = measure_python_memory(
        builder,
        source,
        tmp_path / "large.parquet",
    )
    assert len(retained) == 1
    assert measurement["peak_bytes"] > 2 * 1024 * 1024


@pytest.mark.parametrize("root", ["session", "fastest_lap", "classification"])
def test_missing_json_root_is_still_rejected(tmp_path, root):
    document = {"session": {}, "fastest_lap": {}, "classification": []}
    del document[root]
    source = tmp_path / "source.json"
    source.write_text(json.dumps(document), encoding="utf-8")
    output = tmp_path / "document.parquet"
    output.write_bytes(b"previous version")
    with pytest.raises(KeyError, match=root):
        bronze.build_classification_document(source, output)
    assert output.read_bytes() == b"previous version"
    assert set(tmp_path.iterdir()) == {source, output}


@pytest.mark.parametrize("member", ["drivers", "pit_stops"])
def test_invalid_nested_pit_arrays_are_rejected(tmp_path, member):
    car = {"number": "04", "drivers": [], "pit_stops": []}
    car[member] = None
    source = tmp_path / "source.json"
    source.write_text(
        json.dumps({"session": {}, "pit_stop_analysis": [car]}), encoding="utf-8"
    )
    output = tmp_path / "document.parquet"
    output.write_bytes(b"previous version")
    with pytest.raises(ValueError, match="drivers and pit_stops must be arrays"):
        bronze.build_document(source, output)
    assert output.read_bytes() == b"previous version"


def test_bom_unicode_and_null_fields_survive_native_validation(tmp_path):
    source = tmp_path / "source.json"
    document = {
        "session": {"event": "Montréal 🦆"},
        "fastest_lap": {},
        "classification": [{"number": "04", "team": " BMW ", "position": None}],
    }
    source.write_text(json.dumps(document, ensure_ascii=False), encoding="utf-8-sig")
    output = tmp_path / "document.parquet"
    bronze.build_classification_document(source, output)
    with duckdb.connect() as connection:
        row = connection.read_parquet(str(output)).fetchone()
    assert [json.loads(value) for value in row] == list(document.values())

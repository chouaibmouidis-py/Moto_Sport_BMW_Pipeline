import json

import duckdb
import pytest
from vortex_support import VORTEX_EXTENSION_DIRECTORY

from experiments.storage_formats import bronze_adapter
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


@pytest.mark.parametrize("storage_format", ["vortex"])
def test_json_publication_does_not_decode_or_fetch_documents_in_python(
    json_bronze_case, tmp_path, monkeypatch, storage_format
):
    source, builder = json_bronze_case
    output = tmp_path / f"document.{storage_format}"

    def forbidden(*args, **kwargs):
        raise AssertionError("Full JSON documents must stay inside DuckDB")

    if storage_format == "vortex":
        builder = getattr(bronze_adapter, builder.__name__)

    with monkeypatch.context() as patcher:
        patcher.setattr(json, "load", forbidden)
        patcher.setattr(json, "loads", forbidden)
        patcher.setattr(duckdb.DuckDBPyRelation, "fetchall", forbidden)
        builder(source, output, extension_directory=VORTEX_EXTENSION_DIRECTORY)
    assert output.is_file()
    assert not list(tmp_path.glob("*.tmp.*"))

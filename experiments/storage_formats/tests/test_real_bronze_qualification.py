import json
from pathlib import Path

import pytest
from vortex_support import VORTEX_EXTENSION_DIRECTORY

from experiments.storage_formats import qualify_real_bronze
from experiments.storage_formats.qualify_real_bronze import qualify_source


@pytest.mark.parametrize("kind", ["csv", "classification_json", "pit_json"])
def test_real_qualification_preserves_source_and_loads_silver_input(tmp_path, kind):
    root = tmp_path / "project"
    source = {
        "source_id": "test-source",
        "document_type": "classification",
        "format": "csv",
        "filename": "report.csv",
    }
    if kind != "csv":
        source.update(format="json", filename="report.json")
        if kind == "pit_json":
            source["document_type"] = "pit_stops"
    raw = root / "data/raw/test-source" / source["filename"]
    raw.parent.mkdir(parents=True)
    if kind == "csv":
        raw.write_text("NUMBER;VEHICLE\n 04 ; BMW \n", encoding="utf-8")
    else:
        document = {"session": {}}
        document.update(
            {"pit_stop_analysis": [{"number": "04", "drivers": [], "pit_stops": []}]}
            if kind == "pit_json"
            else {"fastest_lap": {}, "classification": [{"number": "04"}]}
        )
        raw.write_text(json.dumps(document), encoding="utf-8")
    original = raw.read_bytes()
    report = qualify_source(
        root, source, tmp_path / "work", Path(str(VORTEX_EXTENSION_DIRECTORY)), pairs=2
    )
    assert report["content_verified"] is True
    assert report["silver_input_verified"] is True
    assert report["source_unchanged"] is True
    assert report["rows"] == 1
    assert len(report["measurements"]) == 4
    assert set(report["summary"]) == {"parquet", "vortex"}
    assert raw.read_bytes() == original
    assert not (root / "data/bronze").exists()
    assert not list((tmp_path / "work").rglob("*.vortex"))
    assert not list((tmp_path / "work").rglob("*.parquet"))


def test_qualification_refuses_report_if_existing_inputs_change(tmp_path, monkeypatch):
    project = tmp_path / "project"
    raw = project / "data/raw/source-a/report.json"
    raw.parent.mkdir(parents=True)
    raw.write_bytes(b"original")
    (project / "config").mkdir()
    (project / "config/sources.json").write_text(
        '{"documents":[{"enabled":true,"source_id":"source-a"}]}', encoding="utf-8"
    )
    report = tmp_path / "report.json"

    def corrupt_input(*args, **kwargs):
        raw.write_bytes(b"modified")
        return {}

    monkeypatch.setattr(qualify_real_bronze, "qualify_source", corrupt_input)
    with pytest.raises(
        ValueError, match="existing inputs or active references changed"
    ):
        qualify_real_bronze.main(
            [
                "--project",
                str(project),
                "--extension-directory",
                str(VORTEX_EXTENSION_DIRECTORY),
                "--report",
                str(report),
            ]
        )
    assert not report.exists()

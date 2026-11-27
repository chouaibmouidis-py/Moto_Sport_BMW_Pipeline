"""Verify pit-stop Bronze round trips and preservation of previous files on failure."""

import hashlib
import json
from pathlib import Path
from unittest.mock import patch

import pytest

from build_bronze import build_document, main


def test_invalid_json_preserves_previous_file(tmp_path):
    source_path = tmp_path / "source.json"
    output_path = tmp_path / "document.parquet"
    source_path.write_bytes(b'{"session":')
    output_path.write_bytes(b"ancienne version")
    with pytest.raises(json.JSONDecodeError):
        build_document(source_path, output_path)
    assert output_path.read_bytes() == b"ancienne version"


def test_rejects_non_parquet_output(tmp_path):
    directory = tmp_path
    source_path = directory / "source.json"
    output_path = directory / "metadata.json"
    with pytest.raises(ValueError):
        build_document(source_path, output_path)


def test_write_failure_preserves_previous_files(tmp_path):
    directory = tmp_path
    source_path = directory / "source.json"
    output_path = directory / "document.parquet"
    source_path.write_bytes(b'{"session": {}, "pit_stop_analysis": []}')
    output_path.write_bytes(b"ancienne version")
    with patch(
        "duckdb.DuckDBPyRelation.write_parquet",
        side_effect=OSError("Simulated write failure"),
    ):
        with pytest.raises(OSError):
            build_document(source_path, output_path)
        assert output_path.read_bytes() == b"ancienne version"


def test_main_reads_filename_from_manifest(tmp_path):
    root = tmp_path
    source_id = "imsa-2024-daytona-race-hour24-pit-stops"
    filename = "20_Pit Stops Time Cards.JSON"

    config_directory = root / "config"
    config_directory.mkdir()

    manifest = {
        "documents": [
            {
                "source_id": source_id,
                "enabled": True,
                "document_type": "pit_stops",
                "filename": filename,
            }
        ]
    }
    (config_directory / "sources.json").write_text(
        json.dumps(manifest),
        encoding="utf-8",
    )

    raw_directory = root / "data" / "raw" / source_id
    raw_directory.mkdir(parents=True)

    content = json.dumps(
        {
            "session": {"event_name": "Daytona"},
            "pit_stop_analysis": [],
        }
    ).encode("utf-8")

    (raw_directory / filename).write_bytes(content)

    (raw_directory / "metadata.json").write_text(
        json.dumps(
            {
                "sha256": hashlib.sha256(content).hexdigest(),
            }
        ),
        encoding="utf-8",
    )

    with patch("build_bronze.PROJECT_DIR", root):
        main(extension_directory=Path("extensions"))

    output_path = root / "data" / "bronze" / source_id / "document.parquet"
    assert output_path.is_file()

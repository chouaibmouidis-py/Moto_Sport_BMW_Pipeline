"""Verify classification Bronze conversion and failure-safe publication."""

import json
from pathlib import Path
from unittest.mock import patch

import pytest

from build_classification_bronze import (
    build_classification_csv,
    build_classification_document,
    read_classification_csv,
    select_classification_sources,
)


def test_invalid_json_preserves_previous_file(tmp_path):
    directory = tmp_path
    source_path = Path(directory) / "source.json"
    output_path = Path(directory) / "document.parquet"

    source_path.write_bytes(b"invalid json")
    output_path.write_bytes(b"previous version")

    with pytest.raises(json.JSONDecodeError):
        build_classification_document(source_path, output_path)

    assert output_path.read_bytes() == b"previous version"


def test_write_failure_preserves_previous_file(tmp_path):
    directory = tmp_path
    source_path = Path(directory) / "source.json"
    output_path = Path(directory) / "document.parquet"

    source_path.write_text(
        json.dumps(
            {
                "session": {},
                "fastest_lap": {},
                "classification": [],
            }
        ),
        encoding="utf-8",
    )
    output_path.write_bytes(b"previous version")

    with patch(
        "duckdb.DuckDBPyRelation.write_parquet",
        side_effect=OSError("Simulated write failure"),
    ):
        with pytest.raises(OSError):
            build_classification_document(source_path, output_path)

    assert output_path.read_bytes() == b"previous version"


def test_preserves_all_three_roots(tmp_path, connection):
    document = {
        "session": {"report_mark": "Official"},
        "fastest_lap": {"participant_number": "04"},
        "classification": [
            {
                "number": "70",
                "pit_stops": "0",
                "not_finished": True,
            }
        ],
    }
    directory = tmp_path
    source_path = Path(directory) / "source.json"
    output_path = Path(directory) / "document.parquet"
    source_text = json.dumps(document)
    source_path.write_text(source_text, encoding="utf-8")

    build_classification_document(source_path, output_path)

    saved = connection.read_parquet(str(output_path))
    row = saved.project(
        "to_json(session), to_json(fastest_lap), to_json(classification)"
    ).fetchone()

    saved_document = {
        "session": json.loads(row[0]),
        "fastest_lap": json.loads(row[1]),
        "classification": json.loads(row[2]),
    }

    assert saved_document == document


def test_selects_only_enabled_classification_sources():
    documents = [
        {
            "source_id": "enabled-classification",
            "enabled": True,
            "document_type": "classification",
        },
        {
            "source_id": "disabled-classification",
            "enabled": False,
            "document_type": "classification",
        },
        {
            "source_id": "enabled-pits",
            "enabled": True,
            "document_type": "pit_stops",
        },
        {
            "source_id": "classification-without-enabled",
            "document_type": "classification",
        },
    ]

    selected = select_classification_sources(documents)
    assert selected == [documents[0]]


def test_csv_reader_preserves_raw_text(tmp_path, connection):
    directory = tmp_path
    source_path = Path(directory) / "classification.csv"
    source_path.write_text(
        "NUMBER;POSITION;VEHICLE\n 04 ;inconnue; BMW M4 GT3 \n",
        encoding="utf-8",
    )

    result = read_classification_csv(connection, source_path)
    rows = result.fetchall()

    assert rows == [(" 04 ", "inconnue", " BMW M4 GT3 ")]


def test_csv_builder_preserves_raw_fields_in_parquet(tmp_path, connection):
    directory = tmp_path
    source_path = Path(directory) / "classification.csv"
    output_path = Path(directory) / "bronze" / "document.parquet"
    original_content = "NUMBER;POSITION;VEHICLE\n 04 ;inconnue; BMW M4 GT3 \n"
    source_path.write_text(original_content, encoding="utf-8")

    build_classification_csv(source_path, output_path)

    rows = connection.read_parquet(str(output_path)).fetchall()

    assert rows == [(" 04 ", "inconnue", " BMW M4 GT3 ")]
    assert source_path.read_text(encoding="utf-8") == original_content

"""Verify multi-event CSV publication and complete-input prechecks."""

import hashlib
from pathlib import Path

import duckdb
import pytest

from moto_sport_bmw_pipeline.batch_processing import build_classification_batch


def test_separates_event_outputs_and_preserves_provenance(tmp_path):
    sql_path = (
        Path(__file__).resolve().parent.parent
        / "sql"
        / "33_silver_classification_csv.sql"
    )
    directory = tmp_path
    root = Path(directory)
    (root / "sql").mkdir()
    (root / "sql" / sql_path.name).write_bytes(sql_path.read_bytes())

    duration_parser_path = sql_path.parent / "21_create_duration_parser.sql"

    (root / "sql" / duration_parser_path.name).write_bytes(
        duration_parser_path.read_bytes()
    )

    events = []
    for event_id in ("course-a", "course-b"):
        source_id = f"test-2023-{event_id}-classification"
        source = root / "data" / "raw" / source_id / "report.csv"
        source.parent.mkdir(parents=True)
        source.write_text(
            "NUMBER;VEHICLE;POSITION;CLASS;STATUS;IMSA_ManufacturerId;"
            "TEAM;LAPS;FL_LAPNUM;FL_KPH;TOTAL_TIME;FL_TIME;"
            "GAP_FIRST;GAP_PREVIOUS\n"
            " 01 ; BMW M4 GT3 ;inconnue; GTD ; Not started ; 74 "
            ";;;;;;;;\n",
            encoding="utf-8",
        )
        events.append(
            {
                "event_id": event_id,
                "classification_path": str(source.relative_to(root)),
            }
        )
    reference = root / "data" / "current.json"
    reference.write_bytes(b'{"run_id":"previous-run"}')
    results = build_classification_batch(
        root,
        {"season": 2023, "events": events},
        extension_directory=Path("extensions"),
    )
    assert [row["participants"] for row in results] == [1, 1]
    assert [row["missing_positions"] for row in results] == [1, 1]
    for event in events:
        source_id = Path(event["classification_path"]).parent.name
        bronze = root / "data" / "bronze" / source_id / "document.parquet"
        output = (
            root
            / "data"
            / "csv_pdf"
            / f"{event['event_id']}-2023"
            / "silver"
            / "classification.parquet"
        )
        with duckdb.connect() as connection:
            rows = (
                connection.read_parquet(str(output))
                .project(
                    "source_id, bronze_sha256, car_number, overall_position, classification_status"
                )
                .fetchall()
            )
        assert rows == [
            (
                source_id,
                hashlib.sha256(bronze.read_bytes()).hexdigest(),
                "01",
                None,
                "Not started",
            )
        ]
    assert reference.read_bytes() == b'{"run_id":"previous-run"}'


def test_missing_later_input_prevents_any_publication(tmp_path):
    directory = tmp_path
    root = Path(directory)
    first = root / "data" / "raw" / "source-a" / "report.csv"
    first.parent.mkdir(parents=True)
    first.write_text("NUMBER\n24\n", encoding="utf-8")
    catalog = {
        "season": 2023,
        "events": [
            {
                "event_id": "course-a",
                "classification_path": str(first.relative_to(root)),
            },
            {
                "event_id": "course-b",
                "classification_path": "data/raw/source-b/report.csv",
            },
        ],
    }
    with pytest.raises(FileNotFoundError):
        build_classification_batch(root, catalog)
    assert not (root / "data" / "bronze").exists()
    assert not (root / "data" / "csv_pdf").exists()

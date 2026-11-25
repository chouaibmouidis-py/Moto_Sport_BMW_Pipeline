"""Check that JSON and CSV classify and convert the same gap values identically."""

import json
from pathlib import Path

import pytest


@pytest.mark.parametrize("report_format", ("json", "csv"))
def test_same_gap_contract_for_json_and_csv(subtests, report_format, connection):
    # Each case is source text followed by expected normalized outputs.
    cases = [
        (None, None, "missing", None, None),
        ("  ", None, "missing", None, None),
        ("-", "-", "marker", None, None),
        (" +3.028 ", "+3.028", "time", 3.028, None),
        ("+1:17.343", "+1:17.343", "time", 77.343, None),
        ("+1:46:20.303", "+1:46:20.303", "time", 6380.303, None),
        ("1 Lap", "1 Lap", "laps", None, 1),
        (" 2 Laps ", "2 Laps", "laps", None, 2),
        ("1 lap", "1 lap", "laps", None, 1),
        ("2 laps", "2 laps", "laps", None, 2),
        ("1 LAP", "1 LAP", "laps", None, 1),
        ("2 LAPS", "2 LAPS", "laps", None, 2),
        (" 3 lApS ", "3 lApS", "laps", None, 3),
        ("pending review", "pending review", "unrecognized", None, None),
        ("+1:60", "+1:60", "unrecognized", None, None),
        ("+1e3", "+1e3", "unrecognized", None, None),
        ("+nan", "+nan", "unrecognized", None, None),
        ("+inf", "+inf", "unrecognized", None, None),
        ("+NaN", "+NaN", "unrecognized", None, None),
        ("+INF", "+INF", "unrecognized", None, None),
        ("+1E3", "+1E3", "unrecognized", None, None),
        ("3.028", "3.028", "unrecognized", None, None),
    ]
    project = Path(__file__).resolve().parent.parent

    connection.execute(
        (project / "sql/21_create_duration_parser.sql").read_text(encoding="utf-8")
    )
    if report_format == "json":
        entries = [
            {
                "number": str(index),
                "gap_first": raw,
                "gap_previous": raw,
            }
            for index, (raw, *_expected) in enumerate(cases)
        ]
        connection.execute(
            "CREATE TEMP TABLE bronze_classification AS "
            "SELECT ?::JSON AS classification, "
            "'test-source' AS source_id, 'test-hash' AS bronze_sha256",
            [json.dumps(entries)],
        )
        filename = "25_silver_classification.sql"
    else:
        fields = (
            "NUMBER",
            "VEHICLE",
            "POSITION",
            "CLASS",
            "STATUS",
            "IMSA_ManufacturerId",
            "TEAM",
            "LAPS",
            "FL_LAPNUM",
            "FL_KPH",
            "TOTAL_TIME",
            "FL_TIME",
            "GAP_FIRST",
            "GAP_PREVIOUS",
        )
        columns = ", ".join(f"{name} VARCHAR" for name in fields)
        connection.execute(
            "CREATE TEMP TABLE bronze_classification_csv "
            f"(source_id VARCHAR, bronze_sha256 VARCHAR, {columns})"
        )
        for index, (raw, *_expected) in enumerate(cases):
            values = ["test-source", "test-hash", str(index)]
            values += [None] * 11
            values += [raw, raw]
            connection.execute(
                "INSERT INTO bronze_classification_csv VALUES "
                "(" + ", ".join("?" for _ in values) + ")",
                values,
            )
        filename = "33_silver_classification_csv.sql"

    relation = connection.sql((project / "sql" / filename).read_text(encoding="utf-8"))
    for index, (raw, cleaned, kind, seconds, laps) in enumerate(cases):
        for gap in ("first", "previous"):
            with subtests.test(format=report_format, raw=raw, gap=gap):
                actual = (
                    relation.filter(f"car_number = '{index}'")
                    .project(
                        f"gap_{gap}_raw, gap_{gap}_kind, "
                        f"gap_{gap}_seconds, gap_{gap}_laps"
                    )
                    .fetchone()
                )
                assert actual == (cleaned, kind, seconds, laps)

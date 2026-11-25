"""Verify valid duration conversions and rejection of invalid formats."""

from pathlib import Path

import pytest


@pytest.fixture
def duration_connection(connection):
    parser_path = (
        Path(__file__).resolve().parent.parent / "sql/21_create_duration_parser.sql"
    )
    connection.execute(parser_path.read_text(encoding="utf-8"))
    return connection


@pytest.mark.parametrize(
    "raw_duration, expected",
    [
        ("48.019", 48.019),
        ("1:04.099", 64.099),
        ("1:55:57.718", 6957.718),
        ("0", 0.0),
        (" 75:00 ", 4500.0),
        ("100:00:00", 360000.0),
        ("1:30.500", 90.5),
        ("1e3", None),
        ("1.5:30", None),
        ("1:02.5:03", None),
        ("1::30", None),
        ("a:30", None),
        ("1:abc:20", None),
        ("1:2:3:4", None),
        ("", None),
        ("   ", None),
        ("1e308:00", None),
        ("9" * 308 + ":00", None),
        ("9" * 308 + ":00:00", None),
        ("00:75", None),
        ("1:-5", None),
        ("1:60:00", None),
        ("-5", None),
        ("inconnue", None),
        ("NaN", None),
        ("Infinity", None),
        ("-Infinity", None),
        ("NaN:01", None),
        ("1:NaN", None),
        ("1:Infinity", None),
        ("1:NaN:02", None),
        ("1:Infinity:02", None),
        ("1:02:NaN", None),
        ("1:02:Infinity", None),
        (None, None),
    ],
)
def test_converts_valid_durations_and_rejects_invalid_ones(
    duration_connection, raw_duration, expected
):
    actual = duration_connection.sql(
        "SELECT parse_duration_seconds(?)",
        params=[raw_duration],
    ).fetchone()[0]
    if expected is None:
        assert actual is None
    else:
        # Match the previous unittest places=3 absolute-difference semantics.
        assert round(abs(actual - expected), 3) == 0

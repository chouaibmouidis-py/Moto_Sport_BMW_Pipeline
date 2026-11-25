"""Verify session date and temperature normalization with missing and invalid inputs."""

import json
from datetime import datetime
from pathlib import Path

import pytest


@pytest.fixture
def session_input(connection):
    """Create an empty input table; the scenario supplies its own session values."""
    connection.execute("""
        CREATE TEMP TABLE bronze_document (
            source_id VARCHAR,
            bronze_sha256 VARCHAR,
            session JSON
        )
    """)
    return connection


@pytest.mark.parametrize(
    "raw, expected, status",
    [
        ("17.72 ºC", 17.72, "valid"),
        ("17.72 ºc", 17.72, "valid"),
        ("17.72 ºF", None, "invalid"),
        ("17.72 ºf", None, "invalid"),
    ],
)
def test_celsius_case_does_not_change_values_or_quality_statuses(
    session_input, raw, expected, status
):
    query = Path(__file__).resolve().parent.parent / "sql/16_silver_sessions.sql"
    session = {"weather": {"air_temperature": raw, "track_temperature": raw}}
    session_input.execute(
        "INSERT INTO bronze_document VALUES (?, ?, ?)",
        ["source", "hash", json.dumps(session)],
    )
    result = (
        session_input.sql(query.read_text())
        .project(
            "air_temperature_raw, air_temperature_celsius, air_temperature_status, "
            "track_temperature_raw, track_temperature_celsius, track_temperature_status"
        )
        .fetchone()
    )
    assert result == (raw, expected, status, raw, expected, status)


@pytest.mark.parametrize(
    "session, expected",
    [
        pytest.param(
            {
                "session_date": "25/01/2025 01:40",
                "creation_date": "26/01/2025 02:00:29",
                "weather": {
                    "air_temperature": "17.72 ºC",
                    "track_temperature": "33.60 ºC",
                },
            },
            (
                datetime(2025, 1, 25, 1, 40),
                datetime(2025, 1, 26, 2, 0, 29),
                17.72,
                33.60,
                "valid",
                "valid",
                "valid",
                "valid",
            ),
            id="valid-dates-and-temperatures",
        ),
        pytest.param(
            {
                "session_date": "date inconnue",
                "creation_date": "",
                "weather": {
                    "air_temperature": "inconnue",
                    "track_temperature": "inconnue",
                },
            },
            (None, None, None, None, "invalid", "invalid", "invalid", "missing"),
            id="invalid-dates-and-temperatures",
        ),
        pytest.param(
            {
                "session_date": "date inconnue",
                "creation_date": "",
                "weather": {"air_temperature": "   ", "track_temperature": "   "},
            },
            (None, None, None, None, "missing", "missing", "invalid", "missing"),
            id="missing-temperatures",
        ),
    ],
)
def test_session_normalization_preserves_expected_values_and_statuses(
    session_input, session, expected
):
    session_input.execute(
        "INSERT INTO bronze_document VALUES (?, ?, ?)",
        ["test-source", "test-bronze-hash", json.dumps(session)],
    )
    query = Path(__file__).resolve().parent.parent / "sql/16_silver_sessions.sql"
    row = (
        session_input.sql(query.read_text(encoding="utf-8"))
        .project(
            "session_datetime, report_creation_datetime, air_temperature_celsius, "
            "track_temperature_celsius, air_temperature_status, track_temperature_status, "
            "session_datetime_status, report_creation_datetime_status"
        )
        .fetchone()
    )
    assert row == expected

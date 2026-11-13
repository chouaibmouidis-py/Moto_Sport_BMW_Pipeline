"""Verify session date and temperature normalization with missing and invalid inputs."""

import json
import unittest
from datetime import datetime
from pathlib import Path

import duckdb


class SilverSessionsTests(unittest.TestCase):
    def test_converts_dates_and_temperatures(self):
        session = {
            "session_date": "25/01/2025 01:40",
            "creation_date": "26/01/2025 02:00:29",
            "weather": {
                "air_temperature": "17.72 ºC",
                "track_temperature": "33.60 ºC",
            },
        }

        with duckdb.connect() as connection:
            connection.execute("""
                CREATE TEMP TABLE bronze_document (
                    source_id VARCHAR,
                    bronze_sha256 VARCHAR,
                    session JSON
                )
            """)

            connection.execute(
                "INSERT INTO bronze_document VALUES (?, ?, ?)",
                ["test-source", "test-bronze-hash", json.dumps(session)],
            )

            query_path = (
                Path(__file__).resolve().parent.parent
                / "sql"
                / "16_silver_sessions.sql"
            )

            sessions = connection.sql(
                query_path.read_text(encoding="utf-8")
            )
            sessions.create_view("silver_sessions")

            row = connection.sql("""
                SELECT
                    session_datetime,
                    report_creation_datetime,
                    air_temperature_celsius,
                    track_temperature_celsius,
                    air_temperature_status,
                    track_temperature_status,
                    session_datetime_status,
                    report_creation_datetime_status
                FROM silver_sessions
            """).fetchone()

            self.assertEqual(
                row,
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
            )


    def test_invalid_dates_and_missing_temperatures_return_null(self):
        session = {
            "session_date": "date inconnue",
            "creation_date": "",
            "weather": {
                "air_temperature": "inconnue",
                "track_temperature": "inconnue",
            },
        }

        with duckdb.connect() as connection:
            connection.execute("""
                CREATE TEMP TABLE bronze_document (
                    source_id VARCHAR,
                    bronze_sha256 VARCHAR,
                    session JSON
                )
            """)

            connection.execute(
                "INSERT INTO bronze_document VALUES (?, ?, ?)",
                ["test-source", "test-bronze-hash", json.dumps(session)],
            )

            query_path = (
                Path(__file__).resolve().parent.parent
                / "sql"
                / "16_silver_sessions.sql"
            )

            sessions = connection.sql(
                query_path.read_text(encoding="utf-8")
            )
            sessions.create_view("silver_sessions")

            row = connection.sql("""
                SELECT
                    session_datetime,
                    report_creation_datetime,
                    air_temperature_celsius,
                    track_temperature_celsius,
                    air_temperature_status,
                    track_temperature_status,
                    session_datetime_status,
                    report_creation_datetime_status
                FROM silver_sessions
            """).fetchone()

            self.assertEqual(
                row,
                (
                    None, None, None, None,
                    "invalid", "invalid", "invalid", "missing",
                ),
            )


    def test_empty_temperatures_are_missing(self):
        session = {
            "session_date": "date inconnue",
            "creation_date": "",
            "weather": {
                "air_temperature": "   ",
              "track_temperature": "   ",
            },
        }

        with duckdb.connect() as connection:
            connection.execute("""
                CREATE TEMP TABLE bronze_document (
                    source_id VARCHAR,
                    bronze_sha256 VARCHAR,
                    session JSON
                )
            """)

            connection.execute(
                "INSERT INTO bronze_document VALUES (?, ?, ?)",
                ["test-source", "test-bronze-hash", json.dumps(session)],
            )

            query_path = (
                Path(__file__).resolve().parent.parent
                / "sql"
                / "16_silver_sessions.sql"
            )

            sessions = connection.sql(
                query_path.read_text(encoding="utf-8")
            )
            sessions.create_view("silver_sessions")

            row = connection.sql("""
                SELECT
                    session_datetime,
                    report_creation_datetime,
                    air_temperature_celsius,
                    track_temperature_celsius,
                    air_temperature_status,
                    track_temperature_status,
                    session_datetime_status,
                    report_creation_datetime_status
                FROM silver_sessions
            """).fetchone()

            self.assertEqual(
                row,
                (
                    None, None, None, None,
                    "missing", "missing", "invalid", "missing",
                ),
            )

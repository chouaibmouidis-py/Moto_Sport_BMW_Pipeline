import json
import unittest
from pathlib import Path
from datetime import time
import duckdb

class SilverPitStopsTests(unittest.TestCase):
    def test_rejects_seconds_out_of_range(self):
        document = {
            "session": {},
            "pit_stop_analysis": [
                {
                    "number": "24",
                    "vehicle": "BMW M Hybrid V8",
                    "team": "BMW M Team RLL",
                    "pit_stops": [
                        {"pit_number": 1, "pit_time": "00:75"}
                    ],
                }
            ],
        }
        with duckdb.connect() as connexion:

            parser_path = (
                Path(__file__).resolve().parent.parent
                / "sql"
                / "21_create_duration_parser.sql"
            )
            connexion.execute(
                parser_path.read_text(encoding="utf-8")
            )

            connexion.execute("""
                CREATE TEMP TABLE bronze_document (
                    session JSON,
                    pit_stop_analysis JSON
                )
            """)

            connexion.execute(
                "INSERT INTO bronze_document VALUES (?, ?)",
                [
                    json.dumps(document["session"]),
                    json.dumps(document["pit_stop_analysis"]),
                ],
            )
            query_path = (
                Path(__file__).resolve().parent.parent
                / "sql"
                / "07_silver_pit_stops.sql"
                )

            query = query_path.read_text(encoding="utf-8")

            connexion.execute("""
                ALTER TABLE bronze_document
                ADD COLUMN source_id VARCHAR DEFAULT 'test-source'
            """)

            connexion.execute("""
                ALTER TABLE bronze_document
                ADD COLUMN bronze_sha256 VARCHAR DEFAULT 'test-bronze-hash'
            """)

            rows = connexion.sql(query).fetchall()

            self.assertEqual(len(rows), 1)
            actual_seconds = rows[0][-1]
            self.assertIsNone(actual_seconds)

    def test_converts_minutes_and_seconds(self):
        document = {
            "session": {},
            "pit_stop_analysis": [
                {
                    "number": "04",
                    "vehicle": "BMW M Hybrid V8",
                    "manufacturer": " BMW ",
                    "class": " GTP ",
                    "team": "BMW M Team RLL",
                    "pit_stops": [
                        {
                            "pit_number": 1,
                            "pit_time": "1:04.099",
                            "in_driver_number": 1,
                            "out_driver_number": 2,
                            "in_time": "14:04:41.364",
                            "out_time": "14:05:45.463",
                            "total_pit_time": "2:10.500",
                            "in_driver_firstname": " Alice ",
                            "in_driver_surname": " Martin ",
                            "out_driver_firstname": " Bob ",
                            "out_driver_surname": " Bernard ",
                        }
                    ],
                }
            ],
        }
        with duckdb.connect() as connexion:

            parser_path = (
                Path(__file__).resolve().parent.parent
                / "sql"
                / "21_create_duration_parser.sql"
            )
            connexion.execute(
                parser_path.read_text(encoding="utf-8")
            )

            connexion.execute("""
                CREATE TEMP TABLE bronze_document (
                    session JSON,
                    pit_stop_analysis JSON
                )
            """)

            connexion.execute(
                "INSERT INTO bronze_document VALUES (?, ?)",
                [
                    json.dumps(document["session"]),
                    json.dumps(document["pit_stop_analysis"]),
                ],
            )
            query_path = (
                Path(__file__).resolve().parent.parent
                / "sql"
                / "07_silver_pit_stops.sql"
                )

            query = query_path.read_text(encoding="utf-8")

            connexion.execute("""
                ALTER TABLE bronze_document
                ADD COLUMN source_id VARCHAR DEFAULT 'test-source'
            """)

            connexion.execute("""
                ALTER TABLE bronze_document
                ADD COLUMN bronze_sha256 VARCHAR DEFAULT 'test-bronze-hash'
            """)
            result = connexion.sql(query)
            rows = result.fetchall()
            self.assertEqual(len(rows), 1)
            self.assertEqual(rows[0][0], "test-source")
            self.assertEqual(rows[0][1], "04")
            self.assertEqual(rows[0][3], "BMW")
            self.assertEqual(rows[0][4], "GTP")
            self.assertEqual(rows[0][8], 1)
            self.assertEqual(rows[0][9], 2)

            actual_seconds = rows[0][-1]
            self.assertAlmostEqual(actual_seconds, 64.099, places=3)

            total_seconds = result.project(
                "total_pit_time_seconds"
            ).fetchone()[0]

            self.assertAlmostEqual(
                total_seconds,
                130.5,
                places=3,
            )

            passage_times = result.project(
                "in_time, out_time"
            ).fetchone()

            self.assertEqual(
                passage_times,
                (
                    time(14, 4, 41, 364000),
                    time(14, 5, 45, 463000),
                ),
            )

            details = result.project("""
                in_time_raw,
                out_time_raw,
                total_pit_time_raw,
                reported_in_driver_first_name,
                reported_in_driver_surname,
                reported_out_driver_first_name,
                reported_out_driver_surname
            """).fetchone()

            self.assertEqual(
                details,
                (
                    "14:04:41.364",
                    "14:05:45.463",
                    "2:10.500",
                    "Alice",
                    "Martin",
                    "Bob",
                    "Bernard",
                ),
            )

    def test_duration_cases(self):
        cases = [
            ("48.019", 48.019),
            ("1:04.099", 64.099),
            ("1:55:57.718", 6957.718),
            ("00:75", None),
            (None, None),
            ("inconnu", None),
            ("-5", None),
            ("1:-5", None),
            ("1:60:00", None),
            ("1:59:59.999", 7199.999),
            ("02:05.250", 125.250),
            ("1:20:75", None),
        ]

        for pit_time, expected in cases:
            with self.subTest(pit_time=pit_time):
                document = {
                    "session": {},
                    "pit_stop_analysis": [
                        {
                            "number": "24",
                            "vehicle": "BMW M Hybrid V8",
                            "team": "BMW M Team RLL",
                            "pit_stops": [
                                {"pit_number": 1, "pit_time": pit_time}
                            ],
                        }
                    ],
                }
                with duckdb.connect() as connexion:

                    parser_path = (
                        Path(__file__).resolve().parent.parent
                        / "sql"
                        / "21_create_duration_parser.sql"
                    )
                    connexion.execute(
                        parser_path.read_text(encoding="utf-8")
                    )

                    connexion.execute("""
                        CREATE TEMP TABLE bronze_document (
                            session JSON,
                            pit_stop_analysis JSON
                        )
                    """)

                    connexion.execute(
                        "INSERT INTO bronze_document VALUES (?, ?)",
                        [
                            json.dumps(document["session"]),
                            json.dumps(document["pit_stop_analysis"]),
                        ],
                    )

                    query_path = (
                        Path(__file__).resolve().parent.parent
                        / "sql"
                        / "07_silver_pit_stops.sql"
                    )

                    query = query_path.read_text(encoding="utf-8")

                    connexion.execute("""
                        ALTER TABLE bronze_document
                        ADD COLUMN source_id VARCHAR DEFAULT 'test-source'
                    """)

                    connexion.execute("""
                        ALTER TABLE bronze_document
                        ADD COLUMN bronze_sha256 VARCHAR DEFAULT 'test-bronze-hash'
                    """)

                    rows = connexion.sql(query).fetchall()

                    self.assertEqual(len(rows), 1)
                    actual_seconds = rows[0][-1]
                    if expected is None:
                        self.assertIsNone(actual_seconds)
                    else:
                        self.assertAlmostEqual(actual_seconds, expected, places=3)

    def test_calculates_clock_duration_across_midnight(self):
        cases = [
            ("14:00:00", "14:01:00", 60.0),
            ("23:59:50", "00:00:20", 30.0),
            ("23:59:59.900", "00:00:00.100", 0.2),
            ("23:55:04.354", "01:34:14.004", 5949.65),
        ]

        query_path = (
            Path(__file__).resolve().parent.parent
            / "sql"
            / "07_silver_pit_stops.sql"
        )
        query = query_path.read_text(encoding="utf-8")

        for in_time, out_time, expected_seconds in cases:
            with self.subTest(in_time=in_time, out_time=out_time):
                cars = [
                    {
                        "number": "24",
                        "pit_stops": [
                            {
                                "pit_number": 1,
                                "in_time": in_time,
                                "out_time": out_time,
                            }
                        ],
                    }
                ]

                with duckdb.connect() as connexion:
                    parser_path = (
                        Path(__file__).resolve().parent.parent
                        / "sql"
                        / "21_create_duration_parser.sql"
                    )

                    connexion.execute(
                        parser_path.read_text(encoding="utf-8")
                    )

                    connexion.execute("""
                        CREATE TEMP TABLE bronze_document (
                            source_id VARCHAR,
                            bronze_sha256 VARCHAR,
                            pit_stop_analysis JSON
                        )
                    """)

                    connexion.execute(
                        "INSERT INTO bronze_document VALUES (?, ?, ?)",
                        [
                            "test-source",
                            "test-bronze-hash",
                            json.dumps(cars),
                        ],
                    )

                    converted = connexion.sql(query)

                    actual_seconds = converted.project(
                        "clock_duration_seconds"
                    ).fetchone()[0]

                    self.assertAlmostEqual(
                        actual_seconds,
                        expected_seconds,
                        places=3,
                    )

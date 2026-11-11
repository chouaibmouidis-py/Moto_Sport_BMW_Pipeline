import json
import unittest
from pathlib import Path

import duckdb

class SilverClassificationTests(unittest.TestCase):
    def test_preserves_car_number_and_converts_fields(self):
        participants = [
            {
                "number": " 04 ",
                "position": 48,
                "class": " GTD ",
                "pit_stops": "0",
                "not_finished": True,
            }
        ]
        with duckdb.connect() as connection:
            connection.execute("""
                CREATE TEMP TABLE bronze_classification (
                    classification JSON,
                    source_id VARCHAR,
                    bronze_sha256 VARCHAR
                )
            """)

            connection.execute(
                "INSERT INTO bronze_classification VALUES (?, ?, ?)",
                [
                    json.dumps(participants),
                    "test-source",
                    "test-bronze-hash",
                ],
            )
            query_path = (
                Path(__file__).resolve().parent.parent
                / "sql"
                / "25_silver_classification.sql"
            )

            query = query_path.read_text(encoding="utf-8")
            rows = connection.sql(query).fetchall()

            self.assertEqual(
                rows,
                [
                    ("test-source", "test-bronze-hash",
                     "0", "04", 48, "GTD", 0, True)
                ],
            )


    def test_returns_null_for_invalid_pit_stop_count(self):
        participants = [
            {
                "number": " 04 ",
                "position": 48,
                "class": " GTD ",
                "pit_stops": "inconnu",
                "not_finished": True,
            }
        ]
        with duckdb.connect() as connection:
            connection.execute("""
                CREATE TEMP TABLE bronze_classification (
                    classification JSON,
                    source_id VARCHAR,
                    bronze_sha256 VARCHAR
                )
            """)

            connection.execute(
                "INSERT INTO bronze_classification VALUES (?, ?, ?)",
                [
                    json.dumps(participants),
                    "test-source",
                    "test-bronze-hash",
                ],
            )

            query_path = (
                Path(__file__).resolve().parent.parent
                / "sql"
                / "25_silver_classification.sql"
            )

            query = query_path.read_text(encoding="utf-8")
            rows = connection.sql(query).fetchall()

            self.assertEqual(
                rows,
                [
                    ("test-source", "test-bronze-hash",
                     "0", "04", 48, "GTD", None, True)
                ],
            )

    def test_counts_missing_keys(self):
        with duckdb.connect() as connection:
            connection.execute("""
                CREATE TEMP VIEW silver_classification AS
                SELECT *
                FROM (VALUES
                    ('test-source', 'version-1', '0'),
                    (NULL, 'version-1', '1'),
                    ('test-source', NULL, '2'),
                    ('test-source', 'version-1', NULL),
                    (NULL, NULL, NULL)
                ) AS t(
                    source_id,
                    bronze_sha256,
                    source_entry_index
                )
            """)

            missing_keys_path = (
                Path(__file__).resolve().parent.parent
                / "sql"
                / "26_check_missing_classification_keys.sql"
            )

            query = missing_keys_path.read_text(encoding="utf-8")
            missing_keys_count = connection.sql(query).fetchone()[0]

            self.assertEqual(missing_keys_count, 4)

    def test_counts_duplicate_keys(self):
        with duckdb.connect() as connection:
            connection.execute("""
                CREATE TEMP VIEW silver_classification AS
                SELECT *
                FROM (VALUES
                    ('test-source', 'version-1', '0'),
                    ('test-source', 'version-1', '0'),
                    ('test-source', 'version-1', '1'),
                    ('test-source', 'version-2', '0'),
                    ('other-source', 'version-1', '0')
                ) AS t(
                    source_id,
                    bronze_sha256,
                    source_entry_index
                )
            """)

            duplicate_keys_path = (
                Path(__file__).resolve().parent.parent
                / "sql"
                / "27_check_duplicate_classification_keys.sql"
            )

            query = duplicate_keys_path.read_text(encoding="utf-8")
            duplicate_keys_count = connection.sql(query).fetchone()[0]

            self.assertEqual(duplicate_keys_count, 1)

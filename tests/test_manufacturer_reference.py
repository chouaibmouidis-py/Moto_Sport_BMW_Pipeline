"""Verify manufacturer mapping without choosing ambiguous names."""

import unittest
from pathlib import Path
from moto_sport_bmw_pipeline.marts import build_manufacturer_reference
from moto_sport_bmw_pipeline.marts import enrich_2023_manufacturers
import duckdb


class ManufacturerReferenceTests(unittest.TestCase):
    def test_distinguishes_unique_ambiguous_and_missing_names(self):
        with duckdb.connect() as connection:
            connection.execute("""
                CREATE TEMP VIEW manufacturer_reference_input AS
                SELECT *
                FROM (VALUES
                    ('74', 'BMW'),
                    ('74', 'BMW'),
                    ('7643', 'Mercedes AMG'),
                    ('7643', 'Mercedes-AMG'),
                    ('7665', NULL)
                ) AS t(manufacturer_source_id, manufacturer)
            """)

            query_path = (
                Path(__file__).resolve().parent.parent
                / "sql"
                / "36_manufacturer_reference.sql"
            )
            rows = connection.sql(
                query_path.read_text(encoding="utf-8")
            ).fetchall()

            self.assertCountEqual(
                rows,
                [
                    ("74", 1, "matched", "BMW"),
                    ("7643", 2, "ambiguous", None),
                    ("7665", 0, "unmapped", None),
                ],
            )

    def test_extracts_cleaned_evidence_from_both_report_types(self):
        with duckdb.connect() as connection:
            connection.execute("""
                CREATE TEMP VIEW bronze_classification AS
                SELECT
                    'classification-a' AS source_id,
                    'class-version' AS bronze_sha256,
                    CAST('[
                        {"imsa_manufacturerid": " 74 ", "manufacturer": " BMW "},
                        {"imsa_manufacturerid": "", "manufacturer": "BMW"}
                    ]' AS JSON) AS classification
            """)

            connection.execute("""
                CREATE TEMP VIEW bronze_document AS
                SELECT
                    'pits-a' AS source_id,
                    'pit-version' AS bronze_sha256,
                    CAST('[
                        {"imsa_manufacturerid": "74", "manufacturer": "BMW"},
                        {"imsa_manufacturerid": "7665", "manufacturer": ""}
                    ]' AS JSON) AS pit_stop_analysis
            """)

            project_directory = Path(__file__).resolve().parent.parent

            reference = build_manufacturer_reference(
                connection,
                project_directory,
            )

            rows = connection.table(
                "manufacturer_reference_input"
            ).fetchall()

            self.assertCountEqual(
                rows,
                [
                    ("classification-a", "class-version", "74", "BMW"),
                    ("pits-a", "pit-version", "74", "BMW"),
                    ("pits-a", "pit-version", "7665", None),
                ],
            )

            self.assertCountEqual(
                reference.fetchall(),
                [
                    ("74", 1, "matched", "BMW"),
                    ("7665", 0, "unmapped", None),
                ],
            )

    def test_enrichment_preserves_participants_with_unresolved_names(self):
        with duckdb.connect() as connection:
            connection.execute("""
                CREATE TEMP VIEW csv_pdf_race_summary AS
                SELECT *
                FROM (VALUES
                    ('24', '74'),
                    ('57', '7643'),
                    ('33', '7665')
                ) AS t(car_number, manufacturer_source_id)
            """)

            connection.execute("""
                CREATE TEMP VIEW manufacturer_reference AS
                SELECT *
                FROM (VALUES
                    ('74', 'BMW', 'matched', 1),
                    ('7643', NULL, 'ambiguous', 2)
                ) AS t(
                    manufacturer_source_id,
                    manufacturer,
                    manufacturer_mapping_status,
                    manufacturer_name_count
                )
            """)

            project_directory = Path(__file__).resolve().parent.parent

            participants = enrich_2023_manufacturers(
                connection,
                project_directory,
            )
            rows = participants.fetchall()

            self.assertCountEqual(
                rows,
                [
                    ("24", "74", "BMW", "matched", 1),
                    ("57", "7643", None, "ambiguous", 2),
                    ("33", "7665", None, "unmapped", 0),
                ],
            )

    def test_rejects_participant_multiplication(self):
        with duckdb.connect() as connection:
            connection.execute("""
                CREATE TEMP VIEW csv_pdf_race_summary AS
                SELECT
                    '24' AS car_number,
                    '74' AS manufacturer_source_id
            """)

            connection.execute("""
                CREATE TEMP VIEW manufacturer_reference AS
                SELECT *
                FROM (VALUES
                    ('74', 'BMW', 'matched', 1),
                    ('74', 'BMW', 'matched', 1)
                ) AS t(
                    manufacturer_source_id,
                    manufacturer,
                    manufacturer_mapping_status,
                    manufacturer_name_count
                )
            """)

            project_directory = Path(__file__).resolve().parent.parent

            with self.assertRaisesRegex(
                ValueError,
                "participant count changed",
            ):
                enrich_2023_manufacturers(
                    connection,
                    project_directory,
                )
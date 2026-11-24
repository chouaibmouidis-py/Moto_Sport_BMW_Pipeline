"""Verify manufacturer mapping without choosing ambiguous names."""

import unittest
from pathlib import Path
from moto_sport_bmw_pipeline.marts import build_manufacturer_reference
from moto_sport_bmw_pipeline.marts import enrich_csv_pdf_manufacturers
import duckdb


class ManufacturerReferenceTests(unittest.TestCase):
    def test_case_only_names_match_but_different_names_remain_ambiguous(self):
        with duckdb.connect() as connection:
            connection.execute("""
                CREATE TEMP VIEW manufacturer_reference_input AS
                SELECT * FROM (VALUES
                    ('74', 'BMW'), ('74', 'bmw'), ('74', 'BmW'),
                    ('7643', 'Mercedes AMG'), ('7643', 'MERCEDES AMG'),
                    ('7643', 'Mercedes-AMG'), ('unknown', NULL)
                ) AS t(manufacturer_source_id, manufacturer)
            """)
            query = Path(__file__).resolve().parent.parent / 'sql/36_manufacturer_reference.sql'
            self.assertCountEqual(connection.sql(query.read_text()).fetchall(), [
                ('74', 1, 'matched', 'BMW'),
                ('7643', 2, 'ambiguous', None),
                ('unknown', 0, 'unmapped', None),
            ])
            self.assertCountEqual(connection.sql(
                "SELECT manufacturer FROM manufacturer_reference_input WHERE manufacturer_source_id = '74'"
            ).fetchall(), [('BMW',), ('bmw',), ('BmW',)])

    def test_silver_correction_takes_precedence_over_ambiguous_reference(self):
        with duckdb.connect() as connection:
            connection.execute("""
                CREATE TEMP VIEW csv_pdf_race_summary AS
                SELECT '15' AS car_number, '7643' AS manufacturer_source_id,
                    'Mercedes' AS manufacturer, 'matched_override' AS manufacturer_mapping_status
            """)
            connection.execute("""
                CREATE TEMP VIEW manufacturer_reference AS
                SELECT '7643' AS manufacturer_source_id, NULL::VARCHAR AS manufacturer,
                    'ambiguous' AS manufacturer_mapping_status, 2 AS manufacturer_name_count
            """)
            result = enrich_csv_pdf_manufacturers(connection, Path(__file__).resolve().parent.parent)
            self.assertEqual(result.fetchall(), [('15', '7643', 'Mercedes', 'matched_override', 2)])
            self.assertEqual(len(result.columns), len(set(result.columns)))

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

    def test_collects_evidence_from_both_silver_reports(self):
        with duckdb.connect() as connection:
            connection.execute("""
                CREATE TEMP VIEW silver_classification AS
                SELECT
                    * FROM (VALUES
                        ('classification-a', 'class-version', '74', 'BMW'),
                        ('classification-a', 'class-version', NULL, 'BMW')
                    ) AS t(
                        source_id,
                        bronze_sha256,
                        manufacturer_source_id,
                        manufacturer
                    )
            """)

            connection.execute("""
                CREATE TEMP VIEW silver_car_entries AS
                SELECT
                    * FROM (VALUES
                        ('pits-a', 'pit-version', '74', 'BMW'),
                        ('pits-a', 'pit-version', '7665', NULL)
                    ) AS t(
                        source_id,
                        bronze_sha256,
                        manufacturer_source_id,
                        manufacturer
                    )
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
                SELECT *, NULL::VARCHAR AS manufacturer, NULL::VARCHAR AS manufacturer_mapping_status
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

            participants = enrich_csv_pdf_manufacturers(
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
                    '74' AS manufacturer_source_id,
                    NULL::VARCHAR AS manufacturer,
                    NULL::VARCHAR AS manufacturer_mapping_status
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
                enrich_csv_pdf_manufacturers(
                    connection,
                    project_directory,
                )

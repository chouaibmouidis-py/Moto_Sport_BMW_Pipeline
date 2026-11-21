"""Verify normalization of classification CSV fields from Bronze."""

import unittest
from pathlib import Path
from moto_sport_bmw_pipeline.silver import transform_classification_csv
import duckdb
from moto_sport_bmw_pipeline.quality import validate_classification_gaps, build_classification_gap_issues


class SilverClassificationCsvTests(unittest.TestCase):
    def test_normalizes_fields_and_preserves_car_number(self):
        with duckdb.connect() as connection:
            connection.execute("""
                CREATE TEMP VIEW bronze_classification_csv AS
                SELECT
                    'test-source' AS source_id,
                    'test-bronze-hash' AS bronze_sha256,
                    *
                FROM (VALUES
                    (' 04 ', ' BMW M4 GT3 ', '4', ' GTD ', ' Classified ', ' 74 ', 	' Team Test ', '100', '42', '219.6', '1:00:00.000', '1:30.000', '+3.028', '1 Lap')
                ) AS t(
                    NUMBER, VEHICLE, POSITION, CLASS, STATUS, IMSA_ManufacturerId, TEAM, LAPS, FL_LAPNUM, FL_KPH, TOTAL_TIME, FL_TIME, GAP_FIRST, GAP_PREVIOUS
                )
            """)

            project_directory = Path(__file__).resolve().parent.parent

            result = transform_classification_csv(
                connection,
                project_directory,
            )
            rows = result.fetchall()

            self.assertEqual(
                rows,
                [(
                    "test-source",                  # source_id
                    "test-bronze-hash",             # bronze_sha256
                    "04",                          # car_number
                    "BMW M4 GT3",                   # car_model
                    4,                             # overall_position
                    "GTD",                         # car_class
                    "Classified",                  # classification_status
                    "74",                          # manufacturer_source_id
                    "Team Test",                   # team_name
                    100,                           # completed_laps
                    42,                            # fastest_lap_number
                    219.6,                         # fastest_lap_speed_kph
                    "1:00:00.000",                  # total_time_raw
                    3600.0,                        # total_time_seconds
                    "1:30.000",                     # fastest_lap_time_raw
                    90.0,                          # fastest_lap_time_seconds
                    "+3.028",                      # gap_first_raw
                    "1 Lap",                       # gap_previous_raw
                    "time",                        # gap_first_kind
                    3.028,                         # gap_first_seconds
                    None,                          # gap_first_laps
                    "laps",                        # gap_previous_kind
                    None,                          # gap_previous_seconds
                    1,                             # gap_previous_laps
                )],
            )

    def test_keeps_participant_with_invalid_position(self):
        with duckdb.connect() as connection:
            connection.execute("""
                CREATE TEMP VIEW bronze_classification_csv AS
                SELECT
                    'test-source' AS source_id,
                    'test-bronze-hash' AS bronze_sha256,
                    *
                FROM (VALUES
                    (
                        '24', 'BMW M Hybrid V8', 'inconnue',
                        'GTP', 'Classified', CAST(NULL AS VARCHAR),
                        CAST(NULL AS VARCHAR), -- TEAM
                        CAST(NULL AS VARCHAR), -- LAPS
                        CAST(NULL AS VARCHAR), -- FL_LAPNUM
                        CAST(NULL AS VARCHAR), -- FL_KPH
                        CAST(NULL AS VARCHAR), -- TOTAL_TIME
                        CAST(NULL AS VARCHAR), -- FL_TIME
                        CAST(NULL AS VARCHAR), -- GAP_FIRST
                        CAST(NULL AS VARCHAR)  -- GAP_PREVIOUS
                    )
                ) AS t(
                    NUMBER, VEHICLE, POSITION, CLASS, STATUS, IMSA_ManufacturerId,
                    TEAM, LAPS, FL_LAPNUM, FL_KPH, TOTAL_TIME, FL_TIME,
                    GAP_FIRST, GAP_PREVIOUS
                )
            """)

            project_directory = Path(__file__).resolve().parent.parent

            result = transform_classification_csv(
                connection,
                project_directory,
            )

            rows = result.fetchall()

            self.assertEqual(
                rows,
                [(
                    "test-source",       # source_id
                    "test-bronze-hash",  # bronze_sha256
                    "24",               # car_number
                    "BMW M Hybrid V8",   # car_model
                    None,               # overall_position : "inconnue" non convertible
                    "GTP",              # car_class
                    "Classified",       # classification_status
                    None,               # manufacturer_source_id
                    None,               # team_name
                    None,               # completed_laps
                    None,               # fastest_lap_number
                    None,               # fastest_lap_speed_kph
                    None,               # total_time_raw
                    None,               # total_time_seconds
                    None,               # fastest_lap_time_raw
                    None,               # fastest_lap_time_seconds
                    None,               # gap_first_raw
                    None,               # gap_previous_raw
                    "missing",          # gap_first_kind
                    None,               # gap_first_seconds
                    None,               # gap_first_laps
                    "missing",          # gap_previous_kind
                    None,               # gap_previous_seconds
                    None,               # gap_previous_laps
                )],
            )

    def test_rejects_duplicate_car_numbers_before_transformation(self):
        with duckdb.connect() as connection:
            connection.execute("""
                CREATE TEMP VIEW bronze_classification_csv AS
                SELECT
                    'test-source' AS source_id,
                    'test-bronze-hash' AS bronze_sha256,
                    *
                FROM (VALUES
                    ('24', 'BMW M Hybrid V8', '1', 'GTP', 'Classified'),
                    (' 24 ', 'BMW M Hybrid V8', '2', 'GTP', 'Classified')
                ) AS t(NUMBER, VEHICLE, POSITION, CLASS, STATUS)
            """)

            project_directory = Path(__file__).resolve().parent.parent

            with self.assertRaisesRegex(
                ValueError,
                "duplicate car numbers",
            ):
                transform_classification_csv(
                    connection,
                    project_directory,
                )

    def test_rejects_missing_car_number_before_transformation(self):
        with duckdb.connect() as connection:
            connection.execute("""
                CREATE TEMP VIEW bronze_classification_csv AS
                SELECT
                    'test-source' AS source_id,
                    'test-bronze-hash' AS bronze_sha256,
                    *
                FROM (VALUES
                    ('   ', 'BMW M Hybrid V8', '1', 'GTP', 'Classified')
                ) AS t(NUMBER, VEHICLE, POSITION, CLASS, STATUS)
            """)

            project_directory = Path(__file__).resolve().parent.parent

            with self.assertRaisesRegex(
                ValueError,
                "missing car number",
            ):
                transform_classification_csv(
                    connection,
                    project_directory,
                )

    def test_rejects_time_gap_without_seconds(self):
        with duckdb.connect() as connection:
            connection.execute("""
                    CREATE TEMP VIEW silver_classification_csv AS
                    SELECT
                        'time' AS gap_first_kind,
                        CAST(NULL AS DOUBLE) AS gap_first_seconds,
                        CAST(NULL AS INTEGER) AS gap_first_laps,
                        'marker' AS gap_previous_kind,
                        CAST(NULL AS DOUBLE) AS gap_previous_seconds,
                        CAST(NULL AS INTEGER) AS gap_previous_laps
                """)

            with self.assertRaisesRegex(
                ValueError,
                "1 inconsistent rows"
            ):
                validate_classification_gaps(connection)

    def test_reports_unrecognized_first_gap(self):

        with duckdb.connect() as connection:
            connection.execute("""
                CREATE TEMP TABLE silver_classification_csv AS
                SELECT
                    'test-source' AS source_id,
                    'test-hash' AS bronze_sha256,
                    '24' AS car_number,
                    'to be confirmed' AS gap_first_raw,
                    'unrecognized' AS gap_first_kind
                """)

            gap_issues = build_classification_gap_issues(connection)

            rows = gap_issues.fetchall()

            self.assertEqual(
                rows,
                [(
                    "test-source",
                    "test-hash",
                    "24",
                    "GAP_FIRST",
                    "to be confirmed",
                    "unrecognized_gap_format",
                )]
            )

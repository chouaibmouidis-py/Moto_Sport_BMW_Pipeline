"""Verify cross-season Gold alignment and preservation of unknown values."""

import unittest
from pathlib import Path
from moto_sport_bmw_pipeline.marts import build_gold_race_car_summary
from moto_sport_bmw_pipeline.quality import validate_gold_participant_keys
import duckdb


class GoldRaceCarSummaryTests(unittest.TestCase):
    def test_keeps_same_car_in_different_seasons(self):
        with duckdb.connect() as connection:
            connection.execute("""
                CREATE TEMP VIEW enriched_csv_pdf_participants AS
                SELECT
                    'imsa-weathertech' AS championship,
                    2023 AS season,
                    'road-america' AS event_id,
                    'race-2023' AS session_id,
                    'classification-2023' AS source_id,
                    'version-2023' AS bronze_sha256,
                    '04' AS car_number,
                    'BMW M4 GT3' AS car_model,
                    '74' AS manufacturer_source_id,
                    'BMW' AS manufacturer,
                    'matched' AS manufacturer_mapping_status,
                    CAST(NULL AS INTEGER) AS reported_pit_stop_count,
                    2 AS observed_pit_stop_count,
                    2 AS valid_duration_count,
                    0 AS invalid_duration_count,
                    70.0 AS average_pit_time_seconds,
                    100.0 AS duration_coverage_percent,
                    'unavailable_reported_count' AS comparison_status,
                    'pits-2023' AS pit_stop_source_id,
                    'pit-version-2023' AS pit_stop_bronze_sha256,
                    'GTD' AS car_class,
                    'Classified' AS classification_status,
                    'pdf-2023-hash' AS pdf_sha256,
                    CAST(1 AS BIGINT) AS manufacturer_name_count,
                    'available' AS stop_detail_status,
                    4 AS overall_position,
                    'Team CSV' AS team_name,
                    100 AS completed_laps,
                    42 AS fastest_lap_number,
                    219.6::DOUBLE AS fastest_lap_speed_kph,
                    '1:00:00.000' AS total_time_raw,
                    3600.0::DOUBLE AS total_time_seconds,
                    '1:30.000' AS fastest_lap_time_raw,
                    90.0::DOUBLE AS fastest_lap_time_seconds,
                    '+1:17.343' AS gap_first_raw,
                    '2 Laps' AS gap_previous_raw,
                    'time' AS gap_first_kind,
                    77.343::DOUBLE AS gap_first_seconds,
                    CAST(NULL AS INTEGER) AS gap_first_laps,
                    'laps' AS gap_previous_kind,
                    CAST(NULL AS DOUBLE) AS gap_previous_seconds,
                    2::INTEGER AS gap_previous_laps
            """)

            connection.execute("""
                CREATE TEMP VIEW json_race_car_summary AS
                SELECT
                    championship,
                    2024 AS season,
                    event_id,
                    'race-2024' AS session_id,
                    'classification-2024' AS source_id,
                    'version-2024' AS bronze_sha256,
                    car_number,
                    car_model,
                    'BMW' AS manufacturer,
                    'GTD' AS car_class,
                    '0' AS source_entry_index,
                    2 AS overall_position,
                    3 AS reported_pit_stop_count,
                    3 AS observed_pit_stop_count,
                    3 AS valid_duration_count,
                    0 AS invalid_duration_count,
                    90.0 AS average_pit_time_seconds,
                    100.0 AS duration_coverage_percent,
                    'matched' AS comparison_status,
                    'pits-2024' AS pit_stop_source_id,
                    'pit-version-2024' AS pit_stop_bronze_sha256,
                    FALSE AS not_finished,
                    'Team JSON' AS team_name,
                    120 AS completed_laps,
                    55 AS fastest_lap_number,
                    220.3::DOUBLE AS fastest_lap_speed_kph,
                    '2:00:00.000' AS total_time_raw,
                    7200.0::DOUBLE AS total_time_seconds,
                    CAST(NULL AS VARCHAR) AS fastest_lap_time_raw,
                    CAST(NULL AS DOUBLE) AS fastest_lap_time_seconds,
                    '-' AS gap_first_raw,
                    CAST(NULL AS VARCHAR) AS gap_previous_raw,
                    'marker' AS gap_first_kind,
                    CAST(NULL AS DOUBLE) AS gap_first_seconds,
                    CAST(NULL AS INTEGER) AS gap_first_laps,
                    'missing' AS gap_previous_kind,
                    CAST(NULL AS DOUBLE) AS gap_previous_seconds,
                    CAST(NULL AS INTEGER) AS gap_previous_laps
                FROM enriched_csv_pdf_participants
            """)

            project_directory = Path(__file__).resolve().parent.parent

            result = build_gold_race_car_summary(
                connection,
                project_directory,
            )

            rows = result.project("""
                season,
                source_id,
                bronze_sha256,
                car_number,
                overall_position,
                not_finished
            """).order("season").fetchall()

            self.assertEqual(
                rows,
                [
                    (2023, "classification-2023", "version-2023", "04", 4, None),
                    (2024, "classification-2024", "version-2024", "04", 2, False),
                ],
            )

            manufacturers = result.project("""
                season,
                manufacturer_source_id,
                manufacturer,
                manufacturer_origin,
                manufacturer_mapping_status
            """).order("season").fetchall()

            self.assertEqual(
                manufacturers,
                [
                    (2023, "74", "BMW", "reference", "matched"),
                    (2024, None, "BMW", "source", "not_applicable"),
                ],
            )

            statistics = result.project("""
                season,
                reported_pit_stop_count,
                observed_pit_stop_count,
                average_pit_time_seconds,
                comparison_status,
                pit_stop_source_id,
                pit_stop_bronze_sha256
            """).order("season").fetchall()

            self.assertEqual(
                statistics,
                [
                    (
                        2023, None, 2, 70.0, "unavailable_reported_count",
                        "pits-2023", "pit-version-2023",
                    ),
                    (
                        2024, 3, 3, 90.0, "matched",
                        "pits-2024", "pit-version-2024",
                    ),
                ],
            )

            traceability = result.project("""
                season,
                car_class,
                classification_status,
                source_entry_index,
                pdf_sha256,
                manufacturer_name_count,
                stop_detail_status
            """).order("season").fetchall()

            self.assertEqual(
                traceability,
                [
                    (
                        2023, "GTD", "Classified", None,
                        "pdf-2023-hash", 1, "available",
                    ),
                    (
                        2024, "GTD", None, "0",
                        None, None, "available",
                    ),
                ],
            )
            self.assertEqual(len(result.columns), 45)

            sporting_fields = result.project(
                "season, team_name, completed_laps, "
                "fastest_lap_number, fastest_lap_speed_kph"
            ).order("season").fetchall()

            self.assertEqual(
                sporting_fields,
                [
                    (2023, "Team CSV", 100, 42, 219.6),
                    (2024, "Team JSON", 120, 55, 220.3),
                ],
            )

            duration_fields = result.project(
                "season, total_time_raw, total_time_seconds, "
                "fastest_lap_time_raw, fastest_lap_time_seconds"
            ).order("season").fetchall()

            self.assertEqual(
                duration_fields,
                [
                    (2023, "1:00:00.000", 3600.0, "1:30.000", 90.0),
                    (2024, "2:00:00.000", 7200.0, None, None),
                ],
            )

            gap_fields = result.project(
                "season, gap_first_raw, gap_previous_raw, "
                "gap_first_kind, gap_first_seconds, gap_first_laps, "
                "gap_previous_kind, gap_previous_seconds, gap_previous_laps"
            ).order("season").fetchall()
            self.assertEqual(
                gap_fields,
                [
                    (2023, "+1:17.343", "2 Laps", "time", 77.343, None, "laps", None, 2),
                    (2024, "-", None, "marker", None, None, "missing", None, None),
                ],
            )

    def test_rejects_duplicate_participant_keys(self):
        with duckdb.connect() as connection:
            connection.execute("""
                CREATE TEMP VIEW gold_race_car_summary AS
                SELECT *
                FROM (VALUES
                    ('classification-a', 'version-1', '04'),
                    ('classification-a', 'version-1', '04')
                ) AS t(source_id, bronze_sha256, car_number)
            """)

            with self.assertRaisesRegex(
                ValueError,
                "duplicate participant keys",
            ):
                validate_gold_participant_keys(connection)

    def test_rejects_missing_participant_keys(self):
        cases = [
            (None, "version-1", "04"),
            ("classification-a", None, "04"),
            ("classification-a", "version-1", "   "),
        ]

        for source_id, bronze_sha256, car_number in cases:
            with self.subTest(
                source_id=source_id,
                bronze_sha256=bronze_sha256,
                car_number=car_number,
            ):
                with duckdb.connect() as connection:
                    connection.sql("""
                        SELECT
                            CAST(? AS VARCHAR) AS source_id,
                            CAST(? AS VARCHAR) AS bronze_sha256,
                            CAST(? AS VARCHAR) AS car_number
                    """, params=[
                        source_id,
                        bronze_sha256,
                        car_number,
                    ]).create_view("gold_race_car_summary")

                    with self.assertRaisesRegex(
                        ValueError,
                        "missing participant keys",
                    ):
                        validate_gold_participant_keys(connection)

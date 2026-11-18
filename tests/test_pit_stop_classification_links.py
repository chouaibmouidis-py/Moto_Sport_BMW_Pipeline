"""Verify the same participant-link rule in the JSON and CSV/PDF mart paths."""

from pathlib import Path
import unittest

import duckdb

from moto_sport_bmw_pipeline.marts import (
    build_classification_marts,
    build_csv_pdf_race_summary,
    build_pit_stop_counts,
)
from moto_sport_bmw_pipeline.quality import (
    build_source_pairs,
    validate_pit_stop_classification_links,
)


PROJECT_DIRECTORY = Path(__file__).resolve().parent.parent


class PitStopClassificationLinksTests(unittest.TestCase):
    def prepare_inputs(self, connection, classification_view, stop_view):
        connection.execute("""
            CREATE TEMP VIEW source_sessions AS
            SELECT * FROM (VALUES
                ('classification-a', 'imsa', 2025, 'event-a', 'race-a', 'classification'),
                ('pits-a', 'imsa', 2025, 'event-a', 'race-a', 'pit_stops'),
                ('classification-b', 'imsa', 2025, 'event-b', 'race-b', 'classification'),
                ('pits-b', 'imsa', 2025, 'event-b', 'race-b', 'pit_stops')
            ) AS t(source_id, championship, season, event_id, session_id, document_type)
        """)
        connection.sql("""
            SELECT * FROM (VALUES
                ('classification-a', 'class-version-a', '24'),
                ('classification-a', 'class-version-a', '70'),
                ('classification-b', 'class-version-b', '99')
            ) AS t(source_id, bronze_sha256, car_number)
        """).create_view(classification_view)
        connection.execute(f"""
            CREATE TEMP TABLE {stop_view} (
                source_id VARCHAR,
                bronze_sha256 VARCHAR,
                pdf_sha256 VARCHAR,
                car_number VARCHAR,
                pit_number INTEGER,
                pit_time_in_seconds DOUBLE
            )
        """)
        build_source_pairs(connection, PROJECT_DIRECTORY)

    def test_both_builders_reject_car_found_only_in_another_classification(self):
        for classification_view, stop_view, builder in (
            ("silver_classification", "silver_pit_stops", build_classification_marts),
            ("silver_classification_csv", "silver_pdf_pit_stops", build_csv_pdf_race_summary),
        ):
            with self.subTest(builder=builder.__name__):
                with duckdb.connect() as connection:
                    self.prepare_inputs(connection, classification_view, stop_view)
                    connection.execute(f"""
                        INSERT INTO {stop_view}
                        VALUES ('pits-a', 'pit-version-a', 'pdf-a', '99', 1, 60.0)
                    """)
                    with self.assertRaisesRegex(
                        ValueError, "stops without classification",
                    ) as error:
                        builder(connection, PROJECT_DIRECTORY)
                    self.assertIn("('pits-a', '99')", str(error.exception))

    def test_both_formats_accept_classified_participants_without_stop_details(self):
        for classification_view, stop_view in (
            ("silver_classification", "silver_pit_stops"),
            ("silver_classification_csv", "silver_pdf_pit_stops"),
        ):
            with self.subTest(classification_view=classification_view):
                with duckdb.connect() as connection:
                    self.prepare_inputs(connection, classification_view, stop_view)
                    connection.execute(f"""
                        INSERT INTO {stop_view}
                        VALUES ('pits-a', 'pit-version-a', 'pdf-a', '24', 1, 60.0)
                    """)
                    build_pit_stop_counts(
                        connection, PROJECT_DIRECTORY, connection.table(stop_view),
                    )
                    validate_pit_stop_classification_links(connection, classification_view)
                    self.assertEqual(
                        connection.table(classification_view).project("car_number")
                        .order("car_number").fetchall(),
                        [("24",), ("70",), ("99",)],
                    )

    def test_both_formats_accept_an_empty_stop_report(self):
        for classification_view, stop_view in (
            ("silver_classification", "silver_pit_stops"),
            ("silver_classification_csv", "silver_pdf_pit_stops"),
        ):
            with self.subTest(classification_view=classification_view):
                with duckdb.connect() as connection:
                    self.prepare_inputs(connection, classification_view, stop_view)
                    build_pit_stop_counts(
                        connection, PROJECT_DIRECTORY, connection.table(stop_view),
                    )
                    validate_pit_stop_classification_links(connection, classification_view)

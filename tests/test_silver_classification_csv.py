"""Verify normalization of classification CSV fields from Bronze."""

from collections import Counter
from pathlib import Path

import pytest

from moto_sport_bmw_pipeline.quality import (
    build_classification_gap_issues,
    validate_classification_gaps,
)
from moto_sport_bmw_pipeline.silver import transform_classification_csv


def test_applies_only_exact_model_manufacturer_corrections(connection):
    connection.execute("""
        CREATE TEMP VIEW bronze_classification_csv AS
        SELECT 'source' AS source_id, 'hash' AS bronze_sha256,
            NUMBER, VEHICLE, IMSA_ManufacturerId,
            '1' AS POSITION, 'GTD' AS CLASS, 'Classified' AS STATUS,
            NULL::VARCHAR AS TEAM, NULL::VARCHAR AS LAPS,
            NULL::VARCHAR AS FL_LAPNUM, NULL::VARCHAR AS FL_KPH,
            NULL::VARCHAR AS TOTAL_TIME, NULL::VARCHAR AS FL_TIME,
            NULL::VARCHAR AS GAP_FIRST, NULL::VARCHAR AS GAP_PREVIOUS
        FROM (VALUES
            ('15', ' Mercedes-AMG GT3 ', '7643'),
            ('13', 'Duqueine D08', '7665'),
            ('16', 'MERCEDES-AMG GT3', '7643'),
            ('17', 'mercedes-amg gt3', '7643'),
            ('18', 'DUQUEINE D08', '7665'),
            ('19', 'duqueine d08', '7665'),
            ('24', 'Unknown GT3', '9999')
        ) AS t(NUMBER, VEHICLE, IMSA_ManufacturerId)
    """)
    result = transform_classification_csv(
        connection, Path(__file__).resolve().parent.parent
    )
    assert Counter(
        result.project(
            "car_number, manufacturer_source_id, manufacturer, manufacturer_mapping_status"
        ).fetchall()
    ) == Counter(
        [
            ("15", "7643", "Mercedes", "matched_override"),
            ("13", "7665", "Duqueine", "matched_override"),
            ("16", "7643", "Mercedes", "matched_override"),
            ("17", "7643", "Mercedes", "matched_override"),
            ("18", "7665", "Duqueine", "matched_override"),
            ("19", "7665", "Duqueine", "matched_override"),
            ("24", "9999", None, None),
        ]
    )
    assert (
        connection.sql(
            "SELECT VEHICLE FROM bronze_classification_csv WHERE NUMBER = '15'"
        ).fetchone()[0]
        == " Mercedes-AMG GT3 "
    )
    assert (
        result.filter("car_number = '16'").project("car_model").fetchone()[0]
        == "MERCEDES-AMG GT3"
    )


def test_normalizes_fields_and_preserves_car_number(connection):
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

    assert rows == [
        (
            "test-source",
            "test-bronze-hash",
            "04",
            "BMW M4 GT3",
            4,
            "GTD",
            "Classified",
            "74",
            "Team Test",
            100,
            42,
            219.6,
            "1:00:00.000",
            3600.0,
            "1:30.000",
            90.0,
            "+3.028",
            "1 Lap",
            "time",
            3.028,
            None,
            "laps",
            None,
            1,
            None,
            None,
        )
    ]


def test_keeps_participant_with_invalid_position(connection):
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

    assert rows == [
        (
            "test-source",
            "test-bronze-hash",
            "24",
            "BMW M Hybrid V8",
            None,
            "GTP",
            "Classified",
            None,
            None,
            None,
            None,
            None,
            None,
            None,
            None,
            None,
            None,
            None,
            "missing",
            None,
            None,
            "missing",
            None,
            None,
            None,
            None,
        )
    ]


def test_rejects_duplicate_car_numbers_before_transformation(connection):
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

    with pytest.raises(ValueError, match="duplicate car numbers"):
        transform_classification_csv(
            connection,
            project_directory,
        )


def test_rejects_missing_car_number_before_transformation(connection):
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

    with pytest.raises(ValueError, match="missing car number"):
        transform_classification_csv(
            connection,
            project_directory,
        )


def test_rejects_time_gap_without_seconds(connection):
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

    with pytest.raises(ValueError, match="1 inconsistent rows"):
        validate_classification_gaps(connection)


def test_reports_unrecognized_first_gap(connection):
    connection.execute("""
        CREATE TEMP TABLE silver_classification_csv AS
        SELECT
            'test-source' AS source_id,
            'test-hash' AS bronze_sha256,
            '24' AS car_number,
            'to be confirmed' AS gap_first_raw,
            'unrecognized' AS gap_first_kind,
            '-' AS gap_previous_raw,
            'marker' AS gap_previous_kind
        """)

    gap_issues = build_classification_gap_issues(connection)

    rows = gap_issues.fetchall()

    assert rows == [
        (
            "test-source",
            "test-hash",
            "24",
            "GAP_FIRST",
            "to be confirmed",
            "unrecognized_gap_format",
        )
    ]


def test_reports_both_unrecognized_gaps(connection):
    connection.execute("""
        CREATE TEMP TABLE silver_classification_csv AS
        SELECT
            'test-source' AS source_id,
            'test-hash' AS bronze_sha256,
            '24' AS car_number,
            'unrecognized' AS gap_first_kind,
            'to be confirmed' AS gap_first_raw,
            'unrecognized' AS gap_first_kind,
            'pending review' AS gap_previous_raw,
            'unrecognized' AS gap_previous_kind
        """)

    gap_issues = build_classification_gap_issues(connection)

    rows = gap_issues.fetchall()

    assert Counter(rows) == Counter(
        [
            (
                "test-source",
                "test-hash",
                "24",
                "GAP_FIRST",
                "to be confirmed",
                "unrecognized_gap_format",
            ),
            (
                "test-source",
                "test-hash",
                "24",
                "GAP_PREVIOUS",
                "pending review",
                "unrecognized_gap_format",
            ),
        ]
    )

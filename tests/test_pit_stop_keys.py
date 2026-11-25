"""Verify missing and duplicate pit-stop key counts, including empty input."""

from pathlib import Path

import pytest


@pytest.fixture
def integrity_path(tmp_path):
    source_path = tmp_path / "source.json"
    metada_path = tmp_path / "metadata.json"

    return (source_path, metada_path)


def test_counts_missing_keys(connection):
    connection.execute("""
        CREATE TEMP VIEW silver_pit_stops AS
        SELECT *
        FROM (VALUES
            ('course-a', '24', 1),
            (NULL,       '24', 2),
            ('course-a', NULL, 3),
            ('course-a', '24', NULL),
            (NULL, '25', NULL)
        ) AS t(source_id, car_number, pit_number)
    """)
    query_path = (
        Path(__file__).resolve().parent.parent
        / "sql"
        / "08_check_missing_pit_stop_keys.sql"
    )
    query = query_path.read_text(encoding="utf-8")
    invalid_key_count = connection.sql(query).fetchone()[0]
    assert invalid_key_count == 4


def test_counts_duplicate_keys(connection):
    connection.execute("""
        CREATE TEMP VIEW silver_pit_stops AS
        SELECT *
        FROM (VALUES
            ('course-a', '24', 1),
            ('course-a', '24', 1),
            ('course-a', '24', 2),
            ('course-b', '24', 1)
        ) AS t(source_id, car_number, pit_number)
    """)
    query_path = (
        Path(__file__).resolve().parent.parent
        / "sql"
        / "09_check_duplicate_pit_stop_keys.sql"
    )
    query = query_path.read_text(encoding="utf-8")
    duplicate_key_count = connection.sql(query).fetchone()[0]
    assert duplicate_key_count == 1


@pytest.mark.parametrize(
    "filename",
    [
        "08_check_missing_pit_stop_keys.sql",
        "09_check_duplicate_pit_stop_keys.sql",
    ],
)
def test_empty_table_has_no_key_issues(connection, filename):
    connection.execute("""
        CREATE TEMP TABLE silver_pit_stops (
            source_id VARCHAR,
            car_number VARCHAR,
            pit_number INTEGER
        )
    """)

    query_path = Path(__file__).resolve().parent.parent / "sql" / filename

    issue_count = connection.sql(query_path.read_text(encoding="utf-8")).fetchone()[0]

    assert issue_count == 0

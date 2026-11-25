"""Verify duration statistics, missing values and separation of source versions."""

from pathlib import Path


def test_rounds_average_at_half_millisecond(connection):
    connection.execute("""
        CREATE TEMP VIEW pit_stop_summary_input AS
        SELECT 'test-source' AS source_id,
               'version-1' AS bronze_sha256,
               '24' AS car_number,
               CAST(duration AS DOUBLE) AS pit_time_in_seconds
        FROM (VALUES (86.140), (86.141)) AS t(duration)
    """)
    query_path = (
        Path(__file__).resolve().parent.parent / "sql" / "06_pit_stop_summary.sql"
    )
    result = connection.sql(query_path.read_text(encoding="utf-8"))
    assert result.project("average_pit_time_seconds").fetchall() == [(86.141,)]


def test_summary_with_missing_duration(connection):
    connexion = connection
    connexion.execute("""
        CREATE TEMP VIEW pit_stop_summary_input AS
        SELECT
            'test-source' AS source_id,
            'version-1' AS bronze_sha256,
            *
        FROM (VALUES
            ('24', 60.0),
            ('24', NULL),
            ('24', 80.0)
        ) AS t(car_number, pit_time_in_seconds)
    """)
    query_path = (
        Path(__file__).resolve().parent.parent / "sql" / "06_pit_stop_summary.sql"
    )
    query = query_path.read_text(encoding="utf-8")
    rows = connexion.sql(query).fetchall()
    assert rows == [("test-source", "version-1", "24", 3, 2, 1, 70.0, 66.67)]


def test_summary_with_only_missing_durations(connection):
    connexion = connection
    connexion.execute("""
    CREATE TEMP VIEW pit_stop_summary_input AS
    SELECT 'test-source' AS source_id, 'version-1' AS bronze_sha256, *
        FROM (VALUES
            ('25', NULL),
            ('25', NULL)
        ) AS t(car_number, pit_time_in_seconds)
    """)
    query_path = (
        Path(__file__).resolve().parent.parent / "sql" / "06_pit_stop_summary.sql"
    )
    query = query_path.read_text(encoding="utf-8")
    rows = connexion.sql(query).fetchall()
    assert rows == [("test-source", "version-1", "25", 2, 0, 2, None, 0.0)]


def test_keeps_sources_separate(connection):
    connexion = connection
    connexion.execute("""
        CREATE TEMP VIEW pit_stop_summary_input AS
        SELECT *
        FROM (VALUES
            ('course-a', 'version-1', '24', 60.0),
            ('course-a', 'version-1', '24', 80.0),
            ('course-b', 'version-1', '24', 100.0)
        ) AS t(source_id, bronze_sha256, car_number, pit_time_in_seconds)
    """)

    query_path = (
        Path(__file__).resolve().parent.parent / "sql" / "06_pit_stop_summary.sql"
    )
    query = query_path.read_text(encoding="utf-8")
    rows = connexion.sql(query).fetchall()
    expected = [
        ("course-a", "version-1", "24", 2, 2, 0, 70.0, 100.0),
        ("course-b", "version-1", "24", 1, 1, 0, 100.0, 100.0),
    ]
    assert rows == expected


def test_keeps_versions_separate(connection):
    connexion = connection
    connexion.execute("""
        CREATE TEMP VIEW pit_stop_summary_input AS
        SELECT *
        FROM (VALUES
        ('course-a', 'version-1', '24', 60.0),
        ('course-a', 'version-1', '24', 80.0),
        ('course-a', 'version-2', '24', 100.0)
    ) AS t(source_id, bronze_sha256, car_number, pit_time_in_seconds)
    """)

    query_path = (
        Path(__file__).resolve().parent.parent / "sql" / "06_pit_stop_summary.sql"
    )
    query = query_path.read_text(encoding="utf-8")
    rows = connexion.sql(query).fetchall()
    expected = [
        ("course-a", "version-1", "24", 2, 2, 0, 70.0, 100.0),
        ("course-a", "version-2", "24", 1, 1, 0, 100.0, 100.0),
    ]
    assert rows == expected

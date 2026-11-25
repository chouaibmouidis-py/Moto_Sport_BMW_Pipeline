"""Verify observed stop counts remain separate across sources and versions."""

from collections import Counter
from pathlib import Path

from moto_sport_bmw_pipeline.marts import build_pit_stop_counts


def test_counts_stops_separately_by_source_and_version(connection):
    connection.execute("""
    CREATE TEMP VIEW silver_pit_stops AS
    SELECT *
    FROM (VALUES
        ('course-a', 'version-1', '24'),
        ('course-a', 'version-1', '24'),
        ('course-a', 'version-1', '25'),
        ('course-a', 'version-2', '24'),
        ('course-b', 'version-1', '24')
    ) AS t(source_id, bronze_sha256, car_number)
    """)

    rows = build_pit_stop_counts(
        connection,
        Path(__file__).resolve().parent.parent,
        connection.table("silver_pit_stops"),
    ).fetchall()

    expected = [
        ("course-a", "version-1", "24", 2),
        ("course-a", "version-1", "25", 1),
        ("course-a", "version-2", "24", 1),
        ("course-b", "version-1", "24", 1),
    ]

    assert Counter(rows) == Counter(expected)

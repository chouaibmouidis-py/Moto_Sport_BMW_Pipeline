"""Verify detection of missing and duplicate driver-entry keys."""

from pathlib import Path


def test_counts_missing_and_duplicate_keys(connection):
    connection.execute("""
        CREATE TEMP VIEW silver_driver_entries AS
        SELECT *
        FROM (VALUES
            ('course-a', 'version-1', '0', '0'),
            ('course-a', 'version-1', '0', '0'),
            ('course-a', 'version-1', '0', '1'),
            ('course-a', 'version-2', '0', '0'),
            (NULL, 'version-1', '0', '0'),
            ('course-a', NULL, '0', '0'),
            ('course-a', 'version-1', NULL, '0'),
            ('course-a', 'version-1', '0', NULL)
        ) AS t(
            source_id,
            bronze_sha256,
            source_entry_index,
            source_driver_index
        )
    """)

    query_path = (
        Path(__file__).resolve().parent.parent
        / "sql"
        / "15_check_driver_entry_keys.sql"
    )

    counts = connection.sql(query_path.read_text(encoding="utf-8")).fetchone()

    assert counts == (4, 1)

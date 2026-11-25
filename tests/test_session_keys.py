"""Verify detection of missing and duplicate session keys."""

from pathlib import Path

import pytest


@pytest.fixture
def integrity_path(tmp_path):
    source_path = tmp_path / "source.json"
    metada_path = tmp_path / "metadata.json"

    return (source_path, metada_path)


def test_counts_missing_and_duplicate_keys(connection):
    connection.execute("""
        CREATE TEMP VIEW silver_sessions AS
        SELECT *
        FROM (VALUES
            ('course-a', 'version-1'),
            ('course-a', 'version-1'),
            ('course-a', 'version-2'),
            (NULL, 'version-1'),
            ('course-b', NULL)
        ) AS t(source_id, bronze_sha256)
    """)

    query_path = (
        Path(__file__).resolve().parent.parent / "sql" / "17_check_session_keys.sql"
    )

    counts = connection.sql(query_path.read_text(encoding="utf-8")).fetchone()

    assert counts == (2, 1)

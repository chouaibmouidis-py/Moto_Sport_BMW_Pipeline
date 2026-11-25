"""Verify validated Parquet replacement and preservation of previous files on failure."""

from collections import Counter
from pathlib import Path
from unittest.mock import patch

import pytest

from silver_writer import publish_silver


def test_write_failure_preserves_previous_file(tmp_path, connection):
    directory = tmp_path
    output_path = Path(directory) / "pit_stops.parquet"
    output_path.write_bytes(b"previous version")
    converted = connection.sql("""
        SELECT '24' AS car_number
    """)

    with patch(
        "duckdb.DuckDBPyRelation.write_parquet",
        side_effect=OSError("Simulated write failure"),
    ):
        with pytest.raises(OSError):
            publish_silver(connection, converted, output_path)

    assert output_path.read_bytes() == b"previous version"


def test_content_mismatch_preserves_previous_file(tmp_path, connection):
    directory = tmp_path
    output_path = Path(directory) / "pit_stops.parquet"
    output_path.write_bytes(b"previous version")
    converted = connection.sql("""
        SELECT '24' AS car_number
    """)
    converted.create_view("silver_pit_stops")

    different_content = connection.sql("""
        SELECT '25' AS car_number
    """)

    objects_before = connection.sql("SHOW TABLES").fetchall()

    with patch(
        "duckdb.DuckDBPyConnection.read_parquet",
        return_value=different_content,
    ):
        with pytest.raises(
            ValueError, match="Parquet publication rejected: saved content differs"
        ) as raised:
            publish_silver(connection, converted, output_path)
        assert f"path={output_path}" in str(raised.value)

    objects_after = connection.sql("SHOW TABLES").fetchall()

    assert Counter(objects_after) == Counter(objects_before)

    assert output_path.read_bytes() == b"previous version"


def test_valid_content_replaces_previous_file(tmp_path, connection):
    directory = tmp_path
    output_path = Path(directory) / "pit_stops.parquet"
    output_path.write_bytes(b"previous version")

    converted = connection.sql("""
        SELECT '04' AS car_number
    """)

    connection.sql("""
        SELECT '99' AS car_number
    """).create_view("silver_pit_stops")

    objects_before = connection.sql("SHOW TABLES").fetchall()

    publish_silver(connection, converted, output_path)

    objects_after = connection.sql("SHOW TABLES").fetchall()

    assert Counter(objects_after) == Counter(objects_before)

    saved = connection.read_parquet(str(output_path))
    rows = saved.fetchall()

    assert rows == [("04",)]


def test_row_count_mismatch_preserves_previous_file(tmp_path, connection):
    directory = tmp_path
    output_path = Path(directory) / "pit_stops.parquet"
    output_path.write_bytes(b"previous version")
    converted = connection.sql("""
        SELECT *
        FROM (VALUES ('24'), ('25')) AS t(car_number)
    """)
    converted.create_view("silver_pit_stops")

    different_content = connection.sql("""
        SELECT '25' AS car_number
    """)

    with patch(
        "duckdb.DuckDBPyConnection.read_parquet",
        return_value=different_content,
    ):
        with pytest.raises(
            ValueError, match="Parquet publication rejected: row count mismatch"
        ) as raised:
            publish_silver(connection, converted, output_path)
        assert f"path={output_path}" in str(raised.value)
        assert "expected=2, saved=1" in str(raised.value)

    assert output_path.read_bytes() == b"previous version"


def test_publishes_car_entries_with_custom_source_view(tmp_path, connection):
    directory = tmp_path
    output_path = Path(directory) / "car_entries.parquet"

    car_entries = connection.sql("""
        SELECT
            'test-source' AS source_id,
            '0' AS source_entry_index,
            '04' AS car_number,
            0 AS pit_stop_count
    """)
    car_entries.create_view("silver_car_entries")

    publish_silver(
        connection,
        car_entries,
        output_path,
    )

    rows = connection.read_parquet(str(output_path)).fetchall()

    assert rows == [("test-source", "0", "04", 0)]

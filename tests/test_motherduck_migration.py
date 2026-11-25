"""Test the additive migration with local DuckDB, never remote credentials."""

from pathlib import Path
from unittest.mock import patch

import duckdb
import pytest

from migrate_motherduck_schema import SPORTING_COLUMNS, migrate_schema
from publish_motherduck import publish_gold


def prepare(connection, directory):
    connection.execute("ATTACH ':memory:' AS bmw_analytics")
    old = Path(directory) / "old.parquet"
    new = Path(directory) / "new.parquet"
    connection.sql("SELECT '04' AS car_number").write_parquet(str(old))
    publish_gold(connection, old, "old-run")
    fields = ", ".join(
        f"NULL::{kind} AS {name}" for name, kind in SPORTING_COLUMNS.items()
    )
    connection.sql("SELECT '04' AS car_number, " + fields).write_parquet(str(new))
    return new


def test_inspection_does_not_change_schema(tmp_path, connection):
    directory = tmp_path
    new = prepare(connection, directory)
    assert migrate_schema(connection, new) == SPORTING_COLUMNS
    assert (
        len(connection.sql("SELECT * FROM bmw_analytics.main.gold_history").columns)
        == 2
    )


def test_adds_columns_preserves_old_publication_then_accepts_new_run(
    tmp_path, connection
):
    directory = tmp_path
    new = prepare(connection, directory)
    assert migrate_schema(connection, new, apply=True) == SPORTING_COLUMNS
    assert connection.sql(
        "SELECT * FROM bmw_analytics.main.race_car_summary"
    ).fetchall() == [("04", "old-run")]
    assert connection.sql(
        "SELECT * FROM bmw_analytics.main.current_gold_run"
    ).fetchall() == [("old-run",)]
    assert migrate_schema(connection, new, apply=True) == {}
    publish_gold(connection, new, "new-run")
    assert connection.sql(
        "SELECT publication_run_id FROM bmw_analytics.main.race_car_summary"
    ).fetchall() == [("new-run",)]
    assert (
        connection.sql(
            "SELECT COUNT(*) FROM bmw_analytics.main.gold_history"
        ).fetchone()[0]
        == 2
    )


def test_rejects_type_change_before_writing(tmp_path, connection):
    directory = tmp_path
    new = prepare(connection, directory)
    connection.execute(
        "ALTER TABLE bmw_analytics.main.gold_history ALTER car_number TYPE INTEGER"
    )
    with pytest.raises(ValueError, match="incompatible column car_number"):
        migrate_schema(connection, new, apply=True)
    assert (
        len(connection.sql("SELECT * FROM bmw_analytics.main.gold_history").columns)
        == 2
    )


def test_failure_during_addition_rolls_back_schema_and_view(tmp_path, connection):
    directory = tmp_path
    new = prepare(connection, directory)
    # First ADD succeeds, the second is made invalid to check transactional rollback.
    with patch(
        "migrate_motherduck_schema.quote_identifier",
        side_effect=lambda name: "INVALID SQL !"
        if name == "completed_laps"
        else '"' + name + '"',
    ):
        with pytest.raises(duckdb.Error):
            migrate_schema(connection, new, apply=True)
    assert (
        len(connection.sql("SELECT * FROM bmw_analytics.main.gold_history").columns)
        == 2
    )
    assert connection.sql(
        "SELECT * FROM bmw_analytics.main.race_car_summary"
    ).fetchall() == [("04", "old-run")]

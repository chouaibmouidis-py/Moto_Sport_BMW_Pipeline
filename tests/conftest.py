"""Function-scoped test resources; no shared mutable database state."""

import duckdb
import pytest


@pytest.fixture
def connection():
    """Give each test its own in-memory DuckDB connection and close it afterward."""
    with duckdb.connect() as database_connection:
        yield database_connection


@pytest.fixture
def local_motherduck_connection_factory(tmp_path):
    """Open local connections sharing only this test's temporary archive database."""
    database = tmp_path / "archive.duckdb"
    original_connect = duckdb.connect

    def connect(_database_name=None):
        connection = original_connect()
        quoted_path = str(database).replace("'", "''")
        try:
            connection.execute(f"ATTACH '{quoted_path}' AS bmw_analytics")
        except Exception:
            connection.close()
            raise
        return connection

    return connect


@pytest.fixture
def context_caplog(caplog):
    """Capture pipeline context and remove the capture filter after each test."""
    from moto_sport_bmw_pipeline.logging_config import RunContextFilter

    context_filter = RunContextFilter()
    caplog.handler.addFilter(context_filter)
    try:
        yield caplog
    finally:
        caplog.handler.removeFilter(context_filter)

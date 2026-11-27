import duckdb
import pytest

from moto_sport_bmw_pipeline.bronze_storage import publish_bronze, read_bronze


@pytest.mark.parametrize("storage_format", ["parquet"])
@pytest.mark.parametrize(
    "fault", ["missing_duplicate", "extra_duplicate", "wrong_type"]
)
def test_common_publication_rejects_changed_candidate(tmp_path, storage_format, fault):
    output = tmp_path / f"document.{storage_format}"
    output.write_bytes(b"previous version")
    with duckdb.connect(
        config={"extension_directory": str(tmp_path / "extensions")}
    ) as connection:
        document = connection.sql(
            "SELECT * FROM (VALUES (4::INTEGER), (4::INTEGER)) t(car)"
        )

        def changed_reader(database, path):
            if fault == "wrong_type":
                return database.sql("SELECT 4::BIGINT AS car FROM range(2)")
            count = 1 if fault == "missing_duplicate" else 3
            return database.sql(
                "SELECT 4::INTEGER AS car FROM range(?)", params=[count]
            )

        with pytest.raises(ValueError, match="Bronze publication rejected"):
            publish_bronze(connection, document, output, reader=changed_reader)
        assert (
            connection.sql(
                "SELECT count(*) FROM duckdb_views() WHERE view_name LIKE 'bronze_expected_%' OR view_name LIKE 'bronze_saved_%'"
            ).fetchone()[0]
            == 0
        )
    assert output.read_bytes() == b"previous version"
    assert set(tmp_path.iterdir()) == {output}


@pytest.mark.parametrize("storage_format", ["parquet"])
def test_common_publication_preserves_schema_duplicates_and_nulls(
    tmp_path, storage_format
):
    with duckdb.connect(
        config={"extension_directory": str(tmp_path / "extensions")}
    ) as connection:
        document = connection.sql("""
            SELECT * FROM (VALUES
                ('04', 219.6::DOUBLE, '{"event":1}'::JSON),
                ('04', 219.6::DOUBLE, '{"event":1}'::JSON),
                ('24', NULL::DOUBLE, NULL::JSON)
            ) t(car_number, speed, session)
        """)
        output = tmp_path / f"document.{storage_format}"
        publish_bronze(connection, document, output)
        saved = read_bronze(connection, output, json_columns=("session",))
        assert saved.columns == document.columns
        assert saved.types == document.types
        assert (
            saved.order("car_number").fetchall()
            == document.order("car_number").fetchall()
        )
        assert set(tmp_path.iterdir()) == {output}

import json
from pathlib import Path

import duckdb
import pytest
from vortex_support import VORTEX_EXTENSION_DIRECTORY

from moto_sport_bmw_pipeline import bronze
from moto_sport_bmw_pipeline.bronze_storage import publish_bronze, read_bronze


@pytest.mark.parametrize("storage_format", ["parquet", "vortex"])
@pytest.mark.parametrize(
    "fault", ["missing_duplicate", "extra_duplicate", "wrong_type"]
)
def test_common_publication_rejects_changed_candidate(tmp_path, storage_format, fault):
    output = tmp_path / f"document.{storage_format}"
    output.write_bytes(b"previous version")
    with duckdb.connect(
        config={"extension_directory": str(VORTEX_EXTENSION_DIRECTORY)}
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


@pytest.mark.parametrize("storage_format", ["parquet", "vortex"])
def test_common_publication_preserves_schema_duplicates_and_nulls(
    tmp_path, storage_format
):
    with duckdb.connect(
        config={"extension_directory": str(VORTEX_EXTENSION_DIRECTORY)}
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


@pytest.mark.parametrize("kind", ["classification_json", "pit_json", "csv", "pdf"])
def test_all_bronze_builders_support_common_vortex_publication(
    tmp_path, monkeypatch, kind
):
    source = tmp_path / "source"
    output = tmp_path / "document.vortex"
    options = {"extension_directory": Path(str(VORTEX_EXTENSION_DIRECTORY))}
    if kind == "classification_json":
        source.write_text(
            json.dumps(
                {"session": {}, "fastest_lap": {}, "classification": [{"number": "04"}]}
            ),
            encoding="utf-8",
        )
        bronze.build_classification_document(source, output, **options)
        expected_columns = ["session", "fastest_lap", "classification"]
        expected_rows = [("{}", "{}", '[{"number":"04"}]')]
        json_columns = expected_columns
    elif kind == "pit_json":
        source.write_text('{"session":{},"pit_stop_analysis":[]}', encoding="utf-8")
        bronze.build_document(source, output, **options)
        expected_columns = ["session", "pit_stop_analysis"]
        expected_rows = [("{}", "[]")]
        json_columns = expected_columns
    elif kind == "csv":
        source.write_text("NUMBER;VEHICLE\n 04 ; BMW \n", encoding="utf-8")
        bronze.build_classification_csv(source, output, **options)
        expected_columns = ["NUMBER", "VEHICLE"]
        expected_rows = [(" 04 ", " BMW ")]
        json_columns = ()
    else:
        source.write_bytes(b"PDF fixture")
        monkeypatch.setattr(bronze, "iter_stops", lambda path: [])
        bronze.build_pdf_pit_stop_bronze(source, output, "source-a", **options)
        expected_columns = [
            "source_id",
            "pdf_sha256",
            "car_number",
            "pit_number",
            "pit_time_raw",
            "page_number",
            "column_number",
            "block_line_number",
            "source_line",
        ]
        expected_rows = []
        json_columns = ()
    with duckdb.connect(
        config={"extension_directory": str(options["extension_directory"])}
    ) as connection:
        saved = read_bronze(connection, output, json_columns=json_columns)
        assert saved.columns == expected_columns
        assert saved.fetchall() == expected_rows
    assert set(tmp_path.iterdir()) == {source, output}

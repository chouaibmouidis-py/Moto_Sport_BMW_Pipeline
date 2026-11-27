import hashlib
import json
import logging
from pathlib import Path

import duckdb
import pytest
from vortex_support import VORTEX_EXTENSION_DIRECTORY

from moto_sport_bmw_pipeline import bronze
from moto_sport_bmw_pipeline.bronze import (
    build_classification_document,
    read_vortex_classification,
)
from moto_sport_bmw_pipeline.source_loading import (
    load_classification_bronze,
    load_classification_sources,
)
from moto_sport_bmw_pipeline.timing import measure_duration

logger = logging.getLogger(__name__)


def test_storage_formats_preserve_raw_fields(tmp_path):

    with duckdb.connect(
        config={"extension_directory": str(VORTEX_EXTENSION_DIRECTORY)}
    ) as connection:
        connection.execute("LOAD vortex")

        connection.execute("""
            CREATE TEMP TABLE bronze_sample (
                car_number VARCHAR,
                speed DOUBLE,
                team_raw VARCHAR
            )
        """)

        connection.execute("""
            INSERT INTO bronze_sample VALUES
            ('04', 219.6, ' BMW '),
            ('24', NULL, NULL)
        """)

        parquet_path = tmp_path / "sample.parquet"
        vortex_path = tmp_path / "sample.vortex"

        _, parquet_write_seconds = measure_duration(
            connection.execute,
            "COPY bronze_sample TO ? (FORMAT parquet)",
            [str(parquet_path)],
        )

        _, vortex_write_seconds = measure_duration(
            connection.execute,
            "COPY bronze_sample TO ? (FORMAT vortex)",
            [str(vortex_path)],
        )

        parquet_relation = connection.sql(
            "SELECT * FROM read_parquet(?) ORDER BY car_number",
            params=[str(parquet_path)],
        )

        vortex_relation = connection.sql(
            "SELECT * FROM read_vortex(?) ORDER BY car_number",
            params=[str(vortex_path)],
        )

        parquet_rows = parquet_relation.fetchall()
        vortex_rows = vortex_relation.fetchall()

        expected_rows = [
            ("04", 219.6, " BMW "),
            ("24", None, None),
        ]
        expected_columns = ["car_number", "speed", "team_raw"]
        expected_types = ["VARCHAR", "DOUBLE", "VARCHAR"]

        assert parquet_rows == expected_rows
        assert vortex_rows == expected_rows
        assert parquet_relation.columns == expected_columns
        assert vortex_relation.columns == expected_columns
        assert [str(dtype) for dtype in parquet_relation.types] == expected_types
        assert [str(dtype) for dtype in vortex_relation.types] == expected_types

        logger.info(
            "Parquet write completed: elapsed_seconds=%.6f", parquet_write_seconds
        )
        logger.info(
            "Vortex write completed: elapsed_seconds=%.6f", vortex_write_seconds
        )


def test_vortex_preserves_classification_json_types(tmp_path):

    source_path = (
        Path(__file__).resolve().parent.parent
        / "data/raw/imsa-2024-detroit-race-classification-official"
        / "03_Results_Race_Official.JSON"
    )
    if not source_path.is_file():
        pytest.skip("Local qualification requires the Detroit 2024 Raw report")

    with duckdb.connect(
        config={"extension_directory": str(VORTEX_EXTENSION_DIRECTORY)}
    ) as connection:
        connection.execute("LOAD vortex")

        document = connection.read_json(
            str(source_path),
            format="unstructured",
            columns={
                "session": "JSON",
                "fastest_lap": "JSON",
                "classification": "JSON",
            },
        )

        document.create_view("source_document")

        vortex_path = tmp_path / "document.vortex"

        connection.execute(
            "COPY source_document TO ? (FORMAT vortex)",
            [str(vortex_path)],
        )

        saved = read_vortex_classification(connection, vortex_path)

        assert saved.columns == document.columns
        assert [str(dtype) for dtype in saved.types] == [
            str(dtype) for dtype in document.types
        ]

        source_row = document.project("session, fastest_lap, classification").fetchone()

        saved_row = saved.project("session, fastest_lap, classification").fetchone()

        for index in range(3):
            assert json.loads(saved_row[index]) == json.loads(source_row[index])


def test_rejects_invalid_json_when_reading_vortex(tmp_path):

    with duckdb.connect(
        config={"extension_directory": str(VORTEX_EXTENSION_DIRECTORY)}
    ) as connection:
        vortex_path = tmp_path / "invalid.vortex"

        connection.execute("LOAD vortex")

        connection.execute("""
            CREATE TEMP TABLE invalid_document (
                session VARCHAR,
                fastest_lap VARCHAR,
                classification VARCHAR
            )
        """)

        connection.execute("""
            INSERT INTO invalid_document VALUES (
                '{"event":',
                '{}',
                '[]'
            )
        """)

        connection.execute(
            "COPY invalid_document TO ? (FORMAT vortex)",
            [str(vortex_path)],
        )

        with pytest.raises(duckdb.ConversionException):
            read_vortex_classification(connection, vortex_path).fetchall()


@pytest.fixture
def failed_vortex_write(tmp_path, monkeypatch):

    source_path = tmp_path / "source.json"
    output_path = tmp_path / "document.vortex"

    source_path.write_text(
        '{"session": {}, "fastest_lap": {}, "classification": []}',
        encoding="utf-8",
    )
    output_path.write_bytes(b"previous version")

    original_execute = duckdb.DuckDBPyConnection.execute
    write_attempts = []

    def fail_write(connection, query, parameters=None):
        if (
            query.lstrip().upper().startswith("COPY ")
            and "FORMAT VORTEX" in query.upper()
        ):
            write_attempts.append(query)
            temporary_path = Path(parameters[0])
            temporary_path.write_bytes(b"partial vortex")
            raise OSError("Simulated Vortex write failure")

        if parameters is None:
            return original_execute(connection, query)
        return original_execute(connection, query, parameters)

    monkeypatch.setattr(
        duckdb.DuckDBPyConnection,
        "execute",
        fail_write,
    )

    return source_path, output_path, write_attempts


def test_vortex_write_failure_preserves_previous_file(tmp_path, failed_vortex_write):
    source_path, output_path, write_attempts = failed_vortex_write

    with pytest.raises(OSError, match="Simulated Vortex write failure"):
        build_classification_document(
            source_path,
            output_path,
            extension_directory=Path(str(VORTEX_EXTENSION_DIRECTORY)),
        )

    assert output_path.read_bytes() == b"previous version"
    assert len(write_attempts) == 1
    assert {path.name for path in tmp_path.iterdir()} == {
        "source.json",
        "document.vortex",
    }


def test_publishes_vortex_classification_with_preserved_content(tmp_path):

    source_path = tmp_path / "source.json"
    output_path = tmp_path / "document.vortex"

    expected_document = {
        "session": {"event_name": "Test race"},
        "fastest_lap": {"participant_number": "04"},
        "classification": [{"number": "04", "manufacturer": " BMW ", "position": None}],
    }

    source_path.write_text(
        json.dumps(expected_document),
        encoding="utf-8",
    )

    build_classification_document(
        source_path,
        output_path,
        extension_directory=Path(str(VORTEX_EXTENSION_DIRECTORY)),
    )

    with duckdb.connect(
        config={"extension_directory": str(VORTEX_EXTENSION_DIRECTORY)}
    ) as connection:
        connection.execute("LOAD vortex")

        row = read_vortex_classification(connection, output_path).fetchone()

        saved_document = {
            "session": json.loads(row[0]),
            "fastest_lap": json.loads(row[1]),
            "classification": json.loads(row[2]),
        }

        assert saved_document == expected_document
        assert {path.name for path in tmp_path.iterdir()} == {
            "source.json",
            "document.vortex",
        }


def test_cleanup_failure_preserves_write_error(
    failed_vortex_write, monkeypatch, caplog
):
    source_path, output_path, write_attempts = failed_vortex_write

    def fail_cleanup(path, missing_ok=False):
        raise PermissionError("Simulated cleanup failure")

    with monkeypatch.context() as patcher:
        patcher.setattr(Path, "unlink", fail_cleanup)
        with pytest.raises(OSError, match="Simulated Vortex write failure"):
            build_classification_document(
                source_path,
                output_path,
                extension_directory=Path(str(VORTEX_EXTENSION_DIRECTORY)),
            )

    assert output_path.read_bytes() == b"previous version"
    assert len(write_attempts) == 1
    assert "Could not remove Bronze temporary" in caplog.text
    assert "Simulated cleanup failure" in caplog.text


@pytest.mark.parametrize(
    "changed_root",
    ["session", "fastest_lap", "classification"],
)
def test_rejects_changed_vortex_content(tmp_path, monkeypatch, changed_root):

    source_path = tmp_path / "source.json"
    output_path = tmp_path / "document.vortex"

    source_path.write_text(
        '{"session": {"event_name": "Original"}, '
        '"fastest_lap": {}, "classification": []}',
        encoding="utf-8",
    )
    output_path.write_bytes(b"previous version")

    def read_changed_content(connection, source_path):
        changed_document = {
            "session": {"event_name": "Original"},
            "fastest_lap": {},
            "classification": [],
        }

        if changed_root == "classification":
            changed_document[changed_root] = [{"number": "99"}]
        else:
            changed_document[changed_root] = {"unexpected": "changed"}

        return connection.sql(
            """
            SELECT
                CAST(? AS JSON) AS session,
                CAST(? AS JSON) AS fastest_lap,
                CAST(? AS JSON) AS classification
            """,
            params=[
                json.dumps(changed_document["session"]),
                json.dumps(changed_document["fastest_lap"]),
                json.dumps(changed_document["classification"]),
            ],
        )

    monkeypatch.setattr(
        "moto_sport_bmw_pipeline.bronze.read_vortex_classification",
        read_changed_content,
    )

    with pytest.raises(
        ValueError,
        match=f"Bronze rejected: content differs for {changed_root}",
    ):
        build_classification_document(
            source_path,
            output_path,
            extension_directory=Path(str(VORTEX_EXTENSION_DIRECTORY)),
        )

    assert output_path.read_bytes() == b"previous version"
    assert {path.name for path in tmp_path.iterdir()} == {
        "source.json",
        "document.vortex",
    }


def test_loads_vortex_classification_with_provenance(tmp_path):

    source_path = tmp_path / "source.json"
    bronze_path = tmp_path / "document.vortex"

    source_path.write_text(
        '{"session": {}, "fastest_lap": {}, "classification": [{"number": "04"}]}',
        encoding="utf-8",
    )

    build_classification_document(
        source_path,
        bronze_path,
        extension_directory=Path(str(VORTEX_EXTENSION_DIRECTORY)),
    )

    expected_sha256 = hashlib.sha256(bronze_path.read_bytes()).hexdigest()

    with duckdb.connect(
        config={"extension_directory": str(VORTEX_EXTENSION_DIRECTORY)}
    ) as connection:
        connection.execute("LOAD vortex")

        load_classification_bronze(connection, bronze_path, "test-source")

        loaded = connection.table("bronze_classification")
        assert loaded.columns == [
            "session",
            "fastest_lap",
            "classification",
            "source_id",
            "bronze_sha256",
        ]
        assert [str(dtype) for dtype in loaded.types] == [
            "JSON",
            "JSON",
            "JSON",
            "VARCHAR",
            "VARCHAR",
        ]

        row = connection.sql("""
            SELECT classification, source_id, bronze_sha256
            FROM bronze_classification
        """).fetchone()

    assert json.loads(row[0]) == [{"number": "04"}]
    assert row[1] == "test-source"
    assert row[2] == expected_sha256


@pytest.mark.parametrize("preload_vortex", [True, False])
def test_loads_two_classification_sources(tmp_path, preload_vortex):
    storage_format = "parquet"

    cases = [
        ("source-a", "04"),
        ("source-b", "24"),
    ]
    sources = []
    expected_rows = []

    for source_id, car_number in cases:
        source_path = tmp_path / f"{source_id}.json"
        bronze_path = (
            tmp_path / "data" / "bronze" / source_id / f"document.{storage_format}"
        )
        document = {
            "session": {},
            "fastest_lap": {},
            "classification": [{"number": car_number}],
        }
        source_path.write_text(json.dumps(document), encoding="utf-8")

        build_classification_document(
            source_path,
            bronze_path,
            extension_directory=Path(str(VORTEX_EXTENSION_DIRECTORY)),
        )

        sources.append({"source_id": source_id})

        expected_sha256 = hashlib.sha256(bronze_path.read_bytes()).hexdigest()

        expected_rows.append((source_id, car_number, expected_sha256))

    with duckdb.connect(
        config={
            "extension_directory": str(VORTEX_EXTENSION_DIRECTORY),
            "autoload_known_extensions": False,
            "autoinstall_known_extensions": False,
        }
    ) as connection:
        if preload_vortex:
            connection.execute("LOAD vortex")
        assert (
            connection.sql(
                "SELECT loaded FROM duckdb_extensions() WHERE extension_name = 'vortex'"
            ).fetchone()[0]
            is preload_vortex
        )

        load_classification_sources(
            connection,
            sources,
            tmp_path,
        )

        rows = connection.sql("""
            SELECT
                source_id,
                json_extract_string(classification, '$[0].number') AS car_number,
                bronze_sha256
            FROM bronze_classification
            ORDER BY source_id
        """).fetchall()

    assert rows == expected_rows


@pytest.mark.parametrize(
    "extension_directory", [None, Path(str(VORTEX_EXTENSION_DIRECTORY))]
)
def test_routes_json_classification_to_parquet(
    tmp_path, monkeypatch, extension_directory
):

    source = {
        "source_id": "source-a",
        "document_type": "classification",
        "format": "json",
        "filename": "report.json",
    }
    calls = []

    def record_build(source_path, output_path, *, extension_directory=None):
        calls.append((source_path, output_path, extension_directory))

    monkeypatch.setattr(
        bronze,
        "build_classification_document",
        record_build,
    )

    result = bronze.build_source(
        tmp_path, source, extension_directory=extension_directory
    )

    expected_source = tmp_path / "data/raw/source-a/report.json"
    expected_output = tmp_path / "data/bronze/source-a/document.parquet"

    assert result == expected_output
    assert calls == [(expected_source, expected_output, extension_directory)]


def test_build_source_produces_loadable_parquet_classification(tmp_path):
    source = {
        "source_id": "source-a",
        "document_type": "classification",
        "format": "json",
        "filename": "report.json",
    }
    source_path = tmp_path / "data/raw/source-a/report.json"
    source_path.parent.mkdir(parents=True)
    document = {
        "session": {"event_name": "Test race"},
        "fastest_lap": {},
        "classification": [{"number": "04", "team": " BMW ", "position": None}],
    }
    source_path.write_text(json.dumps(document), encoding="utf-8")
    extension_directory = Path(str(VORTEX_EXTENSION_DIRECTORY))

    output = bronze.build_source(
        tmp_path, source, extension_directory=extension_directory
    )

    assert output == tmp_path / "data/bronze/source-a/document.parquet"
    with duckdb.connect(
        config={
            "extension_directory": str(extension_directory),
            "autoload_known_extensions": False,
            "autoinstall_known_extensions": False,
        }
    ) as connection:
        load_classification_sources(connection, [source], tmp_path)
        row = connection.sql(
            "SELECT session, fastest_lap, classification, source_id, bronze_sha256 FROM bronze_classification"
        ).fetchone()
        assert [
            str(dtype) for dtype in connection.table("bronze_classification").types
        ] == [
            "JSON",
            "JSON",
            "JSON",
            "VARCHAR",
            "VARCHAR",
        ]
    assert [json.loads(value) for value in row[:3]] == [
        document["session"],
        document["fastest_lap"],
        document["classification"],
    ]
    assert row[3] == "source-a"
    assert row[4] == hashlib.sha256(output.read_bytes()).hexdigest()
    assert json.loads(source_path.read_text(encoding="utf-8")) == document
    assert {path.name for path in output.parent.iterdir()} == {"document.parquet"}


def test_production_bronze_does_not_require_vortex_installation(tmp_path):
    source = {
        "source_id": "source-a",
        "document_type": "classification",
        "format": "csv",
        "filename": "report.csv",
    }
    raw = tmp_path / "data/raw/source-a/report.csv"
    raw.parent.mkdir(parents=True)
    raw.write_text("NUMBER;VEHICLE\n04; BMW \n", encoding="utf-8")
    output = bronze.build_source(
        tmp_path, source, extension_directory=tmp_path / "empty-extensions"
    )
    assert output == tmp_path / "data/bronze/source-a/document.parquet"
    with duckdb.connect(
        config={
            "autoload_known_extensions": False,
            "autoinstall_known_extensions": False,
        }
    ) as connection:
        assert connection.read_parquet(str(output)).fetchall() == [("04", " BMW ")]
        assert not connection.sql(
            "SELECT loaded FROM duckdb_extensions() WHERE extension_name='vortex'"
        ).fetchone()[0]

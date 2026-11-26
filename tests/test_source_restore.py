import hashlib
import json
import sys
from pathlib import Path

import pytest

import restore_sources
from memory_probe import measure_python_memory
from restore_sources import validate_archive_content


@pytest.fixture
def restore_project(tmp_path, local_motherduck_connection_factory, monkeypatch):
    """Provide two archived files and an isolated destination, without cloud access."""
    root = tmp_path / "project"
    (root / "config").mkdir(parents=True)
    (root / "config/source_archive.json").write_text(
        json.dumps({"archive_id": "test-archive", "file_count": 2}),
        encoding="utf-8",
    )
    archived_files = [
        ("data/raw/source-a/report.json", b"BMW"),
        ("data/raw/source-b/report.json", b"IMSA"),
    ]
    with local_motherduck_connection_factory() as connection:
        connection.execute("""
            CREATE TABLE bmw_analytics.main.source_archive (
                source_id VARCHAR,
                relative_path VARCHAR,
                sha256 VARCHAR,
                size_bytes BIGINT,
                content BLOB,
                PRIMARY KEY (relative_path, sha256)
            )
        """)
        connection.execute("""
            CREATE TABLE bmw_analytics.main.source_archive_inventory (
                archive_id VARCHAR,
                relative_path VARCHAR,
                sha256 VARCHAR,
                PRIMARY KEY (archive_id, relative_path)
            )
        """)
        for relative_path, content in archived_files:
            sha256 = hashlib.sha256(content).hexdigest()
            source_id = relative_path.split("/")[2]
            connection.execute(
                "INSERT INTO bmw_analytics.main.source_archive VALUES (?, ?, ?, ?, ?)",
                [source_id, relative_path, sha256, len(content), content],
            )
            connection.execute(
                "INSERT INTO bmw_analytics.main.source_archive_inventory VALUES (?, ?, ?)",
                ["test-archive", relative_path, sha256],
            )

    destination = tmp_path / "restored"
    monkeypatch.setattr(restore_sources, "PROJECT_DIR", root)
    monkeypatch.setattr(
        restore_sources.duckdb, "connect", local_motherduck_connection_factory
    )
    monkeypatch.setenv("motherduck_token", "local-test-only")
    monkeypatch.setattr(
        sys, "argv", ["restore_sources.py", "--destination", str(destination)]
    )
    return destination


@pytest.fixture
def prepare_restore_memory(restore_project, local_motherduck_connection_factory):
    """Build the requested local archive before measuring the real restoration."""

    def prepare(file_count, file_size_bytes):
        content = b" " * (file_size_bytes - 2) + b"{}"
        sha256 = hashlib.sha256(content).hexdigest()
        with local_motherduck_connection_factory() as connection:
            connection.execute(
                "DELETE FROM bmw_analytics.main.source_archive_inventory"
            )
            connection.execute("DELETE FROM bmw_analytics.main.source_archive")
            for index in range(file_count):
                source_id = f"memory-{index}"
                relative_path = f"data/raw/{source_id}/report.json"
                connection.execute(
                    "INSERT INTO bmw_analytics.main.source_archive VALUES (?, ?, ?, ?, ?)",
                    [source_id, relative_path, sha256, file_size_bytes, content],
                )
                connection.execute(
                    "INSERT INTO bmw_analytics.main.source_archive_inventory VALUES (?, ?, ?)",
                    ["test-archive", relative_path, sha256],
                )
        (restore_sources.PROJECT_DIR / "config/source_archive.json").write_text(
            json.dumps({"archive_id": "test-archive", "file_count": file_count}),
            encoding="utf-8",
        )
        return restore_project

    return prepare


def test_accepts_valid_archive_content():

    relative_path = "data/raw/example/report.json"
    content = b"BMW"
    expected_sha256 = hashlib.sha256(content).hexdigest()
    size_bytes = 3

    result = validate_archive_content(
        relative_path,
        expected_sha256,
        size_bytes,
        content,
    )

    assert result is None


def test_rejects_archive_content_with_wrong_hash():

    relative_path = "data/raw/example/report.json"
    content = b"BMW"
    expected_sha256 = hashlib.sha256(b"OTHER").hexdigest()
    size_bytes = 3

    with pytest.raises(ValueError, match="Source restoration rejected: hash mismatch"):
        validate_archive_content(
            relative_path,
            expected_sha256,
            size_bytes,
            content,
        )


def test_rejects_missing_archive_content():

    relative_path = "data/raw/example/report.json"
    expected_sha256 = hashlib.sha256(b"BMW").hexdigest()
    size_bytes = 3
    content = None

    with pytest.raises(
        ValueError, match="Source restoration rejected: missing content"
    ):
        validate_archive_content(
            relative_path,
            expected_sha256,
            size_bytes,
            content,
        )


def test_rejects_archive_content_with_wrong_size():

    relative_path = "data/raw/example/report.json"
    content = b"BMW"
    expected_sha256 = hashlib.sha256(content).hexdigest()
    size_bytes = 4

    with pytest.raises(ValueError, match="Source restoration rejected: size mismatch"):
        validate_archive_content(
            relative_path,
            expected_sha256,
            size_bytes,
            content,
        )


def test_rejects_missing_archive_size():

    relative_path = "data/raw/example/report.json"
    content = b"BMW"
    expected_sha256 = hashlib.sha256(content).hexdigest()
    size_bytes = None

    with pytest.raises(
        ValueError, match="Source restoration rejected: missing content"
    ):
        validate_archive_content(
            relative_path,
            expected_sha256,
            size_bytes,
            content,
        )


def test_restores_two_valid_archive_files(restore_project):

    destination = restore_project

    restore_sources.main()
    first_file = destination / "data/raw/source-a/report.json"
    second_file = destination / "data/raw/source-b/report.json"

    assert first_file.read_bytes() == b"BMW"
    assert second_file.read_bytes() == b"IMSA"


def test_corrupted_second_file_preserves_existing_files(
    restore_project,
    local_motherduck_connection_factory,
):
    destination = restore_project
    first_file = destination / "data/raw/source-a/report.json"
    second_file = destination / "data/raw/source-b/report.json"

    first_file.parent.mkdir(parents=True)
    second_file.parent.mkdir(parents=True)

    first_file.write_bytes(b"previous-a")
    second_file.write_bytes(b"previous-b")

    with local_motherduck_connection_factory() as connection:
        connection.execute(
            """
            UPDATE bmw_analytics.main.source_archive
            SET content = ?
            WHERE relative_path = ?
            """,
            [b"FAIL", "data/raw/source-b/report.json"],
        )

    with pytest.raises(ValueError, match="Source restoration rejected: hash mismatch"):
        restore_sources.main()

    assert first_file.read_bytes() == b"previous-a"
    assert second_file.read_bytes() == b"previous-b"

    remaining_files = {path for path in destination.rglob("*") if path.is_file()}

    assert remaining_files == {first_file, second_file}


def test_stages_first_file_before_fetching_second(
    restore_project, local_motherduck_connection_factory, monkeypatch
):
    destination = restore_project
    first_file = destination / "data/raw/source-a/report.json"
    second_file = destination / "data/raw/source-b/report.json"
    first_file.parent.mkdir(parents=True)
    second_file.parent.mkdir(parents=True)
    first_file.write_bytes(b"previous-a")
    second_file.write_bytes(b"previous-b")

    events = []
    staged_files = {}
    original_stage_restore_file = restore_sources.stage_restore_file

    def record_stage(target_path, content):
        temporary_path = original_stage_restore_file(target_path, content)
        if content in (b"BMW", b"IMSA"):
            label = "A" if content == b"BMW" else "B"
            events.append(("write", label))
            staged_files[label] = temporary_path
        return temporary_path

    def observe_row(row):
        if row is None:
            return
        for value in row:
            if isinstance(value, bytes) and value in (b"BMW", b"IMSA"):
                label = "A" if value == b"BMW" else "B"
                events.append(("fetch", label))
                if label == "B":
                    assert "A" in staged_files, "A must be staged before fetching B"
                    assert staged_files["A"] != first_file
                    assert staged_files["A"].read_bytes() == b"BMW"
                    assert first_file.read_bytes() == b"previous-a"
                    assert second_file.read_bytes() == b"previous-b"

    class ObservedConnection:
        """Forward real queries while observing rows delivered to Python."""

        def __init__(self, connection):
            self.connection = connection

        def __enter__(self):
            return self

        def __exit__(self, *exception):
            return self.connection.__exit__(*exception)

        def execute(self, *args, **kwargs):
            self.connection.execute(*args, **kwargs)
            return self

        def fetchone(self):
            row = self.connection.fetchone()
            observe_row(row)
            return row

        def fetchall(self):
            rows = self.connection.fetchall()
            for row in rows:
                observe_row(row)
            return rows

        def fetchmany(self, size=1):
            rows = self.connection.fetchmany(size)
            for row in rows:
                observe_row(row)
            return rows

    def connect_observed(database_name):
        return ObservedConnection(local_motherduck_connection_factory(database_name))

    monkeypatch.setattr(restore_sources, "stage_restore_file", record_stage)
    monkeypatch.setattr(restore_sources.duckdb, "connect", connect_observed)

    restore_sources.main()

    assert events == [("fetch", "A"), ("write", "A"), ("fetch", "B"), ("write", "B")]
    assert first_file.read_bytes() == b"BMW"
    assert second_file.read_bytes() == b"IMSA"


def test_loads_archive_inventory_without_payloads(
    restore_project,
    local_motherduck_connection_factory,
):

    with local_motherduck_connection_factory() as connection:
        inventory = restore_sources.load_archive_inventory(
            connection,
            "test-archive",
        )

    assert inventory == [
        (
            "data/raw/source-a/report.json",
            hashlib.sha256(b"BMW").hexdigest(),
        ),
        (
            "data/raw/source-b/report.json",
            hashlib.sha256(b"IMSA").hexdigest(),
        ),
    ]


def test_loads_one_archive_file(
    restore_project,
    local_motherduck_connection_factory,
):

    relative_path = "data/raw/source-a/report.json"
    expected_sha256 = hashlib.sha256(b"BMW").hexdigest()

    with local_motherduck_connection_factory() as connection:
        archived_file = restore_sources.load_archive_file(
            connection,
            relative_path,
            expected_sha256,
        )

    assert archived_file == (3, b"BMW")


def test_returns_none_when_archive_hash_does_not_match(
    restore_project,
    local_motherduck_connection_factory,
):

    relative_path = "data/raw/source-a/report.json"
    expected_sha256 = hashlib.sha256(b"OTHER").hexdigest()

    with local_motherduck_connection_factory() as connection:
        archived_file = restore_sources.load_archive_file(
            connection, relative_path, expected_sha256
        )

    assert archived_file is None


def test_returns_none_when_archive_path_does_not_match(
    restore_project, local_motherduck_connection_factory
):

    relative_path = "data/raw/unknown/report.json"
    expected_sha256 = hashlib.sha256(b"BMW").hexdigest()

    with local_motherduck_connection_factory() as connection:
        archived_file = restore_sources.load_archive_file(
            connection, relative_path, expected_sha256
        )

    assert archived_file is None


def test_builds_restore_targets_without_payloads(tmp_path):

    restore_directory = tmp_path / "restored"
    inventory = [
        ("data/raw/source-a/report.json", "hash-a"),
        ("data/raw/source-b/report.json", "hash-b"),
    ]

    targets = restore_sources.build_restore_targets(restore_directory, inventory)

    assert targets == [
        (
            (restore_directory / "data/raw/source-a/report.json").resolve(),
            "data/raw/source-a/report.json",
            "hash-a",
        ),
        (
            (restore_directory / "data/raw/source-b/report.json").resolve(),
            "data/raw/source-b/report.json",
            "hash-b",
        ),
    ]


def test_rejects_restore_target_outside_raw(tmp_path):

    restore_directory = tmp_path / "restored"
    inventory = [("../outside.json", "hash-a")]

    with pytest.raises(ValueError, match="Source restoration rejected: invalid path"):
        restore_sources.build_restore_targets(
            restore_directory,
            inventory,
        )


def test_stages_content_without_replacing_destination(tmp_path):

    target_path = tmp_path / "data/raw/source-a/report.json"
    target_path.parent.mkdir(parents=True)
    target_path.write_bytes(b"previous-a")

    content = b"BMW"

    temporary_path = restore_sources.stage_restore_file(
        target_path,
        content,
    )

    assert temporary_path != target_path
    assert temporary_path.read_bytes() == b"BMW"
    assert target_path.read_bytes() == b"previous-a"


def test_stages_content_when_parent_directory_is_missing(tmp_path):

    target_path = tmp_path / "new/data/raw/source-a/report.json"
    content = b"BMW"

    temporary_path = restore_sources.stage_restore_file(target_path, content)

    assert temporary_path.parent == target_path.parent
    assert temporary_path.read_bytes() == b"BMW"
    assert not target_path.exists()


def test_stages_same_destination_in_distinct_temporary_files(tmp_path):

    target_path = tmp_path / "data/raw/source-a/report.json"

    first_temporary = restore_sources.stage_restore_file(target_path, b"BMW")

    second_temporary = restore_sources.stage_restore_file(target_path, b"IMSA")

    assert first_temporary != second_temporary
    assert first_temporary.read_bytes() == b"BMW"
    assert second_temporary.read_bytes() == b"IMSA"
    assert not target_path.exists()


def test_removes_temporary_file_when_readback_differs(tmp_path, monkeypatch):

    target_path = tmp_path / "report.json"
    target_path.write_bytes(b"previous")

    def read_corrupted_bytes(path):
        return b"corrupted"

    with monkeypatch.context() as patcher:
        patcher.setattr(Path, "read_bytes", read_corrupted_bytes)

        with pytest.raises(
            ValueError,
            match="Source restoration rejected: written content differs",
        ):
            restore_sources.stage_restore_file(target_path, b"BMW")

    assert target_path.read_bytes() == b"previous"
    assert list(tmp_path.iterdir()) == [target_path]


@pytest.mark.parametrize("file_count", [1, 3, 10])
def test_restore_payload_memory_guard(prepare_restore_memory, file_count):

    file_size_bytes = 4 * 1024 * 1024
    max_peak_bytes = 3 * file_size_bytes + 2 * 1024 * 1024

    destination = prepare_restore_memory(file_count, file_size_bytes)

    measurement = measure_python_memory(restore_sources.main)

    assert len(list(destination.rglob("report.json"))) == file_count
    assert measurement["peak_bytes"] < max_peak_bytes


def test_memory_guard_detects_retained_restore_payloads(
    prepare_restore_memory,
    monkeypatch,
):

    file_count = 10
    file_size_bytes = 4 * 1024 * 1024
    max_peak_bytes = 3 * file_size_bytes + 2 * 1024 * 1024

    destination = prepare_restore_memory(file_count, file_size_bytes)

    retained_payloads = []
    original_stage = restore_sources.stage_restore_file

    def stage_and_retain(target_path, content):
        retained_payloads.append(content)
        return original_stage(target_path, content)

    monkeypatch.setattr(
        restore_sources,
        "stage_restore_file",
        stage_and_retain,
    )

    measurement = measure_python_memory(restore_sources.main)

    assert len(list(destination.rglob("report.json"))) == file_count
    assert len(retained_payloads) == file_count
    assert measurement["peak_bytes"] >= max_peak_bytes

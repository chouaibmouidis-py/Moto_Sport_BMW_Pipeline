"""Verify archive integrity, single reads and preservation of the active reference."""

import hashlib
import json
import sys
from unittest.mock import call, patch
import pytest
import archive_sources
from memory_probe import measure_python_memory


@pytest.fixture
def archive_project(tmp_path):
    """Prepare one source with a manifest hash and a previous archive reference."""
    root = tmp_path
    (root / "config").mkdir()
    raw = root / "data/raw/example/report.json"
    raw.parent.mkdir(parents=True)
    content = b'{"classification": []}'
    raw.write_bytes(content)
    (root / "config/sources.json").write_text(
        json.dumps(
            {
                "documents": [
                    {
                        "source_id": "example",
                        "enabled": True,
                        "filename": "report.json",
                        "expected_sha256": hashlib.sha256(content).hexdigest(),
                    }
                ]
            }
        )
    )
    reference = root / "config/source_archive.json"
    reference.write_text('{"archive_id": "previous", "file_count": 1}')
    return root, reference


def test_success_pins_inventory_and_failure_keeps_previous_reference(
    archive_project,
    local_motherduck_connection_factory,
    monkeypatch,
):
    root, reference = archive_project
    monkeypatch.setattr(archive_sources, "PROJECT_DIR", root)
    monkeypatch.setattr(
        archive_sources.duckdb, "connect", local_motherduck_connection_factory
    )
    monkeypatch.setenv("motherduck_token", "local-test-only")
    monkeypatch.setattr(sys, "argv", ["archive_sources.py", "--pin"])

    archive_sources.main()
    verified = json.loads(reference.read_text())
    assert verified["archive_id"] != "previous"
    assert verified["file_count"] == 1

    with local_motherduck_connection_factory() as connection:
        connection.execute(
            "UPDATE bmw_analytics.main.source_archive SET content = 'corrupted'::BLOB"
        )
    reference.write_text('{"archive_id": "previous", "file_count": 1}')

    with pytest.raises(ValueError, match="saved content differs"):
        archive_sources.main()
    assert json.loads(reference.read_text())["archive_id"] == "previous"


def test_archive_reads_source_once(
    archive_project,
    local_motherduck_connection_factory,
    monkeypatch,
):
    root, reference = archive_project
    source_path = root / "data/raw/example/report.json"

    monkeypatch.setattr(archive_sources, "PROJECT_DIR", root)
    monkeypatch.setattr(
        archive_sources.duckdb, "connect", local_motherduck_connection_factory
    )
    monkeypatch.setenv("motherduck_token", "local-test-only")
    monkeypatch.setattr(sys, "argv", ["archive_sources.py", "--pin"])

    with patch.object(
        type(source_path),
        "read_bytes",
        autospec=True,
        side_effect=type(source_path).read_bytes,
    ) as supervisor_reading:
        archive_sources.main()
        supervisor_reading.assert_called_once_with(source_path)


def test_archive_reads_source_once_with_metadata(
    archive_project,
    local_motherduck_connection_factory,
    monkeypatch,
):
    # 1. Remove the manifest hash so main() must use metadata.json.
    root, reference = archive_project
    source_path = root / "data/raw/example/report.json"
    metadata_path = source_path.parent / "metadata.json"
    manifest_path = root / "config/sources.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    expected_sha256 = manifest["documents"][0].pop("expected_sha256")
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")

    # 2. Keep the exact metadata bytes that must appear in the archive.
    metadata_content = json.dumps({"sha256": expected_sha256}, indent=2).encode("utf-8")
    metadata_path.write_bytes(metadata_content)

    # 3. Run the real archiver against the temporary project and local database.
    monkeypatch.setattr(archive_sources, "PROJECT_DIR", root)
    monkeypatch.setattr(
        archive_sources.duckdb, "connect", local_motherduck_connection_factory
    )
    monkeypatch.setenv("motherduck_token", "local-test-only")
    monkeypatch.setattr(sys, "argv", ["archive_sources.py", "--pin"])

    with patch.object(
        type(source_path),
        "read_bytes",
        autospec=True,
        side_effect=type(source_path).read_bytes,
    ) as supervisor_reading:
        archive_sources.main()
        assert supervisor_reading.call_args_list.count(call(source_path)) == 1
        assert supervisor_reading.call_args_list.count(call(metadata_path)) == 1

    # 4. Read the saved metadata row and compare all four fields with our input.
    with local_motherduck_connection_factory() as connection:
        saved = connection.execute(
            """
            SELECT source_id, sha256, size_bytes, content
            FROM bmw_analytics.main.source_archive
            WHERE relative_path = ?
            """,
            ["data/raw/example/metadata.json"],
        ).fetchone()

    assert saved == (
        "example",
        hashlib.sha256(metadata_content).hexdigest(),
        len(metadata_content),
        metadata_content,
    )
    assert json.loads(reference.read_text())["file_count"] == 2


def test_metadata_hash_mismatch_preserves_reference(
    archive_project,
    local_motherduck_connection_factory,
    monkeypatch,
):
    # 1. Force the metadata path, then supply a deliberately incorrect source hash.
    root, reference = archive_project
    source_path = root / "data/raw/example/report.json"
    metadata_path = source_path.parent / "metadata.json"
    manifest_path = root / "config/sources.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["documents"][0].pop("expected_sha256")
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
    metadata_content = json.dumps({"sha256": "incorrect-hash"}).encode("utf-8")
    metadata_path.write_bytes(metadata_content)

    monkeypatch.setattr(archive_sources, "PROJECT_DIR", root)
    monkeypatch.setattr(
        archive_sources.duckdb, "connect", local_motherduck_connection_factory
    )
    monkeypatch.setenv("motherduck_token", "local-test-only")
    monkeypatch.setattr(sys, "argv", ["archive_sources.py", "--pin"])

    # 2. Preserve the old reference, then call main() once inside the exception check.
    previous_reference = reference.read_bytes()
    with pytest.raises(ValueError, match="Raw fingerprint mismatch: example"):
        archive_sources.main()

    # 3. A rejected source must leave the previous reference byte-for-byte intact.
    assert reference.read_bytes() == previous_reference


def test_archives_first_source_before_preparing_second(
    archive_project,
    local_motherduck_connection_factory,
    monkeypatch,
):

    root, reference = archive_project

    second_source_path = root / "data/raw/example-b/report.json"
    second_content = b'{"classification": ["second"]}'

    second_source_path.parent.mkdir(parents=True)
    second_source_path.write_bytes(second_content)

    manifest_path = root / "config/sources.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))

    manifest["documents"].append(
        {
            "source_id": "example-b",
            "enabled": True,
            "filename": "report.json",
            "expected_sha256": hashlib.sha256(second_content).hexdigest(),
        }
    )

    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")

    original_prepare = archive_sources.prepare_archive_file
    active_connections = []

    def connect_locally(database_name):
        connection = local_motherduck_connection_factory(database_name)
        active_connections.append(connection)
        return connection

    def prepare_and_check(project_directory, source_id, source_path, expected_sha256):
        if source_id == "example-b":
            assert active_connections, (
                "The archive connection must be open before preparing B"
            )

            saved_count = (
                active_connections[-1]
                .execute(
                    """
                SELECT COUNT(*)
                FROM bmw_analytics.main.source_archive
                WHERE relative_path = ?
                """,
                    ["data/raw/example/report.json"],
                )
                .fetchone()[0]
            )

            assert saved_count == 1, "A must be inserted before preparing B"

        return original_prepare(
            project_directory,
            source_id,
            source_path,
            expected_sha256,
        )

    monkeypatch.setattr(archive_sources, "PROJECT_DIR", root)
    monkeypatch.setattr(archive_sources.duckdb, "connect", connect_locally)
    monkeypatch.setattr(
        archive_sources,
        "prepare_archive_file",
        prepare_and_check,
    )
    monkeypatch.setenv("motherduck_token", "local-test-only")
    monkeypatch.setattr(sys, "argv", ["archive_sources.py", "--pin"])

    archive_sources.main()


def test_second_source_failure_rolls_back_first_and_preserves_reference(
    archive_project,
    local_motherduck_connection_factory,
    monkeypatch,
):

    root, reference = archive_project
    previous_reference = reference.read_bytes()

    second_source_path = root / "data/raw/example-b/report.json"
    second_content = b'{"classification": ["second"]}'

    second_source_path.parent.mkdir(parents=True)
    second_source_path.write_bytes(second_content)

    manifest_path = root / "config/sources.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))

    manifest["documents"].append(
        {
            "source_id": "example-b",
            "enabled": True,
            "filename": "report.json",
            "expected_sha256": "incorrect-hash",
        }
    )

    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")

    original_prepare = archive_sources.prepare_archive_file
    active_connections = []

    def connect_locally(database_name):
        connection = local_motherduck_connection_factory(database_name)
        active_connections.append(connection)
        return connection

    def prepare_and_check(project_directory, source_id, source_path, expected_sha256):
        if source_id == "example-b":
            assert active_connections, (
                "The archive connection must be open before preparing B"
            )

            saved_count = (
                active_connections[-1]
                .execute(
                    """
                SELECT COUNT(*)
                FROM bmw_analytics.main.source_archive
                WHERE relative_path = ?
                """,
                    ["data/raw/example/report.json"],
                )
                .fetchone()[0]
            )

            assert saved_count == 1, "A must be inserted before preparing B"

        return original_prepare(
            project_directory,
            source_id,
            source_path,
            expected_sha256,
        )

    monkeypatch.setattr(archive_sources, "PROJECT_DIR", root)
    monkeypatch.setattr(archive_sources.duckdb, "connect", connect_locally)
    monkeypatch.setattr(
        archive_sources,
        "prepare_archive_file",
        prepare_and_check,
    )
    monkeypatch.setenv("motherduck_token", "local-test-only")
    monkeypatch.setattr(sys, "argv", ["archive_sources.py", "--pin"])

    with pytest.raises(
        ValueError,
        match="Raw fingerprint mismatch: example-b",
    ):
        archive_sources.main()

    with local_motherduck_connection_factory() as connection:
        saved_count = connection.execute(
            "SELECT COUNT(*) FROM bmw_analytics.main.source_archive"
        ).fetchone()[0]

        inventory_count = connection.execute(
            "SELECT COUNT(*) FROM bmw_analytics.main.source_archive_inventory"
        ).fetchone()[0]

    assert saved_count == 0
    assert inventory_count == 0
    assert reference.read_bytes() == previous_reference


@pytest.mark.parametrize(
    ("file_count", "retain_payloads"),
    [(1, False), (3, False), (10, False), (10, True)],
    ids=["one-file", "three-files", "ten-files", "detect-retained-payloads"],
)
def test_archive_payload_memory_guard(
    archive_project,
    local_motherduck_connection_factory,
    monkeypatch,
    file_count,
    retain_payloads,
):
    root, reference = archive_project
    file_size_bytes = 4 * 1024 * 1024
    max_peak_bytes = 3 * file_size_bytes + 2 * 1024 * 1024

    documents = []
    content = b" " * (file_size_bytes - 2) + b"{}"
    expected_sha256 = hashlib.sha256(content).hexdigest()

    for index in range(file_count):
        source_id = f"memory-{index}"
        source_path = root / "data/raw" / source_id / "report.json"
        source_path.parent.mkdir(parents=True)
        source_path.write_bytes(content)
        documents.append(
            {
                "source_id": source_id,
                "enabled": True,
                "filename": "report.json",
                "expected_sha256": expected_sha256,
            }
        )

    del content

    source = root / "config/sources.json"

    source.write_text(json.dumps({"documents": documents}), encoding="utf-8")

    monkeypatch.setattr(archive_sources, "PROJECT_DIR", root)
    monkeypatch.setattr(
        archive_sources.duckdb, "connect", local_motherduck_connection_factory
    )
    monkeypatch.setenv("motherduck_token", "local-test-only")
    monkeypatch.setattr(sys, "argv", ["archive_sources.py", "--pin"])

    # Initialize DuckDB's lazy Python imports without reading any measured file.
    # Cold-start/process memory is a separate measurement from payload retention.
    with local_motherduck_connection_factory() as connection:
        connection.execute("SELECT ?", [1]).fetchone()

    retained_payloads = []
    if retain_payloads:
        original_store = archive_sources.store_archive_file

        def store_and_retain(connection, source_file):
            retained_payloads.append(source_file)
            return original_store(connection, source_file)

        monkeypatch.setattr(archive_sources, "store_archive_file", store_and_retain)

    measurement = measure_python_memory(archive_sources.main)

    print(
        f"files={file_count}, "
        f"peak_bytes={measurement['peak_bytes']}, "
        f"limit_bytes={max_peak_bytes}"
    )

    assert json.loads(reference.read_text())["file_count"] == file_count
    if retain_payloads:
        # The guard must catch this deliberate regression, with real archive writes.
        assert len(retained_payloads) == file_count
        assert measurement["peak_bytes"] >= max_peak_bytes
    else:
        assert measurement["peak_bytes"] < max_peak_bytes

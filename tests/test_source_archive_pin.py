"""Verify archive integrity, single reads and preservation of the active reference."""

import hashlib
import json
import sys
from unittest.mock import call, patch
import pytest
import archive_sources


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

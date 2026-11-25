"""Pin the local archive reference only after verified archival succeeds."""

import hashlib
import json
import sys

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

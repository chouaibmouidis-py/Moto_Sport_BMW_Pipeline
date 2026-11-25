import hashlib
from archive_sources import prepare_archive_file
import pytest
from unittest.mock import patch


def test_prepares_verified_archive_file(tmp_path):
    project_directory = tmp_path

    source_path = project_directory / "data/raw/example/report.json"

    source_path.parent.mkdir(parents=True)

    source_path.write_bytes(b"BMW")

    expected_sha256 = hashlib.sha256(b"BMW").hexdigest()

    source_id = "example"

    result = prepare_archive_file(
        project_directory,
        source_id,
        source_path,
        expected_sha256,
    )

    assert result == {
        "source_id": "example",
        "relative_path": "data/raw/example/report.json",
        "sha256": expected_sha256,
        "size_bytes": 3,
        "content": b"BMW",
    }


def test_rejects_incorrect_archive_file_hash(tmp_path):
    source_path = tmp_path / "report.json"

    source_path.write_bytes(b"BMW")

    with pytest.raises(ValueError, match="Raw fingerprint mismatch: example"):
        prepare_archive_file(tmp_path, "example", source_path, "Incorrect-hash")


def test_reads_archive_file_once(tmp_path):
    source_path = tmp_path / "report.json"

    source_path.write_bytes(b"BMW")

    expected_sha256 = hashlib.sha256(b"BMW").hexdigest()

    with patch.object(
        type(source_path),
        "read_bytes",
        autospec=True,
        side_effect=type(source_path).read_bytes,
    ) as supervisor_reading:
        prepare_archive_file(tmp_path, "example", source_path, expected_sha256)

        supervisor_reading.assert_called_once_with(source_path)

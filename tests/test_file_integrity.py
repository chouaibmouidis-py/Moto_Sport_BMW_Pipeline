"""Verify local file integrity against recorded SHA-256 metadata."""

import hashlib
import json

import pytest

from file_integrity import verify_local_file


@pytest.fixture
def integrity_path(tmp_path):
    source_path = tmp_path / "source.json"
    metada_path = tmp_path / "metadata.json"

    return (source_path, metada_path)


def test_missing_metadata_raises(integrity_path):
    source_path, metadata_path = integrity_path

    source_path.write_bytes(b"{}")

    with pytest.raises(FileNotFoundError):
        verify_local_file(source_path, metadata_path)


def test_hash_mismatch_raises(integrity_path):
    source_path, metadata_path = integrity_path

    source_path.write_bytes(b"BMW")

    metadata_path.write_text('{"sha256": "empreinte_incorrect"}', encoding="utf-8")

    with pytest.raises(ValueError):
        verify_local_file(source_path, metadata_path)


def test_matching_hash_is_accepted(integrity_path):
    source_path, metadata_path = integrity_path

    source_path.write_bytes(b"BMW")

    expected_hash = hashlib.sha256(source_path.read_bytes()).hexdigest()

    metadata = {"sha256": expected_hash}

    metadata_path.write_text(json.dumps(metadata), encoding="utf-8")

    verify_local_file(source_path, metadata_path)

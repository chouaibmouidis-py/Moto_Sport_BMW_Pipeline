"""Verify local file integrity against recorded SHA-256 metadata."""

import unittest
import tempfile
from pathlib import Path
from file_integrity import verify_local_file
import hashlib
import json

class FileIntegrityTests(unittest.TestCase):
    def test_missing_metadata_raises(self):
        with tempfile.TemporaryDirectory() as directory:
            source_path = Path(directory) / "source.json"
            metadata_path = Path(directory) / "metadata.json"

            source_path.write_bytes(b"{}")

            self.assertRaises(
                FileNotFoundError,
                verify_local_file,
                source_path,
                metadata_path,
            )

    def test_hash_mismatch_raises(self):
        with tempfile.TemporaryDirectory() as directory:
            source_path = Path(directory) / "source.json"
            metadata_path = Path(directory) / "metadata.json"

            source_path.write_bytes(b"BMW")
            metadata_path.write_text('{"sha256": "empreinte_incorrect"}', encoding="utf-8")
            self.assertRaises(
                ValueError,
                verify_local_file,
                source_path,
                metadata_path,
            )

    def test_matching_hash_is_accepted(self):
        with tempfile.TemporaryDirectory() as directory:
            source_path = Path(directory) / "source.json"
            metadata_path = Path(directory) / "metadata.json"

            source_path.write_bytes(b"BMW")
            expected_hash = hashlib.sha256(source_path.read_bytes()).hexdigest()

            metadata = {"sha256": expected_hash}
            metadata_path.write_text(json.dumps(metadata), encoding="utf-8")
            verify_local_file(source_path, metadata_path)

"""Verify pit-stop Bronze round trips and preservation of previous files on failure."""

import json
import tempfile
import unittest
from pathlib import Path
from build_bronze import build_document
from unittest.mock import patch

from download import SOURCE_FILENAME, download


class DownloadTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.destination = Path(self.directory.name) / "raw"
        self.target = self.destination / SOURCE_FILENAME
        self.url = "https://example.invalid/source.json"

    def test_invalid_json_preserves_previous_file(self):
        source_path = Path(self.directory.name) / "source.json"
        output_path = Path(self.directory.name) / "document.parquet"
        source_path.write_bytes(b'{"session":')
        output_path.write_bytes(b"ancienne version")
        self.assertRaises(json.JSONDecodeError, build_document, source_path, output_path)
        self.assertEqual(output_path.read_bytes(), b"ancienne version")

    def test_rejects_non_parquet_output(self):
        directory = Path(self.directory.name)
        source_path = directory / "source.json"
        output_path = directory / "metadata.json"
        self.assertRaises(ValueError, build_document, source_path, output_path)

    def test_write_failure_preserves_previous_files(self):
        directory = Path(self.directory.name)
        source_path = directory / "source.json"
        output_path = directory / "document.parquet"
        source_path.write_bytes(b'{"session": {}, "pit_stop_analysis": []}')
        output_path.write_bytes(b"ancienne version")
        with patch(
            "duckdb.DuckDBPyRelation.write_parquet",
            side_effect=OSError("Simulated write failure")
        ):
            self.assertRaises(
                OSError,
                build_document,
                source_path,
                output_path,
            )
            self.assertEqual(output_path.read_bytes(), b"ancienne version")









if __name__ == "__main__":
    unittest.main()

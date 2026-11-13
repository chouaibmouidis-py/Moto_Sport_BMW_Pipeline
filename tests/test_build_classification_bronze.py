"""Verify classification Bronze conversion and failure-safe publication."""

import tempfile
import unittest
from pathlib import Path
import json
from build_classification_bronze import build_classification_document
from unittest.mock import patch
import duckdb
from build_classification_bronze import select_classification_sources

class BuildClassificationBronzeTests(unittest.TestCase):
    def test_invalid_json_preserves_previous_file(self):
        with tempfile.TemporaryDirectory() as directory:
            source_path = Path(directory) / "source.json"
            output_path = Path(directory) / "document.parquet"

            source_path.write_bytes(b"invalid json")
            output_path.write_bytes(b"previous version")

            with self.assertRaises(json.JSONDecodeError):
                build_classification_document(source_path, output_path)

            self.assertEqual(
                output_path.read_bytes(),
                b"previous version",
            )

    def test_write_failure_preserves_previous_file(self):
        with tempfile.TemporaryDirectory() as directory:
            source_path = Path(directory) / "source.json"
            output_path = Path(directory) / "document.parquet"

            source_path.write_text(
                json.dumps({
                    "session": {},
                    "fastest_lap": {},
                    "classification": [],
                }),
                encoding="utf-8",
            )
            output_path.write_bytes(b"previous version")

            with patch(
                "duckdb.DuckDBPyRelation.write_parquet",
                side_effect=OSError("Simulated write failure"),
            ):
                with self.assertRaises(OSError):
                    build_classification_document(source_path, output_path)

            self.assertEqual(
                output_path.read_bytes(),
                b"previous version",
            )

    def test_preserves_all_three_roots(self):
        document = {
            "session": {"report_mark": "Official"},
            "fastest_lap": {"participant_number": "04"},
            "classification": [
                {
                    "number": "70",
                    "pit_stops": "0",
                    "not_finished": True,
                }
            ],
        }
        with tempfile.TemporaryDirectory() as directory:
            source_path = Path(directory) / "source.json"
            output_path = Path(directory) / "document.parquet"
            source_text = json.dumps(document)
            source_path.write_text(source_text, encoding="utf-8")

            build_classification_document(source_path, output_path)

            with duckdb.connect() as connection:
                saved = connection.read_parquet(str(output_path))
                row = saved.project(
                    "to_json(session), "
                    "to_json(fastest_lap), "
                    "to_json(classification)"
                ).fetchone()

            saved_document = {
                "session": json.loads(row[0]),
                "fastest_lap": json.loads(row[1]),
                "classification": json.loads(row[2]),
            }

            self.assertEqual(saved_document, document)

    def test_selects_only_enabled_classification_sources(self):
        documents = [
            {
                "source_id": "enabled-classification",
                "enabled": True,
                "document_type": "classification",
            },
            {
                "source_id": "disabled-classification",
                "enabled": False,
                "document_type": "classification",
            },
            {
                "source_id": "enabled-pits",
                "enabled": True,
                "document_type": "pit_stops",
            },
            {
                "source_id": "classification-without-enabled",
                "document_type": "classification",
            },
        ]

        selected = select_classification_sources(documents)
        self.assertEqual(selected, [documents[0]])

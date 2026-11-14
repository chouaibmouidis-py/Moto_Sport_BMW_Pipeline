"""Verify that Gold inputs preserve the exact bytes used by a candidate."""

import hashlib
import tempfile
import unittest
from pathlib import Path

from moto_sport_bmw_pipeline.gold import (
    snapshot_gold_input,
    validate_gold_inputs,
    write_gold_input_manifest,
)


class GoldInputTests(unittest.TestCase):
    def test_snapshot_survives_source_replacement(self):
        with tempfile.TemporaryDirectory() as directory:
            project_directory = Path(directory)
            source_path = project_directory / "data" / "source.parquet"
            source_path.parent.mkdir()
            source_path.write_bytes(b"original version")

            run_directory = (
                project_directory / "data" / "gold"
                / "runs" / "candidate-run"
            )

            record = snapshot_gold_input(
                project_directory,
                run_directory,
                source_path,
                role="classification_mart",
            )

            source_path.write_bytes(b"replacement version")

            snapshot_path = run_directory / record["snapshot_path"]

            self.assertEqual(
                snapshot_path.read_bytes(),
                b"original version",
            )
            self.assertEqual(
                record["sha256"],
                hashlib.sha256(b"original version").hexdigest(),
            )
            self.assertEqual(
                record["source_path"],
                "data/source.parquet",
            )
            self.assertEqual(
                record["role"],
                "classification_mart",
            )

    def test_rejects_a_snapshot_changed_after_manifest_creation(self):
        with tempfile.TemporaryDirectory() as directory:
            project_directory = Path(directory)
            source_path = project_directory / "source.parquet"
            source_path.write_bytes(b"original content")
            run_directory = project_directory / "gold-run"

            record = snapshot_gold_input(
                project_directory,
                run_directory,
                source_path,
                role="classification_mart",
            )

            write_gold_input_manifest(
                run_directory,
                source_run_id="source-run",
                inputs=[record],
            )

            # The intact snapshot must pass validation.
            validate_gold_inputs(run_directory)

            snapshot_path = run_directory / record["snapshot_path"]
            snapshot_path.write_bytes(b"altered content")

            with self.assertRaisesRegex(
                ValueError,
                "input snapshot changed",
            ):
                validate_gold_inputs(run_directory)
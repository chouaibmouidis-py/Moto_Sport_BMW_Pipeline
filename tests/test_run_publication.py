"""Verify complete-run activation, current-run resolution and reference preservation on failure."""

import tempfile
import unittest
from pathlib import Path
import json
from run_publication import REQUIRED_OUTPUTS, activate_run, get_current_run
from unittest.mock import patch


class RunPublicationTests(unittest.TestCase):
    def test_missing_classification_comparison_preserves_current_reference(self):
        with tempfile.TemporaryDirectory() as directory:
            data_directory = Path(directory) / "data"
            run_directory = data_directory / "runs" / "new-run"
            run_directory.mkdir(parents=True)
            current_path = data_directory / "current.json"
            previous_content = b'{"run_id": "previous-run"}'
            current_path.write_bytes(previous_content)

            missing_output = "quality/classification_pit_stop_comparison.parquet"
            for relative_path in REQUIRED_OUTPUTS:
                if relative_path == missing_output:
                    continue
                output_path = run_directory / relative_path
                output_path.parent.mkdir(parents=True, exist_ok=True)
                output_path.write_bytes(b"test fixture")

            with self.assertRaisesRegex(
                FileNotFoundError, "classification_pit_stop_comparison"
            ):
                activate_run(run_directory)

            self.assertEqual(current_path.read_bytes(), previous_content)

    def test_incomplete_run_preserves_current_reference(self):
        with tempfile.TemporaryDirectory() as directory:
            data_directory = Path(directory) / "data"
            run_directory = data_directory / "runs" / "new-run"
            run_directory.mkdir(parents=True)

            current_path = data_directory / "current.json"
            previous_content = b'{"run_id": "previous-run"}'
            current_path.write_bytes(previous_content)

            with self.assertRaises(FileNotFoundError):
                activate_run(run_directory)

            self.assertEqual(
                current_path.read_bytes(),
                previous_content,
            )

    def test_complete_run_replaces_current_reference(self):
        with tempfile.TemporaryDirectory() as directory:
            data_directory = Path(directory) / "data"
            run_directory = data_directory / "runs" / "new-run"
            run_directory.mkdir(parents=True)

            current_path = data_directory / "current.json"
            current_path.write_text(
                '{"run_id": "previous-run"}',
                encoding="utf-8",
            )

            for relative_path in REQUIRED_OUTPUTS:
                output_path = run_directory / relative_path
                output_path.parent.mkdir(parents=True, exist_ok=True)
                output_path.write_bytes(b"test fixture")

            result = activate_run(run_directory)

            with current_path.open("r", encoding="utf-8") as file:
                current = json.load(file)

            self.assertEqual(result, current_path)
            self.assertEqual(current, {"run_id": "new-run"})


    def test_replace_failure_preserves_current_reference(self):
        with tempfile.TemporaryDirectory() as directory:
            data_directory = Path(directory) / "data"
            run_directory = data_directory / "runs" / "new-run"
            run_directory.mkdir(parents=True)

            current_path = data_directory / "current.json"
            current_path.write_text(
                '{"run_id": "previous-run"}',
                encoding="utf-8",
            )

            for relative_path in REQUIRED_OUTPUTS:
                output_path = run_directory / relative_path
                output_path.parent.mkdir(parents=True, exist_ok=True)
                output_path.write_bytes(b"test fixture")

            previous_content = current_path.read_bytes()

            with patch(
                "run_publication.Path.replace",
                side_effect=OSError("Simulated activation failure"),
            ):
                with self.assertRaises(OSError):
                    activate_run(run_directory)

            self.assertEqual(
                current_path.read_bytes(),
                previous_content,
            )

    def test_get_current_run_returns_referenced_directory(self):
        with tempfile.TemporaryDirectory() as directory:
            data_directory = Path(directory) / "data"
            expected_directory = data_directory / "runs" / "selected-run"
            expected_directory.mkdir(parents=True)

            current_path = data_directory / "current.json"
            current_path.write_text(
                '{"run_id": "selected-run"}',
                encoding="utf-8",
            )

            result = get_current_run(data_directory)
            self.assertEqual(result, expected_directory)

    def test_missing_current_reference_raises(self):
        with tempfile.TemporaryDirectory() as directory:
            data_directory = Path(directory) / "data"
            data_directory.mkdir()

            with self.assertRaises(FileNotFoundError):
                get_current_run(data_directory)

    def test_missing_referenced_directory_raises(self):
        with tempfile.TemporaryDirectory() as directory:
            data_directory = Path(directory) / "data"
            data_directory.mkdir()

            current_path = data_directory / "current.json"
            current_path.write_text(
                '{"run_id": "missing-run"}',
                encoding="utf-8",
            )

            with self.assertRaisesRegex(
                FileNotFoundError,
                "Current run directory not found",
            ):
                get_current_run(data_directory)

    def test_activates_gold_with_its_own_required_outputs(self):
        with tempfile.TemporaryDirectory() as directory:
            data_directory = Path(directory) / "data"
            gold_directory = data_directory / "gold"
            run_directory = gold_directory / "runs" / "gold-test-run"
            run_directory.mkdir(parents=True)

            main_reference = data_directory / "current.json"
            main_reference.write_text(
                '{"run_id": "previous-main-run"}',
                encoding="utf-8",
            )

            required_outputs = (
                "race_car_summary.parquet",
                "manufacturer_reference.parquet",
                "manufacturer_evidence.parquet",
                "inputs.json",
            )

            for filename in required_outputs:
                (run_directory / filename).write_bytes(b"test marker")

            current_path = activate_run(
                run_directory,
                required_outputs=required_outputs,
            )

            self.assertEqual(
                current_path,
                gold_directory / "current.json",
            )
            self.assertEqual(
                json.loads(current_path.read_text(encoding="utf-8")),
                {"run_id": "gold-test-run"},
            )
            self.assertEqual(
                main_reference.read_text(encoding="utf-8"),
                '{"run_id": "previous-main-run"}',
            )

    def test_incomplete_gold_preserves_previous_reference(self):
        with tempfile.TemporaryDirectory() as directory:
            gold_directory = Path(directory) / "data" / "gold"
            run_directory = gold_directory / "runs" / "candidate-run"
            run_directory.mkdir(parents=True)

            current_path = gold_directory / "current.json"
            previous_reference = b'{"run_id": "previous-gold-run"}'
            current_path.write_bytes(previous_reference)

            (run_directory / "race_car_summary.parquet").write_bytes(
                b"test marker"
            )

            with self.assertRaisesRegex(
                FileNotFoundError,
                "missing files",
            ):
                activate_run(
                    run_directory,
                    required_outputs=(
                        "race_car_summary.parquet",
                        "manufacturer_reference.parquet",
                    ),
                )

            self.assertEqual(
                current_path.read_bytes(),
                previous_reference,
            )

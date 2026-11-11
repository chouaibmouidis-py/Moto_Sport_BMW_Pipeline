import subprocess
import unittest
from pathlib import Path
from unittest.mock import patch

from run_pipeline import main


class RunPipelineTests(unittest.TestCase):
    def test_stops_when_bronze_fails(self):
        with patch("run_pipeline.subprocess.run") as mocked_run:
            mocked_run.side_effect = [
                subprocess.CompletedProcess(args=[], returncode=0),
                subprocess.CalledProcessError(
                    returncode=1,
                    cmd=["build_bronze.py"],
                ),
            ]

            with self.assertRaises(subprocess.CalledProcessError):
                main()

            started_scripts = [
                Path(call.args[0][1]).name
                for call in mocked_run.call_args_list
            ]

            for recorded_call in mocked_run.call_args_list:
                self.assertTrue(recorded_call.kwargs.get("check"))

            self.assertEqual(
                started_scripts,
                ["inspect_manifest.py", "build_bronze.py"],
            )

    def test_stops_when_classification_bronze_fails(self):
        with patch("run_pipeline.subprocess.run") as mocked_run:
            mocked_run.side_effect = [
                subprocess.CompletedProcess(args=[], returncode=0),
                subprocess.CompletedProcess(args=[], returncode=0),
                subprocess.CompletedProcess(args=[], returncode=0),
                subprocess.CalledProcessError(
                    returncode=1,
                    cmd=["build_classification_bronze.py"],
                ),
            ]

            with self.assertRaises(subprocess.CalledProcessError):
                main()
            started_scripts = [
                Path(call.args[0][1]).name
                for call in mocked_run.call_args_list
            ]
            for recorded_call in mocked_run.call_args_list:
                self.assertTrue(recorded_call.kwargs.get("check"))

            self.assertEqual(
                started_scripts,
                                [
                    "inspect_manifest.py",
                    "build_bronze.py",
                    "inspect_classification.py",
                    "build_classification_bronze.py",
                ],
            )

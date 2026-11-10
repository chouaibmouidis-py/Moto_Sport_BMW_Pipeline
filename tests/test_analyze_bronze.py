import runpy
import unittest
from pathlib import Path
from unittest.mock import patch
from analyze_bronze import select_pit_stop_sources


class AnalyzeBronzeTests(unittest.TestCase):
    def test_import_does_not_start_pipeline(self):
        script_path = (
            Path(__file__).resolve().parent.parent
            / "analyze_bronze.py"
        )

        with patch("duckdb.connect") as mocked_connect:
            runpy.run_path(
                str(script_path),
                run_name="analyze_bronze",
            )

        mocked_connect.assert_not_called()

    def test_selects_only_enabled_pit_stop_sources(self):
        documents = [
            {
                "source_id": "enabled-pits",
                "enabled": True,
                "document_type": "pit_stops",
            },
            {
                "source_id": "disabled-pits",
                "enabled": False,
                "document_type": "pit_stops",
            },
            {
                "source_id": "enabled-weather",
                "enabled": True,
                "document_type": "weather",
            },
        ]

        selected = select_pit_stop_sources(documents)
        self.assertEqual(selected, [documents[0]])

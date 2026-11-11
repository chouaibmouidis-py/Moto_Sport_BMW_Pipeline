import unittest
from unittest.mock import patch
from inspect_classification import main
import hashlib
import json
import tempfile
from pathlib import Path
from inspect_classification import prepare_classification_raw
from inspect_classification import SOURCE_URL


class InspectClassificationTests(unittest.TestCase):
    def test_help_does_not_download(self):
        with patch(
            "sys.argv",
            ["inspect_classification.py", "--help"],
        ):
            with patch("inspect_classification.download") as mocked_download:
                with self.assertRaises(SystemExit) as raised:
                    main()

        self.assertEqual(raised.exception.code, 0)
        mocked_download.assert_not_called()

    def test_reuses_verified_raw_without_downloading(self):
        with tempfile.TemporaryDirectory() as directory:
            destination = Path(directory)
            source_path = destination / "03_Results_Race_Official.JSON"
            metadata_path = destination / "metadata.json"

            content = b'{"classification": []}'
            source_path.write_bytes(content)

            metadata = {
                "sha256": hashlib.sha256(content).hexdigest(),
            }
            metadata_path.write_text(
                json.dumps(metadata),
                encoding="utf-8",
            )
            with patch("inspect_classification.download") as mocked_download:
                result = prepare_classification_raw(destination)
                self.assertEqual(result, source_path)
                mocked_download.assert_not_called()

    def test_rejects_modified_raw_without_downloading(self):
        with tempfile.TemporaryDirectory() as directory:
            destination = Path(directory)
            source_path = destination / "03_Results_Race_Official.JSON"
            metadata_path = destination / "metadata.json"

            content = b'{"classification": []}'
            source_path.write_bytes(content)

            metadata = {
                "sha256": hashlib.sha256(content).hexdigest(),
            }
            metadata_path.write_text(
                json.dumps(metadata),
                encoding="utf-8",
            )

            source_path.write_bytes(b'{"classification": [1]}')


            with patch("inspect_classification.download") as mocked_download:
                with self.assertRaises(ValueError):
                    prepare_classification_raw(destination)

                mocked_download.assert_not_called()

    def test_refresh_downloads_even_when_raw_exists(self):

        with tempfile.TemporaryDirectory() as directory:
            destination = Path(directory)
            source_path = destination / "03_Results_Race_Official.JSON"
            metadata_path = destination / "metadata.json"

            content = b'{"classification": []}'
            source_path.write_bytes(content)

            metadata = {
                "sha256": hashlib.sha256(content).hexdigest(),
            }
            metadata_path.write_text(
                json.dumps(metadata),
                encoding="utf-8",
            )

            source_path.write_bytes(b'{"classification": [1]}')

            with patch(
                "inspect_classification.download",
                return_value=source_path,
            ) as mocked_download:
                result = prepare_classification_raw(
                    destination,
                    refresh=True,
                )

                mocked_download.assert_called_once_with(
                    SOURCE_URL,
                    destination,
                    filename=source_path.name,
                )

            self.assertEqual(result, source_path)

    def test_download_uses_requested_url(self):
        with tempfile.TemporaryDirectory() as directory:
            destination = Path(directory)
            source_path = destination / "custom.json"
            source_path.write_bytes(b'{"classification": []}')
            custom_url = "https://example.com/custom.json"

            with patch(
                "inspect_classification.download",
                return_value=source_path,
            ) as mocked_download:
                prepare_classification_raw(
                    destination,
                    refresh=True,
                    source_id="custom-source",
                    url=custom_url,
                    filename="custom.json",
                )

                mocked_download.assert_called_once_with(
                    custom_url,
                    destination,
                    filename="custom.json",
                )

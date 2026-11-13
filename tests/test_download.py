"""Verify JSON downloads, custom filenames and preservation of previous files on errors."""

import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import requests

from download import SOURCE_FILENAME, download


class DownloadTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.destination = Path(self.directory.name) / "raw"
        self.target = self.destination / SOURCE_FILENAME
        self.url = "https://example.invalid/source.json"

    def response(self, content: bytes, status: int = 200):
        response = requests.Response()
        response.status_code = status
        response.url = self.url
        response._content = content
        return response

    def seed_previous_file(self):
        self.destination.mkdir()
        self.target.write_bytes(b'{"version": "previous"}')
        return self.target.read_bytes()

    def test_valid_json_creates_final_file_and_removes_partial_file(self):
        content = b'\xef\xbb\xbf{"session": {}, "pit_stop_analysis": []}'
        with patch("download.requests.get", return_value=self.response(content)):
            result = download(self.url, self.destination)

        self.assertEqual(result, self.target)
        self.assertEqual(self.target.read_bytes(), content)
        self.assertFalse(self.target.with_suffix(".part").exists())

    def test_invalid_json_preserves_previous_file(self):
        previous = self.seed_previous_file()
        response = self.response(b"<html>Unavailable</html>")
        with patch("download.requests.get", return_value=response):
            with self.assertRaises(json.JSONDecodeError):
                download(self.url, self.destination)

        self.assertEqual(self.target.read_bytes(), previous)

    def test_timeout_preserves_previous_file(self):
        previous = self.seed_previous_file()
        with patch("download.requests.get", side_effect=requests.Timeout):
            with self.assertRaises(requests.Timeout):
                download(self.url, self.destination)

        self.assertEqual(self.target.read_bytes(), previous)

    def test_http_error_preserves_previous_file(self):
        previous = self.seed_previous_file()
        response = self.response(b"Not found", status=404)
        with patch("download.requests.get", return_value=response):
            with self.assertRaises(requests.HTTPError):
                download(self.url, self.destination)

        self.assertEqual(self.target.read_bytes(), previous)

    def test_repeated_download_does_not_create_duplicate_final_files(self):
        response = self.response(b'{"version": "same"}')
        with patch("download.requests.get", return_value=response):
            first = download(self.url, self.destination)
            second = download(self.url, self.destination)

        self.assertEqual(first, second)
        self.assertEqual(list(self.destination.iterdir()), [self.target])

    def test_http_503_preserves_previous_file(self):
        previous = self.seed_previous_file()
        reponse = self.response(b"Service Unavailable", status=503)
        with patch("download.requests.get", return_value=reponse):
            with self.assertRaises(requests.HTTPError):
                download(self.url, self.destination)

        self.assertEqual(self.target.read_bytes(), previous)

    def test_invalid_json_does_not_create_final_file(self):
        reponse = self.response(b'{"session": {}, "pit_stop_analysis": [}')
        with patch("download.requests.get", return_value=reponse):
            with self.assertRaises(json.JSONDecodeError):
                download(self.url, self.destination)
        self.assertFalse(self.target.exists())

    def test_download_uses_custom_filename(self):
        filename = "03_Results_Race_Official.JSON"
        expected_path = self.destination / filename
        content = b'{"session": {}, "classification": []}'

        with patch(
            "download.requests.get",
            return_value=self.response(content),
        ):
            result = download(
                self.url,
                self.destination,
                filename=filename,
            )

        self.assertEqual(result, expected_path)
        self.assertEqual(expected_path.read_bytes(), content)
        self.assertFalse(self.target.exists())


if __name__ == "__main__":
    unittest.main()

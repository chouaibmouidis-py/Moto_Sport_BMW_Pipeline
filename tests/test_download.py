"""Verify JSON downloads, custom filenames and preservation of previous files on errors."""

import json
from unittest.mock import patch

import pytest
import requests

from download import SOURCE_FILENAME, download


def make_response(content: bytes, status: int = 200):
    response = requests.Response()
    response.status_code = status
    response.url = "https://example.invalid/source.json"
    response._content = content
    return response


def seed_previous_file(download_paths):
    download_paths[0].mkdir()
    download_paths[1].write_bytes(b'{"version": "previous"}')
    return download_paths[1].read_bytes()


def test_valid_json_creates_final_file_and_removes_partial_file(download_paths):
    content = b'\xef\xbb\xbf{"session": {}, "pit_stop_analysis": []}'
    with patch("download.requests.get", return_value=make_response(content)):
        result = download("https://example.invalid/source.json", download_paths[0])

    assert result == download_paths[1]
    assert download_paths[1].read_bytes() == content
    assert not download_paths[1].with_suffix(".part").exists()


def test_invalid_json_preserves_previous_file(download_paths):
    previous = seed_previous_file(download_paths)
    response = make_response(b"<html>Unavailable</html>")
    with patch("download.requests.get", return_value=response):
        with pytest.raises(json.JSONDecodeError):
            download("https://example.invalid/source.json", download_paths[0])

    assert download_paths[1].read_bytes() == previous


def test_timeout_preserves_previous_file(download_paths):
    previous = seed_previous_file(download_paths)
    with patch("download.requests.get", side_effect=requests.Timeout):
        with pytest.raises(requests.Timeout):
            download("https://example.invalid/source.json", download_paths[0])

    assert download_paths[1].read_bytes() == previous


@pytest.mark.parametrize("status", (404, 503))
def test_http_error_preserves_previous_file(download_paths, status):
    previous = seed_previous_file(download_paths)
    response = make_response(b"HTTP error", status=status)
    with patch("download.requests.get", return_value=response):
        with pytest.raises(requests.HTTPError):
            download("https://example.invalid/source.json", download_paths[0])

    assert download_paths[1].read_bytes() == previous


def test_repeated_download_does_not_create_duplicate_final_files(download_paths):
    response = make_response(b'{"version": "same"}')
    with patch("download.requests.get", return_value=response):
        first = download("https://example.invalid/source.json", download_paths[0])
        second = download("https://example.invalid/source.json", download_paths[0])

    assert first == second
    assert list(download_paths[0].iterdir()) == [download_paths[1]]


def test_invalid_json_does_not_create_final_file(download_paths):
    reponse = make_response(b'{"session": {}, "pit_stop_analysis": [}')
    with patch("download.requests.get", return_value=reponse):
        with pytest.raises(json.JSONDecodeError):
            download("https://example.invalid/source.json", download_paths[0])
    assert not download_paths[1].exists()


def test_download_uses_custom_filename(download_paths):
    filename = "03_Results_Race_Official.JSON"
    expected_path = download_paths[0] / filename
    content = b'{"session": {}, "classification": []}'

    with patch(
        "download.requests.get",
        return_value=make_response(content),
    ):
        result = download(
            "https://example.invalid/source.json",
            download_paths[0],
            filename=filename,
        )

    assert result == expected_path
    assert expected_path.read_bytes() == content
    assert not download_paths[1].exists()


@pytest.fixture
def download_paths(tmp_path):
    destination = tmp_path / "raw"
    return destination, destination / SOURCE_FILENAME

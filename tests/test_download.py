"""Verify JSON downloads, custom filenames and preservation of previous files on errors."""

import hashlib
import json
from pathlib import Path
from unittest.mock import patch

import pytest
import requests

from download import SOURCE_FILENAME, download
from moto_sport_bmw_pipeline import raw_download


class StreamingResponse:
    """Expose response chunks while rejecting full-body buffering in the test."""

    def __init__(self, chunks):
        self.chunks = chunks
        self.chunk_sizes = []
        self.closed = False

    def raise_for_status(self):
        pass

    @property
    def content(self):
        raise AssertionError("Full response buffering is forbidden")

    def iter_content(self, chunk_size):
        self.chunk_sizes.append(chunk_size)
        yield from self.chunks

    def close(self):
        self.closed = True

    def __enter__(self):
        return self

    def __exit__(self, *exception):
        self.close()


@pytest.fixture
def streaming_response():
    return StreamingResponse([b'{"team":', b'"BMW"}'])


def make_response(content: bytes, status: int = 200):
    response = requests.Response()
    response.status_code = status
    response.url = "https://example.invalid/source.json"
    response._content = content
    response._content_consumed = True
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
    assert not download_paths[1].with_suffix(".part").exists()


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


def test_download_streams_without_buffering_entire_response(
    download_paths,
    streaming_response,
):

    with patch(
        "download.requests.get",
        return_value=streaming_response,
    ) as get_spy:
        result = download(
            "https://example.invalid/source.json",
            download_paths[0],
        )

    get_spy.assert_called_once_with(
        "https://example.invalid/source.json",
        timeout=60,
        stream=True,
    )

    assert result == download_paths[1]
    assert result.read_bytes() == b'{"team":"BMW"}'
    assert streaming_response.closed


def test_interrupted_stream_preserves_previous_file_and_removes_partial(
    download_paths,
    streaming_response,
    monkeypatch,
):

    previous = seed_previous_file(download_paths)

    def interrupted_chunks(chunk_size):
        yield b'{"team":'
        raise requests.ConnectionError("Simulated interrupted transfer")

    monkeypatch.setattr(streaming_response, "iter_content", interrupted_chunks)

    with patch("download.requests.get", return_value=streaming_response):
        with pytest.raises(
            requests.ConnectionError,
            match="Simulated interrupted transfer",
        ):
            download(
                "https://example.invalid/source.json",
                download_paths[0],
            )

    assert download_paths[1].read_bytes() == previous
    assert not download_paths[1].with_suffix(".part").exists()
    assert streaming_response.closed


def test_download_uses_requested_chunk_size(
    download_paths,
    streaming_response,
):
    with patch("download.requests.get", return_value=streaming_response):
        result = download(
            "https://example.invalid/source.json",
            download_paths[0],
            chunk_size=1024,
        )
    assert streaming_response.chunk_sizes == [1024]
    assert result.read_bytes() == b'{"team":"BMW"}'
    assert streaming_response.closed


@pytest.mark.parametrize("chunk_size", [0, -1])
def test_download_rejects_nonpositive_chunk_size(download_paths, chunk_size):

    with patch("download.requests.get") as get_spy:
        with pytest.raises(
            ValueError,
            match="chunk_size must be a positive integer",
        ):
            download(
                "https://example.invalid/source.json",
                download_paths[0],
                chunk_size=chunk_size,
            )
        get_spy.assert_not_called()


@pytest.mark.parametrize("chunk_size", [True, False, 1.5, "1024", None])
def test_download_rejects_invalid_chunk_size_type(download_paths, chunk_size):

    with patch("download.requests.get") as get_spy:
        with pytest.raises(
            ValueError,
            match="chunk_size must be a positive integer",
        ):
            download(
                "https://example.invalid/source.json",
                download_paths[0],
                chunk_size=chunk_size,
            )
        get_spy.assert_not_called()


def test_download_ignores_empty_chunks(download_paths):

    response = StreamingResponse(
        [
            b"",
            b'{"team":',
            b"",
            b'"BMW"}',
            b"",
        ]
    )

    with patch("download.requests.get", return_value=response):
        result = download(
            "https://example.invalid/source.json",
            download_paths[0],
        )

    assert result.read_bytes() == b'{"team":"BMW"}'
    assert response.closed
    assert not result.with_suffix(".part").exists()


def test_streamed_fingerprint_matches_written_bytes_without_full_reread(
    download_paths, streaming_response, monkeypatch
):
    def forbid_read_bytes(path):
        raise AssertionError("Fingerprint must reuse streamed bytes")

    with monkeypatch.context() as patcher:
        patcher.setattr(Path, "read_bytes", forbid_read_bytes)
        with patch("download.requests.get", return_value=streaming_response):
            result, sha256 = raw_download.download_with_fingerprint(
                "https://example.invalid/source.json",
                download_paths[0],
                chunk_size=1024,
            )

    assert result.read_bytes() == b'{"team":"BMW"}'
    assert sha256 == hashlib.sha256(b'{"team":"BMW"}').hexdigest()
    assert streaming_response.closed


def test_prepare_source_records_streamed_fingerprint(
    tmp_path, streaming_response, monkeypatch
):
    source = {
        "source_id": "test-source",
        "filename": "report.json",
        "format": "json",
        "url": "https://example.invalid/source.json",
    }

    def forbid_read_bytes(path):
        raise AssertionError("Acquisition must not reread the whole file for hashing")

    with monkeypatch.context() as patcher:
        patcher.setattr(Path, "read_bytes", forbid_read_bytes)
        with patch("download.requests.get", return_value=streaming_response):
            result = raw_download.prepare_source(tmp_path, source)

    assert result.read_bytes() == b'{"team":"BMW"}'
    metadata = json.loads((result.parent / "metadata.json").read_text(encoding="utf-8"))
    assert metadata["sha256"] == hashlib.sha256(b'{"team":"BMW"}').hexdigest()
    assert metadata["source_id"] == source["source_id"]
    assert {path.name for path in result.parent.iterdir()} == {
        "report.json",
        "metadata.json",
    }


def test_refresh_with_wrong_hash_preserves_file_and_metadata(
    tmp_path, streaming_response
):
    source = {
        "source_id": "test-source",
        "filename": "report.json",
        "format": "json",
        "url": "https://example.invalid/source.json",
        "expected_sha256": "0" * 64,
    }
    directory = tmp_path / "data/raw/test-source"
    directory.mkdir(parents=True)
    (directory / "report.json").write_bytes(b'{"version":"previous"}')
    (directory / "metadata.json").write_bytes(b'{"sha256":"previous"}')

    with patch("download.requests.get", return_value=streaming_response):
        with pytest.raises(ValueError, match="Raw fingerprint mismatch: test-source"):
            raw_download.prepare_source(tmp_path, source, refresh=True)

    assert (directory / "report.json").read_bytes() == b'{"version":"previous"}'
    assert (directory / "metadata.json").read_bytes() == b'{"sha256":"previous"}'
    assert {path.name for path in directory.iterdir()} == {
        "report.json",
        "metadata.json",
    }


def test_unsupported_format_is_rejected_before_network_or_files(download_paths):
    with patch("download.requests.get") as get_spy:
        with pytest.raises(ValueError, match="Unsupported format"):
            download(
                "https://example.invalid/source.json",
                download_paths[0],
                expected_format="unknown",
            )
    get_spy.assert_not_called()
    assert not download_paths[0].exists()


def test_cleanup_failure_preserves_original_network_error(
    download_paths, streaming_response, monkeypatch, caplog
):
    previous = seed_previous_file(download_paths)

    def interrupted_chunks(chunk_size):
        yield b'{"team":'
        raise requests.ConnectionError("Original transfer failure")

    def fail_cleanup(path, missing_ok=False):
        raise PermissionError("Simulated cleanup failure")

    monkeypatch.setattr(streaming_response, "iter_content", interrupted_chunks)
    with monkeypatch.context() as patcher:
        patcher.setattr(Path, "unlink", fail_cleanup)
        with patch("download.requests.get", return_value=streaming_response):
            with pytest.raises(
                requests.ConnectionError, match="Original transfer failure"
            ):
                download("https://example.invalid/source.json", download_paths[0])

    assert download_paths[1].read_bytes() == previous
    assert streaming_response.closed
    assert "Could not remove download temporary" in caplog.text

"""Verify classification Raw reuse, refresh and manifest download parameters."""

import hashlib
import json
from pathlib import Path
from unittest.mock import patch

import pytest

from inspect_classification import SOURCE_URL, main, prepare_classification_raw


def test_help_does_not_download():
    with patch(
        "sys.argv",
        ["inspect_classification.py", "--help"],
    ):
        with patch("inspect_classification.download") as mocked_download:
            with pytest.raises(SystemExit) as raised:
                main()

    assert raised.value.code == 0
    mocked_download.assert_not_called()


def test_reuses_verified_raw_without_downloading(tmp_path):
    directory = tmp_path
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
        assert result == source_path
        mocked_download.assert_not_called()


def test_rejects_modified_raw_without_downloading(tmp_path):
    directory = tmp_path
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
        with pytest.raises(ValueError):
            prepare_classification_raw(destination)

        mocked_download.assert_not_called()


def test_refresh_downloads_even_when_raw_exists(tmp_path):
    directory = tmp_path
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

    assert result == source_path


def test_download_uses_requested_url(tmp_path):
    directory = tmp_path
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

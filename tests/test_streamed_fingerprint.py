import hashlib
from pathlib import Path

from moto_sport_bmw_pipeline import integrity


def test_file_fingerprint_matches_exact_bytes_without_read_bytes(tmp_path, monkeypatch):
    source = tmp_path / "source.bin"
    block = bytes(range(256)) * 4096
    expected = hashlib.sha256()
    with source.open("wb") as file:
        for _ in range(4):
            file.write(block)
            expected.update(block)

    def forbidden(path):
        raise AssertionError("Full read_bytes is forbidden for file fingerprints")

    monkeypatch.setattr(Path, "read_bytes", forbidden)
    assert integrity.sha256_file(source) == expected.hexdigest()

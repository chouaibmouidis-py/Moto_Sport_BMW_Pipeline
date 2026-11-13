"""Verify a local Raw file against the SHA-256 recorded in its metadata."""

from pathlib import Path
import hashlib
import json
import logging

logger = logging.getLogger(__name__)


def verify_local_file(source_path: Path, metadata_path: Path) -> None:
    if not metadata_path.exists():
        raise FileNotFoundError(f"Metadata file not found at {metadata_path}. Try with --refresh")

    with metadata_path.open("r", encoding="utf-8") as file:
        metadata = json.load(file)

    expected_hash = metadata["sha256"]
    content = source_path.read_bytes()
    actual_hash = hashlib.sha256(content).hexdigest()

    if actual_hash == expected_hash:
        logger.debug('%s', "Hashes match")
    else:
        exception_message = f"Hashes do not match: expected {expected_hash}, got {actual_hash}"
        raise ValueError(exception_message)

"""Stream file fingerprints and verify metadata-recorded Raw versions."""

import hashlib
import json
import logging
from pathlib import Path

logger = logging.getLogger(__name__)


def sha256_file(path: str | Path) -> str:
    """Hash file bytes with a bounded Python buffer, without retaining a payload."""
    with Path(path).open("rb") as file:
        return hashlib.file_digest(file, "sha256").hexdigest()


def verify_local_file(source_path: Path, metadata_path: Path) -> None:
    if not metadata_path.exists():
        raise FileNotFoundError(
            f"Metadata file not found at {metadata_path}. Try with --refresh"
        )

    with metadata_path.open("r", encoding="utf-8") as file:
        metadata = json.load(file)

    expected_hash = metadata["sha256"]
    actual_hash = sha256_file(source_path)

    if actual_hash == expected_hash:
        logger.debug("%s", "Hashes match")
    else:
        exception_message = (
            f"Hashes do not match: expected {expected_hash}, got {actual_hash}"
        )
        raise ValueError(exception_message)

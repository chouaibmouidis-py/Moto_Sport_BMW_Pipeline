"""Stream and fingerprint source bytes, validate, then replace the final Raw path."""

import csv
import hashlib
import json
import logging
import os
import tempfile
from datetime import datetime, timezone
from pathlib import Path

import requests
from pypdf import PdfReader

from moto_sport_bmw_pipeline.logging_config import configure_logging, log_operation

from .integrity import sha256_file

logger = logging.getLogger(__name__)


BASE_URL = "https://imsa.results.alkamelcloud.com/Results/25_2025/16_Road%20America/01_IMSA%20WeatherTech%20SportsCar%20Championship/202508031310_Race/20_Pit%20Stops%20Time%20Cards_Race.JSON"
RAW_DIR = "data/raw"
BRONZE_DIR = "data/bronze"
SOURCE_FILENAME = "20_Pit Stops Time Cards_Race.JSON"


def validate_json(path: Path) -> None:
    with path.open("r", encoding="utf-8-sig") as file:
        json.load(file)


def validate_classification_csv(path: Path) -> None:
    with path.open("r", encoding="utf-8-sig", newline="") as file:
        required_columns = [
            "NUMBER",
            "VEHICLE",
            "POSITION",
            "CLASS",
            "STATUS",
            "IMSA_ManufacturerId",
            "TEAM",
            "LAPS",
            "FL_LAPNUM",
            "FL_KPH",
            "TOTAL_TIME",
            "FL_TIME",
            "GAP_FIRST",
            "GAP_PREVIOUS",
        ]
        reader = csv.reader(file, delimiter=";")
        header = next(reader, None)
        if not header:
            raise ValueError("Missing CSV header")
        for column in required_columns:
            if column not in header:
                raise ValueError(f"Incompatible header, missing column: {column}")
        if not any(field.strip() for row in reader for field in row):
            raise ValueError("CSV contains no data rows")


def validate_pdf(path: Path) -> None:
    document = PdfReader(path)
    if len(document.pages) == 0:
        raise ValueError("PDF contains no pages")


VALIDATORS = {
    "json": validate_json,
    "csv": validate_classification_csv,
    "pdf": validate_pdf,
}


def prepare_source(project_directory: Path, source: dict, *, refresh=False) -> Path:
    """Acquire or verify one source; choose its validator from the declared format."""
    with log_operation(
        logger, "Prepare source", stage="raw", source_id=source["source_id"]
    ):
        from .integrity import verify_local_file

        directory = project_directory / "data/raw" / source["source_id"]
        target = directory / source["filename"]
        metadata_path = directory / "metadata.json"
        validator = VALIDATORS[source["format"]]
        expected = source.get("expected_sha256")
        if target.is_file() and not refresh:
            if expected:
                if sha256_file(target) != expected:
                    raise ValueError(f"Raw fingerprint mismatch: {source['source_id']}")
            else:
                verify_local_file(target, metadata_path)
            validator(target)
            return target
        directory.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory(dir=directory) as temporary:
            candidate, digest = download_with_fingerprint(
                source["url"], temporary, source["filename"], source["format"]
            )
            if expected and digest != expected:
                raise ValueError(f"Raw fingerprint mismatch: {source['source_id']}")
            metadata = {
                "source_id": source["source_id"],
                "url": source["url"],
                "filename": source["filename"],
                "sha256": digest,
                "downloaded_at": datetime.now(timezone.utc).isoformat(),
            }
            candidate_metadata = Path(temporary) / "metadata.json"
            candidate_metadata.write_text(
                json.dumps(metadata, indent=2), encoding="utf-8"
            )
            candidate.replace(target)
            candidate_metadata.replace(metadata_path)
        return target


def download(
    url: str,
    save_path: str | Path,
    filename: str = SOURCE_FILENAME,
    expected_format: str = "json",
    chunk_size: int = 64 * 1024,
) -> Path:
    """Keep the historical path-only result while using the shared streaming transfer."""
    target_path, _ = download_with_fingerprint(
        url, save_path, filename, expected_format, chunk_size
    )
    return target_path


def download_with_fingerprint(
    url: str,
    save_path: str | Path,
    filename: str = SOURCE_FILENAME,
    expected_format: str = "json",
    chunk_size: int = 64 * 1024,
) -> tuple[Path, str]:
    """Return the validated path and SHA-256 of the bytes written during transfer."""
    if (
        isinstance(chunk_size, bool)
        or not isinstance(chunk_size, int)
        or chunk_size <= 0
    ):
        raise ValueError("chunk_size must be a positive integer")
    if expected_format not in VALIDATORS:
        raise ValueError(f"Unsupported format :{expected_format}")
    target_path = Path(save_path) / filename
    target_path.parent.mkdir(parents=True, exist_ok=True)
    temporary_path = None
    digest = hashlib.sha256()

    try:
        with requests.get(url, timeout=60, stream=True) as response:
            response.raise_for_status()

            descriptor, temporary_name = tempfile.mkstemp(
                dir=target_path.parent, prefix=f".{target_path.name}.", suffix=".part"
            )
            temporary_path = Path(temporary_name)
            with os.fdopen(descriptor, "wb") as file:
                for chunk in response.iter_content(chunk_size=chunk_size):
                    if chunk:
                        file.write(chunk)
                        digest.update(chunk)

        VALIDATORS[expected_format](temporary_path)

        temporary_path.replace(target_path)

    except Exception:
        if temporary_path is not None:
            try:
                temporary_path.unlink(missing_ok=True)
            except OSError:
                logger.exception(
                    "Could not remove download temporary: %s", temporary_path
                )
        raise
    return target_path, digest.hexdigest()


def main() -> None:
    configure_logging()
    download_path = download(BASE_URL, RAW_DIR)
    logger.info("%s %s", "Downloaded to:", download_path)


if __name__ == "__main__":
    main()

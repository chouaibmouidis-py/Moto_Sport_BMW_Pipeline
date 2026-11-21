"""Download and validate a JSON document before replacing its final Raw path."""

from pathlib import Path
import json
import logging
import csv
import requests
from pypdf import PdfReader
from moto_sport_bmw_pipeline.logging_config import configure_logging

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
        if not any(
            field.strip()
            for row in reader
            for field in row
        ):
            raise ValueError("CSV contains no data rows")

def validate_pdf(path: Path) -> None:
    document = PdfReader(path)
    if len(document.pages) == 0:
        raise ValueError("PDF contains no pages")

def download(
    url: str,
    save_path: str | Path,
    filename: str = SOURCE_FILENAME,
    expected_format: str = "json",
) -> Path:
    target_path = Path(save_path) / filename
    response = requests.get(url, timeout=60)
    response.raise_for_status()
    target_path.parent.mkdir(parents=True, exist_ok=True)
    temporary_path = target_path.with_suffix(".part")

    with temporary_path.open("wb") as file:
        file.write(response.content)

    if expected_format == "json":
        validate_json(temporary_path)
    elif expected_format == "csv":
        validate_classification_csv(temporary_path)
    elif expected_format == "pdf":
        validate_pdf(temporary_path)
    else:
        raise ValueError(f"Unsupported format :{expected_format}")

    temporary_path.replace(target_path)
    return target_path


def main() -> None:
    configure_logging()
    download_path = download(BASE_URL, RAW_DIR)
    logger.info('%s %s', "Downloaded to:", download_path)


if __name__ == "__main__":
    main()

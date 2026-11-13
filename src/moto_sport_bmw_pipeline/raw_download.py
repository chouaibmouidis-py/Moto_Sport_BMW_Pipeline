"""Download and validate a JSON document before replacing its final Raw path."""

from pathlib import Path
import json
import logging

import requests

from moto_sport_bmw_pipeline.logging_config import configure_logging

logger = logging.getLogger(__name__)


BASE_URL = "https://imsa.results.alkamelcloud.com/Results/25_2025/16_Road%20America/01_IMSA%20WeatherTech%20SportsCar%20Championship/202508031310_Race/20_Pit%20Stops%20Time%20Cards_Race.JSON"
RAW_DIR = "data/raw"
BRONZE_DIR = "data/bronze"
SOURCE_FILENAME = "20_Pit Stops Time Cards_Race.JSON"


def download(
    url: str,
    save_path: str | Path,
    filename: str = SOURCE_FILENAME,
) -> Path:
    target_path = Path(save_path) / filename
    response = requests.get(url, timeout=60)
    response.raise_for_status()
    target_path.parent.mkdir(parents=True, exist_ok=True)
    temporary_path = target_path.with_suffix(".part")

    with temporary_path.open("wb") as file:
        file.write(response.content)

    with temporary_path.open("r", encoding="utf-8-sig") as file:
        json.load(file)

    temporary_path.replace(target_path)
    return target_path


def main() -> None:
    configure_logging()
    download_path = download(BASE_URL, RAW_DIR)
    logger.info('%s %s', "Downloaded to:", download_path)


if __name__ == "__main__":
    main()

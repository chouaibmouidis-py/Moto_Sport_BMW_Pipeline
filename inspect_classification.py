"""Download or reuse enabled classification Raw documents with version metadata."""

from datetime import datetime, timezone
from pathlib import Path
import argparse
import hashlib
import json
import logging

from build_classification_bronze import select_classification_sources
from download import download
from file_integrity import verify_local_file
from moto_sport_bmw_pipeline.logging_config import configure_logging

logger = logging.getLogger("moto_sport_bmw_pipeline.inspect_classification")


SOURCE_URL = (
    "https://imsa.results.alkamelcloud.com/Results/"
    "25_2025/16_Road%20America/"
    "01_IMSA%20WeatherTech%20SportsCar%20Championship/"
    "202508031310_Race/03_Results_Race_Official.JSON"
)
SOURCE_ID = "imsa-2025-road-america-race-classification-official"

def prepare_classification_raw(
    destination: Path,
    refresh: bool = False,
    *,
    source_id: str = SOURCE_ID,
    url: str = SOURCE_URL,
    filename: str = "03_Results_Race_Official.JSON",
) -> Path:

    downloaded_path = destination / filename
    metadata_path = destination / "metadata.json"

    if downloaded_path.exists() and not refresh:
        verify_local_file(downloaded_path, metadata_path)
    else:
        downloaded_path = download(
            url,
            destination,
            filename=downloaded_path.name,
        )

        metadata = {
            "source_id": source_id,
            "url": url,
            "filename": downloaded_path.name,
            "downloaded_at": datetime.now(timezone.utc).isoformat(),
            "sha256": hashlib.sha256(
                downloaded_path.read_bytes()
            ).hexdigest(),
        }

        temporary_metadata_path = metadata_path.with_suffix(".json.part")

        with temporary_metadata_path.open("w", encoding="utf-8") as file:
            json.dump(metadata, file, ensure_ascii=False, indent=2)

        temporary_metadata_path.replace(metadata_path)
    return downloaded_path


def main() -> None:
    configure_logging()
    parser = argparse.ArgumentParser(
        description="Download or reuse the classification document."
    )
    parser.add_argument(
        "--refresh",
        action="store_true",
        help="Refresh the downloaded classification document.",
    )
    args = parser.parse_args()
    project_directory = Path(__file__).resolve().parent
    manifest_path = project_directory / "config" / "sources.json"

    with manifest_path.open("r", encoding="utf-8") as file:
        manifest = json.load(file)

    selected_sources = select_classification_sources(
        manifest["documents"]
    )

    for source in selected_sources:
        destination = (
            project_directory / "data" / "raw" / source["source_id"]
        )

        downloaded_path = prepare_classification_raw(
            destination,
            refresh=args.refresh,
            source_id=source["source_id"],
            url=source["url"],
            filename=source["filename"],
        )
        metadata_path = destination / "metadata.json"

        logger.info('%s %s', "Raw document:", downloaded_path)
        logger.info('%s %s', "Metadata:", metadata_path)

        with downloaded_path.open("r", encoding="utf-8-sig") as file:
            document = json.load(file)

        logger.debug('%s %s', "Root keys:", list(document))
        logger.info('%s %s', "Report status:", document["session"]["report_mark"])
        logger.info('%s %s', "Classification entries:", len(document["classification"]))

        for participant in document["classification"]:
            if participant["manufacturer"] == "BMW":
                logger.debug('%s | %s | %s | %s', participant["number"], participant["position"], participant["class"], participant["pit_stops"])

        for participant in document["classification"]:
            if participant["number"] == "70":
                logger.debug('%s | %s | %s | %s | %s', participant["number"], participant["laps"], participant["pit_stops"], participant["status"], participant["not_finished"])


if __name__ == "__main__":
    main()

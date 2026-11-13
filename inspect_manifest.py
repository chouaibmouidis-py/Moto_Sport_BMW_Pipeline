"""Download or reuse enabled pit-stop Raw documents and inspect their basic volumes."""

from datetime import datetime, timezone
from pathlib import Path
import argparse
import hashlib
import json
import logging

from download import SOURCE_FILENAME, download
from file_integrity import verify_local_file
from moto_sport_bmw_pipeline.logging_config import configure_logging
from race_metrics import count_manufacturer_pit_stops

logger = logging.getLogger("moto_sport_bmw_pipeline.inspect_manifest")


def main():
    configure_logging()
    parser = argparse.ArgumentParser()

    PROJECT_DIR = Path(__file__).resolve().parent


    parser.add_argument("--refresh", action="store_true", help="Refresh the downloaded files")
    args = parser.parse_args()

    manifest_path = PROJECT_DIR / "config" / "sources.json"

    with manifest_path.open("r", encoding="utf-8") as file:
        manifest = json.load(file)

    for document in manifest["documents"]:
        if not document.get("enabled", False):
            continue

        if document["document_type"] != "pit_stops":
            continue

        destination_dir = PROJECT_DIR / "data" / "raw" / document["source_id"]
        downloaded_path = destination_dir / SOURCE_FILENAME
        metadata_path = destination_dir / "metadata.json"

        logger.info('%s %s', "Source :", document["source_id"])
        logger.debug('%s %s', "URL :", document["url"])
        logger.info('%s %s', "Directory:", destination_dir)

        if downloaded_path.exists() and not args.refresh:
            verify_local_file(downloaded_path, metadata_path)
        else:
            downloaded_path = download(document["url"], destination_dir)
            downloaded_at = datetime.now(timezone.utc).isoformat()

            logger.info('%s %s', "Downloaded:", downloaded_path)

            content = downloaded_path.read_bytes()
            sha256 = hashlib.sha256(content).hexdigest()

            metadata = {
                "source_id": document["source_id"],
                "url": document["url"],
                "downloaded_at": downloaded_at,
                "sha256": sha256,
            }

            temporary_metadata_path = metadata_path.with_suffix(".json.part")

            with temporary_metadata_path.open("w", encoding="utf-8") as file:
                json.dump(metadata, file, ensure_ascii=False, indent=2)

            temporary_metadata_path.replace(metadata_path)

        with downloaded_path.open("r", encoding="utf-8-sig") as file:
            data = json.load(file)

        logger.info('%s %s', "Event:", data["session"]["event_name"])
        logger.info('%s %s', "Car entries:", len(data["pit_stop_analysis"]))

        pit_stop_count = 0
        for car in data["pit_stop_analysis"]:
            pit_stop_count += len(car["pit_stops"])

        logger.info('%s %s', "Pit stops:", pit_stop_count)
        bmw_pit_stop_count = count_manufacturer_pit_stops(data["pit_stop_analysis"], "BMW")
        logger.info('%s %s', "BMW pit stops:", bmw_pit_stop_count)

        for car in data["pit_stop_analysis"]:
            if car["manufacturer"] == "BMW":
                logger.debug('%s %s %s %s %s %s %s %s', "BMW :", car["number"], "|", car["vehicle"], "|", car["class"], "| Stops:", len(car["pit_stops"]))

        logger.debug('')


if __name__ == "__main__":
    main()

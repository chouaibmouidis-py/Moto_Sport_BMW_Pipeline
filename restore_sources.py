"""Restore a pinned source archive for pipeline execution."""

import json
import logging
import getpass
import os
import duckdb
from moto_sport_bmw_pipeline.paths import PROJECT_DIR
from moto_sport_bmw_pipeline.logging_config import configure_logging, log_operation
import hashlib
import argparse
from pathlib import Path

logger = logging.getLogger("moto_sport_bmw_pipeline.restore_sources")

def main():

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--destination",
        type=Path,
        help="Restore archived paths beneath this directory.",
    )
    args = parser.parse_args()

    configure_logging()

    reference_path = PROJECT_DIR / "config" / "source_archive.json"

    with reference_path.open("r", encoding="utf-8") as file:
        archive_reference = json.load(file)

    archive_id = archive_reference["archive_id"]
    with log_operation(logger, "Restore pinned source archive",
                       run_id=archive_id, stage="restore_sources", source_id="-"):
        expected_file_count = archive_reference["file_count"]

        logger.info(
            "Archive ID: %s | File count: %s",
            archive_id,
            expected_file_count,
        )

        if not os.environ.get("motherduck_token"):
            os.environ["motherduck_token"] = getpass.getpass(
                "Token MotherDuck : "
            ).strip()

        with duckdb.connect("md:bmw_analytics") as connection:
            archived_files = connection.execute(
                """
                SELECT
                    inventory.relative_path,
                    inventory.sha256,
                    archive.size_bytes,
                    archive.content
                FROM bmw_analytics.main.source_archive_inventory AS inventory
                LEFT JOIN bmw_analytics.main.source_archive AS archive
                    ON inventory.relative_path = archive.relative_path
                    AND inventory.sha256 = archive.sha256
                WHERE inventory.archive_id = ?
                ORDER BY inventory.relative_path
                """,
                [archive_id],
            ).fetchall()

            logger.info("Retrieved inventory entries: %s", len(archived_files))

            if len(archived_files) != expected_file_count:
                raise ValueError("Source restoration rejected: file count mismatch")

            for relative_path, expected_sha256, size_bytes, content in archived_files:
                if content is None or size_bytes is None:
                    raise ValueError(
                        f"Source restoration rejected: missing content for {relative_path}"
                    )

                if len(content) != size_bytes:
                    raise ValueError(
                        f"Source restoration rejected: size mismatch for {relative_path}"
                    )

                actual_sha256 = hashlib.sha256(content).hexdigest()

                if actual_sha256 != expected_sha256:
                    raise ValueError(
                        f"Source restoration rejected: hash mismatch for {relative_path}"
                    )

            logger.info("Verified archived files: %s", len(archived_files))

            if args.destination is None:
                restore_directory = (
                    PROJECT_DIR / "scratch" / "source_restore" / archive_id
                ).resolve()
            else:
                restore_directory = args.destination.resolve()

            restore_targets = []

            for relative_path, _, _, content in archived_files:
                target_path = (restore_directory / relative_path).resolve()

                if not target_path.is_relative_to(
                    restore_directory / "data" / "raw"
                ):
                    raise ValueError(
                        f"Source restoration rejected: invalid path {relative_path}"
                    )

                restore_targets.append((target_path, content))

            for target_path, content in restore_targets:
                target_path.parent.mkdir(parents=True, exist_ok=True)

                temporary_path = target_path.with_name(
                    target_path.name + ".part"
                )

                temporary_path.write_bytes(content)

                if temporary_path.read_bytes() != content:
                    raise ValueError(
                        f"Source restoration rejected: written content differs "
                        f"for {target_path}"
                    )

                temporary_path.replace(target_path)

            logger.info(
                "Restored and verified %s files in %s",
                len(restore_targets),
                restore_directory,
            )

if __name__ == "__main__":
    main()

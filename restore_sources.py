"""Restore a pinned source archive for pipeline execution."""

import argparse
import getpass
import hashlib
import json
import logging
import os
import tempfile
from pathlib import Path

import duckdb

from moto_sport_bmw_pipeline.logging_config import configure_logging, log_operation
from moto_sport_bmw_pipeline.paths import PROJECT_DIR

logger = logging.getLogger("moto_sport_bmw_pipeline.restore_sources")


def validate_archive_content(
    relative_path,
    expected_sha256,
    size_bytes,
    content,
) -> None:

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


def load_archive_inventory(connection, archive_id):

    query = connection.execute(
        """
        SELECT
            relative_path,
            sha256
        FROM
            bmw_analytics.main.source_archive_inventory
        WHERE archive_id = ?
        ORDER BY relative_path
    """,
        [archive_id],
    ).fetchall()

    return query


def load_archive_file(connection, relative_path, expected_sha256):

    query = connection.execute(
        """
        SELECT
            size_bytes,
            content
        FROM
            bmw_analytics.main.source_archive
        WHERE
            relative_path = ? AND sha256 = ?
    """,
        [relative_path, expected_sha256],
    ).fetchone()

    return query


def build_restore_targets(restore_directory, inventory):

    restore_directory = restore_directory.resolve()
    targets = []
    for relative_path, expected_sha256 in inventory:
        target_path = (restore_directory / relative_path).resolve()
        if not target_path.is_relative_to(restore_directory / "data" / "raw"):
            raise ValueError(
                f"Source restoration rejected: invalid path {relative_path}"
            )
        targets.append((target_path, relative_path, expected_sha256))
    return targets


def stage_restore_file(target_path, content):

    target_path.parent.mkdir(parents=True, exist_ok=True)

    descriptor, filename = tempfile.mkstemp(
        dir=target_path.parent, prefix=f"{target_path.name}", suffix=".part"
    )
    temporary_path = Path(filename)
    try:
        with os.fdopen(descriptor, "wb") as file:
            file.write(content)
        if temporary_path.read_bytes() != content:
            raise ValueError(
                f"Source restoration rejected: written content differs for {target_path}"
            )
    except Exception:
        temporary_path.unlink(missing_ok=True)
        raise

    return temporary_path


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
    with log_operation(
        logger,
        "Restore pinned source archive",
        run_id=archive_id,
        stage="restore_sources",
        source_id="-",
    ):
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
            inventory = load_archive_inventory(connection, archive_id)

            if len(inventory) != expected_file_count:
                raise ValueError("Source restoration rejected: file count mismatch")

            if args.destination is None:
                restore_directory = (
                    PROJECT_DIR / "scratch" / "source_restore" / archive_id
                ).resolve()
            else:
                restore_directory = args.destination.resolve()

            targets = build_restore_targets(restore_directory, inventory)
            staged_files = []

            try:
                for target_path, relative_path, expected_sha256 in targets:
                    archived_file = load_archive_file(
                        connection, relative_path, expected_sha256
                    )

                    if archived_file is None:
                        raise ValueError(
                            "Source restoration rejected: missing content "
                            f"for {relative_path}"
                        )

                    size_bytes, content = archived_file

                    validate_archive_content(
                        relative_path, expected_sha256, size_bytes, content
                    )

                    temporary_path = stage_restore_file(target_path, content)
                    staged_files.append((temporary_path, target_path))

                    del content
                    del archived_file

                for temporary_path, target_path in staged_files:
                    temporary_path.replace(target_path)

            finally:
                for temporary_path, _ in staged_files:
                    try:
                        temporary_path.unlink(missing_ok=True)
                    except OSError:
                        logger.exception(
                            "Could not remove restore temporary: %s",
                            temporary_path,
                        )

            logger.info(
                "Restored and verified %s files in %s",
                len(targets),
                restore_directory,
            )


if __name__ == "__main__":
    main()

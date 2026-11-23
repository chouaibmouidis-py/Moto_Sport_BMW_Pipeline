"""Archive pipeline source files for remote reconstruction."""

import json
import logging
import hashlib
from moto_sport_bmw_pipeline.paths import PROJECT_DIR
from moto_sport_bmw_pipeline.logging_config import configure_logging
from moto_sport_bmw_pipeline.integrity import verify_local_file
import getpass
import os
import duckdb
import argparse

logger = logging.getLogger("moto_sport_bmw_pipeline.archive_sources")


def pin_archive_reference(reference_path, archive_id, file_count):
    """Pin a verified archive atomically; called only after the remote commit."""
    temporary_path = reference_path.with_name(reference_path.name + '.part')
    temporary_path.write_text(json.dumps({
        'archive_id': archive_id, 'file_count': file_count,
    }, indent=2) + '\n', encoding='utf-8')
    temporary_path.replace(reference_path)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--pin', action='store_true', help='Update the local archive reference after remote verification.')
    args = parser.parse_args()
    configure_logging()

    manifest_path = PROJECT_DIR / "config" / "sources.json"

    with manifest_path.open("r", encoding="utf-8") as file:
        manifest = json.load(file)
    source_files = []
    for source in manifest["documents"]:
        if not source.get("enabled", False):
            continue

        source_path = (
            PROJECT_DIR
            / "data"
            / "raw"
            / source["source_id"]
            / source["filename"]
        )

        if not source_path.is_file():
            raise FileNotFoundError(f"Raw source not found: {source_path}")

        source_files.append({
            "source_id": source["source_id"],
            "relative_path": source_path.relative_to(PROJECT_DIR).as_posix(),
        })

        metadata_path = source_path.parent / "metadata.json"

        if source.get("expected_sha256"):
            if hashlib.sha256(source_path.read_bytes()).hexdigest() != source["expected_sha256"]:
                raise ValueError(f"Raw fingerprint mismatch: {source["source_id"]}")
            continue

        if not metadata_path.is_file():
            raise FileNotFoundError(
                f"Raw metadata not found: {metadata_path}"
            )

        verify_local_file(source_path, metadata_path)

        source_files.append({
            "source_id": source["source_id"],
            "relative_path": metadata_path.relative_to(PROJECT_DIR).as_posix(),
        })

        logger.info("Source: %s | Path: %s", source["source_id"], source_path)

    relative_paths = [
        source_file["relative_path"]
        for source_file in source_files
    ]

    if len(relative_paths) != len(set(relative_paths)):
        raise ValueError("Duplicate archive paths")

    for source_file in source_files:
        source_path = PROJECT_DIR / source_file["relative_path"]
        content = source_path.read_bytes()

        source_file["sha256"] = hashlib.sha256(content).hexdigest()
        source_file["size_bytes"] = len(content)
        source_file["content"] = content

    inventory = sorted(
        [
            {
                "relative_path": source_file["relative_path"],
                "sha256": source_file["sha256"],
            }
            for source_file in source_files
        ],
        key=lambda item: item["relative_path"],
    )

    inventory_bytes = json.dumps(
        inventory,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")

    archive_id = hashlib.sha256(inventory_bytes).hexdigest()

    logger.info("Source archive ID: %s", archive_id)
    logger.info("Inventoried source files: %s", len(source_files))

    if not os.environ.get("motherduck_token"):
        os.environ["motherduck_token"] = getpass.getpass(
            "Token MotherDuck : "
        ).strip()

    with duckdb.connect("md:bmw_analytics") as connection:
        connection.execute("""
            CREATE TABLE IF NOT EXISTS
                bmw_analytics.main.source_archive (
                    source_id VARCHAR NOT NULL,
                    relative_path VARCHAR NOT NULL,
                    sha256 VARCHAR NOT NULL,
                    size_bytes BIGINT NOT NULL,
                    content BLOB NOT NULL,
                    PRIMARY KEY (relative_path, sha256)
                )
        """)

        connection.execute("""
            CREATE TABLE IF NOT EXISTS
                bmw_analytics.main.source_archive_inventory (
                    archive_id VARCHAR NOT NULL,
                    relative_path VARCHAR NOT NULL,
                    sha256 VARCHAR NOT NULL,
                    PRIMARY KEY (archive_id, relative_path)
                )
        """)

        connection.execute("BEGIN TRANSACTION")

        try:
            for source_file in source_files:
                connection.execute(
                    """
                    INSERT INTO bmw_analytics.main.source_archive (
                        source_id,
                        relative_path,
                        sha256,
                        size_bytes,
                        content
                    )
                    VALUES (?, ?, ?, ?, ?)
                    ON CONFLICT (relative_path, sha256) DO NOTHING
                    """,
                    [
                        source_file["source_id"],
                        source_file["relative_path"],
                        source_file["sha256"],
                        source_file["size_bytes"],
                        source_file["content"],
                    ],
                )

                saved = connection.execute(
                    """
                    SELECT source_id, size_bytes, content
                    FROM bmw_analytics.main.source_archive
                    WHERE relative_path = ? AND sha256 = ?
                    """,
                    [
                        source_file["relative_path"],
                        source_file["sha256"],
                    ],
                ).fetchone()

                expected = (
                    source_file["source_id"],
                    source_file["size_bytes"],
                    source_file["content"],
                )

                if saved != expected:
                    raise ValueError(
                        "Source archive rejected: saved content differs for "
                        f"{source_file['relative_path']}"
                    )

            for item in inventory:
                connection.execute(
                    """
                    INSERT INTO
                        bmw_analytics.main.source_archive_inventory
                    VALUES (?, ?, ?)
                    ON CONFLICT (archive_id, relative_path) DO NOTHING
                    """,
                    [
                        archive_id,
                        item["relative_path"],
                        item["sha256"],
                    ],
                )

            saved_inventory = connection.execute(
                """
                SELECT relative_path, sha256
                FROM bmw_analytics.main.source_archive_inventory
                WHERE archive_id = ?
                ORDER BY relative_path
                """,
                [archive_id],
            ).fetchall()

            expected_inventory = [
                (item["relative_path"], item["sha256"])
                for item in inventory
            ]

            if saved_inventory != expected_inventory:
                raise ValueError(
                    "Source archive rejected: saved inventory differs"
                )

            connection.execute("COMMIT")

        except Exception:
            connection.execute("ROLLBACK")
            raise

    logger.info("Source archive verified: %s files", len(source_files))
    if args.pin:
        pin_archive_reference(PROJECT_DIR / 'config/source_archive.json', archive_id, len(source_files))
        logger.info('Pinned verified source archive: %s', archive_id)


if __name__ == "__main__":
    main()

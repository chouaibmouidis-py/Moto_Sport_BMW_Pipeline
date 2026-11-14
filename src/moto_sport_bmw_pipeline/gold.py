"""Build reproducible Gold candidates from snapshotted input files."""

import hashlib
from pathlib import Path
import json
import logging
import uuid

import duckdb

from .logging_config import log_context
from .marts import (
    build_gold_race_car_summary, build_manufacturer_reference,
    enrich_2023_manufacturers,
)
from .publication import GOLD_OUTPUT_VIEWS, GOLD_REQUIRED_OUTPUTS, publish_run_outputs
from .run_reference import activate_run, get_current_run
from .source_loading import (
    load_classification_sources, load_pit_stop_bronze,
    select_classification_sources, select_pit_stop_sources,
)

logger = logging.getLogger(__name__)


def snapshot_gold_input(
    project_directory: Path,
    run_directory: Path,
    source_path: Path,
    role: str,
) -> dict:
    """Copy an input into the candidate and describe the exact copied bytes."""
    relative_source = source_path.relative_to(project_directory)
    snapshot_path = run_directory / "inputs" / relative_source

    content = source_path.read_bytes()
    sha256 = hashlib.sha256(content).hexdigest()

    snapshot_path.parent.mkdir(parents=True, exist_ok=True)
    snapshot_path.write_bytes(content)

    return {
        "role": role,
        "source_path": relative_source.as_posix(),
        "snapshot_path": snapshot_path.relative_to(
            run_directory
        ).as_posix(),
        "sha256": sha256,
    }

def write_gold_input_manifest(
    run_directory: Path,
    source_run_id: str,
    inputs: list[dict],
) -> Path:
    """Record the source run and all snapshotted inputs of a Gold candidate."""
    manifest = {
        "schema_version": 1,
        "gold_run_id": run_directory.name,
        "source_run_id": source_run_id,
        "inputs": inputs,
    }

    output_path = run_directory / "inputs.json"
    temporary_path = run_directory / "inputs.json.part"

    with temporary_path.open("w", encoding="utf-8") as file:
        json.dump(
            manifest,
            file,
            ensure_ascii=False,
            indent=2,
        )

    temporary_path.replace(output_path)
    return output_path

def validate_gold_inputs(run_directory: Path) -> None:
    """Reject missing or changed input snapshots before Gold activation."""
    manifest_path = run_directory / "inputs.json"
    manifest = json.loads(
        manifest_path.read_text(encoding="utf-8")
    )

    if not manifest["inputs"]:
        raise ValueError("Gold rejected: no input snapshots")

    for record in manifest["inputs"]:
        snapshot_path = run_directory / record["snapshot_path"]

        if not snapshot_path.is_file():
            raise FileNotFoundError(
                f"Gold rejected: input snapshot missing: {snapshot_path}"
            )

        actual_hash = hashlib.sha256(
            snapshot_path.read_bytes()
        ).hexdigest()

        if actual_hash != record["sha256"]:
            raise ValueError(
                f"Gold rejected: input snapshot changed: {snapshot_path}"
            )


def build_gold_candidate(project_directory: Path) -> Path:
    """Snapshot inputs, build Gold tables, validate and activate a separate run.

    Copies pin the bytes used by this build; they do not prove that independently
    published exploratory marts were created together. No main run is modified.
    """
    project_directory = project_directory.resolve()
    source_run = get_current_run(project_directory / "data")
    run_directory = project_directory / "data" / "gold" / "runs" / uuid.uuid4().hex
    records = []

    def freeze(relative_path: Path, role: str) -> Path:
        record = snapshot_gold_input(
            project_directory, run_directory, project_directory / relative_path, role,
        )
        records.append(record)
        return run_directory / record["snapshot_path"]

    with log_context(run_directory.name):
        logger.info("Gold candidate started; main input run: %s", source_run.name)
        try:
            manifest_path = freeze(Path("config/sources.json"), "source_manifest")
            catalog_path = freeze(Path("config/exploration_2023.json"), "exploration_catalog")
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            catalog = json.loads(catalog_path.read_text(encoding="utf-8"))
            if not catalog["events"]:
                raise ValueError("Gold rejected: empty exploration catalog")
            event_ids = [event["event_id"] for event in catalog["events"]]
            if len(event_ids) != len(set(event_ids)):
                raise ValueError("Gold rejected: duplicate exploratory event IDs")

            frozen_project = run_directory / "inputs"
            for name in (
                "36_manufacturer_reference.sql", "37_manufacturer_reference_input.sql",
                "38_enrich_2023_manufacturers.sql", "39_gold_race_car_summary.sql",
            ):
                freeze(Path("sql") / name, "transformation_sql")

            pit_sources = select_pit_stop_sources(manifest["documents"])
            classification_sources = select_classification_sources(manifest["documents"])
            sources = pit_sources + classification_sources
            source_ids = [source["source_id"] for source in sources]
            if len(source_ids) != len(set(source_ids)):
                raise ValueError("Gold rejected: duplicate evidence source IDs")
            for source in sources:
                freeze(
                    Path("data/bronze") / source["source_id"] / "document.parquet",
                    "manufacturer_evidence_bronze",
                )

            json_mart = freeze(
                (source_run / "marts/race_car_summary.parquet").relative_to(project_directory),
                "json_participant_mart",
            )
            csv_marts = [
                str(freeze(
                    Path("data/exploration") / f"{event['event_id']}-{catalog['season']}"
                    / "marts/race_car_summary.parquet",
                    "csv_pdf_participant_mart",
                ))
                for event in catalog["events"]
            ]
            write_gold_input_manifest(run_directory, source_run.name, records)
            validate_gold_inputs(run_directory)

            with duckdb.connect() as connection:
                load_pit_stop_bronze(connection, pit_sources, frozen_project)
                load_classification_sources(connection, classification_sources, frozen_project)
                build_manufacturer_reference(connection, frozen_project)
                connection.read_parquet(csv_marts).create_view("csv_pdf_race_summary")
                enrich_2023_manufacturers(connection, frozen_project)
                connection.read_parquet(str(json_mart)).create_view("json_race_car_summary")
                gold = build_gold_race_car_summary(connection, frozen_project)
                logger.info("Gold participants: %s", gold.count("*").fetchone()[0])
                publish_run_outputs(connection, run_directory, GOLD_OUTPUT_VIEWS)

            validate_gold_inputs(run_directory)
            activate_run(run_directory, required_outputs=GOLD_REQUIRED_OUTPUTS)
            logger.info("Activated Gold run: %s", run_directory.name)
        except Exception:
            logger.exception("Gold candidate failed; previous Gold reference retained")
            raise
    return run_directory

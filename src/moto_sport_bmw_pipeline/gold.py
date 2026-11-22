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
    enrich_csv_pdf_manufacturers,
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


def _empty_participants(connection, view_name):
    """Supply typed empty inputs when the selected run has only one report family."""
    columns = {
        "championship": "VARCHAR", "season": "INTEGER", "event_id": "VARCHAR",
        "session_id": "VARCHAR", "source_id": "VARCHAR", "bronze_sha256": "VARCHAR",
        "car_number": "VARCHAR", "car_model": "VARCHAR", "manufacturer": "VARCHAR",
        "manufacturer_source_id": "VARCHAR", "car_class": "VARCHAR",
        "classification_status": "VARCHAR", "source_entry_index": "VARCHAR",
        "not_finished": "BOOLEAN", "reported_pit_stop_count": "INTEGER",
        "observed_pit_stop_count": "BIGINT", "valid_duration_count": "BIGINT",
        "invalid_duration_count": "BIGINT", "average_pit_time_seconds": "DOUBLE",
        "duration_coverage_percent": "DOUBLE", "comparison_status": "VARCHAR",
        "pit_stop_source_id": "VARCHAR", "pit_stop_bronze_sha256": "VARCHAR",
        "pdf_sha256": "VARCHAR", "stop_detail_status": "VARCHAR", "overall_position": "INTEGER",
    }
    query = ", ".join(f"CAST(NULL AS {kind}) AS {name}" for name, kind in columns.items())
    connection.execute(f"CREATE TEMP VIEW {view_name} AS SELECT {query} WHERE FALSE")


def build_gold_candidate(project_directory: Path, *, expected_source_ids=None) -> Path:
    """Snapshot one complete processing run and activate Gold after verification."""
    project_directory = project_directory.resolve()
    source_run = get_current_run(project_directory / "data/processing")
    run_directory = project_directory / "data/gold/runs" / uuid.uuid4().hex
    records = []

    def freeze(relative_path, role):
        relative_path = Path(relative_path)
        if relative_path.is_absolute() or ".." in relative_path.parts:
            raise ValueError(f"Gold rejected: unsafe input path {relative_path}")
        record = snapshot_gold_input(project_directory, run_directory, project_directory / relative_path, role)
        records.append(record)
        return run_directory / record["snapshot_path"]

    with log_context(run_directory.name):
        try:
            manifest_path = freeze((source_run / "sources.json").relative_to(project_directory), "source_manifest")
            descriptor_path = freeze((source_run / "outputs.json").relative_to(project_directory), "processing_run")
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            if expected_source_ids is not None and set(expected_source_ids) != {source["source_id"] for source in manifest["documents"]}:
                raise ValueError("Gold rejected: active processing selection differs from requested sources")
            descriptor = json.loads(descriptor_path.read_text(encoding="utf-8"))
            if not descriptor["outputs"]:
                raise ValueError("Gold rejected: no processing outputs")
            frozen_project = run_directory / "inputs"
            for name in (
                "36_manufacturer_reference.sql", "37_manufacturer_reference_input.sql",
                "38_enrich_csv_pdf_manufacturers.sql", "39_gold_race_car_summary.sql",
            ):
                freeze(Path("sql") / name, "transformation_sql")
            pit_sources = select_pit_stop_sources(manifest["documents"], format="json")
            classification_sources = select_classification_sources(manifest["documents"], format="json")
            for source in pit_sources + classification_sources:
                relative = f"data/bronze/{source['source_id']}/document.parquet"
                snapshot = freeze(relative, "manufacturer_evidence_bronze")
                if hashlib.sha256(snapshot.read_bytes()).hexdigest() != descriptor["bronze_hashes"][relative]:
                    raise ValueError(f"Gold rejected: Bronze changed after processing: {relative}")
            marts = {}
            for output in descriptor["outputs"]:
                snapshot = freeze(output["path"], output["role"])
                expected = output.get("sha256")
                if expected and hashlib.sha256(snapshot.read_bytes()).hexdigest() != expected:
                    raise ValueError(f"Gold rejected: processing output changed: {output['path']}")
                marts.setdefault(output["role"], []).append(str(snapshot))
            write_gold_input_manifest(run_directory, source_run.name, records)
            validate_gold_inputs(run_directory)
            with duckdb.connect() as connection:
                load_pit_stop_bronze(connection, pit_sources, frozen_project)
                load_classification_sources(connection, classification_sources, frozen_project)
                build_manufacturer_reference(connection, frozen_project)
                for role, view in (
                    ("json_participant_mart", "json_race_car_summary"),
                    ("csv_pdf_participant_mart", "csv_pdf_race_summary"),
                ):
                    if marts.get(role):
                        connection.read_parquet(marts[role]).create_view(view)
                    else:
                        _empty_participants(connection, view)
                enrich_csv_pdf_manufacturers(connection, frozen_project)
                build_gold_race_car_summary(connection, frozen_project)
                publish_run_outputs(connection, run_directory, GOLD_OUTPUT_VIEWS)
            validate_gold_inputs(run_directory)
            activate_run(run_directory, required_outputs=GOLD_REQUIRED_OUTPUTS)
        except Exception:
            logger.exception("Gold candidate failed; previous Gold reference retained")
            raise
    return run_directory

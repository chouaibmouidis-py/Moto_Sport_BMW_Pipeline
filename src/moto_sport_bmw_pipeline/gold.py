"""Build reproducible Gold candidates from snapshotted input files."""

import hashlib
from pathlib import Path
import json
import logging
import uuid
import duckdb
from .logging_config import log_operation
from .marts import (
    build_gold_race_car_summary, build_manufacturer_reference,
    enrich_csv_pdf_manufacturers,
)
from .publication import GOLD_OUTPUT_VIEWS, GOLD_REQUIRED_OUTPUTS, publish_run_outputs
from .run_reference import activate_run, get_current_run

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
        "manufacturer_mapping_status": "VARCHAR",
        "classification_status": "VARCHAR", "source_entry_index": "VARCHAR",
        "not_finished": "BOOLEAN", "reported_pit_stop_count": "INTEGER",
        "observed_pit_stop_count": "BIGINT", "valid_duration_count": "BIGINT",
        "invalid_duration_count": "BIGINT", "average_pit_time_seconds": "DOUBLE",
        "duration_coverage_percent": "DOUBLE", "comparison_status": "VARCHAR",
        "pit_stop_source_id": "VARCHAR", "pit_stop_bronze_sha256": "VARCHAR",
        "pdf_sha256": "VARCHAR", "stop_detail_status": "VARCHAR", "overall_position": "INTEGER","team_name": "VARCHAR",
        "completed_laps": "INTEGER", "fastest_lap_number": "INTEGER", "fastest_lap_speed_kph": "DOUBLE",
        "total_time_raw": "VARCHAR", "total_time_seconds": "DOUBLE",
        "fastest_lap_time_raw": "VARCHAR", "fastest_lap_time_seconds": "DOUBLE",
        "gap_first_raw": "VARCHAR", "gap_previous_raw": "VARCHAR",
        "gap_first_kind": "VARCHAR", "gap_first_seconds": "DOUBLE",
        "gap_first_laps": "INTEGER", "gap_previous_kind": "VARCHAR",
        "gap_previous_seconds": "DOUBLE", "gap_previous_laps": "INTEGER",
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

    with log_operation(logger, "Build Gold candidate",
                       run_id=run_directory.name, stage="gold", source_id="-"):
        try:
            logger.info("Gold input processing run: processing_run=%s", source_run.name)
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
                roles = [
                            ("json_silver_classification", "silver_classification"),
                            ("json_silver_car_entries", "silver_car_entries"),
                        ]
                for role, view in roles:
                    if marts.get(role):
                        connection.read_parquet(marts[role]).create_view(view)
                    elif any(source["format"] == "json" for source in manifest["documents"]):
                        raise ValueError(f"Missing role: {role}")
                    else:
                        empty_view = connection.sql("""
                                        SELECT
                                            CAST(NULL AS VARCHAR) AS source_id,
                                            CAST(NULL AS VARCHAR) AS bronze_sha256,
                                            CAST(NULL AS VARCHAR) AS manufacturer_source_id,
                                            CAST(NULL AS VARCHAR) AS manufacturer,
                                        WHERE FALSE
                                    """)
                        empty_view.create_view(view)
                with log_operation(logger, "Build manufacturer reference from Silver", stage="gold_reference"):
                    build_manufacturer_reference(connection, frozen_project)
                for role, view in (
                    ("json_participant_mart", "json_race_car_summary"),
                    ("csv_pdf_participant_mart", "csv_pdf_race_summary"),
                ):
                    if marts.get(role):
                        connection.read_parquet(marts[role]).create_view(view)
                    else:
                        _empty_participants(connection, view)
                with log_operation(logger, "Enrich participant manufacturers", stage="gold_enrichment"):
                    enrich_csv_pdf_manufacturers(connection, frozen_project)
                with log_operation(logger, "Align Gold participants", stage="gold_build"):
                    build_gold_race_car_summary(connection, frozen_project)
                with log_operation(logger, "Write verified Gold outputs", stage="gold_write"):
                    publish_run_outputs(connection, run_directory, GOLD_OUTPUT_VIEWS)
            validate_gold_inputs(run_directory)
            activate_run(run_directory, required_outputs=GOLD_REQUIRED_OUTPUTS)
        except Exception:
            logger.exception("Gold candidate failed; previous Gold reference retained")
            raise
    return run_directory

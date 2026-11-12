import json
import uuid
from pathlib import Path


REQUIRED_OUTPUTS = (
    "silver/pit_stops.parquet",
    "silver/car_entries.parquet",
    "silver/driver_entries.parquet",
    "silver/sessions.parquet",
    "silver/classification.parquet",
    "quality/classification_pit_stop_comparison.parquet",
    "quality/total_pit_duration_quality.parquet",
    "quality/total_pit_duration_comparison.parquet",
    "quality/session_quality_summary.parquet",
    "marts/enriched_pit_stops.parquet",
    "marts/race_car_summary.parquet",
    "quality/classification_count_quality.parquet",
)


def activate_run(run_directory: Path) -> Path:
    missing_files = [
        relative_path
        for relative_path in REQUIRED_OUTPUTS
        if not (run_directory / relative_path).is_file()
    ]

    if missing_files:
        raise FileNotFoundError(
            f"Run activation rejected: missing files {missing_files}"
        )

    current_path = run_directory.parent.parent / "current.json"
    temporary_path = current_path.with_name(
        f"current.{uuid.uuid4().hex}.json.part"
    )

    with temporary_path.open("w", encoding="utf-8") as file:
        json.dump(
            {"run_id": run_directory.name},
            file,
            indent=2,
        )

    temporary_path.replace(current_path)
    return current_path


def get_current_run(data_directory: Path) -> Path:
    current_path = data_directory / "current.json"

    with current_path.open("r", encoding="utf-8") as file:
        current = json.load(file)

    run_directory = data_directory / "runs" / current["run_id"]

    if not run_directory.is_dir():
        raise FileNotFoundError(
            f"Current run directory not found: {run_directory}"
        )

    return run_directory

"""Publish candidate-run views file by file; activation remains a separate step."""

from pathlib import Path

from .parquet_writer import publish_silver


# Single registry shared by publication and run activation.
OUTPUT_VIEWS = (
    ("silver/pit_stops.parquet", "silver_pit_stops"),
    ("silver/car_entries.parquet", "silver_car_entries"),
    ("silver/driver_entries.parquet", "silver_driver_entries"),
    ("silver/sessions.parquet", "silver_sessions"),
    ("silver/classification.parquet", "silver_classification"),
    ("quality/classification_pit_stop_comparison.parquet", "classification_pit_stop_comparison"),
    ("quality/total_pit_duration_quality.parquet", "total_pit_duration_quality"),
    ("quality/total_pit_duration_comparison.parquet", "total_pit_duration_comparison"),
    ("quality/session_quality_summary.parquet", "session_quality_summary"),
    ("marts/enriched_pit_stops.parquet", "enriched_pit_stops"),
    ("marts/race_car_summary.parquet", "race_car_summary"),
    ("quality/classification_count_quality.parquet", "classification_count_quality"),
)

# Gold tables and their corresponding views in the build connection.
GOLD_OUTPUT_VIEWS = (
    ("race_car_summary.parquet", "gold_race_car_summary"),
    ("manufacturer_reference.parquet", "manufacturer_reference"),
    ("manufacturer_evidence.parquet", "manufacturer_reference_input"),
)

# Input provenance must also be present before activating the Gold run.
GOLD_REQUIRED_OUTPUTS = (
    *(relative_path for relative_path, _ in GOLD_OUTPUT_VIEWS),
    "inputs.json",
)

def publish_run_outputs(
    connection,
    run_directory: Path,
    outputs,
    *,
    verbose: bool = False,
) -> None:
    for relative_path, view_name in outputs:
        relation = connection.table(view_name)

        publish_silver(
            connection,
            relation,
            run_directory / relative_path,
            source_view=view_name,
            verbose=verbose,
        )

from pathlib import Path
from run_publication import get_current_run
import duckdb


mart_path = data_directory = Path(__file__).resolve().parent / "data"
run_directory = get_current_run(data_directory)

print("Reading run:", run_directory.name)

mart_path = run_directory / "marts" / "enriched_pit_stops.parquet"

with duckdb.connect() as connection:
    stops = connection.read_parquet(str(mart_path))

    stops.filter(
        "manufacturer = 'BMW'"
    ).project("""
        source_id,
        car_number,
        pit_number,
        in_driver_first_name,
        in_driver_surname,
        out_driver_first_name,
        out_driver_surname,
        ROUND(pit_time_in_seconds, 3) AS pit_time_in_seconds
    """).show()

    summary_path = (
        run_directory / "marts" / "race_car_summary.parquet"
    )

    summary = connection.read_parquet(str(summary_path))

    summary.filter(
        "manufacturer = 'BMW'"
    ).project("""
        source_id,
        car_number,
        manufacturer,
        car_model,
        overall_position,
        car_class,
        reported_pit_stop_count,
        observed_pit_stop_count,
        average_pit_time_seconds,
        valid_duration_count,
        invalid_duration_count,
        duration_coverage_percent,
        comparison_status
    """).order("source_id, overall_position").show()
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
"""Read anomaly reports from one pinned active run; never activate or rewrite data."""

from pathlib import Path
import logging

import duckdb

from moto_sport_bmw_pipeline.logging_config import configure_logging
from run_publication import get_current_run

logger = logging.getLogger("moto_sport_bmw_pipeline.inspect_quality")


def main():
    configure_logging()
    data_directory = Path(__file__).resolve().parent / "data"
    run_directory = get_current_run(data_directory)

    logger.info('%s %s', "Reading run:", run_directory.name)

    report_path = run_directory / "quality" / "session_quality_summary.parquet"

    with duckdb.connect() as connection:
        report = connection.read_parquet(str(report_path))
        report.filter(
            "missing_count > 0 OR invalid_count > 0"
        ).show()

    total_quality_path = (
        run_directory / "quality" / "total_pit_duration_quality.parquet"
    )

    with duckdb.connect() as connection:
        report_quality = connection.read_parquet(str(total_quality_path))
        report_quality.filter(
            "missing_total_duration_count > 0 OR invalid_total_duration_count > 0"
        ).show()

    comparison_path = (
        run_directory
        / "quality"
        / "classification_pit_stop_comparison.parquet"
    )

    with duckdb.connect() as connection:
        comparison = connection.read_parquet(str(comparison_path))

        comparison.filter(
            "comparison_status != 'matched'"
        ).project("""
            source_id,
            car_number,
            reported_pit_stop_count,
            observed_pit_stop_count,
            comparison_status
        """).show()

    count_quality_path = (
        run_directory
        / "quality"
        / "classification_count_quality.parquet"
    )

    with duckdb.connect() as connection:
        count_quality = connection.read_parquet(str(count_quality_path))

        count_quality.project("""
            source_id,
            participant_count,
            count_mismatch_count,
            count_mismatch_percent
        """).show()


if __name__ == "__main__":
    main()

"""Verify publication safeguards for the classification CSV pipeline."""

from pathlib import Path

import pytest

from moto_sport_bmw_pipeline.pipeline import (
    publish_classification_csv_from_bronze,
)


def test_duplicate_numbers_preserve_previous_output(tmp_path, connection):
    project_directory = Path(__file__).resolve().parent.parent

    directory = tmp_path
    bronze_path = Path(directory) / "bronze.parquet"
    output_path = Path(directory) / "silver.parquet"
    output_path.write_bytes(b"previous version")

    connection.sql("""
        SELECT *
        FROM (VALUES
            ('24', 'BMW M Hybrid V8', '1', 'GTP', 'Classified'),
            (' 24 ', 'BMW M Hybrid V8', '2', 'GTP', 'Classified')
        ) AS t(NUMBER, VEHICLE, POSITION, CLASS, STATUS)
    """).write_parquet(str(bronze_path))

    with pytest.raises(ValueError, match="duplicate car numbers"):
        publish_classification_csv_from_bronze(
            project_directory,
            bronze_path,
            "test-source",
            output_path,
        )

    assert output_path.read_bytes() == b"previous version"

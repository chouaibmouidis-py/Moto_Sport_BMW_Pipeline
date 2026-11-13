"""Explore the single Road America classification; shared transformations live in the package."""

import duckdb

from moto_sport_bmw_pipeline.logging_config import configure_logging
from moto_sport_bmw_pipeline.paths import PROJECT_DIR
from moto_sport_bmw_pipeline.silver import transform_classification
from moto_sport_bmw_pipeline.source_loading import (
    load_classification_bronze, load_classification_sources,
)


def main():
    configure_logging()
    source_id = "imsa-2025-road-america-race-classification-official"
    bronze_path = PROJECT_DIR / "data" / "bronze" / source_id / "document.parquet"
    with duckdb.connect() as connection:
        load_classification_bronze(connection, bronze_path, source_id)
        classification = transform_classification(connection, PROJECT_DIR)
        classification.filter("car_number = '70'").show()


if __name__ == "__main__":
    main()

from pathlib import Path
import hashlib
import duckdb


def transform_classification(connection, project_directory):
    query_path = (
        project_directory / "sql" / "25_silver_classification.sql"
    )
    query = query_path.read_text(encoding="utf-8")
    classification = connection.sql(query)
    classification.create_view("silver_classification")

    checks = (
        (
            "26_check_missing_classification_keys.sql",
            "Classification rejected: missing key values",
        ),
        (
            "27_check_duplicate_classification_keys.sql",
            "Classification rejected: duplicate keys",
        ),
    )

    for filename, error_message in checks:
        check_path = project_directory / "sql" / filename
        check_query = check_path.read_text(encoding="utf-8")
        issue_count = connection.sql(check_query).fetchone()[0]

        if issue_count > 0:
            raise ValueError(error_message)

    return classification

def load_classification_bronze(connection, bronze_path, source_id):
    saved = connection.read_parquet(str(bronze_path))
    bronze_sha256 = hashlib.sha256(
        bronze_path.read_bytes()
    ).hexdigest()

    saved.create_view("bronze_classification_input")

    connection.sql(
        """
        SELECT
            *,
            ? AS source_id,
            ? AS bronze_sha256
        FROM bronze_classification_input
        """,
        params=[source_id, bronze_sha256],
    ).create_view("bronze_classification")

def load_classification_sources(
    connection,
    sources,
    project_directory: Path,
) -> None:

    connection.execute("""
        CREATE TEMP TABLE bronze_classification (
            session JSON,
            fastest_lap JSON,
            classification JSON,
            source_id VARCHAR,
            bronze_sha256 VARCHAR
        )
    """)

    for source in sources:
        bronze_path = (
         project_directory
            / "data"
            / "bronze"
            / source["source_id"]
            / "document.parquet"
        )

        if not bronze_path.is_file():
            raise FileNotFoundError(
                "Classification loading rejected: missing Bronze file "
                f"for source '{source['source_id']}': {bronze_path}"
            )

        bronze_sha256 = hashlib.sha256(
            bronze_path.read_bytes()
        ).hexdigest()

        connection.execute(
            """
            INSERT INTO bronze_classification
            SELECT session, fastest_lap, classification, ?, ?
            FROM read_parquet(?)
            """,
            [
                source["source_id"],
                bronze_sha256,
                str(bronze_path),
            ],
        )

        print("Source chargée :", source["source_id"])

def main() -> None:

    project_directory = Path(__file__).resolve().parent
    source_id = "imsa-2025-road-america-race-classification-official"

    bronze_path = (
        project_directory
        / "data"
        / "bronze"
        / source_id
        / "document.parquet"
    )

    with duckdb.connect() as connection:
        load_classification_bronze(connection, bronze_path, source_id)
        classification = transform_classification(
            connection, project_directory
        )
        classification.filter("car_number = '70'").show()


if __name__ == "__main__":
    main()
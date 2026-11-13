"""Validate source pairing, parent links and participant preservation; build quality views."""

from pathlib import Path


def validate_entry_links(connection, project_directory: Path):

    matched_driver_count = connection.sql("""
        SELECT COUNT(*)
        FROM silver_driver_entries AS drivers
        JOIN silver_car_entries AS cars
            ON drivers.source_id = cars.source_id
            AND drivers.bronze_sha256 = cars.bronze_sha256
            AND drivers.source_entry_index = cars.source_entry_index
    """).fetchone()[0]

    expected_driver_count = connection.table(
        "silver_driver_entries"
    ).count("*").fetchone()[0]

    if matched_driver_count != expected_driver_count:
        raise ValueError(
            "Silver rejected: drivers do not match car entries"
        )

    matched_stops_query_path = (
        project_directory
        / "sql"
        / "13_check_matched_pit_stops.sql"
    )

    matched_stop_count = connection.sql(
        matched_stops_query_path.read_text(encoding="utf-8")
    ).fetchone()[0]

    expected_stop_count = connection.table(
        "silver_pit_stops"
    ).count("*").fetchone()[0]

    if matched_stop_count != expected_stop_count:
        raise ValueError(
            "Silver rejected: pit stops do not match car entries"
        )

    return matched_driver_count, matched_stop_count

def build_session_quality(connection, project_directory: Path):
    query_path = (
        project_directory / "sql" / "18_session_quality_summary.sql"
    )

    session_quality = connection.sql(
        query_path.read_text(encoding="utf-8")
    )
    session_quality.create_view("session_quality_summary")

    return session_quality

def build_total_duration_quality(connection, project_directory: Path):
    query_path = (
        project_directory / "sql" / "23_total_pit_duration_quality.sql"
    )

    total_duration_quality = connection.sql(
        query_path.read_text(encoding="utf-8")
    )
    total_duration_quality.create_view("total_pit_duration_quality")

    return total_duration_quality

def build_source_pairs(connection, project_directory: Path):
    source_pairs_path = (
        project_directory
        / "sql"
        / "29_classification_pit_stop_sources.sql"
    )

    source_pairs = connection.sql(
        source_pairs_path.read_text(encoding="utf-8")
    )
    source_pairs.create_view("classification_pit_stop_sources")

    ambiguous_pairs = connection.sql("""
        SELECT
            classification_source_id,
            COUNT(*) AS candidate_count
        FROM classification_pit_stop_sources
        GROUP BY classification_source_id
        HAVING COUNT(*) > 1
    """).fetchall()

    if ambiguous_pairs:
        raise ValueError(
            f"Source pairing rejected: multiple pit-stop reports "
            f"for the same classification: {ambiguous_pairs}"
        )
    missing_pairs = connection.sql("""
        SELECT sources.source_id
        FROM source_sessions AS sources
        LEFT JOIN classification_pit_stop_sources AS pairs
            ON sources.source_id = pairs.classification_source_id
        WHERE sources.document_type = 'classification'
            AND pairs.classification_source_id IS NULL
    """).fetchall()

    if missing_pairs:
        raise ValueError(
            f"Source pairing rejected: missing pit-stop report "
            f"for classifications: {missing_pairs}"
        )
    return source_pairs

def validate_race_car_summary(connection) -> None:
    missing_key_count = connection.sql("""
        SELECT COUNT(*)
        FROM race_car_summary
        WHERE source_id IS NULL
           OR bronze_sha256 IS NULL
           OR car_number IS NULL
    """).fetchone()[0]

    if missing_key_count > 0:
        raise ValueError(
            "Race car summary rejected: missing key values"
        )

    duplicate_keys = connection.sql("""
        SELECT
            source_id,
            bronze_sha256,
            car_number,
            COUNT(*) AS occurrence_count
        FROM race_car_summary
        GROUP BY source_id, bronze_sha256, car_number
        HAVING COUNT(*) > 1
    """).fetchall()

    if duplicate_keys:
        raise ValueError(
            "Race car summary rejected: duplicate keys"
        )

    missing_participants, unexpected_participants = connection.sql("""
        WITH missing AS (
            SELECT source_id, bronze_sha256, car_number
            FROM silver_classification
            EXCEPT
            SELECT source_id, bronze_sha256, car_number
            FROM race_car_summary
        ),
        unexpected AS (
            SELECT source_id, bronze_sha256, car_number
            FROM race_car_summary
            EXCEPT
            SELECT source_id, bronze_sha256, car_number
            FROM silver_classification
        )
        SELECT
            (SELECT COUNT(*) FROM missing),
            (SELECT COUNT(*) FROM unexpected)
    """).fetchone()

    if missing_participants > 0 or unexpected_participants > 0:
        raise ValueError(
            "Race car summary rejected: participant keys differ"
        )

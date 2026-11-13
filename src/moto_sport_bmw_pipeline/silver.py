"""Transform Bronze documents and reject invalid Silver keys using existing SQL."""

from pathlib import Path


def transform_sessions(connection, project_directory: Path):

    sessions_query_path = (
        project_directory / "sql" / "16_silver_sessions.sql"
    )

    sessions = connection.sql(
        sessions_query_path.read_text(encoding="utf-8")
    )
    sessions.create_view("silver_sessions")

    session_key_check_path = (
        project_directory / "sql" / "17_check_session_keys.sql"
    )

    missing_session_keys, duplicate_session_keys = connection.sql(
        session_key_check_path.read_text(encoding="utf-8")
    ).fetchone()

    if missing_session_keys > 0:
        raise ValueError("Silver sessions rejected: missing key values")

    if duplicate_session_keys > 0:
        raise ValueError("Silver sessions rejected: duplicate keys")

    return sessions

def transform_car_entries(connection, project_directory: Path):

    car_entries_query_path = (
        project_directory / "sql" / "10_silver_car_entries.sql"
    )

    car_entries = connection.sql(
        car_entries_query_path.read_text(encoding="utf-8")
    )
    car_entries.create_view("silver_car_entries")

    car_entry_key_check_path = (
        project_directory
        / "sql"
        / "11_check_missing_car_entry_keys.sql"
    )

    missing_car_entry_key_count = connection.sql(
        car_entry_key_check_path.read_text(encoding="utf-8")
    ).fetchone()[0]

    if missing_car_entry_key_count > 0:
        raise ValueError("Silver car entries rejected: missing key values")

    car_entry_duplicate_check_path = (
        project_directory
        / "sql"
        / "12_check_duplicate_car_entry_keys.sql"
    )

    duplicate_car_entry_key_count = connection.sql(
        car_entry_duplicate_check_path.read_text(encoding="utf-8")
    ).fetchone()[0]

    if duplicate_car_entry_key_count > 0:
        raise ValueError("Silver car entries rejected: duplicate keys")
    return car_entries

def transform_driver_entries(connection, project_directory: Path):

    driver_entries_query_path = (
        project_directory / "sql" / "14_silver_driver_entries.sql"
    )

    driver_entries = connection.sql(
        driver_entries_query_path.read_text(encoding="utf-8")
    )
    driver_entries.create_view("silver_driver_entries")


    driver_key_check_path = (
        project_directory / "sql" / "15_check_driver_entry_keys.sql"
    )

    missing_driver_keys, duplicate_driver_keys = connection.sql(
        driver_key_check_path.read_text(encoding="utf-8")
    ).fetchone()

    if missing_driver_keys > 0:
        raise ValueError("Silver drivers rejected: missing key values")

    if duplicate_driver_keys > 0:
        raise ValueError("Silver drivers rejected: duplicate keys")

    return driver_entries

def transform_pit_stops(connection, project_directory: Path):
    silver_query_path = (
        project_directory / "sql" / "07_silver_pit_stops.sql"
    )

    converted = connection.sql(
        silver_query_path.read_text(encoding="utf-8")
    )
    converted.create_view("silver_pit_stops")

    key_check_path = (
        project_directory / "sql" / "08_check_missing_pit_stop_keys.sql"
    )

    invalid_key_count = connection.sql(
        key_check_path.read_text(encoding="utf-8")
        ).fetchone()[0]

    if invalid_key_count > 0:
        raise ValueError("Silver rejected: missing key values")

    duplicate_check_path = (
        project_directory / "sql" / "09_check_duplicate_pit_stop_keys.sql"
    )

    duplicate_key_count = connection.sql(
        duplicate_check_path.read_text(encoding="utf-8")
        ).fetchone()[0]

    if duplicate_key_count > 0:
        raise ValueError("Silver rejected: duplicate keys")

    return converted

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

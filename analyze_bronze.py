import json
from pathlib import Path
import uuid
import duckdb
from silver_writer import publish_silver
import hashlib
import argparse
from run_publication import activate_run


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Build and check the BMW pipeline outputs."
    )
    parser.add_argument(
            "--verbose",
        action="store_true",
        help="Display detailed exploration tables.",
    )
    args = parser.parse_args()

    run_id = uuid.uuid4().hex
    run_directory = (
        Path(__file__).resolve().parent
        / "data"
        / "runs"
        / run_id
    )

    manifest_path = Path(__file__).parent / "config" / "sources.json"

    with manifest_path.open("r", encoding="utf-8") as file:
        manifest = json.load(file)

    selected_sources = select_pit_stop_sources(manifest["documents"])

    print("Sources sélectionnées :", len(selected_sources))

    with duckdb.connect() as connection:

        duration_parser_path = (
            Path(__file__).parent / "sql" / "21_create_duration_parser.sql"
        )

        connection.execute(
            duration_parser_path.read_text(encoding="utf-8")
        )

        if args.verbose:
            connection.sql("""
                SELECT
                    parse_duration_seconds('1:04.099') AS valid_seconds,
                    parse_duration_seconds('00:75') AS invalid_seconds
            """).show()

        connection.execute("""
            CREATE TEMP TABLE bronze_document (
                session JSON,
                pit_stop_analysis JSON,
                source_id VARCHAR,
                bronze_sha256 VARCHAR
            )
        """)

        for source in selected_sources:
            bronze_path = (
                Path(__file__).parent
                / "data"
                / "bronze"
                / source["source_id"]
                / "document.parquet"
            )

            bronze_sha256 = hashlib.sha256(
                bronze_path.read_bytes()
            ).hexdigest()

            connection.execute(
                """
                INSERT INTO bronze_document
                SELECT session, pit_stop_analysis, ?, ?
                FROM read_parquet(?)
                """,
                [
                    source["source_id"],
                    bronze_sha256,
                    str(bronze_path),
                ],
            )

            print("Source chargée :", source["source_id"])

        saved = connection.table("bronze_document")
        print("Documents chargés :", saved.count("*").fetchone()[0])

        sessions_query_path = (
            Path(__file__).parent / "sql" / "16_silver_sessions.sql"
        )

        sessions = connection.sql(
            sessions_query_path.read_text(encoding="utf-8")
        )
        sessions.create_view("silver_sessions")

        session_key_check_path = (
            Path(__file__).parent / "sql" / "17_check_session_keys.sql"
        )

        missing_session_keys, duplicate_session_keys = connection.sql(
            session_key_check_path.read_text(encoding="utf-8")
        ).fetchone()

        if missing_session_keys > 0:
            raise ValueError("Silver sessions rejected: missing key values")

        if duplicate_session_keys > 0:
            raise ValueError("Silver sessions rejected: duplicate keys")

        if args.verbose:
            sessions.show()

        session_quality_query_path = (
            Path(__file__).parent
            / "sql"
            / "18_session_quality_summary.sql"
        )

        session_quality = connection.sql(
            session_quality_query_path.read_text(encoding="utf-8")
        )
        session_quality.create_view("session_quality_summary")
        if args.verbose:
            session_quality.show()

        car_entries_query_path = (
            Path(__file__).parent / "sql" / "10_silver_car_entries.sql"
        )

        car_entries = connection.sql(
            car_entries_query_path.read_text(encoding="utf-8")
        )
        car_entries.create_view("silver_car_entries")

        driver_entries_query_path = (
            Path(__file__).parent / "sql" / "14_silver_driver_entries.sql"
        )

        driver_entries = connection.sql(
            driver_entries_query_path.read_text(encoding="utf-8")
        )
        driver_entries.create_view("silver_driver_entries")
        if args.verbose:
            connection.sql("""
                SELECT
                    source_id,
                    bronze_sha256,
                    source_entry_index,
                    driver_number,
                    COUNT(*) AS occurrence_count
                FROM silver_driver_entries
                WHERE driver_number IS NOT NULL
                GROUP BY
                    source_id,
                    bronze_sha256,
                    source_entry_index,
                    driver_number
                HAVING COUNT(*) > 1
            """).show()
        if args.verbose:
            connection.sql("""
                SELECT
                    source_id,
                    COUNT(*) AS driver_entry_count
                FROM silver_driver_entries
                GROUP BY source_id
                ORDER BY source_id
            """).show()

        print(
            "Silver driver entries:",
            driver_entries.count("*").fetchone()[0],
        )
        if args.verbose:
            driver_entries.show()

        car_entry_key_check_path = (
            Path(__file__).parent
            / "sql"
            / "11_check_missing_car_entry_keys.sql"
        )

        missing_car_entry_key_count = connection.sql(
            car_entry_key_check_path.read_text(encoding="utf-8")
        ).fetchone()[0]

        if missing_car_entry_key_count > 0:
            raise ValueError("Silver car entries rejected: missing key values")

        car_entry_duplicate_check_path = (
            Path(__file__).parent
            / "sql"
            / "12_check_duplicate_car_entry_keys.sql"
        )

        duplicate_car_entry_key_count = connection.sql(
            car_entry_duplicate_check_path.read_text(encoding="utf-8")
        ).fetchone()[0]

        if duplicate_car_entry_key_count > 0:
            raise ValueError("Silver car entries rejected: duplicate keys")

        if args.verbose:
            connection.sql("""
                SELECT
                    source_id,
                    COUNT(*) AS car_entry_count,
                    SUM(pit_stop_count) AS total_pit_stops
                FROM silver_car_entries
                GROUP BY source_id
                ORDER BY source_id
            """).show()

        print("Silver car entries:", car_entries.count("*").fetchone()[0])
        if args.verbose:
            car_entries.show()

        if args.verbose:
            saved.project("""
                NULLIF(TRIM(json_extract_string(session, '$.event_name')), '') AS event_name,
                NULLIF(TRIM(json_extract_string(session, '$.session_name')), '') AS session_name,
                NULLIF(TRIM(json_extract_string(session, '$.circuit.name')), '')  AS circuit_name,
                NULLIF(
                TRIM(json_extract_string(session, '$.circuit.country')),
                ''
                ) AS circuit_country,
                TRY_CAST(
                json_extract_string(session, '$.circuit.length')
                AS DOUBLE
                ) AS circuit_length
            """).show()
        if args.verbose:
            saved.project(
                "json_array_length(pit_stop_analysis) AS car_entry_count"
            ).show()

        if args.verbose:
            connection.sql("""
            SELECT
                entry.key AS source_entry_index,
                json_extract_string(entry.value, '$.number') AS car_number,
                json_extract_string(entry.value, '$.vehicle') AS car_model,
                NULLIF(
                    TRIM(json_extract_string(entry.value, '$.manufacturer')),
                ''
                ) AS manufacturer,
                NULLIF(
                    TRIM(json_extract_string(entry.value, '$.class')),
                ''
                ) AS car_class,
                NULLIF(
                    TRIM(json_extract_string(entry.value, '$.team')),
                ''
                ) AS team,
                json_array_length(entry.value, '$.pit_stops') AS pit_stop_count
            FROM bronze_document
            CROSS JOIN json_each(pit_stop_analysis) AS entry
            """).show()

        if args.verbose:
            connection.sql("""
                SELECT
                    COUNT(*) AS car_entry_count,
                    SUM(
                        json_array_length(entry.value, '$.pit_stops')
                    ) AS total_pit_stops
                FROM bronze_document
                CROSS JOIN json_each(pit_stop_analysis) AS entry
            """).show()

        silver_query_path = (
            Path(__file__).parent / "sql" / "07_silver_pit_stops.sql"
        )

        converted = connection.sql(
            silver_query_path.read_text(encoding="utf-8")
        )

        converted.create_view("silver_pit_stops")

        total_duration_quality_path = (
            Path(__file__).parent / "sql" / "23_total_pit_duration_quality.sql"
        )

        total_duration_quality = connection.sql(
            total_duration_quality_path.read_text(encoding="utf-8")
        )

        total_comparison_path = (
            Path(__file__).parent
            / "sql"
            / "24_compare_total_pit_durations.sql"
        )

        total_comparison = connection.sql(
            total_comparison_path.read_text(encoding="utf-8")
        )

        total_comparison_output_path = (
            run_directory
            / "quality"
            / "total_pit_duration_comparison.parquet"
        )

        total_comparison.create_view("total_pit_duration_comparison")

        print(
            "Cars with pit stops:",
            total_comparison.count("*").fetchone()[0],
        )
        total_comparison_issues = total_comparison.filter(
            "comparison_status != 'matched'"
        )

        issue_count = total_comparison_issues.count("*").fetchone()[0]
        print("Total duration comparison issues:", issue_count)

        if issue_count > 0:
            total_comparison_issues.project("""
                source_id,
                car_number,
                stop_count,
                converted_duration_count,
                calculated_total_seconds,
                reported_total_seconds
            """).limit(20).show()

        if args.verbose:
            total_duration_quality.show()
        total_duration_quality.create_view("total_pit_duration_quality")

        total_duration_quality_output_path = run_directory / "quality" / "total_pit_duration_quality.parquet"

        total_duration_check_path = (
            Path(__file__).parent
            / "sql"
            / "22_check_missing_total_pit_durations.sql"
        )

        total_duration_check = connection.sql(
            total_duration_check_path.read_text(encoding="utf-8")
        )

        missing_total_count = total_duration_check.count("*").fetchone()[0]
        print("Unconverted total pit durations:", missing_total_count)

        if missing_total_count > 0:
            total_duration_check.limit(20).show()



        duration_issues = converted.filter("""
            clock_duration_seconds IS NULL
            OR pit_time_in_seconds IS NULL
            OR ABS(
                clock_duration_seconds - pit_time_in_seconds
            ) > 0.001
        """)

        duration_issue_count = duration_issues.count("*").fetchone()[0]
        print("Duration comparison issues:", duration_issue_count)

        if duration_issue_count > 0:
            duration_issues.project("""
                source_id,
                car_number,
                pit_number,
                clock_duration_seconds,
                pit_time_in_seconds
            """).limit(20).show()

        if args.verbose:
            converted.filter("""
                source_id = 'imsa-2025-daytona-race-hour24-pit-stops'
                AND car_number = '31'
                AND pit_number = 12
            """).project("""
                in_time,
                out_time,
                ROUND(clock_duration_seconds, 3) AS clock_duration_seconds,
                ROUND(pit_time_in_seconds, 3) AS reported_duration_seconds
            """).show()

        driver_links_query_path = (
            Path(__file__).parent
            / "sql"
            / "19_check_pit_stop_driver_links.sql"
        )

        driver_link_issues = connection.sql(
            driver_links_query_path.read_text(encoding="utf-8")
        )

        if args.verbose:
            driver_link_issues.show()

        invalid_driver_link_count = driver_link_issues.filter(
            "link_status IN ('unmatched', 'ambiguous')"
        ).count("*").fetchone()[0]

        if invalid_driver_link_count > 0:
            raise ValueError(
                "Silver rejected: unmatched or ambiguous driver links"
            )

        missing_driver_link_count = driver_link_issues.filter(
            "link_status = 'missing'"
        ).count("*").fetchone()[0]

        print("Missing driver references:", missing_driver_link_count)

        enriched_stops_query_path = (
            Path(__file__).parent / "sql" / "20_enriched_pit_stops.sql"
        )

        enriched_stops = connection.sql(
            enriched_stops_query_path.read_text(encoding="utf-8")
        )

        enriched_stops.create_view("enriched_pit_stops")

        enriched_stop_count = enriched_stops.count("*").fetchone()[0]
        expected_stop_count = converted.count("*").fetchone()[0]

        if enriched_stop_count != expected_stop_count:
            raise ValueError("Enriched stops rejected: row count mismatch")

        print("Enriched pit stops:", enriched_stop_count)
        if args.verbose:
            enriched_stops.show()

        if args.verbose:
            enriched_stops.filter("""
                source_id = 'imsa-2025-road-america-race-pit-stops'
                AND car_number = '1'
                AND pit_number = 1
            """).project("""
                car_number,
                pit_number,
                in_driver_first_name,
                in_driver_surname,
                out_driver_first_name,
                out_driver_surname
            """).show()

        if args.verbose:
            connection.sql("""
                SELECT
                    stops.source_id,
                    stops.car_number,
                    stops.pit_number,
                    stops.in_driver_number
                FROM silver_pit_stops AS stops
                LEFT JOIN silver_driver_entries AS drivers
                    ON stops.source_id = drivers.source_id
                   AND stops.bronze_sha256 = drivers.bronze_sha256
                   AND stops.source_entry_index = drivers.source_entry_index
                   AND stops.in_driver_number = drivers.driver_number
                WHERE drivers.source_driver_index IS NULL
            """).show()

        if args.verbose:
            connection.sql("""
                SELECT
                    stops.source_id,
                    stops.car_number,
                    stops.pit_number,
                    stops.out_driver_number
                FROM silver_pit_stops AS stops
                LEFT JOIN silver_driver_entries AS drivers
                    ON stops.source_id = drivers.source_id
                   AND stops.bronze_sha256 = drivers.bronze_sha256
                   AND stops.source_entry_index = drivers.source_entry_index
                   AND stops.out_driver_number = drivers.driver_number
                WHERE drivers.source_driver_index IS NULL
            """).show()

        driver_key_check_path = (
            Path(__file__).parent / "sql" / "15_check_driver_entry_keys.sql"
        )

        missing_driver_keys, duplicate_driver_keys = connection.sql(
            driver_key_check_path.read_text(encoding="utf-8")
        ).fetchone()

        if missing_driver_keys > 0:
            raise ValueError("Silver drivers rejected: missing key values")

        if duplicate_driver_keys > 0:
            raise ValueError("Silver drivers rejected: duplicate keys")

        matched_driver_count = connection.sql("""
            SELECT COUNT(*)
            FROM silver_driver_entries AS drivers
            JOIN silver_car_entries AS cars
                ON drivers.source_id = cars.source_id
               AND drivers.bronze_sha256 = cars.bronze_sha256
               AND drivers.source_entry_index = cars.source_entry_index
        """).fetchone()[0]

        expected_driver_count = driver_entries.count("*").fetchone()[0]

        if matched_driver_count != expected_driver_count:
            raise ValueError(
                "Silver rejected: drivers do not match car entries"
            )

        print("Matched driver entries:", matched_driver_count)

        matched_stops_query_path = (
            Path(__file__).parent
            / "sql"
            / "13_check_matched_pit_stops.sql"
        )

        matched_stop_count = connection.sql(
            matched_stops_query_path.read_text(encoding="utf-8")
        ).fetchone()[0]

        expected_stop_count = converted.count("*").fetchone()[0]

        if matched_stop_count != expected_stop_count:
            raise ValueError(
                "Silver rejected: pit stops do not match car entries"
            )

        print("Matched pit stops:", matched_stop_count)

        if args.verbose:
            connection.sql("""
                SELECT
                    source_id,
                    car_class,
                    COUNT(*) AS bmw_pit_stop_count
                FROM silver_pit_stops
                WHERE manufacturer = 'BMW'
                GROUP BY source_id, car_class
                ORDER BY source_id, car_class
            """).show()
        if args.verbose:
            converted.show()

        if args.verbose:
            connection.sql("""
                SELECT
                    source_id,
                    COUNT(*) AS total_pit_stops
                FROM silver_pit_stops
                GROUP BY source_id
                ORDER BY source_id
            """).show()

        if args.verbose:
            connection.sql("""
                SELECT
                    source_id,
                    car_number,
                    pit_number,
                    COUNT(*) AS occurrence_count
                FROM silver_pit_stops
                GROUP BY source_id, car_number, pit_number
                HAVING COUNT(*) > 1
            """).show()

        if args.verbose:
            connection.sql("""
                SELECT source_id, car_number, pit_number
                FROM silver_pit_stops
                WHERE source_id IS NULL
                    OR car_number IS NULL
                    OR pit_number IS NULL
            """).show()

        key_check_path = (
            Path(__file__).parent / "sql" / "08_check_missing_pit_stop_keys.sql"
        )

        invalid_key_count = connection.sql(
            key_check_path.read_text(encoding="utf-8")
            ).fetchone()[0]

        if invalid_key_count > 0:
            raise ValueError("Silver rejected: missing key values")

        duplicate_check_path = (
            Path(__file__).parent / "sql" / "09_check_duplicate_pit_stop_keys.sql"
        )

        duplicate_key_count = connection.sql(
            duplicate_check_path.read_text(encoding="utf-8")
            ).fetchone()[0]

        if duplicate_key_count > 0:
            raise ValueError("Silver rejected: duplicate keys")

        silver_output_path = run_directory / "silver" / "pit_stops.parquet"

        publish_silver(
            connection, converted, silver_output_path, verbose=args.verbose
        )

        car_entries_output_path = run_directory / "silver" / "car_entries.parquet"

        publish_silver(
            connection,
            car_entries,
            car_entries_output_path,
            source_view="silver_car_entries",
            verbose=args.verbose,
        )

        driver_entries_output_path = run_directory / "silver" / "driver_entries.parquet"

        publish_silver(
            connection,
            driver_entries,
            driver_entries_output_path,
            source_view="silver_driver_entries",
            verbose=args.verbose,
        )

        sessions_output_path = run_directory / "silver" / "sessions.parquet"

        publish_silver(
            connection,
            sessions,
            sessions_output_path,
            source_view="silver_sessions",
            verbose=args.verbose,
        )

        session_quality_output_path = run_directory / "quality" / "session_quality_summary.parquet"

        publish_silver(
            connection,
            total_duration_quality,
            total_duration_quality_output_path,
            source_view="total_pit_duration_quality",
            verbose=args.verbose,
        )

        publish_silver(
            connection,
            total_comparison,
            total_comparison_output_path,
            source_view="total_pit_duration_comparison",
            verbose=args.verbose,
        )

        publish_silver(
            connection,
            session_quality,
            session_quality_output_path,
            source_view="session_quality_summary",
            verbose=args.verbose,
        )

        enriched_stops_output_path = run_directory / "marts" / "enriched_pit_stops.parquet"

        publish_silver(
            connection,
            enriched_stops,
            enriched_stops_output_path,
            source_view="enriched_pit_stops",
            verbose=args.verbose,
        )

        summary_query_path = (
            Path(__file__).parent / "sql" / "06_pit_stop_summary.sql"
        )

        summary_query_path = (
            Path(__file__).parent / "sql" / "06_pit_stop_summary.sql"
        )

        if args.verbose:
            connection.sql(
                summary_query_path.read_text(encoding="utf-8")
            ).show()

    current_path = activate_run(run_directory)
    print("Activated run:", run_id)
    print("Current reference:", current_path)


def select_pit_stop_sources(documents):
    selected_sources = []
    for document in documents:
        if document.get("enabled", False) and document["document_type"] == "pit_stops":
            selected_sources.append(document)
    return selected_sources


if __name__ == "__main__":
    main()

-- Stack season participants using explicit, compatible columns.
-- Missing information remains NULL rather than being inferred.

SELECT
    championship,
    season,
    event_id,
    session_id,
    source_id,
    bronze_sha256,
    car_number,
    car_model,
    manufacturer_source_id,
    manufacturer,
    reported_pit_stop_count,
    observed_pit_stop_count,
    valid_duration_count,
    invalid_duration_count,
    average_pit_time_seconds,
    duration_coverage_percent,
    comparison_status,
    pit_stop_source_id,
    pit_stop_bronze_sha256,
    CASE
        WHEN manufacturer_mapping_status = 'matched' THEN 'reference'
        ELSE 'unresolved'
    END AS manufacturer_origin,
    manufacturer_mapping_status,
    car_class,
    classification_status,
    CAST(NULL AS VARCHAR) AS source_entry_index,
    pdf_sha256,
    manufacturer_name_count,
    stop_detail_status,
    overall_position,
    CAST(NULL AS BOOLEAN) AS not_finished
FROM enriched_2023_participants

UNION ALL

SELECT
    championship,
    season,
    event_id,
    session_id,
    source_id,
    bronze_sha256,
    car_number,
    car_model,
    CAST(NULL AS VARCHAR) AS manufacturer_source_id,
    manufacturer,
    reported_pit_stop_count,
    observed_pit_stop_count,
    valid_duration_count,
    invalid_duration_count,
    average_pit_time_seconds,
    duration_coverage_percent,
    comparison_status,
    pit_stop_source_id,
    pit_stop_bronze_sha256,
    CASE
        WHEN NULLIF(TRIM(manufacturer), '') IS NOT NULL THEN 'source'
        ELSE 'unresolved'
    END AS manufacturer_origin,
    'not_applicable' AS manufacturer_mapping_status,
    car_class,
    CAST(NULL AS VARCHAR) AS classification_status,
    source_entry_index,
    CAST(NULL AS VARCHAR) AS pdf_sha256,
    CAST(NULL AS BIGINT) AS manufacturer_name_count,
    CASE
        WHEN pit_stop_source_id IS NULL THEN 'missing_pit_stop_report'
        WHEN observed_pit_stop_count IS NULL THEN 'no_stop_details'
        ELSE 'available'
    END AS stop_detail_status,
    overall_position,
    not_finished
FROM json_race_car_summary;
-- Normalize JSON classification and qualify gaps without mixing seconds and laps.
-- Separate stages keep duration-macro subqueries out of same-SELECT alias dependencies.

WITH normalized AS (
    SELECT
        source_id,
        bronze_sha256,
        entry.key AS source_entry_index,
        NULLIF(TRIM(json_extract_string(entry.value, '$.number')), '') AS car_number,
        NULLIF(TRIM(json_extract_string(entry.value, '$.manufacturer')), '') AS manufacturer,
        NULLIF(TRIM(json_extract_string(entry.value, '$.imsa_manufacturerid')), '') AS manufacturer_source_id,
        NULLIF(TRIM(json_extract_string(entry.value, '$.vehicle')), '') AS car_model,
        TRY_CAST(json_extract_string(entry.value, '$.position') AS INTEGER) AS overall_position,
        NULLIF(TRIM(json_extract_string(entry.value, '$.class')), '') AS car_class,
        NULLIF(TRIM(json_extract_string(entry.value, '$.team')), '') AS team_name,
        TRY_CAST(json_extract_string(entry.value, '$.laps') AS INTEGER) AS completed_laps,
        TRY_CAST(json_extract_string(entry.value, '$.fastest_lap_number') AS INTEGER) AS fastest_lap_number,
        TRY_CAST(json_extract_string(entry.value, '$.fastest_lap_kph') AS DOUBLE) AS fastest_lap_speed_kph,
        NULLIF(TRIM(json_extract_string(entry.value, '$.elapsed_time')), '') AS total_time_raw,
        NULLIF(TRIM(json_extract_string(entry.value, '$.fastest_lap_time')), '') AS fastest_lap_time_raw,
        NULLIF(TRIM(json_extract_string(entry.value, '$.gap_first')), '') AS gap_first_raw,
        NULLIF(TRIM(json_extract_string(entry.value, '$.gap_previous')), '') AS gap_previous_raw,
        TRY_CAST(json_extract_string(entry.value, '$.pit_stops') AS INTEGER) AS reported_pit_stop_count,
        TRY_CAST(json_extract_string(entry.value, '$.not_finished') AS BOOLEAN) AS not_finished
    FROM bronze_classification
    CROSS JOIN json_each(classification) AS entry
),
converted AS (
    SELECT
        *,
        parse_duration_seconds(total_time_raw) AS total_time_seconds,
        parse_duration_seconds(fastest_lap_time_raw) AS fastest_lap_time_seconds,
        parse_duration_seconds(substring(gap_first_raw, 2)) AS gap_first_parsed_seconds,
        parse_duration_seconds(substring(gap_previous_raw, 2)) AS gap_previous_parsed_seconds
    FROM normalized
),
qualified AS (
    SELECT
        *,
        CASE
            WHEN gap_first_raw IS NULL THEN 'missing'
            WHEN gap_first_raw = '-' THEN 'marker'
            WHEN starts_with(gap_first_raw, '+')
                AND gap_first_parsed_seconds IS NOT NULL THEN 'time'
            WHEN regexp_full_match(lower(gap_first_raw), '[0-9]+ laps?') THEN 'laps'
            ELSE 'unrecognized'
        END AS gap_first_kind,
        CASE
            WHEN gap_previous_raw IS NULL THEN 'missing'
            WHEN gap_previous_raw = '-' THEN 'marker'
            WHEN starts_with(gap_previous_raw, '+')
                AND gap_previous_parsed_seconds IS NOT NULL THEN 'time'
            WHEN regexp_full_match(lower(gap_previous_raw), '[0-9]+ laps?') THEN 'laps'
            ELSE 'unrecognized'
        END AS gap_previous_kind
    FROM converted
)
SELECT
    source_id,
    bronze_sha256,
    source_entry_index,
    car_number,
    manufacturer,
    manufacturer_source_id,
    car_model,
    overall_position,
    car_class,
    team_name,
    completed_laps,
    fastest_lap_number,
    fastest_lap_speed_kph,
    total_time_raw,
    total_time_seconds,
    fastest_lap_time_raw,
    fastest_lap_time_seconds,
    gap_first_raw,
    gap_previous_raw,
    gap_first_kind,
    CASE WHEN gap_first_kind = 'time' THEN gap_first_parsed_seconds ELSE NULL END AS gap_first_seconds,
    CASE WHEN gap_first_kind = 'laps' THEN TRY_CAST(split_part(gap_first_raw, ' ', 1) AS INTEGER) ELSE NULL END AS gap_first_laps,
    gap_previous_kind,
    CASE WHEN gap_previous_kind = 'time' THEN gap_previous_parsed_seconds ELSE NULL END AS gap_previous_seconds,
    CASE WHEN gap_previous_kind = 'laps' THEN TRY_CAST(split_part(gap_previous_raw, ' ', 1) AS INTEGER) ELSE NULL END AS gap_previous_laps,
    reported_pit_stop_count,
    not_finished
FROM qualified;

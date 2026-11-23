-- Normalize CSV classification and qualify gaps without mixing seconds and laps.
-- Separate stages keep duration-macro subqueries out of same-SELECT alias dependencies.

WITH normalized AS (
    SELECT
        source_id,
        bronze_sha256,
        NULLIF(TRIM(NUMBER), '') AS car_number,
        NULLIF(TRIM(VEHICLE), '') AS car_model,
        TRY_CAST(POSITION AS INTEGER) AS overall_position,
        NULLIF(TRIM(CLASS), '') AS car_class,
        NULLIF(TRIM(STATUS), '') AS classification_status,
        NULLIF(TRIM(IMSA_ManufacturerId), '') AS manufacturer_source_id,
        NULLIF(TRIM(TEAM), '') AS team_name,
        TRY_CAST(LAPS AS INTEGER) AS completed_laps,
        TRY_CAST(FL_LAPNUM AS INTEGER) AS fastest_lap_number,
        TRY_CAST(FL_KPH AS DOUBLE) AS fastest_lap_speed_kph,
        NULLIF(TRIM(TOTAL_TIME), '') AS total_time_raw,
        NULLIF(TRIM(FL_TIME), '') AS fastest_lap_time_raw,
        NULLIF(TRIM(GAP_FIRST), '') AS gap_first_raw,
        NULLIF(TRIM(GAP_PREVIOUS), '') AS gap_previous_raw
    FROM bronze_classification_csv
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
            WHEN regexp_full_match(gap_first_raw, '[0-9]+ Laps?') THEN 'laps'
            ELSE 'unrecognized'
        END AS gap_first_kind,
        CASE
            WHEN gap_previous_raw IS NULL THEN 'missing'
            WHEN gap_previous_raw = '-' THEN 'marker'
            WHEN starts_with(gap_previous_raw, '+')
                AND gap_previous_parsed_seconds IS NOT NULL THEN 'time'
            WHEN regexp_full_match(gap_previous_raw, '[0-9]+ Laps?') THEN 'laps'
            ELSE 'unrecognized'
        END AS gap_previous_kind
    FROM converted
)
SELECT
    source_id,
    bronze_sha256,
    car_number,
    car_model,
    overall_position,
    car_class,
    classification_status,
    manufacturer_source_id,
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
    -- Targeted model corrections; never infer a constructor from a partial name.
    CASE
        WHEN car_model = 'Mercedes-AMG GT3' THEN 'Mercedes'
        WHEN car_model = 'Duqueine D08' THEN 'Duqueine'
        ELSE NULL
    END AS manufacturer,
    CASE
        WHEN car_model IN ('Mercedes-AMG GT3', 'Duqueine D08') THEN 'matched_override'
        ELSE NULL
    END AS manufacturer_mapping_status
FROM qualified;

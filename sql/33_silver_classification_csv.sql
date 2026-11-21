-- Normalize classification CSV fields read from Bronze Parquet.

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
    parse_duration_seconds(TOTAL_TIME) AS total_time_seconds,
    NULLIF(TRIM(FL_TIME), '') AS fastest_lap_time_raw,
    parse_duration_seconds(FL_TIME) AS fastest_lap_time_seconds,
    NULLIF(TRIM(GAP_FIRST), '') AS gap_first_raw,
    NULLIF(TRIM(GAP_PREVIOUS), '') AS gap_previous_raw,
    CASE
        WHEN NULLIF(TRIM(GAP_FIRST), '') IS NULL THEN 'missing'
        WHEN TRIM(GAP_FIRST) = '-' THEN 'marker'
        WHEN regexp_full_match(
            TRIM(GAP_FIRST), '[+][0-9]+[.][0-9]+'
        ) THEN 'time'
        WHEN regexp_full_match(
            TRIM(GAP_FIRST), '[0-9]+ Laps?'
        ) THEN 'laps'
        ELSE 'unrecognized'
    END AS gap_first_kind,
    CASE
        WHEN regexp_full_match(TRIM(GAP_FIRST), '[+][0-9]+[.][0-9]+')
        THEN TRY_CAST(TRIM(GAP_FIRST) AS DOUBLE)
        ELSE NULL
    END AS gap_first_seconds,
        CASE
        WHEN regexp_full_match(TRIM(GAP_FIRST), '[0-9]+ Laps?')
        THEN TRY_CAST(split_part(TRIM(GAP_FIRST), ' ', 1) AS INTEGER)
        ELSE NULL
    END AS gap_first_laps,
    CASE
        WHEN NULLIF(TRIM(GAP_PREVIOUS), '') IS NULL THEN 'missing'
        WHEN TRIM(GAP_PREVIOUS) = '-' THEN 'marker'
        WHEN regexp_full_match(
            TRIM(GAP_PREVIOUS), '[+][0-9]+[.][0-9]+'
        ) THEN 'time'
        WHEN regexp_full_match(
            TRIM(GAP_PREVIOUS), '[0-9]+ Laps?'
        ) THEN 'laps'
        ELSE 'unrecognized'
    END AS gap_previous_kind,
    CASE
        WHEN regexp_full_match(TRIM(GAP_PREVIOUS), '[+][0-9]+[.][0-9]+')
        THEN TRY_CAST(TRIM(GAP_PREVIOUS) AS DOUBLE)
        ELSE NULL
    END AS gap_previous_seconds,
    CASE
        WHEN regexp_full_match(TRIM(GAP_PREVIOUS), '[0-9]+ Laps?')
        THEN TRY_CAST(split_part(TRIM(GAP_PREVIOUS), ' ', 1) AS INTEGER)
        ELSE NULL
    END AS gap_previous_laps
FROM bronze_classification_csv;

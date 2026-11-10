WITH extracted_stops AS (
    SELECT
        bronze_document.source_id AS source_id,
        bronze_document.bronze_sha256 AS bronze_sha256,
        car.key AS source_entry_index,
        NULLIF(TRIM(json_extract_string(car.value, '$.number')), '')  AS car_number,
        NULLIF(
            TRIM(json_extract_string(car.value, '$.vehicle')),
            ''
        ) AS car_model,
                NULLIF(
            TRIM(json_extract_string(car.value, '$.manufacturer')),
            ''
        ) AS manufacturer,
        NULLIF(
            TRIM(json_extract_string(car.value, '$.class')),
            ''
        ) AS car_class,
        NULLIF(
            TRIM(json_extract_string(car.value, '$.team')),
            ''
        ) AS team,
        TRY_CAST(
            json_extract_string(stop.value, '$.pit_number')
            AS INTEGER
        ) AS pit_number,
        TRY_CAST(
            json_extract_string(stop.value, '$.in_driver_number')
            AS INTEGER
        ) AS in_driver_number,
        TRY_CAST(
            json_extract_string(stop.value, '$.out_driver_number')
            AS INTEGER
        ) AS out_driver_number,
        json_extract_string(stop.value, '$.pit_time') AS pit_time,
        NULLIF(
            TRIM(json_extract_string(stop.value, '$.in_time')), ''
        ) AS in_time_raw,
        NULLIF(
            TRIM(json_extract_string(stop.value, '$.out_time')), ''
        ) AS out_time_raw,
        NULLIF(
            TRIM(json_extract_string(stop.value, '$.total_pit_time')), ''
        ) AS total_pit_time_raw,
        NULLIF(
            TRIM(json_extract_string(stop.value, '$.in_driver_firstname')), ''
        ) AS reported_in_driver_first_name,
        NULLIF(
            TRIM(json_extract_string(stop.value, '$.in_driver_surname')), ''
        ) AS reported_in_driver_surname,
        NULLIF(
            TRIM(json_extract_string(stop.value, '$.out_driver_firstname')), ''
        ) AS reported_out_driver_first_name,
        NULLIF(
            TRIM(json_extract_string(stop.value, '$.out_driver_surname')), ''
        ) AS reported_out_driver_surname
    FROM bronze_document
    CROSS JOIN json_each(pit_stop_analysis) AS car
    CROSS JOIN json_each(car.value, '$.pit_stops') AS stop
),
parsed_stops AS (
    SELECT
        *,
        TRY_CAST(in_time_raw AS TIME) AS in_time,
        TRY_CAST(out_time_raw AS TIME) AS out_time
    FROM extracted_stops
),
converted_stops AS (
    SELECT
        *,
        parse_duration_seconds(pit_time) AS pit_time_in_seconds,
        parse_duration_seconds(total_pit_time_raw)
            AS total_pit_time_seconds
    FROM parsed_stops
)
SELECT
    source_id,
    car_number,
    car_model,
    manufacturer,
    car_class,
    team,
    pit_number,
    pit_time,
    in_driver_number,
    out_driver_number,
    in_time_raw,
    out_time_raw,
    in_time,
    out_time,
    epoch(in_time) AS in_seconds_since_midnight,
    epoch(out_time) AS out_seconds_since_midnight,
    CASE
        WHEN out_time < in_time THEN
            out_seconds_since_midnight
            - in_seconds_since_midnight
            + 86400
        ELSE
            out_seconds_since_midnight
            - in_seconds_since_midnight
    END AS clock_duration_seconds,
    total_pit_time_raw,
    total_pit_time_seconds,
    reported_in_driver_first_name,
    reported_in_driver_surname,
    reported_out_driver_first_name,
    reported_out_driver_surname,
    source_entry_index,
    bronze_sha256,
    pit_time_in_seconds
FROM converted_stops;

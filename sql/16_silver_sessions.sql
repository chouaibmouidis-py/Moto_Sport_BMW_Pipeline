SELECT
    source_id,
    bronze_sha256,
    NULLIF(TRIM(json_extract_string(session, '$.championship_name')), '')
        AS championship_name,
    NULLIF(TRIM(json_extract_string(session, '$.event_name')), '')
        AS event_name,
    NULLIF(TRIM(json_extract_string(session, '$.session_name')), '')
        AS session_name,
    NULLIF(TRIM(json_extract_string(session, '$.session_type')), '')
        AS session_type,
    NULLIF(TRIM(json_extract_string(session, '$.session_date')), '')
        AS session_date_raw,
    TRY_STRPTIME(
        json_extract_string(session, '$.session_date'),
        '%d/%m/%Y %H:%M'
    ) AS session_datetime,
    CASE
        WHEN session_date_raw IS NULL THEN 'missing'
        WHEN session_datetime IS NULL THEN 'invalid'
        ELSE 'valid'
    END AS session_datetime_status,
    NULLIF(TRIM(json_extract_string(session, '$.creation_date')), '')
        AS creation_date_raw,
    TRY_STRPTIME(
        json_extract_string(session, '$.creation_date'),
        '%d/%m/%Y %H:%M:%S'
    ) AS report_creation_datetime,
    CASE
        WHEN creation_date_raw IS NULL THEN 'missing'
        WHEN report_creation_datetime IS NULL THEN 'invalid'
        ELSE 'valid'
    END AS report_creation_datetime_status,
    NULLIF(TRIM(json_extract_string(session, '$.circuit.name')), '')
        AS circuit_name,
    TRY_CAST(
        json_extract_string(session, '$.circuit.length') AS DOUBLE
    ) AS circuit_length,
    NULLIF(TRIM(json_extract_string(session, '$.circuit.country')), '')
        AS circuit_country,
    NULLIF(TRIM(json_extract_string(session, '$.weather.air_temperature')), '')
        AS air_temperature_raw,
    CASE
        WHEN ends_with(
            TRIM(json_extract_string(session, '$.weather.air_temperature')),
            'ºC'
        )
        THEN TRY_CAST(
            TRIM(
                replace(
                    json_extract_string(session, '$.weather.air_temperature'),
                    'ºC',
                    ''
                )
            ) AS DOUBLE
        )
        ELSE NULL
    END AS air_temperature_celsius,
    CASE
        WHEN air_temperature_raw IS NULL THEN 'missing'
        WHEN air_temperature_celsius IS NULL THEN 'invalid'
        ELSE 'valid'
    END AS air_temperature_status,
    NULLIF(TRIM(json_extract_string(session, '$.weather.track_temperature')), '')
        AS track_temperature_raw,
        CASE
    WHEN ends_with(
        TRIM(json_extract_string(session, '$.weather.track_temperature')),
        'ºC'
    )
    THEN TRY_CAST(
        TRIM(
            replace(
                json_extract_string(session, '$.weather.track_temperature'),
                'ºC',
                ''
            )
        ) AS DOUBLE
    )
        ELSE NULL
    END AS track_temperature_celsius,
    CASE
        WHEN track_temperature_raw IS NULL THEN 'missing'
        WHEN track_temperature_celsius IS NULL THEN 'invalid'
        ELSE 'valid'
    END AS track_temperature_status,
    NULLIF(TRIM(json_extract_string(session, '$.weather.track_status')), '')
        AS track_status,
    NULLIF(TRIM(json_extract_string(session, '$.finalize_type.type')), '')
        AS finalize_type,
    TRY_CAST(
        json_extract_string(session, '$.finalize_type.time_in_seconds')
        AS DOUBLE
    ) AS finalize_time_seconds
FROM bronze_document;
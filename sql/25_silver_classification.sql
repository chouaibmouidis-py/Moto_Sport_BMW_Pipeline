-- Flatten Bronze classification entries and normalize fields while retaining provenance.

SELECT
    source_id,
    bronze_sha256,
    entry.key AS source_entry_index,
    NULLIF(
        TRIM(json_extract_string(entry.value, '$.number')),
        ''
    ) AS car_number,
    NULLIF(
        TRIM(json_extract_string(entry.value, '$.manufacturer')),
        ''
    ) AS manufacturer,
    NULLIF(
        TRIM(json_extract_string(entry.value, '$.vehicle')),
        ''
    ) AS car_model,
    TRY_CAST(
        json_extract_string(entry.value, '$.position')
        AS INTEGER
    ) AS overall_position,
    NULLIF(
        TRIM(json_extract_string(entry.value, '$.class')),
        ''
    ) AS car_class,
    TRY_CAST(
        json_extract_string(entry.value, '$.pit_stops')
        AS INTEGER
        ) AS reported_pit_stop_count,
    TRY_CAST(
        json_extract_string(entry.value, '$.not_finished')
        AS BOOLEAN
        ) AS not_finished
FROM bronze_classification
CROSS JOIN json_each(classification) AS entry;

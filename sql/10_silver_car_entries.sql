SELECT
    bronze_document.source_id,
    bronze_document.bronze_sha256,
    entry.key AS source_entry_index,
    NULLIF(
        TRIM(json_extract_string(entry.value, '$.number')), ''
    ) AS car_number,
    NULLIF(
        TRIM(json_extract_string(entry.value, '$.vehicle')), ''
    ) AS car_model,
    NULLIF(
        TRIM(json_extract_string(entry.value, '$.manufacturer')), ''
    ) AS manufacturer,
    NULLIF(
        TRIM(json_extract_string(entry.value, '$.class')), ''
    ) AS car_class,
    NULLIF(
        TRIM(json_extract_string(entry.value, '$.team')), ''
    ) AS team,
    NULLIF(
        TRIM(json_extract_string(entry.value, '$.group')), ''
    ) AS car_group,
    NULLIF(
        TRIM(json_extract_string(entry.value, '$.tires')), ''
    ) AS tires,
    json_array_length(entry.value, '$.pit_stops') AS pit_stop_count
FROM bronze_document
CROSS JOIN json_each(pit_stop_analysis) AS entry;
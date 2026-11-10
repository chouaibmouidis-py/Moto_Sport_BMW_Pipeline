SELECT
    bronze_document.source_id,
    bronze_document.bronze_sha256,
    car.key AS source_entry_index,
    driver.key AS source_driver_index,
    TRY_CAST(
        json_extract_string(driver.value, '$.number') AS INTEGER
    ) AS driver_number,
    NULLIF(
        TRIM(json_extract_string(driver.value, '$.firstname')), ''
    ) AS first_name,
    NULLIF(
        TRIM(json_extract_string(driver.value, '$.surname')), ''
    ) AS surname,
    NULLIF(
        TRIM(json_extract_string(driver.value, '$.license')), ''
    ) AS license,
    NULLIF(
        TRIM(json_extract_string(driver.value, '$.hometown')), ''
    ) AS hometown,
    NULLIF(
        TRIM(json_extract_string(driver.value, '$.country')), ''
    ) AS country
FROM bronze_document
CROSS JOIN json_each(pit_stop_analysis) AS car
CROSS JOIN json_each(car.value, '$.drivers') AS driver;
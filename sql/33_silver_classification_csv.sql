-- Normalize classification CSV fields read from Bronze Parquet.

SELECT
    source_id,
    bronze_sha256,
    NULLIF(TRIM(NUMBER), '') AS car_number,
    NULLIF(TRIM(VEHICLE), '') AS car_model,
    TRY_CAST(POSITION AS INTEGER) AS overall_position,
    NULLIF(TRIM(CLASS), '') AS car_class,
    NULLIF(TRIM(STATUS), '') AS classification_status
FROM
    bronze_classification_csv;

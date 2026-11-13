-- Count duplicated classification key groups.

WITH duplicate_count AS (
    SELECT
        source_id,
        bronze_sha256,
        source_entry_index
    FROM silver_classification
    GROUP BY source_id, bronze_sha256, source_entry_index
    HAVING COUNT(*) > 1
)

SELECT COUNT(*) AS duplicate_key_count
FROM duplicate_count;

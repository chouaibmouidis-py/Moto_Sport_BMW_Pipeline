-- Report missing and duplicate Silver driver-entry keys.

WITH duplicate_keys AS (
    SELECT
        source_id,
        bronze_sha256,
        source_entry_index,
        source_driver_index
    FROM silver_driver_entries
    GROUP BY
        source_id,
        bronze_sha256,
        source_entry_index,
        source_driver_index
    HAVING COUNT(*) > 1
)
SELECT
    (
        SELECT COUNT(*)
        FROM silver_driver_entries
        WHERE source_id IS NULL
           OR bronze_sha256 IS NULL
           OR source_entry_index IS NULL
           OR source_driver_index IS NULL
    ) AS missing_key_count,
    (
        SELECT COUNT(*)
        FROM duplicate_keys
    ) AS duplicate_key_count;

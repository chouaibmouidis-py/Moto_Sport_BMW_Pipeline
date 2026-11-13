-- Count duplicated Silver car-entry key groups.

WITH duplicate_keys AS (
    SELECT
        source_id,
        source_entry_index
    FROM silver_car_entries
    GROUP BY source_id, source_entry_index
    HAVING COUNT(*) > 1
)
SELECT COUNT(*) AS duplicate_key_count
FROM duplicate_keys;

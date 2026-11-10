WITH duplicate_keys AS (
    SELECT
        source_id,
        car_number,
        pit_number
    FROM silver_pit_stops
    GROUP BY source_id, car_number, pit_number
    HAVING COUNT(*) > 1
)
SELECT COUNT(*) AS duplicate_key_count
FROM duplicate_keys;
-- Count Silver pit stops with missing required key values.

SELECT COUNT(*) AS invalid_key_count
FROM silver_pit_stops
WHERE source_id IS NULL
   OR car_number IS NULL
   OR pit_number IS NULL;

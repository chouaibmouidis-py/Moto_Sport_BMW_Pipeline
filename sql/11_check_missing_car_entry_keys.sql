SELECT COUNT(*) AS missing_key_count
FROM silver_car_entries
WHERE source_id IS NULL
   OR source_entry_index IS NULL;
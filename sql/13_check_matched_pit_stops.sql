-- Count pit stops linked to car entries from the same source and Bronze version.

SELECT COUNT(*) AS matched_pit_stop_count
FROM silver_pit_stops AS stops
JOIN silver_car_entries AS entries
    ON stops.source_id = entries.source_id
   AND stops.bronze_sha256 = entries.bronze_sha256
   AND stops.source_entry_index = entries.source_entry_index;

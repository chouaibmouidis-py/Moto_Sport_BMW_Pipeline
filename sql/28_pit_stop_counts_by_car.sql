-- Count observed pit stops by source, Bronze version and car number.
-- build_pit_stop_counts registers either format's Silver relation as input.

SELECT
    source_id,
    bronze_sha256,
    car_number,
    COUNT(*) AS observed_pit_stop_count
FROM
    pit_stop_count_input
GROUP BY source_id, bronze_sha256, car_number;

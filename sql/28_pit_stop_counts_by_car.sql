-- Count observed pit stops by source, Bronze version and car number.

SELECT
    source_id,
    bronze_sha256,
    car_number,
    COUNT(*) AS observed_pit_stop_count
FROM
    silver_pit_stops
GROUP BY source_id, bronze_sha256, car_number;

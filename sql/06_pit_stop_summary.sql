SELECT
    source_id,
    bronze_sha256,
    car_number,
    COUNT(*) AS total_pit_stops,
    COUNT(pit_time_in_seconds) AS valid_duration_count,
    COUNT(*) - COUNT(pit_time_in_seconds) AS invalid_duration_count,
    ROUND(AVG(pit_time_in_seconds), 3) AS average_pit_time_seconds,
    ROUND(100 * COUNT(pit_time_in_seconds) / COUNT(*), 2) AS duration_coverage_percent
FROM silver_pit_stops
GROUP BY source_id, car_number, bronze_sha256
ORDER BY source_id, car_number, bronze_sha256
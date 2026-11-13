-- Summarize stop counts, duration averages and coverage by source, version and car.

SELECT
    source_id,
    bronze_sha256,
    car_number,
    COUNT(*) AS total_pit_stops,
    COUNT(pit_time_in_seconds) AS valid_duration_count,
    COUNT(*) - COUNT(pit_time_in_seconds) AS invalid_duration_count,
    -- Sum exact milliseconds before dividing: floating sums can cross rounding ties.
    ROUND(
        SUM(CAST(pit_time_in_seconds AS DECIMAL(18, 3)))
        / NULLIF(COUNT(pit_time_in_seconds), 0),
        3
    ) AS average_pit_time_seconds,
    ROUND(100 * COUNT(pit_time_in_seconds) / COUNT(*), 2) AS duration_coverage_percent
FROM silver_pit_stops
GROUP BY source_id, car_number, bronze_sha256
ORDER BY source_id, car_number, bronze_sha256

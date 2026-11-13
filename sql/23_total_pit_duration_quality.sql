-- Count missing and invalid total pit durations by source and Bronze version.

SELECT
    source_id,
    bronze_sha256,
    COUNT(*) AS total_stop_count,
    COUNT(*) FILTER (
        WHERE total_pit_time_raw IS NULL
    ) AS missing_total_duration_count,
    COUNT(*) FILTER (
        WHERE total_pit_time_seconds IS NULL
        AND total_pit_time_raw IS NOT NULL
    )AS invalid_total_duration_count
FROM
    silver_pit_stops
GROUP BY
    source_id, bronze_sha256
ORDER BY
    source_id, bronze_sha256;

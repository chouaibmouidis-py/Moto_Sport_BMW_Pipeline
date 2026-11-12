WITH calculated_totals AS (
    SELECT
        source_id,
        bronze_sha256,
        car_number,
        COUNT(*) AS stop_count,
        COUNT(pit_time_in_seconds) AS converted_duration_count,
        ROUND(SUM(pit_time_in_seconds), 3) AS calculated_total_seconds
    FROM silver_pit_stops
    GROUP BY source_id, bronze_sha256, car_number
),
ranked_stops AS (
    SELECT
        source_id,
        bronze_sha256,
        car_number,
        pit_number,
        total_pit_time_seconds,
        ROW_NUMBER() OVER (
            PARTITION BY source_id, bronze_sha256, car_number
            ORDER BY pit_number DESC
        ) AS stop_rank
    FROM silver_pit_stops
)
SELECT
    totals.*,
    stops.pit_number AS last_pit_number,
    stops.total_pit_time_seconds AS reported_total_seconds,
    CASE
        WHEN totals.converted_duration_count != totals.stop_count
            OR stops.total_pit_time_seconds IS NULL
        THEN 'incomplete'

        WHEN ABS(
            totals.calculated_total_seconds
            - stops.total_pit_time_seconds
        ) > 0.001
        THEN 'mismatch'

        ELSE 'matched'
    END AS comparison_status
FROM calculated_totals AS totals
JOIN ranked_stops AS stops
    ON totals.source_id = stops.source_id
   AND totals.bronze_sha256 = stops.bronze_sha256
   AND totals.car_number = stops.car_number
WHERE stops.stop_rank = 1;

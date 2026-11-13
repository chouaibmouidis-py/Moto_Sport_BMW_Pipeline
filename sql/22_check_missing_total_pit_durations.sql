-- List unconverted total pit durations and distinguish missing from invalid values.

SELECT
    source_id,
    car_number,
    pit_number,
    total_pit_time_raw,
    total_pit_time_seconds,
    CASE
        WHEN total_pit_time_raw IS NULL THEN 'missing'
    ELSE 'invalid'
    END AS dutation_status
FROM
    silver_pit_stops
WHERE total_pit_time_seconds IS NULL;

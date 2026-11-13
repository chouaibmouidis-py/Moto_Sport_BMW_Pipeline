-- Demonstrate duration coverage and averages on synthetic pit-stop data.

WITH converted_stops AS (
    SELECT *
    FROM (VALUES
        ('24', 60.0),
        ('24', NULL),
        ('24', 80.0),
        ('25', NULL),
        ('25', NULL),
        ('96', 50.0),
        ('96', 70.0)
    ) AS t(car_number, pit_time_in_seconds)
)
        SELECT
            car_number,
            COUNT(*) AS total_pit_stops,
            COUNT(pit_time_in_seconds) AS valid_duration_count,
            COUNT(*) - COUNT(pit_time_in_seconds) AS invalid_duration_count,
            ROUND(AVG(pit_time_in_seconds), 3) AS average_pit_time_seconds,
            ROUND(
            100.0 * COUNT(pit_time_in_seconds) / COUNT(*),
            2
            ) AS duration_coverage_percent
        FROM converted_stops
        GROUP BY car_number
        HAVING COUNT(pit_time_in_seconds) < COUNT(*)
        ORDER BY car_number

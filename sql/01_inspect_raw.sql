-- Explore nested Raw pit stops and convert duration components to seconds.

WITH pit_stops AS (
    SELECT
        session.event_name AS event_name,
        session.session_name AS session_name,
        car.number AS car_number,
        car.manufacturer AS manufacturer,
        car.vehicle AS car_model,
        car.class AS car_class,
        car.team AS team,
        stop.pit_number,
        stop.pit_time,
        CASE
            -- Reject invalid minute:second components
            WHEN array_length(string_split(stop.pit_time, ':')) = 2
                AND (
                    TRY_CAST(split_part(stop.pit_time, ':', 1) AS DOUBLE) < 0
                    OR TRY_CAST(split_part(stop.pit_time, ':', 2) AS DOUBLE) < 0
                    OR TRY_CAST(split_part(stop.pit_time, ':', 2) AS DOUBLE) >= 60
                )
            THEN NULL

            -- Reject invalid hour:minute:second components
            WHEN array_length(string_split(stop.pit_time, ':')) = 3
                AND (
                    TRY_CAST(split_part(stop.pit_time, ':', 1) AS DOUBLE) < 0
                    OR TRY_CAST(split_part(stop.pit_time, ':', 2) AS DOUBLE) < 0
                    OR TRY_CAST(split_part(stop.pit_time, ':', 2) AS DOUBLE) >= 60
                    OR TRY_CAST(split_part(stop.pit_time, ':', 3) AS DOUBLE) < 0
                    OR TRY_CAST(split_part(stop.pit_time, ':', 3) AS DOUBLE) >= 60
                )
            THEN NULL

            -- Convert hours:minutes:seconds
            WHEN array_length(string_split(stop.pit_time, ':')) = 3 THEN
                TRY_CAST(split_part(stop.pit_time, ':', 1) AS DOUBLE) * 3600
                + TRY_CAST(split_part(stop.pit_time, ':', 2) AS DOUBLE) * 60
                + TRY_CAST(split_part(stop.pit_time, ':', 3) AS DOUBLE)

            -- Convert minutes:seconds
            WHEN array_length(string_split(stop.pit_time, ':')) = 2 THEN
                TRY_CAST(split_part(stop.pit_time, ':', 1) AS DOUBLE) * 60
                + TRY_CAST(split_part(stop.pit_time, ':', 2) AS DOUBLE)

            -- Convert standalone seconds when non-negative
            WHEN array_length(string_split(stop.pit_time, ':')) = 1 THEN
                CASE
                    WHEN TRY_CAST(stop.pit_time AS DOUBLE) >= 0
                    THEN TRY_CAST(stop.pit_time AS DOUBLE)
                    ELSE NULL
                END

            ELSE NULL
        END AS pit_time_in_seconds
    FROM raw_document
    CROSS JOIN UNNEST(pit_stop_analysis) AS entries(car)
    CROSS JOIN UNNEST(car.pit_stops) AS stops(stop)
)
SELECT
    event_name,
    session_name,
    car_number,
    manufacturer,
    car_model,
    car_class,
    team,
    pit_number,
    pit_time,
    pit_time_in_seconds
FROM pit_stops
ORDER BY car_number, pit_number;

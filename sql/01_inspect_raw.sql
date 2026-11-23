-- Inspect Raw pit stops using the shared duration parser.

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
        parse_duration_seconds(stop.pit_time) AS pit_time_in_seconds
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

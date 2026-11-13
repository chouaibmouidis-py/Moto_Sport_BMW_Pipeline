-- Profile car attributes and nested driver and pit-stop counts in raw_document.

SELECT
    car.number AS car_number,
    car.vehicle AS car_model,
    car.manufacturer,
    car.class AS car_class,
    car.team,
    car."group" AS car_group,
    car.tires,
    array_length(car.drivers) AS driver_entry_count,
    array_length(car.pit_stops) AS pit_stop_count
FROM raw_document
CROSS JOIN UNNEST(pit_stop_analysis) AS entries(car)
ORDER BY car_number;

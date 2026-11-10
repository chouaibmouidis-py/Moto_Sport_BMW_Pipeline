def count_manufacturer_pit_stops(cars, manufacturer):
    count = 0
    for car in cars:
        if car["manufacturer"] == manufacturer:
            count += len(car["pit_stops"])
    return count

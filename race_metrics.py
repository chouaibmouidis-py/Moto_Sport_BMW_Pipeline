"""Compute source-level manufacturer pit-stop counts without mutating input data."""
def count_manufacturer_pit_stops(cars, manufacturer):
    count = 0
    for car in cars:
        if car["manufacturer"] == manufacturer:
            count += len(car["pit_stops"])
    return count

"""Verify pit-stop counting for a requested manufacturer."""

from race_metrics import count_manufacturer_pit_stops


def test_counts_only_requested_manufacturer():
    cars = [
        {"manufacturer": "BMW", "pit_stops": [{}, {}, {}]},
        {"manufacturer": "BMW", "pit_stops": [{}, {}]},
        {"manufacturer": "Cadillac", "pit_stops": [{}, {}, {}, {}]},
    ]

    result = count_manufacturer_pit_stops(cars, "BMW")

    assert result == 5


def test_returns_zero_when_manufacturer_is_absent():
    cars = [{"manufacturer": "Cadillac", "pit_stops": [{}, {}]}]

    result = count_manufacturer_pit_stops(cars, "BMW")

    assert result == 0


def test_returns_zero_for_empty_list():
    cars = []

    result = count_manufacturer_pit_stops(cars, "BMW")

    assert result == 0

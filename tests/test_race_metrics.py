"""Verify pit-stop counting for a requested manufacturer."""

import unittest

from race_metrics import count_manufacturer_pit_stops


class RaceMetricsTests(unittest.TestCase):
    def test_counts_only_requested_manufacturer(self):
        cars = [
            {"manufacturer": "BMW", "pit_stops": [{}, {}, {}]},
            {"manufacturer": "BMW", "pit_stops": [{}, {}]},
            {"manufacturer": "Cadillac", "pit_stops": [{}, {}, {}, {}]},
        ]

        result = count_manufacturer_pit_stops(cars, "BMW")

        self.assertEqual(result, 5)

    def test_returns_zero_when_manufacturer_is_absent(self):
        cars = [
            {"manufacturer": "Cadillac", "pit_stops": [{}, {}]}
            ]

        result = count_manufacturer_pit_stops(cars, "BMW")

        self.assertEqual(result, 0)

    def test_returns_zero_for_empty_list(self):
        cars = []

        result = count_manufacturer_pit_stops(cars, "BMW")

        self.assertEqual(result, 0)

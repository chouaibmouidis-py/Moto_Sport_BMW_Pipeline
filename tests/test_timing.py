import pytest

from moto_sport_bmw_pipeline import timing
from moto_sport_bmw_pipeline.timing import measure_duration


def test_returns_result_and_elapsed_seconds(monkeypatch):

    calls = []

    def add(left, *, right):
        calls.append((left, right))
        return left + right

    ticks = iter([10.0, 10.25])
    monkeypatch.setattr(timing.time, "perf_counter", lambda: next(ticks))

    result, elapsed_seconds = measure_duration(add, 2, right=3)

    assert result == 5
    assert elapsed_seconds == 0.25
    assert calls == [(2, 3)]


def test_preserves_operation_exception():

    original_error = ValueError("Simulated operation failure")

    def fail():
        raise original_error

    with pytest.raises(ValueError) as caught:
        measure_duration(fail)

    assert caught.value is original_error

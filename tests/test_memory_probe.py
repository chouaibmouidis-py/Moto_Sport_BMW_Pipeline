from memory_probe import measure_python_memory
import pytest
import tracemalloc


def test_measures_allocated_buffer():

    size_bytes = 1024 * 1024

    def allocate_buffer(size_bytes):
        return bytearray(size_bytes)

    measurement = measure_python_memory(allocate_buffer, size_bytes)

    assert len(measurement["result"]) == size_bytes
    assert measurement["peak_bytes"] >= size_bytes


def test_stops_tracing_when_function_fails():

    def failing_operation():
        raise ValueError("Simulated processing failure")

    with pytest.raises(ValueError, match="Simulated processing failure"):
        measure_python_memory(failing_operation)

    assert not tracemalloc.is_tracing()


def test_preserves_existing_tracing_session():
    calls = []

    def operation():
        calls.append("executed")

    tracemalloc.start()
    try:
        with pytest.raises(
            RuntimeError,
            match="Memory tracing is already active",
        ):
            measure_python_memory(operation)

        assert tracemalloc.is_tracing()
        assert calls == []
    finally:
        tracemalloc.stop()


def test_forwards_arguments_and_calls_function_once():

    calls = []

    def calculate_total(left, right, *, multiplier):
        calls.append((left, right, multiplier))
        return (left + right) * multiplier

    measurement = measure_python_memory(
        calculate_total,
        2,
        3,
        multiplier=4,
    )

    assert measurement["result"] == 20
    assert calls == [(2, 3, 4)]

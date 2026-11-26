"""Measure allocations made by one callback without taking over another tracing session."""

import tracemalloc


def measure_python_memory(function, *args, **kwargs):
    """Return the callback result and traced Python peak; native memory is excluded."""
    if tracemalloc.is_tracing():
        raise RuntimeError("Memory tracing is already active")

    tracemalloc.start()

    try:
        result = function(*args, **kwargs)
        _, peak_bytes = tracemalloc.get_traced_memory()
    finally:
        tracemalloc.stop()

    return {"result": result, "peak_bytes": peak_bytes}

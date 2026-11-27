import time


def measure_duration(operation, *args, **kwargs):

    started_at = time.perf_counter()

    result = operation(*args, **kwargs)

    elapsed_seconds = time.perf_counter() - started_at

    return result, elapsed_seconds

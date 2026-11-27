from vortex_support import VORTEX_EXTENSION_DIRECTORY

from experiments.storage_formats.benchmark import run_benchmark


def test_benchmark_alternates_order_and_checks_contents(tmp_path):
    report = run_benchmark(
        rows=20,
        pairs=2,
        directory=tmp_path,
        extension_directory=str(VORTEX_EXTENSION_DIRECTORY),
    )
    assert [record["format"] for record in report["measurements"]] == [
        "parquet",
        "vortex",
        "vortex",
        "parquet",
    ]
    assert all(record["rows"] == 20 for record in report["measurements"])
    assert all(record["content_verified"] for record in report["measurements"])
    assert all(record["write_seconds"] >= 0 for record in report["measurements"])
    assert all(record["scan_seconds"] >= 0 for record in report["measurements"])
    assert all(record["size_bytes"] > 0 for record in report["measurements"])
    assert len(report["summary"]) == 2

# Local experiments

The optional storage tests run with
`uv run --locked --no-sync python -m pytest experiments/storage_formats/tests -v`.
See the [local test setup](../docs/ci.fr.md#local-test-setup) for the Vortex installation.

These tools explore implementation choices without changing the production
pipeline. Their findings apply to the recorded workloads and environments.

## Storage formats

[storage_formats/benchmark.py](storage_formats/benchmark.py) compares Parquet and
Vortex using a flat synthetic table, alternating write order, exact content and
schema checks, consumed queries, and median timings. Temporary data files are
removed; a JSON report retains the measurements.

See the [study, limitations and reproduction commands](../docs/parquet_vortex_benchmark.md).
Run it from the repository root with
`uv run --locked --no-sync python -m experiments.storage_formats.benchmark` plus
the arguments documented there. Vortex must already be installed for the selected
DuckDB version and extension directory. The experiment does not install extensions
automatically and is not invoked by the pipeline.

[storage_formats/qualify_real_bronze.py](storage_formats/qualify_real_bronze.py)
qualifies all enabled local reports in temporary files, verifies source preservation
and Silver input loading, and measures repeated publication and scans. See the
[real-data results](../docs/real_bronze_vortex_qualification.md): the current Bronze
layout produced larger Vortex files, unlike the large flat synthetic example.

[storage_formats/benchmark_pdf_blob.py](storage_formats/benchmark_pdf_blob.py)
stores an entire PDF in one BLOB column. The [123 MB real-PDF experiment](../docs/large_pdf_blob_experiment.md)
found a 0.27% size difference, not the extracted Bronze's 3.65× ratio. It is a
separate workload from parsing a report into rows.

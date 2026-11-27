# Large PDF stored as a single BLOB

27 November 2026 — local storage experiment; no production change.

The maintainer requested a real PDF around 100 MB to check whether the earlier
Bronze size ratio also appeared on a large document. The downloaded source is the
[Indonesian Geoparks report, Langkawi 2026](https://indonesiangeoparks.org/wp-content/uploads/2026/10/Indonesia-Geoparks-Report-Langkawi-2026.pdf),
linked from the [publisher's publications page](https://indonesiangeoparks.org/publications/).
It contains 54 pages and **123,008,176 bytes**. It is not a generated padding file.

## Results

| Representation | Bytes | Decimal MB |
| --- | ---: | ---: |
| Original PDF | 123,008,176 | 123.008176 |
| One BLOB row in Parquet | 122,682,786 | 122.682786 |
| One BLOB row in Vortex | 123,010,688 | 123.010688 |

**Vortex is 327,902 bytes larger than Parquet, a difference of 0.2673%.** The
3.65× ratio from the real Bronze qualification does not occur in this scenario.
Neither default writer substantially reduces the original PDF's size here.

The four write observations per format have medians of 0.4123 seconds for Parquet
and 0.8336 seconds for Vortex. These are warmed COPY timings, not pipeline times.
All eight readbacks preserved BLOB type, row count, byte length, SHA-256, and exact
SQL byte equality with the input. The source hash was unchanged afterwards:

```text
e980cb4ed51713516041d4e5d03917f3d746f73affcf034b019388a825ee14e9
```

Raw observations: [JSON report](benchmarks/large-pdf-blob-2026-11-27.json).

## What this establishes

Three distinct workloads now have recorded outcomes:

- A large flat synthetic table: Vortex used 47.78% less space at one million rows.
- The 68 small extracted Bronze tables: Vortex used 3.65× the Parquet space.
- This 123 MB PDF stored as one BLOB: Vortex used 0.27% more space than Parquet.

These observations do not establish a universal size multiplier or a universal
winning format. File size, value distribution, physical representation and writer
settings all matter. This experiment changes the representation as well as the
input: it does not isolate file size as the sole cause of the different ratio.

The pipeline extracts stop rows from supported IMSA PDFs. Here, the complete PDF
is stored in a single binary cell: no stop extraction or Silver processing occurs.
The production decision remains Parquet for the current Bronze layout. This BLOB
experiment does not overturn the measured sizes of those extracted tables.

## Protocol and reproduction

Tool: [benchmark_pdf_blob.py](../experiments/storage_formats/benchmark_pdf_blob.py).
DuckDB 1.5.4; Vortex revision 275ac23; macOS 13.7.8 Intel; two threads; 2 GB DuckDB
memory setting. No RSS measurement or process-memory bound is claimed.

The PDF is loaded once into a native DuckDB BLOB table, outside timing. Both
writers are initialized; four paired rounds alternate P/V and V/P. Default writer
settings are used. Each readback is verified outside COPY timing. OS caches are
uncontrolled; no other test suite was run during the benchmark. Temporary output
files are deleted; the source PDF is not vendored in the repository.

```bash
uv run --locked --no-sync python -m experiments.storage_formats.benchmark_pdf_blob \
  /path/to/report.pdf \
  --extension-directory /path/to/duckdb/extensions \
  --pairs 4 \
  --report /tmp/pdf-blob-report.json
```

Vortex must already be installed in the indicated directory. Use the publisher's
link to obtain the original file; its rights remain with its publisher.

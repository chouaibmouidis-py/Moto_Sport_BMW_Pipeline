# Parquet and Vortex: exploratory local storage comparison

Measured on 27 November 2026. Status: local synthetic experiment, not deployed.
The subsequent [real Bronze qualification](real_bronze_vortex_qualification.md)
found larger Vortex outputs for the current report layout. Read both studies
before applying this synthetic result to the pipeline.

## Finding

For the one-million-row synthetic table, Vortex produced a 2,391,956-byte file
against 4,580,728 bytes for Parquet: **47.78% less storage** for this dataset and
these writer settings. Median write and read times did not show a Vortex speed
advantage at that scale. Storage is a useful optimization dimension in its own
right; no monetary saving has been measured or extrapolated to the hosted project.

At 100,000 rows the sizes were almost equal, with Vortex slightly larger. The
one-million-row result must therefore not be applied as a fixed compression ratio
to every source or volume.

## Protocol

- DuckDB 1.5.4, macOS 13.7.8, Intel x86_64; both formats on the same machine.
- Two DuckDB threads and a 512 MB engine memory setting. This setting is not a
  measured or guaranteed bound on total process RAM.
- One flat synthetic table, prepared outside timing: BIGINT entry ID, VARCHAR
  car number retaining leading zeros, nullable DOUBLE speed, and nullable VARCHAR
  team label retaining spaces. It is not actual race data or nested Bronze JSON.
- Default writer compression settings; Parquet compression variants were not tuned.
- Both writers initialized once before recording. Six paired rounds per volume,
  alternating Parquet/Vortex and Vortex/Parquet: six observations per format.
- Writing times cover COPY. Files are closed but no explicit fsync durability
  barrier is requested by the benchmark.
- Each output's column names and types are compared with the source. EXCEPT ALL
  in both directions verifies exact row-multiset equality, including duplicates
  and NULLs. Validation is outside timing.
- The scan computes sum(hash(entry_id, car_number, speed, team_raw)); it consumes
  all column values and includes hashing CPU cost. This fingerprint is used to
  force execution, not as the proof of data equality.
- The filtered query computes sum(speed) WHERE entry_id % 100 = 0. It measures
  that specific predicate and projection, not every form of selective access.
- Reads follow writing and validation, using the same connection. OS caches are
  uncontrolled: these are repeated/warm workload observations, not cold reads.
- Each generated file is deleted after its measurements. Small JSON reports
  retain individual observations, configuration and medians.

## Results

Times below are medians, in milliseconds; file sizes are exact bytes.

| Rows | Metric | Parquet | Vortex |
| ---: | --- | ---: | ---: |
| 100,000 | Write | 35.126 | 97.920 |
| 100,000 | All-column scan plus hash | 6.176 | 4.893 |
| 100,000 | Filter plus sum | 2.306 | 2.171 |
| 100,000 | File size (bytes) | 450,850 | 451,844 |
| 1,000,000 | Write | 260.072 | 283.901 |
| 1,000,000 | All-column scan plus hash | 49.924 | 50.682 |
| 1,000,000 | Filter plus sum | 7.920 | 8.269 |
| 1,000,000 | File size (bytes) | 4,580,728 | 2,391,956 |

Storage reduction at one million rows:

```text
(4,580,728 - 2,391,956) / 4,580,728 × 100 ≈ 47.78%
```

Raw observations: [100k report](benchmarks/parquet-vortex-100k-2026-11-27.json)
and [1M report](benchmarks/parquet-vortex-1m-2026-11-27.json).

## Limits and next experiments

This is an exploratory run, not an isolated performance qualification. Other
machine activity was not controlled; targeted pytest checks also ran at the start
of the one-million-row experiment. The available reports do not capture CPU model,
Vortex extension build identifier, process RSS, peak memory, spill volume or I/O
traffic. Small timing differences cannot establish a general ranking.

Next steps are isolated repetitions, explicit extension-version recording,
Parquet compression variants, real classification CSV data, nested JSON Bronze
documents, and end-to-end extraction/validation measurements. Total-process memory
requires a separate measurement. Downstream readers and publication must also be
qualified before changing the pipeline's storage contract.

## Reproduce

From the repository root, synchronize the locked environment. Install the official
Vortex extension once into the same directory used by the experiment; installation
requires network access. Tests and the benchmark only LOAD it.

```bash
uv sync --locked
uv run --locked --no-sync python -c 'import duckdb; c = duckdb.connect(config={"extension_directory": "/private/tmp/bmw-vortex-extensions"}); c.execute("INSTALL vortex"); c.close()'
uv run --locked --no-sync python -m pytest tests/test_timing.py experiments/storage_formats/tests -v
uv run --locked --no-sync python -m experiments.storage_formats.benchmark --rows 100000 --pairs 6 --report /private/tmp/storage-100k.json
uv run --locked --no-sync python -m experiments.storage_formats.benchmark --rows 1000000 --pairs 6 --report /private/tmp/storage-1m.json
```

The extension path is a local laboratory default, not a pipeline configuration.
Use --extension-directory to select another installation for the benchmark.
The report destination's parent directory must already exist. The synthetic
benchmark does not read credentials or change Raw, Bronze, Silver or Gold files.

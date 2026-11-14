# Shared IMSA Gold layer, 2023–2025

The `race_car_summary.parquet` table contains one versioned participation per
row, with 29 explicit columns defined by SQL 39. Sources are stacked using
UNION ALL, without silent deduplication. Missing or repeated keys
(`source_id`, `bronze_sha256`, `car_number`) block the result.

```bash
uv run python build_gold.py
```

This command reads the referenced JSON run once at startup and the eleven
existing 2023 CSV/PDF marts. It does not rebuild the seasons. The builder is in
`src/moto_sport_bmw_pipeline/gold.py`; the launcher only configures logging and
calls that builder.

## Independent publication

```text
data/gold/current.json
data/gold/runs/<run_id>/
    race_car_summary.parquet
    manufacturer_reference.parquet
    manufacturer_evidence.parquet
    inputs.json
    inputs/...
```

Each candidate copies both configurations, the four SQL files 36–39, the JSON
Bronze files used as evidence and the input marts. Calculations use these copies.
`inputs.json` records their role, original path, copy path and SHA-256,
as well as the JSON run used. Copy hashes are checked before calculations and
again before activation. The three Parquet files are published with read-back
and content comparison, then the Gold reference is replaced only if all required
files are present. A failure leaves the candidate on disk and retains the old
Gold reference. `data/current.json` remains untouched.

The copies freeze the bytes read but do not prove that the exploratory 2023
marts were published together: their per-race publication remains independent.
The Python environment and implementations are not archived by this mechanism;
repository dependencies remain described by pyproject.toml/uv.lock.
Exact reproduction after code changes also requires preserving the code revision
and environment. No concurrent deployment or hardware crash has been validated.

## Meaning of missing fields and manufacturers

Information absent from input marts is represented by typed NULLs. The 2023
textual classification status is not converted into the not_finished boolean;
missing reported counts are never calculated from observed stops.

When populated, the JSON manufacturer is supplied directly: origin `source`;
a missing or blank name has origin `unresolved`. Reference resolution is
`not_applicable` for this branch. For 2023, the provider identifier is joined to names
explicitly associated with it in local JSON Bronze data: origin `reference` if
the name is unique, otherwise `unresolved`. Ambiguous values are not normalized
automatically. Evidence retains source_id and bronze_sha256.
This mapping reuses reports from later seasons; it is a documented analytical
resolution, not evidence known in real time in 2023.
Do not use it without assessment as historical information available before a
race or as a prediction variable free of temporal leakage risk.

## Checks for the first publication

187 tests passed, including checks for schema, alignment, keys, copying,
independent activation, publication failure and rebuilding from copies after
deleting the mock originals.

Expected reference counts for the validated inputs: 1 392 participations,
including 137 BMW: 455/51 in 2023, 468/38 in 2024 and 469/48 in 2025.
The 55 unresolved 2023 manufacturers remain explicitly flagged. The current
Gold layer covers participations; it is not yet a shared table of all detailed
stops. The checks do not establish completeness across all PDFs.

To view the result, open `data/gold/current.json`, then the Parquet file from
the indicated run in the VS Code DuckDB extension. Do not use a glob across all
run directories: it would stack the different publications.

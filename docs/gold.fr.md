> Historical qualification results below describe the validated datasets. For the current runtime, use the [code map](code_map.md): one source manifest and one multiformat orchestrator. Old per-season output paths are not current production inputs.

# Shared IMSA Gold layer

The `race_car_summary.parquet` table contains one versioned participation per
row, with 45 explicit columns in the active local schema defined by SQL 39.
The remote history schema was migrated additively on 23 November 2026, while
preserving the previous active publication and its public column projection.
The locally activated run includes Daytona 2022: 61 participants (3 BMW) and
1,762 stops. Combined local Gold contains 1,453 participants, including 140 BMW.
The 2023–2025 participant records were compared in both directions with EXCEPT ALL
against the previous active Gold, excluding the three intentionally corrected
manufacturer fields; no other differences were found in their shared columns.
The pinned archive was subsequently renewed to 114 files and restored for verification.
The hosted participant dataset still awaits publication of the new Gold run.
Sources are stacked using
UNION ALL, without silent deduplication. Missing or repeated keys
(`source_id`, `bronze_sha256`, `car_number`) block the result.

```bash
uv run python build_gold.py
```

This command reads the active complete processing run and its declared JSON and
CSV/PDF outputs. It does not rebuild the seasons. The builder is in
`src/moto_sport_bmw_pipeline/gold.py`; the launcher only configures logging and
calls that builder.

## Independent publication

Source-archive renewal and history-schema migration are explicit maintenance
operations, separate from the recurring publication workflow:

```bash
uv run --locked --no-sync python archive_sources.py --pin
uv run --locked --no-sync python migrate_motherduck_schema.py
uv run --locked --no-sync python migrate_motherduck_schema.py --apply
```

Archival pins `config/source_archive.json` only after its remote transaction and
read-back checks succeed. The migration defaults to inspection; `--apply` adds
only the 16 known sporting columns and rejects incompatible existing types or
unexpected missing fields. Historical values, the active run and the existing
public view projection are checked and preserved transactionally. The next normal
publication exposes the expanded schema together with its new run. Publication
compares stored rows in candidate column order because EXCEPT ALL is positional,
whereas INSERT BY NAME and ALTER TABLE may leave a different physical order.

```text
data/gold/current.json
data/gold/runs/<run_id>/
    race_car_summary.parquet
    manufacturer_reference.parquet
    manufacturer_evidence.parquet
    inputs.json
    inputs/...
```

Each candidate copies the processing source manifest and output descriptor, the
four SQL files 36–39, the JSON Silver classification and car-entry files used as
manufacturer evidence, and the input marts. Gold does not reload Bronze for
manufacturer normalization. Calculations use these copies.
`inputs.json` records their role, original path, copy path and SHA-256,
as well as the processing run used. Copy hashes are checked before calculations and
again before activation. The three Parquet files are published with read-back
and content comparison, then the Gold reference is replaced only if all required
files are present. A failure leaves the candidate on disk and retains the old
Gold reference. `data/current.json` remains untouched.

The production builder consumes the complete processing run selected by
`data/processing/current.json`. Standalone diagnostic batches do not provide
that complete-run activation guarantee.
The Python environment and implementations are not archived by this mechanism;
repository dependencies remain described by pyproject.toml/uv.lock.
Exact reproduction after code changes also requires preserving the code revision
and environment. No concurrent deployment or hardware crash has been validated.

## Sporting fields preserved from Silver

Both report adapters normalize team, completed laps, fastest-lap number and
speed, total elapsed time, fastest-lap time and gaps. Gold carries these values
without recalculating them. Textual durations accompany their values in seconds.

`gap_first_raw` and `gap_previous_raw` retain the trimmed source text. Each gap
also has a kind (`missing`, `marker`, `time`, `laps` or `unrecognized`), a seconds
column and a laps column. Time gaps require a leading `+`; the shared duration
parser supports seconds, minutes/seconds and hours/minutes/seconds. Lap gaps
remain integers and are never converted to seconds. Missing, marker and unknown
values do not become zero. Unrecognized text remains visible in Gold.

## Meaning of missing fields and manufacturers

Information absent from input marts is represented by typed NULLs. The CSV/PDF
textual classification status is not converted into the not_finished boolean;
missing reported counts are never calculated from observed stops.

When populated, the JSON manufacturer is supplied directly: origin `source`;
a missing or blank name has origin `unresolved`. Reference resolution is
`not_applicable` for this branch. For CSV/PDF, the provider identifier is joined to names
explicitly associated with it in JSON Silver data: origin `reference` if
the name is unique, otherwise `unresolved`. Ambiguous values are not normalized
automatically. Evidence retains source_id and bronze_sha256.

Two exact normalized model names have targeted corrections in CSV Silver:
`Mercedes-AMG GT3` maps to `Mercedes` and `Duqueine D08` to `Duqueine`.
These corrections retain the source constructor ID and model, leave Raw/Bronze
unchanged, and set `manufacturer_mapping_status=matched_override`. Gold carries
the Silver correction ahead of the reference lookup and marks its origin as
`silver_override`. No partial-name matching or inference for unknown models is used.
The reference itself and its name count remain unchanged: the name count measures
reference evidence, not the validity of the model correction.
This mapping reuses reports from later seasons; it is a documented analytical
resolution, not evidence known in real time in 2023.
Do not use it without assessment as historical information available before a
race or as a prediction variable free of temporal leakage risk.

## Historical checks for the first 2023–2025 publication

The figures below describe that first publication, not the current 222-test
baseline or the later manufacturer corrections. Current local coverage and
remote preparation status are recorded at the start of this document.

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

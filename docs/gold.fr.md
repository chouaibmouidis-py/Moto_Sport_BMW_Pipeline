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
The maintainer subsequently confirmed the Daytona 2022 extension on the hosted
dashboard. The later case-handling and rollback-diagnostic fixes remain a separate
maintenance delivery; local tests alone do not establish their remote deployment.
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

If an operation fails, publication, schema migration and source archival attempt
ROLLBACK. If that attempt also fails, its exception is logged separately and the
original operation exception is re-raised. A failed rollback is not confirmation
that the remote transaction was undone. After connection loss, particularly around
COMMIT, verify the remote history, active reference or archive inventory after
reconnection before deciding how to recover. Regression tests simulate the double
failure locally; they do not simulate an actual MotherDuck network outage.

### Migration memory limit and planned optimization

The current schema migration fetches historical rows and the public view into
Python before and after the change, then compares row multiplicities with Counter.
It checks content rather than counts alone, but retains complete result sets and
Python counting structures. Memory usage grows with row count and width, and
remote reads transfer the compared data to the client. The successful migration
on the qualified dataset is not a large-history memory or performance benchmark.
A larger history can exhaust client memory; an exception handler does not provide
recovery from process termination or an operating-system kill.

The planned optimization moves the exact comparison into the database engine:
capture the previous column projection, compare before/after with EXCEPT ALL in
both directions, and return only difference counts to Python. Engine placement,
temporary storage, memory limits, transfer volume and runtime costs must be measured
for the actual DuckDB/MotherDuck execution environment. This is not implemented.

COUNT alone does not establish unchanged content. COUNT plus an aggregated hash
is a compact fingerprint, not an exact multiset equality check; XOR also cancels
pairs of identical row hashes. These alternatives must not silently replace the
existing preservation contract. The new implementation must start with regression
tests for changed content at equal counts, duplicate multiplicities, NULL values,
row order, and rollback, followed by a representative memory/cost benchmark.

<a id="archive-repeated-reads-and-planned-single-read-validation"></a>
### Single-read archival and remaining memory limit

The archiver now reads each source once, validates its expected SHA-256 and keeps
those same bytes for size calculation, hashing and archival. Manifest-backed
sources provide the expected hash directly; metadata-backed sources obtain it
from metadata.json. Metadata bytes are read once and retained unchanged for the
archive as well. The former second preparation/read loop has been removed.

Local tests verify both source-hash paths, a single source read, a single metadata
read, exact metadata content/size/hash in the local archive, rejection of incorrect
expected hashes and preservation of the previous pin after validation failure.
The existing saved-content corruption scenario still rejects publication and
preserves the prior pin. These checks run against temporary files/local DuckDB,
not against the live MotherDuck archive. No production performance or cost gain
has been measured; this code change has not been deployed to the remote workflow.

All prepared file payloads still accumulate in source_files before the database
connection opens. Single reading removes redundant I/O and keeps validation tied
to the submitted bytes; it does not bound cumulative payload memory. File-by-file
processing is the next separate milestone.

The related bounded-memory archive milestone processes one file at a time inside
the archive transaction: read and validate, insert, verify the saved bytes, then
release the content before handling the next file. Only lightweight inventory
records are retained across files. The full inventory is verified before COMMIT;
the local pin changes afterward. This bounds accumulated Python file payloads by
the largest file in flight rather than their total size; it does not cap total
process memory or remove DuckDB/driver buffers. Chunked handling of an individually
oversized BLOB requires separate interface validation. Tests must check incremental
processing and preservation of the previous pin on a later-file failure, with a
representative peak-memory measurement. The current dataset has not established
a measured universal 1 GB memory bound. This is preventive planned work, not an
implemented streaming guarantee.

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
Lap-label recognition ignores letter case while retaining raw text. The
[case contract](data_case_contract.md) also covers model corrections, manufacturer
reference ambiguity and session temperature validation.

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

The figures below describe that first publication, not the current pytest
baseline (302 tests and 97 subtests passing) or the later manufacturer corrections. Current local coverage and
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

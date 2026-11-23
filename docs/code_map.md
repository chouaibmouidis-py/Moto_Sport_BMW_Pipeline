# Runtime code map

The production pipeline is organized by responsibility, not by season or file format.

| Responsibility | Owner |
| --- | --- |
| Source inventory, activation and expected raw fingerprints | `config/sources.json` |
| Selection, identifier validation and report pairing | `src/moto_sport_bmw_pipeline/manifest.py` |
| Download, cached-source verification and format validation | `src/moto_sport_bmw_pipeline/raw_download.py` |
| Raw extraction and Bronze construction | `src/moto_sport_bmw_pipeline/bronze.py` |
| PDF layout interpretation | `src/moto_sport_bmw_pipeline/pdf_parser.py` |
| Bronze loading and session context | `src/moto_sport_bmw_pipeline/source_loading.py` |
| Normalization | `src/moto_sport_bmw_pipeline/silver.py` and `sql/` |
| Blocking invariants and nonblocking quality reports | `src/moto_sport_bmw_pipeline/quality.py` |
| Participant summaries and manufacturer resolution | `src/moto_sport_bmw_pipeline/marts.py` |
| Candidate processing run construction | `src/moto_sport_bmw_pipeline/pipeline.py` |
| Verified Parquet writing and run activation | `parquet_writer.py`, `publication.py`, `run_reference.py` in the package |
| Gold input snapshots, verification and activation | `src/moto_sport_bmw_pipeline/gold.py` |
| Stage ordering and CLI arguments | `src/moto_sport_bmw_pipeline/orchestration.py` |
| Scheduling the shared stages | `dags/bmw_pipeline.py` |
| Source archival and verified local pin | `archive_sources.py --pin` |
| Additive MotherDuck history migration | `migrate_motherduck_schema.py` |
| Transactional remote data publication | `publish_motherduck.py` |
| Separate share provisioning | `configure_motherduck_share.py` |

## Shared execution

```text
run_pipeline.py → orchestration.main()
  config/sources.json → select_documents() → pair_reports()
  raw     → prepare_source() → format validator
  bronze  → build_source()   → document-role / format reader
  process → build_processing_run()
              JSON normalization adapter
              CSV classification / PDF stops adapters
              shared key, link and provenance checks
              classification quality report and participant marts
              activate complete processing run
  gold    → snapshot processing inputs → align participant schema
              verify outputs → activate Gold
```

Format-specific functions remain necessary to interpret different source
structures. They live in their responsibility modules and do not define separate
production CLIs or configuration files. The supported report pairings currently
are JSON classification + JSON stops, and CSV classification + PDF stops.
Unknown formats and unsupported pairings fail before acquisition. Supporting a
new pairing still requires an adapter and tests; it is not automatic.

```bash
uv run python run_pipeline.py
uv run python run_pipeline.py --season 2023 --event daytona
uv run python run_pipeline.py --stage bronze
```

Available stages: `raw`, `bronze`, `process`, `gold`, `all` (default).
The same CLI is used by `python -m moto_sport_bmw_pipeline` and Airflow.
Selection applies to enabled sources only. A focused selection replaces local
Gold coverage with that selection after success; it does not append to a run.
The Gold stage rejects a selection different from the active processing run.

## Versioned outputs

```text
data/raw/<source_id>/                         Cached source + metadata, if applicable
data/bronze/<source_id>/document.parquet       Format-specific extraction
data/runs/<uuid>/                            JSON adapter candidate outputs
data/processing/runs/<uuid>/
  sources.json                               Exact selected manifest documents
  outputs.json                               Marts, quality reports and fingerprints
  reports/<classification_source_id>/
    silver/classification.parquet
    silver/pit_stops.parquet
    quality/classification_gap_issues.parquet
    marts/race_car_summary.parquet
data/processing/current.json                 Complete processing reference
data/gold/runs/<uuid>/                        Snapshotted inputs + Gold outputs
data/gold/current.json                        Complete Gold reference
```

The shared path does not activate the legacy JSON `data/current.json` reference.
Gold uses only one completed processing run. Failed candidate directories may
remain for diagnosis; they are not selected by the active reference. Cleanup and
retention policies remain a separate operational concern.

Each Parquet is reread and compared before replacement. Processing activation
occurs only after all reports succeed, so classification and quality files in a
failed candidate cannot become active independently. Gold freezes outputs and
verifies their recorded hashes before building. A Gold failure preserves the
previous Gold reference. These filesystem references are not database transactions.

## Diagnostics and compatibility

`inspect_source.py`, `inspect_json_sql.py`, `inspect_classification_csv.py`,
`inspect_pdf_pair.py`, `inspect_marts.py` and `inspect_quality.py` are independent
inspection commands. `pair_diagnostics.py` can save an explicitly requested
diagnostic snapshot; it is never called by the production DAG.

Historical individual JSON launchers and batch helper APIs remain available for
focused operations and existing tests. Production no longer orchestrates those
scripts. Business transforms and Bronze builders are imported from the package.

`archive_sources.py` inventories enabled sources from the same manifest. JSON
metadata and pinned raw fingerprints support reconstruction; archive restoration
does not discover new reports or corrections. `publish_motherduck.py` publishes
the active Gold separately. No refactor deployment or remote refresh is implicit.

## Verification of this refactor

The latest suite has 222 passing tests. Scenarios cover JSON-only, CSV/PDF-only
and mixed runs, report-write failure, wrong Gold selection, changed inputs,
logging context, additive migration and archive pinning on success/failure.
A complete local rebuild using the 68 enabled reports produced 1,453 participants
and 140 BMW entries across 45 columns (2022: 61; 2023: 455; 2024: 468; 2025: 469).
The active local Gold includes Daytona 2022. The 114-file archive was renewed and
restored for verification; MotherDuck history received 16 additional columns.
Its active publication and public view remain on the previous 1,392-participant
dataset until the new publication workflow succeeds.

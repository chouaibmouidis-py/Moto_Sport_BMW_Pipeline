# BMW Motorsport — IMSA analytics

### [Explore the live dashboard →](https://bmw-imsa-analytics.streamlit.app/)

Compare BMW pit-stop records across **34 IMSA races, Daytona 2022 and 2023–2025**. Filter by
season, event and class; inspect missing observations, count discrepancies and
source provenance. **Open in your browser — no installation required.**

A personal data engineering project that transforms official IMSA WeatherTech
race reports into traceable participant and pit-stop datasets using **Python,
SQL and DuckDB**. The project is developed as a simulated internship assignment,
independently of BMW and IMSA.

**Python · SQL · DuckDB · Airflow · GitHub Actions · MotherDuck · Streamlit**

## Coverage & release status

| Season | Source formats | Race entries | BMW entries |
| --- | --- | ---: | ---: |
| 2022 — Daytona | Classification CSV and pit-stop PDF | 61 | 3 |
| 2023 | Classification CSV and pit-stop PDF | 455 | 51 |
| 2024 | Classification and pit-stop JSON | 468 | 38 |
| 2025 | Classification and pit-stop JSON | 469 | 48 |
| **Total** | **34 races** | **1,453** | **140** |

The Daytona 2022 extension (45 columns, 114 archived files) is live on the
hosted dashboard. Subsequent maintenance, the pytest migration and file-by-file
archival/restoration are validated locally with 334 passing tests and 97 passing subtests.
Pushing code triggers CI; renewing the archive and running production publication
are separate operations.

## Delivered milestones

| Milestone | Result and evidence |
| --- | --- |
| Multiformat integration | One manifest and orchestrator for 68 enabled reports: JSON/JSON and CSV/PDF pairs across 34 races. |
| Layer boundaries | Bronze extracts source data; Silver normalizes and applies explicit corrections; Gold consumes checked Silver evidence and marts rather than re-extracting Bronze. |
| Sporting data preservation | Gold expanded from 29 to 45 columns, retaining team, laps, fastest-lap metrics, raw/converted durations and separately typed time/lap gaps. |
| Daytona 2022 | 61 participants, 3 BMW and 1,762 extracted stops integrated; previous participant records compared in both directions, excluding intentional manufacturer corrections. |
| Traceability and publication | Versioned inputs, SHA-256 checks, verified Parquet writes and independent Gold activation. Remote publication validates content before switching the active run in a transaction. |
| Remote reconstruction and access | 114-file source archive renewed and restored for verification; additive history migration completed; hosted dashboard uses a separate read-only identity. |
| Review maintenance — locally validated | Case-independent coherence rules, contextual logs, and preservation of the original exception if rollback also fails. These later fixes are distinct from the already published data extension. |
| Pytest migration — completed locally | All non-empty test modules use native pytest functions and explicit fixtures. Scenarios, assertions and per-test isolation are preserved; see the migration guide. |
| File-by-file archival — locally validated | Validate, insert and verify each file before preparing the next; retain lightweight inventory records. Single-read, metadata round-trip, later-file rollback and Python payload-retention tests pass locally. |
| File-by-file restoration — locally validated | Load a lightweight inventory, fetch and validate one payload, verify a unique temporary file, then release the payload before fetching the next. Replace destinations only after all files are prepared; invalid later content preserves existing files and removes staged temporaries. |
| Archive regression maintenance | Isolated fixtures share repeated setup; explicit CLI arguments replace argv patches in archive tests. A golden archive ID detects changes to the fixed inventory serialization. |
| Regression coverage | Latest full local run on 26 November 2026: **334 passing tests and 97 passing subtests**, including mutation, publication failure, migration, archive and restoration scenarios. |

All non-empty test modules now use native pytest functions. Shared fixtures
provide isolated DuckDB connections, temporary paths and contextual log capture.
Input variants are parameterized; checks within a shared scenario use native
pytest subtests. No TestCase classes remain. See the [migration guide](docs/pytest_migration.md).
Tests are launched explicitly or by CI; running the pipeline alone does not run
the `tests/` suite. Data validation inside production modules still executes on
every applicable pipeline run. New development follows a test-first workflow:
define the contract, observe the intended failing test, implement, then refactor.

## Data flow

```text
Official IMSA reports
    ├── 2024–2025 JSON → Raw → Bronze → Silver → quality reports and marts
    └── 2022–2023 CSV/PDF → Raw → Bronze → Silver → per-event marts
                                                        │
Both participant-mart paths + manufacturer evidence ─────┘
    ↓
Local 2022–2025 Gold participants + provenance snapshots
    ↓
MotherDuck publication → hosted Streamlit dashboard
```

GitHub Actions restores the pinned source and metadata archive
from MotherDuck and executes the manifest-driven Airflow DAG. Validated Gold data is
published transactionally. The workflow is scheduled for Mondays at **23:59,
Africa/Casablanca**, and can also be triggered manually. The remote path has
completed successfully. The schedule is configured; a scheduled-run outcome
should be checked in GitHub Actions rather than inferred from a manual run.

Controls cover source integrity, conversion, keys, relationships and participant
preservation. Each output is written to a temporary Parquet and checked after
reloading. Main and Gold runs have separate active references, updated after
successful publication and required-file checks.

Both JSON and CSV/PDF mart paths require every observed stop to match a participant
in the classification paired with its report. An unmatched stop blocks publication.
Classified participants without stop details remain in the results with NULL
observed counts and an explicit status.

## Quick start

Use Python 3.12 or later and uv. Run these commands from the project root.
Initial setup and JSON downloads require Internet access.

```bash
uv sync --locked
uv run --locked python -m pytest -v
uv run --locked python run_pipeline.py
```

The default command processes all enabled JSON, CSV and PDF sources. It does
not publish to MotherDuck. See the [execution guide](docs/project_reference.md#execution-order)
for refresh, selection and publication options.

<details>
<summary>Advanced CLI & legacy diagnostics</summary>

Optional diagnostics for the legacy JSON main-run reference:

```bash
uv run --locked python inspect_marts.py
uv run --locked python inspect_quality.py
```

These readers follow `data/current.json`, which the shared multiformat path does
not activate. For current common results, use the dashboard or read
`data/gold/current.json` and the selected Gold Parquet as described in the
[execution reference](docs/project_reference.md#responsibilities-and-active-paths).

Enable detailed tables and retain execution logs:

```bash
uv run --locked python run_pipeline.py --verbose --log-file data/logs/pipeline.log
```

Select sources or execute individual stages:

```bash
# Optional selection, without creating a format- or season-specific launcher:
uv run python run_pipeline.py --season 2023 --event daytona
# Airflow invokes these same stages:
uv run python run_pipeline.py --stage raw
uv run python run_pipeline.py --stage bronze
uv run python run_pipeline.py --stage process
uv run python run_pipeline.py --stage gold
```

The only source configuration is `config/sources.json`. Readers and validators
are selected by document type and declared format. Processing writes unique
candidate directories, including classification quality reports, and activates
`data/processing/current.json` only after every selected report succeeds.
Gold snapshots that complete processing run; it no longer reads independently
updated per-season files. A failed quality-report write retains the previous
processing and Gold references. Source fingerprints are checked before reuse.

Rebuild the processing stage before building Gold on this checkout. Existing
legacy files under `data/exploration/` or `data/csv_pdf/` are preserved but
are no longer production inputs. A selected season/event builds a correspondingly
scoped Gold; run without selection to restore the complete configured coverage.
No command publishes to MotherDuck unless `publish_motherduck.py` is invoked.

Gold publication and dashboard sharing are separate operations.
`publish_motherduck.py` writes and validates the data, then commits the active
run in one transaction. It does not create shares or change access grants.
Run `uv run --locked --no-sync python configure_motherduck_share.py` separately
when setting up the `bmw_gold` share or its `explorer` read access. This command
does not publish data and is not part of the recurring Airflow publication task.
The existing share uses automatic updates; its configuration is not repeated
for each Gold run. An existing remote history schema must be migrated separately
before publishing a Gold run with additional columns.

Build Gold from the already completed processing run:


```bash
uv run --locked python build_gold.py
```

The [execution guide](docs/project_reference.md#execution-order) covers the shared
commands, source refresh and selection. The [2023 qualification](docs/imsa_2023_season_coverage.fr.md)
retains historical findings; the [current reference](docs/project_reference.md#responsibilities-and-active-paths)
describes the common production paths for JSON and CSV/PDF.

</details>

## Dashboard

The Streamlit dashboard reads the active publication from the restricted
MotherDuck Gold share. It does not require local race reports or Parquet files.
Configure the dedicated dashboard token in `.streamlit/secrets.toml`, following
the [hosting guide](docs/dashboard_hosting.md), then start the app:

```bash
uv run --locked streamlit run dashboard.py
```

Select a season, event and class to explore BMW participants,
recorded pit-stop counts and mean durations. The quality panel lists count
discrepancies, missing stop details and unconverted durations for that selection.
The source panel exposes report identifiers and fingerprints.

Column help explains declared counts, duration averages and coverage. Missing
values remain visible, and selections without participants or averages receive
an explicit message. Keep the terminal open while using the dashboard; press
`Ctrl+C` to stop its local server. Active browser sessions check for updates every
five minutes. Use **Refresh data** to request an immediate refresh. All charts
and tables in an update use the same downloaded Gold snapshot.

## Reading the project

| Need | Documentation |
| --- | --- |
| Find a script, module, SQL query or call path | [Code and execution map](docs/code_map.md) |
| Commands, output schemas, reconciliation rules and failure handling | [Detailed project reference](docs/project_reference.md) |
| Gold inputs, publication and limitations | [Gold guide](docs/gold.fr.md) |
| Module organization and logging | [Architecture guide](docs/architecture_et_logs.fr.md) |
| Case-independent interpretation of source labels | [Case contract](docs/data_case_contract.md) |
| Configuring source reports | [Configuration guide](config/README.fr.md) |
| Qualified sources and remaining coverage | [Source inventory](docs/source_inventory.fr.md) and [coverage plan](docs/coverage_plan.fr.md) |
| Automated checks and manual source smoke check | [CI guide](docs/ci.fr.md) |
| Assignment, acceptance criteria and current milestones | [Project brief](docs/mission_stage_personnel.fr.md) |

Public documentation is in English. Historical `.fr.md` filenames are retained
to preserve previously shared links.

## Validation and boundaries

| Current limitation | Implication |
| --- | --- |
| Qualified report coverage | The dataset covers the selected IMSA reports, not all of 2022, other championships or worldwide BMW activity. Gold is a participation table, not a common publication of every detailed stop. |
| Source accuracy and interpretation | Hashes establish byte identity, not sporting truth. Missing observations remain NULL; source count discrepancies remain visible. Clock-derived durations assume a stop under 24 hours. |
| Historical manufacturer evidence | Some earlier-season name resolution uses later reports. Assess temporal leakage before predictive or pre-race use; explicit model corrections retain their status and provenance. |
| Migration client memory | `fetchall()` plus `Counter` retains historical/visible rows in Python. Memory and transfer volume grow with the history; no large-history memory/cost benchmark is established. |
| Archive memory | File payloads no longer accumulate in Python. Inventory grows with file count; one complete file, metadata and engine/driver/transaction buffers still consume memory. The warmed Python allocation guard is not a total-process RAM bound or a live MotherDuck benchmark. |
| Restoration memory and activation | Payloads are fetched and staged one at a time; inventory and staged paths grow with file count. Temporary disk usage grows with the archive size. Final replacements are individually atomic, not globally atomic: a failure during activation can leave mixed versions. Cleanup errors are logged and can leave temporary files. |
| Failed candidate retention | Local candidate files may remain after failure. Automatic expiration and cleanup are not implemented. |
| Operational failure boundaries | Concurrency and hardware-crash recovery are not qualified. If connection loss prevents rollback, the remote outcome must be verified after reconnection; preserving the exception does not confirm rollback. |
| Reconstruction and source revisions | Snapshots retain inputs and SQL, not the Python implementation/environment. Preserve the code revision and lockfile. The pinned archive does not discover new races or upstream corrections automatically. |

Full behavior and evidence are documented in the
[project reference](docs/project_reference.md#validation-and-limits) and
[Gold guide](docs/gold.fr.md). A passing suite covers its defined scenarios;
it is not a guarantee for untested source formats, volumes or failure modes.

Working files stay under the ignored `data/` directory. Versioned source bytes
are also retained in the restricted MotherDuck archive for remote reconstruction.
The pinned archive does not automatically discover new races or official report
corrections. See the [reuse notes](docs/project_reference.md#remaining-work-and-historical-evidence).

## Planned milestones

The following work is **planned, not implemented**.
Tests precede each behavioral change; measurements precede performance claims.

| Milestone | Target and acceptance |
| --- | --- |
| Exact migration checks inside the engine | Replace Python-wide historical copies with occurrence-sensitive before/after comparisons and scalar results. Preserve content, duplicate, NULL and rollback semantics; measure engine placement, RAM, transfers and temporary-storage cost. COUNT alone or an aggregated fingerprint must not silently weaken the contract. |
| Archive engine and oversized-file memory | Qualify native/driver/transaction memory and cold-start RSS separately from the completed Python payload-retention guard. Validate chunked handling before accepting individually oversized BLOBs. Preserve the all-or-nothing archive transaction. |
| Progressive processing beyond source transfer | Audit downloading, Bronze extraction, Silver consolidation and Gold publication independently; extend progressive processing where it preserves cross-source checks and activation contracts. File-by-file archive/restore does not establish end-to-end micro-batching. |
| Restoration recovery and staging budget | Test replacement failures and recovery from mixed final versions, qualify concurrent restores and crash recovery, and define temporary-disk capacity/cleanup policies. Existing preservation tests cover preparation failures, not global multi-file atomicity. |
| Failed-candidate retention | Add explicit failure status/time, a configurable retention period and a dry-run cleanup command. Protect active, running and successful historical runs; test selection and deletion safeguards before enabling a real scheduled trigger. |
| dbt-duckdb pilot | Move a bounded vertical slice of transformations/tests while preserving contracts and explicit publication/activation guarantees. Expand only after equivalence is verified. |
| Streaming integrity helpers | Reduce full-file hashing/copy memory with a measured, tested common implementation while keeping hashes tied to the bytes actually processed. |
| Wider source coverage | Qualify additional report families and races before activation, including the remaining 2022 scope and future car/motorcycle sources. Worldwide 2022–2026 coverage remains an objective. |

Detailed delivery scope and acceptance criteria are maintained in the
[project brief](docs/mission_stage_personnel.fr.md). The next milestone is chosen
explicitly rather than inferred from this backlog; no delivery dates or measured
savings are claimed for work not yet executed.

## License

Copyright 2026 Chouaib MOUID. Original project code and original documentation
are licensed under the [Apache License 2.0](LICENSE). See [NOTICE](NOTICE) for
attribution and scope.

Official IMSA reports, source datasets, third-party materials and BMW/IMSA
trademarks are excluded from this code license and retain their own rights and
usage terms. This project is not affiliated with or endorsed by BMW or IMSA.

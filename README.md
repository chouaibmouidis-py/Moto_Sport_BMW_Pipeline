# BMW Motorsport — IMSA analytics

### [Explore the live dashboard →](https://bmw-imsa-analytics.streamlit.app/)

Compare BMW pit-stop records across **33 IMSA races, 2023–2025**. Filter by
season, event and class; inspect missing observations, count discrepancies and
source provenance. **Open in your browser — no installation required.**

A personal data engineering project that transforms official IMSA WeatherTech
race reports into traceable participant and pit-stop datasets using **Python,
SQL and DuckDB**. The project is developed as a simulated internship assignment,
independently of BMW and IMSA.

**Python · SQL · DuckDB · Airflow · GitHub Actions · MotherDuck · Streamlit**

## Hosted dashboard coverage

| Season | Source formats | Race entries | BMW entries |
| --- | --- | ---: | ---: |
| 2023 | Classification CSV and pit-stop PDF | 455 | 51 |
| 2024 | Classification and pit-stop JSON | 468 | 38 |
| 2025 | Classification and pit-stop JSON | 469 | 48 |
| **Total** | **33 races** | **1,392** | **137** |

The common Gold participant table contains **29 columns**, including session
context, stop statistics, source provenance and quality statuses. The JSON
workflow covers 8,307 detailed stops; the 2023 PDF path covers 3,953.

## Locally validated coverage

The local pipeline also includes **Daytona 2022**: 61 participants (3 BMW) and
1,762 extracted pit stops. Both sources are enabled in the manifest after a
complete local Raw → Bronze → Silver → Gold run. Local Gold now contains
**1,453 participants, including 140 BMW, across 34 races, with 45 columns**.
The previous 1,392 participant records are preserved, apart from the documented
targeted manufacturer corrections. Exact model corrections are computed in
Silver and retained in Gold with `matched_override` / `silver_override` statuses.

These changes are **not deployed to the hosted dashboard yet**. The source archive
has been renewed to 114 files, including the two 2022 reports and their metadata,
and the MotherDuck history schema has received the 16 additional columns.
The existing public view and active publication remain unchanged. After the code
and archive reference are pushed and CI passes, run the publication workflow and
verify the dashboard. Local activation does not publish a new remote Gold run.

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
MotherDuck publication → hosted Streamlit dashboard (extension pending deployment)
```

GitHub Actions restores the pinned source and metadata archive
from MotherDuck and executes the manifest-driven Airflow DAG. Validated Gold data is
published transactionally. The workflow is scheduled for Mondays at **23:59,
Africa/Casablanca**, and can also be triggered manually. The remote path has
completed successfully; the first scheduled execution remains to be observed.

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
uv run --locked python -m unittest discover -s tests -v
uv run --locked python run_pipeline.py
```

Read results from the active main run:

```bash
uv run --locked python inspect_marts.py
uv run --locked python inspect_quality.py
```

Enable detailed tables and retain execution logs:

```bash
uv run --locked python run_pipeline.py --verbose --log-file data/logs/pipeline.log
```

Run all enabled sources through the shared pipeline (JSON, CSV and PDF):

```bash
uv run python run_pipeline.py
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
| Configuring source reports | [Configuration guide](config/README.fr.md) |
| Qualified sources and remaining coverage | [Source inventory](docs/source_inventory.fr.md) and [coverage plan](docs/coverage_plan.fr.md) |
| Automated checks and manual source smoke check | [CI guide](docs/ci.fr.md) |
| Assignment, acceptance criteria and current milestones | [Project brief](docs/mission_stage_personnel.fr.md) |

Public documentation is in English. Historical `.fr.md` filenames are retained
to preserve previously shared links.

## Validation and boundaries

The automated suite covers unit and local integration scenarios, including
publication failures and reconstruction from copied inputs.

Source fields unavailable in a report remain `NULL`; quality statuses expose
missing values and count discrepancies. Clock-derived stop durations assume
less than 24 hours. Manufacturer resolution for 2023 uses later-season evidence,
which requires a temporal-leakage assessment for predictive uses.

The JSON run and Gold have independent activation. The 2023 exploratory marts
are published per event. Remote-change detection, concurrent publication and
hardware-crash recovery remain areas for further work. Gold snapshots retain
input data and SQL; reproduction also depends on the code revision and Python
environment. Full details are in the [reference](docs/project_reference.md#validation-and-limits)
and [Gold guide](docs/gold.fr.md).

Working files stay under the ignored `data/` directory. Versioned source bytes
are also retained in the restricted MotherDuck archive for remote reconstruction.
The pinned archive does not automatically discover new races or official report
corrections. See the [reuse notes](docs/project_reference.md#remaining-work-and-historical-evidence).

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

## Current coverage

| Season | Source formats | Race entries | BMW entries |
| --- | --- | ---: | ---: |
| 2023 | Classification CSV and pit-stop PDF | 455 | 51 |
| 2024 | Classification and pit-stop JSON | 468 | 38 |
| 2025 | Classification and pit-stop JSON | 469 | 48 |
| **Total** | **33 races** | **1,392** | **137** |

The common Gold participant table contains **29 columns**, including session
context, stop statistics, source provenance and quality statuses. The JSON
workflow covers 8,307 detailed stops; the 2023 PDF path covers 3,953.

## Data flow

```text
Official IMSA reports
    ├── 2024–2025 JSON → Raw → Bronze → Silver → quality reports and marts
    └── 2023 CSV/PDF  → Raw → Bronze → Silver → per-event marts
                                                        │
Both participant-mart paths + manufacturer evidence ─────┘
    ↓
Common 2023–2025 Gold participants + provenance snapshots
    ↓
MotherDuck publication → hosted Streamlit dashboard
```

GitHub Actions restores a pinned archive of **110 source and metadata files**
from MotherDuck and executes the **13-task Airflow DAG**. Validated Gold data is
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

Build Gold after preparing both the JSON run and the 2023 per-event marts:

```bash
uv run --locked python build_gold.py
```

The [execution guide](docs/project_reference.md#setup-and-execution) covers
refreshing JSON sources. The [2023 guide](docs/imsa_2023_season_coverage.fr.md)
and [detailed reference](docs/project_reference.md#current-project-scope) describe
the separate CSV/PDF batch commands and required local inputs.

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
| Original learning assignment | [Project brief](docs/mission_stage_personnel.fr.md) |

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
environment. Full details are in the [reference](docs/project_reference.md#checks-and-current-limitations)
and [Gold guide](docs/gold.fr.md).

Working files stay under the ignored `data/` directory. Versioned source bytes
are also retained in the restricted MotherDuck archive for remote reconstruction.
The pinned archive does not automatically discover new races or official report
corrections. See the [reuse notes](docs/project_reference.md#github-actions-and-reuse).

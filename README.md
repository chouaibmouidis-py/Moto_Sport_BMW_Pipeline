# BMW Motorsport data pipeline

Public documentation is written in English. Historical `.fr.md` filenames are
retained so previously shared links keep working.

A personal data engineering project structured as a simulated internship assignment:
turn official race reports into traceable, validated datasets, then analyze BMW
race entries and their pit stops. This is an educational portfolio project, not a
production service. It is not affiliated with, endorsed by, or sponsored by BMW or
IMSA. The [project brief](docs/mission_stage_personnel.fr.md) defines the scope,
deliverables, and acceptance criteria.

## Current project scope

Shared implementation lives in `src/moto_sport_bmw_pipeline/`; historical root
scripts remain available as CLI and compatibility facades. The
[repository CI](docs/ci.fr.md) checks changes on every push and pull request.
The [architecture and logging guide](docs/architecture_et_logs.fr.md) explains
module responsibilities, logging rules, and the limits of fail-fast behavior.
To retain logs from the complete workflow:

```bash
uv run python run_pipeline.py --log-file data/logs/pipeline.log
```

Alongside the 2024–2025 JSON pipeline described below, a separate CSV/PDF
exploration covers eleven 2023 WeatherTech races: **455 classification entries
(including two non-starters), 51 BMW entries, and 3,953 extracted pit stops,
including 367 BMW stops**. The eleven summaries remain in `data/exploration`,
outside the active main run. See the
[2023 findings and limitations](docs/imsa_2023_season_coverage.fr.md).
Run against local Raw files with `uv run python explore_2023_season.py`.

The eleven classification CSV files also have a separate Bronze → Silver path:
`uv run python explore_2023_season.py --classification-only`.
It preserves all 455 race entries and their provenance; Silver outputs are stored
in `data/exploration/<event_id>-2023/silver/classification.parquet`, without
activation in the main run.

The eleven PDF pit-stop reports also have their own Bronze and Silver layers:
3,953 stops, including 367 BMW stops, with converted durations and extraction
markers retained. Rebuild separately from local files:

```bash
uv run python explore_2023_season.py --pdf-bronze-only
uv run python explore_2023_season.py --pdf-silver-only
```

Generate the eleven marts from these Silver files with:
`uv run python explore_2023_season.py --mart-only`.
They preserve all 455 race entries, including eleven without pit-stop details
(observed count remains `NULL`). Reported counts remain `NULL` because they are
absent from the 2023 CSV files. These 2023 batches do not change the main run reference.

The [common 2023–2025 Gold layer](docs/gold.fr.md) combines race entries using an
explicit schema, traceable manufacturer resolution, and input copies captured
for each run. Build an independent publication with `uv run python build_gold.py`;
its reference is `data/gold/current.json`. The current qualified dataset contains
**1,392 race entries, including 137 BMW entries, across 29 columns**: 455/51 in
2023, 468/38 in 2024, and 469/48 in 2025 (all entries/BMW entries).
Gold combines participant summaries; it is not a common table of all detailed
pit stops. Its three Parquet outputs, `inputs.json`, and **62 input snapshots**
are described below.

Forty-four JSON documents from the official
[IMSA / Al Kamel portal](https://imsa.results.alkamelcloud.com/) are configured in
[`config/sources.json`](config/sources.json): twenty-two “Pit Stops Time Cards”
reports and twenty-two Official classification reports. Eleven pairs cover
2025: Road America, Long Beach, Daytona, Laguna Seca, Detroit, Sebring, Watkins
Glen, Canadian Tire Motorsport Park, VIR, Indianapolis, and Road Atlanta.
Final reports are selected for Daytona (hour 24), Sebring (hour 12), Watkins Glen
(hour 6), Indianapolis (hour 6), and Road Atlanta (hour 10), without adding
together intermediate hourly snapshots. All eleven calendar races are included
for these two report families; the
[2025 coverage tracker](docs/imsa_2025_season_coverage.fr.md) distinguishes the batches.
Eleven 2024 pairs are also validated locally: Road America, Laguna Seca, Detroit,
Long Beach, Canadian Tire, VIR, Daytona, Sebring, Watkins Glen, Indianapolis,
and Road Atlanta, using the same transformations. All eleven 2024 races are
covered for these two report families; see the
[2024 coverage tracker](docs/imsa_2024_season_coverage.fr.md).

| 2025 report | Car entries | Driver entries | Pit stops | BMW pit stops |
| --- | ---: | ---: | ---: | ---: |
| Road America, Race | 50 | 100 | 137 | 15 |
| Long Beach, Race | 26 | 52 | 32 | 3 |
| Daytona, Race, hour 24 | 69 | 265 | 1,622 | 144 |
| Laguna Seca, Race | 37 | 74 | 88 | 13 |
| Detroit, Race | 22 | 44 | 36 | 10 |
| Sebring, Race, hour 12 | 64 | 192 | 716 | 66 |
| Watkins Glen, Race, hour 6 | 57 | 151 | 387 | 34 |
| Canadian Tire Motorsport Park, Race | 35 | 70 | 111 | 8 |
| VIR, Race | 23 | 46 | 54 | 7 |
| Indianapolis, Race, hour 6 | 63 | 167 | 376 | 31 |
| Road Atlanta, Race, hour 10 | 61 | 183 | 558 | 57 |
| **Total** | **507** | **1,344** | **4,117** | **388** |

These volumes are reference values for this dataset, not business constants
imposed on future races. A source entry is not necessarily a distinct car: the
same number may appear in several fragments. All competitors are retained;
the mart reader applies the BMW filter afterward.

For 2025, classifications contain **469 race entries, including 48 BMW entries**:

| 2025 classification | Participants | BMW race entries | `count_mismatch` | Percentage |
| --- | ---: | ---: | ---: | ---: |
| Road America | 48 | 5 | 2 | 4.17% |
| Long Beach | 27 | 3 | 0 | 0% |
| Daytona, hour 24 | 61 | 5 | 14 | 22.95% |
| Laguna Seca | 36 | 5 | 1 | 2.78% |
| Detroit | 22 | 4 | 0 | 0% |
| Sebring, hour 12 | 56 | 5 | 8 | 14.29% |
| Watkins Glen, hour 6 | 55 | 5 | 6 | 10.91% |
| Canadian Tire Motorsport Park | 35 | 3 | 0 | 0% |
| VIR | 23 | 3 | 0 | 0% |
| Indianapolis, hour 6 | 53 | 5 | 4 | 7.55% |
| Road Atlanta, hour 10 | 53 | 5 | 3 | 5.66% |

These totals count entries per race, not unique cars across all events.

Road America 2024 adds 47 race entries, including four BMW entries, 49 car
entries, 98 driver entries, and 163 detailed pit stops, including eight BMW stops.
With the other ten integrated 2024 races, the active 2024–2025 scope totals
**937 race entries, including 86 BMW entries**, **8,307 detailed pit stops,
including 711 BMW stops**, 1,066 car entries, and 2,877 driver entries.
Twenty-two quality summaries are separated by source and version.
Road America 2024 has four count mismatches out of 47 (8.51%), separate from
the 2025 results. Source models `BMW M4 GT3` and `BMW M4 GT3 EVO` remain distinct.

At Road America 2025, the pit-stop report contains 50 fragments for 47 distinct
car numbers. The comparison preserves all 48 classification participants:
car `70` reports zero stops but has no details; its status is
`zero_reported_no_detail`, with an observed count retained as `NULL`.
At Long Beach, car `34` reports one stop with no matching details; it remains
present with `missing_stop_details`. At Daytona, all 61 numbers appear in both
reports; the pit-stop report's 69 entries are fragments. BMW `48` has 29 reported
stops versus 30 detailed stops. At Laguna Seca, car `70` reports four stops
versus three detailed stops.

A published pit-stop duration does not necessarily measure refueling, mechanics'
work, or net time lost on track. Worldwide car and motorcycle coverage for
2022–2026 remains an exploration goal, not achieved coverage. The reported
coverage is limited to the selected events and report families above.

## Setup and execution

Requirements: Python 3.12 or later, uv, and Internet access to install dependencies
and download the initial sources. From the project root:

```bash
uv sync --locked
uv run --locked python -m unittest discover -s tests -v
uv run --locked python run_pipeline.py
```

The single command runs these stages in order:

1. `inspect_manifest.py`: select enabled `pit_stops` reports, download them if
   needed, or verify the SHA-256 hashes of local files.
2. `build_bronze.py`: preserve JSON blocks in Parquet and compare contents and
   volumes with the source document.
3. `inspect_classification.py`: select enabled classifications, verify existing
   Raw files, or download them with metadata.
4. `build_classification_bronze.py`: preserve and compare the three roots
   `session`, `fastest_lap`, and `classification` in a separate Bronze layer.
5. `analyze_bronze.py`: transform, validate, write twelve outputs into a new run
   directory, then activate that set.

If a stage fails, the launcher stops before the next one.
`Pipeline completed successfully.` is logged only after all five stages succeed.
Stage paths are resolved relative to the project location by the package's
orchestration module, which also runs stages with the project root as their
working directory.

Example from another directory; adapt the paths:

```bash
uv run --locked --project /path/to/Moto_Sport_BMW_Pipeline python /path/to/Moto_Sport_BMW_Pipeline/run_pipeline.py
```

Existing files are reused. To deliberately download the configured reports again,
record new metadata, and rebuild:

```bash
uv run --locked python inspect_manifest.py --refresh
uv run --locked python inspect_classification.py --refresh
uv run --locked python run_pipeline.py
```

To display detailed analysis tables, either run the analysis directly or enable
verbose output for the complete pipeline:

```bash
uv run --locked python analyze_bronze.py --verbose
uv run --locked python run_pipeline.py --verbose --log-file data/logs/pipeline.log
```

`run_pipeline.py` supports both `--verbose` and `--log-file`: it propagates the
logging configuration to its stages and forwards `--verbose` to the analysis.
Verbose mode enables DEBUG logs and analysis tables. Blocking checks and essential
counts also run without it. The optional UTF-8 log file is appended to.

## Data and outputs

```text
data/
├── raw/<source_id>/
│   ├── <source document .JSON>
│   └── metadata.json
├── bronze/<source_id>/document.parquet
├── runs/<run_id>/
│   ├── silver/
│   │   ├── sessions.parquet
│   │   ├── car_entries.parquet
│   │   ├── driver_entries.parquet
│   │   ├── pit_stops.parquet
│   │   └── classification.parquet
│   ├── quality/
│   │   ├── session_quality_summary.parquet
│   │   ├── total_pit_duration_quality.parquet
│   │   ├── total_pit_duration_comparison.parquet
│   │   ├── classification_pit_stop_comparison.parquet
│   │   └── classification_count_quality.parquet
│   └── marts/
│       ├── enriched_pit_stops.parquet
│       └── race_car_summary.parquet
├── current.json
└── gold/
    ├── current.json
    └── runs/<run_id>/
        ├── race_car_summary.parquet
        ├── manufacturer_reference.parquet
        ├── manufacturer_evidence.parquet
        ├── inputs.json
        └── inputs/...
```

- **Raw**: downloaded document and provenance metadata, download timestamp, and
  SHA-256 hash. The hash checks the identity of local bytes; it does not prove
  that the source content is correct.
- **Bronze**: one row per document. Pit-stop reports preserve `session` and
  `pit_stop_analysis` as JSON; classifications preserve `session`, `fastest_lap`,
  and `classification`. Business transformations take place in Silver.
- **Silver**: separate session context per document, car entries, driver entries,
  pit stops, and classification participants. Text car numbers retain leading
  zeros. Classification Silver currently projects only keys, car number,
  manufacturer, model, overall position, class, reported stop count, and
  `not_finished`; other fields remain preserved in Bronze.
- **Quality**: missing values and conversion failures are distinguished;
  summed durations are compared with the last reported cumulative duration by
  source, version, and car number, using `matched`, `incomplete`, and `mismatch`
  statuses. A separate report also reconciles classification and pit-stop counts.
- **Marts**: stops enriched with incoming and outgoing driver names without
  multiplying rows by the number of drivers; a per-participant summary combining
  classification, counts, comparison status, and duration statistics.
- **Gold**: a common, explicitly defined 29-column participant summary, plus
  manufacturer reference and evidence tables. Source rows are combined using
  `UNION ALL`, without silent deduplication. Missing or duplicate
  (`source_id`, `bronze_sha256`, `car_number`) keys block publication.

`bronze_sha256` identifies the bytes of the Bronze file used. Relationships to
car entries also use `source_id` and `source_entry_index`. That index is a
position within a document version, not a permanent car identifier.

### Classification and pit-stop reconciliation

Documents are paired through the manifest using `championship`, `season`,
`event_id`, and `session_id`. Each classification must have exactly one candidate
pit-stop report; a missing or multiple match blocks processing.
The shared process loads enabled classifications into one temporary Bronze table,
retaining each document's identifier and hash. Transformations and joins keep
sources and their versions separate. The batch must include every enabled
classification. If a Bronze file is missing, the loader raises
`FileNotFoundError` with the source and expected path. Processing stops without
publishing a partial batch or activating a new run; documents already loaded
remain in the temporary connection. A test covers this rejection after a first
valid document has been loaded.

Stops are counted by source, Bronze hash, and text car number, across all
fragments. A `LEFT JOIN` from the classification preserves participants without
detailed stops. The loaded report version participates in the join; classification
and pit-stop report hashes are retained separately. Participant counts before
and after the join are checked.

The `race_car_summary` adds stop-summary statistics by pit-stop report source,
Bronze hash, and car number. It retains participants without details; their
statistics remain `NULL`. Before publication, `validate_race_car_summary` rejects
missing or duplicate keys and compares participant keys against the classification
in both directions. Its grain is one row per classification `source_id`,
`bronze_sha256`, and `car_number`. Tests cover, among other cases, substituting a
participant while keeping the same row count, concurrent sources and versions,
and a valid case. The mean duration describes the values available in the report;
it does not, by itself, measure mechanics' performance.

| `comparison_status` | Meaning |
| --- | --- |
| `matched` | Reported and observed counts are equal. |
| `zero_reported_no_detail` | Zero reported; no detailed rows found. |
| `missing_stop_details` | Reported count is available and nonzero; no details found. |
| `count_mismatch` | Both counts are available but differ. |
| `unavailable_reported_count` | Reported count is missing or cannot be converted. |
| `missing_pit_stop_report` | Matching report not found in the loaded Bronze data. |

These statuses describe the data; they neither correct source counts nor explain
race events. Count mismatches are published for investigation and do not, on
their own, block publication. Zero reported with no details is not automatically
an error. Reconciliation uses the selected documents; it does not demonstrate
that they were published at the same time.

### Code responsibilities

Root scripts are CLI and compatibility facades; shared processing belongs to
`src/moto_sport_bmw_pipeline/`. `orchestration.py` coordinates the five stages;
`pipeline.py` coordinates loading, Silver transformations, relationship checks,
reports, and main-run publication. `source_loading.py`, `silver.py`, `quality.py`,
`duration_quality.py`, and `marts.py` own their respective shared operations.
`diagnostics.py` displays detailed analysis tables.

`analyze_bronze.py` invokes the shared candidate-run builder.
`analyze_classification.py` uses the shared classification loader and
transformation; running it alone remains an exploration of the Road America
pilot dataset only. The historical `silver_writer.py` and `run_publication.py`
facades expose shared implementations: `parquet_writer.py` writes and verifies
individual files, while `run_reference.py` activates a complete set and resolves
the current run for readers. `publication.py` registers and publishes outputs.
`gold.py` builds the independent Gold candidate from snapshotted inputs.
SQL queries remain separate so they can be tested independently.

## Inspecting active results

After a successful main run:

```bash
uv run --locked python inspect_quality.py
uv run --locked python inspect_marts.py
```

Each reader displays `Reading run: ...`, reads `current.json` once, then uses the
selected directory for its files.

- The quality reader displays missing or invalid session information and
  unconverted cumulative times. In the current dataset, both Long Beach
  temperatures are missing; no cumulative time fails conversion.
- It also displays classification/pit-stop comparisons other than `matched`.
  At Road America, cars `22` and `88` have `count_mismatch`: respectively one
  reported stop versus two detailed stops, and four reported versus three
  detailed stops. Car `70` has `zero_reported_no_detail`. At Long Beach, car `34`
  has `missing_stop_details`. At Daytona, 14 participants have `count_mismatch`,
  including BMW `48`. Values were checked against Raw files; the cause of the
  discrepancies is not established and no correction is applied.
- The mart reader displays the 711 BMW stops and associated drivers, rounding
  displayed values to three decimal places.
- It also displays the **86 BMW race entries** from the twenty-two classifications,
  grouped by source and then position. The thirteen columns include source,
  manufacturer, model, position, class, stop counts, mean duration, valid and
  invalid duration counts, coverage, and status. Both tables are read from the
  same active run. The saved summary contains all 937 participants; the BMW
  filter belongs to the reader.
- The quality reader also displays a summary per classification source and
  version: total participants, `count_mismatch` count, and percentage.
  Twenty-two rows are produced: the eleven 2024 classifications,
  Road America (47, 4, 8.51%), Laguna Seca (34, 1, 2.94%), Detroit (21, 2, 9.52%),
  Long Beach (27, 3, 11.11%), Canadian Tire (34, 0, 0%), VIR (23, 0, 0%),
  Daytona (59, 16, 27.12%), Sebring (58, 4, 6.90%), Watkins Glen (56, 7, 12.50%),
  Indianapolis (56, 9, 16.07%), and Road Atlanta (53, 6, 11.32%);
  then the eleven 2025 classifications: Road America (48, 2, 4.17%),
  Long Beach (27, 0, 0%), Daytona (61, 14, 22.95%), Laguna Seca (36, 1, 2.78%),
  Detroit (22, 0, 0%), Sebring (56, 8, 14.29%), Watkins Glen (55, 6, 10.91%),
  Canadian Tire Motorsport Park (35, 0, 0%), VIR (23, 0, 0%),
  Indianapolis (53, 4, 7.55%), and Road Atlanta (53, 3, 5.66%).
  This indicator measures count mismatches only. Other statuses remain included
  in total participants without being counted as `count_mismatch`. Long Beach's
  0% therefore does not mean there are no anomalies: the detail flags car `34`.

An empty anomaly table means no row matches that particular filter, not that
the file contains no data. The cumulative-duration comparison report is saved
but is not yet displayed by `inspect_quality.py`.

To inspect Gold, read `data/gold/current.json`, then open
`data/gold/runs/<run_id>/race_car_summary.parquet` for that run in SQL or the
VS Code DuckDB extension. Do not glob across all run directories: that would
stack multiple publications of the same data.

## Publication and failure handling

Each file is first written to a temporary Parquet file, read back, and compared
with expected data before replacement within the candidate directory.
The twelve main-run files are written under `data/runs/<run_id>/`. Their presence
is checked before writing a temporary JSON reference and replacing
`data/current.json`.

Failure before activation leaves the previous reference unchanged. An incomplete
candidate directory and some temporary files may remain for diagnosis. Automatic
cleanup is not implemented; do not delete a directory still used by a reader.

The next launch restarts transformations; it does not resume exactly from the
last successful stage. Existing Raw files are verified and reused. A first run
that fails before activation creates no active run; readers then report the
missing reference.

The presence check at activation complements content checks performed during
writes; by itself, it is not Parquet validation. Simulated scenarios do not
establish recovery after machine interruption, durability after hardware failure,
or safe handling of concurrent publications.

### Independent Gold publication

`build_gold.py` reads the active JSON run reference once at startup and consumes
its participant mart plus the eleven existing 2023 CSV/PDF marts; it does not
rebuild the seasons. Each candidate copies the two configurations, SQL files
36–39, JSON Bronze manufacturer evidence, and input marts. For the current
scope, these are **62 snapshots**: two configurations, four SQL files, 44 Bronze
files, one main-run mart, and eleven 2023 marts. Calculations use those copies.

`inputs.json` records each input's role, original path, snapshot path, and
SHA-256 hash, together with the source JSON run ID. Snapshot hashes are validated
before calculation and again before activation. The three outputs are
`race_car_summary.parquet`, `manufacturer_reference.parquet`, and
`manufacturer_evidence.parquet`; each is read back and compared before
publication. Gold activation requires these three files plus `inputs.json`.
Only then is `data/gold/current.json` replaced. A failure retains the previous
Gold reference and leaves the candidate available for diagnosis;
`data/current.json` remains unchanged.

These copies pin the bytes used but do not prove that the independently
published 2023 exploratory marts were created together. This mechanism does not
archive the Python environment or implementation code; dependencies are described
by `pyproject.toml` and `uv.lock`. Exact reproduction after code changes also
requires retaining the code revision and environment. Concurrent deployment and
hardware-crash behavior have not been qualified.

Missing input-mart fields become typed `NULL` values. The 2023 text classification
status is not converted into `not_finished`; missing reported counts are never
inferred from observed stops. JSON manufacturers come directly from the source
(origin `source`, reference resolution `not_applicable`). For 2023, supplier IDs
are matched to names explicitly associated in local JSON Bronze evidence:
origin `reference` when the name is unique, otherwise `unresolved`. Ambiguous
values are not normalized automatically; **55 unresolved 2023 manufacturer
values** remain explicitly flagged. Evidence retains `source_id` and
`bronze_sha256`.

This mapping reuses later-season reports. It is a documented analytical
resolution, not proof of information available in real time in 2023. Using it
as pre-race historical information or a prediction feature requires assessing
temporal leakage. See the [Gold documentation](docs/gold.fr.md) for details.

## Checks and current limitations

The current validation baseline is **187 passing tests**, including Gold schema,
alignment, keys, input copying, independent activation, publication failures,
and rebuilding from snapshots after synthetic originals are removed.
The suite also covers HTTP and JSON errors, preservation of previous files,
conversions and midnight rollover, keys, relationships, versions, cumulative
durations, launcher failure handling, and activation. Test fixtures are synthetic;
the race-report data is real.

Report dates are interpreted without assigning an unconfirmed time zone.
Calculating durations from passage times assumes a stop lasts less than 24 hours;
differences are diagnosed without replacing the source duration. Numeric
durations use `DOUBLE`, so small binary-representation differences are possible.
Comparisons use an explicit tolerance.

The association between rebuilt Bronze files and currently available Raw files
is not an immutable history of all source versions. `--refresh` replaces the
Raw copy and its metadata; that pair is not published in a single transaction.
The pipeline does not yet automatically detect remote changes. Local SHA-256
verification does not contact the server. Hyphenated dates, the official message,
weather, and classification `fastest_lap` are preserved in Bronze but are not
yet normalized into classification Silver tables. Old `data/silver`,
`data/quality`, and `data/marts` paths may still exist locally; current readers
use directories under `runs`.

## GitHub Actions and reuse

Two workflows have distinct responsibilities:

- **Pipeline CI** (`.github/workflows/ci.yml`) runs on push, pull request, or
  manual dispatch. It installs locked dependencies on Python 3.12, checks
  whitespace in the HEAD change, runs unit and local integration tests, checks
  the package CLI and module entry points, and validates manifest identifiers.
  It does not download race reports or publish datasets.
- **Manual IMSA source smoke check** (`.github/workflows/extract.yml`) runs only
  on manual dispatch. It runs the test suite, then the historical
  `download.py` → `inspect_source.py` path for Road America. It does not run
  `run_pipeline.py` or archive results.

The complete dataset validation and publication described here remain local.
See the [CI guide](docs/ci.fr.md).

`data/`, virtual environments, and secret files are excluded from Git. Public
access to reports does not grant blanket permission to redistribute the data;
reuse terms still need checking before publishing data files. Code licensing
is a separate matter; no code license is announced here.

## Next milestone

Complete the classification data contract and document context, then extend
sources in verified batches. The common Gold participant layer is implemented;
the next step is to demonstrate its use from SQL or a notebook. Use by an AI
application remains unproven. Advanced orchestration, remote-change detection,
and Raw version archiving remain in the backlog. Local and cloud object-storage
experiments will use a separate scope with a defined budget.

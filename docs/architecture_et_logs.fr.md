# Architecture and logging

Refactoring dated November 13, 2026. It organizes responsibilities and runtime
messages; it does not integrate 2023 into the JSON run or extend season
coverage. The business SQL queries remain unchanged.

## Navigate the project by responsibility

The legacy commands at the root remain usable. Shared functions reside in
`src/moto_sport_bmw_pipeline`. Small ingestion and inspection scripts remain
at the root; importing them no longer triggers downloads or data reads.

| Need | Owning module | Legacy command or facade |
| --- | --- | --- |
| Coordinate the five JSON steps | `orchestration.py` | `run_pipeline.py` |
| Build and activate a JSON candidate | `pipeline.py` | `analyze_bronze.py` |
| Resolve project paths | `paths.py` | Shared by launchers |
| Download a Raw JSON file | `raw_download.py` | `download.py` |
| Check Raw hashes | `integrity.py` | `file_integrity.py` |
| Validate manifest identifiers | `manifest.py` | `manifest_validation.py` |
| Load Bronze data and metadata | `source_loading.py` | Functions re-exported by legacy scripts |
| Transform and validate Silver keys | `silver.py` | Legacy functions retained |
| Match sources, validate links and participants | `quality.py` | Called by the pipeline |
| Produce duration diagnostics | `duration_quality.py` | Called by the pipeline |
| Build enrichments and summaries | `marts.py` | Called by the pipeline |
| Declare and publish the twelve outputs | `publication.py` | Single `OUTPUT_VIEWS` registry |
| Validate and replace a Parquet file | `parquet_writer.py` | `silver_writer.py` |
| Activate or read a run reference | `run_reference.py` | `run_publication.py` |
| Identify PDF blocks and stops | `pdf_parser.py` | Re-exported by `explore_pit_stop_pdf.py` |
| Convert, validate and publish a CSV/PDF pair | `exploration.py` | `explore_pit_stop_pdf.py`, `explore_2023_season.py` |
| Display diagnostic tables | `diagnostics.py` | Enabled by `--verbose` |
| Configure logs and run context | `logging_config.py` | Configured at entry points |

Each Python module has a module-level docstring explaining its role.
SQL files remain in `sql/`, manifests in `config/`, test scenarios in `tests/`,
and local data ignored by Git in `data/`.
The facades avoid breaking existing imports during the transition;
new code should import directly from the owning module.

## Data flow

```text
run_pipeline.py
  ├── inspect_manifest.py → build_bronze.py
  ├── inspect_classification.py → build_classification_bronze.py
  └── analyze_bronze.py → pipeline.build_candidate_run
        loading → Silver → checks → marts → publication → activation

explore_2023_season.py
  exploratory catalog → pdf_parser → exploration → exploratory Parquet files
```

The required-output registry is shared by publication and activation.
A file can no longer be omitted because two lists diverge.
Blocking rules, NULL behavior and SQL formulas are preserved.
The old educational tables specific to one 2025 car have been replaced in the
main analysis by generic view previews in verbose mode.

## Operational logs

The old progress `print()` calls are replaced by `logging`. The `.show()` calls
remain for displaying actual tables, particularly in business-data readers.

| Level | Usage |
| --- | --- |
| INFO | Step start/end, sources loaded, row counts and files published |
| WARNING | Reported anomaly that does not block publication |
| ERROR | Step or candidate failure, with traceback |
| DEBUG | Hashes, temporary paths and exploration details |

Format: UTC timestamp, level, module, run identifier and message.
The identifier is `-` before a JSON candidate is created and during exploration.
Exploration event/session context appears in its messages and data.
Console logs go to stderr; tables go to stdout. An optional UTF-8 file is opened
in append mode. Configuring logging a second time does not duplicate application
handlers. Imports do not configure logging.

```bash
# Full JSON workflow, shared logging across the five processes
uv run python run_pipeline.py --log-file data/logs/pipeline.log

# Transformation/publication from existing Bronze data
uv run python analyze_bronze.py --log-file data/logs/analyze.log

# DEBUG details and tables, only when needed
uv run python analyze_bronze.py --verbose --log-file data/logs/analyze-debug.log

# Exploratory 2023 season, outside current.json
uv run python explore_2023_season.py --log-file data/logs/exploration-2023.log

# Equivalent JSON launcher entry points from this checkout
uv run moto-sport-bmw-pipeline --help
uv run python -m moto_sport_bmw_pipeline --help
```

The launcher passes `BMW_LOG_LEVEL` and, if requested, `BMW_LOG_FILE` to the steps.
Small scripts that do not expose these options can also inherit these variables.
This refactoring adds no cloud logging service, automatic rotation or log-file
concurrency mechanism.
The project remains validated from its checkout with `config/`, `sql/` and the
scripts present; standalone wheel distribution has not yet been demonstrated.

## Actual scope of fail-fast behavior

Existing checks detect the errors they express: invalid JSON, incorrect hashes,
invalid keys, ambiguous links, altered participant counts or different Parquet
content. This is not an exhaustive provider-schema contract. For example,
renaming an optional field may produce a NULL and a non-blocking anomaly;
an added field may remain in Bronze without being projected into Silver.

Before tackling 2026, assess the actual documents, then define required fields
and schema compatibility. Do not promise adaptation without code changes before
that assessment. Sporting hypotheses explaining a missing stop do not become
business rules without source evidence.

## Validation and interpreting tests

Legacy imports remain available. However, a mock must target the module that
actually uses the dependency: for example,
`moto_sport_bmw_pipeline.publication.publish_silver` rather than the old launcher.
Logging tests cover duplicate prevention, UTF-8 files, DEBUG level, run context
and forwarding options to processes. Reader imports are tested without
connections or downloads.

Results must be compared before/after using schemas and row differences in both
directions; a simple count does not prove equality.

Validation performed on November 13, 2026: 132 tests passed; the full five-step
JSON workflow was run from local Raw files; twelve outputs were compared exactly
with the reference run before refactoring (schema and EXCEPT ALL in both
directions). The eleven 2023 summaries were also regenerated and compared with
their references with exact equality. Quality and mart readers were run against
the same active run. Help commands for the console entry point and Python module
work. A clean installation and an initial network download were not rerun for
this change.

## Bronze construction for PDF stops

The `bronze.py` module builds Bronze Parquet files from fields extracted from
sources. Its first builder, `build_pdf_pit_stop_bronze`, reuses
`pdf_parser.extract_stops` and safe publication through `parquet_writer`.
It retains the seven fields of each stop along with the source identifier and
PDF hash, without converting durations. It does not run a season or activate a
run. This separation keeps writing out of the parser itself.

## Language and file descriptions

Maintained Python modules, tests and SQL queries have an English header
describing their role. Identifiers, technical comments and operational messages
are written in English. Public project documentation is now in English as well;
historical `.fr.md` filenames remain to preserve previously shared links.
Source values retain their language, and the logging test intentionally uses a
French message to check UTF-8 encoding. Draft copies not tracked by Git are
excluded from this harmonization.

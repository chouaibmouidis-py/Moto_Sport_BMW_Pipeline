# Code and execution map

#### Execution map

The repository map below covers the entry points, shared modules, configuration,
SQL, tests, workflows and generated data. The execution trees that follow trace
the calls made by the three build workflows.

```text
Moto_Sport_BMW_Pipeline/
├── Root Python scripts             CLI entry points, local exploration and compatibility imports
├── src/moto_sport_bmw_pipeline/     Shared Python implementation
├── config/
│   ├── sources.json                Enabled JSON sources and session identifiers
│   ├── exploration_2023.json       Per-event CSV/PDF paths and session context
│   └── README.fr.md                Configuration documentation
├── sql/                            Transformations, checks and exploration queries
├── tests/
│   ├── test_*.py                   Unit and local integration scenarios
│   └── fixtures/                   Small source examples used by tests
├── .github/workflows/              Code CI and manually triggered source smoke check
├── docs/                           Architecture, contracts, coverage and qualification notes
├── pyproject.toml                  Dependencies, package build and console command
├── uv.lock                         Locked dependency resolution
└── data/                           Locally generated inputs and outputs
    ├── raw/<source_id>/            Downloaded source and metadata.json
    ├── bronze/<source_id>/         Bronze Parquet files
    ├── runs/<run_id>/              Main JSON Silver, quality reports and marts
    ├── current.json                Active main-run reference
    ├── exploration/<event>-2023/   Per-event CSV/PDF Silver and marts
    └── gold/
        ├── runs/<run_id>/          Input snapshots, inputs.json and Gold tables
        └── current.json            Active Gold-run reference
```

#### Root scripts and their responsibilities

| File | Responsibility and main connection |
| --- | --- |
| [run_pipeline.py](../run_pipeline.py) | Calls `orchestration.main()` to launch the five JSON stages. |
| [inspect_manifest.py](../inspect_manifest.py) | Prepares enabled pit-stop Raw reports, verifies integrity, records metadata and logs volumes. Calls `download()`, `verify_local_file()` and the manufacturer counter. |
| [build_bronze.py](../build_bronze.py) | Verifies pit-stop Raw integrity and calls its local `build_document()` to publish and compare JSON roots in Bronze Parquet. |
| [inspect_classification.py](../inspect_classification.py) | Selects enabled classifications and calls its local `prepare_classification_raw()` to reuse or download each Raw report. |
| [build_classification_bronze.py](../build_classification_bronze.py) | Its CLI publishes classification JSON Bronze. Its `read_classification_csv()` and `build_classification_csv()` helpers serve the 2023 batch. |
| [analyze_bronze.py](../analyze_bronze.py) | Calls `pipeline.build_candidate_run()` for JSON Silver, quality reports, marts and activation. Re-exports historical helper imports. |
| [explore_2023_season.py](../explore_2023_season.py) | Coordinates the CSV/PDF classification, PDF Bronze, PDF Silver and mart batch modes, or direct source exploration. |
| [build_gold.py](../build_gold.py) | Calls `gold.build_gold_candidate()` for cross-season participants and an independent activation. |
| [inspect_marts.py](../inspect_marts.py) | Resolves the active main run and displays BMW mart results. |
| [inspect_quality.py](../inspect_quality.py) | Resolves the active main run and displays quality reports and flagged cases. |
| [inspect_source.py](../inspect_source.py) | Reads a local pit-stop JSON and displays source context and BMW entries. |
| [explore_bronze.py](../explore_bronze.py) | Reads a caller-selected Raw JSON into `raw_document` and executes a selected SQL file. |
| [explore_classification_csv.py](../explore_classification_csv.py) | Inspects a classification CSV and optionally a timing CSV. |
| [explore_pit_stop_pdf.py](../explore_pit_stop_pdf.py) | Calls `exploration.explore_source_pair()` with the Road America 2023 pilot context and caller-supplied PDF/CSV paths. |
| [analyze_classification.py](../analyze_classification.py) | Loads the Road America 2025 classification Bronze, applies the shared transformation and displays car 70. |
| [race_metrics.py](../race_metrics.py) | Defines the manufacturer-specific pit-stop counter used by Raw inspection. |
| [download.py](../download.py) | Re-exports `raw_download` helpers and calls its standalone `main()` when executed. |
| [file_integrity.py](../file_integrity.py) | Re-exports `integrity.verify_local_file()`. |
| [manifest_validation.py](../manifest_validation.py) | Re-exports the manifest identifier validator. |
| [silver_writer.py](../silver_writer.py) | Re-exports the shared Parquet publication helpers. |
| [run_publication.py](../run_publication.py) | Re-exports run activation and current-run resolution helpers. |

#### Shared implementation map

Paths in this table are relative to `src/moto_sport_bmw_pipeline/`.

| Module | Responsibility and connections |
| --- | --- |
| `__init__.py` | Exposes `main()` for the `moto-sport-bmw-pipeline` console command and delegates to `orchestration.main(None)`. |
| `__main__.py` | Calls the package `main()` for `python -m moto_sport_bmw_pipeline`. |
| `orchestration.py` | Validates manifest IDs and launches the five root scripts through `subprocess.run(check=True)`. |
| `manifest.py` | Rejects missing, non-string, blank and duplicate source IDs. |
| `raw_download.py` | Downloads JSON to a temporary file, parses it and replaces the final Raw file. |
| `integrity.py` | Compares a local file's SHA-256 with its recorded metadata. |
| `paths.py` | Defines shared project, SQL and data directory paths. |
| `logging_config.py` | Configures console/file logging and supplies the run-ID logging context. |
| `pdf_parser.py` | Extracts positioned PDF text blocks and parses stop rows with car context and source-location fields. Used by `bronze.py` and `exploration.py`. |
| `bronze.py` | Publishes extracted PDF stop rows to Bronze with source and PDF provenance. CSV and JSON Bronze builders also exist in the root scripts listed above. |
| `source_loading.py` | Selects source families and loads Bronze relations and source-session metadata into a DuckDB connection. |
| `queries.py` | Reads a SQL file, executes it and registers the resulting view through `build_view()`. |
| `silver.py` | Runs JSON, CSV and PDF Silver transformations and their key checks. |
| `quality.py` | Checks source pairing, entry links, classification/PDF/Gold keys and participant preservation, and builds session/duration quality views. |
| `duration_quality.py` | Builds duration comparison and quality views and logs their issues. Uses `queries.py` and `quality.py`. |
| `marts.py` | Builds driver-enriched stops, stop statistics, participant comparisons, manufacturer resolution and Gold participant views. Uses shared SQL and quality checks. |
| `pipeline.py` | Coordinates the main JSON candidate run and the per-event CSV Silver, PDF Silver and CSV/PDF mart publication helpers. |
| `exploration.py` | Coordinates direct PDF/CSV exploration, duration conversion, source hashes and pilot summaries. |
| `diagnostics.py` | Displays detailed main-run analysis tables when requested. |
| `parquet_writer.py` | Writes a temporary Parquet, validates the saved rows and content, then replaces the final path. Exposes `publish_parquet()` and its compatibility name `publish_silver`. |
| `publication.py` | Registers the main and Gold output paths/views and publishes those views through the shared writer. |
| `run_reference.py` | Checks required output presence, replaces `current.json` and resolves the active run for consumers. |
| `gold.py` | Snapshots input files and SQL, records and validates provenance, builds the common participant tables and activates the Gold run. |

The shared operations connect as follows. Arrows represent calls or use of the
named module's functions. Individual build paths use the operations appropriate
to their input family.

```text
pipeline.py / gold.py / explore_2023_season.py
    ├── source_loading.py → DuckDB input views and source-session context
    ├── silver.py → SQL transformations + quality.py key checks
    ├── marts.py → queries.py → sql/ → DuckDB result views
    │           └── quality.py → relationship and participant checks
    ├── duration_quality.py → queries.py + quality.py
    └── publication.py → parquet_writer.py → validated Parquet files

pipeline.build_candidate_run() / gold.build_gold_candidate()
    └── run_reference.activate_run() → current.json

CSV/PDF exploration and Bronze
    ├── build_classification_bronze.py → read_classification_csv()
    ├── bronze.py → pdf_parser.py → extracted stop records
    └── exploration.py → pdf_parser.py + DuckDB → exploratory summaries

Cross-cutting support
    ├── paths.py → project-relative locations
    ├── logging_config.py → logging configuration and run context
    └── diagnostics.py → detailed analysis tables
```

#### SQL map

The prefixes identify files in `sql/`. Runtime callers determine execution order.
For example, manufacturer evidence query 37 runs before reference query 36.

| Files | Purpose | Main caller |
| --- | --- | --- |
| `01_inspect_raw.sql`, `02_test_duration_parser`, `03_profile_cars.sql`, `04_test_text_cleaning.sql`, `05_test_duration_coverage.sql` | Source inspection and early SQL experiments. File 02 retains its historical extensionless name. | Local exploration, including `explore_bronze.py --sql`. |
| `06_pit_stop_summary.sql` | Duration counts, averages and coverage grouped by source, version and car. | `marts.build_pit_stop_summary()`. |
| `07_silver_pit_stops.sql` | JSON pit-stop extraction and conversion. | `silver.transform_pit_stops()`. |
| `08_check_missing_pit_stop_keys.sql`, `09_check_duplicate_pit_stop_keys.sql` | Pit-stop key checks. | `silver.transform_pit_stops()`. |
| `10_silver_car_entries.sql` | JSON car-entry extraction. | `silver.transform_car_entries()`. |
| `11_check_missing_car_entry_keys.sql`, `12_check_duplicate_car_entry_keys.sql` | Car-entry key checks. | `silver.transform_car_entries()`. |
| `13_check_matched_pit_stops.sql` | Pit-stop to car-entry matching count. | `quality.validate_entry_links()`. |
| `14_silver_driver_entries.sql`, `15_check_driver_entry_keys.sql` | Driver extraction and key checks. | `silver.transform_driver_entries()`. |
| `16_silver_sessions.sql`, `17_check_session_keys.sql` | Session transformation and key checks. | `silver.transform_sessions()`. |
| `18_session_quality_summary.sql` | Session-field quality summary. | `quality.build_session_quality()`. |
| `19_check_pit_stop_driver_links.sql`, `20_enriched_pit_stops.sql` | Driver-link diagnostics and driver-enriched stops. | `marts.build_enriched_stops()`. |
| `21_create_duration_parser.sql` | Shared SQL duration-parsing macro. | JSON candidate and PDF conversion workflows. |
| `22_check_missing_total_pit_durations.sql`, `23_total_pit_duration_quality.sql`, `24_compare_total_pit_durations.sql` | Unconverted cumulative durations, quality counts and comparison with summed stop durations. | `duration_quality.py` and `quality.build_total_duration_quality()`. |
| `25_silver_classification.sql`, `26_check_missing_classification_keys.sql`, `27_check_duplicate_classification_keys.sql` | JSON classification transformation and key checks. | `silver.transform_classification()`. |
| `28_pit_stop_counts_by_car.sql` | Stop counts grouped by source, version and car. | `marts.build_pit_stop_counts()`. |
| `29_classification_pit_stop_sources.sql` | Classification/stop source pairing using session context. | `quality.build_source_pairs()`. |
| `30_classification_pit_stop_comparison.sql`, `31_race_car_summary.sql`, `32_classification_count_quality.sql` | JSON participant comparison, enriched summary and mismatch counts/percentages. | `marts.build_classification_marts()`. |
| `33_silver_classification_csv.sql`, `34_silver_pdf_pit_stops.sql` | CSV classification and PDF stop Silver transformations. | Corresponding functions in `silver.py`. |
| `35_csv_pdf_race_summary.sql` | CSV/PDF participant summary with paired provenance and stop statistics. | `marts.build_csv_pdf_race_summary()`. |
| `37_manufacturer_reference_input.sql`, `36_manufacturer_reference.sql` | Explicit manufacturer evidence followed by name-resolution status. | `marts.build_manufacturer_reference()`. |
| `38_enrich_2023_manufacturers.sql` | Manufacturer enrichment for 2023 participants. | `marts.enrich_2023_manufacturers()`. |
| `39_gold_race_car_summary.sql` | Explicit compatible-column union of season participant tables. | `marts.build_gold_race_car_summary()`. |

#### Tests, workflows and documentation

```text
tests/test_*.py
├── Raw and configuration
│   └── Download failures, hashes, source selection and manifest identifiers
├── Bronze and extraction
│   └── JSON/CSV preservation, PDF parsing, provenance and batch processing
├── Silver and quality
│   └── Conversion, NULL handling, keys, source/version separation and links
├── Marts and Gold
│   └── Participant preservation, stop comparisons and manufacturer resolution
├── Publication
│   └── Saved-content checks, previous-file preservation and run activation
└── Entry points and integration
    └── Import behavior, subprocess stopping, logging, batches and Gold snapshots

.github/workflows/
├── Code CI → locked dependencies → tests → entry-point and manifest checks
└── Manual source smoke check → tests → historical download → source inspection

docs/
├── architecture_et_logs.fr.md → module organization and logging
├── gold.fr.md / gold_contract.fr.md → Gold publication and schema contract
├── coverage_plan.fr.md / source_inventory.fr.md → scope and source inventory
├── imsa_*_season_coverage.fr.md → per-season coverage observations
├── qualification_*.fr.md → dated source qualification evidence
├── ci.fr.md → workflow behavior
└── mission_stage_personnel.fr.md → original project assignment
```

`tests/fixtures/` supplies test inputs. Each `test_*.py` groups scenarios for the
component named in the filename. The test suite runs through `unittest discover`.
Generated files under `data/` and local communication drafts are covered by the
repository's ignore rules. `.gitignore` defines those exclusions.

The JSON workflow launches five scripts sequentially. Each script runs in its
own Python process. The nested entries below show function calls within a script.

```text
run_pipeline.py
└── orchestration.main()
    ├── validate_unique_source_ids()
    └── subprocess.run() for each stage, in this order
        ├── 1. inspect_manifest.py → main()
        │   ├── verify_local_file() or download()
        │   └── count_manufacturer_pit_stops()
        ├── 2. build_bronze.py → main()
        │   ├── verify_local_file()
        │   └── build_document()
        ├── 3. inspect_classification.py → main()
        │   ├── select_classification_sources()
        │   └── prepare_classification_raw()
        │       └── verify_local_file() or download()
        ├── 4. build_classification_bronze.py → main()
        │   ├── select_classification_sources()
        │   ├── verify_local_file()
        │   └── build_classification_document()
        └── 5. analyze_bronze.py → main()
            └── pipeline.build_candidate_run()
                ├── Load Bronze and source-session metadata
                ├── Transform and validate Silver
                ├── Build quality reports and marts
                ├── publish_run_outputs()
                └── activate_run() → data/current.json
```

The 2023 CSV/PDF batch has a separate entry point. Each selected mode performs
one stage using `config/exploration_2023.json`. Run the modes in dependency order
to produce the per-event marts consumed by Gold.

```text
explore_2023_season.py → main()
├── --classification-only → build_classification_batch() → CSV Bronze and Silver
├── --pdf-bronze-only     → build_pdf_bronze_batch()     → PDF Bronze
├── --pdf-silver-only     → build_pdf_silver_batch()     → PDF Silver
├── --mart-only           → build_mart_batch()          → per-event CSV/PDF marts
└── No mode flag          → explore_source_pair()       → source exploration
```

The Gold entry point consumes the active JSON participant mart, the 2023
per-event marts, and Bronze evidence for manufacturer resolution.

```text
build_gold.py → main()
└── gold.build_gold_candidate()
    ├── get_current_run() → resolve data/current.json once
    ├── Snapshot configuration, SQL and input Parquet files
    ├── Write and validate inputs.json
    ├── Build the manufacturer reference from Bronze evidence
    ├── Enrich 2023 participants and assemble the common Gold schema
    ├── Publish and validate Gold outputs
    └── activate_run() → data/gold/current.json

inspect_marts.py / inspect_quality.py
└── get_current_run() → data/current.json → active main-run Parquet files
```

In Python, defining a function makes it available to call. Execution enters its
body when a caller invokes it. For example, `prepare_classification_raw()` is
defined and called in `inspect_classification.py`; both Raw preparation scripts
reuse the shared `download()` and `verify_local_file()` functions.

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

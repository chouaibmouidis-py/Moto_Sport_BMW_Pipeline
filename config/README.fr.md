# Source manifest

`sources.json` is an initial inventory, not the complete list of BMW races.
It is read by inspection, Bronze construction and analysis scripts.
They select enabled documents (`enabled: true`) by family:
`pit_stops` for stops, `classification` for classifications.
The eleven WeatherTech 2024 races and the eleven 2025 races have passed through
the local JSON pipeline for classifications and stops: 44 enabled documents.
The 2023 CSV/PDF exploration is described in `exploration_2023.json` and remains
separate from the active manifest and run.
The manifest alone triggers nothing: downloads are performed by
`inspect_manifest.py` and `inspect_classification.py`, directly or through
`run_pipeline.py`.

Classifications must provide `filename`, for example
`03_Results_Race_Official.JSON`. The downloader receives this name explicitly.
The stop workflow retains its legacy default filename.
`pipeline_status` describes the assessment status; it is not used to exclude
an already tested document from subsequent runs.

Matching associates documents on `championship`, `season`, `event_id`
and `session_id`; `source_id` remains specific to each document. A classification
without a compatible stop report, or with several candidates, is rejected.
The shared loader accepts multiple classifications and retains each one's
identifier and Bronze hash before matching.

Seasons are a coverage target, not evidence of ingestion.
`documents` references specific files. `catalogs_to_explore` contains portals to
explore and must not be treated as a list of JSON files to read.
Other candidate championships remain listed in
`../docs/coverage_plan.fr.md`.

The `session_id` comes from the source folder label. It does not prove a UTC
timestamp. `publication_status` remains `unspecified` when the report name does
not explicitly carry a status. Hour 24 denotes an hourly report, not an
additional race.

`source_id` is the logical identity chosen for a report. Ingestion records the
download date and SHA-256 hash in the `metadata.json` file beside the Raw
document. A refresh replaces these files; this is not immutable archiving of
revisions published at the same URL.
The `as_of_date` is the date of this inventory, not the retrieval date of each
file. Silver results separately retain the hash of the Bronze file used.

Before starting its steps, `run_pipeline.py` checks `source_id` values throughout
the `documents` list, including disabled entries. Each identifier must be
present, non-null, a string, nonempty and not composed solely of whitespace.
An invalid value raises a `ValueError` indicating the document's position in the
list (zero-based index) and the reason for rejection.
Duplicates are also rejected with a message naming the identifier.
The validator does not modify values or check report contents.
These errors prevent the scripts from starting.
Running these scripts individually does not automatically invoke this launcher
check.
Full validation of required fields and permitted formats remains to be added.
Pipeline data checks are separate from the descriptive statuses recorded in
this file.

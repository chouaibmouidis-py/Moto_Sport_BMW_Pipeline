# Source configuration

`sources.json` is the single production source inventory for JSON, CSV and PDF.
`enabled: true` controls selection; descriptive inspection and pipeline statuses
do not trigger processing. `target_seasons` is a coverage goal, not achieved coverage.

Each enabled document declares its source ID, URL, filename, format, document type,
championship, season, event ID and session ID. Reports are paired by championship,
season, event and session. Missing or ambiguous pairs are rejected. Identifiers
must be nonempty strings and unique, including disabled documents. Source IDs and
filenames may not escape their directories.

Supported readers currently cover classification JSON/CSV and pit-stop JSON/PDF.
The qualified pairings are JSON + JSON and CSV + PDF. Unsupported combinations
are rejected explicitly rather than guessed. The parser validates structure;
normalization and business consistency belong to Silver and quality controls.

The current enabled scope is 44 JSON reports for 2024–2025 and 22 CSV/PDF reports
for 2023. Daytona 2022 remains disabled until its integration is qualified.
The previous season-specific catalog is retired. URLs, filenames and source
context for 2023 have been migrated into this manifest.

Raw JSON versions are verified against their `metadata.json` sidecars. Migrated
CSV/PDF sources carry `expected_sha256`, pinning the previously qualified local
bytes also held in the remote archive. A changed upstream report must be reviewed
before updating that fingerprint. Cached data are validated without redownload;
`--refresh` explicitly requests acquisition. Refresh is not immutable revision
archiving. No secret belongs in this file.

```bash
uv run python run_pipeline.py
uv run python run_pipeline.py --season 2023 --event daytona
uv run python run_pipeline.py --stage raw
```

These commands use the same orchestrator. Omitting selection processes every
enabled race. Selecting a season/event builds a correspondingly scoped Gold,
rather than adding rows to the previous run. The `gold` stage requires the same
selection as the active processing run.

`source_archive.json` is the pinned remote archive reference, not a competing
source inventory. `catalogs_to_explore` contains discovery portals, not inputs
to ingest automatically. Changes to source coverage also require updating the
remote source archive before relying on a clean cloud runner.

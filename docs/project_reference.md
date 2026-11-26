# Detailed project reference

Current implementation and delivery status, reviewed on 24 November 2026.
The [assignment](mission_stage_personnel.fr.md) defines the business objective;
this document describes the implemented pipeline. Annual qualification reports
retain their original measurements and dates rather than defining current runtime.

## Coverage and delivery state

| Season | Formats | Participations | BMW |
| --- | --- | ---: | ---: |
| 2022 — Daytona only | Classification CSV / stops PDF | 61 | 3 |
| 2023 — eleven races | Classification CSV / stops PDF | 455 | 51 |
| 2024 — eleven races | Classification / stops JSON | 468 | 38 |
| 2025 — eleven races | Classification / stops JSON | 469 | 48 |
| Local total — 34 races | Both report pairings | 1,453 | 140 |

Local Gold has 45 columns. Daytona 2022 contributes 1,762 extracted stops;
2023 contributes 3,953 PDF stops and 2024–2025 contributes 8,307 JSON stops.
Gold currently publishes participation summaries, not a common table of all
individual stops. These volumes qualify the selected documents, not every race
or every BMW activity worldwide.

The [hosted dashboard](https://bmw-imsa-analytics.streamlit.app/) includes the
Daytona 2022 extension, confirmed by the maintainer after publication. The remote
archive contains 114 verified files. The additive migration preserved the previous
publication during preparation; the later data publication exposed the expanded
schema. Subsequent case-handling and rollback-diagnostic fixes belong to a separate
maintenance lot, whose local tests do not establish remote deployment.

## Execution order

```bash
uv sync --locked
uv run --locked --no-sync python -m pytest -v
uv run --locked --no-sync python run_pipeline.py --log-file data/logs/pipeline.log
```

`config/sources.json` is the only production source inventory. Selection validates
IDs and pairs reports by championship, season, event and session. Supported pairs
are JSON/JSON and CSV/PDF; unsupported or ambiguous pairs fail explicitly.

1. **Raw:** verify cached bytes and their declared fingerprint or metadata, then
   validate the expected format. Download only when required or explicitly refreshed.
2. **Bronze:** extract the selected report into a versioned Parquet representation.
   JSON roots, CSV fields and PDF stop records have different extraction schemas.
   PDF extraction retains the source PDF hash and page/column/line locations;
   it does not preserve every visual element as a table.
3. **Processing:** load Bronze, normalize into Silver, check keys and relationships,
   produce quality reports and participant marts. Complete all selected report
   outputs before activating `data/processing/current.json`.
4. **Gold:** read that processing run, snapshot its manifest, output descriptor,
   SQL 36–39, declared marts, quality reports and JSON Silver manufacturer evidence.
   Verify copied inputs, combine participants, write/read-back outputs, then
   activate `data/gold/current.json` after all required checks succeed.

Airflow invokes the same four stages after archive restoration, then runs the
separate MotherDuck publisher. It does not invoke historical inspection scripts.
The [code map](code_map.md) identifies each responsibility and its owning module.

```bash
uv run --locked --no-sync python run_pipeline.py --stage process
uv run --locked --no-sync python run_pipeline.py --stage gold
uv run --locked --no-sync python run_pipeline.py --season 2022 --event daytona
```

A focused selection replaces the coverage of the resulting local run; it does
not append to an older Gold. The Gold stage requires the selection of its active
processing input. Rebuild processing after transformation/schema changes before
building Gold. `--refresh` deliberately reacquires sources; it does not preserve
an immutable history of every Raw revision.

## Responsibilities and active paths

| Layer / responsibility | Content and boundary |
| --- | --- |
| Raw | Source document and provenance metadata or declared hash. Identity checks do not prove sporting accuracy. |
| Bronze | Format-specific extraction with provenance; source values are retained. |
| Silver | Normalize identifiers, strings, numeric types, durations and gaps; apply explicit known corrections. |
| Quality | Reject structural/key/relationship violations; retain report discrepancies as signals where allowed. |
| Marts | Aggregate stop counts and durations and preserve classification participants without multiplying joins. |
| Gold | Align checked marts and enrich from Silver evidence; never reload Bronze to redo manufacturer normalization. |
| Publication | Verify saved content and activate the complete candidate; database publication and share provisioning are separate. |

```text
data/raw/<source_id>/<filename>                  Cached source
data/bronze/<source_id>/document.parquet         Bronze extraction
data/runs/<run_id>/                             JSON adapter outputs
data/processing/runs/<run_id>/sources.json       Selected report configuration
data/processing/runs/<run_id>/outputs.json       Declared outputs and hashes
data/processing/runs/<run_id>/reports/<source>/  CSV/PDF Silver, quality and mart
data/processing/current.json                    Complete processing reference
data/gold/runs/<run_id>/                         Gold files, inputs.json and copies
data/gold/current.json                          Complete Gold reference
```

The JSON adapter is built without replacing the legacy `data/current.json` in
the shared production path. Legacy diagnostic readers may still follow that
reference; they do not establish the current common Gold coverage. Read the Gold
reference once and use that run directory rather than globbing across histories.

## Analytical contract

The participation grain is (`source_id`, `bronze_sha256`, `car_number`). Car numbers
remain text, including leading zeros. The source-entry index is a position within
a document version, not a permanent identity across reports.

The 45-column Gold groups:

- Championship, season, event, session and overall position/class/status.
- Classification and pit-stop source IDs, Bronze hashes, PDF hash and entry index.
- Model, manufacturer ID, resolved name, origin and mapping/evidence status.
- Reported and observed stop counts, valid/invalid durations, mean and coverage.
- Team, completed laps, fastest-lap number and speed.
- Total and fastest-lap raw durations with seconds.
- Raw gaps to first/previous, each with kind, seconds and laps columns.

Missing values remain NULL. A missing observed count does not establish zero
stops. CSV textual status is not inferred into `not_finished`. Unknown duration
and gap formats retain their raw values; a time gap and a lap gap use distinct
numeric columns. The common duration macro handles supported numeric forms;
clock passage differences still assume a stop under 24 hours.

For exact normalized CSV models, Silver maps `Mercedes-AMG GT3` to `Mercedes`
and `Duqueine D08` to `Duqueine`, with `matched_override`. Gold retains the
correction and reports origin `silver_override`. Other CSV names use explicit
ID/name evidence from JSON Silver. Reference ambiguities remain visible; no
partial-model guessing is used. JSON names retain source origin. Later-season
reference evidence is not proof of information available before an earlier race.

Reported/observed count differences are nonblocking signals. A stop linked to a
car absent from its paired classification is a blocking relationship violation.
Participants without detail remain present. Duration means describe observed
report values, not mechanics' performance in isolation. Cross-race comparisons
require context such as class and event duration.

## Publication and diagnostics

Each Parquet candidate is reread and compared using counts and EXCEPT ALL before
replacing its target. Processing and Gold references change only after their
required outputs succeed. Failed candidate directories can remain for diagnosis;
cleanup, retention and concurrent readers/writers need separate operational rules.
Filesystem reference replacement is not a multi-file database transaction.

MotherDuck inserts the candidate into `gold_history`, validates counts and
content, updates `current_gold_run` and rebuilds the public view in one transaction.
Its rollback preserves the previous run. The saved projection is explicitly
ordered like the candidate because ALTER TABLE and INSERT BY NAME can leave
physical columns in a different order. `configure_motherduck_share.py` provisions
sharing independently; it is not part of each publication.

`archive_sources.py --pin` renews and verifies the remote archive before updating
its local pin. `migrate_motherduck_schema.py` inspects by default; `--apply` adds
only the 16 known sporting columns, checking historical values and preserving
the current public projection and run. Neither operation publishes the new Gold.
See [CI and deployment](ci.fr.md) and [Gold publication](gold.fr.md).

Logs include module, run, stage and source where applicable. Aggregate operations
use `source_id=-` instead of claiming one report. Nested contexts restore previous
values on completion or failure. SQL errors identify the query file and view;
exceptions propagate to the caller. See [architecture and logs](architecture_et_logs.fr.md).

## Validation and limits

Schema migration currently materializes historical and visible rows in Python
with fetchall and Counter. This preserves occurrence-sensitive comparisons but
scales client memory and data transfer with the history size. No large-history
benchmark is established. An engine-side exact-comparison milestone is recorded
in [Gold operations](gold.fr.md#migration-memory-limit-and-planned-optimization);
it is planned, not deployed, and must preserve the current content contract.

Source archival now reads each source once and uses the validated bytes for its
archive payload. Metadata-backed sources also retain the exact metadata bytes
used to obtain the expected hash. See the [single-read archive contract](gold.fr.md#archive-repeated-reads-and-planned-single-read-validation).
Payloads are prepared, inserted, read-back verified and released file by file in
one transaction. Only lightweight inventory records accumulate. Tests cover
incremental insertion, later-file rollback and a warmed Python allocation guard
with a deliberate payload-retention control. Native/driver/transaction memory,
cold-start RSS and individually oversized files remain separate limits; this is
not a total-process memory bound or a live MotherDuck benchmark.

Restoration now reads only paths and hashes into its inventory. It checks the
inventory count and all destination paths before fetching one payload at a time.
Each payload is validated and written to a unique neighboring temporary file,
then reread and released from Python before the next payload is fetched. Only
paths remain across files. Final replacements start after every file is prepared.
An invalid second file preserves both existing destinations and staged temporaries
are removed. Replacement-time failures can leave mixed final versions; there is
no global filesystem transaction. Temporary disk usage grows with the staged
archive size. See the [restoration contract](gold.fr.md#file-by-file-source-restoration).

The latest local pytest run on 26 November 2026 has 334 passing tests and 97 passing subtests.
Earlier parametrization exposed former inner cases separately; restoration adds
new behavioral coverage. Synthetic and temporary-file tests
cover conversions, keys, relationships, row preservation, input mutation,
publication failure, context restoration, additive schema migration, archive
pinning and progressive restoration. They establish only the behaviors asserted
by those scenarios. File-by-file transfer is not end-to-end micro-batching of
Bronze, Silver and Gold.

The complete real local rebuild produced 1,453 participants and 140 BMW across
45 columns. Comparison in both directions with EXCEPT ALL retained the previous
1,392 rows' shared fields, excluding the three intentionally corrected manufacturer
fields. The 114-file remote archive was restored into a temporary directory and
its reports compared with local Raw. The remote schema migration preserved the
previous public rows, column projection and active run.

Unqualified behavior includes concurrent deployment, hardware-crash recovery,
automatic remote revision detection, completeness of all PDF observations and
worldwide coverage. Input copies do not archive the Python implementation or
runtime; preserve the code revision and locked environment for reproduction.
Durations use DOUBLE and quality comparisons use explicit tolerances. No timezone
is assigned when the source does not establish it.

## Remaining work and historical evidence

The recent implementation review is complete. Close its maintenance lot with a
final diff and test check, local commit, authorized push and CI. Data publication
is a separate workflow when rebuilding/publishing is required. The next development
milestone follows the documented test-first workflow.
A dbt-duckdb pilot and streaming hashes remain planned. The pytest migration is complete locally: all non-empty test modules use native
functions and explicit fixtures; existing scenarios and assertions are retained. See the
[pytest migration guide](pytest_migration.md).

Historical source qualifications:
[2023](imsa_2023_season_coverage.fr.md),
[2024](imsa_2024_season_coverage.fr.md),
[2025](imsa_2025_season_coverage.fr.md), and
[Daytona 2022](qualification_daytona_2022.fr.md).
The [coverage research plan](coverage_plan.fr.md) is a wider objective, not a
promise that all listed sources are supported. Public access does not establish
redistribution rights. Code licensing is a separate question.

# Exploratory IMSA WeatherTech 2023 coverage

Exploratory qualification and publication carried out on November 13, 2026.
[Official schedule](https://www.imsa.com/weathertech/weathertech-2023-schedule/).
[Results index](https://imsa.results.alkamelcloud.com/Results/23_2023/).

The eleven Official classification CSV / pit-stop PDF pairs are described in
`config/exploration_2023.json`. The 22 files were retained locally
in `data/raw` after downloading and checking that the copies were identical.
This catalog is independent of `config/sources.json`: no 2023 source
is enabled in the main pipeline.

> Current-status clarification: the separate three-season Gold now includes the
> 2023 CSV/PDF marts alongside the 2024–2025 JSON inputs. Statements below that
> these summaries are not yet integrated into Gold describe an earlier stage
> and are stale as current claims. The 2023 catalog remains separate from the
> main JSON run. See [the Gold documentation](gold.fr.md).

| Race | Session | Scope | Classification entries | BMW | Extracted stops | BMW stops |
| --- | --- | --- | ---: | ---: | ---: | ---: |
| Daytona | 202301281340-race | Hour 24 | 61 | 5 | 1 631 | 140 |
| Sebring | 202303181010-race | Hour 12 | 53 | 5 | 733 | 59 |
| Long Beach | 202304151405-race | Session | 28 | 5 | 28 | 6 |
| Laguna Seca | 202305141210-race | Session | 38 | 5 | 124 | 14 |
| Watkins Glen | 202306251040-race | Hour 6 | 57 | 5 | 383 | 29 |
| Canadian Tire | 202307091205-race | Session | 34 | 5 | 96 | 15 |
| Lime Rock | 202307221210-race | Session | 20 | 3 | 45 | 8 |
| Road America | 202308061010-race | Session | 45 | 5 | 116 | 9 |
| VIR | 202308271410-race | Session | 19 | 3 | 46 | 6 |
| Indianapolis | 202309171310-race | Session | 48 | 5 | 126 | 14 |
| Road Atlanta | 202310141140-race | Hour 10 | 52 | 5 | 625 | 67 |
| **Total** | | | **455** | **51** | **3 953** | **367** |

Long Beach includes two Not started entries (80 and 93), with NULL positions.
The term “classification entries” includes these non-starters; it does not mean
455 cars that actually started the race.

## Checks performed

- No duplicate car/stop-number pairs or stops without a matching participant
  were found; stop sequences were checked.
- For the nine new PDFs, coordinate-based extraction was compared with
  text reading without spatial restrictions: the lists were identical.
  Both readings share the recognition rules; this is not an
  independent validation of every visual row.
- The eleven summaries were published through `publish_silver`, checking the
  row count and the content read back. Each summary contains the race
  context, status, and both source hashes.
- Full suite: 127 tests passed. One test checks two publications with
  separate contexts and directories to prevent reuse of the
  Road America context for another race.

Missing details in the extraction: Long Beach 01/80/93; Laguna Seca 94;
Watkins Glen 51/24; Lime Rock 91/94; Road America 57; VIR 92; Indianapolis 93.
Counts remain NULL. For the newly identified missing details, visual absence
from the PDF still needs confirmation: do not interpret them as zero stops.

## Usage

```bash
uv run python explore_2023_season.py
```

The launcher checks that the local batch is present, then calls `explore_source_pair`
for each race. Outputs go to
`data/exploration/<event_id>-2023/car_summary.parquet`. The catalog retains
the official URLs, but the launcher does not download missing files.
The PDF reader remains tied to the observed layout, with no guarantee for
new formats. The individual script retains Road America as its exploration
context; use the catalog for the other races.

## Integration limits

This coverage remains **outside the active 2024–2025 run** and its readers.
The classifications have a separate Bronze/Silver path described below; the
CSV/PDF summaries are not yet integrated into its Gold outputs.
The CSVs do not provide an
independent reported count; the JSON pipeline's count_mismatch assessments
are therefore not carried over. Driver names, entry/exit times, and cumulative
PDF totals are not yet exposed by this reader.

> Historical integration limit: the “not yet integrated” Gold statement above
> predates the separate 2023–2025 Gold. It remains relevant to the main JSON
> run's readers, but does not describe current cross-season Gold coverage.

The eleven publications are checked file by file, without atomic activation
of the exploratory set: a late failure can leave a batch
partially updated. `data/current.json` is never modified.
The hashes identify the versions read; the catalog context is
declarative, not an automatic check of which race the PDF contains.

## Common structure of stops extracted from PDFs

All calls to `extract_stops` return a list of dictionaries with
the same seven fields: `car_number`, `pit_number`, `pit_time_raw`,
`page_number`, `column_number`, `block_line_number`, and `source_line`.
Variants returning only three values and car filters
hardcoded in the parser have been removed. Business filtering belongs in the readers.

`extract_stop_blocks` organizes fragments into pages/columns;
`parse_stop_blocks` is the sole logic for recognizing cars and stops.
`convert_extracted_stops` retains the seven fields and adds `pit_time_seconds`.
Text-only tests without a document may use NULL page/column markers;
extraction from an actual PDF provides numbers starting at 1.

`block_line_number` counts retained lines in the extracted block, not visual
lines in the PDF. `source_line` is the text supplied by extraction, after
selection and trimming of surrounding whitespace; it does not replace
the Raw PDF. This common schema does not make the reading coordinates universal.
The `build_pdf_pit_stop_bronze` builder in `bronze.py` publishes these seven
fields with `source_id` and `pdf_sha256`, making nine columns. The Raw PDF remains
the reference; Bronze retains the fields selected by the extractor, not
the document's entire content. Durations remain textual.

The Road America pilot is published in
`data/bronze/imsa-2023-road-america-race-pit-stops/document.parquet`: 116 stops,
markers and provenance read back and compared with the extraction. The PDF hash
is separate from the Bronze Parquet hash, which will be computed when it is loaded.
The builder rejects a source modified during extraction; a parser or write
error preserves any previous output.
An empty extraction produces an empty typed schema without inventing a stop;
this does not prove that an unfamiliar PDF has been interpreted correctly.

All eleven races now have PDF Bronze and Silver outputs. Loading
adds `bronze_sha256`, then `34_silver_pdf_pit_stops.sql` adds
`pit_time_in_seconds` by reusing the existing duration macro.
The shared quality check rejects missing provenance or a repeated key
(`source_id`, `bronze_sha256`, `car_number`, `pit_number`).

The pilot Silver is saved in
`data/exploration/road-america-2023/silver/pit_stops.parquet`: 116 rows,
eleven columns, no unconverted durations. The Bronze fields and their markers
were compared with the output; schemas and content were checked after
publication. Batch processing is available through two exclusive modes:

```bash
uv run python explore_2023_season.py --pdf-bronze-only
uv run python explore_2023_season.py --pdf-silver-only
```

The first builds the eleven Bronze outputs from the local Raw PDFs; the second
builds the Silver outputs from the existing Bronze outputs. Output verification:
3 953 stops, including 367 BMW stops, zero unconverted durations. Extracted fields
and markers are identical between Bronze and Silver; PDF and Bronze hashes
match the local files. No orphan stops were detected against
the corresponding Silver classifications. The active reference remains unchanged.

The `--classification-only`, `--pdf-bronze-only`, and `--pdf-silver-only` modes
are mutually exclusive. Input presence is checked before each
batch, but a late content error can leave earlier outputs
updated: no atomic season activation is provided.

The eight PDF Bronze/Silver batch tests pass. After correcting the stray block
in silver_writer.py and strengthening the Silver scenario with two
races, Chouaib confirms 170 tests passed in the full suite.

## Mart reconciliation for the eleven races

```bash
uv run python explore_2023_season.py --mart-only
```

This exclusive mode uses the two Silver outputs already published for each race and
calls `publish_csv_pdf_race_summary` with that race's context only.
It checks all paths and rejects duplicate identifiers before
publishing to `data/exploration/<event_id>-2023/marts/race_car_summary.parquet`.
It does not reread Raw inputs or rebuild Bronze or Silver.

Validation across the eleven outputs: 455 entries, including 51 BMW entries,
3 953 observed stops, including 367 BMW stops. Participant keys are identical to
those in the Silver classifications (EXCEPT ALL in both directions). Sessions
and CSV/PDF versions match the inputs; Silver outputs and `data/current.json`
are unchanged. Full suite: 173 tests passed.

Eleven entries are retained without stop details, with an observed count of
NULL: Long Beach (01, 80, 93), Laguna Seca (94), Watkins Glen (24, 51), Lime
Rock (91, 94), Road America (57), VIR (92), and Indianapolis (93).
This absence establishes neither zero stops nor a sporting explanation.

All reported counts remain NULL; `comparison_status` is
`unavailable_reported_count`. The independent `stop_detail_status` field
distinguishes `available` from `no_stop_details`.

Three batch tests check separation of two races with the same
car, rejection of a missing input before publication, and preservation
of a previous mart if a Silver output from another source is placed in the wrong
directory. Publication remains individual: a late error can leave
earlier races updated. The batch is not activated atomically and
is not integrated into the main run's readers.

### Road America pilot history

The pilot summary is published in
`data/exploration/road-america-2023/marts/race_car_summary.parquet`: 45
entries retained, 116 stops found, car 57 retained with
an observed count of NULL. Reported counts remain NULL and the status is
`unavailable_reported_count`; `stop_detail_status` distinguishes available
details from their absence. CSV and PDF versions are retained separately.

`build_pit_stop_counts` populates a shared `pit_stop_count_input` view to
reuse SQL 28 for both formats. `build_csv_pdf_race_summary` reuses
SQL 29 matching, rejects multiple versions of the same source and
stops without a matching participant, then applies the LEFT JOIN from SQL 35.
The same car in two sessions does not mix their counts.

Validation: 158 tests passed; shared counts checked against the 8 307 active
JSON stops, Silver inputs and active reference unchanged during the pilot.
This pilot has now been generalized through `build_mart_batch` without duplicating
the SQL logic; the PDF reading limits described above still apply.

## CSV classifications: separate Bronze/Silver path

```bash
uv run python explore_2023_season.py --classification-only
```

This option reads the eleven `classification_path` values from the existing catalog,
without rereading the PDFs. It checks all paths before publication and rejects
duplicate race or source identifiers. The source identifier uses
the Raw directory name, consistent with the existing directories.

For each race:

1. The CSV is read as text (`;`, header, missing trailing fields filled
   with NULL), without cleaning Bronze values.
2. The Bronze Parquet is published to `data/bronze/<source_id>/document.parquet`.
3. Loading adds `source_id` and the SHA-256 hash of the Bronze Parquet.
4. Missing or duplicate numbers after cleaning block transformation.
5. The `33_silver_classification_csv.sql` query normalizes five fields.
6. The seven Silver columns are published and read back with content checks in
   `data/exploration/<event_id>-2023/silver/classification.parquet`.

Validation on the eleven actual classifications: 455 entries, including 51 BMW entries;
only the positions of 80 and 93 at Long Beach are NULL (`Not started`).
Bronze schemas and content were compared with the CSV readings in both
directions using EXCEPT ALL. Silver volumes and provenance were checked for
each race, with no missing or duplicate numbers. The Raw CSVs and the
`data/current.json` reference remained unchanged.

This command publishes files individually: a late failure can
leave outputs from earlier races updated. It provides neither
atomic season activation nor integration into the main run's outputs.

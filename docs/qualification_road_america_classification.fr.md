# Qualification — Road America 2025 official classification

Initial inspection: 10 November 2026, before integration. Milestone update:
11 November 2026. The observations below describe the inspected document;
the final section distinguishes completed integration from remaining work.

## Source and status

- Championship: IMSA WeatherTech SportsCar Championship.
- Event: Motul SportsCar Grand Prix, Road America, Race.
- Document: `03_Results_Race_Official.JSON`.
- [Official directory](https://imsa.results.alkamelcloud.com/Results/25_2025/16_Road%20America/01_IMSA%20WeatherTech%20SportsCar%20Championship/202508031310_Race/).
- [Inspected JSON](https://imsa.results.alkamelcloud.com/Results/25_2025/16_Road%20America/01_IMSA%20WeatherTech%20SportsCar%20Championship/202508031310_Race/03_Results_Race_Official.JSON).
- `session.report_mark` is `Official`. The directory also exposes
  Provisional and Unofficial versions: they must not be ingested as
  additional races.
- `session.creation_date`: `08-08-2025 10:12:17`, text without a confirmed time zone.

## Observed structure

Three roots: `session`, `fastest_lap`, `classification`.

- `session`: document context, weather, end mode, report status, and message.
- `fastest_lap`: fastest-lap reference object with car, driver,
  lap number, duration, and speed. Preserve separately from the classification.
- `classification`: 48 entries and 48 distinct text numbers. One row
  in the array describes one participant in this classification report.
- Each participant contains a `drivers` list. Expanding it into a separate
  table will avoid multiplying classification rows.

Fields populated at least once among participants, excluding the drivers list:
`status`, `not_finished`, `position`, `number`, `elapsed_time`,
`fastest_lap_number`, `fastest_lap_time`, `fastest_lap_kph`,
`fastest_lap_driver_number`, `time`, `gap_first`, `gap_previous`, `kph`,
`laps`, `pit_stops`, `team`, `class`, `group`, `vehicle`, `tires`, `manufacturer`.
The apparent aliases (`time`/`fastest_lap_time`, `kph`/`fastest_lap_kph`) still
need to be compared across all rows before removing any field.

Observed types: `position` and `fastest_lap_driver_number` are numeric,
`not_finished` is Boolean; car numbers, laps, and stop counts are
represented as text in the JSON. Gaps combine an initial
`-` marker with other representations to be inventoried before conversion.

## Initial BMW results

The positions below are from the overall classification, not positions
recalculated within each class.

| Car | Position | Class | Laps | Reported pit stops |
| --- | ---: | --- | ---: | ---: |
| 24 | 1 | GTP | 66 | 3 |
| 25 | 2 | GTP | 66 | 2 |
| 1 | 24 | GTDPRO | 62 | 3 |
| 96 | 31 | GTD | 62 | 3 |
| 48 | 41 | GTDPRO | 62 | 4 |

## Differences to address before joins

1. The classification contains 48 participants; the pit stop report contains
   50 fragments for 47 distinct numbers. All pit stop car numbers are
   present in the classification. Number `70` appears only in the classification:
   four laps, zero reported stops, `not_finished: true`.
2. All classification entries here have `status: Classified`, including
   car 70. This status alone therefore cannot determine whether the car
   finished: also retain the `not_finished` Boolean.
3. The session date is `03-08-2025 01:10`, versus `03/08/2025 01:10` in
   the pit stop document. The current `%d/%m/%Y` parser is not suitable as is.
4. Temperatures differ: air/track 25.22/35.56 ºC in the classification,
   versus 17.89/21.11 ºC in the pit stop report. These are document
   contexts; do not overwrite them or treat them as simultaneous measurements.
5. The official report message mentions the invalidation of some laps
   for exceeding track limits. It is populated and must be retained.
6. The two reports have different source identifiers and hashes.
   The cross-family join cannot require equality of `source_id` or
   `bronze_sha256`. Define an explicit mapping by championship,
   season, event, session, and then text car number, while retaining
   each document's provenance and version.

## Implications identified during initial qualification

- The current downloader enforces the pit stop filename. The
  destination will need to be configurable, with tests ensuring that families do not overwrite each other.
- The current Bronze build fixes the roots as `session` and
  `pit_stop_analysis`. It must not be applied to the classification: preserve
  its three roots with suitable ingestion before Silver projections.
- The scripts select only `document_type: pit_stops`. Adding a
  manifest entry is not enough to integrate a classification.
- The session context must retain the report status, message, and family;
  the rule excluding empty fields must be reassessed against the
  documents actually supported.
- For a future results mart, starting from the classification and joining pit stops
  aggregated by car will retain car 70. Distinguish a missing
  report, a missing match, and an established zero-stop count.

## Proposed acceptance criteria

- Document and metadata retained unchanged, with all three roots.
- 48 participants and five BMW entries in the reference dataset.
- Text numbers preserved, class and overall position distinguished.
- Car 70 retained with zero reported stops and a non-finish indicator.
- Hyphenated dates tested; official version and message retained.
- Cross-family join documented and tested without row multiplication.
- No regression in the current pipeline for the three pit stop reports.

## Discrepancies observed during actual reconciliation

Reading of the verified local Raw files on 11 November 2026:

| Car | Pit stops reported in the classification | Detailed pit stops found | Status |
| --- | ---: | ---: | --- |
| 22 | 1 | 2 (numbers 1 and 2) | `count_mismatch` |
| 88 | 4 | 3 (numbers 1, 2, and 3) | `count_mismatch` |
| 70 | 0 | No rows | `zero_reported_no_detail` |

Both numerical discrepancies are present in the source documents; their cause
remains to be investigated. The check flags the divergence and retains both
document versions, without asserting that either report is incorrect or rewriting
the counts. Passing code tests does not imply equality of all
values from two different public reports.

## Integration status as of 11 November 2026

- Source enabled in the manifest with its own `source_id` and `filename`.
- Configurable download, SHA-256 metadata, reuse of verified Raw files,
  and explicit refresh via `--refresh`.
- Separate Bronze layer: three roots retained, read back, and compared with the JSON
  before replacing the final file.
- Silver layer with 48 participants, provenance, source index, text number,
  overall position, class, reported stop count, and `not_finished`.
- Reports matched by championship, season, event, and session;
  multiple candidates and missing reports rejected. Stop counts associated
  with the loaded version, followed by a join retaining participants without detail.
- Comparison report published in the candidate run and accessed by the quality
  reader using the same active reference as the other results.
- Synthetic scenarios: retaining a participant without detail, excluding
  another version, count discrepancy, and missing detail with a nonzero
  reported count. Separate tests cover selection and key checks.

The Silver classification projection remains partial. Normalization of hyphenated
dates, weather context, the official message, classification drivers, and
the fastest lap are not yet integrated into dedicated Silver tables: this
information remains preserved in Bronze. The acceptance criteria above
are therefore not all satisfied. The shared workflow remains limited to one enabled
classification; a multi-classification extension must adapt loading before
expanding the manifest.

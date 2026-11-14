# Initial Road America 2023 qualification

Inspection on 12 November 2026. No addition to the active manifest: the available
formats differ from the JSON pairs integrated for 2024 and 2025.

[Official race directory](https://imsa.results.alkamelcloud.com/Results/23_2023/17_Road%20America/01_IMSA%20WeatherTech%20SportsCar%20Championship/202308061010_Race/).

## Observed availability

- Classification: `03_Results_Race_Official.CSV` and PDF.
- Pit stops: `20_Pit Stops Time Cards_Race.PDF`; no JSON or CSV equivalent
  is listed in this index.
- Timing: `23_Time Cards_Race.CSV`, at car/lap granularity, with
  `PIT_TIME`, `DRIVER_NUMBER`, `LAP_NUMBER`, `HOUR`, `MANUFACTURER`, and
  `CROSSING_FINISH_LINE_IN_PIT`. This is not the pit stop report already integrated.

## Initial differences

Semicolon-delimited CSV files, with a UTF-8 BOM. The timing headers
sometimes contain leading spaces. Preserve text numbers
such as `01`. The classification contains `POSITION`, `NUMBER`, `VEHICLE`, `CLASS`,
but no pit stop count column or textual manufacturer name;
`IMSA_ManufacturerId` is an identifier, not a label.

Classification reading verified with DuckDB: 45 participants. The header has
93 fields, while each participant row has 73. `null_padding=True` allows
missing trailing fields to be filled with NULL, without skipping rows.
`all_varchar=True` preserves text numbers. This exploratory reading
does not yet constitute validation or Bronze publication.

Do not fabricate a reported stop count from timing data: it would
no longer be independent of the observed count. Do not equate `PIT_TIME`
with the duration in the JSON reports without examining its definition and checking the PDF.

## Verified exploration and Git reference

`explore_classification_csv.py` reads the classification and a timing sample.
The timing path remains temporarily fixed at `/tmp/imsa-ra2023-timing.csv`.
For BMW 24, the two CSV durations match the PDF (1:28.481 and 1:22.665).
BMW 25 has four timing rows without PIT_TIME, whereas the PDF
contains a stop of 1:59:53.389: timing data does not replace the PDF.

`explore_pit_stop_pdf.py` extracts 116 pit stops for 44 cars, without duplicate
car/stop keys in the inspected PDF. Coordinates, body boundaries, and
font sizes are specific to this report. The car context carries across
columns/pages; one-, two-, and three-digit numbers are recognized.
The checks reject a stop without context, an out-of-sequence number, or a
candidate row whose duration cannot be extracted. Degradation that
even prevents recognition as a candidate can still go unnoticed.

Validation before the reference commit: 114 passing tests, including nine targeting
PDF exploration; both scripts were run on the local sources.
These checks do not prove completeness for other PDFs. Temporary source
files are not included in Git. No 2023 source has been
enabled in the pipeline, and these scripts do not trigger any publication.

The previous commit covers 2024 and 2025. The new milestone adds the
2023 exploration as a single batch; without intermediate commits, Git cannot
retrospectively separate the contributions of the different assistants.

## Exploratory summary and checks — 13 November 2026

The PDF script now receives two paths: pit stop PDF followed by classification
CSV. Both files must exist before any extraction.
`convert_extracted_stops` reuses the SQL duration macro and retains the raw
text, with a result rounded to the millisecond. `build_pdf_car_summary`
aggregates stops by car before the left join with the classification.

Chouaib confirms the 45-participant summary. Car 57, absent from the
inspected PDF report, is retained with an observed count of NULL, without
asserting that it made zero stops. The classification does not provide an
independent reported count allowing a comparison similar to 2024–2025.

Checks: reject NULL/empty/whitespace-only or duplicate classification numbers,
preserve the textual distinction between 01 and 1, and reject stops without a
matching participant. A participant without detail is still accepted.
The review detected an association check tested in isolation but missing from
`main()`: the call was added, and a `main()` test now verifies rejection
before the summary is built. These additions remain exploratory; no
2023 source is enabled or published by the main pipeline.

## Local sources and traceability of the exploratory output

The previously inspected PDF and classification CSV were copied, without conversion
or overwriting an existing file, from `/tmp` to the following Raw directories.
Matching hashes between each temporary source and its copy were verified.

- `data/raw/imsa-2023-road-america-race-pit-stops/20_Pit Stops Time Cards_Race.PDF`
- `data/raw/imsa-2023-road-america-race-classification-official/03_Results_Race_Official.CSV`

These local files, ignored by Git, must be retained to reproduce
the exploration. This copy is not yet an automated download or an
immutable archive. The official links remain those of the directory listed above.

The exploratory summary is published to
`data/exploration/road-america-2023/car_summary.parquet`, with content verification
by `publish_silver`, without activation in `current.json`.
Its current version produces 45 rows and eleven columns: the four business
columns, the two source hashes, championship/season/event_id/session_id,
and classification_status (source status, added after the Long Beach qualification).
The existing file must be regenerated to receive this new column.
Context values are declared in the script; they are not
automatically inferred or validated against the content of the two documents.

```bash
uv run python explore_pit_stop_pdf.py \
  "data/raw/imsa-2023-road-america-race-pit-stops/20_Pit Stops Time Cards_Race.PDF" \
  data/raw/imsa-2023-road-america-race-classification-official/03_Results_Race_Official.CSV
```

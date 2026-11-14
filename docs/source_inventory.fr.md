# Source inventory and implications for the pipeline

Verification dated November 6, 2026. This document distinguishes files read from
families identified in the official indexes. It is not an exhaustive
inventory of all championships, seasons, or schemas.

> Historical-status clarification: the proposed design decisions and work order
> below describe the November 6 assessment, not the current implementation
> backlog. The project now has a separate 2023–2025 Gold for race entries;
> statements about “our current file” and introducing a source manifest are
> stale if read as current claims. The source observations and unvalidated
> compatibility caveats remain historical evidence, not fresh portal checks.
> See [the Gold documentation](gold.fr.md).

## Official sources

- [IMSA 2025 index](https://imsa.results.alkamelcloud.com/Results/25_2025/)
- [Road America 2025 race](https://imsa.results.alkamelcloud.com/Results/25_2025/16_Road%20America/01_IMSA%20WeatherTech%20SportsCar%20Championship/202508031310_Race/)
- [Long Beach 2025 race](https://imsa.results.alkamelcloud.com/Results/25_2025/07_Long%20Beach%20Street%20Circuit/01_IMSA%20WeatherTech%20SportsCar%20Championship/202504121405_Race/)
- [Daytona 2025 race](https://imsa.results.alkamelcloud.com/Results/25_2025/02_Daytona%20International%20Speedway/01_IMSA%20WeatherTech%20SportsCar%20Championship/202501251340_Race/)
- [WEC portal](https://fiawec.alkamelsystems.com/)
- [GT World Challenge Europe portal](https://www.gt-world-challenge-europe.com/results)
- [DTM results](https://www.dtm.com/ergebnisse/results?season=2025)
- [WorldSBK portal](https://www.worldsbk.com/en/standings)

The non-IMSA portals have been identified, but their files and schemas have
not been validated as compatible with our reader. The historical WEC URL tested
now returns an HTML application: HTTP 200 does not guarantee a results
file. FIM EWC source availability remains to be checked.

## Families present in the Road America race index

| Family | Formats identified | Intended use |
| --- | --- | --- |
| Starting grids, in a subdirectory | Detailed inventory still to do | Starting position |
| Overall results | CSV, JSON, PDF | Classification, laps, gaps, status |
| Results by category | JSON, PDF | Class classifications |
| Best laps by driver | PDF | Performance summaries |
| Lap chart | JSON, PDF | Positions over the laps |
| Best sectors | JSON, PDF | Sector analysis |
| Leader sequence | PDF | Lead changes |
| Average distance and speed | JSON, PDF | Summaries |
| Best-lap sequence | JSON, PDF | Progression of benchmarks |
| Lap analysis | PDF | Detailed analysis |
| Drive time | PDF | Driving time |
| Pit stops | JSON, PDF | Entries/exits and durations |
| Time cards | CSV, JSON, PDF | Timed laps |
| Flag analysis | PDF | Neutralization context |
| Weather | CSV, JSON, PDF | Timestamped measurements |

Official, Provisional, and Unofficial results coexist. Championship points
and awards also appear at the parent level, along with
practice and qualifying sessions. Several formats can represent the
same facts: do not concatenate them as independent observations.
Presence in an index does not mean that every PDF's content has been read.

## Comparison of files actually read

The following volumes concern pit-stop JSON; they are source entries,
not necessarily distinct vehicles or people.

| 2025 event | Car entries | Driver entries | Stops |
| --- | ---: | ---: | ---: |
| Long Beach | 26 | 52 | 32 |
| Road America | 50 | 100 | 137 |
| Daytona, Hour 24 report | 69 | 265 | 1622 |

The three pit-stop JSON files have the roots `session` and `pit_stop_analysis`.
The official results have `session`, `fastest_lap`, `classification`:
27 entries at Long Beach, 48 at Road America, 61 at Daytona Hour 24.
The classification entry count therefore differs from the stop-report count.
The cause of individual discrepancies still needs analysis before joins.

The Road America Time Cards JSON has the roots `session`, `participants`
and 48 participant entries. Each participant has `drivers`
and `laps` lists. Laps expose number, driver, duration, speeds, elapsed time,
time of day, validity, invalidation indicators, pit-lane line crossing, and
`sector_times`. These indicators must accompany lap-time analysis;
an invalid lap must not become a performance benchmark by default.

The Daytona race has Hour 1 to Hour 24 subdirectories. Their content
must not be added together without checking temporal scope and overlaps.

The weather JSON files read have the roots `session`, `meteoSamples` and the fields:
`time_utc_secconds` (source spelling), `time_utc_str`, `air_temp`,
`track_temp`, `pressure`, `wind_speed`, `wind_direction`.
Daytona Hour 24 contains 1333 samples. Units and time conventions
must be checked per family and version; do not infer a unit
solely from the magnitude of the numbers. No humidity measurement was identified
in these fields, nor was internal maintenance or fuel telemetry demonstrated.

## Proposed design decisions

1. Retain the complete raw source, its provenance, and its versions.
2. Identify each document by source, championship, season, event,
   session, family, and report revision/period. The race name alone
   is not a sufficient key.
3. Isolate files by identity and version; a single
   `imsa_document.parquet` path is unsuitable for a collection of races.
4. Compare volumes computed from the JSON with volumes read back from the
   corresponding Parquet, rather than imposing `(50, 100, 137)` on every ingestion.
   Keep these numbers only in the Road America file test.
5. Also validate schema, content, and types: equal volumes do not prove
   equal data. Check before publishing the final file.
6. Provide a reader per format and processing per document family.
   The stop reader is not a universal reader for all results.
7. Define each Silver table's grain: session, entry,
   crew, stop, lap, weather measurement. Preserve numbers with leading zeros.
8. Check joins and retain entries without stops; do not
   use the stop report as the complete participant list.
9. Retain all fields in Raw/Bronze. Exclude from projections only
   fields that are entirely empty within the profiled scope, with the option
   of reintroducing them for another race or season.
10. Distinguish missing, empty, unknown, and not applicable. Do not equate a
    practice session with a race to impose the same requirements.
11. Check the terms of use before redistributing data.
    The project's code license grants no rights to the results.

## Work order

First replace fixed volumes with a source/output comparison on
our current file. Then introduce the source manifest, per-document paths,
and a second stop file. Add results, laps, and weather
with their own checks, and only then validate another championship.
The goal is gradual expansion, without promising untested compatibility.

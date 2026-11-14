# Road America 2024 qualification — cross-season pilot

Inspection and integration on 12 November 2026. Both sources are enabled
and marked `tested_locally` after Chouaib confirmed the reference totals:
516 entries, including 52 BMW entries, 4 280 pit stops including 396 BMW stops, twelve summaries, and
separation of the two seasons. The agent did not rerun the test suite
for this configuration addition.

[Official directory](https://imsa.results.alkamelcloud.com/Results/24_2024/14_Road%20America/01_IMSA%20WeatherTech%20SportsCar%20Championship/202408041410_Race/).
Files: `03_Results_Race_Official.JSON` and `20_Pit Stops Time Cards_Race.JSON`.
The classification is marked Official. Proposed session identity: season 2024,
event_id road-america, session_id 202408041410-race, report_period session.

Unchanged roots: session/fastest_lap/classification for the classification,
session/pit_stop_analysis for the pit stops. The expected Silver fields are
present for all 47 participants. The first participant's keys were
compared with those of Road America 2025, with no differences; this does not prove
complete equality of schemas and types across the entire year.

| Reference | Value |
| --- | ---: |
| Classified participants / distinct numbers | 47 / 47 |
| BMW entries | 4 |
| Pit stop report entries | 49 |
| Driver entries | 98 |
| Detailed pit stops | 163 |
| BMW pit stops | 8 |
| Count discrepancies | 4 (8,51 %) |

BMW cars: 24 (position 7), 1 (22), 96 (24), 25 (46).
The GT cars are labeled BMW M4 GT3, without EVO; retain the source model.
Discrepancies: 023 (5 reported / 4 detailed), 120 (4/3), 45 (2/3), 11 (2/1).
Causes not established; no automatic correction.
Classification session date: 04-08-2024 02:10, without a confirmed time zone.

Expected reference totals after adding to the eleven 2025 races: 516 entries,
including 52 BMW entries; 4 280 detailed pit stops, including 396 BMW stops; twelve quality summaries,
still twelve output families. The full workflow and conversion, key, and
association checks still need to run before local validation.

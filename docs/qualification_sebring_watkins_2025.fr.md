# Sebring / Watkins Glen 2025 qualification

Inspection followed by integration on 12 November 2026. Four sources enabled and
moved to `tested_locally` after execution confirmed by Chouaib: run
`cf43b04e5ef849e38aafe0f07c16aec2`, 305 entries, including 32 BMW entries,
3 018 linked and enriched pit stops, including 285 BMW stops. The discrepancies below
come from qualification of the JSON files; the agent did not rerun the test suite
for this configuration addition.

## Selected directories

- [Sebring, hour 12](https://imsa.results.alkamelcloud.com/Results/25_2025/06_Sebring%20International%20Raceway/01_IMSA%20WeatherTech%20SportsCar%20Championship/202503151010_Race/12_Hour%2012/)
- [Watkins Glen, hour 6](https://imsa.results.alkamelcloud.com/Results/25_2025/14_Watkins%20Glen%20International/01_IMSA%20WeatherTech%20SportsCar%20Championship/202506221210_Race/06_Hour%206/)

The session indexes expose twelve and six hourly subdirectories,
respectively. Only the final pair is selected, without concatenating earlier states.
Files: `03_Results_Race_Official.JSON` and `20_Pit Stops Time Cards_Race.JSON`.
The classifications have `report_mark: Official` and an end duration of
43 200 / 21 600 seconds, consistent with twelve / six hours.

| Reference | Sebring | Watkins Glen |
| --- | ---: | ---: |
| Distinct classified participants | 56 | 55 |
| BMW entries | 5 | 5 |
| Pit stop report entries | 64 | 57 |
| Driver entries | 192 | 151 |
| Detailed pit stops | 716 | 387 |
| Detailed BMW pit stops | 66 | 34 |
| Count discrepancies | 8 (14,29 %) | 6 (10,91 %) |

Affected numbers at Sebring: 40, 52, 021, 63, 14, 19, 73, 18.
At Watkins Glen: 85, 14, 44, 25, 11, 52. For each, the classification reports
one more stop than the inspected detail. BMW 25 at Watkins Glen reports
five stops versus four detailed stops. Causes not established; no correction.
No number in the pit stop detail is absent from the corresponding classification.

The roots match the existing families; full compatibility of
conversions, keys, links, and durations remains to be checked in the pipeline.
The proposed session identifiers come from the directories:
`202503151010-race` and `202506221210-race`. They do not establish a time zone.

After integration with the five existing races, expected reference totals:
305 classified entries, including 32 BMW entries, 3 018 detailed pit stops, including 285 BMW stops,
seven summary rows, and still twelve output families.

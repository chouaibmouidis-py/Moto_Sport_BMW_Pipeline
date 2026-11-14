# Long Beach, Canadian Tire, and VIR 2024 qualification

Official JSON files inspected on 12 November 2026. After Chouaib confirmed
the expected pipeline results and the reported anomalies, the six sources
were marked `tested_locally`. The agent did not rerun the pipeline for
this batch; the previous full suite had 105 passing tests.

| Race | Session | Participants | BMW | Car entries | Drivers | Pit stops | BMW pit stops |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: |
| Long Beach | 202404201335-race | 27 | 3 | 25 | 50 | 31 | 4 |
| Canadian Tire | 202407141105-race | 34 | 2 | 34 | 68 | 95 | 9 |
| VIR | 202408251210-race | 23 | 2 | 23 | 46 | 58 | 4 |

All three classifications are marked `Official` and belong to IMSA WeatherTech.
Reports: `03_Results_Race_Official.JSON` and
`20_Pit Stops Time Cards_Race.JSON`, with exact links in the manifest.

Long Beach: count discrepancies for 25 (3 reported / 2 detailed),
27 (2/1), and 12 (3/2), or 3/27 = 11,11 %. Car 120 reports one stop
without detail: `missing_stop_details`, which must not be counted as `count_mismatch`.
Canadian Tire and VIR: no count discrepancies identified in the JSON files.
No automatic correction of source values.

The GT BMW cars are M4 GT3 models, without adding the EVO suffix. BMW cars 24 and 25
are present at Long Beach; do not require their presence at the other two races.

Cumulative reference totals confirmed by Chouaib: 655 entries including 66 BMW entries,
4 584 pit stops including 426 BMW stops, 693 car entries, and 1 716 driver entries,
17 sessions, and 17 count quality summaries. Still twelve output files.

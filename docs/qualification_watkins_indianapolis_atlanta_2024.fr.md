# Watkins Glen, Indianapolis, and Road Atlanta 2024 qualification

Official JSON files inspected on 12 November 2026. After Chouaib confirmed
the expected results of the full execution, the six sources were marked
`tested_locally`. The agent did not rerun this batch or the test suite.
Classifications marked Official. Only the final reports are selected,
without concatenating hourly reports. Indianapolis: directory 17 WeatherTech,
not directory 18 Mustang Challenge.

| Race | Session | Hour | Participants | BMW | Car fragments | Drivers | Pit stops | BMW pit stops |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| Watkins Glen | 202406231110-race | 6 | 56 | 4 | 65 | 171 | 407 | 38 |
| Indianapolis | 202409221230-race | 6 | 56 | 4 | 64 | 171 | 405 | 32 |
| Road Atlanta | 202410121210-race | 10 | 53 | 4 | 63 | 189 | 578 | 41 |

The six exact links are in the manifest. Files:
`03_Results_Race_Official.JSON` and `20_Pit Stops Time Cards_Race.JSON`.
No duplicate car/stop-number keys identified in the three pit stop reports.

## Anomalies to retain

- Watkins Glen: seven `count_mismatch` (12,50 %), including BMW 25 (10/11).
  Other cars: 19 (9/8), 11 (8/7), 81 (8/7), 62 (7/6), 63 (7/6), 27 (4/3).
  Cars 47 and 18: zero reported, no detail (`zero_reported_no_detail`).
- Indianapolis: nine `count_mismatch` (16,07 %): 66 (5/6), 55 (7/6),
  83 (7/6), 20 (11/10), 34 (9/8), 63 (6/5), 21 (5/4), 023 (6/5), 31 (4/3).
  Car 19: one reported stop without detail (`missing_stop_details`).
- Road Atlanta: six `count_mismatch` (11,32 %): 10 (11/10), 86 (11/10),
  120 (10/9), 4 (9/10), BMW 25 (6/5), 85 (5/4).
  Car 44: one reported stop without detail (`missing_stop_details`).

The causes have not been established; no automatic correction.
BMW cars present: 24 and 25 (M Hybrid V8), 1 and 96 (M4 GT3, without EVO).

## Cumulative reference totals confirmed by Chouaib

The eleven 2024 races and eleven 2025 races represent
44 documents, 937 entries including 86 BMW entries, 8 307 pit stops including 711 BMW stops,
1 066 car fragments, 2 877 driver entries, and 22 count quality summaries.
Still twelve output files. Full execution was confirmed
by Chouaib; the anomalies remain visible in the quality reports.

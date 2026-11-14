# Daytona and Sebring 2024 qualification

Official JSON files inspected on 12 November 2026. After Chouaib confirmed
the expected results, the four sources were marked `tested_locally`.
The agent did not rerun this batch or the test suite after that confirmation.
The official indexes were used to select only the final
Hour 24 and Hour 12 reports, without concatenating intermediate reports.

| Race | Session | Participants | BMW | Car fragments | Drivers | Pit stops | BMW pit stops |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: |
| Daytona, hour 24 | 202401271340-race | 59 | 4 | 112 | 423 | 1 545 | 123 |
| Sebring, hour 12 | 202403160940-race | 58 | 4 | 69 | 207 | 788 | 51 |

The classifications are marked `Official`, IMSA WeatherTech championship.
Daytona: `20_Pit Stops Time Cards.JSON`, without the `_Race` suffix.
Sebring: `20_Pit Stops Time Cards_Race.JSON`.
The exact paths of the four reports are in the manifest.

Daytona: 59 distinct numbers in 112 fragments; no duplicate
car/stop-number key identified. Sixteen count discrepancies, or 27,12 %,
including BMW 24 (30 reported / 31 detailed).
Sebring: 57 numbers in the pit stop report for 58 classified participants.
Four discrepancies: 45 (13/12), 80 (12/11), 85 (7/6), 83 (9/8), or 6,90 %.
Car 32: one reported stop, no detailed row (`missing_stop_details`).
The causes have not been established, and no source value is replaced.

BMW cars present in both classifications: 24, 25 (M Hybrid V8),
1 and 96 (M4 GT3, without EVO).

Cumulative reference totals confirmed by Chouaib after publication: 772 entries including
74 BMW entries, 6 917 pit stops including 600 BMW stops, 874 car fragments,
2 346 driver entries, and 19 count summaries. Still twelve outputs.
The reported anomalies are retained in the quality reports.

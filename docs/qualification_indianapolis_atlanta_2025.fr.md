# Indianapolis / Road Atlanta 2025 qualification

Inspection and integration on 12 November 2026. The four sources are
`tested_locally`. The active run `57425c9ee72947108831adc8aa6232ad` was read back:
469 entries, 4 117 pit stops including 388 BMW stops, eleven summaries; Chouaib confirms
48 BMW entries. The Indianapolis and Road Atlanta summaries match
the discrepancies below. The test suite still needs to be rerun after this latest batch.

- [Indianapolis hour 6](https://imsa.results.alkamelcloud.com/Results/25_2025/20_Indianapolis%20Motor%20Speedway%20RC/01_IMSA%20WeatherTech%20SportsCar%20Championship/202509211140_Race/06_Hour%206/)
- [Road Atlanta hour 10](https://imsa.results.alkamelcloud.com/Results/25_2025/22_Road%20Atlanta/01_IMSA%20WeatherTech%20SportsCar%20Championship/202510111210_Race/10_Hour%2010/)

Files: `03_Results_Race_Official.JSON` and `20_Pit Stops Time Cards_Race.JSON`.
Classifications marked Official, roots session/fastest_lap/classification. End durations
21 600 and 36 000 seconds, consistent with six and ten hours. Only the final
pair is selected; hourly subdirectories are not concatenated.

| Reference | Indianapolis | Road Atlanta |
| --- | ---: | ---: |
| Participants / distinct numbers | 53 / 53 | 53 / 53 |
| BMW entries | 5 | 5 |
| Pit stop report entries | 63 | 61 |
| Driver entries | 167 | 183 |
| Detailed pit stops | 376 | 558 |
| BMW pit stops | 31 | 57 |
| Count discrepancies inspected | 4 (7,55 %) | 3 (5,66 %) |

Indianapolis discrepancies: 65, 88, 75, 19. Road Atlanta discrepancies: 22, 9, 78.
Each discrepancy corresponds to one more reported stop than the detail found.
Causes not established; no correction. No car number in the pit stop reports is absent
from the corresponding classification. Conversions and links remain to be tested.

Expected reference totals for all eleven races: 469 entries,
including 48 BMW entries; 4 117 detailed pit stops, including 388 BMW stops; 507 car entries
and 1 344 driver entries in the pit stop reports; eleven quality summaries.
Twenty-two source documents, still twelve output file families.

# IMSA WeatherTech 2024 coverage

Initial inventory dated November 12, 2026, after validation of the Road America pilot.
[Official schedule announcement and revision](https://www.imsa.com/news/2023/08/04/2024-imsa-schedules-revealed-at-road-america/).
[Official 2024 index](https://imsa.results.alkamelcloud.com/Results/24_2024/).
Actual dates and sessions will be checked in the reports before activation.

> Historical-status clarification: the future-tense activation check above
> belongs to the initial inventory. The completed batches below and the current
> separate 2023–2025 Gold supersede that pending status; the figures below
> retain their original two-season scope. See [the Gold documentation](gold.fr.md).

## Scope and batches

| Race | Status | Proposed batch |
| --- | --- | --- |
| Road America | Classification and stops validated locally | Pilot completed |
| Laguna Seca | Classification and stops validated locally | 1 completed |
| Detroit | Classification and stops validated locally | 1 completed |
| Long Beach | Classification and stops validated locally | 2 completed |
| Canadian Tire Motorsport Park | Classification and stops validated locally | 2 completed |
| VIR | Classification and stops validated locally | 2 completed |
| Daytona | Final Hour 24 reports validated locally | 3 completed |
| Sebring | Final Hour 12 reports validated locally | 3 completed |
| Watkins Glen | Final Hour 6 reports validated locally | 4 completed |
| Indianapolis | Final Hour 6 reports validated locally | 4 completed |
| Road Atlanta | Final Hour 10 reports validated locally | 4 completed |

Eleven races expected and integrated for classifications and stops. The presence
of a directory in the archive does not prove that our two JSON families are available.
The index also contains practice sessions and other series: do not ingest all
directories as WeatherTech races. Two Indianapolis directories appear
in 2024: directory 17 concerns WeatherTech (September 22, six hours),
directory 18 Mustang Challenge (races on October 3 and 4), outside the scope.
The inspected WeatherTech classification contains 56 participants; the Mustang
Challenge race 1 classification contains 25. Check the championship and session,
not just the circuit name.

Do not construct 2024 URLs by substituting the year in 2025 URLs:
event prefixes and session dates differ. Do not assume the
same BMW models or numbers. GT3 and GT3 EVO retain their source labels.
Hourly reports will be selected according to their scope, never concatenated
as separate races.

## Validated coverage summary

Chouaib confirmed the final batch results: together with 2025, 937 entries
including 86 BMW entries, 8 307 stops including 711 BMW stops, 1 066 car fragments,
2 877 driver entries, and 22 count quality assessments. The 44 sources are
marked `tested_locally`. Coverage concerns these two report families,
not all IMSA data. The full suite was not rerun by
the agent for this final configuration addition.

### Historical pilot reference

Road America 2024: 47 participants including four BMWs, 163 stops including eight BMW stops,
four count mismatches (8,51 %). Together with the integrated 2025 season:
516 entries including 52 BMW entries, 4 280 stops including 396 BMW stops, twelve quality assessments.
Each addition must preserve championship/season/event/session separation,
as well as each report's provenance and version.

# Laguna Seca and Detroit 2024 qualification

Inspection and validation on 12 November 2026. The four manifest sources
are marked `tested_locally` after full publication and run activation.

| Race | Session | Participants | BMW | Car entries | Drivers | Pit stops | BMW pit stops | Count discrepancies |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| Laguna Seca | 202405121210-race | 34 | 4 | 34 | 68 | 85 | 9 | 1 (2,94 %) |
| Detroit | 202406011510-race | 21 | 3 | 21 | 42 | 35 | 4 | 2 (9,52 %) |

[Laguna Seca reports](https://imsa.results.alkamelcloud.com/Results/24_2024/08_Weathertech%20Raceway%20Laguna%20Seca/01_IMSA%20WeatherTech%20SportsCar%20Championship/202405121210_Race/).
[Detroit reports](https://imsa.results.alkamelcloud.com/Results/24_2024/09_Detroit%20Street%20Course/01_IMSA%20WeatherTech%20SportsCar%20Championship/202406011510_Race/).
Each session exposes `03_Results_Race_Official.JSON` (marked Official)
and `20_Pit Stops Time Cards_Race.JSON`.

Reported/detailed discrepancies: Laguna Seca, car 34 (3/2); Detroit,
car 35 (2/1) and car 64 (1/2). Causes not established; values retained.
The source data remains the reference for the exact model, without automatic
conversion from GT3 to GT3 EVO.

Expected cumulative reference totals with 2025 and Road America 2024:
571 entries including 59 BMW entries, 4 400 pit stops including 409 BMW stops,
611 car entries, 1 552 driver entries, and 14 quality summaries.
These volumes alone do not validate conversions, keys, and joins.
The full transformation and publication confirmed these volumes;
the detailed business view remains available through the project's readers.

Validation performed by the agent: the twelve outputs were published and run
`f0526cabb65d425b9007cec9ca5ab637` activated. The full suite passes (105 tests).
The exact check revealed two floating-point calculation instabilities: the sum of
durations and the average at the half-thousandth boundary. The total is rounded to three
decimal places; the average uses a sum in DECIMAL(18,3) before division.
The content check remains exact, and its message now identifies the output.

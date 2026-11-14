# Canadian Tire Motorsport Park / VIR 2025 qualification

Inspection followed by integration on 12 November 2026. Four sources enabled and
moved to `tested_locally` after Chouaib confirmed the outputs:
363 entries, including 38 BMW entries; 3 183 linked pit stops, including 300 BMW stops;
nine quality summary rows. The agent did not rerun the test suite
for this configuration addition.

- [CTMP session](https://imsa.results.alkamelcloud.com/Results/25_2025/15_Canadian%20Tire%20Motorsport%20Park/01_IMSA%20WeatherTech%20SportsCar%20Championship/202507131405_Race/)
- [VIR session](https://imsa.results.alkamelcloud.com/Results/25_2025/17_VIRginia%20International%20Raceway/01_IMSA%20WeatherTech%20SportsCar%20Championship/202508241410_Race/)

Files: `03_Results_Race_Official.JSON` and `20_Pit Stops Time Cards_Race.JSON`.
The classifications are marked Official; their roots are session, fastest_lap,
classification. The pit stop reports retain session and pit_stop_analysis.

| Reference | CTMP | VIR |
| --- | --- | --- |
| Session derived from the directory | 202507131405-race | 202508241410-race |
| Classes present | LMP2, GTDPRO, GTD | GTDPRO, GTD |
| Distinct classified participants | 35 | 23 |
| BMW entries | 3 | 3 |
| BMW numbers | 1, 48, 96 | 1, 96, 48 |
| Pit stop report entries | 35 | 23 |
| Driver entries | 70 | 46 |
| Detailed pit stops | 111 | 54 |
| BMW pit stops | 8 | 7 |
| Count discrepancies inspected | None | None |

No number in either pit stop report is absent from the corresponding classification.
The absence of BMW GTP cars 24 and 25 is not a completeness defect: the
GTP class does not appear in either classification. Do not require the five
BMW cars from races featuring all classes as a constant validation rule.
The absence of count discrepancies does not establish the quality of all other fields.

Expected reference totals after integration across the seven races: 363 entries,
including 38 BMW entries; 3 183 detailed pit stops, including 300 BMW stops; nine quality summaries and
still twelve file families. Conversions, keys, and links must be checked by
the pipeline before declaring the batch validated.

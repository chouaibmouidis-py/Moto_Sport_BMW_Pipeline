# Laguna Seca / Detroit 2025 batch qualification

Inspection on 12 November 2026, followed by activation of the four sources and local
validation confirmed by Chouaib: 194 entries, including 22 BMW entries, 1 915 linked
and enriched pit stops. Laguna Seca summary: 36 participants, one discrepancy (2,78 %);
Detroit: 22 participants, no count discrepancies. The status of the four sources
was changed to `tested_locally`. The 103-test suite had passed before this addition;
the agent did not rerun it for this qualification.

## Official sources

- [Laguna Seca directory](https://imsa.results.alkamelcloud.com/Results/25_2025/10_Weathertech%20Raceway%20Laguna%20Seca/01_IMSA%20WeatherTech%20SportsCar%20Championship/202505111210_Race/)
- [Detroit directory](https://imsa.results.alkamelcloud.com/Results/25_2025/11_Detroit%20Street%20Course/01_IMSA%20WeatherTech%20SportsCar%20Championship/202505311640_Race/)

Each directory provides `03_Results_Race_Official.JSON` and
`20_Pit Stops Time Cards_Race.JSON`. Both classifications have report_mark
Official. The pit stop reports are not assumed to be official solely
because they are present in this directory.

| Reference | Laguna Seca | Detroit |
| --- | --- | --- |
| Proposed event_id | laguna-seca | detroit |
| session_id derived from the directory | 202505111210-race | 202505311640-race |
| Classified participants / distinct numbers | 36 / 36 | 22 / 22 |
| BMW entries | 5 | 4 |
| Pit stop report entries | 37 | 22 |
| Detailed pit stops | 88 | 36 |
| Observed count discrepancies | Car 70: 4 reported, 3 detailed | None |

Classification roots: session, fastest_lap, classification. Pit stop roots:
session, pit_stop_analysis. No number in either pit stop report is
absent from the corresponding classification. The fields projected by the current Silver
layer are present in the previews; conversion, key, and link checks
still need to run on the full batch before concluding that it is integrated.

Dates: Laguna Seca exposes `11-05-2025 12:10` in the classification and
`11/05/2025 12:10` in the pit stops; Detroit exposes `31/05/2025 04:40` in both.
These strings do not establish a time zone or a 12/24-hour convention.
The cross-document join must use explicit manifest metadata.
The cause of the Laguna Seca discrepancy has not been established; no correction is planned.

After integration, expected reference totals for all five races:
194 classified entries, including 22 BMW entries, 1 915 detailed pit stops, and five
count summary rows. The twelve file families remain unchanged.
These reference totals do not replace validation of the transformations and the run.

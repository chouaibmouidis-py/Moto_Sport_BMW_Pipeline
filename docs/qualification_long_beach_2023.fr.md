# Exploratory qualification of Long Beach 2023

Inspection on 13 November 2026, without activation in the main manifest.
[Official directory](https://imsa.results.alkamelcloud.com/Results/23_2023/08_Long%20Beach%20Street%20Circuit/01_IMSA%20WeatherTech%20SportsCar%20Championship/202304151405_Race/).
Sources inspected: `03_Results_Race_Official.CSV` and
`20_Pit Stops Time Cards_Race.PDF`.

The Road America PDF reader, run without modification or publication,
extracts 28 pit stops for 25 car numbers on one page. All these numbers
exist among the 28 CSV entries. This provides a second real case of
compatibility, but does not prove completeness for all IMSA reports.

BMW cars in the classification: 25 (position 2), 24 (4), 1 (11), 96 (19), 97 (23).
Do not apply the 24/25 display filter when measuring the total volume.

Three entries have no detail in the extraction: 01, 80, and 93.
The CSV indicates 01: Classified, position 26, zero laps; 80 and 93:
Not started, missing position, zero laps. Missing positions must be
retained, along with the source status. They do not prove a reading error.
Do not convert missing detail into a certified zero-stop count.

The main exploration script remains configured for the Road America 2023 context
and output path: do not run it to publish Long Beach before
making that context explicit. No Road America result was
replaced during this qualification. An independent comparison of the complete
PDF content is still required before validating completeness.

The exploratory summary now retains `STATUS` as
`classification_status`. In-memory verification: 28 rows, eleven columns,
01 Classified/position 26, 80 and 93 Not started/position NULL, with an observed
count of NULL for all three. Missing positions are sorted last.
The 21 targeted tests pass, including the summary with a synthetic non-starter.

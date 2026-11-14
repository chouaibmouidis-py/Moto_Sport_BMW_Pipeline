# BMW car and motorcycle coverage, seasons 2022 to 2026

Requested objective: test races with BMW participation worldwide,
including factory programs and customer teams. The five selected seasons are
2022, 2023, 2024, 2025, and 2026; 2026 data is limited to publications
available as of November 6, 2026. This season-based scope is not an exact
rolling five-year window. The 2021 archives are a possible extension.

This document organizes the research. It does not claim that all races
below have been inventoried or tested, or that BMW is present at every round.

> Current-status clarification: the IMSA row below preserves the earlier
> integration status. Its description of 2023 as outside the active run still
> applies to the main JSON run, but is incomplete as a current coverage claim:
> the separate Gold now combines 2023–2025 race entries. It is not yet a common
> table of all detailed stops. See [the Gold documentation](gold.fr.md).

## Initial register of families to cover

| Discipline | Family | Starting source | Status |
| --- | --- | --- | --- |
| Car racing | IMSA WeatherTech | https://imsa.results.alkamelcloud.com/ | Eleven 2024 races and eleven 2025 races integrated; eleven exploratory 2023 summaries outside the active run; 2022 and 2026 to qualify. See the annual coverage documents. |
| Car racing | IMSA Michelin Pilot Challenge, GT4 | Same IMSA portal | Season archives and participation to inventory |
| Car racing | FIA WEC | https://fiawec.alkamelsystems.com/ | Portal identified; current archive access to resolve |
| Car racing | GT World Challenge Europe, Sprint and Endurance | https://www.gt-world-challenge-europe.com/results | Public results identified; collection and schemas to test |
| Car racing | GT World Challenge America, Asia, Australia | Official regional SRO portals | Sources and BMW races to inventory |
| Car racing | Intercontinental GT Challenge | https://www.intercontinentalgtchallenge.com/results | Portal and Suzuka 2025 report identified |
| Car racing | DTM | https://www.dtm.com/ergebnisse/results?season=2025 | Results identified; extraction to test |
| Car racing | Nürburgring 24h and qualifying races | https://www.24h-rennen.de/ergebnisarchiv/ | Official archive identified |
| Car racing | NLS | Official organizer | Archives and schemas to identify |
| Car racing | GT4, national GT series, and BMW cups | Organizers by championship | Register to complete, without assuming a universal SRO format |
| Motorcycle racing | WorldSBK | https://www.worldsbk.com/en/results | Portal identified; reports by season and session to test |
| Motorcycle racing | FIM EWC | https://www.fimewc.fr/results/ | 2021–2023 archive identified; this page does not demonstrate 2024–2026 coverage |
| Motorcycle racing | British Superbike and Superstock | https://www.britishsuperbike.com/ | BMW customer program documented; files to inventory |
| Motorcycle racing | IDM / EURO MOTO, FSBK, ESBK | Federations and organizers | BMW customer leads; participation to confirm race by race |
| Motorcycle racing | MotoAmerica, Japanese competitions, and other national series | Official organizers | Worldwide register to complete |
| Motorcycle racing | Road racing, including the TT and international events | Official organizers | Sources, formats, and participation to confirm |

## Program evidence and entry points

- [BMW: WEC and IMSA prototype programs in 2025](https://www.press.bmwgroup.com/global/article/attachment/T0446905EN/625752).
  The M Hybrid V8 starts in IMSA in 2023 and WEC in 2024: do not automatically
  assign this model to earlier seasons.
- [BMW: Motorrad 2025 guide](https://www.press.bmwgroup.com/canada/article/detail/T0448209EN?forceSitePreference=DESKTOP).
- [BMW: Motorrad 2025 review, factory and customers worldwide](https://www.press.bmwgroup.com/global/article/attachment/T0454682EN/641940).
- [BMW: Motorrad 2026 programs](https://www.press.bmwgroup.com/usa/article/attachment/T0455315EN_US/643118).
- [Official IGTC Suzuka 2025 report with BMW M4 GT3 EVO](https://www.intercontinentalgtchallenge.com/images/results/147/2025%20IGTC%20Suzuka%201000KM%20Aggregate%20Combined%20Classification%20Final.pdf).

A press release proves an announced program or reported results; it does not
replace each race's schedule, entry list, and results.

## Measure coverage rather than promising “all”

Build a manifest with: discipline, organizer, championship, season,
event, date, circuit, session, evidence of BMW participation, evidence type
(entered, started, or classified), source URL, report family, revision, covered
period, format, access status, extraction status, and validation status.

Statuses remain distinct: identified, accessible, downloaded, parsed, validated,
unavailable, or not applicable. An HTTP 200 URL may return HTML instead
of the expected document. A missing file does not prove an absence of BMWs.

Coverage is measured by championship and season: confirmed BMW races,
races with available documents, ingested races, and validated races.
Until schedules and entries have been reconciled, the expected
worldwide total remains unknown.

## Testing and modeling rules

1. Test one adapter per provider and document family; do not impose
   `pit_stop_analysis` on WorldSBK, results, or weather.
2. Preserve every document and revision; do not double-count a race
   shared by several championships, such as a GT and IGTC event.
3. Distinguish race, round, and session. A round may have several races.
   DNS, DNF, DSQ, cancellations, and interruptions remain facts to retain.
4. Do not require a pit stop in a motorcycle sprint race. Separate missing,
   unknown, and not applicable rather than filling with zeros.
5. Identify the competition, season, and session before joining vehicle
   or rider/driver numbers. Do not use a number as a worldwide identity.
6. Retain non-BMW competitors for comparisons; select BMWs
   in analyses rather than prematurely removing competitors in Bronze.
7. Define units and time conventions per source: dates, time zones,
   midnight, durations, weather, and revisions are not interchangeable.
8. Compare source and output for every document, checking content
   and types as well as volumes; test errors before publication.
9. Keep `(50, 100, 137)` solely as the expected result of the Road America 2025
   test file, never as a requirement for all competitions.
10. Check each provider's terms of use, especially
    before automated storage or redistribution of public datasets.

## Learning sequence

Design the multi-season, multi-discipline manifest now.
Then validate a complete car-racing path and a complete motorcycle-racing path,
and run the same checks on other compatible documents. Additional formats
require their own adapters and tests. This sequence
does not reduce the worldwide target; it avoids launching mass collection
before knowing how to interpret files and measure failures.

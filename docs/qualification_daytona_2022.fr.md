# Daytona 2022 — local integration qualification

Qualified on 22–23 November 2026. Event: IMSA WeatherTech Rolex 24 at Daytona,
session `202201291340-race`, final 24-hour report period.

## Sources and processing

The enabled source pair in [the manifest](../config/sources.json) is:

- `imsa-2022-daytona-race-hour24-classification-official`: classification CSV,
  `03_Results_Race_Official.CSV`.
- `imsa-2022-daytona-race-hour24-pit-stops`: pit-stop PDF,
  `20_Pit Stops Time Cards_Race.PDF`.

Both use the existing multiformat Raw → Bronze → Silver → participant mart →
Gold path. No season-specific production script was added. Source bytes and
metadata were verified locally; the complete run used existing Raw files without
network acquisition. PDF extraction retained provenance and page/column/line
locations. Counts qualify these documents, not independent real-world completeness.

## Observed results

| Check | Result |
| --- | ---: |
| Classification participants | 61 |
| BMW participants | 3 |
| Extracted PDF stops | 1,762 |
| Stop cars absent from paired classification | 0 |
| Unrecognized classification gap-format issues | 0 |
| Exact-model Mercedes corrections | 6 |
| Exact-model Duqueine corrections | 4 |
| Unresolved participant manufacturers after enrichment | 0 |

Silver maps exact normalized `Mercedes-AMG GT3` and `Duqueine D08` names to
`Mercedes` and `Duqueine`, with `matched_override`. Gold retains those values
with origin `silver_override`. Source IDs, raw models and Bronze values remain
available; the reference's original ambiguity and name counts are not rewritten.
CSV does not provide the reported stop-count field used by the JSON reports:
that count stays NULL and comparison status is `unavailable_reported_count`.

## Combined local Gold and deployment boundary

The new local Gold contains 1,453 participations, including 140 BMW, with 45
columns. The previous 1,392 participations retain their shared fields, except for
the three manufacturer name/origin/status fields intentionally corrected. This
was checked with EXCEPT ALL in both directions.

Both 2022 sources are enabled and marked `tested_locally`. The remote 114-file
archive includes their reports and metadata, and restoration was verified in a
temporary directory. MotherDuck history has received the 16 additional sporting
columns. The migration preserved the previous publication during preparation.
The maintainer subsequently confirmed the hosted Daytona 2022 extension after
publication; later maintenance changes require their own delivery checks.

The qualification baseline had 222 passing tests; the later review maintenance
lot has 227. No common detailed-stop Gold table or remaining 2022-race coverage
is claimed here.

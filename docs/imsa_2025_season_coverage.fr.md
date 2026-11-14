# IMSA WeatherTech 2025 season coverage

Objective defined on November 12, 2026: cover the races of the 2025 season,
across all circuits, for the classification and detailed-stop report families.
This scope concerns WeatherTech, not all IMSA championships.

## Race reference list

Starting point: [official eleven-race schedule announcement](https://www.imsa.com/news/2024/march/15/imsa-announces-2025-schedules-for-weathertech-championship-michelin-pilot-challenge).
This preseason announcement is used to establish the event list;
the sessions actually held, final dates, classes, and documents
must be checked in the official results. The announcement dates
are not used to construct download paths.

| Event / circuit | Classification + stops | Next check |
| --- | --- | --- |
| Daytona | Integrated and validated locally | Retain the Hour 24 report pair |
| Sebring | Integrated and validated locally | Final Hour 12 pair, mismatches retained |
| Long Beach | Integrated and validated locally | Case without details retained |
| Laguna Seca | Integrated and validated locally | Car 70: count mismatch retained |
| Detroit | Integrated and validated locally | No count mismatch in the inspected batch |
| Watkins Glen | Integrated and validated locally | Final Hour 6 pair, mismatches retained |
| Canadian Tire Motorsport Park | Integrated and validated locally | LMP2 and GT; three BMW GT cars |
| Road America | Integrated and validated locally | Count mismatches retained |
| VIRginia International Raceway | Integrated and validated locally | GT only; three BMWs |
| Indianapolis | Integrated and validated locally | Final Hour 6 pair |
| Road Atlanta / Petit Le Mans | Integrated and validated locally | Final Hour 10 pair |

The eleven races are integrated for both families: classification and stops.
The manifest contains twenty-two enabled documents. The active run
`57425c9ee72947108831adc8aa6232ad` was read back by the agent: 469 entries,
4 117 detailed stops, including 388 BMW stops, and eleven quality assessments. Chouaib confirms
48 BMW entries. This scope does not cover other report families
or other IMSA championships.
A missing report must be documented, not equated with zero stops or
an absence of BMWs. Non-BMW entries are retained.

> Historical-status clarification: “active run” above refers to the recorded
> 2025-only validation, not a claim about the current reference. The current
> separate Gold covers 2023–2025; the 2025 figures and run identifier above are
> preserved as historical evidence. See [the Gold documentation](gold.fr.md).

## Progress by batch

1. Laguna Seca and Detroit batch completed: qualification followed by pipeline
   execution and output reading confirmed by Chouaib on November 12, 2026. The five
   races total 194 classified entries, including 22 BMW entries, and 1 915 detailed
   stops. Laguna Seca: one mismatch out of 36 (2,78 %); Detroit: none out of 22.
2. Sebring and Watkins Glen batch integrated: final Hour 12 and Hour 6 reports,
   without adding hourly cumulative totals. Chouaib confirms run
   `cf43b04e5ef849e38aafe0f07c16aec2`: 305 entries, including 32 BMW entries,
   3 018 matched and enriched stops, including 285 BMW stops.
3. Canadian Tire Motorsport Park and VIR batch integrated. Volumes confirmed by
   Chouaib: 363 entries, including 38 BMW entries; 3 183 stops, including 300 BMW stops;
   nine quality assessments. Absence of GTP consistent with the report categories.
4. Indianapolis and Road Atlanta integrated. All eleven events in the reference
   list are represented, each by a classification and a final stop report.
   Count mismatches are retained and do not constitute missing
   coverage. The test suite needs to be rerun to close out the delivery.

> Historical follow-up: the pending test-suite rerun in item 4 records that
> delivery stage. It is stale as a statement of current overall validation:
> the Gold documentation records a later first-publication check with 187 tests
> passed. This does not retroactively change the checks recorded for that batch.

For each batch: qualified documents, explicit configuration, execution,
per-race checks, mismatch documentation, and a local commit. No participant
volume or anomaly threshold is assumed to be identical across races.
The pipeline retains its rule rejecting incomplete enabled batches.

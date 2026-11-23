# Personal internship assignment — BMW racing data

Status reviewed on 23 November 2026. Public documentation is maintained in English;
historical filenames are retained to preserve existing links.

This is an independent educational portfolio project. BMW is the fictional
recipient of the presentation; no commission, affiliation, internship agreement
or validation by BMW is claimed.

## Business objective

Make race participation and pit-stop data accessible through a browser, with
sources, missing information and report discrepancies visible. Keep all
competitors in the analytical dataset so BMW entries can be compared in context.
A reported pit-stop duration is not a direct measure of mechanics' performance
or net time lost on track.

## Delivered scope and publication status

| Deliverable | Verified state |
| --- | --- |
| Common source manifest and multiformat execution | One manifest and one orchestrator for JSON classification/stops and CSV classification/PDF stops; no per-season production workflow. |
| Local coverage | 34 IMSA WeatherTech races: Daytona 2022 and eleven races in each of 2023, 2024 and 2025. Gold contains 1,453 participations, including 140 BMW. |
| Daytona 2022 integration | Enabled and validated end to end: 61 participants, 3 BMW and 1,762 extracted stops. |
| Layer responsibilities | Raw retains documents; Bronze extracts fields and provenance; Silver normalizes and applies explicit corrections; Gold combines checked results and reference evidence from Silver. |
| Local analytical publication | 45-column Gold, with versioned inputs and independent activation after validation. |
| Diagnosis | Logs identify run, stage and source where applicable; failures propagate. Quality reports retain nonblocking source discrepancies. |
| Remote prerequisites | 114-file archive renewed and restored for verification. Sixteen sporting columns added to MotherDuck history without changing its active run or public projection. |
| Hosted dashboard | Available with the previous publication: 1,392 participations, including 137 BMW, for 2023–2025. The local 2022 extension is not yet published there. |
| Validation | 222 passing unit and local integration tests; complete local rebuild and remote archive/schema checks performed separately. |

The original three-report pilot and its early figures describe earlier deliveries.
They are not the current acceptance baseline. Annual qualification reports remain
available as dated evidence; see the [project reference](project_reference.md).

## Acceptance criteria and evidence

1. **Reconstruction:** uv restores the locked environment. `run_pipeline.py`
   selects enabled report pairs and executes Raw, Bronze, processing and Gold.
   Cached source identity and format are verified before reuse.
2. **Preservation:** retain textual car numbers, source IDs, file fingerprints,
   raw duration/gap values and extraction locations where available. Missing
   observations remain NULL rather than becoming artificial zeros.
3. **Consistency:** reject missing/duplicate keys, stops without a matching
   classified participant, altered inputs, changed participant populations and
   content differences after writing. Reported-versus-observed count differences
   remain visible and do not alone reject the source.
4. **Corrections:** known exact-model manufacturer corrections are calculated in
   Silver, marked `matched_override`, and carried into Gold with origin
   `silver_override`. Raw/Bronze and reference evidence remain intact.
5. **Publication:** verify candidate files before activation. A failed Gold build
   retains the previous Gold reference. MotherDuck checks data and switches its
   active run inside one transaction; share provisioning is a separate operation.
6. **Demonstration:** consumers use the hosted dashboard without installing tools.
   Local and hosted coverage must be stated separately until deployment succeeds.
7. **Understanding:** explain the implemented execution chain, input/output
   contracts, failure paths and tests. A passing suite establishes tested software
   behavior; it does not independently establish authorship or interview readiness.

## Remaining delivery milestones

1. Review the completed changes in execution order, including their inputs,
   outputs, reasons and tests, before starting another implementation milestone.
2. Review the staged Git diff and create the local commit for the complete lot.
3. Push when authorized, check CI, then run the Gold publication workflow.
4. Verify the published run, 1,453 participants, 140 BMW and dashboard refresh.
5. Prepare the project demonstration and interview discussion around verified
   decisions, limitations and practical exercises.

## Later development

A dbt-duckdb pilot, pytest fixture consolidation and streaming integrity checks
are planned separately and are not implemented milestones. Wider car/motorcycle
coverage for 2022–2026 remains a research objective, not delivered coverage.
Additional sources require qualification before activation.

Concurrency, recovery after hardware failure, automatic remote revision detection
and a shared detailed-stop table are not established by this delivery. Machine
learning is not an acceptance criterion; future consumers must assess temporal
leakage and sporting comparability.

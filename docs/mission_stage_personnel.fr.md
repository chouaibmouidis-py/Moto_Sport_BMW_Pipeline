# Simulated personal internship assignment — BMW racing data

This document retains the original assignment and dated milestones. For current
coverage, including the separate 2023–2025 Gold publication, see the
[README](../README.md) and [Gold documentation](gold.fr.md).

Scoping version: November 10, 2026.
Local milestone update: November 12, 2026.

Independent educational project. BMW is the fictional recipient of the presentation: no commission, affiliation, internship agreement or validation by BMW is claimed. The portfolio deliverable will be presented as a personal project that used an AI tutor as a technical sparring partner (critical code review, architecture challenges and test scenarios).

## Business need

Enable a fictional sports analytics team to find BMW entries, their drivers and their stops, with verifiable race context and data quality.

The first results must answer three questions: which BMW entries appear in the available documents; which durations and driver changes are reported; and which information is missing, unreadable or inconsistent? A stop duration is not equated with mechanics' performance or a net loss of track time.

## Scope and progression

- Initial delivery baseline: three official IMSA 2025 reports, Road America, Long Beach and Daytona Hour 24; all competitors remain available to put BMW entries in context.
- Data: preserve source documents and empty fields in Bronze; represent populated fields in Silver, with the source values needed for diagnosis.
- Extension: assess and then integrate a first source with a different structure. The long-term goal remains to study BMW car and motorcycle participations across the 2022–2026 seasons; global coverage has not yet been demonstrated and will require a verified inventory.
- First integrated pilot: Road America Official classification, 48 participants, matched to stop reports. Batch extended and validated locally: Long Beach (27 participants) and Daytona Hour 24 (61 participants). The three classifications total 136 participations, including 13 BMW; their Silver projection remains partial and fields not projected remain in Bronze. Joins and quality summaries separate sources and their versions.
- Storage experiment: local emulation followed by targeted validation in a test cloud, with a budget agreed before use. No cloud deployment is required to accept the first local deliverable.

## Deliverables

1. Reproducible local pipeline with one command, source configuration and dependencies restorable with uv.
2. Separate Silver tables for session context per document, car entries, driver entries and stops; documented relationships and grains.
3. Quality reports and an enriched stop mart, accessible from a consistent active run.
4. Getting-started README, data dictionary, architecture and diagnosis/recovery procedure.
5. Business demonstration, assignment report and oral presentation covering limitations, test evidence and technical decisions.

## Acceptance criteria for the first local deliverable

- A documented procedure allows the environment to be restored and the launcher's five steps to be run from another directory.
- The eleven integrated stop reports produce the reference volumes: 507 car entries, 1 344 driver entries and 4 117 stops; the BMW filter returns 388 stops. The eleven classifications produce 469 participations, including 48 BMW. These numbers are references for this dataset, not universal business constants.
- The count summary is separate for each classification and version: Road America, 2 mismatches out of 48 (4,17 %); Long Beach, no `count_mismatch` out of 27; Daytona, 14 mismatches out of 61 (22,95 %). The Long Beach case without details remains flagged separately; this indicator does not measure all anomalies.
- Textual numbers, provenance and version are preserved; joins do not unintentionally add or remove stops.
- Conversions, keys, parent/child links and cumulative totals have tested valid and invalid scenarios. Absence and conversion failure are distinguished.
- The twelve files of a run are prepared and checked before activation, including the classification, its comparison with stops and the per-participant summary. This summary rejects missing or duplicate keys and lost or added participants. A simulated failure leaves the old reference usable. Readers select a single run per read.
- The test suite passes; the startup procedure and quality and mart readers are rerun as described in the README.
- Limitations are explicit: still few sources, dates without a confirmed timezone, conditions for sporting comparisons, and no validation of concurrency or recovery after a machine power loss.

## Milestones and coaching

1. Stabilize the reference reader, documentation and existing local workflow.
2. Assess a new source and document its differences before adapting the pipeline.
3. Consolidate business results and present the demonstration.
4. Conduct a code review and a graded practical assessment of the fundamentals required for independent work.

The pace respects Chouaib's work and availability; no delivery deadline is invented. Assessment distinguishes independent work, hints and supplied solutions. The project's test count is not a sufficient measure of independence. No message or deliverable will be sent to BMW without an explicit request.

# Gold participation contract

Implementation status reviewed on 24 November 2026. The original design was
written on 12 November; this contract now describes the implemented participant
publication. See [Gold operations](gold.fr.md) for snapshots and deployment.

## Grain and coverage

One row represents a classified participation identified by source_id,
bronze_sha256 and textual car_number. Missing or duplicate keys block publication.
Championship, season, event and session are explicit columns; consumers need not
decode source IDs to identify a race.

Local Gold covers Daytona 2022 and eleven races in each of 2023–2025: 1,453 rows,
including 140 BMW, across 45 columns. The maintainer confirmed publication of
this extended scope on the hosted dashboard. Coverage for other 2022 races, 2026 and
other championships remains outside the validated dataset.

Individual-stop and cross-format quality-summary Gold tables are not delivered
by this participant contract. Detailed stops and quality outputs exist upstream;
a shared detailed-stop publication needs its own grain, schema and acceptance.

## Consumption rules

- Keep classified participants without stop details. Missing counts and averages
  remain NULL rather than becoming zero.
- Retain raw durations and gaps alongside normalized values. Seconds and lap
  differences occupy separate numeric columns, with an explicit format kind.
- Preserve team, completed laps, fastest-lap number/speed and available timing
  fields from Silver. Unknown source values remain visible through raw fields.
- Treat count disagreement as a signal, not a correction or explanation of a
  race incident. Reject stops absent from the paired classification.
- Preserve known Silver manufacturer corrections and their origin/status.
  Unresolved reference names remain explicit; no partial-model inference is used.
- Compare sporting results only with stated context. Stop duration does not alone
  measure mechanics' performance. Later-season reference evidence needs temporal
  leakage assessment before predictive use.

## Traceability and publication

Gold reads a complete processing run, snapshots its declared outputs and relevant
SQL, and builds from the copies. It uses JSON Silver evidence for manufacturer
resolution; Bronze normalization is not repeated in Gold. Inputs include source
IDs, hashes and paths; inputs.json identifies the processing run and copied bytes.

Counts and EXCEPT ALL checks protect written content; keys and participant sets
are checked independently. All required outputs must succeed before local Gold
activation. MotherDuck publication inserts and validates data, changes the active
run and replaces the public view in one transaction. Share provisioning and
history-schema migration are separate responsibilities.

The 23 November remote migration added the 16 sporting columns without changing
historical rows or the active publication. A subsequent publication exposes the
expanded public schema together with its new run. Source archive renewal and
schema migration are not automatically performed on push.

## Evidence and limits

The pytest suite (296 tests and 97 subtests passing) includes preservation, invalid-input, mutation, failure,
rollback and migration scenarios. Real local reconstruction and remote archive
restoration were also checked. These checks do not establish completeness of
all reports, concurrent-publication safety or hardware-crash recovery. Preserve
the repository revision and locked environment as well as input snapshots for
reproduction after code changes.

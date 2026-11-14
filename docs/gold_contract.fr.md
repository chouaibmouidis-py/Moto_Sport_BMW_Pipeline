# Initial Gold layer contract

Historical design baseline. The implemented participation schema and publication
mechanism are documented in [Shared Gold](gold.fr.md). As of November 14, 2026,
that separate Gold publication covers 2023–2025; the JSON run remains independent.

Draft dated November 12, 2026, to be validated before making any delivery commitment.
The target historical coverage remains 2022–2026. As of November 13, 2026,
the WeatherTech 2024 and 2025 seasons are integrated for classifications and stops.
The eleven 2023 races have separate exploratory CSV/PDF summaries, without
integration into the active run. The 2022 and 2026 seasons still require assessment.

## Tables and grains

- Participation summary: one row per classification source and version,
  and textual car number. Race, season and championship must be exposed
  explicitly, without requiring the consumer to decode source_id.
- Stop details: one row per validated stop key within its report/version.
  Preserve the source-entry reference and links to drivers.
- Quality summary: one row per classification/version, with population, counts,
  percentages and status definitions.

## Consumption rules

Retain participants without details. A missing average remains NULL,
never zero by default. Present duration coverage and count agreement separately.
The denominator of the count_mismatch rate is all participants in the
classification; this indicator does not measure every error.
Durations are in seconds and do not measure mechanics' performance in isolation.
Any sporting comparison must state its contextual criteria explicitly.

## Traceability and acceptance

Retain references and hashes for both reports, transformation rules and the
publication run. Test keys, participant preservation, links, conversions and
separation between races/versions.
Provide a field dictionary and an SQL/notebook example for reading the active
run. A future AI consumer will use the same definitions, units and limitations;
this draft demonstrates no AI compatibility.

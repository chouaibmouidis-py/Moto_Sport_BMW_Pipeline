# Case handling in coherence rules

Source labels whose case has no business meaning must produce the same interpreted
value and coherence status when only their letter case changes. This is part of
the data contract, not a source anomaly to report. Case normalization applies to
comparison expressions; Raw/Bronze and retained source text are not overwritten.

## Rules currently audited

| Input | Rule | Output / status |
| --- | --- | --- |
| JSON/CSV gap_first_raw and gap_previous_raw | Compare lower(text) with the lap pattern. | Lap, lap, LAP and mixed-case variants have kind laps and the same lap count. Raw text remains available. |
| CSV car_model | Compare the normalized model name ignoring case, without partial matching. | Mercedes-AMG GT3 and Duqueine D08 corrections retain matched_override for all case variants. The original model spelling remains in car_model. |
| Silver manufacturer evidence | Count distinct lower(manufacturer) values per source constructor ID. | BMW/bmw/BmW represent one name and do not create false ambiguity. Distinct names or punctuation differences remain distinct. MIN retains one deterministic evidence spelling for display; evidence rows remain unchanged. |
| JSON air/track temperature | Recognize the existing Celsius unit ºC regardless of C/c. | Same numeric Celsius value and valid status; the raw temperature remains unchanged. Fahrenheit stays invalid and is not silently treated as Celsius. |

Other current quality statuses depend on numeric counts, nullability, numeric
conversions, numeric date formats or exact provenance/relationship keys. They do
not interpret case-sensitive source labels. Status names such as matched, time,
valid and missing are generated internal enums, not labels copied from reports.
Source textual classification/track statuses that are carried through without
interpretation are not silently renamed.

Identifiers, fingerprints, paths and source JSON keys remain exact. Case folding
is not fuzzy matching: it does not remove punctuation, merge different models,
accept unknown units or turn unsupported numeric syntax into valid data. The
existing numeric duration grammar continues to reject NaN/INF and scientific
notation regardless of case.

## Verification and maintenance

The common JSON/CSV gap test exercises both gap fields and case variants while
asserting retained text, kind and numerical outputs. Model tests verify the same
correction/status and preserved model spelling. Reference tests distinguish
case-only variants from real ambiguity and retain original evidence. Temperature
tests check both case equivalence and rejected units.

For any new source-label interpretation, explicitly define its case semantics and
add equivalent-case inputs with identical expected business outputs. A passing
existing suite does not establish coverage for rules added later.

These code changes affect subsequent processing/Gold builds. They do not mutate
existing input snapshots, rebuild active data or publish a remote run by themselves.

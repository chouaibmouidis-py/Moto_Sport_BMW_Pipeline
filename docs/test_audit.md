# Test audit

Historical test-consolidation audit. Its 186/188-method counts and module inventory
describe that audit only. The current suite has 222 passing tests as of 23 November
2026; see [the project reference](project_reference.md) for current validation,
including migration, archive pinning, logging and Daytona 2022 integration.

## Scope and execution

The audit covered the 51 tracked Python test modules present at its start,
their production functions and SQL queries. The baseline contained 188 passing
test methods. Assertions were reviewed for the observable behavior they protect,
including file contents, returned paths, SQL results, exceptions and active-run
references.

After consolidation and fixture corrections, all 186 test methods passed in
9.713 seconds. The maintained inventory now contains 50 Python test modules.
The HTTP status consolidation retains two cases within one method, and the
removed publication demonstration is replaced by the stronger Gold scenario.

Temporary in-memory code changes were used to check selected tests against
specific faults. These experiments exercised the production functions or SQL
with altered behavior. The working production implementation was preserved.

## Strengthened scenarios

| Area | Weakness found | Change |
| --- | --- | --- |
| PDF extraction | Already ordered fragments and identity coordinates allowed missing sorting and missing coordinate conversion to pass. | Emit fragments out of order with translated coordinates and retain exact extracted-record assertions. |
| Missing stop keys | The row lacking a pit number also lacked its source, masking removal of the pit-number check. | Add a row with only the pit number missing. |
| Driver keys | Missing source, version and parent-entry checks had no isolated examples. | Add one independently missing value for each component. |
| Session quality | Three fields were checked only through the total row count. | Vary all four field statuses independently and assert all 12 result rows. |
| Stop counts | Every row used car 24, allowing aggregation across cars to pass. | Add car 25 within the same source and version, with its own expected count. |
| Driver enrichment | Different-source and different-parent drivers were absent. | Add competing driver records with distinctive names and retain exact expected output rows. |
| PDF Bronze batches | Column count and three values did not establish exact schema or provenance. | Check all column names, types and values, including the PDF fingerprint and location fields. |
| Gold inputs | Checking only the number of archived inputs allowed input substitution. | Check the complete role, source-path and snapshot-path inventory. |
| Gold publication | The failure occurred before any output was written. | Build a valid previous run, publish the first candidate output, fail the second, then check the previous reference and output remain intact. |

The first six faults listed above comprise seven executable fault experiments,
because PDF sorting and coordinate conversion were checked separately. All seven
escaped their original targeted fixtures and were detected after strengthening
those fixtures.

## Consolidation and retained coverage

- HTTP 404 and 503 preservation cases share one test method with two subtests.
  Both response codes remain covered.
- The separate mixed-file publication demonstration was removed. Its successful
  and failed file writes are covered by writer tests, and partial publication is
  now exercised through the Gold builder with an active-reference assertion.
- The Gold snapshot test was retained. Fault experiments confirmed detection of
  a missing copy, incorrect recorded fingerprint and incorrect returned snapshot
  path. It also asserts the source path and role metadata. A separate experiment
  confirmed detection of a symbolic link substituted for an independent copy.
- SQL fixtures remain useful where their results distinguish a concrete broken
  query from the intended behavior. Input fixtures are selected to exercise
  grouping, source/version isolation, missing values and unmatched joins.
- Ignored local files `test_silver_pit_stops 2.py` and
  `test_silver_pit_stops 3.py` are historical drafts. Standard unittest discovery
  excludes those filenames. They are outside the maintained test inventory.

## Production findings requiring separate corrections

These findings were reproduced during the audit and remain open.

| Finding | Observable consequence | Owning code |
| --- | --- | --- |
| JSON pit-stop key checks omit `bronze_sha256`. | A missing fingerprint is accepted, and identical source/car/stop combinations from different Bronze versions are reported as duplicates. | `sql/08_check_missing_pit_stop_keys.sql`, `sql/09_check_duplicate_pit_stop_keys.sql` |
| Gold trusts the exploratory mart's catalog-derived location without checking the mart's event and season values. | A mart containing a different event/season can be activated under the selected input catalog. | `src/moto_sport_bmw_pipeline/gold.py` |
| Invalid downloaded JSON leaves its staging file behind. | A failed download preserves the previous final file but leaves a `.part` file. The staging name is shared by concurrent downloads to the same target. | `src/moto_sport_bmw_pipeline/raw_download.py` |

The audit establishes specific observed strengths and gaps. Further cases can
exercise final Gold activation replacement failures, logging-context restoration
and additional schema/format boundaries.

## Subsequent corrections

- The shared duration macro rejects non-finite components. Regression cases cover
  `NaN` and infinity in the supported duration layouts.
- Parquet publication derives its expected view from the supplied relation and
  removes its uniquely named internal views after success or failure.
- Pit-stop Raw filenames are read from the source manifest by both download and
  Bronze stages. A local integration scenario exercises a custom configured name.
- BMW exploration counters use normalized summary fields and return zero when
  the selected reports contain no detailed BMW stops.

## Run the suite

```sh
uv run python -m unittest discover -s tests -v
```

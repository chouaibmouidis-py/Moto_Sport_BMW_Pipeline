# Pytest migration

The local migration is complete on 25 November 2026. All 56 non-empty test
modules use native pytest functions; there are no TestCase classes, self.assert*
checks, setUp/tearDown methods or manually managed TemporaryDirectory blocks.
The empty archive-file-preparation draft remains untouched.

Pytest is a development dependency pinned in uv.lock. Pytest 9 supplies the
native subtests fixture without an additional plugin. unittest.mock is retained
only for mocks and patches; it is not the test runner or assertion framework.
Production Python modules, SQL and pipeline behavior are unchanged by this migration.

```bash
uv sync --locked
uv run --locked --no-sync python -m pytest -v
uv run --locked --no-sync python -m pytest tests/test_file_integrity.py -v
```

## Resources and isolation

- `connection` in tests/conftest.py opens a fresh in-memory DuckDB connection for
  each test and closes it after yield, including on failure.
- `tmp_path` supplies a separate temporary directory per test. Old pytest run
  directories can remain under pytest's retention policy; these are not live
  connections or shared mutable database state.
- `local_motherduck_connection_factory` creates connections attaching one local
  archive database within a single scenario. Reconnection can see that scenario's
  previous writes; another test receives a different directory. No remote
  credentials are required by these local archive checks.
- `context_caplog` adds the normal RunContextFilter to pytest's capture handler
  during a test and removes that exact filter in finally. Log records keep the
  run, stage and source fields without leaking filters to later tests.
- Module-local fixtures retain specialized prerequisites: file-integrity paths,
  download destinations, duration/session schemas, logger state and synthetic
  Gold project inputs. Logger handlers, levels and propagation are restored after
  the logging tests. Business rows and expected outputs remain visible in tests
  or their explicitly named preparation helpers.

Direct connection contexts remain where a helper or scenario deliberately opens
several connections. A fixture is not a reason to change reconnection behavior.

## Assertions and cases

Plain assert replaces unittest assertions. pytest.raises verifies exception types
and preserves existing regex checks through match=. ExceptionInfo.value exposes
captured exceptions. Counter comparisons retain unordered result multiplicities;
they do not replace exact content checks with row counts. Duration comparisons
retain the original places=3 absolute-difference semantics.

Independent input variants use pytest.mark.parametrize. Checks over the same
already-produced result retain native subtests: the first/previous gap format
matrix, the stages/sources emitted during one pipeline run, and import checks
within a shared mocked scope. This avoids rerunning an entire pipeline merely to
check another log record. Failed subtests still fail the containing test while
allowing later checks to execute.

Before the final migration batch, the full suite passed with 265 tests and 143
subtests. The final suite passes with **296 tests and 97 native subtests** in
**39.93 seconds**. Collection counts change when inner cases become independent
parameterized tests; they do not imply new behavioral coverage. A structural
audit against the pre-batch files retained all 225 test-function names and all
396 assertion/exception-check sites, and compared normalized SQL literals. The
57-file inventory includes the one empty draft; 56 modules contain actual tests.

The pre-batch run took 54.20 seconds. These are individual local observations,
not a controlled repeated benchmark or a guaranteed performance improvement.
Reduced repeated setup and clearer failure identification are direct maintenance
gains. No production throughput, peak-memory or cloud-cost gain was measured.

## Execution and next milestone

CI and the manual source-check workflow invoke pytest, so native functions are
collected. Tests run explicitly or through CI; starting the pipeline does not
implicitly execute the tests directory. Production data controls remain in their
own modules and still execute during applicable pipeline stages.

The migration does not implement single-read archival, streaming BLOB handling,
engine-side migration comparisons, candidate retention or dbt. New behavior still
starts with a contract and a meaningful failing test before implementation.

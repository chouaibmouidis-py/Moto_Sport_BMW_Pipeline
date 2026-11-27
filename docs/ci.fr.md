# Automated repository checks

`Pipeline CI` starts on pushes, pull requests and manual runs.
It installs Python 3.12 and the dependencies locked in `uv.lock`, then runs the
tests, checks both package entry points and validates manifest identifiers.
The shared local action `.github/actions/install-vortex` explicitly installs
and loads Vortex, then exports its extension directory for experimental tests.
The production Bronze remains Parquet and does not require Vortex to run.
Previous runs for the same ref are canceled when a new version arrives.
The GitHub token remains read-only.

The automated suite uses synthetic data, temporary files and mocked downloads.
The optional Detroit real-Raw qualification test explicitly skips when its local
report is absent; it is not counted as a real-data validation by CI. The complete
68-report experiment is a separate local command with recorded results.
Installing dependencies and the Vortex extension requires network access;
the tests themselves do not install extensions or download race reports.

The manual `Manual IMSA source smoke check` workflow retains the actual download
of a historical source. This check is not a full run of the seasons and may fail
when the provider is unavailable.

These two checks do not publish Parquet files or deploy the project.
After pushing, check their results in GitHub Actions. To make CI mandatory before
merging, subsequently configure a branch protection rule with the
`Python 3.12 tests` check: the YAML alone does not enforce this rule.

The configuration follows the official GitHub Actions syntax and uv integration:

- https://docs.github.com/en/actions/reference/workflows-and-actions/workflow-syntax
- https://docs.astral.sh/uv/guides/integration/github/

## Local test setup

From the repository root, install Vortex explicitly into a directory shared by
the installer and pytest.

```bash
uv sync --locked
export BMW_VORTEX_EXTENSION_DIRECTORY="${TMPDIR:-/tmp}/bmw-vortex-extensions"
uv run --locked --no-sync python -c 'import os, duckdb; c = duckdb.connect(config={"extension_directory": os.environ["BMW_VORTEX_EXTENSION_DIRECTORY"]}); c.execute("INSTALL vortex"); c.close()'
uv run --locked --no-sync python -m pytest -v
```

## Remote Gold publication

`Build and publish IMSA Gold` is a separate workflow, triggered manually or on
Mondays at 23:59 in `Africa/Casablanca`. It installs the locked orchestration
dependencies, installs the experimental test extension, runs pytest, initializes
temporary Airflow metadata and executes the seven-task
DAG with `airflow dags test`. This executes real tasks without hosting a
permanent scheduler or web interface.
If the pytest step fails, subsequent Airflow initialization/execution steps do not
run. This gate is configured in the workflow, not implicitly in Python main().
These workflow changes remain locally checked until an authorized push and remote run.

The DAG restores the pinned 114-file source archive, rebuilds both source-format
paths and publishes Gold to MotherDuck after validation. The repository secret
`MOTHERDUCK_TOKEN` is supplied through the environment. Concurrent executions of
this workflow are serialized, and Airflow logs are retained for seven days even
after failures. Manual publication has succeeded. Check actual scheduled runs in
GitHub Actions; the configured schedule alone does not establish their outcome.

The [live dashboard](https://bmw-imsa-analytics.streamlit.app/) reads the active
Gold share with a separate account. See the [hosting guide](dashboard_hosting.md).

The seven tasks are manifest validation, archive restoration, Raw, Bronze,
processing, Gold and MotherDuck publication. A push starts CI, not this workflow.
Source archival, additive history migration and share provisioning are separate
maintenance operations; `airflow db migrate` only initializes Airflow metadata.
The archive and remote history schema were prepared on 23 November 2026, and the
maintainer subsequently confirmed Daytona 2022 on the hosted dashboard. For the
later maintenance changes, verify CI after push, then dispatch publication when
a rebuild is required and check the published run/dashboard separately. Local
review and test execution do not dispatch this workflow.

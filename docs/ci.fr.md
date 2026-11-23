# Automated repository checks

`Pipeline CI` starts on pushes, pull requests and manual runs.
It installs Python 3.12 and the dependencies locked in `uv.lock`, then runs the
tests, checks both package entry points and validates manifest identifiers.
Previous runs for the same ref are canceled when a new version arrives.
The GitHub token remains read-only.

The tests use synthetic data, temporary files and mocked downloads.
They do not require the reports in `data/`.
Installing dependencies does, however, require network access.

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

## Remote Gold publication

`Build and publish IMSA Gold` is a separate workflow, triggered manually or on
Mondays at 23:59 in `Africa/Casablanca`. It installs the locked orchestration
dependencies, initializes temporary Airflow metadata and executes the seven-task
DAG with `airflow dags test`. This executes real tasks without hosting a
permanent scheduler or web interface.

The DAG restores the pinned 114-file source archive, rebuilds both source-format
paths and publishes Gold to MotherDuck after validation. The repository secret
`MOTHERDUCK_TOKEN` is supplied through the environment. Concurrent executions of
this workflow are serialized, and Airflow logs are retained for seven days even
after failures. The first manual remote execution succeeded; the first weekly
trigger remains to be observed.

The [live dashboard](https://bmw-imsa-analytics.streamlit.app/) reads the active
Gold share with a separate account. See the [hosting guide](dashboard_hosting.md).

The seven tasks are manifest validation, archive restoration, Raw, Bronze,
processing, Gold and MotherDuck publication. A push starts CI, not this workflow.
Source archival, additive history migration and share provisioning are separate
maintenance operations; `airflow db migrate` only initializes Airflow metadata.
On 23 November 2026 the archive and remote history schema were prepared for
Daytona 2022, but the new 1,453-participant Gold had not been deployed. After the
code and updated archive pin are pushed, verify CI and dispatch this workflow,
then check the published run and dashboard. No new workflow execution is claimed
by these local changes.

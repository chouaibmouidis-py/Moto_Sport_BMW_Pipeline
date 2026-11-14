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

These workflows do not publish Parquet files or deploy the project.
After pushing, check their results in GitHub Actions. To make CI mandatory before
merging, subsequently configure a branch protection rule with the
`Python 3.12 tests` check: the YAML alone does not enforce this rule.

The configuration follows the official GitHub Actions syntax and uv integration:

- https://docs.github.com/en/actions/reference/workflows-and-actions/workflow-syntax
- https://docs.astral.sh/uv/guides/integration/github/

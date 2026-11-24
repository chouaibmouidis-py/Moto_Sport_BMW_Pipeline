# Dashboard hosting

Live application: <https://bmw-imsa-analytics.streamlit.app/>

The dashboard reads `bmw_analytics.main.race_car_summary` through a read-only
MotherDuck share attached to the dedicated `bmw_dashboard` service account.
The publishing account and its token are not needed by the dashboard.

## Local configuration

Copy `.streamlit/secrets.toml.example` to `.streamlit/secrets.toml` and replace
the placeholder with the dashboard token. The real secrets file is ignored by
Git. Never add it to a commit or print its contents in logs.

```bash
uv run --locked --group orchestration streamlit run dashboard.py
```

The orchestration group keeps an existing local Airflow installation available;
the dashboard itself does not require Airflow.

## Streamlit Community Cloud

1. Sign in at <https://share.streamlit.io/> and connect the GitHub repository.
2. Select `chouaibmouidis-py/Moto_Sport_BMW_Pipeline`, branch `main`, entrypoint
   `dashboard.py`.
3. In Advanced settings, select Python **3.12** and enter the dashboard token in
   Secrets using the same TOML key as the example file. Save the secret in the
   hosting console, not in GitHub source files.
4. Deploy the app and verify the displayed publication ID, the three filters,
   quality signals, and the **Refresh data** button.
5. Verify the visitor link in a signed-out browser before sharing it.

Community Cloud recognizes the repository's `uv.lock`. No additional requirements
file is necessary. No local `data/` directory is required by this dashboard.

## Publication and refresh

Status reviewed on 24 November 2026: the maintainer confirmed the published
Daytona 2022 extension on the dashboard (1,453 participants, including 140 BMW).
The source archive contains 114 verified files. A push runs CI; later transformed
data must be published through the separate Gold workflow and its run ID/counts
verified. Schema migration and archive renewal do not themselves switch the public
run. Local tests of subsequent maintenance fixes are not proof of their deployment.

GitHub Actions restores the pinned source archive, executes the Airflow DAG,
and publishes a validated Gold run to MotherDuck. The dashboard reads the active
Gold view through the automatically updating share. Share propagation can add a
delay after the publisher commits.

The app caches a Gold snapshot for five minutes to reduce remote compute usage.
An active browser session checks for updates every five minutes; **Refresh data**
clears this cache and requests a fresh snapshot. Each update uses one snapshot
for all filters, metrics, charts and source references.

Free hosting can sleep when inactive and remains subject to the provider's
resource limits. MotherDuck Lite also has storage and compute caps. This setup
does not provide an uptime guarantee.

## Official references

- [Community Cloud deployment](https://docs.streamlit.io/deploy/streamlit-community-cloud/deploy-your-app/deploy)
- [Dependency selection](https://docs.streamlit.io/deploy/streamlit-community-cloud/deploy-your-app/app-dependencies)
- [Secrets management](https://docs.streamlit.io/deploy/streamlit-community-cloud/deploy-your-app/secrets-management)
- [Automatic fragment refresh](https://docs.streamlit.io/develop/api-reference/execution-flow/st.fragment)

"""Schedule the shared manifest-driven pipeline; never select work by season."""

import json
import pendulum
from airflow.sdk import DAG, task
from airflow.providers.standard.operators.bash import BashOperator
from moto_sport_bmw_pipeline.manifest import select_documents
from moto_sport_bmw_pipeline.paths import PROJECT_DIR

with DAG(dag_id="bmw_pipeline", start_date=pendulum.datetime(2026, 11, 18, tz="Africa/Casablanca"), schedule="59 23 * * 1", catchup=True, max_active_runs=1) as dag:
    @task
    def validate_manifest():
        manifest = json.loads((PROJECT_DIR / "config/sources.json").read_text(encoding="utf-8"))
        select_documents(manifest)

    validation = validate_manifest()
    restore = BashOperator(task_id="restore_sources", bash_command=".venv/bin/python restore_sources.py --destination .", cwd=str(PROJECT_DIR))
    previous = validation >> restore
    for stage in ("raw", "bronze", "process", "gold"):
        current = BashOperator(task_id=stage, bash_command=f".venv/bin/python run_pipeline.py --stage {stage}", cwd=str(PROJECT_DIR))
        previous >> current
        previous = current
    publish = BashOperator(task_id="publish_gold", bash_command=".venv/bin/python publish_motherduck.py", cwd=str(PROJECT_DIR))
    previous >> publish

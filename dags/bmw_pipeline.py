"""Orchestrate the BMW pipeline with Apache Airflow."""


import pendulum
import json
from airflow.sdk import DAG, task
from moto_sport_bmw_pipeline.manifest import validate_unique_source_ids
from moto_sport_bmw_pipeline.paths import PROJECT_DIR
from airflow.providers.standard.operators.bash import BashOperator

with DAG(
    dag_id = "bmw_pipeline",
    start_date= pendulum.datetime(2026, 11, 18, tz="Africa/Casablanca"),
    schedule= "59 23 * * 1",
    catchup= True,
    max_active_runs=1,
) as dag:

    @task
    def validate_manifest():
        manifest_path = PROJECT_DIR / "config" / "sources.json"
        with manifest_path.open("r", encoding="utf-8") as file:
            manifest = json.load(file)
            validate_unique_source_ids(manifest["documents"])
    manifest_validation = validate_manifest()

    prepare_pit_stop_row = BashOperator(
        task_id="prepare_pit_stop_raw",
        bash_command=".venv/bin/python inspect_manifest.py",
        cwd=str(PROJECT_DIR),
    )

    build_pit_stop_bronze = BashOperator(
        task_id="build_pit_stop_bronze",
        bash_command=".venv/bin/python build_bronze.py",
        cwd=str(PROJECT_DIR),
    )
    
    prepare_classification_raw = BashOperator(
        task_id="prepare_classification_raw",
        bash_command=".venv/bin/python inspect_classification.py",
        cwd=str(PROJECT_DIR),
    )

    build_classification_bronze = BashOperator(
        task_id="build_classification_bronze",
        bash_command=".venv/bin/python build_classification_bronze.py",
        cwd=str(PROJECT_DIR),
    )

    build_json_run = BashOperator(
        task_id="build_json_run",
        bash_command=".venv/bin/python analyze_bronze.py",
        cwd=str(PROJECT_DIR),
    )
    
    build_2023_classifications = BashOperator(
        task_id="build_2023_classifications",
        bash_command=".venv/bin/python explore_2023_season.py --classification-only",
        cwd=str(PROJECT_DIR),
    )

    build_2023_pdf_bronze = BashOperator(
        task_id="build_2023_pdf_bronze",
        bash_command=".venv/bin/python explore_2023_season.py --pdf-bronze-only",
        cwd=str(PROJECT_DIR),
    )

    build_2023_pdf_silver = BashOperator(
        task_id="build_2023_pdf_silver",
        bash_command=".venv/bin/python explore_2023_season.py --pdf-silver-only",
        cwd=str(PROJECT_DIR),
    )

    build_2023_marts = BashOperator(
        task_id="build_2023_marts",
        bash_command=".venv/bin/python explore_2023_season.py --mart-only",
        cwd=str(PROJECT_DIR),
    )

    build_gold = BashOperator(
        task_id="build_gold",
        bash_command=".venv/bin/python build_gold.py",
        cwd=str(PROJECT_DIR),
    )

    restore_sources = BashOperator(
        task_id="restore_sources",
        bash_command=".venv/bin/python restore_sources.py --destination .",
        cwd=str(PROJECT_DIR),
    )

    publish_gold = BashOperator(
        task_id="publish_gold",
        bash_command=".venv/bin/python publish_motherduck.py",
        cwd=str(PROJECT_DIR),
    )

    (
        manifest_validation
        >> restore_sources
        >> prepare_pit_stop_row
        >> build_pit_stop_bronze
        >> prepare_classification_raw
        >> build_classification_bronze
        >> build_json_run
        >> build_2023_classifications
        >> build_2023_pdf_bronze
        >> build_2023_pdf_silver
        >> build_2023_marts
        >> build_gold
        >> publish_gold
    )
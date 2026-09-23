"""Orquestração do pipeline de gastos públicos municipais."""

from datetime import timedelta

import pendulum
from airflow.providers.standard.operators.bash import BashOperator
from airflow.sdk import DAG
from src.observability.airflow_callbacks import (
    record_dag_failure,
    record_dag_success,
)

PROJECT_ROOT = "/opt/airflow/project"

default_args = {
    "owner": "engenharia-de-dados",
    "retries": 2,
    "retry_delay": timedelta(minutes=5),
}


with DAG(
    dag_id="gastos_publicos_salto",
    description=(
        "Atualiza a Bronze do TCE-SP e reconstrói as camadas Silver e Gold."
    ),
    default_args=default_args,
    start_date=pendulum.datetime(
        2026,
        9,
        20,
        tz="America/Sao_Paulo",
    ),
    schedule="0 10 * * 1",
    catchup=False,
    max_active_runs=1,
    on_success_callback=record_dag_success,
    on_failure_callback=record_dag_failure,
    tags=[
        "tce-sp",
        "salto",
        "engenharia-de-dados",
    ],
) as dag:
    atualizar_bronze = BashOperator(
        task_id="atualizar_bronze",
        bash_command=(
            "python -u -m src.ingestion.tce_sp.recurring  "
            "{% if dag_run and dag_run.conf.get('dry_run', false) %}"
            "--dry-run"
            "{% endif %}"
        ),
        cwd=PROJECT_ROOT,
        execution_timeout=timedelta(hours=2),
    )

    transformar_e_testar = BashOperator(
        task_id="transformar_e_testar",
        bash_command="./scripts/dbt.sh build",
        cwd=PROJECT_ROOT,
        execution_timeout=timedelta(minutes=30),
    )

    exportar_power_bi = BashOperator(
        task_id="exportar_power_bi",
        bash_command="python -m src.serving.export_power_bi",
        cwd=PROJECT_ROOT,
        execution_timeout=timedelta(minutes=15),
    )

    atualizar_bronze >> transformar_e_testar >> exportar_power_bi

"""Callbacks de observabilidade das execuções do Airflow."""

from datetime import datetime, timezone
from typing import Any

from src.observability.pipeline_runs import (
    append_pipeline_run,
    build_pipeline_run_record,
)


def get_execution_source(dag_run: Any) -> str:
    """Identifica se a execução foi manual ou agendada."""
    run_type = getattr(dag_run, "run_type", None)

    if run_type is None:
        return "airflow"

    return str(
        getattr(run_type, "value", run_type)
    )


def get_dry_run(dag_run: Any) -> bool:
    """Obtém o parâmetro dry_run da configuração da DAG."""
    configuration = getattr(dag_run, "conf", None) or {}

    return bool(configuration.get("dry_run", False))


def record_dag_result(
    context: dict[str, Any],
    status: str,
) -> None:
    """Registra o resultado final de uma execução da DAG."""
    dag_run = context["dag_run"]

    started_at = (
        getattr(dag_run, "start_date", None)
        or datetime.now(timezone.utc)
    )
    completed_at = datetime.now(timezone.utc)

    failed_stage: str | None = None
    error_message: str | None = None

    if status == "failed":
        task_instance = context.get("task_instance")

        if task_instance is not None:
            failed_stage = task_instance.task_id

        exception = context.get("exception")

        if exception is not None:
            error_message = str(exception)

    record = build_pipeline_run_record(
        run_id=dag_run.run_id,
        execution_source=get_execution_source(dag_run),
        status=status,
        started_at=started_at,
        completed_at=completed_at,
        dry_run=get_dry_run(dag_run),
        failed_stage=failed_stage,
        error_message=error_message,
    )

    append_pipeline_run(record)


def record_dag_success(context: dict[str, Any]) -> None:
    """Registra uma execução concluída com sucesso."""
    record_dag_result(
        context=context,
        status="success",
    )


def record_dag_failure(context: dict[str, Any]) -> None:
    """Registra uma execução concluída com falha."""
    record_dag_result(
        context=context,
        status="failed",
    )

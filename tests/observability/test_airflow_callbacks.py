"""Testes dos callbacks de observabilidade do Airflow."""

from datetime import datetime, timezone
from types import SimpleNamespace
from unittest.mock import patch

from src.observability.airflow_callbacks import (
    get_dry_run,
    get_execution_source,
    record_dag_failure,
    record_dag_success,
)


def create_dag_run(
    *,
    run_id: str = "manual__2026-09-23",
    run_type: str = "manual",
    dry_run: bool = False,
) -> SimpleNamespace:
    """Cria uma representação mínima de uma execução da DAG."""
    return SimpleNamespace(
        run_id=run_id,
        run_type=run_type,
        conf={"dry_run": dry_run},
        start_date=datetime(
            2026,
            9,
            23,
            10,
            0,
            0,
            tzinfo=timezone.utc,
        ),
    )


def test_identifies_execution_source() -> None:
    """Identifica a origem da execução."""
    dag_run = create_dag_run(
        run_type="scheduled",
    )

    assert get_execution_source(dag_run) == "scheduled"


def test_reads_dry_run_configuration() -> None:
    """Lê o parâmetro dry_run da configuração."""
    dag_run = create_dag_run(
        dry_run=True,
    )

    assert get_dry_run(dag_run) is True


@patch(
    "src.observability.airflow_callbacks."
    "append_pipeline_run"
)
def test_records_successful_dag_run(
    append_mock,
) -> None:
    """Registra uma execução bem-sucedida."""
    dag_run = create_dag_run(
        run_id="manual-success",
        dry_run=True,
    )

    record_dag_success(
        {
            "dag_run": dag_run,
            "task_instance": SimpleNamespace(
                task_id="exportar_power_bi"
            ),
        }
    )

    append_mock.assert_called_once()

    record = append_mock.call_args.args[0]

    assert record["run_id"] == "manual-success"
    assert record["execution_source"] == "manual"
    assert record["status"] == "success"
    assert record["dry_run"] is True
    assert record["failed_stage"] is None
    assert record["error_message"] is None
    assert record["duration_seconds"] >= 0


@patch(
    "src.observability.airflow_callbacks."
    "append_pipeline_run"
)
def test_records_failed_dag_run(
    append_mock,
) -> None:
    """Registra a tarefa e a mensagem da falha."""
    dag_run = create_dag_run(
        run_id="manual-failure",
    )

    record_dag_failure(
        {
            "dag_run": dag_run,
            "task_instance": SimpleNamespace(
                task_id="transformar_e_testar"
            ),
            "exception": RuntimeError(
                "dbt build retornou código 1."
            ),
        }
    )

    append_mock.assert_called_once()

    record = append_mock.call_args.args[0]

    assert record["run_id"] == "manual-failure"
    assert record["status"] == "failed"
    assert record["failed_stage"] == (
        "transformar_e_testar"
    )
    assert record["error_message"] == (
        "dbt build retornou código 1."
    )


def test_handles_missing_configuration() -> None:
    """Assume execução real quando a configuração está ausente."""
    dag_run = SimpleNamespace(
        run_id="scheduled-001",
        run_type="scheduled",
        conf=None,
        start_date=datetime.now(timezone.utc),
    )

    assert get_dry_run(dag_run) is False

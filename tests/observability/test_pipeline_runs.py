"""Testes do registro operacional das execuções do pipeline."""

import json
from datetime import datetime, timezone
from pathlib import Path

import pytest

from src.observability.pipeline_runs import (
    append_pipeline_run,
    build_pipeline_run_record,
)


def test_builds_successful_pipeline_run() -> None:
    """Cria um registro de execução concluída com sucesso."""
    started_at = datetime(
        2026,
        9,
        23,
        10,
        0,
        0,
        tzinfo=timezone.utc,
    )
    completed_at = datetime(
        2026,
        9,
        23,
        10,
        2,
        30,
        tzinfo=timezone.utc,
    )

    record = build_pipeline_run_record(
        run_id="manual-001",
        execution_source="manual",
        status="success",
        started_at=started_at,
        completed_at=completed_at,
        dry_run=False,
    )

    assert record["run_id"] == "manual-001"
    assert record["execution_source"] == "manual"
    assert record["status"] == "success"
    assert record["dry_run"] is False
    assert record["duration_seconds"] == 150.0
    assert record["failed_stage"] is None
    assert record["error_message"] is None


def test_builds_failed_pipeline_run() -> None:
    """Cria um registro com a etapa e a mensagem da falha."""
    started_at = datetime(
        2026,
        9,
        23,
        10,
        0,
        0,
        tzinfo=timezone.utc,
    )
    completed_at = datetime(
        2026,
        9,
        23,
        10,
        0,
        45,
        tzinfo=timezone.utc,
    )

    record = build_pipeline_run_record(
        run_id="airflow-001",
        execution_source="airflow",
        status="failed",
        started_at=started_at,
        completed_at=completed_at,
        dry_run=True,
        failed_stage="transformar_e_testar",
        error_message="dbt build retornou código 1.",
    )

    assert record["status"] == "failed"
    assert record["dry_run"] is True
    assert record["duration_seconds"] == 45.0
    assert record["failed_stage"] == "transformar_e_testar"
    assert record["error_message"] == "dbt build retornou código 1."


def test_rejects_invalid_pipeline_status() -> None:
    """Rejeita status que não pertence ao contrato operacional."""
    current_time = datetime.now(timezone.utc)

    with pytest.raises(
        ValueError,
        match="Status inválido para o pipeline",
    ):
        build_pipeline_run_record(
            run_id="run-001",
            execution_source="manual",
            status="running",
            started_at=current_time,
            completed_at=current_time,
            dry_run=False,
        )


def test_rejects_failed_stage_on_success() -> None:
    """Impede que uma execução bem-sucedida registre etapa com falha."""
    current_time = datetime.now(timezone.utc)

    with pytest.raises(
        ValueError,
        match="sucesso não pode possuir etapa com falha",
    ):
        build_pipeline_run_record(
            run_id="run-001",
            execution_source="airflow",
            status="success",
            started_at=current_time,
            completed_at=current_time,
            dry_run=False,
            failed_stage="exportar_power_bi",
        )


def test_appends_pipeline_runs_as_json_lines(
    tmp_path: Path,
) -> None:
    """Acrescenta execuções sem sobrescrever registros anteriores."""
    output_path = tmp_path / "pipeline_runs.jsonl"

    first_record = {
        "run_id": "run-001",
        "status": "success",
    }
    second_record = {
        "run_id": "run-002",
        "status": "failed",
    }

    append_pipeline_run(
        record=first_record,
        output_path=output_path,
    )
    append_pipeline_run(
        record=second_record,
        output_path=output_path,
    )

    lines = output_path.read_text(
        encoding="utf-8",
    ).splitlines()

    assert len(lines) == 2
    assert json.loads(lines[0]) == first_record
    assert json.loads(lines[1]) == second_record

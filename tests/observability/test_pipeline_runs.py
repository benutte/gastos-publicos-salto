"""Testes do registro operacional das execuções do pipeline."""

import json
from datetime import datetime, timezone
from pathlib import Path

import pytest

from src.observability.pipeline_runs import (
    append_pipeline_run,
    build_pipeline_run_record,
)

from src.observability.pipeline_runs import (
    append_pipeline_run,
    build_pipeline_run_record,
    read_pipeline_runs,
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


def test_reads_and_normalizes_pipeline_runs(
    tmp_path: Path,
) -> None:
    """Lê e normaliza execuções completas do pipeline."""
    input_path = tmp_path / "pipeline_runs.jsonl"

    records = [
        {
            "run_id": "manual-001",
            "execution_source": "manual",
            "status": "success",
            "dry_run": True,
            "started_at_utc": (
                "2026-09-23T10:00:00+00:00"
            ),
            "completed_at_utc": (
                "2026-09-23T10:00:30+00:00"
            ),
            "duration_seconds": 30.0,
            "failed_stage": None,
            "error_message": None,
        },
        {
            "run_id": "scheduled-001",
            "execution_source": "scheduled",
            "status": "failed",
            "dry_run": False,
            "started_at_utc": (
                "2026-09-23T11:00:00+00:00"
            ),
            "completed_at_utc": (
                "2026-09-23T11:00:45+00:00"
            ),
            "duration_seconds": 45.0,
            "failed_stage": "transformar_e_testar",
            "error_message": "dbt build falhou.",
        },
    ]

    for record in records:
        append_pipeline_run(
            record=record,
            output_path=input_path,
        )

    normalized_records = read_pipeline_runs(
        input_path=input_path,
    )

    assert len(normalized_records) == 2

    assert normalized_records[0]["run_id"] == "manual-001"
    assert normalized_records[0]["status"] == "success"
    assert normalized_records[0]["dry_run"] is True
    assert normalized_records[0]["duration_seconds"] == 30.0
    assert normalized_records[0]["manifest_line_number"] == 1

    assert normalized_records[1]["status"] == "failed"
    assert normalized_records[1]["failed_stage"] == (
        "transformar_e_testar"
    )
    assert normalized_records[1]["manifest_line_number"] == 2


def test_returns_empty_list_when_manifest_does_not_exist(
    tmp_path: Path,
) -> None:
    """Retorna uma lista vazia quando ainda não há execuções."""
    input_path = tmp_path / "missing.jsonl"

    assert read_pipeline_runs(input_path=input_path) == []


def test_rejects_invalid_pipeline_run_json(
    tmp_path: Path,
) -> None:
    """Rejeita uma linha que não possui JSON válido."""
    input_path = tmp_path / "pipeline_runs.jsonl"

    input_path.write_text(
        '{"run_id": "incompleto"\n',
        encoding="utf-8",
    )

    with pytest.raises(
        ValueError,
        match="JSON inválido no manifesto do pipeline",
    ):
        read_pipeline_runs(input_path=input_path)


def test_rejects_pipeline_run_with_missing_fields(
    tmp_path: Path,
) -> None:
    """Rejeita uma execução sem campos obrigatórios."""
    input_path = tmp_path / "pipeline_runs.jsonl"

    append_pipeline_run(
        record={
            "run_id": "run-001",
            "status": "success",
        },
        output_path=input_path,
    )

    with pytest.raises(
        ValueError,
        match="campos obrigatórios ausentes",
    ):
        read_pipeline_runs(input_path=input_path)
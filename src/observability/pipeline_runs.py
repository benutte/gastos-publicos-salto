"""Registro operacional das execuções completas do pipeline."""

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


DEFAULT_PIPELINE_RUNS_PATH = Path(
    "data/metadata/pipeline_runs.jsonl"
)

VALID_PIPELINE_STATUSES = {
    "success",
    "failed",
}


def utc_now() -> datetime:
    """Retorna o horário atual em UTC."""
    return datetime.now(timezone.utc)


def calculate_duration_seconds(
    started_at: datetime,
    completed_at: datetime,
) -> float:
    """Calcula a duração total da execução."""
    return (completed_at - started_at).total_seconds()


def build_pipeline_run_record(
    *,
    run_id: str,
    execution_source: str,
    status: str,
    started_at: datetime,
    completed_at: datetime,
    dry_run: bool,
    failed_stage: str | None = None,
    error_message: str | None = None,
) -> dict[str, Any]:
    """Constrói um registro operacional do pipeline."""
    if status not in VALID_PIPELINE_STATUSES:
        raise ValueError(
            f"Status inválido para o pipeline: {status}."
        )

    if status == "success" and failed_stage is not None:
        raise ValueError(
            "Uma execução com sucesso não pode possuir etapa com falha."
        )

    return {
        "run_id": run_id,
        "execution_source": execution_source,
        "status": status,
        "dry_run": dry_run,
        "started_at_utc": started_at.isoformat(),
        "completed_at_utc": completed_at.isoformat(),
        "duration_seconds": calculate_duration_seconds(
            started_at=started_at,
            completed_at=completed_at,
        ),
        "failed_stage": failed_stage,
        "error_message": error_message,
    }


def append_pipeline_run(
    record: dict[str, Any],
    output_path: Path = DEFAULT_PIPELINE_RUNS_PATH,
) -> None:
    """Acrescenta uma execução ao manifesto operacional."""
    output_path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    serialized_record = json.dumps(
        record,
        ensure_ascii=False,
        sort_keys=True,
    )

    with output_path.open(
        "a",
        encoding="utf-8",
    ) as output_file:
        output_file.write(serialized_record)
        output_file.write("\n")

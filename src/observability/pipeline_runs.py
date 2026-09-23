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

def read_pipeline_runs(
    input_path: Path = DEFAULT_PIPELINE_RUNS_PATH,
) -> list[dict[str, Any]]:
    """Lê e valida as execuções completas do pipeline.

    Args:
        input_path: Caminho do manifesto JSON Lines do pipeline.

    Returns:
        Lista de execuções normalizadas na ordem do manifesto.

    Raises:
        ValueError: Se uma linha estiver vazia, possuir JSON inválido,
            campos obrigatórios ausentes ou status desconhecido.
    """
    if not input_path.exists():
        return []

    records: list[dict[str, Any]] = []

    with input_path.open(
        "r",
        encoding="utf-8",
    ) as input_file:
        for line_number, line in enumerate(
            input_file,
            start=1,
        ):
            stripped_line = line.strip()

            if not stripped_line:
                raise ValueError(
                    f"Linha {line_number}: linha vazia "
                    "no manifesto do pipeline."
                )

            try:
                record = json.loads(stripped_line)
            except json.JSONDecodeError as error:
                raise ValueError(
                    f"Linha {line_number}: JSON inválido "
                    "no manifesto do pipeline."
                ) from error

            if not isinstance(record, dict):
                raise ValueError(
                    f"Linha {line_number}: o registro deve "
                    "ser um objeto JSON."
                )

            required_fields = {
                "run_id",
                "execution_source",
                "status",
                "dry_run",
                "started_at_utc",
                "completed_at_utc",
                "duration_seconds",
            }

            missing_fields = sorted(
                required_fields - record.keys()
            )

            if missing_fields:
                raise ValueError(
                    f"Linha {line_number}: campos obrigatórios "
                    f"ausentes: {', '.join(missing_fields)}."
                )

            status = str(record["status"])

            if status not in VALID_PIPELINE_STATUSES:
                raise ValueError(
                    f"Linha {line_number}: status inválido: "
                    f"{status}."
                )

            records.append(
                {
                    "run_id": str(record["run_id"]),
                    "execution_source": str(
                        record["execution_source"]
                    ),
                    "status": status,
                    "dry_run": bool(record["dry_run"]),
                    "started_at_utc": datetime.fromisoformat(
                        str(record["started_at_utc"])
                    ),
                    "completed_at_utc": datetime.fromisoformat(
                        str(record["completed_at_utc"])
                    ),
                    "duration_seconds": float(
                        record["duration_seconds"]
                    ),
                    "failed_stage": record.get(
                        "failed_stage"
                    ),
                    "error_message": record.get(
                        "error_message"
                    ),
                    "manifest_line_number": line_number,
                }
            )

    return records
"""Leitura e normalização das execuções registradas no manifesto Bronze."""

import json
from datetime import datetime
from pathlib import Path
from typing import Any


VALID_STATUSES = {"success", "empty", "failed"}


def parse_utc_datetime(value: str | None) -> datetime | None:
    """Converte um timestamp ISO 8601 para datetime."""
    if not value:
        return None

    return datetime.fromisoformat(
        value.replace("Z", "+00:00")
    )


def calculate_duration_seconds(
    started_at: datetime | None,
    completed_at: datetime | None,
) -> float | None:
    """Calcula a duração da execução em segundos."""
    if started_at is None or completed_at is None:
        return None

    return (completed_at - started_at).total_seconds()


def normalize_manifest_record(
    record: dict[str, Any],
    line_number: int,
) -> dict[str, Any]:
    """Normaliza um registro do manifesto de ingestão."""
    required_fields = {
        "run_id",
        "status",
        "dataset",
        "municipality",
        "year",
        "month",
    }

    missing_fields = sorted(
        required_fields - record.keys()
    )

    if missing_fields:
        raise ValueError(
            f"Linha {line_number}: "
            "campos obrigatórios ausentes: "
            f"{', '.join(missing_fields)}."
        )

    status = record["status"]

    if status not in VALID_STATUSES:
        raise ValueError(
            f"Linha {line_number}: "
            f"status inválido: {status}."
        )

    started_at = parse_utc_datetime(
        record.get("started_at_utc")
    )

    completed_at = parse_utc_datetime(
        record.get("completed_at_utc")
        or record.get("extracted_at_utc")
    )

    return {
        "run_id": str(record["run_id"]),
        "status": status,
        "dataset": str(record["dataset"]),
        "municipality": str(record["municipality"]),
        "year": int(record["year"]),
        "month": int(record["month"]),
        "source_url": record.get("source_url"),
        "record_count": int(
            record.get("record_count") or 0
        ),
        "content_length_bytes": (
            int(record["content_length_bytes"])
            if record.get("content_length_bytes")
            is not None
            else None
        ),
        "sha256": record.get("sha256"),
        "started_at_utc": started_at,
        "completed_at_utc": completed_at,
        "duration_seconds": calculate_duration_seconds(
            started_at=started_at,
            completed_at=completed_at,
        ),
        "output_path": record.get("output_path"),
        "error_type": record.get("error_type"),
        "error_message": record.get("error_message"),
        "manifest_line_number": line_number,
    }


def read_ingestion_manifest(
    manifest_path: Path,
) -> list[dict[str, Any]]:
    """Lê e normaliza todas as execuções do manifesto Bronze."""
    if not manifest_path.exists():
        raise FileNotFoundError(
            "Manifesto de ingestão não encontrado: "
            f"{manifest_path}"
        )

    normalized_records: list[dict[str, Any]] = []

    with manifest_path.open(
        encoding="utf-8"
    ) as manifest_file:
        for line_number, line in enumerate(
            manifest_file,
            start=1,
        ):
            stripped_line = line.strip()

            if not stripped_line:
                raise ValueError(
                    f"Linha {line_number}: "
                    "linha vazia no manifesto."
                )

            try:
                record = json.loads(stripped_line)
            except json.JSONDecodeError as error:
                raise ValueError(
                    f"Linha {line_number}: JSON inválido."
                ) from error

            if not isinstance(record, dict):
                raise ValueError(
                    f"Linha {line_number}: "
                    "o registro deve ser um objeto JSON."
                )

            normalized_records.append(
                normalize_manifest_record(
                    record=record,
                    line_number=line_number,
                )
            )

    return normalized_records
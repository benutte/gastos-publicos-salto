"""Testes da leitura do manifesto para observabilidade."""

import json
from pathlib import Path

import pytest

from src.observability.ingestion_runs import read_ingestion_manifest


def write_manifest(
    path: Path,
    records: list[dict[str, object]],
) -> None:
    """Grava registros no formato JSON Lines."""
    path.parent.mkdir(parents=True, exist_ok=True)

    content = "\n".join(
        json.dumps(record, ensure_ascii=False)
        for record in records
    )

    path.write_text(
        f"{content}\n",
        encoding="utf-8",
    )


def create_valid_record(
    status: str = "success",
) -> dict[str, object]:
    """Cria um registro válido usado pelos testes."""
    return {
        "run_id": "run-001",
        "status": status,
        "dataset": "despesas",
        "municipality": "salto",
        "year": 2026,
        "month": 9,
        "source_url": "https://example.test/despesas",
        "record_count": 10 if status == "success" else 0,
        "content_length_bytes": 100,
        "sha256": "abc123",
        "started_at_utc": "2026-09-20T10:00:00+00:00",
        "completed_at_utc": "2026-09-20T10:00:02.500000+00:00",
        "output_path": "data/bronze/example.json",
        "error_type": None,
        "error_message": None,
    }


def test_reads_and_normalizes_manifest(
    tmp_path: Path,
) -> None:
    """Normaliza tipos e calcula a duração da execução."""
    manifest_path = tmp_path / "manifest.jsonl"

    write_manifest(
        manifest_path,
        [
            create_valid_record("success"),
            {
                **create_valid_record("empty"),
                "run_id": "run-002",
            },
        ],
    )

    records = read_ingestion_manifest(manifest_path)

    assert len(records) == 2
    assert records[0]["run_id"] == "run-001"
    assert records[0]["duration_seconds"] == 2.5
    assert records[0]["record_count"] == 10
    assert records[0]["manifest_line_number"] == 1

    assert records[1]["status"] == "empty"
    assert records[1]["record_count"] == 0
    assert records[1]["manifest_line_number"] == 2


def test_rejects_invalid_json(tmp_path: Path) -> None:
    """Rejeita uma linha que não contém JSON válido."""
    manifest_path = tmp_path / "manifest.jsonl"

    manifest_path.write_text(
        '{"run_id": "incompleto"\n',
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="JSON inválido"):
        read_ingestion_manifest(manifest_path)


def test_rejects_missing_required_fields(
    tmp_path: Path,
) -> None:
    """Rejeita registros sem campos operacionais obrigatórios."""
    manifest_path = tmp_path / "manifest.jsonl"

    write_manifest(
        manifest_path,
        [
            {
                "run_id": "run-001",
                "status": "success",
            }
        ],
    )

    with pytest.raises(
        ValueError,
        match="campos obrigatórios ausentes",
    ):
        read_ingestion_manifest(manifest_path)


def test_rejects_invalid_status(tmp_path: Path) -> None:
    """Rejeita status fora do contrato do manifesto."""
    manifest_path = tmp_path / "manifest.jsonl"

    write_manifest(
        manifest_path,
        [create_valid_record("unknown")],
    )

    with pytest.raises(ValueError, match="status inválido"):
        read_ingestion_manifest(manifest_path)


def test_rejects_missing_manifest(tmp_path: Path) -> None:
    """Informa quando o manifesto não existe."""
    manifest_path = tmp_path / "missing.jsonl"

    with pytest.raises(
        FileNotFoundError,
        match="Manifesto de ingestão não encontrado",
    ):
        read_ingestion_manifest(manifest_path)

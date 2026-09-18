"""Testes do perfilador de esquemas da camada Bronze."""

import json
from pathlib import Path

import pytest

from src.ingestion.tce_sp.schema_profiler import profile_dataset


def write_json(path: Path, payload: object) -> None:
    """Grava um conteúdo JSON usado pelos testes."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, ensure_ascii=False),
        encoding="utf-8",
    )


def test_profiles_all_records_and_empty_files(tmp_path: Path) -> None:
    """Identifica esquemas distintos e arquivos vazios."""
    bronze_path = tmp_path / "bronze"

    first_file = (
        bronze_path
        / "despesas"
        / "municipio=salto"
        / "exercicio=2020"
        / "mes=01"
        / "first.json"
    )
    empty_file = (
        bronze_path
        / "despesas"
        / "municipio=salto"
        / "exercicio=2020"
        / "mes=02"
        / "empty.json"
    )

    write_json(
        first_file,
        [
            {"orgao": "Prefeitura", "valor": "10,00"},
            {
                "orgao": "Prefeitura",
                "valor": "20,00",
                "campo_novo": "exemplo",
            },
        ],
    )
    write_json(empty_file, [])

    profile = profile_dataset(bronze_path, "despesas")

    assert profile.total_files == 2
    assert profile.total_records == 2
    assert profile.empty_files == [empty_file]
    assert len(profile.schema_files) == 2
    assert ("orgao", "valor") in profile.schema_files
    assert ("campo_novo", "orgao", "valor") in profile.schema_files


def test_rejects_non_list_json(tmp_path: Path) -> None:
    """Rejeita um arquivo cujo conteúdo principal não seja uma lista."""
    bronze_path = tmp_path / "bronze"
    invalid_file = (
        bronze_path
        / "receitas"
        / "municipio=salto"
        / "exercicio=2020"
        / "mes=01"
        / "invalid.json"
    )

    write_json(invalid_file, {"orgao": "Prefeitura"})

    with pytest.raises(ValueError, match="não contém uma lista JSON"):
        profile_dataset(bronze_path, "receitas")

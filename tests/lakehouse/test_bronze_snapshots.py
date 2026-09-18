"""Testes da seleção de snapshots da camada Bronze."""

from pathlib import Path

import pytest

from src.lakehouse.bronze_snapshots import select_latest_snapshots


def create_snapshot(path: Path) -> None:
    """Cria um arquivo JSON mínimo para representar um snapshot."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("[]", encoding="utf-8")


def test_selects_latest_snapshot_from_each_partition(
    tmp_path: Path,
) -> None:
    """Seleciona somente o snapshot mais recente de cada mês."""
    bronze_path = tmp_path / "tce_sp"

    january_path = (
        bronze_path
        / "despesas"
        / "municipio=salto"
        / "exercicio=2026"
        / "mes=01"
    )
    february_path = (
        bronze_path
        / "despesas"
        / "municipio=salto"
        / "exercicio=2026"
        / "mes=02"
    )

    january_old = (
        january_path
        / "despesas_salto_2026_01_20260917T100000Z.json"
    )
    january_latest = (
        january_path
        / "despesas_salto_2026_01_20260917T120000Z.json"
    )
    february_only = (
        february_path
        / "despesas_salto_2026_02_20260917T130000Z.json"
    )

    create_snapshot(january_old)
    create_snapshot(january_latest)
    create_snapshot(february_only)

    selected = select_latest_snapshots(
        bronze_path=bronze_path,
        dataset="despesas",
        municipality="salto",
    )

    assert selected == [january_latest, february_only]
    assert january_old not in selected


def test_rejects_invalid_dataset(tmp_path: Path) -> None:
    """Rejeita datasets que não pertencem ao contrato da ingestão."""
    with pytest.raises(ValueError, match="Dataset inválido"):
        select_latest_snapshots(
            bronze_path=tmp_path,
            dataset="fornecedores",
            municipality="salto",
        )


def test_rejects_missing_snapshots(tmp_path: Path) -> None:
    """Informa quando nenhum snapshot é encontrado."""
    with pytest.raises(
        FileNotFoundError,
        match="Nenhum snapshot encontrado",
    ):
        select_latest_snapshots(
            bronze_path=tmp_path,
            dataset="receitas",
            municipality="salto",
        )

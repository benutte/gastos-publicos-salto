"""Testes da leitura dos snapshots Bronze com DuckDB."""

import json
from pathlib import Path

import duckdb
import pytest

from src.lakehouse.bronze_reader import create_bronze_view


def write_json(path: Path, payload: object) -> None:
    """Grava um arquivo JSON utilizado pelo teste."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, ensure_ascii=False),
        encoding="utf-8",
    )


def test_creates_expenses_view_from_multiple_snapshots(
    tmp_path: Path,
) -> None:
    """Cria uma visão de despesas preservando valores como texto."""
    first_snapshot = tmp_path / "despesas_01.json"
    second_snapshot = tmp_path / "despesas_02.json"

    write_json(
        first_snapshot,
        [
            {
                "orgao": "PREFEITURA",
                "mes": "Janeiro",
                "evento": "Empenhado",
                "nr_empenho": "1-2020",
                "id_fornecedor": "CNPJ - 123",
                "nm_fornecedor": "FORNECEDOR A",
                "dt_emissao_despesa": "04/01/2020",
                "vl_despesa": "4.444,17",
            }
        ],
    )
    write_json(
        second_snapshot,
        [
            {
                "orgao": "PREFEITURA",
                "mes": "Fevereiro",
                "evento": "Valor Pago",
                "nr_empenho": "2-2020",
                "id_fornecedor": "CNPJ - 456",
                "nm_fornecedor": "FORNECEDOR B",
                "dt_emissao_despesa": "05/02/2020",
                "vl_despesa": "3399,90",
            }
        ],
    )

    connection = duckdb.connect()

    try:
        view_name = create_bronze_view(
            connection=connection,
            dataset="despesas",
            snapshots=[first_snapshot, second_snapshot],
        )

        result = connection.execute(
            f"""
            SELECT
                mes,
                dt_emissao_despesa,
                vl_despesa,
                filename
            FROM {view_name}
            ORDER BY mes
            """
        ).fetchall()

        assert len(result) == 2
        assert result[0][2] == "3399,90"
        assert result[1][2] == "4.444,17"
        assert result[0][3].endswith("despesas_02.json")
        assert result[1][3].endswith("despesas_01.json")
    finally:
        connection.close()


def test_rejects_dataset_without_schema(tmp_path: Path) -> None:
    """Rejeita datasets que não possuem contrato de leitura."""
    connection = duckdb.connect()

    try:
        with pytest.raises(
            ValueError,
            match="Dataset sem esquema Bronze definido",
        ):
            create_bronze_view(
                connection=connection,
                dataset="fornecedores",
                snapshots=[tmp_path / "example.json"],
            )
    finally:
        connection.close()


def test_rejects_empty_snapshot_list() -> None:
    """Rejeita a criação de uma visão sem arquivos de origem."""
    connection = duckdb.connect()

    try:
        with pytest.raises(
            ValueError,
            match="não pode estar vazia",
        ):
            create_bronze_view(
                connection=connection,
                dataset="receitas",
                snapshots=[],
            )
    finally:
        connection.close()

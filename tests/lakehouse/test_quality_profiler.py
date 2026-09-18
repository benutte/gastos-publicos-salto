"""Testes do perfil de qualidade dos dados da camada Bronze."""

import json
from pathlib import Path

import duckdb
import pytest

from src.lakehouse.bronze_reader import create_bronze_view
from src.lakehouse.quality_profiler import profile_bronze_view


def write_json(path: Path, payload: object) -> None:
    """Grava dados JSON utilizados pelos testes."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, ensure_ascii=False),
        encoding="utf-8",
    )


def test_profiles_expenses_quality_problems(
    tmp_path: Path,
) -> None:
    """Identifica problemas de qualidade em registros de despesas."""
    snapshot = (
        tmp_path
        / "despesas"
        / "municipio=salto"
        / "exercicio=2020"
        / "mes=01"
        / "despesas_salto_2020_01_20200101T120000Z.json"
    )

    valid_record = {
        "orgao": "PREFEITURA",
        "mes": "Janeiro",
        "evento": "Empenhado",
        "nr_empenho": "1-2020",
        "id_fornecedor": "CNPJ - 123",
        "nm_fornecedor": "FORNECEDOR A",
        "dt_emissao_despesa": "04/01/2020",
        "vl_despesa": "4.444,17",
    }

    invalid_record = {
        "orgao": "",
        "mes": "Fevereiro",
        "evento": "Evento desconhecido",
        "nr_empenho": "2-2020",
        "id_fornecedor": None,
        "nm_fornecedor": "FORNECEDOR B",
        "dt_emissao_despesa": "31/02/2020",
        "vl_despesa": "valor inválido",
    }

    write_json(
        snapshot,
        [
            valid_record,
            valid_record,
            invalid_record,
        ],
    )

    connection = duckdb.connect()

    try:
        view_name = create_bronze_view(
            connection=connection,
            dataset="despesas",
            snapshots=[snapshot],
        )

        profile = profile_bronze_view(
            connection=connection,
            dataset="despesas",
            view_name=view_name,
        )

        assert profile.total_records == 3
        assert profile.invalid_months == 0
        assert profile.partition_month_mismatches == 1
        assert profile.invalid_monetary_values == 1
        assert profile.invalid_dates == 1
        assert profile.exact_duplicate_groups == 1
        assert profile.null_or_empty_by_column["orgao"] == 1
        assert profile.null_or_empty_by_column["id_fornecedor"] == 1
        assert profile.distinct_months == ["Fevereiro", "Janeiro"]
        assert profile.distinct_events == [
            "Empenhado",
            "Evento desconhecido",
        ]
    finally:
        connection.close()


def test_profiles_revenue_quality_problems(
    tmp_path: Path,
) -> None:
    """Identifica problemas de qualidade em registros de receitas."""
    snapshot = (
        tmp_path
        / "receitas"
        / "municipio=salto"
        / "exercicio=2020"
        / "mes=02"
        / "receitas_salto_2020_02_20200201T120000Z.json"
    )

    write_json(
        snapshot,
        [
            {
                "orgao": "PREFEITURA",
                "mes": "Fevereiro",
                "ds_fonte_recurso": "01 - TESOURO",
                "ds_cd_aplicacao_fixo": "200 - EDUCAÇÃO",
                "ds_alinea": "1000 - RECEITA",
                "ds_subalinea": "1001 - RECEITA PRINCIPAL",
                "vl_arrecadacao": "1.234,56",
            },
            {
                "orgao": "PREFEITURA",
                "mes": "Mês inexistente",
                "ds_fonte_recurso": "",
                "ds_cd_aplicacao_fixo": "200 - EDUCAÇÃO",
                "ds_alinea": "1000 - RECEITA",
                "ds_subalinea": None,
                "vl_arrecadacao": "inválido",
            },
        ],
    )

    connection = duckdb.connect()

    try:
        view_name = create_bronze_view(
            connection=connection,
            dataset="receitas",
            snapshots=[snapshot],
        )

        profile = profile_bronze_view(
            connection=connection,
            dataset="receitas",
            view_name=view_name,
        )

        assert profile.total_records == 2
        assert profile.invalid_months == 1
        assert profile.partition_month_mismatches == 1
        assert profile.invalid_monetary_values == 1
        assert profile.invalid_dates is None
        assert profile.distinct_events is None
        assert profile.exact_duplicate_groups == 0
        assert (
            profile.null_or_empty_by_column["ds_fonte_recurso"]
            == 1
        )
        assert (
            profile.null_or_empty_by_column["ds_subalinea"]
            == 1
        )
    finally:
        connection.close()


def test_accepts_valid_brazilian_monetary_formats(
    tmp_path: Path,
) -> None:
    """Aceita valores monetários brasileiros com ou sem milhar."""
    snapshot = (
        tmp_path
        / "receitas"
        / "municipio=salto"
        / "exercicio=2020"
        / "mes=01"
        / "receitas_salto_2020_01_20200101T120000Z.json"
    )

    base_record = {
        "orgao": "PREFEITURA",
        "mes": "Janeiro",
        "ds_fonte_recurso": "01 - TESOURO",
        "ds_cd_aplicacao_fixo": "200 - EDUCAÇÃO",
        "ds_alinea": "1000 - RECEITA",
        "ds_subalinea": "1001 - RECEITA PRINCIPAL",
    }

    write_json(
        snapshot,
        [
            {
                **base_record,
                "vl_arrecadacao": "3399,90",
            },
            {
                **base_record,
                "vl_arrecadacao": "4.444,17",
            },
            {
                **base_record,
                "vl_arrecadacao": "0,00",
            },
        ],
    )

    connection = duckdb.connect()

    try:
        view_name = create_bronze_view(
            connection=connection,
            dataset="receitas",
            snapshots=[snapshot],
        )

        profile = profile_bronze_view(
            connection=connection,
            dataset="receitas",
            view_name=view_name,
        )

        assert profile.invalid_monetary_values == 0
        assert profile.partition_month_mismatches == 0
    finally:
        connection.close()


def test_rejects_unsupported_dataset() -> None:
    """Rejeita um dataset sem regras de qualidade definidas."""
    connection = duckdb.connect()

    try:
        with pytest.raises(
            ValueError,
            match="Dataset inválido para o perfil de qualidade",
        ):
            profile_bronze_view(
                connection=connection,
                dataset="fornecedores",
                view_name="bronze_fornecedores",
            )
    finally:
        connection.close()

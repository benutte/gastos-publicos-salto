
"""Leitura dos snapshots selecionados da camada Bronze com DuckDB."""

from collections.abc import Sequence
from pathlib import Path

import duckdb


BRONZE_SCHEMAS: dict[str, dict[str, str]] = {
    "despesas": {
        "orgao": "VARCHAR",
        "mes": "VARCHAR",
        "evento": "VARCHAR",
        "nr_empenho": "VARCHAR",
        "id_fornecedor": "VARCHAR",
        "nm_fornecedor": "VARCHAR",
        "dt_emissao_despesa": "VARCHAR",
        "vl_despesa": "VARCHAR",
    },
    "receitas": {
        "orgao": "VARCHAR",
        "mes": "VARCHAR",
        "ds_fonte_recurso": "VARCHAR",
        "ds_cd_aplicacao_fixo": "VARCHAR",
        "ds_alinea": "VARCHAR",
        "ds_subalinea": "VARCHAR",
        "vl_arrecadacao": "VARCHAR",
    },
}


def create_bronze_view(
    connection: duckdb.DuckDBPyConnection,
    dataset: str,
    snapshots: Sequence[Path],
) -> str:
    """Cria uma visão temporária sobre os snapshots Bronze selecionados.

    Todos os campos da API são lidos inicialmente como VARCHAR. Essa decisão
    preserva o conteúdo bruto e impede que a inferência automática converta
    datas ou valores monetários de forma incorreta.

    A coluna virtual filename é mantida para garantir rastreabilidade até o
    arquivo Bronze que originou cada registro.

    Args:
        connection: Conexão DuckDB aberta.
        dataset: Dataset que será lido, como despesas ou receitas.
        snapshots: Arquivos mais recentes selecionados por partição mensal.

    Returns:
        Nome da visão temporária criada.

    Raises:
        ValueError: Se o dataset não possuir um esquema definido ou se a lista
            de snapshots estiver vazia.
    """
    if dataset not in BRONZE_SCHEMAS:
        raise ValueError(
            f"Dataset sem esquema Bronze definido: {dataset}."
        )

    if not snapshots:
        raise ValueError(
            "A lista de snapshots não pode estar vazia."
        )

    view_name = f"bronze_{dataset}"

    # Caminhos absolutos evitam erros quando o processo é iniciado a partir
    # de diferentes diretórios de trabalho.
    snapshot_paths = [
        str(snapshot.resolve())
        for snapshot in snapshots
    ]

    columns = BRONZE_SCHEMAS[dataset]

    # Declara explicitamente todas as colunas como VARCHAR para preservar
    # os valores brutos recebidos da API.
    columns_sql = ", ".join(
        f"'{column}': '{column_type}'"
        for column, column_type in columns.items()
    )

    # Instruções CREATE VIEW não aceitam parâmetros preparados para a lista
    # de arquivos. Portanto, os caminhos são convertidos em literais SQL.
    # Aspas simples existentes nos caminhos são duplicadas para impedir que
    # elas interrompam a instrução SQL.
    snapshot_paths_sql = ", ".join(
        f"'{path.replace(chr(39), chr(39) * 2)}'"
        for path in snapshot_paths
    )

    connection.execute(
        f"""
        CREATE OR REPLACE TEMP VIEW {view_name} AS
        SELECT *
        FROM read_json(
            [{snapshot_paths_sql}],
            format = 'array',
            columns = {{{columns_sql}}},
            filename = true
        )
        """
    )

    return view_name

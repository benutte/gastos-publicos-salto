"""Perfil de qualidade dos dados selecionados da camada Bronze."""

from dataclasses import dataclass

import duckdb


MONTH_NUMBERS = {
    "Janeiro": 1,
    "Fevereiro": 2,
    "Março": 3,
    "Abril": 4,
    "Maio": 5,
    "Junho": 6,
    "Julho": 7,
    "Agosto": 8,
    "Setembro": 9,
    "Outubro": 10,
    "Novembro": 11,
    "Dezembro": 12,
}

DATASET_COLUMNS = {
    "despesas": [
        "orgao",
        "mes",
        "evento",
        "nr_empenho",
        "id_fornecedor",
        "nm_fornecedor",
        "dt_emissao_despesa",
        "vl_despesa",
    ],
    "receitas": [
        "orgao",
        "mes",
        "ds_fonte_recurso",
        "ds_cd_aplicacao_fixo",
        "ds_alinea",
        "ds_subalinea",
        "vl_arrecadacao",
    ],
}


@dataclass(frozen=True)
class QualityProfile:
    """Resumo das verificações de qualidade de um dataset Bronze."""

    dataset: str
    total_records: int
    null_or_empty_by_column: dict[str, int]
    distinct_months: list[str]
    invalid_months: int
    partition_month_mismatches: int
    invalid_monetary_values: int
    exact_duplicate_groups: int
    invalid_dates: int | None = None
    distinct_events: list[str] | None = None


def brazilian_decimal_expression(column: str) -> str:
    """Cria uma expressão SQL para converter moeda brasileira.

    Exemplos:

    - 3399,90 torna-se 3399.90;
    - 4.444,17 torna-se 4444.17.

    TRY_CAST retorna NULL quando a conversão não é possível. Isso permite
    identificar valores inválidos sem interromper todo o diagnóstico.

    Args:
        column: Nome da coluna que contém o valor monetário textual.

    Returns:
        Expressão SQL compatível com DuckDB.
    """
    return (
        "TRY_CAST("
        f"REPLACE(REPLACE(TRIM({column}), '.', ''), ',', '.') "
        "AS DECIMAL(18, 2))"
    )


def partition_month_expression() -> str:
    """Cria uma expressão SQL para extrair o mês da partição.

    O caminho do arquivo contém um trecho como mes=01. A expressão regular
    extrai os dois dígitos e os converte para INTEGER.

    Returns:
        Expressão SQL que representa o mês da partição.
    """
    return (
        "TRY_CAST("
        "regexp_extract(filename, 'mes=([0-9]{2})', 1) "
        "AS INTEGER)"
    )


def record_month_expression() -> str:
    """Cria uma expressão SQL para converter o nome do mês em número.

    Returns:
        Expressão CASE que converte meses em português para INTEGER.
    """
    cases = " ".join(
        f"WHEN mes = '{month_name}' THEN {month_number}"
        for month_name, month_number in MONTH_NUMBERS.items()
    )

    return f"CASE {cases} ELSE NULL END"


def count_null_or_empty(
    connection: duckdb.DuckDBPyConnection,
    view_name: str,
    columns: list[str],
) -> dict[str, int]:
    """Conta valores nulos ou vazios em cada coluna.

    Args:
        connection: Conexão DuckDB que contém a visão analisada.
        view_name: Nome da visão temporária.
        columns: Colunas que participarão da verificação.

    Returns:
        Dicionário com a quantidade de nulos ou vazios por coluna.
    """
    expressions = ", ".join(
        (
            f"COUNT(*) FILTER "
            f"(WHERE {column} IS NULL OR TRIM({column}) = '') "
            f"AS {column}"
        )
        for column in columns
    )

    result = connection.execute(
        f"""
        SELECT {expressions}
        FROM {view_name}
        """
    ).fetchone()

    if result is None:
        return {column: 0 for column in columns}

    return dict(zip(columns, result, strict=True))


def count_exact_duplicate_groups(
    connection: duckdb.DuckDBPyConnection,
    view_name: str,
    columns: list[str],
) -> int:
    """Conta grupos de registros exatamente iguais.

    As colunas do dataset e o exercício extraído de filename participam da
    comparação. Isso evita classificar como duplicados registros iguais que
    pertencem a exercícios diferentes.

    Um grupo com duas ou mais linhas idênticas conta como um grupo duplicado,
    independentemente da quantidade de repetições dentro dele.

    Args:
        connection: Conexão DuckDB que contém a visão analisada.
        view_name: Nome da visão temporária.
        columns: Colunas utilizadas para comparar os registros.

    Returns:
        Quantidade de grupos que possuem mais de uma ocorrência.
    """
    # O exercício não existe no conteúdo das receitas e precisa ser extraído
    # do caminho. Sem ele, registros iguais de anos diferentes seriam
    # classificados incorretamente como duplicados.
    comparison_columns = [
        *columns,
        (
            "regexp_extract("
            "filename, 'exercicio=([0-9]{4})', 1"
            ")"
        ),
    ]
    grouped_columns = ", ".join(comparison_columns)

    result = connection.execute(
        f"""
        SELECT COUNT(*)
        FROM (
            SELECT {grouped_columns}
            FROM {view_name}
            GROUP BY {grouped_columns}
            HAVING COUNT(*) > 1
        ) AS duplicate_groups
        """
    ).fetchone()

    return int(result[0]) if result else 0


def profile_bronze_view(
    connection: duckdb.DuckDBPyConnection,
    dataset: str,
    view_name: str,
) -> QualityProfile:
    """Executa verificações de qualidade sobre uma visão Bronze.

    Args:
        connection: Conexão DuckDB que contém a visão temporária.
        dataset: Dataset analisado, despesas ou receitas.
        view_name: Nome da visão Bronze criada no DuckDB.

    Returns:
        Perfil consolidado das verificações de qualidade.

    Raises:
        ValueError: Se o dataset informado não for suportado.
    """
    if dataset not in DATASET_COLUMNS:
        raise ValueError(
            f"Dataset inválido para o perfil de qualidade: {dataset}."
        )

    columns = DATASET_COLUMNS[dataset]

    monetary_column = (
        "vl_despesa"
        if dataset == "despesas"
        else "vl_arrecadacao"
    )

    total_result = connection.execute(
        f"""
        SELECT COUNT(*)
        FROM {view_name}
        """
    ).fetchone()

    total_records = int(total_result[0]) if total_result else 0

    distinct_months = [
        row[0]
        for row in connection.execute(
            f"""
            SELECT DISTINCT mes
            FROM {view_name}
            WHERE mes IS NOT NULL
            ORDER BY mes
            """
        ).fetchall()
    ]

    record_month_sql = record_month_expression()
    partition_month_sql = partition_month_expression()
    monetary_sql = brazilian_decimal_expression(monetary_column)

    invalid_months_result = connection.execute(
        f"""
        SELECT COUNT(*)
        FROM {view_name}
        WHERE {record_month_sql} IS NULL
        """
    ).fetchone()

    invalid_months = (
        int(invalid_months_result[0])
        if invalid_months_result
        else 0
    )

    mismatch_result = connection.execute(
        f"""
        SELECT COUNT(*)
        FROM {view_name}
        WHERE {record_month_sql}
              IS DISTINCT FROM {partition_month_sql}
        """
    ).fetchone()

    partition_month_mismatches = (
        int(mismatch_result[0])
        if mismatch_result
        else 0
    )

    invalid_monetary_result = connection.execute(
        f"""
        SELECT COUNT(*)
        FROM {view_name}
        WHERE {monetary_column} IS NOT NULL
          AND TRIM({monetary_column}) <> ''
          AND {monetary_sql} IS NULL
        """
    ).fetchone()

    invalid_monetary_values = (
        int(invalid_monetary_result[0])
        if invalid_monetary_result
        else 0
    )

    invalid_dates: int | None = None
    distinct_events: list[str] | None = None

    if dataset == "despesas":
        invalid_dates_result = connection.execute(
            f"""
            SELECT COUNT(*)
            FROM {view_name}
            WHERE dt_emissao_despesa IS NOT NULL
              AND TRIM(dt_emissao_despesa) <> ''
              AND TRY_STRPTIME(
                    dt_emissao_despesa,
                    '%d/%m/%Y'
                  ) IS NULL
            """
        ).fetchone()

        invalid_dates = (
            int(invalid_dates_result[0])
            if invalid_dates_result
            else 0
        )

        distinct_events = [
            row[0]
            for row in connection.execute(
                f"""
                SELECT DISTINCT evento
                FROM {view_name}
                WHERE evento IS NOT NULL
                ORDER BY evento
                """
            ).fetchall()
        ]

    return QualityProfile(
        dataset=dataset,
        total_records=total_records,
        null_or_empty_by_column=count_null_or_empty(
            connection=connection,
            view_name=view_name,
            columns=columns,
        ),
        distinct_months=distinct_months,
        invalid_months=invalid_months,
        partition_month_mismatches=partition_month_mismatches,
        invalid_monetary_values=invalid_monetary_values,
        exact_duplicate_groups=count_exact_duplicate_groups(
            connection=connection,
            view_name=view_name,
            columns=columns,
        ),
        invalid_dates=invalid_dates,
        distinct_events=distinct_events,
    )


def print_quality_profile(profile: QualityProfile) -> None:
    """Exibe o perfil de qualidade em formato legível.

    Args:
        profile: Resultado produzido pelo perfil de qualidade.
    """
    print(f"\nDataset: {profile.dataset}")
    print(f"Registros: {profile.total_records}")
    print(f"Meses distintos: {', '.join(profile.distinct_months)}")
    print(f"Meses inválidos: {profile.invalid_months}")

    print(
        "Divergências entre registro e partição: "
        f"{profile.partition_month_mismatches}"
    )

    print(
        "Valores monetários inválidos: "
        f"{profile.invalid_monetary_values}"
    )

    print(
        "Grupos de duplicidades exatas: "
        f"{profile.exact_duplicate_groups}"
    )

    if profile.invalid_dates is not None:
        print(f"Datas inválidas: {profile.invalid_dates}")

    if profile.distinct_events is not None:
        print(
            "Eventos distintos: "
            f"{', '.join(profile.distinct_events)}"
        )

    print("Nulos ou vazios por coluna:")

    for column, count in profile.null_or_empty_by_column.items():
        print(f"  - {column}: {count}")
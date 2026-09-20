"""Exportação das tabelas Gold para consumo no Power BI."""

import argparse
from pathlib import Path

import duckdb

from src.lakehouse.connection import create_lakehouse_connection


DEFAULT_OUTPUT_PATH = Path("data/bi/gastos_publicos.duckdb")
DEFAULT_SOURCE_CATALOG = "gastos_publicos"
DEFAULT_SOURCE_SCHEMA = "gold"

GOLD_TABLES = (
    "dim_municipio",
    "dim_orgao",
    "dim_tempo",
    "dim_fornecedor",
    "dim_fonte_recurso",
    "dim_aplicacao",
    "dim_alinea",
    "dim_subalinea",
    "fct_despesas",
    "fct_receitas",
)


def remove_temporary_files(temporary_path: Path) -> None:
    """Remove arquivos temporários deixados por uma execução incompleta.

    O DuckDB pode criar um arquivo principal e um arquivo auxiliar com
    extensão .wal durante a escrita.

    Args:
        temporary_path: Caminho do banco DuckDB temporário.
    """
    temporary_wal_path = Path(f"{temporary_path}.wal")

    temporary_path.unlink(missing_ok=True)
    temporary_wal_path.unlink(missing_ok=True)


def export_gold_to_duckdb(
    connection: duckdb.DuckDBPyConnection,
    output_path: Path = DEFAULT_OUTPUT_PATH,
    source_catalog: str = DEFAULT_SOURCE_CATALOG,
    source_schema: str = DEFAULT_SOURCE_SCHEMA,
) -> dict[str, int]:
    """Exporta as tabelas Gold para um arquivo DuckDB independente.

    O arquivo é criado primeiro em um caminho temporário. Depois da exportação,
    as contagens das tabelas de origem e destino são comparadas. O arquivo
    final é substituído somente quando todas as validações são aprovadas.

    Args:
        connection: Conexão DuckDB com o catálogo de origem disponível.
        output_path: Caminho do arquivo DuckDB destinado ao Power BI.
        source_catalog: Catálogo que contém as tabelas Gold.
        source_schema: Schema que contém as tabelas Gold.

    Returns:
        Dicionário com a quantidade de registros exportados por tabela.

    Raises:
        RuntimeError: Se alguma tabela apresentar divergência de registros.
    """
    output_path = output_path.resolve()
    temporary_path = output_path.with_suffix(".tmp.duckdb")

    output_path.parent.mkdir(parents=True, exist_ok=True)
    remove_temporary_files(temporary_path)

    # O caminho é gerado internamente pelo projeto, mas ainda escapamos aspas
    # simples para produzir um literal SQL válido.
    temporary_path_sql = str(temporary_path).replace("'", "''")

    exported_counts: dict[str, int] = {}
    destination_attached = False

    try:
        connection.execute(
            f"""
            ATTACH '{temporary_path_sql}'
            AS power_bi
            """
        )
        destination_attached = True

        connection.execute(
            """
            CREATE SCHEMA power_bi.gold
            """
        )

        for table_name in GOLD_TABLES:
            source_relation = (
                f"{source_catalog}.{source_schema}.{table_name}"
            )
            destination_relation = f"power_bi.gold.{table_name}"

            source_count = connection.execute(
                f"""
                SELECT COUNT(*)
                FROM {source_relation}
                """
            ).fetchone()[0]

            connection.execute(
                f"""
                CREATE TABLE {destination_relation} AS
                SELECT *
                FROM {source_relation}
                """
            )

            destination_count = connection.execute(
                f"""
                SELECT COUNT(*)
                FROM {destination_relation}
                """
            ).fetchone()[0]

            if source_count != destination_count:
                raise RuntimeError(
                    "Divergência na exportação da tabela "
                    f"{table_name}: origem={source_count}, "
                    f"destino={destination_count}."
                )

            exported_counts[table_name] = int(destination_count)

        connection.execute(
            """
            CHECKPOINT power_bi
            """
        )

        connection.execute(
            """
            DETACH power_bi
            """
        )
        destination_attached = False

        # os.replace() realiza a substituição atômica no mesmo sistema de
        # arquivos. Se houver uma versão anterior, ela só será substituída
        # depois que toda a nova exportação tiver sido validada.
        temporary_path.replace(output_path)

    except Exception:
        if destination_attached:
            try:
                connection.execute("DETACH power_bi")
            except duckdb.Error:
                pass

        remove_temporary_files(temporary_path)
        raise

    return exported_counts


def parse_arguments() -> argparse.Namespace:
    """Define e interpreta os argumentos da exportação."""
    parser = argparse.ArgumentParser(
        description=(
            "Exporta as tabelas Gold para um arquivo DuckDB "
            "destinado ao Power BI."
        )
    )

    parser.add_argument(
        "--output",
        type=Path,
        default=DEFAULT_OUTPUT_PATH,
        help="Caminho do arquivo DuckDB de saída.",
    )

    return parser.parse_args()


def main() -> None:
    """Executa a exportação das tabelas Gold."""
    args = parse_arguments()
    connection = create_lakehouse_connection()

    try:
        exported_counts = export_gold_to_duckdb(
            connection=connection,
            output_path=args.output,
        )
    finally:
        connection.close()

    print("Exportação para o Power BI concluída")
    print(f"Arquivo: {args.output.resolve()}")
    print(f"Tabelas exportadas: {len(exported_counts)}")

    for table_name, record_count in exported_counts.items():
        print(f"  - {table_name}: {record_count} registros")


if __name__ == "__main__":
    main()

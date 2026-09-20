"""Gerenciamento da conexão local com DuckDB e DuckLake."""

from pathlib import Path

import duckdb


DEFAULT_CATALOG_PATH = Path(
    "data/lakehouse/catalog/gastos_publicos.ducklake"
)
DEFAULT_DATA_PATH = Path("data/lakehouse/files")
DEFAULT_CATALOG_NAME = "gastos_publicos"


def create_lakehouse_connection(
    catalog_path: Path = DEFAULT_CATALOG_PATH,
    data_path: Path = DEFAULT_DATA_PATH,
) -> duckdb.DuckDBPyConnection:
    """Cria uma conexão DuckDB com o catálogo DuckLake anexado.

    O DuckLake utiliza dois componentes separados:

    - um catálogo, responsável por armazenar os metadados;
    - um diretório de dados, responsável por armazenar arquivos Parquet.

    Args:
        catalog_path: Caminho do arquivo utilizado como catálogo DuckLake.
        data_path: Diretório em que os arquivos de dados serão armazenados.

    Returns:
        Conexão DuckDB aberta e pronta para utilizar o catálogo DuckLake.
    """
    # Caminhos absolutos garantem que Python, dbt e DuckLake identifiquem
    # exatamente os mesmos locais, independentemente do diretório de execução.
    catalog_path = catalog_path.resolve()
    data_path = data_path.resolve()

    # Os diretórios são criados automaticamente para permitir que a primeira
    # execução ocorra em um ambiente recém-configurado.
    catalog_path.parent.mkdir(parents=True, exist_ok=True)
    data_path.mkdir(parents=True, exist_ok=True)

    connection = duckdb.connect()

    try:
        # A extensão já foi instalada no ambiente local. LOAD apenas a
        # disponibiliza para a conexão DuckDB atual.
        connection.execute("LOAD ducklake")

        connection.execute(
            f"""
            ATTACH 'ducklake:{catalog_path}'
            AS {DEFAULT_CATALOG_NAME}
            (
                DATA_PATH '{data_path}/',
                OVERRIDE_DATA_PATH true
            )
            """
        )
    except Exception:
        # Uma conexão parcialmente configurada não deve permanecer aberta
        # quando ocorrer uma falha durante a inicialização.
        connection.close()
        raise

    return connection

"""Testes da conexão local com DuckDB e DuckLake."""

from pathlib import Path

from src.lakehouse.connection import (
    DEFAULT_CATALOG_NAME,
    create_lakehouse_connection,
)


def test_creates_directories_and_attaches_catalog(tmp_path: Path) -> None:
    """Cria os diretórios e anexa o catálogo DuckLake corretamente."""
    catalog_path = tmp_path / "catalog" / "test.ducklake"
    data_path = tmp_path / "files"

    connection = create_lakehouse_connection(
        catalog_path=catalog_path,
        data_path=data_path,
    )

    try:
        databases = connection.execute(
            """
            SELECT database_name
            FROM duckdb_databases()
            WHERE database_name = ?
            """,
            [DEFAULT_CATALOG_NAME],
        ).fetchall()

        assert catalog_path.parent.exists()
        assert data_path.exists()
        assert databases == [(DEFAULT_CATALOG_NAME,)]
    finally:
        connection.close()


def test_catalog_accepts_table_creation(tmp_path: Path) -> None:
    """Valida que o catálogo anexado permite criar e consultar tabelas."""
    catalog_path = tmp_path / "catalog" / "test.ducklake"
    data_path = tmp_path / "files"

    connection = create_lakehouse_connection(
        catalog_path=catalog_path,
        data_path=data_path,
    )

    try:
        connection.execute(
            f"""
            CREATE TABLE {DEFAULT_CATALOG_NAME}.test_table (
                id INTEGER,
                description VARCHAR
            )
            """
        )

        connection.execute(
            f"""
            INSERT INTO {DEFAULT_CATALOG_NAME}.test_table
            VALUES (1, 'registro de teste')
            """
        )

        result = connection.execute(
            f"""
            SELECT id, description
            FROM {DEFAULT_CATALOG_NAME}.test_table
            """
        ).fetchall()

        assert result == [(1, "registro de teste")]
    finally:
        connection.close()

"""Testes da exportação das tabelas Gold para o Power BI."""

from pathlib import Path

import duckdb
import pytest

from src.serving.export_power_bi import (
    GOLD_TABLES,
    export_gold_to_duckdb,
)


def create_source_catalog(
    connection: duckdb.DuckDBPyConnection,
) -> None:
    """Cria um catálogo Gold mínimo utilizado pelos testes."""
    connection.execute("CREATE SCHEMA gold")

    for index, table_name in enumerate(GOLD_TABLES, start=1):
        connection.execute(
            f"""
            CREATE TABLE gold.{table_name} AS
            SELECT
                {index} AS id,
                '{table_name}' AS description
            """
        )


def test_exports_all_gold_tables(tmp_path: Path) -> None:
    """Exporta todas as tabelas e preserva as contagens."""
    output_path = tmp_path / "gastos_publicos.duckdb"
    connection = duckdb.connect()

    try:
        create_source_catalog(connection)

        counts = export_gold_to_duckdb(
            connection=connection,
            output_path=output_path,
            source_catalog="memory",
            source_schema="gold",
            manifest_path=None,
            pipeline_runs_path=None,
        )
    finally:
        connection.close()

    assert output_path.exists()
    assert set(counts) == set(GOLD_TABLES)
    assert all(count == 1 for count in counts.values())

    exported_connection = duckdb.connect(
        str(output_path),
        read_only=True,
    )

    try:
        tables = {
            row[0]
            for row in exported_connection.execute(
                """
                SELECT table_name
                FROM information_schema.tables
                WHERE table_schema = 'gold'
                """
            ).fetchall()
        }

        assert tables == set(GOLD_TABLES)

        result = exported_connection.execute(
            """
            SELECT id, description
            FROM gold.fct_despesas
            """
        ).fetchone()

        assert result == (
            GOLD_TABLES.index("fct_despesas") + 1,
            "fct_despesas",
        )
    finally:
        exported_connection.close()


def test_replaces_existing_file_only_after_success(
    tmp_path: Path,
) -> None:
    """Substitui uma exportação anterior depois da validação."""
    output_path = tmp_path / "gastos_publicos.duckdb"

    previous_connection = duckdb.connect(str(output_path))

    try:
        previous_connection.execute(
            """
            CREATE TABLE previous_data (
                id INTEGER
            )
            """
        )
    finally:
        previous_connection.close()

    source_connection = duckdb.connect()

    try:
        create_source_catalog(source_connection)

        export_gold_to_duckdb(
            connection=source_connection,
            output_path=output_path,
            source_catalog="memory",
            source_schema="gold",
            manifest_path=None,
            pipeline_runs_path=None,
        )
    finally:
        source_connection.close()

    exported_connection = duckdb.connect(
        str(output_path),
        read_only=True,
    )

    try:
        previous_table_count = exported_connection.execute(
            """
            SELECT COUNT(*)
            FROM information_schema.tables
            WHERE table_name = 'previous_data'
            """
        ).fetchone()[0]

        assert previous_table_count == 0
    finally:
        exported_connection.close()


def test_preserves_existing_file_when_export_fails(
    tmp_path: Path,
) -> None:
    """Mantém a versão anterior se a nova exportação falhar."""
    output_path = tmp_path / "gastos_publicos.duckdb"

    previous_connection = duckdb.connect(str(output_path))

    try:
        previous_connection.execute(
            """
            CREATE TABLE previous_data AS
            SELECT 123 AS id
            """
        )
    finally:
        previous_connection.close()

    source_connection = duckdb.connect()

    try:
        source_connection.execute("CREATE SCHEMA gold")

        with pytest.raises(duckdb.Error):
            export_gold_to_duckdb(
                connection=source_connection,
                output_path=output_path,
                source_catalog="memory",
                source_schema="gold",
                manifest_path=None,
                pipeline_runs_path=None,
            )
    finally:
        source_connection.close()

    preserved_connection = duckdb.connect(
        str(output_path),
        read_only=True,
    )

    try:
        preserved_value = preserved_connection.execute(
            """
            SELECT id
            FROM previous_data
            """
        ).fetchone()[0]

        assert preserved_value == 123
    finally:
        preserved_connection.close()
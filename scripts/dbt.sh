#!/usr/bin/env bash

# Executa o dbt sempre a partir da raiz do repositório.
#
# Isso garante que os caminhos configurados para Bronze, DuckDB e DuckLake
# sejam resolvidos de forma consistente, independentemente do diretório em
# que o usuário esteja ao chamar este script.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
DBT_DIR="${PROJECT_ROOT}/transform/dbt_gastos_publicos"

cd "${PROJECT_ROOT}"

export DBT_PROJECT_DIR="${DBT_DIR}"
export DBT_PROFILES_DIR="${DBT_DIR}"

exec dbt "$@"

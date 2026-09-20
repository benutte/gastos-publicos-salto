#!/usr/bin/env bash

# Executa o pipeline completo de atualização dos gastos públicos.
#
# Etapas:
# 1. atualiza os snapshots recorrentes da camada Bronze;
# 2. reconstrói as camadas Silver e Gold;
# 3. executa todos os testes de qualidade do dbt.
#
# O script pode ser chamado manualmente ou por um orquestrador, como o
# Apache Airflow. Qualquer falha encerra a execução com código diferente
# de zero, permitindo que o orquestrador identifique o erro.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
VENV_PYTHON="${PROJECT_ROOT}/.venv/bin/python"
DBT_WRAPPER="${SCRIPT_DIR}/dbt.sh"

cd "${PROJECT_ROOT}"

if [[ ! -x "${VENV_PYTHON}" ]]; then
    echo "Erro: Python do ambiente virtual não encontrado."
    echo "Caminho esperado: ${VENV_PYTHON}"
    exit 1
fi

if [[ ! -x "${DBT_WRAPPER}" ]]; then
    echo "Erro: wrapper do dbt não encontrado ou não executável."
    echo "Caminho esperado: ${DBT_WRAPPER}"
    exit 1
fi

echo "========================================"
echo "Início do pipeline de gastos públicos"
echo "========================================"

echo
echo "[1/3] Atualizando a camada Bronze..."

"${VENV_PYTHON}" -m src.ingestion.tce_sp.recurring "$@"

echo
echo "[2/3] Reconstruindo Silver e Gold..."

"${DBT_WRAPPER}" build

echo
echo "[3/3] Exportando a Gold para o Power BI..."

"${VENV_PYTHON}" -m src.serving.export_power_bi

echo
echo "========================================"
echo "Pipeline concluído com sucesso"
echo "========================================"

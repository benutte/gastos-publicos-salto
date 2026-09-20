#!/usr/bin/env bash

# Executa todas as validações automatizadas do projeto.
#
# Os testes gerais usam o ambiente virtual local. Os testes da DAG são
# executados dentro da imagem Docker porque o Apache Airflow não faz parte
# da .venv do projeto.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
VENV_PYTEST="${PROJECT_ROOT}/.venv/bin/pytest"
DBT_WRAPPER="${SCRIPT_DIR}/dbt.sh"
AIRFLOW_IMAGE="gastos-publicos-airflow:3.3.2"

cd "${PROJECT_ROOT}"

if [[ ! -x "${VENV_PYTEST}" ]]; then
    echo "Erro: pytest do ambiente virtual não encontrado."
    echo "Caminho esperado: ${VENV_PYTEST}"
    exit 1
fi

if [[ ! -x "${DBT_WRAPPER}" ]]; then
    echo "Erro: wrapper do dbt não encontrado ou não executável."
    echo "Caminho esperado: ${DBT_WRAPPER}"
    exit 1
fi

if ! docker image inspect "${AIRFLOW_IMAGE}" >/dev/null 2>&1; then
    echo "Erro: imagem Docker do Airflow não encontrada."
    echo "Imagem esperada: ${AIRFLOW_IMAGE}"
    echo
    echo "Crie a imagem com:"
    echo "docker build -f docker/airflow/Dockerfile \\"
    echo "  -t ${AIRFLOW_IMAGE} ."
    exit 1
fi

echo "========================================"
echo "Validação completa do projeto"
echo "========================================"

echo
echo "[1/4] Executando testes Python locais..."

"${VENV_PYTEST}" \
    -q \
    --ignore=tests/airflow

echo
echo "[2/4] Reconstruindo e testando modelos dbt..."

"${DBT_WRAPPER}" build

echo
echo "[3/4] Validando o Docker Compose..."

docker compose config --quiet

echo "Docker Compose validado com sucesso."

echo
echo "[4/4] Executando testes estruturais da DAG..."

docker run --rm \
    --entrypoint bash \
    -v "${PROJECT_ROOT}:/opt/airflow/project:ro" \
    -w /opt/airflow/project \
    -e PYTHONPATH=/opt/airflow/project \
    -e PYTHONDONTWRITEBYTECODE=1 \
    "${AIRFLOW_IMAGE}" \
    -c "pytest -q -p no:cacheprovider tests/airflow"

echo
echo "========================================"
echo "Todas as validações foram aprovadas"
echo "========================================"

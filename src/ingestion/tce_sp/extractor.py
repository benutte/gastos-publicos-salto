"""Orquestra a extração mensal e o armazenamento na camada Bronze."""

from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

from src.ingestion.tce_sp.api_client import TceApiClient
from src.ingestion.tce_sp.manifest import append_manifest
from src.ingestion.tce_sp.storage import save_json_atomic


# Datasets disponíveis nos endpoints mensais utilizados pelo projeto.
VALID_DATASETS = {"despesas", "receitas"}


def extract_month(
    client: TceApiClient,
    bronze_path: str,
    manifest_path: str,
    dataset: str,
    municipality: str,
    year: int,
    month: int,
) -> dict:
    """Extrai um mês da API, salva o JSON e registra a execução."""

    # Validamos os parâmetros antes de iniciar a requisição.
    # Falhas de entrada são erros de uso e não falhas de ingestão.
    if dataset not in VALID_DATASETS:
        raise ValueError(
            f"Dataset inválido: {dataset}. "
            f"Valores permitidos: {sorted(VALID_DATASETS)}"
        )

    if not 1 <= month <= 12:
        raise ValueError(
            f"Mês inválido: {month}. Use um valor entre 1 e 12."
        )

    # Cada extração recebe um identificador único para auditoria.
    run_id = str(uuid4())

    endpoint = f"{dataset}/{municipality}/{year}/{month}"
    source_url = f"{client.base_url}/{endpoint}"

    # Registramos separadamente início e término da execução.
    started_at = datetime.now(timezone.utc)

    try:
        # Consulta a API. O cliente HTTP é responsável por retry e timeout.
        records = client.get(endpoint)

        completed_at = datetime.now(timezone.utc)
        timestamp = completed_at.strftime("%Y%m%dT%H%M%SZ")

        # O caminho segue particionamento no estilo Hive:
        # municipio=salto/exercicio=2026/mes=03
        output_path = (
            Path(bronze_path)
            / "tce_sp"
            / dataset
            / f"municipio={municipality}"
            / f"exercicio={year}"
            / f"mes={month:02d}"
            / (
                f"{dataset}_{municipality}_{year}_"
                f"{month:02d}_{timestamp}.json"
            )
        )

        # Salva o JSON de forma atômica e retorna metadados do arquivo.
        file_metadata = save_json_atomic(records, output_path)

        # Uma lista vazia é uma execução válida, mas recebe status próprio.
        result = {
            "run_id": run_id,
            "status": "success" if records else "empty",
            "dataset": dataset,
            "municipality": municipality,
            "year": year,
            "month": month,
            "source_url": source_url,
            "record_count": len(records),
            "content_length_bytes": (
                file_metadata["content_length_bytes"]
            ),
            "sha256": file_metadata["sha256"],
            "started_at_utc": started_at.isoformat(),
            "completed_at_utc": completed_at.isoformat(),
            "output_path": str(output_path),
            "error_type": None,
            "error_message": None,
        }

        append_manifest(result, manifest_path)

        return result

    except Exception as error:
        # Uma falha também precisa ser registrada no manifesto.
        # Isso permite identificar o período afetado e reprocessá-lo depois.
        completed_at = datetime.now(timezone.utc)

        failure = {
            "run_id": run_id,
            "status": "failed",
            "dataset": dataset,
            "municipality": municipality,
            "year": year,
            "month": month,
            "source_url": source_url,
            "record_count": None,
            "content_length_bytes": None,
            "sha256": None,
            "started_at_utc": started_at.isoformat(),
            "completed_at_utc": completed_at.isoformat(),
            "output_path": None,
            "error_type": type(error).__name__,
            "error_message": str(error),
        }

        append_manifest(failure, manifest_path)

        # Registramos a falha, mas não a escondemos.
        # A exceção continua para que CLI, Airflow ou outro orquestrador
        # reconheça que a execução terminou com erro.
        raise

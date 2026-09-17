"""Execução em lote de múltiplos períodos da ingestão."""

from collections.abc import Iterable

from src.ingestion.tce_sp.api_client import TceApiClient
from src.ingestion.tce_sp.extractor import extract_month


def extract_periods(
    client: TceApiClient,
    bronze_path: str,
    manifest_path: str,
    datasets: list[str],
    municipality: str,
    periods: Iterable[tuple[int, int]],
    continue_on_error: bool = True,
) -> dict:
    """Executa a ingestão para vários datasets e períodos.

    O processamento ocorre sequencialmente para evitar sobrecarregar
    a API pública do TCE-SP.

    Quando ``continue_on_error`` for verdadeiro, uma falha não interrompe
    os períodos seguintes. Ao final, o resumo indica quantas extrações
    tiveram sucesso, retornaram vazias ou falharam.
    """

    # Convertemos para lista porque o plano pode ser um gerador.
    # Isso também permite calcular antecipadamente o total de tarefas.
    period_list = list(periods)

    total_tasks = len(datasets) * len(period_list)

    summary = {
        "total": total_tasks,
        "success": 0,
        "empty": 0,
        "failed": 0,
        "results": [],
    }

    current_task = 0

    # Cada dataset percorre todos os períodos planejados.
    # Nesta fase usamos processamento sequencial, mais simples e seguro.
    for dataset in datasets:
        for year, month in period_list:
            current_task += 1

            print(
                f"[{current_task}/{total_tasks}] "
                f"Extraindo {dataset} de {municipality}, "
                f"período {year}-{month:02d}..."
            )

            try:
                result = extract_month(
                    client=client,
                    bronze_path=bronze_path,
                    manifest_path=manifest_path,
                    dataset=dataset,
                    municipality=municipality,
                    year=year,
                    month=month,
                )

                summary[result["status"]] += 1
                summary["results"].append(result)

                print(
                    f"Concluído: {result['status']} "
                    f"com {result['record_count']} registros."
                )

            except Exception as error:
                # A falha detalhada já foi registrada no manifesto
                # pela função extract_month(). Aqui mantemos apenas
                # um resumo para a execução completa do lote.
                summary["failed"] += 1

                summary["results"].append(
                    {
                        "status": "failed",
                        "dataset": dataset,
                        "municipality": municipality,
                        "year": year,
                        "month": month,
                        "error_type": type(error).__name__,
                        "error_message": str(error),
                    }
                )

                print(
                    f"Falha: {type(error).__name__}: {error}"
                )

                # Em uma execução histórica, geralmente queremos continuar
                # e identificar todas as lacunas no resumo final.
                if not continue_on_error:
                    raise

    return summary

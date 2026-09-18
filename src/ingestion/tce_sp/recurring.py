"""Interface de linha de comando para atualizações recorrentes da Bronze."""

import argparse
from datetime import datetime

from src.ingestion.tce_sp.api_client import TceApiClient
from src.ingestion.tce_sp.batch import extract_periods
from src.ingestion.tce_sp.config import load_config
from src.ingestion.tce_sp.planner import build_period_plan


def build_recurring_periods(
    current_date: datetime,
    refresh_previous_year: bool,
) -> list[tuple[int, int]]:
    """Cria o plano de períodos de uma atualização recorrente.

    Quando a atualização do exercício anterior está habilitada, o plano
    começa em janeiro do ano anterior. Caso contrário, começa em janeiro do
    exercício corrente. O plano sempre termina no mês corrente.

    Args:
        current_date: Data utilizada como referência para o planejamento.
        refresh_previous_year: Indica se o exercício anterior será atualizado.

    Returns:
        Lista ordenada de pares contendo exercício e mês.
    """
    start_year = (
        current_date.year - 1
        if refresh_previous_year
        else current_date.year
    )

    return build_period_plan(
        start_year=start_year,
        end_year=current_date.year,
        end_month=current_date.month,
    )


def parse_arguments() -> argparse.Namespace:
    """Define e interpreta os argumentos da atualização recorrente."""
    parser = argparse.ArgumentParser(
        description=(
            "Atualização recorrente da camada Bronze da API do TCE-SP."
        )
    )

    parser.add_argument(
        "--datasets",
        nargs="+",
        choices=["despesas", "receitas"],
        default=["despesas", "receitas"],
        help="Datasets que serão processados.",
    )

    parser.add_argument(
        "--municipality",
        help="Slug do município.",
    )

    parser.add_argument(
        "--config",
        default="config/ingestion.yml",
        help="Caminho do arquivo de configuração.",
    )

    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Mostra o plano de execução sem acessar a API.",
    )

    return parser.parse_args()


def main() -> None:
    """Planeja e executa uma atualização recorrente da Bronze."""
    args = parse_arguments()
    config = load_config(args.config)

    municipality = (
        args.municipality
        or config["ingestion"]["municipality"]
    )

    current_date = datetime.now()

    periods = build_recurring_periods(
        current_date=current_date,
        refresh_previous_year=config["ingestion"][
            "refresh_previous_year"
        ],
    )

    first_year, first_month = periods[0]
    last_year, last_month = periods[-1]
    total_tasks = len(periods) * len(args.datasets)

    print("Plano de atualização recorrente")
    print(f"Município: {municipality}")
    print(f"Datasets: {', '.join(args.datasets)}")
    print(
        f"Período: {first_year}-{first_month:02d} "
        f"até {last_year}-{last_month:02d}"
    )
    print(f"Meses planejados: {len(periods)}")
    print(f"Extrações planejadas: {total_tasks}")

    if args.dry_run:
        print("Modo dry-run: nenhuma requisição foi realizada.")
        return

    client = TceApiClient(
        base_url=config["api"]["base_url"],
        connect_timeout=config["api"]["connect_timeout_seconds"],
        read_timeout=config["api"]["read_timeout_seconds"],
        max_retries=config["api"]["max_retries"],
        backoff_factor=config["api"]["backoff_factor"],
    )

    summary = extract_periods(
        client=client,
        bronze_path=config["storage"]["bronze_path"],
        manifest_path=config["storage"]["manifest_path"],
        datasets=args.datasets,
        municipality=municipality,
        periods=periods,
        continue_on_error=True,
    )

    print("\nResumo da atualização recorrente")
    print(f"Total: {summary['total']}")
    print(f"Sucesso: {summary['success']}")
    print(f"Vazios: {summary['empty']}")
    print(f"Falhas: {summary['failed']}")

    # O código diferente de zero permite que scripts e orquestradores
    # reconheçam a execução como falha.
    if summary["failed"] > 0:
        raise SystemExit(1)


if __name__ == "__main__":
    main()

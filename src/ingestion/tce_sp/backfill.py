"""Interface de linha de comando para cargas históricas em lote."""

import argparse
from datetime import datetime

from src.ingestion.tce_sp.api_client import TceApiClient
from src.ingestion.tce_sp.batch import extract_periods
from src.ingestion.tce_sp.config import load_config
from src.ingestion.tce_sp.planner import build_period_plan


def parse_arguments() -> argparse.Namespace:
    """Define e interpreta os argumentos do backfill."""

    parser = argparse.ArgumentParser(
        description="Backfill histórico da API do TCE-SP."
    )

    # Exercício inicial da carga histórica.
    parser.add_argument(
        "--start-year",
        required=True,
        type=int,
        help="Primeiro exercício que será processado.",
    )

    # Por padrão, o exercício final será o ano corrente.
    parser.add_argument(
        "--end-year",
        type=int,
        default=datetime.now().year,
        help="Último exercício que será processado.",
    )

    # Limita os meses do último exercício.
    # Anos anteriores continuam sendo processados de janeiro a dezembro.
    parser.add_argument(
        "--end-month",
        type=int,
        choices=range(1, 13),
        metavar="1-12",
        default=None,
        help="Último mês do exercício final.",
    )

    # Permite processar um ou os dois datasets na mesma execução.
    parser.add_argument(
        "--datasets",
        nargs="+",
        choices=["despesas", "receitas"],
        default=["despesas", "receitas"],
        help="Datasets que serão processados.",
    )

    # Quando omitido, será usado o município definido no YAML.
    parser.add_argument(
        "--municipality",
        help="Slug do município.",
    )

    parser.add_argument(
        "--config",
        default="config/ingestion.yml",
        help="Caminho do arquivo de configuração.",
    )

    # O dry-run mostra o plano sem consultar a API ou criar arquivos.
    # É uma proteção importante antes de cargas históricas extensas.
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Mostra o plano de execução sem baixar dados.",
    )

    return parser.parse_args()


def main() -> None:
    """Planeja e executa uma carga histórica."""

    # Lê os argumentos informados no terminal.
    args = parse_arguments()

    # Carrega as configurações gerais do projeto.
    config = load_config(args.config)

    # O município informado pela CLI tem prioridade.
    # Se não for informado, usamos o município definido no YAML.
    municipality = (
        args.municipality
        or config["ingestion"]["municipality"]
    )

    # Quando o mês final não é informado:
    # - para o exercício corrente, usamos o mês atual;
    # - para exercícios anteriores, usamos dezembro.
    current_date = datetime.now()

    if args.end_month is not None:
        end_month = args.end_month
    elif args.end_year == current_date.year:
        end_month = current_date.month
    else:
        end_month = 12

    # Gera todas as combinações de exercício e mês.
    periods = build_period_plan(
        start_year=args.start_year,
        end_year=args.end_year,
        end_month=end_month,
    )

    # Separa o primeiro e o último período para facilitar
    # a exibição e evitar expressões complexas nas f-strings.
    first_year, first_month = periods[0]
    last_year, last_month = periods[-1]

    # Cada dataset será processado para cada período planejado.
    total_tasks = len(periods) * len(args.datasets)

    print("Plano de backfill")
    print(f"Município: {municipality}")
    print(f"Datasets: {', '.join(args.datasets)}")
    print(
        f"Período: {first_year}-{first_month:02d} "
        f"até {last_year}-{last_month:02d}"
    )
    print(f"Meses planejados: {len(periods)}")
    print(f"Extrações planejadas: {total_tasks}")

    # No modo dry-run, mostramos somente o plano.
    # Nenhuma chamada à API ou gravação de arquivo é realizada.
    if args.dry_run:
        print("Modo dry-run: nenhuma requisição foi realizada.")
        return

    # Cria o cliente HTTP usando timeout, retry e backoff
    # definidos no arquivo de configuração.
    client = TceApiClient(
        base_url=config["api"]["base_url"],
        connect_timeout=config["api"]["connect_timeout_seconds"],
        read_timeout=config["api"]["read_timeout_seconds"],
        max_retries=config["api"]["max_retries"],
        backoff_factor=config["api"]["backoff_factor"],
    )

    # Executa todas as combinações de dataset e período.
    # Uma falha individual é registrada, mas não interrompe o lote.
    summary = extract_periods(
        client=client,
        bronze_path=config["storage"]["bronze_path"],
        manifest_path=config["storage"]["manifest_path"],
        datasets=args.datasets,
        municipality=municipality,
        periods=periods,
        continue_on_error=True,
    )

    print("\nResumo do backfill")
    print(f"Total: {summary['total']}")
    print(f"Sucesso: {summary['success']}")
    print(f"Vazios: {summary['empty']}")
    print(f"Falhas: {summary['failed']}")

    # Mesmo continuando após falhas individuais, o processo termina
    # com código diferente de zero se alguma extração falhar.
    # Isso permitirá que o Airflow reconheça a execução como falha.
    if summary["failed"] > 0:
        raise SystemExit(1)


if __name__ == "__main__":
    main()

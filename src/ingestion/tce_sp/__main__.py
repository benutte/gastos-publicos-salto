"""Interface de linha de comando para a ingestão mensal do TCE-SP."""

import argparse

from src.ingestion.tce_sp.api_client import TceApiClient
from src.ingestion.tce_sp.config import load_config
from src.ingestion.tce_sp.extractor import extract_month


def parse_arguments() -> argparse.Namespace:
    """Define e interpreta os argumentos recebidos pelo terminal."""

    parser = argparse.ArgumentParser(
        description="Ingestão mensal da API do TCE-SP para a camada Bronze."
    )

    # Dataset que será consultado na API.
    # O parâmetro choices impede valores diferentes dos suportados.
    parser.add_argument(
        "--dataset",
        required=True,
        choices=["despesas", "receitas"],
        help="Dataset que será extraído.",
    )

    # Exercício financeiro referente aos dados.
    parser.add_argument(
        "--year",
        required=True,
        type=int,
        help="Exercício da extração.",
    )

    # O mês é convertido para inteiro e validado entre 1 e 12.
    parser.add_argument(
        "--month",
        required=True,
        type=int,
        choices=range(1, 13),
        metavar="1-12",
        help="Mês da extração.",
    )

    # Município opcional.
    # Quando omitido, será utilizado o valor definido no arquivo YAML.
    parser.add_argument(
        "--municipality",
        help="Slug do município. Se omitido, usa o valor da configuração.",
    )

    # Permite utilizar outro arquivo de configuração quando necessário.
    parser.add_argument(
        "--config",
        default="config/ingestion.yml",
        help="Caminho do arquivo de configuração.",
    )

    return parser.parse_args()


def main() -> None:
    """Coordena a configuração, o cliente HTTP e a extração."""

    # Lê os parâmetros fornecidos pelo usuário no terminal.
    args = parse_arguments()

    # Carrega configurações como URL, timeouts, retries e caminhos.
    config = load_config(args.config)

    # O município informado pela CLI tem prioridade.
    # Se ele não for informado, usamos o município definido no YAML.
    municipality = (
        args.municipality
        or config["ingestion"]["municipality"]
    )

    # Cria o cliente HTTP usando todas as configurações da API.
    # Dessa forma, mudanças no YAML não exigem alterações neste código.
    client = TceApiClient(
        base_url=config["api"]["base_url"],
        connect_timeout=config["api"]["connect_timeout_seconds"],
        read_timeout=config["api"]["read_timeout_seconds"],
        max_retries=config["api"]["max_retries"],
        backoff_factor=config["api"]["backoff_factor"],
    )

    # Executa a extração mensal, salva o JSON na Bronze
    # e registra o resultado no manifesto de ingestão.
    result = extract_month(
        client=client,
        bronze_path=config["storage"]["bronze_path"],
        manifest_path=config["storage"]["manifest_path"],
        dataset=args.dataset,
        municipality=municipality,
        year=args.year,
        month=args.month,
    )

    # Exibe um resumo legível ao final da execução.
    print(f"Status: {result['status']}")
    print(f"Dataset: {result['dataset']}")
    print(f"Município: {result['municipality']}")
    print(f"Período: {result['year']}-{result['month']:02d}")
    print(f"Registros: {result['record_count']}")
    print(f"Arquivo: {result['output_path']}")


# Este bloco é executado quando chamamos:
# python -m src.ingestion.tce_sp
#
# Ele não é executado quando este módulo é apenas importado por outro arquivo.
if __name__ == "__main__":
    main()

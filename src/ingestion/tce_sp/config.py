from pathlib import Path

import yaml


def load_config(config_path: str = "config/ingestion.yml") -> dict:
    path = Path(config_path)

    if not path.exists():
        raise FileNotFoundError(
            f"Arquivo de configuração não encontrado: {path}"
        )

    with path.open("r", encoding="utf-8") as file:
        config = yaml.safe_load(file)

    if not config:
        raise ValueError("O arquivo de configuração está vazio.")

    return config


if __name__ == "__main__":
    config = load_config()

    print("Configuração carregada com sucesso.")
    print(f"API: {config['api']['base_url']}")
    print(f"Município: {config['ingestion']['municipality']}")
    print(f"Bronze: {config['storage']['bronze_path']}")

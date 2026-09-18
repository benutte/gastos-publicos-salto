"""Inspeção dos esquemas encontrados nos arquivos da camada Bronze."""

import argparse
import json
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path


SUPPORTED_DATASETS = ("despesas", "receitas")


@dataclass
class SchemaProfile:
    """Resultado da inspeção de esquema de um dataset Bronze."""

    dataset: str
    total_files: int
    total_records: int
    empty_files: list[Path]
    schema_files: dict[tuple[str, ...], set[Path]]


def profile_dataset(
    bronze_path: Path,
    dataset: str,
) -> SchemaProfile:
    """Inspeciona os esquemas presentes nos arquivos de um dataset.

    Cada esquema é representado por uma tupla ordenada com os nomes das
    colunas encontradas. A inspeção ocorre em todos os registros, e não
    somente no primeiro registro de cada arquivo.

    Args:
        bronze_path: Diretório raiz da camada Bronze do TCE-SP.
        dataset: Nome do dataset que será inspecionado.

    Returns:
        Perfil contendo arquivos, registros, vazios e esquemas encontrados.

    Raises:
        ValueError: Se o dataset não for suportado ou se algum arquivo não
            contiver uma lista JSON com objetos.
    """
    if dataset not in SUPPORTED_DATASETS:
        raise ValueError(
            f"Dataset inválido: {dataset}. "
            f"Valores aceitos: {', '.join(SUPPORTED_DATASETS)}."
        )

    dataset_path = bronze_path / dataset
    files = sorted(dataset_path.glob(
        "municipio=*/exercicio=*/mes=*/*.json"
    ))

    empty_files: list[Path] = []
    schema_files: dict[tuple[str, ...], set[Path]] = defaultdict(set)
    total_records = 0

    for file_path in files:
        with file_path.open(encoding="utf-8") as file:
            payload = json.load(file)

        if not isinstance(payload, list):
            raise ValueError(
                f"O arquivo {file_path} não contém uma lista JSON."
            )

        if not payload:
            empty_files.append(file_path)
            continue

        for record_index, record in enumerate(payload):
            if not isinstance(record, dict):
                raise ValueError(
                    f"O registro {record_index} do arquivo {file_path} "
                    "não contém um objeto JSON."
                )

            schema = tuple(sorted(record.keys()))
            schema_files[schema].add(file_path)
            total_records += 1

    return SchemaProfile(
        dataset=dataset,
        total_files=len(files),
        total_records=total_records,
        empty_files=empty_files,
        schema_files=dict(schema_files),
    )


def print_profile(profile: SchemaProfile) -> None:
    """Exibe um resumo legível do perfil de esquema encontrado."""
    print(f"\nDataset: {profile.dataset}")
    print(f"Arquivos analisados: {profile.total_files}")
    print(f"Registros analisados: {profile.total_records}")
    print(f"Arquivos vazios: {len(profile.empty_files)}")
    print(f"Esquemas distintos: {len(profile.schema_files)}")

    for index, (schema, files) in enumerate(
        sorted(profile.schema_files.items()),
        start=1,
    ):
        print(f"\nEsquema {index}")
        print(f"Arquivos que contêm o esquema: {len(files)}")
        print("Colunas:")

        for column in schema:
            print(f"  - {column}")

        if len(profile.schema_files) > 1:
            print("Arquivos:")

            for file_path in sorted(files):
                print(f"  - {file_path}")

    if profile.empty_files:
        print("\nArquivos vazios:")

        for file_path in profile.empty_files:
            print(f"  - {file_path}")


def parse_args() -> argparse.Namespace:
    """Lê os argumentos informados pela linha de comando."""
    parser = argparse.ArgumentParser(
        description=(
            "Inspeciona os esquemas dos arquivos JSON da camada Bronze."
        )
    )
    parser.add_argument(
        "--bronze-path",
        type=Path,
        default=Path("data/bronze/tce_sp"),
        help="Diretório raiz da camada Bronze do TCE-SP.",
    )

    return parser.parse_args()


def main() -> None:
    """Executa o perfil de esquema para todos os datasets suportados."""
    args = parse_args()

    for dataset in SUPPORTED_DATASETS:
        profile = profile_dataset(args.bronze_path, dataset)
        print_profile(profile)


if __name__ == "__main__":
    main()

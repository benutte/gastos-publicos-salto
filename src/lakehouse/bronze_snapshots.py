"""Seleção dos snapshots mais recentes da camada Bronze."""

from collections import defaultdict
from pathlib import Path


SUPPORTED_DATASETS = ("despesas", "receitas")


def select_latest_snapshots(
    bronze_path: Path,
    dataset: str,
    municipality: str,
) -> list[Path]:
    """Seleciona o snapshot mais recente de cada partição mensal.

    A camada Bronze é imutável e pode conter vários snapshots para a mesma
    combinação de dataset, município, exercício e mês. A camada Silver deve
    receber somente o snapshot mais recente de cada partição para evitar
    duplicidade de registros.

    A seleção utiliza o timestamp UTC presente no nome do arquivo. Como o
    timestamp segue o formato YYYYMMDDTHHMMSSZ, a ordenação alfabética dos
    nomes também corresponde à ordem cronológica.

    Args:
        bronze_path: Diretório raiz da camada Bronze do TCE-SP.
        dataset: Dataset que será selecionado, como despesas ou receitas.
        municipality: Identificador do município utilizado no particionamento.

    Returns:
        Lista ordenada com o snapshot mais recente de cadansal.

    Raises:
        ValueError: Se o dataset informado não for suportado.
        FileNotFoundError: Se nenhum snapshot for encontrado.
    """
    if dataset not in SUPPORTED_DATASETS:
        raise ValueError(
            f"Dataset inválido: {dataset}. "
            f"Valores aceitos: {', '.join(SUPPORTED_DATASETS)}."
        )

    dataset_path = (
        bronze_path
        / dataset
        / f"municipio={municipality}"
    )

    files = sorted(
        dataset_path.glob("exercicio=*/mes=*/*.json")
    )

    if not files:
        raise FileNotFoundError(
            f"Nenhum snapshot encontrado em {dataset_path}."
        )

    snapshots_by_partition: dict[Path, list[Path]] = defaultdict(list)

    for file_path in files:
        # O diretório pai representa uma partição mensal completa:
        # dataset, município, exercício e mês.
        snapshots_by_partition[file_path.parent].append(file_path)

    latest_snapshots = [
        max(partition_files, key=lambda path: path.name)
        for partition_files in snapshots_by_partition.values()
    ]

    return sorted(latest_snapshots)

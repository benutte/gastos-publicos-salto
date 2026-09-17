"""Planejamento dos períodos que serão processados pela ingestão."""


def build_period_plan(
    start_year: int,
    end_year: int,
    end_month: int = 12,
) -> list[tuple[int, int]]:
    """Cria uma lista ordenada de exercícios e meses para processamento.

    Anos anteriores ao último exercício recebem os doze meses.
    O último exercício termina no mês informado em ``end_month``.

    Exemplo:
        start_year=2025, end_year=2026, end_month=3

        Resultado:
        2025-01 até 2025-12
        2026-01 até 2026-03
    """

    # Evita intervalos invertidos, como início em 2026 e fim em 2025.
    if start_year > end_year:
        raise ValueError(
            "O exercício inicial não pode ser maior que o exercício final."
        )

    # O último mês precisa representar um mês válido do calendário.
    if not 1 <= end_month <= 12:
        raise ValueError(
            f"Mês final inválido: {end_month}. Use um valor entre 1 e 12."
        )

    periods = []

    # Percorre todos os exercícios do intervalo, incluindo os extremos.
    for year in range(start_year, end_year + 1):
        # Exercícios anteriores ao último são carregados integralmente.
        # Apenas o último exercício respeita o limite de end_month.
        last_month = end_month if year == end_year else 12

        for month in range(1, last_month + 1):
            periods.append((year, month))

    return periods

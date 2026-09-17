"""Testes unitários do planejamento de períodos da ingestão."""

import pytest

from src.ingestion.tce_sp.planner import build_period_plan


def test_builds_complete_year():
    """Deve gerar os doze meses para um exercício completo."""

    periods = build_period_plan(
        start_year=2025,
        end_year=2025,
        end_month=12,
    )

    assert len(periods) == 12
    assert periods[0] == (2025, 1)
    assert periods[-1] == (2025, 12)


def test_limits_last_year_to_informed_month():
    """Deve limitar somente o último exercício ao mês informado."""

    periods = build_period_plan(
        start_year=2025,
        end_year=2026,
        end_month=3,
    )

    # Doze meses de 2025 mais três meses de 2026.
    assert len(periods) == 15

    assert periods[0] == (2025, 1)
    assert periods[11] == (2025, 12)
    assert periods[12] == (2026, 1)
    assert periods[-1] == (2026, 3)


def test_rejects_inverted_year_range():
    """Deve rejeitar um intervalo em que o início supera o fim."""

    with pytest.raises(
        ValueError,
        match="exercício inicial",
    ):
        build_period_plan(
            start_year=2026,
            end_year=2025,
        )


@pytest.mark.parametrize("end_month", [0, 13])
def test_rejects_invalid_end_month(end_month):
    """Deve rejeitar um mês final fora do intervalo de 1 a 12."""

    with pytest.raises(
        ValueError,
        match="Mês final inválido",
    ):
        build_period_plan(
            start_year=2025,
            end_year=2026,
            end_month=end_month,
        )

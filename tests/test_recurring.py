"""Testes do planejamento da atualização recorrente da Bronze."""

from datetime import datetime

from src.ingestion.tce_sp.recurring import build_recurring_periods


def test_includes_previous_year_when_enabled() -> None:
    """Inclui o exercício anterior completo quando configurado."""
    current_date = datetime(2026, 9, 18, 12, 0, 0)

    periods = build_recurring_periods(
        current_date=current_date,
        refresh_previous_year=True,
    )

    assert periods[0] == (2025, 1)
    assert periods[-1] == (2026, 9)
    assert len(periods) == 21


def test_includes_only_current_year_when_disabled() -> None:
    """Processa somente o exercício corrente quando configurado."""
    current_date = datetime(2026, 9, 18, 12, 0, 0)

    periods = build_recurring_periods(
        current_date=current_date,
        refresh_previous_year=False,
    )

    assert periods[0] == (2026, 1)
    assert periods[-1] == (2026, 9)
    assert len(periods) == 9


def test_limits_current_year_to_current_month() -> None:
    """Não planeja meses posteriores ao mês de referência."""
    current_date = datetime(2026, 3, 10, 12, 0, 0)

    periods = build_recurring_periods(
        current_date=current_date,
        refresh_previous_year=False,
    )

    assert periods == [
        (2026, 1),
        (2026, 2),
        (2026, 3),
    ]

"""Testes unitários da execução em lote."""

from src.ingestion.tce_sp.batch import extract_periods


def test_extracts_all_datasets_and_periods(monkeypatch):
    """Deve executar todas as combinações de dataset e período."""

    # Armazena as chamadas feitas pelo executor para verificarmos
    # posteriormente a ordem e os parâmetros utilizados.
    calls = []

    def fake_extract_month(**kwargs):
        """Simula uma extração bem-sucedida sem acessar a API."""

        calls.append(
            (
                kwargs["dataset"],
                kwargs["year"],
                kwargs["month"],
            )
        )

        return {
            "status": "success",
            "dataset": kwargs["dataset"],
            "municipality": kwargs["municipality"],
            "year": kwargs["year"],
            "month": kwargs["month"],
            "record_count": 10,
        }

    # Substitui a extração real pela função simulada.
    # Assim, o teste não acessa a internet nem cria arquivos na Bronze.
    monkeypatch.setattr(
        "src.ingestion.tce_sp.batch.extract_month",
        fake_extract_month,
    )

    summary = extract_periods(
        client=None,
        bronze_path="data/bronze",
        manifest_path="data/metadata/manifest.jsonl",
        datasets=["despesas", "receitas"],
        municipality="salto",
        periods=[(2026, 1), (2026, 2)],
    )

    # Dois datasets multiplicados por dois períodos resultam
    # em quatro tarefas de ingestão.
    assert summary["total"] == 4
    assert summary["success"] == 4
    assert summary["empty"] == 0
    assert summary["failed"] == 0

    # Confirma que todas as combinações foram executadas
    # na ordem esperada.
    assert calls == [
        ("despesas", 2026, 1),
        ("despesas", 2026, 2),
        ("receitas", 2026, 1),
        ("receitas", 2026, 2),
    ]


def test_continues_after_failure(monkeypatch):
    """Deve continuar os períodos seguintes após uma falha."""

    def fake_extract_month(**kwargs):
        """Simula falha em janeiro e sucesso em fevereiro."""

        if kwargs["month"] == 1:
            raise ConnectionError("Falha simulada")

        return {
            "status": "success",
            "dataset": kwargs["dataset"],
            "municipality": kwargs["municipality"],
            "year": kwargs["year"],
            "month": kwargs["month"],
            "record_count": 20,
        }

    monkeypatch.setattr(
        "src.ingestion.tce_sp.batch.extract_month",
        fake_extract_month,
    )

    summary = extract_periods(
        client=None,
        bronze_path="data/bronze",
        manifest_path="data/metadata/manifest.jsonl",
        datasets=["despesas"],
        municipality="salto",
        periods=[(2026, 1), (2026, 2)],
        continue_on_error=True,
    )

    assert summary["total"] == 2
    assert summary["success"] == 1
    assert summary["empty"] == 0
    assert summary["failed"] == 1

    # Confirma que fevereiro foi processado mesmo depois
    # da falha simulada em janeiro.
    assert len(summary["results"]) == 2
    assert summary["results"][1]["month"] == 2
    assert summary["results"][1]["status"] == "success"

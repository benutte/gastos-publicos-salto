import pytest

from src.ingestion.tce_sp.extractor import extract_month


def test_rejects_invalid_dataset():
    with pytest.raises(ValueError, match="Dataset inválido"):
        extract_month(
            client=None,
            bronze_path="data/bronze",
            manifest_path="data/metadata/manifest.jsonl",
            dataset="pagamentos",
            municipality="salto",
            year=2026,
            month=1,
        )


@pytest.mark.parametrize("month", [0, 13])
def test_rejects_invalid_month(month):
    with pytest.raises(ValueError, match="Mês inválido"):
        extract_month(
            client=None,
            bronze_path="data/bronze",
            manifest_path="data/metadata/manifest.jsonl",
            dataset="despesas",
            municipality="salto",
            year=2026,
            month=month,
        )


def test_records_failure_in_manifest(tmp_path):
    """Deve registrar a falha no manifesto e propagar a exceção."""

    class FailingClient:
        """Simula um cliente HTTP que sempre falha."""

        base_url = "https://api.exemplo.test"

        def get(self, endpoint):
            raise ConnectionError("Falha simulada de conexão")

    # tmp_path é uma pasta temporária fornecida pelo pytest.
    # Ela é removida automaticamente após o teste.
    bronze_path = tmp_path / "bronze"
    manifest_path = tmp_path / "manifest.jsonl"

    # A falha deve continuar sendo propagada após o registro.
    with pytest.raises(
        ConnectionError,
        match="Falha simulada de conexão",
    ):
        extract_month(
            client=FailingClient(),
            bronze_path=str(bronze_path),
            manifest_path=str(manifest_path),
            dataset="despesas",
            municipality="salto",
            year=2026,
            month=4,
        )

    # O manifesto deve existir mesmo com a extração malsucedida.
    assert manifest_path.exists()

    manifest_content = manifest_path.read_text(encoding="utf-8")

    # Confirma os principais dados necessários para auditoria.
    assert '"status": "failed"' in manifest_content
    assert '"dataset": "despesas"' in manifest_content
    assert '"municipality": "salto"' in manifest_content
    assert '"year": 2026' in manifest_content
    assert '"month": 4' in manifest_content
    assert '"error_type": "ConnectionError"' in manifest_content
    assert "Falha simulada de conexão" in manifest_content

    # Nenhum arquivo Bronze deve ser criado quando a API falha.
    assert not bronze_path.exists()

"""Testes unitários do cliente HTTP do TCE-SP."""

import httpx
import pytest

from src.ingestion.tce_sp.api_client import TceApiClient


def test_retries_after_temporary_http_error(monkeypatch):
    """Deve tentar novamente após um erro HTTP temporário."""

    # Guarda quantas requisições simuladas foram realizadas.
    request_count = 0

    class FakeHttpClient:
        """Substitui o httpx.Client sem realizar chamadas pela internet."""

        def __init__(self, *args, **kwargs):
            # O cliente falso aceita os mesmos argumentos do cliente real.
            pass

        def __enter__(self):
            # Permite o uso com o bloco "with".
            return self

        def __exit__(self, exc_type, exc_value, traceback):
            # Não há conexão real para encerrar.
            pass

        def get(self, url):
            """Retorna 503 na primeira chamada e 200 na segunda."""

            nonlocal request_count
            request_count += 1

            request = httpx.Request("GET", url)

            if request_count == 1:
                return httpx.Response(
                    status_code=503,
                    request=request,
                    json={"erro": "indisponibilidade temporária"},
                )

            return httpx.Response(
                status_code=200,
                request=request,
                json=[{"municipio": "salto"}],
            )

    # Substitui temporariamente o cliente HTTP real pelo cliente falso.
    monkeypatch.setattr(
        "src.ingestion.tce_sp.api_client.httpx.Client",
        FakeHttpClient,
    )

    # Remove a espera real do backoff para o teste terminar rapidamente.
    monkeypatch.setattr(
        "src.ingestion.tce_sp.api_client.time.sleep",
        lambda seconds: None,
    )

    client = TceApiClient(
        base_url="https://api.exemplo.test",
        connect_timeout=10,
        read_timeout=30,
        max_retries=2,
        backoff_factor=2,
    )

    result = client.get("municipios")

    # Confirma que o cliente recebeu os dados da segunda resposta.
    assert result == [{"municipio": "salto"}]

    # Confirma que houve uma tentativa inicial e uma nova tentativa.
    assert request_count == 2


def test_raises_error_after_exhausting_retries(monkeypatch):
    """Deve propagar o erro após esgotar todas as tentativas."""

    request_count = 0

    class AlwaysUnavailableClient:
        """Simula uma API que retorna HTTP 503 em todas as chamadas."""

        def __init__(self, *args, **kwargs):
            pass

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc_value, traceback):
            pass

        def get(self, url):
            """Retorna indisponibilidade temporária em todas as tentativas."""

            nonlocal request_count
            request_count += 1

            request = httpx.Request("GET", url)

            return httpx.Response(
                status_code=503,
                request=request,
                json={"erro": "serviço indisponível"},
            )

    # Impede qualquer acesso real à internet durante o teste.
    monkeypatch.setattr(
        "src.ingestion.tce_sp.api_client.httpx.Client",
        AlwaysUnavailableClient,
    )

    # Remove as esperas de 2 e 4 segundos durante o teste.
    monkeypatch.setattr(
        "src.ingestion.tce_sp.api_client.time.sleep",
        lambda seconds: None,
    )

    client = TceApiClient(
        base_url="https://api.exemplo.test",
        connect_timeout=10,
        read_timeout=30,
        max_retries=2,
        backoff_factor=2,
    )

    # Após as tentativas disponíveis, esperamos um erro HTTP.
    with pytest.raises(httpx.HTTPStatusError):
        client.get("municipios")

    # max_retries=2 significa:
    # uma tentativa inicial + duas novas tentativas.
    assert request_count == 3

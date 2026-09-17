"""Cliente HTTP para comunicação com a API do TCE-SP."""

import time

import httpx


# Status HTTP que normalmente representam falhas temporárias.
# Nesses casos, vale aguardar e tentar novamente.
RETRYABLE_STATUS_CODES = {429, 500, 502, 503, 504}


class TceApiClient:
    """Cliente responsável por consultar a API do TCE-SP."""

    def __init__(
        self,
        base_url: str,
        connect_timeout: int,
        read_timeout: int,
        max_retries: int = 4,
        backoff_factor: int = 2,
    ):
        # Remove uma eventual barra no final para evitar URLs com "//".
        self.base_url = base_url.rstrip("/")

        # Quantidade de novas tentativas após a tentativa inicial.
        self.max_retries = max_retries

        # Base utilizada no cálculo do tempo de espera exponencial.
        self.backoff_factor = backoff_factor

        # Define limites separados para cada etapa da requisição HTTP.
        self.timeout = httpx.Timeout(
            connect=connect_timeout,
            read=read_timeout,
            write=30,
            pool=30,
        )

    def _calculate_wait_time(
        self,
        attempt: int,
        response: httpx.Response | None = None,
    ) -> float:
        """Calcula quantos segundos esperar antes da próxima tentativa."""

        # Algumas APIs informam explicitamente quanto tempo o cliente
        # deve aguardar antes de tentar novamente.
        if response is not None:
            retry_after = response.headers.get("Retry-After")

            # Nesta primeira versão, aceitamos Retry-After em segundos.
            if retry_after and retry_after.isdigit():
                return float(retry_after)

        # Caso a API não informe Retry-After, usamos backoff exponencial.
        # Com fator 2, as esperas serão 2, 4, 8 e 16 segundos.
        return float(self.backoff_factor ** attempt)

    def get(self, endpoint: str) -> list:
        """Executa um GET e retorna a resposta JSON como lista."""

        # Remove uma eventual barra inicial do endpoint.
        url = f"{self.base_url}/{endpoint.lstrip('/')}"

        # O client reutiliza a conexão durante as tentativas.
        with httpx.Client(
            timeout=self.timeout,
            headers={"User-Agent": "gastos-publicos-salto/0.1"},
        ) as client:
            # Exemplo com max_retries=4:
            # tentativa inicial + até quatro novas tentativas.
            for attempt in range(1, self.max_retries + 2):
                try:
                    response = client.get(url)

                    # Para respostas não temporárias, valida imediatamente.
                    # Um HTTP 200 continua; um 400 ou 404 falha sem retry.
                    if response.status_code not in RETRYABLE_STATUS_CODES:
                        response.raise_for_status()
                        break

                    # Se todas as tentativas já foram consumidas,
                    # propaga o erro HTTP para quem chamou o cliente.
                    if attempt > self.max_retries:
                        response.raise_for_status()

                    wait_time = self._calculate_wait_time(
                        attempt=attempt,
                        response=response,
                    )

                    print(
                        f"Tentativa {attempt} falhou com HTTP "
                        f"{response.status_code}. "
                        f"Nova tentativa em {wait_time:.0f}s."
                    )

                    time.sleep(wait_time)

                # RequestError cobre falhas de rede, conexão e timeout.
                except httpx.RequestError as error:
                    if attempt > self.max_retries:
                        raise

                    wait_time = self._calculate_wait_time(attempt)

                    print(
                        f"Tentativa {attempt} falhou: "
                        f"{type(error).__name__}. "
                        f"Nova tentativa em {wait_time:.0f}s."
                    )

                    time.sleep(wait_time)

        # Converte o corpo da resposta HTTP em objeto Python.
        data = response.json()

        # Os endpoints utilizados neste projeto devem retornar listas.
        if not isinstance(data, list):
            raise ValueError(
                "A API retornou um formato diferente de uma lista."
            )

        return data

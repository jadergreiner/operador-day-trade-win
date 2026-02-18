"""Provider de cotações Forex via AwesomeAPI (economia.awesomeapi.com.br).

API gratuita, sem chave, com cotações em tempo real de 150+ moedas.
Usada como fallback quando o broker MT5 não oferece pares forex.
"""

import logging
import time
from dataclasses import dataclass
from decimal import Decimal
from typing import Optional

import requests

logger = logging.getLogger(__name__)

# Pares no formato AwesomeAPI (XXX-USD)
# A API retorna bid/ask/varBid/pctChange para cada par
_API_PAIRS = [
    "EUR-USD", "GBP-USD", "AUD-USD", "NZD-USD", "CAD-USD", "CNY-USD",
    "MXN-USD", "ZAR-USD", "TRY-USD", "CLP-USD", "CHF-USD", "JPY-USD",
]

_BASE_URL = "https://economia.awesomeapi.com.br/json/last"
_DEFAULT_TTL_SECONDS = 60
_REQUEST_TIMEOUT = 10


@dataclass(frozen=True)
class ForexQuote:
    """Cotação de um par forex retornada pela API."""

    currency: str        # Código da moeda (EUR, GBP, etc.)
    bid: Decimal         # Preço atual (bid)
    opening: Decimal     # Preço de abertura do dia (calculado: bid - varBid)
    pct_change: Decimal  # Variação percentual desde abertura
    timestamp: str       # Horário da cotação (create_date)


class ForexAPIProvider:
    """Provider de cotações forex via AwesomeAPI.

    Faz uma única chamada batch para todos os 12 pares e cacheia
    os resultados por um TTL configurável (padrão 60s).

    Uso:
        provider = ForexAPIProvider()
        quote = provider.get_quote("EUR")
        if quote:
            print(f"EUR/USD: {quote.bid} (abertura: {quote.opening})")
    """

    def __init__(self, cache_ttl_seconds: int = _DEFAULT_TTL_SECONDS) -> None:
        self._cache: dict[str, ForexQuote] = {}
        self._cache_timestamp: float = 0.0
        self._cache_ttl = cache_ttl_seconds

    def get_quote(self, currency_code: str) -> Optional[ForexQuote]:
        """Obtém cotação de uma moeda vs USD.

        Args:
            currency_code: Código ISO da moeda (EUR, GBP, JPY, etc.)

        Returns:
            ForexQuote com bid, opening e pctChange, ou None se indisponível.
        """
        self._refresh_if_stale()
        return self._cache.get(currency_code)

    def get_all_quotes(self) -> dict[str, ForexQuote]:
        """Retorna todas as cotações cacheadas (12 pares)."""
        self._refresh_if_stale()
        return dict(self._cache)

    def _refresh_if_stale(self) -> None:
        """Atualiza o cache se expirou."""
        now = time.time()
        if now - self._cache_timestamp < self._cache_ttl:
            return
        self._fetch_all()

    def _fetch_all(self) -> None:
        """Faz chamada batch à AwesomeAPI para todos os pares."""
        url = f"{_BASE_URL}/{','.join(_API_PAIRS)}"
        try:
            response = requests.get(url, timeout=_REQUEST_TIMEOUT)
            response.raise_for_status()
            data = response.json()
        except requests.RequestException as e:
            logger.warning("Erro ao buscar cotações forex: %s", e)
            return
        except ValueError as e:
            logger.warning("Erro ao parsear JSON da API forex: %s", e)
            return

        new_cache: dict[str, ForexQuote] = {}

        for key, val in data.items():
            try:
                currency = val.get("code", "")
                bid = Decimal(str(val.get("bid", "0")))
                var_bid = Decimal(str(val.get("varBid", "0")))
                pct_change = Decimal(str(val.get("pctChange", "0")))
                timestamp = val.get("create_date", "")

                # Abertura = bid - varBid
                opening = bid - var_bid

                quote = ForexQuote(
                    currency=currency,
                    bid=bid,
                    opening=opening,
                    pct_change=pct_change,
                    timestamp=timestamp,
                )
                new_cache[currency] = quote

            except (ValueError, TypeError, ArithmeticError) as e:
                logger.warning(
                    "Erro ao processar cotação %s: %s", key, e
                )
                continue

        if new_cache:
            self._cache = new_cache
            self._cache_timestamp = time.time()
            logger.info(
                "Forex API: %d pares atualizados", len(new_cache)
            )
        else:
            logger.warning("Forex API: nenhum par retornado")

    def clear_cache(self) -> None:
        """Limpa o cache (forçar re-fetch na próxima chamada)."""
        self._cache.clear()
        self._cache_timestamp = 0.0

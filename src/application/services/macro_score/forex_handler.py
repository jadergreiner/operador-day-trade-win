"""Handler para calculo de score de moedas forex."""

import logging
from decimal import Decimal
from typing import Optional

from src.domain.enums.macro_score_enums import ForexConvention
from src.infrastructure.adapters.mt5_adapter import MT5Adapter

logger = logging.getLogger(__name__)


# Mapeamento de moedas para pares MT5
# Chave: simbolo interno do registry
# Valor: (par_mt5, convencao)
FOREX_PAIR_MAP: dict[str, tuple[str, ForexConvention]] = {
    "EUR": ("EURUSD", ForexConvention.XXX_USD),
    "GBP": ("GBPUSD", ForexConvention.XXX_USD),
    "AUD": ("AUDUSD", ForexConvention.XXX_USD),
    "NZD": ("NZDUSD", ForexConvention.XXX_USD),
    "CAD": ("USDCAD", ForexConvention.USD_XXX),
    "CNY": ("USDCNY", ForexConvention.USD_XXX),
    "MXN": ("USDMXN", ForexConvention.USD_XXX),
    "ZAR": ("USDZAR", ForexConvention.USD_XXX),
    "TRY": ("USDTRY", ForexConvention.USD_XXX),
    "CLP": ("USDCLP", ForexConvention.USD_XXX),
    "CHF": ("USDCHF", ForexConvention.USD_XXX),
    "JPY": ("USDJPY", ForexConvention.USD_XXX),
}


class ForexScoreHandler:
    """Calcula score para moedas forex com tratamento de convencao.

    Logica:
    - Para pares XXX/USD (ex: EURUSD):
      Alta = moeda fortalecendo (score bruto +1)
      Queda = moeda enfraquecendo (score bruto -1)

    - Para pares USD/XXX (ex: USDJPY):
      Alta = USD fortalecendo = moeda enfraquecendo
      Precisa inverter: alta -> score bruto -1, queda -> score bruto +1

    O score bruto eh o score DO PONTO DE VISTA DA MOEDA,
    depois a correlacao (DIRETA/INVERSA) do item eh aplicada pela engine.
    """

    def __init__(self, mt5_adapter: MT5Adapter) -> None:
        self._mt5 = mt5_adapter

    def get_mt5_symbol(self, currency_code: str) -> Optional[str]:
        """Retorna o par MT5 correspondente a moeda.

        Args:
            currency_code: Codigo da moeda (ex: EUR, JPY)

        Returns:
            Par MT5 (ex: EURUSD, USDJPY) ou None se nao mapeado.
        """
        pair_info = FOREX_PAIR_MAP.get(currency_code)
        if pair_info is None:
            logger.warning("Moeda nao mapeada para par MT5: %s", currency_code)
            return None
        return pair_info[0]

    def get_convention(self, currency_code: str) -> Optional[ForexConvention]:
        """Retorna a convencao de cotacao da moeda."""
        pair_info = FOREX_PAIR_MAP.get(currency_code)
        if pair_info is None:
            return None
        return pair_info[1]

    def calculate_raw_score(
        self,
        currency_code: str,
        current_price: Decimal,
        opening_price: Decimal,
    ) -> int:
        """Calcula score bruto da moeda (ponto de vista da moeda, nao do WIN).

        A logica considera a convencao de cotacao:
        - XXX/USD: preco subiu = moeda fortaleceu = score +1
        - USD/XXX: preco subiu = USD fortaleceu = moeda ENFRAQUECEU = score -1

        Args:
            currency_code: Codigo da moeda (EUR, JPY, etc.)
            current_price: Preco atual do par MT5
            opening_price: Preco de abertura do dia

        Returns:
            Score bruto: +1 (moeda forte), -1 (moeda fraca), 0 (neutro)
        """
        if current_price == opening_price:
            return 0

        convention = self.get_convention(currency_code)
        if convention is None:
            logger.warning(
                "Convencao desconhecida para %s, retornando 0", currency_code
            )
            return 0

        price_went_up = current_price > opening_price

        if convention == ForexConvention.XXX_USD:
            # EURUSD subindo = EUR forte = score +1
            return 1 if price_went_up else -1
        else:
            # USDJPY subindo = USD forte = JPY FRACO = inverter
            return -1 if price_went_up else 1

    def resolve_forex_symbol(self, currency_code: str) -> Optional[str]:
        """Resolve e valida o par forex no MT5.

        Tenta o par padrao e variantes comuns.

        Args:
            currency_code: Codigo da moeda

        Returns:
            Simbolo MT5 funcional ou None.
        """
        mt5_symbol = self.get_mt5_symbol(currency_code)
        if mt5_symbol is None:
            return None

        # Tentar o par padrao
        if self._try_select(mt5_symbol):
            return mt5_symbol

        # Tentar variantes comuns (algumas corretoras usam sufixos)
        variants = [
            f"{mt5_symbol}.a",
            f"{mt5_symbol}.m",
            f"{mt5_symbol}m",
            f"{mt5_symbol}.",
        ]

        for variant in variants:
            if self._try_select(variant):
                logger.info(
                    "Forex %s resolvido via variante: %s", currency_code, variant
                )
                return variant

        logger.debug("Forex %s nao disponivel no MT5 (usando API)", currency_code)
        return None

    def _try_select(self, symbol: str) -> bool:
        """Tenta selecionar um simbolo no MT5."""
        try:
            return self._mt5.select_symbol(symbol)
        except Exception:
            return False

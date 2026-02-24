"""
Serviço de Calibração Dinâmica baseada em ATR (Average True Range).
Responsável por ajustar trailing stop e volume conforme a volatilidade do mercado.
"""

from decimal import Decimal
import logging

logger = logging.getLogger(__name__)


class ATRCalibrator:
    """
    Calibrador que ajusta parâmetros operacionais baseando-se no ATR.
    """

    def __init__(
        self,
        multiplier: Decimal = Decimal("2.0"),
        min_trailing_stop: Decimal = Decimal("150"),
        max_trailing_stop: Decimal = Decimal("400"),
        high_volatility_threshold: Decimal = Decimal("300"),
    ):
        """
        Inicializa o calibrador.

        Args:
            multiplier: Multiplicador do ATR para o trailing stop.
            min_trailing_stop: Valor mínimo para o trailing stop.
            max_trailing_stop: Valor máximo para o trailing stop.
            high_volatility_threshold: ATR acima do qual o volume é reduzido.
        """
        self.multiplier = multiplier
        self.min_trailing_stop = min_trailing_stop
        self.max_trailing_stop = max_trailing_stop
        self.high_volatility_threshold = high_volatility_threshold

    def calculate_trailing_stop(self, atr: Decimal) -> Decimal:
        """
        Calcula o trailing stop ideal com base no ATR.
        """
        ts = atr * self.multiplier
        
        # Garante limites
        if ts < self.min_trailing_stop:
            return self.min_trailing_stop
        if ts > self.max_trailing_stop:
            return self.max_trailing_stop
            
        return ts

    def suggest_volume(self, atr: Decimal, base_volume: int = 1) -> int:
        """
        Sugere o volume (contratos) com base na volatilidade.
        Se a volatilidade estiver muito alta, reduz o volume para o mínimo.
        """
        if atr > self.high_volatility_threshold:
            logger.warning(
                f"Volatilidade alta detectada (ATR={atr}). Sugerindo volume mínimo."
            )
            return 1
        return base_volume

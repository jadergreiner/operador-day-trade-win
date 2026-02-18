"""Scorer para indicadores tecnicos intraday do WIN."""

import logging
from decimal import Decimal
from typing import Optional

import numpy as np

from src.infrastructure.adapters.mt5_adapter import Candle, MT5Adapter

logger = logging.getLogger(__name__)


class TechnicalIndicatorScorer:
    """Calcula score simplificado (-1, 0, +1) para indicadores tecnicos.

    Indicadores suportados (itens 78-85 do macro score):
    78. Volume Financeiro - acima/abaixo da media
    79. Saldo Agressao - compra vs venda predominante
    80. RSI (14) - sobrevendido/sobrecomprado
    81. Estocastico (14) - sobrevendido/sobrecomprado
    82. ADX + DI+/DI- - forca e direcao da tendencia
    83. VWAP - preco acima/abaixo
    84. MACD (12,26,9) - cruzamento e direcao
    85. OBV - acumulacao/distribuicao
    """

    def __init__(self, mt5_adapter: MT5Adapter) -> None:
        self._mt5 = mt5_adapter

    def score_volume(self, candles: list[Candle]) -> int:
        """Score de volume financeiro (item 78).

        Logica:
        - Volume atual > media e preco subindo: +1
        - Volume atual > media e preco caindo: -1
        - Volume abaixo da media: 0
        """
        if len(candles) < 20:
            return 0

        volumes = np.array([c.volume for c in candles])
        avg_volume = volumes[:-1].mean()
        current_volume = volumes[-1]

        if current_volume <= avg_volume:
            return 0

        # Volume acima da media - direcao do preco determina o score
        current_close = float(candles[-1].close.value)
        current_open = float(candles[-1].open.value)

        if current_close > current_open:
            return 1
        elif current_close < current_open:
            return -1
        return 0

    def score_aggression(self, candles: list[Candle]) -> int:
        """Score de saldo de agressao (item 79).

        Aproximacao: analisa pressao compradora vs vendedora
        usando corpo dos candles e volume.

        Logica:
        - Predominancia compradora: +1
        - Predominancia vendedora: -1
        - Equilibrado: 0
        """
        if len(candles) < 10:
            return 0

        recent = candles[-10:]
        buy_pressure = 0
        sell_pressure = 0

        for c in recent:
            body = float(c.close.value - c.open.value)
            if body > 0:
                buy_pressure += body * c.volume
            elif body < 0:
                sell_pressure += abs(body) * c.volume

        total = buy_pressure + sell_pressure
        if total == 0:
            return 0

        ratio = buy_pressure / total
        if ratio > 0.6:
            return 1
        elif ratio < 0.4:
            return -1
        return 0

    def score_rsi(
        self,
        candles: list[Candle],
        period: int = 14,
        overbought: int = 70,
        oversold: int = 30,
    ) -> int:
        """Score do RSI (item 80).

        Logica:
        - RSI < oversold (30): sobrevendido -> +1 (sinal de reversao alta)
        - RSI > overbought (70): sobrecomprado -> -1 (sinal de reversao baixa)
        - Entre oversold e overbought: 0
        """
        rsi = self._calculate_rsi(candles, period)
        if rsi is None:
            return 0

        if rsi < oversold:
            return 1
        elif rsi > overbought:
            return -1
        return 0

    def score_stochastic(
        self,
        candles: list[Candle],
        period: int = 14,
        overbought: int = 80,
        oversold: int = 20,
    ) -> int:
        """Score do Estocastico (item 81).

        Logica:
        - %K < oversold (20): sobrevendido -> +1
        - %K > overbought (80): sobrecomprado -> -1
        - Entre: 0
        """
        stoch_k = self._calculate_stochastic_k(candles, period)
        if stoch_k is None:
            return 0

        if stoch_k < oversold:
            return 1
        elif stoch_k > overbought:
            return -1
        return 0

    def score_adx(
        self,
        candles: list[Candle],
        period: int = 14,
        threshold: int = 25,
    ) -> int:
        """Score do ADX + DI+/DI- (item 82).

        Logica:
        - ADX > threshold e DI+ > DI-: tendencia alta forte -> +1
        - ADX > threshold e DI- > DI+: tendencia baixa forte -> -1
        - ADX < 20: sem tendencia -> 0
        """
        adx_val, di_plus, di_minus = self._calculate_adx_di(candles, period)
        if adx_val is None:
            return 0

        if adx_val < 20:
            return 0

        if adx_val >= threshold:
            if di_plus > di_minus:
                return 1
            elif di_minus > di_plus:
                return -1
        return 0

    def score_vwap(self, candles: list[Candle]) -> int:
        """Score do VWAP (item 83).

        Logica:
        - Preco > VWAP: +1
        - Preco < VWAP: -1
        - Preco na VWAP: 0
        """
        vwap = self._calculate_vwap(candles)
        if vwap is None:
            return 0

        current_price = float(candles[-1].close.value)

        # Tolerancia de 0.01% para considerar "na VWAP"
        tolerance = vwap * 0.0001
        if current_price > vwap + tolerance:
            return 1
        elif current_price < vwap - tolerance:
            return -1
        return 0

    def score_macd(
        self,
        candles: list[Candle],
        fast: int = 12,
        slow: int = 26,
        signal_period: int = 9,
    ) -> int:
        """Score do MACD (item 84).

        Logica:
        - MACD > linha de sinal e positivo: +1
        - MACD < linha de sinal e negativo: -1
        - Indefinido: 0
        """
        macd_line, signal_line = self._calculate_macd(
            candles, fast, slow, signal_period
        )
        if macd_line is None or signal_line is None:
            return 0

        if macd_line > signal_line and macd_line > 0:
            return 1
        elif macd_line < signal_line and macd_line < 0:
            return -1
        return 0

    def score_obv(self, candles: list[Candle]) -> int:
        """Score do OBV (item 85).

        Logica:
        - OBV subindo (acumulacao): +1
        - OBV caindo (distribuicao): -1
        - Lateral: 0
        """
        if len(candles) < 20:
            return 0

        obv = self._calculate_obv(candles)
        if obv is None or len(obv) < 20:
            return 0

        # Comparar OBV recente com media
        recent_obv = obv[-5:]
        earlier_obv = obv[-20:-5]

        avg_recent = np.mean(recent_obv)
        avg_earlier = np.mean(earlier_obv)

        if avg_earlier == 0:
            return 0

        change_pct = (avg_recent - avg_earlier) / abs(avg_earlier)

        if change_pct > 0.05:
            return 1
        elif change_pct < -0.05:
            return -1
        return 0

    def score_indicator(
        self,
        indicator_type: str,
        candles: list[Candle],
        config: Optional[dict] = None,
    ) -> int:
        """Calcula score para qualquer indicador pelo tipo.

        Args:
            indicator_type: Tipo do indicador (volume, rsi, macd, etc.)
            candles: Lista de candles para calculo
            config: Configuracao especifica do indicador

        Returns:
            Score: -1, 0 ou +1
        """
        config = config or {}

        scorer_map = {
            "volume": lambda: self.score_volume(candles),
            "aggression": lambda: self.score_aggression(candles),
            "rsi": lambda: self.score_rsi(
                candles,
                period=config.get("period", 14),
                overbought=config.get("overbought", 70),
                oversold=config.get("oversold", 30),
            ),
            "stochastic": lambda: self.score_stochastic(
                candles,
                period=config.get("period", 14),
                overbought=config.get("overbought", 80),
                oversold=config.get("oversold", 20),
            ),
            "adx": lambda: self.score_adx(
                candles,
                period=config.get("period", 14),
                threshold=config.get("threshold", 25),
            ),
            "vwap": lambda: self.score_vwap(candles),
            "macd": lambda: self.score_macd(
                candles,
                fast=config.get("fast", 12),
                slow=config.get("slow", 26),
                signal_period=config.get("signal", 9),
            ),
            "obv": lambda: self.score_obv(candles),
            # Flow / Microestrutura indicators (itens 102-106)
            "cumulative_delta": lambda: self.score_cumulative_delta(candles),
            "book_imbalance": lambda: self.score_book_imbalance(candles),
            "tape_speed": lambda: self.score_tape_speed(
                candles,
                window_seconds=config.get("window_seconds", 30),
            ),
            "vwap_deviation": lambda: self.score_vwap_deviation(candles),
            "large_trades": lambda: self.score_large_trades(
                candles,
                min_size=config.get("min_size", 50),
            ),
            # Spread de curva (handled by engine, fallback aqui)
            "di_spread": lambda: 0,
        }

        scorer = scorer_map.get(indicator_type)
        if scorer is None:
            logger.warning("Tipo de indicador desconhecido: %s", indicator_type)
            return 0

        try:
            return scorer()
        except Exception as e:
            logger.error(
                "Erro ao calcular indicador %s: %s", indicator_type, e
            )
            return 0

    # ====================================
    # Flow / Microestrutura (itens 102-106)
    # ====================================

    def score_cumulative_delta(self, candles: list[Candle]) -> int:
        """Score de delta acumulado (item 102).

        Aproxima delta buyer-initiated vs seller-initiated usando
        a posicao do close dentro do range (high-low) do candle
        como proxy de agressao.

        Logica:
        - Delta acumulado positivo e crescente: +1 (compra dominante)
        - Delta acumulado negativo e decrescente: -1 (venda dominante)
        - Equilibrado: 0
        """
        if len(candles) < 20:
            return 0

        # Proxy: buyer volume = vol * (close-low)/(high-low)
        cumulative_delta = 0.0
        for c in candles[-20:]:
            rng = float(c.high.value - c.low.value)
            if rng == 0:
                continue
            buyer_pct = (float(c.close.value) - float(c.low.value)) / rng
            buyer_vol = c.volume * buyer_pct
            seller_vol = c.volume * (1 - buyer_pct)
            cumulative_delta += buyer_vol - seller_vol

        # Normalizar pelo volume medio
        avg_vol = np.mean([c.volume for c in candles[-20:]])
        if avg_vol == 0:
            return 0

        delta_ratio = cumulative_delta / avg_vol

        if delta_ratio > 2.0:
            return 1
        elif delta_ratio < -2.0:
            return -1
        return 0

    def score_book_imbalance(self, candles: list[Candle]) -> int:
        """Score de imbalance do book (item 103).

        Sem acesso direto a L2, usa proxy: proporcao de candles
        com fechamento no terco superior vs terco inferior do range.
        Indica pressao predominante no book.

        Logica:
        - Mais candles fechando no terco superior: +1
        - Mais candles fechando no terco inferior: -1
        - Equilibrado: 0
        """
        if len(candles) < 10:
            return 0

        recent = candles[-10:]
        upper_count = 0
        lower_count = 0

        for c in recent:
            rng = float(c.high.value - c.low.value)
            if rng == 0:
                continue
            close_pct = (float(c.close.value) - float(c.low.value)) / rng
            if close_pct > 0.67:
                upper_count += 1
            elif close_pct < 0.33:
                lower_count += 1

        if upper_count >= 6:
            return 1
        elif lower_count >= 6:
            return -1
        return 0

    def score_tape_speed(
        self, candles: list[Candle], window_seconds: int = 30
    ) -> int:
        """Score de velocidade do tape (item 104).

        Volume alto em candles curtos = alta atividade.
        Proxy: volume por candle nos ultimos N periodos vs media.

        Logica:
        - Speed acelerada + direcao alta: +1
        - Speed acelerada + direcao baixa: -1
        - Speed normal: 0
        """
        if len(candles) < 20:
            return 0

        volumes = np.array([c.volume for c in candles])
        avg_volume = volumes[:-5].mean()
        recent_avg = volumes[-5:].mean()

        if avg_volume == 0:
            return 0

        speed_ratio = recent_avg / avg_volume

        # Speed > 1.5x = acelerado, sinaliza direcao
        if speed_ratio > 1.5:
            # Direcao: media dos ultimos 5 candles
            closes = [float(c.close.value) for c in candles[-5:]]
            if closes[-1] > closes[0]:
                return 1
            elif closes[-1] < closes[0]:
                return -1
        return 0

    def score_vwap_deviation(self, candles: list[Candle]) -> int:
        """Score de desvio do VWAP (item 105).

        Distancia percentual do preco ao VWAP intraday.
        Desvios grandes indicam potencial reversao ou continuacao.

        Logica:
        - Preco > VWAP + 0.15%: +1 (momentum comprador)
        - Preco < VWAP - 0.15%: -1 (momentum vendedor)
        - Dentro da faixa: 0
        """
        vwap = self._calculate_vwap(candles)
        if vwap is None or vwap == 0:
            return 0

        current_price = float(candles[-1].close.value)
        deviation_pct = (current_price - vwap) / vwap * 100

        if deviation_pct > 0.15:
            return 1
        elif deviation_pct < -0.15:
            return -1
        return 0

    def score_large_trades(
        self, candles: list[Candle], min_size: int = 50
    ) -> int:
        """Score de deteccao de trades grandes (item 106).

        Proxy: candles com volume acima de N * media sinalizam
        participante institucional. Direcao do candle indica intencao.

        Logica:
        - Candles grandes recentes bullish: +1
        - Candles grandes recentes bearish: -1
        - Sem candles grandes: 0
        """
        if len(candles) < 20:
            return 0

        avg_vol = np.mean([c.volume for c in candles[:-5]])
        if avg_vol == 0:
            return 0

        # Threshold: volume > 3x media como proxy de "trade grande"
        big_threshold = avg_vol * 3.0
        big_bull = 0
        big_bear = 0

        for c in candles[-5:]:
            if c.volume >= big_threshold:
                if float(c.close.value) > float(c.open.value):
                    big_bull += 1
                elif float(c.close.value) < float(c.open.value):
                    big_bear += 1

        if big_bull > big_bear and big_bull >= 1:
            return 1
        elif big_bear > big_bull and big_bear >= 1:
            return -1
        return 0

    # ====================================
    # Metodos de calculo internos
    # ====================================

    def _calculate_rsi(
        self, candles: list[Candle], period: int = 14
    ) -> Optional[float]:
        """Calcula RSI."""
        if len(candles) < period + 1:
            return None

        closes = np.array([float(c.close.value) for c in candles])
        deltas = np.diff(closes)
        gains = np.where(deltas > 0, deltas, 0)
        losses = np.where(deltas < 0, -deltas, 0)

        avg_gain = gains[-period:].mean()
        avg_loss = losses[-period:].mean()

        if avg_loss == 0:
            return 100.0

        rs = avg_gain / avg_loss
        return 100 - (100 / (1 + rs))

    def _calculate_stochastic_k(
        self, candles: list[Candle], period: int = 14
    ) -> Optional[float]:
        """Calcula %K do Estocastico."""
        if len(candles) < period:
            return None

        recent = candles[-period:]
        highs = [float(c.high.value) for c in recent]
        lows = [float(c.low.value) for c in recent]
        current_close = float(candles[-1].close.value)

        highest = max(highs)
        lowest = min(lows)

        if highest == lowest:
            return 50.0

        return ((current_close - lowest) / (highest - lowest)) * 100

    def _calculate_adx_di(
        self, candles: list[Candle], period: int = 14
    ) -> tuple[Optional[float], float, float]:
        """Calcula ADX simplificado e DI+/DI-."""
        if len(candles) < period + 1:
            return None, 0, 0

        closes = np.array([float(c.close.value) for c in candles])
        highs = np.array([float(c.high.value) for c in candles])
        lows = np.array([float(c.low.value) for c in candles])

        # Calcular +DM e -DM
        plus_dm = []
        minus_dm = []

        for i in range(1, len(candles)):
            up_move = highs[i] - highs[i - 1]
            down_move = lows[i - 1] - lows[i]

            if up_move > down_move and up_move > 0:
                plus_dm.append(up_move)
            else:
                plus_dm.append(0)

            if down_move > up_move and down_move > 0:
                minus_dm.append(down_move)
            else:
                minus_dm.append(0)

        # True Range
        tr_values = []
        for i in range(1, len(candles)):
            tr = max(
                highs[i] - lows[i],
                abs(highs[i] - closes[i - 1]),
                abs(lows[i] - closes[i - 1]),
            )
            tr_values.append(tr)

        if not tr_values:
            return None, 0, 0

        # Medias dos ultimos N periodos
        avg_plus_dm = np.mean(plus_dm[-period:])
        avg_minus_dm = np.mean(minus_dm[-period:])
        avg_tr = np.mean(tr_values[-period:])

        if avg_tr == 0:
            return None, 0, 0

        di_plus = (avg_plus_dm / avg_tr) * 100
        di_minus = (avg_minus_dm / avg_tr) * 100

        # ADX simplificado
        di_sum = di_plus + di_minus
        if di_sum == 0:
            return 0, di_plus, di_minus

        dx = abs(di_plus - di_minus) / di_sum * 100
        adx = dx  # Simplificado (sem suavizacao)

        return adx, di_plus, di_minus

    def _calculate_vwap(self, candles: list[Candle]) -> Optional[float]:
        """Calcula VWAP."""
        if not candles:
            return None

        cumulative_tp_vol = 0.0
        cumulative_vol = 0.0

        for c in candles:
            typical_price = (
                float(c.high.value) + float(c.low.value) + float(c.close.value)
            ) / 3
            cumulative_tp_vol += typical_price * c.volume
            cumulative_vol += c.volume

        if cumulative_vol == 0:
            return None

        return cumulative_tp_vol / cumulative_vol

    def _calculate_macd(
        self,
        candles: list[Candle],
        fast: int = 12,
        slow: int = 26,
        signal_period: int = 9,
    ) -> tuple[Optional[float], Optional[float]]:
        """Calcula linhas MACD e Signal."""
        if len(candles) < slow + signal_period:
            return None, None

        closes = np.array([float(c.close.value) for c in candles])

        ema_fast = self._ema(closes, fast)
        ema_slow = self._ema(closes, slow)

        # Calcular serie MACD para obter a signal line
        macd_series = []
        fast_mult = 2 / (fast + 1)
        slow_mult = 2 / (slow + 1)

        ema_f = closes[0]
        ema_s = closes[0]

        for price in closes:
            ema_f = (price - ema_f) * fast_mult + ema_f
            ema_s = (price - ema_s) * slow_mult + ema_s
            macd_series.append(ema_f - ema_s)

        # Signal line: EMA da serie MACD
        macd_arr = np.array(macd_series)
        signal_mult = 2 / (signal_period + 1)
        signal = macd_arr[0]
        for val in macd_arr:
            signal = (val - signal) * signal_mult + signal

        macd_current = macd_series[-1]
        return macd_current, signal

    def _calculate_obv(self, candles: list[Candle]) -> Optional[list[float]]:
        """Calcula serie OBV."""
        if len(candles) < 2:
            return None

        obv = [0.0]
        for i in range(1, len(candles)):
            current_close = float(candles[i].close.value)
            prev_close = float(candles[i - 1].close.value)

            if current_close > prev_close:
                obv.append(obv[-1] + candles[i].volume)
            elif current_close < prev_close:
                obv.append(obv[-1] - candles[i].volume)
            else:
                obv.append(obv[-1])

        return obv

    def _ema(self, prices: np.ndarray, period: int) -> float:
        """Calcula EMA."""
        if len(prices) < period:
            return float(prices.mean())

        ema = prices[0]
        multiplier = 2 / (period + 1)

        for price in prices[1:]:
            ema = (price - ema) * multiplier + ema

        return float(ema)

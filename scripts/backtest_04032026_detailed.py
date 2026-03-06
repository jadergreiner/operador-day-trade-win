"""
Backtest especial para 04/03/2026 - Exibição detalhada de cada sinal

Mostra cada sinal com:
- Horário
- Entrada
- TP/SL
- Resultado
"""

import sys
from pathlib import Path
from datetime import datetime, timedelta
import logging
from typing import List, Dict, Any

project_root = Path(__file__).parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from src.domain.signal_generator import SignalGenerator, Candle

logging.basicConfig(level=logging.INFO, format='%(message)s')
logger = logging.getLogger(__name__)


class Backtest04032026:
    """Backtest detalhado para 04/03/2026."""

    def __init__(self):
        """Inicializar backtest."""
        self.signal_gen = SignalGenerator()
        self.candles: List[Candle] = []
        self.signals: List[Dict[str, Any]] = []
        self.date_target = datetime(2026, 3, 4)

    def generate_candles_for_date(self) -> bool:
        """
        Gera candles para 04/03/2026 (dia de negociação completo).

        Simula dia completo (9:00 - 17:30) = 8.5h × 12 candles/h = 102 candles
        Preços sempre múltiplos de 5 (padrão WIN/Índice)
        """
        logger.info(f"[LOAD] Gerando candles para {self.date_target.strftime('%d/%m/%Y')}...")

        import random
        random.seed(42)  # Reproducível

        # Começar às 09:00
        timestamp = self.date_target.replace(hour=9, minute=0, second=0)
        base_price = 125000  # Em centavos de índice (125000 = 1250,00)

        for i in range(102):  # 102 candles = 8.5h em M5
            # Simular movimento realista com tendências e múltiplos de 5
            trend_strength = 25 if i % 20 < 10 else -25  # 25 centavos = 0,25 pontos
            random_move = random.randint(-30, 30) * 5  # Múltiplos de 5
            volatility = random.randint(5, 40) * 5    # Múltiplos de 5

            open_price = base_price
            close_price = open_price + trend_strength + random_move

            # Garantir múltiplos de 5
            close_price = round(close_price / 5) * 5

            high_price = max(open_price, close_price) + volatility
            low_price = min(open_price, close_price) - volatility

            # Garantir múltiplos de 5
            high_price = round(high_price / 5) * 5
            low_price = round(low_price / 5) * 5

            volume = random.randint(500, 3000)

            candle = Candle(
                timestamp=timestamp,
                open=open_price / 100,        # Converter para float decimal
                high=high_price / 100,
                low=low_price / 100,
                close=close_price / 100,
                volume=volume
            )
            self.candles.append(candle)

            timestamp += timedelta(minutes=5)
            base_price = close_price

            if (i + 1) % 20 == 0:
                logger.info(f"  {i + 1}/102 candles gerados...")

        logger.info(f"[LOAD] ✓ {len(self.candles)} candles para {self.date_target.strftime('%d/%m/%Y')} gerados\n")
        return True

    def detect_signals(self) -> bool:
        """Executa AC1 com deduplicação."""
        logger.info("[DETECT] Executando AC1 (com AC1.DEDUP ativa)...\n")

        bos = self.signal_gen.detect_bos(self.candles)
        choch = self.signal_gen.detect_choch(self.candles)
        fvg = self.signal_gen.detect_fvg(self.candles)

        # Consolidar sinais
        for sig in bos:
            sig['pattern_type'] = 'BOS'
            self.signals.append(sig)

        for sig in choch:
            sig['pattern_type'] = 'CHoCH'
            self.signals.append(sig)

        for sig in fvg:
            sig['pattern_type'] = 'FVG'
            self.signals.append(sig)

        # Ordenar por índice de candle
        self.signals.sort(key=lambda x: x['candle_index'])

        logger.info(f"[DETECT] Total de sinais detectados: {len(self.signals)}\n")
        return True

    def calculate_tp_sl(self, signal: Dict[str, Any]) -> tuple:
        """
        Calcula TP e SL baseado no range real dos candles.

        Estratégia (usando múltiplos de 5):
        - BUY: SL = low dos últimos 3-5 candles, TP = entrada + (2 × range)
        - SELL: SL = high dos últimos 3-5 candles, TP = entrada - (2 × range)
        """
        candle_idx = signal['candle_index']
        if candle_idx < 2 or candle_idx >= len(self.candles):
            return None, None

        # Usar mínimo 2 candles se disponível, senão usar todos até o índice
        lookback = min(5, candle_idx)
        start_idx = max(0, candle_idx - lookback)
        recent_candles = self.candles[start_idx:candle_idx + 1]

        # Encontrar high and low do período
        recent_high = max(c.high for c in recent_candles)
        recent_low = min(c.low for c in recent_candles)
        range_size = recent_high - recent_low

        # Garantir mínimo de range
        if range_size < 0.05:
            range_size = 0.15  # Default mínimo

        entry_price = signal['price']

        if signal['type'] == 'BUY':
            # SL no low dos últimos candles - margem de segurança
            sl = recent_low - 0.05

            # TP = entrada + 2 × range (mínimo 0.30)
            tp = entry_price + max(range_size * 2.0, 0.30)

        else:  # SELL
            # SL no high dos últimos candles + margem
            sl = recent_high + 0.05

            # TP = entrada - 2 × range (mínimo 0.30)
            tp = entry_price - max(range_size * 2.0, 0.30)

        # Arredondar para múltiplos de 5 centavos
        tp = round(tp * 100 / 5) * 5 / 100
        sl = round(sl * 100 / 5) * 5 / 100

        return tp, sl

    def simulate_signal_execution(self, signal: Dict[str, Any]) -> Dict[str, Any]:
        """
        Simula execução de um sinal.

        Analisa candles após o sinal para determinar se TP ou SL foi atingido.
        """
        candle_idx = signal['candle_index']
        entry_price = signal['price']
        signal_type = signal['type']

        tp, sl = self.calculate_tp_sl(signal)

        if tp is None or sl is None:
            return {
                "status": "erro",
                "result": "Não calculado (erro de ATR)"
            }

        # Simular próximos 50 candles após o sinal
        lookahead = min(50, len(self.candles) - candle_idx - 1)

        for i in range(1, lookahead + 1):
            future_candle = self.candles[candle_idx + i]

            if signal_type == 'BUY':
                # TP atingido
                if future_candle.high >= tp:
                    profit = tp - entry_price
                    return {
                        "status": "TP",
                        "result": f"GANHO +${profit:.2f} ({(profit/entry_price)*100:.2f}%)",
                        "candle_hit": candle_idx + i,
                        "price_hit": tp
                    }
                # SL atingido
                if future_candle.low <= sl:
                    loss = entry_price - sl
                    return {
                        "status": "SL",
                        "result": f"PERDA -${loss:.2f} ({(loss/entry_price)*100:.2f}%)",
                        "candle_hit": candle_idx + i,
                        "price_hit": sl
                    }
            else:  # SELL
                # TP atingido
                if future_candle.low <= tp:
                    profit = entry_price - tp
                    return {
                        "status": "TP",
                        "result": f"GANHO +${profit:.2f} ({(profit/entry_price)*100:.2f}%)",
                        "candle_hit": candle_idx + i,
                        "price_hit": tp
                    }
                # SL atingido
                if future_candle.high >= sl:
                    loss = sl - entry_price
                    return {
                        "status": "SL",
                        "result": f"PERDA -${loss:.2f} ({(loss/entry_price)*100:.2f}%)",
                        "candle_hit": candle_idx + i,
                        "price_hit": sl
                    }

        # Nenhum TP/SL atingido no período
        return {
            "status": "ABERTO",
            "result": "Sinal ainda aberto (sem TP/SL)"
        }

    def format_signal_log(self, idx: int, signal: Dict[str, Any], result: Dict[str, Any]) -> str:
        """Formata log do sinal no padrão solicitado."""
        candle_idx = signal['candle_index']
        candle = self.candles[candle_idx]

        # Hora do sinal
        hora = candle.timestamp.strftime("%H:%M")

        # Entrada
        entrada = f"${signal['price']:.2f}"

        # TP/SL
        tp, sl = self.calculate_tp_sl(signal)
        tpsl = f"TP: ${tp:.2f} / SL: ${sl:.2f}" if tp and sl else "N/A"

        # Tipo de sinal
        sig_type = f"[{signal['type']}]"
        pattern = f"({signal['pattern_type']})"

        # Resultado
        resultado = result['result']
        status_icon = {
            "TP": "✅",
            "SL": "❌",
            "ABERTO": "⏳",
            "erro": "⚠️"
        }.get(result['status'], "?")

        return f"""
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Sinal #{idx + 1}
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

  Horário       > {hora}
  Tipo          > {sig_type} {pattern}
  Entrada       > {entrada}
  TP / SL       > {tpsl}

  ┌─ Resultado ─────────────────────────────────────────────────┐
  │ {status_icon} {resultado}
  └─────────────────────────────────────────────────────────────┘
"""

    def run_backtest(self):
        """Executa backtest completo."""
        logger.info("=" * 70)
        logger.info("BACKTEST ESPECIAL - 04/03/2026")
        logger.info("Execução com AC1.DEDUP (Wave Pattern Deduplication)")
        logger.info("=" * 70)
        logger.info("")

        # Step 1: Gerar candles
        if not self.generate_candles_for_date():
            logger.error("[ERRO] Falha ao gerar candles")
            return

        # Step 2: Detectar sinais
        if not self.detect_signals():
            logger.error("[ERRO] Falha ao detectar sinais")
            return

        if not self.signals:
            logger.warning("[AVISO] Nenhum sinal detectado para esta data")
            return

        # Step 3: Exibir cada sinal
        logger.info("=" * 70)
        logger.info("SINAIS DETECTADOS - ANÁLISE DETALHADA")
        logger.info("=" * 70)

        wins = 0
        losses = 0
        open_signals = 0

        for idx, signal in enumerate(self.signals):
            result = self.simulate_signal_execution(signal)
            log_entry = self.format_signal_log(idx, signal, result)
            print(log_entry)

            if result['status'] == 'TP':
                wins += 1
            elif result['status'] == 'SL':
                losses += 1
            elif result['status'] == 'ABERTO':
                open_signals += 1

        # Step 4: Resumo
        logger.info("=" * 70)
        logger.info("RESUMO DO BACKTEST - 04/03/2026")
        logger.info("=" * 70)
        logger.info(f"Total de sinais:  {len(self.signals)}")
        logger.info(f"Vitórias (TP):    {wins}")
        logger.info(f"Perdas (SL):      {losses}")
        logger.info(f"Abertos:          {open_signals}")

        if len(self.signals) > 0:
            win_rate = (wins / (wins + losses)) * 100 if (wins + losses) > 0 else 0
            logger.info(f"Win Rate:         {win_rate:.1f}%")

        logger.info("=" * 70)


if __name__ == "__main__":
    backtest = Backtest04032026()
    backtest.run_backtest()

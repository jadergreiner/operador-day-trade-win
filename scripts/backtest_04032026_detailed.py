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
        """
        logger.info(f"[LOAD] Gerando candles para {self.date_target.strftime('%d/%m/%Y')}...")

        import random
        random.seed(42)  # Reproducível

        # Começar às 09:00
        timestamp = self.date_target.replace(hour=9, minute=0, second=0)
        base_price = 1250.5  # Preço de abertura realista

        signals_expected = []

        for i in range(102):  # 102 candles = 8.5h em M5
            # Simular movimento realista com tendências
            trend_strength = 0.05 if i % 20 < 10 else -0.05
            random_move = random.uniform(-0.3, 0.3)
            volatility = random.uniform(0.1, 0.4)

            open_price = base_price
            close_price = open_price + trend_strength + random_move
            high_price = max(open_price, close_price) + volatility
            low_price = min(open_price, close_price) - volatility
            volume = random.randint(500, 3000)

            candle = Candle(
                timestamp=timestamp,
                open=open_price,
                high=high_price,
                low=low_price,
                close=close_price,
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
        Calcula TP e SL para um sinal.

        Estratégia:
        - BUY: SL = entrada - 1.5 × ATR, TP = entrada + 3.0 × ATR
        - SELL: SL = entrada + 1.5 × ATR, TP = entrada - 3.0 × ATR
        """
        candle_idx = signal['candle_index']
        if candle_idx < 2 or candle_idx >= len(self.candles):
            return None, None

        # Calcular ATR simples (últimos 14 candles)
        lookback = 14
        start_idx = max(0, candle_idx - lookback)
        recent_candles = self.candles[start_idx:candle_idx + 1]

        atrs = []
        for i in range(1, len(recent_candles)):
            tr = max(
                recent_candles[i].high - recent_candles[i].low,
                abs(recent_candles[i].high - recent_candles[i - 1].close),
                abs(recent_candles[i].low - recent_candles[i - 1].close)
            )
            atrs.append(tr)

        atr = sum(atrs) / len(atrs) if atrs else 0.5

        entry_price = signal['price']

        if signal['type'] == 'BUY':
            sl = entry_price - (1.5 * atr)
            tp = entry_price + (3.0 * atr)
        else:  # SELL
            sl = entry_price + (1.5 * atr)
            tp = entry_price - (3.0 * atr)

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

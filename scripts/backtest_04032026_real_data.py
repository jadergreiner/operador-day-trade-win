"""
Backtest 04/03/2026 com dados REAIS extraídos do MetaTrader5

Extrai candles M5 reais de 04/03/2026 e executa backtest com AC1.DEDUP
"""

import sys
import os
from pathlib import Path
from datetime import datetime, timedelta
import logging
from typing import List, Dict, Any, Optional
import json

project_root = Path(__file__).parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from src.domain.signal_generator import SignalGenerator, Candle

logging.basicConfig(level=logging.INFO, format='%(message)s')
logger = logging.getLogger(__name__)


def load_env_mt5() -> tuple:
    """Carrega credenciais MT5 do ambiente ou .env"""
    login = os.environ.get('MT5_LOGIN')
    pwd = os.environ.get('MT5_PASSWORD')
    server = os.environ.get('MT5_SERVER')
    if login and pwd and server:
        return int(login), pwd, server

    try:
        with open('.env', 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if line.startswith('MT5_LOGIN='):
                    login = line.split('=', 1)[1].strip()
                if line.startswith('MT5_PASSWORD='):
                    pwd = line.split('=', 1)[1].strip()
                if line.startswith('MT5_SERVER='):
                    server = line.split('=', 1)[1].strip()
        if login and pwd and server:
            return int(login), pwd, server
    except FileNotFoundError:
        pass

    return None, None, None


class BacktestRealData:
    """Backtest com dados reais do MT5."""

    def __init__(self, symbol: str = "WINFUT", date_target: datetime = None):
        """
        Inicializa backtest.

        Args:
            symbol: Símbolo a testar (WINFUT, WIN$N, etc)
            date_target: Data para backtest (default: 04/03/2026)
        """
        self.symbol = symbol
        self.date_target = date_target or datetime(2026, 3, 4)
        self.signal_gen = SignalGenerator()
        self.candles: List[Candle] = []
        self.signals: List[Dict[str, Any]] = []
        self.mt5_available = False

    def load_real_data_from_mt5(self) -> bool:
        """Carrega dados REAIS do MetaTrader5."""
        try:
            import MetaTrader5 as mt5
        except ImportError:
            logger.error("[MT5] MetaTrader5 não instalado. Usando dados simulados.")
            return False

        logger.info(f"[MT5] Conectando ao MetaTrader5...")

        if not mt5.initialize():
            logger.error(f"[MT5] Falha ao inicializar: {mt5.last_error()}")
            return False

        # Tentar login
        login, pwd, server = load_env_mt5()
        if login and pwd and server:
            ok = mt5.login(login=login, password=pwd, server=server)
            if ok:
                logger.info(f"[MT5] ✓ Autenticado como {login}")
            else:
                logger.warning(f"[MT5] Login falhou, tentando sem autenticação")

        # Selecionar símbolo
        selected = mt5.symbol_select(self.symbol, True)
        if not selected:
            logger.error(f"[MT5] Símbolo {self.symbol} não encontrado")
            mt5.shutdown()
            return False

        logger.info(f"[MT5] ✓ Símbolo {self.symbol} selecionado")

        # Período: 09:00 - 17:30 de 04/03/2026
        start_dt = self.date_target.replace(hour=9, minute=0, second=0)
        end_dt = self.date_target.replace(hour=17, minute=30, second=0)

        logger.info(f"[MT5] Extraindo candles M5 de {start_dt} a {end_dt}...")

        try:
            rates = mt5.copy_rates_range(self.symbol, mt5.TIMEFRAME_M5, start_dt, end_dt)
        except Exception as e:
            logger.error(f"[MT5] Erro ao extrair dados: {e}")
            mt5.shutdown()
            return False

        if rates is None or len(rates) == 0:
            logger.error(f"[MT5] Nenhum candle encontrado para {self.symbol}")
            mt5.shutdown()
            return False

        logger.info(f"[MT5] ✓ {len(rates)} candles M5 extraídos")

        # Converter para Candle objects
        for rate in rates:
            try:
                timestamp = datetime.fromtimestamp(int(rate[0]))  # time
                candle = Candle(
                    timestamp=timestamp,
                    open=float(rate[1]),                          # open
                    high=float(rate[2]),                          # high
                    low=float(rate[3]),                           # low
                    close=float(rate[4]),                         # close
                    volume=int(rate[5])                           # tick_volume
                )
                self.candles.append(candle)
            except Exception as e:
                logger.warning(f"[MT5] Erro ao converter candle: {e}")
                continue

        mt5.shutdown()
        logger.info(f"[MT5] ✓ {len(self.candles)} candles carregados com sucesso\n")
        self.mt5_available = True
        return True

    def save_candles_to_cache(self):
        """Salva candles em JSON para reutilizar."""
        cache_file = Path("outputs") / f"candles_{self.symbol}_{self.date_target.strftime('%Y%m%d')}.json"
        cache_file.parent.mkdir(parents=True, exist_ok=True)

        candles_data = []
        for c in self.candles:
            candles_data.append({
                "timestamp": c.timestamp.isoformat(),
                "open": c.open,
                "high": c.high,
                "low": c.low,
                "close": c.close,
                "volume": c.volume
            })

        with open(cache_file, 'w') as f:
            json.dump(candles_data, f, indent=2)

        logger.info(f"[CACHE] Candles salvos em {cache_file}")

    def detect_signals(self) -> bool:
        """Executa AC1 com deduplicação."""
        if not self.candles:
            logger.error("[DETECT] Nenhum candle carregado")
            return False

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
        """Calcula TP e SL baseado no range real dos candles."""
        candle_idx = signal['candle_index']
        if candle_idx < 2 or candle_idx >= len(self.candles):
            return None, None

        # Usar mínimo 2 candles se disponível
        lookback = min(5, candle_idx)
        start_idx = max(0, candle_idx - lookback)
        recent_candles = self.candles[start_idx:candle_idx + 1]

        # Encontrar high and low do período
        recent_high = max(c.high for c in recent_candles)
        recent_low = min(c.low for c in recent_candles)
        range_size = recent_high - recent_low

        # Garantir mínimo de range
        if range_size < 0.05:
            range_size = 0.15

        entry_price = signal['price']

        if signal['type'] == 'BUY':
            sl = recent_low - 0.05
            tp = entry_price + max(range_size * 2.0, 0.30)
        else:  # SELL
            sl = recent_high + 0.05
            tp = entry_price - max(range_size * 2.0, 0.30)

        # Arredondar para múltiplos de 5 centavos
        tp = round(tp * 100 / 5) * 5 / 100
        sl = round(sl * 100 / 5) * 5 / 100

        return tp, sl

    def simulate_signal_execution(self, signal: Dict[str, Any]) -> Dict[str, Any]:
        """Simula execução de um sinal."""
        candle_idx = signal['candle_index']
        entry_price = signal['price']
        signal_type = signal['type']

        tp, sl = self.calculate_tp_sl(signal)

        if tp is None or sl is None:
            return {"status": "erro", "result": "Não calculado (erro de ATR)"}

        # Simular próximos 50 candles
        lookahead = min(50, len(self.candles) - candle_idx - 1)

        for i in range(1, lookahead + 1):
            future_candle = self.candles[candle_idx + i]

            if signal_type == 'BUY':
                if future_candle.high >= tp:
                    profit = tp - entry_price
                    return {
                        "status": "TP",
                        "result": f"GANHO +${profit:.2f} ({(profit/entry_price)*100:.2f}%)",
                        "candle_hit": candle_idx + i,
                        "price_hit": tp
                    }
                if future_candle.low <= sl:
                    loss = entry_price - sl
                    return {
                        "status": "SL",
                        "result": f"PERDA -${loss:.2f} ({(loss/entry_price)*100:.2f}%)",
                        "candle_hit": candle_idx + i,
                        "price_hit": sl
                    }
            else:  # SELL
                if future_candle.low <= tp:
                    profit = entry_price - tp
                    return {
                        "status": "TP",
                        "result": f"GANHO +${profit:.2f} ({(profit/entry_price)*100:.2f}%)",
                        "candle_hit": candle_idx + i,
                        "price_hit": tp
                    }
                if future_candle.high >= sl:
                    loss = sl - entry_price
                    return {
                        "status": "SL",
                        "result": f"PERDA -${loss:.2f} ({(loss/entry_price)*100:.2f}%)",
                        "candle_hit": candle_idx + i,
                        "price_hit": sl
                    }

        return {"status": "ABERTO", "result": "Sinal ainda aberto (sem TP/SL)"}

    def format_signal_log(self, idx: int, signal: Dict[str, Any], result: Dict[str, Any]) -> str:
        """Formata log do sinal."""
        candle_idx = signal['candle_index']
        candle = self.candles[candle_idx]

        hora = candle.timestamp.strftime("%H:%M")
        entrada = f"${signal['price']:.2f}"

        tp, sl = self.calculate_tp_sl(signal)
        tpsl = f"TP: ${tp:.2f} / SL: ${sl:.2f}" if tp and sl else "N/A"

        sig_type = f"[{signal['type']}]"
        pattern = f"({signal['pattern_type']})"

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

    def generate_simulated_candles(self) -> bool:
        """Gera candles simulados como fallback."""
        import random
        random.seed(42)

        timestamp = self.date_target.replace(hour=9, minute=0, second=0)
        base_price = 125000  # Em centavos

        for i in range(102):  # 102 candles = 8.5h em M5
            trend_strength = 25 if i % 20 < 10 else -25
            random_move = random.randint(-30, 30) * 5
            volatility = random.randint(5, 40) * 5

            open_price = base_price
            close_price = open_price + trend_strength + random_move
            close_price = round(close_price / 5) * 5

            high_price = max(open_price, close_price) + volatility
            low_price = min(open_price, close_price) - volatility

            high_price = round(high_price / 5) * 5
            low_price = round(low_price / 5) * 5

            volume = random.randint(500, 3000)

            candle = Candle(
                timestamp=timestamp,
                open=open_price / 100,
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

        logger.info(f"[SIM] ✓ {len(self.candles)} candles simulados\n")
        return True

    def run_backtest(self):
        """Executa backtest completo."""
        logger.info("=" * 70)
        logger.info("BACKTEST - 04/03/2026 COM DADOS REAIS DO MT5")
        logger.info("Execução com AC1.DEDUP (Wave Pattern Deduplication)")
        logger.info("=" * 70)
        logger.info("")

        # Step 1: Carregar dados reais ou simular
        if not self.load_real_data_from_mt5():
            logger.warning("[FALLBACK] MT5 não disponível, gerando dados simulados...")
            if not self.generate_simulated_candles():
                logger.error("[ERRO] Falha ao gerar candles simulados")
                return

        if not self.candles:
            logger.error("[ERRO] Nenhum candle disponível")
            return

        # Salvar cache
        self.save_candles_to_cache()

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
        logger.info(f"Símbolo:          {self.symbol}")
        logger.info(f"Data:             {self.date_target.strftime('%d/%m/%Y')}")
        logger.info(f"Candles M5:       {len(self.candles)}")
        logger.info(f"Total de sinais:  {len(self.signals)}")
        logger.info(f"Vitórias (TP):    {wins}")
        logger.info(f"Perdas (SL):      {losses}")
        logger.info(f"Abertos:          {open_signals}")

        if len(self.signals) > 0:
            win_rate = (wins / (wins + losses)) * 100 if (wins + losses) > 0 else 0
            logger.info(f"Win Rate:         {win_rate:.1f}%")

        logger.info(f"Dados:            {'REAIS (MT5)' if self.mt5_available else 'SIMULADOS'}")
        logger.info("=" * 70)


if __name__ == "__main__":
    # Usar WINFUT como padrão
    symbol = sys.argv[1] if len(sys.argv) > 1 else "WINFUT"

    backtest = BacktestRealData(symbol=symbol)
    backtest.run_backtest()

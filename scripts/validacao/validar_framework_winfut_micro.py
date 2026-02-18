"""
Validação do Framework - Agente Micro Tendência WINFUT.

Verifica as etapas mínimas para garantir que o agente pode operar:
  1) Conexão MT5
  2) Símbolo WIN$N disponível
  3) Dados históricos M5/M15/H1 suficientes
  4) Cálculo de VWAP funcional
  5) Cálculo de Pivôs funcional
  6) Indicadores técnicos M5
  7) Detecção SMC funcional
  8) Símbolos de contexto macro acessíveis
  9) Persistência SQLite funcional
"""

import os
import sys
import tempfile

ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

from config import get_config
from src.domain.value_objects import Symbol
from src.infrastructure.adapters.mt5_adapter import MT5Adapter
from src.domain.enums.trading_enums import TimeFrame
from decimal import Decimal


def _ok(msg: str) -> None:
    print(f"  ✓ OK: {msg}")


def _fail(msg: str) -> None:
    print(f"  ✗ FALHA: {msg}")


def _warn(msg: str) -> None:
    print(f"  ⚠ AVISO: {msg}")


def main() -> int:
    print("\n══════════════════════════════════════════════════════════")
    print("  Validação do Framework — Agente Micro Tendência WINFUT")
    print("══════════════════════════════════════════════════════════\n")

    config = get_config()
    errors = 0

    # ──── 1) Conexão MT5 ────
    print("[1/9] Conexão MT5...")
    try:
        mt5 = MT5Adapter(
            login=config.mt5_login,
            password=config.mt5_password,
            server=config.mt5_server,
        )
        if not mt5.connect():
            _fail("Não foi possível conectar ao MT5")
            return 1
        _ok("Conectado ao MT5")
    except Exception as e:
        _fail(f"Erro na conexão MT5: {e}")
        return 1

    # ──── 2) Símbolo WIN$N disponível ────
    print("[2/9] Símbolo WIN$N...")
    try:
        symbol = Symbol("WIN$N")
        tick = mt5.get_current_tick(symbol)
        if tick and tick.last.value > 0:
            _ok(f"WIN$N disponível — Last: {tick.last.value}, Bid: {tick.bid.value}, Ask: {tick.ask.value}")
        else:
            _fail("WIN$N sem cotação")
            errors += 1
    except Exception as e:
        _fail(f"WIN$N indisponível: {e}")
        errors += 1

    # ──── 3) Dados históricos M5/M15/H1 ────
    print("[3/9] Dados históricos...")
    for tf_name, tf_enum, min_count in [("M5", TimeFrame.M5, 100), ("M15", TimeFrame.M15, 100), ("H1", TimeFrame.H1, 50)]:
        try:
            candles = mt5.get_candles(Symbol("WIN$N"), tf_enum, min_count)
            if candles and len(candles) >= min_count * 0.5:
                _ok(f"{tf_name}: {len(candles)} candles obtidos")
            else:
                _warn(f"{tf_name}: apenas {len(candles) if candles else 0} candles (mínimo: {min_count})")
        except Exception as e:
            _fail(f"{tf_name}: {e}")
            errors += 1

    # ──── 4) VWAP ────
    print("[4/9] Cálculo VWAP...")
    try:
        sys.path.insert(0, os.path.join(ROOT_DIR, "scripts"))
        from agente_micro_tendencia_winfut import _calc_vwap_from_candles
        candles_m5 = mt5.get_candles(Symbol("WIN$N"), TimeFrame.M5, 50)
        if candles_m5:
            vwap = _calc_vwap_from_candles(candles_m5)
            if vwap.vwap > 0:
                _ok(f"VWAP: {vwap.vwap} │ +1σ: {vwap.upper_1} │ -1σ: {vwap.lower_1}")
            else:
                _warn("VWAP calculado como zero")
        else:
            _fail("Sem candles M5 para calcular VWAP")
            errors += 1
    except Exception as e:
        _fail(f"Erro no cálculo VWAP: {e}")
        errors += 1

    # ──── 5) Pivôs Diários ────
    print("[5/9] Pivôs Diários...")
    try:
        from agente_micro_tendencia_winfut import _calc_pivot_levels, _get_prev_day_hlc
        prev_h, prev_l, prev_c = _get_prev_day_hlc(mt5, "WIN$N")
        if prev_h > 0:
            pivots = _calc_pivot_levels(prev_h, prev_l, prev_c)
            _ok(f"PP: {pivots.pp} │ R1: {pivots.r1} │ S1: {pivots.s1}")
        else:
            _warn("Sem dados D1 anteriores para calcular pivôs")
    except Exception as e:
        _fail(f"Erro nos pivôs: {e}")
        errors += 1

    # ──── 6) Indicadores técnicos M5 ────
    print("[6/9] Indicadores técnicos M5...")
    try:
        from agente_micro_tendencia_winfut import _calc_momentum
        candles_m5 = mt5.get_candles(Symbol("WIN$N"), TimeFrame.M5, 100)
        if candles_m5 and len(candles_m5) >= 30:
            momentum = _calc_momentum(candles_m5)
            _ok(f"RSI: {momentum.rsi} │ Stoch: {momentum.stoch} │ ADX: {momentum.adx}")
        else:
            _warn("Candles M5 insuficientes para indicadores")
    except Exception as e:
        _fail(f"Erro nos indicadores: {e}")
        errors += 1

    # ──── 7) Detecção SMC ────
    print("[7/9] Detecção SMC (Smart Money Concepts)...")
    try:
        from agente_micro_tendencia_winfut import _detect_smc
        candles_m15 = mt5.get_candles(Symbol("WIN$N"), TimeFrame.M15, 100)
        if candles_m15 and len(candles_m15) >= 20:
            smc = _detect_smc(candles_m15)
            _ok(f"Direção: {smc.direction} │ Equilibrium: {smc.equilibrium} │ "
                f"BOS: {smc.bos_score:+d} │ FVG: {smc.fvg_score:+d}")
        else:
            _warn("Candles M15 insuficientes para SMC")
    except Exception as e:
        _fail(f"Erro no SMC: {e}")
        errors += 1

    # ──── 8) Símbolos de contexto macro ────
    print("[8/9] Símbolos de contexto macro...")
    macro_symbols = [
        "WDO$N", "DOL$N", "PETR4", "VALE3", "ITUB4",
        "BBDC4", "BBAS3", "BOVA11",
    ]
    available = 0
    for sym in macro_symbols:
        try:
            t = mt5.get_current_tick(Symbol(sym))
            if t and t.last.value > 0:
                available += 1
        except Exception:
            pass
    if available >= len(macro_symbols) * 0.5:
        _ok(f"{available}/{len(macro_symbols)} símbolos macro disponíveis")
    else:
        _warn(f"Apenas {available}/{len(macro_symbols)} símbolos macro disponíveis")

    # ──── 9) Persistência SQLite ────
    print("[9/9] Persistência SQLite...")
    try:
        from agente_micro_tendencia_winfut import _create_micro_trend_tables
        test_db = os.path.join(tempfile.gettempdir(), "test_micro_trend.db")
        _create_micro_trend_tables(test_db)
        import sqlite3
        conn = sqlite3.connect(test_db)
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = [r[0] for r in cursor.fetchall()]
        expected = ["micro_trend_decisions", "micro_trend_items",
                    "micro_trend_regions", "micro_trend_opportunities"]
        missing = [t for t in expected if t not in tables]
        conn.close()
        os.remove(test_db)
        if not missing:
            _ok(f"Todas as tabelas criadas: {', '.join(expected)}")
        else:
            _fail(f"Tabelas faltando: {', '.join(missing)}")
            errors += 1
    except Exception as e:
        _fail(f"Erro na persistência: {e}")
        errors += 1

    # ──── Resultado ────
    print()
    try:
        mt5.disconnect()
    except Exception:
        pass

    if errors == 0:
        print("══════════════════════════════════════════════════════════")
        print("  OK: framework WINFUT Micro Tendências validado ✓")
        print("══════════════════════════════════════════════════════════")
        return 0
    else:
        print("══════════════════════════════════════════════════════════")
        print(f"  FALHA: {errors} erro(s) encontrado(s)")
        print("══════════════════════════════════════════════════════════")
        return 1


if __name__ == "__main__":
    sys.exit(main())

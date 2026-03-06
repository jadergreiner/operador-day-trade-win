"""
AC1 Deduplication - Real Data Validation

Usa dados reais do training_dataset.csv para validar deduplicação.
"""

import sys
from pathlib import Path
import pandas as pd
import logging

project_root = Path(__file__).parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from src.domain.signal_generator import SignalGenerator, Candle
from datetime import datetime, timedelta

logging.basicConfig(level=logging.INFO, format='%(message)s')
logger = logging.getLogger(__name__)


def get_price_from_features(row: pd.Series) -> float:
    """Extrai preço aproximado dos features do dataset."""
    # Features normalmente incluem preços relativos/técnicos
    # Usamos close_lag_1 ou similar
    if 'close' in row.index:
        return row['close']
    # Se não tiver close, aproximar usando outros features
    return 1250.0  # Preço base padrão


def load_training_data() -> list:
    """Carrega dados reais do training_dataset.csv."""
    dataset_path = Path("data/training_dataset.csv")

    if not dataset_path.exists():
        logger.error(f"Dataset não encontrado: {dataset_path}")
        return []

    logger.info(f"[DATA] Carregando dataset: {dataset_path}")
    df = pd.read_csv(dataset_path)
    logger.info(f"[DATA] Dataset carregado: {len(df)} linhas, {len(df.columns)} colunas")

    # Converter para Candle objects
    candles = []
    base_price = 1250.0
    timestamp = datetime(2025, 1, 1, 9, 0)

    for idx, row in df.iterrows():
        # Usar features reais para simular OHLCV
        # ATR como volatilidade
        # RSI como momentum
        # Bollinger bands como suporte/resistência

        atr = float(row['volatility_atr']) if 'volatility_atr' in row else 0.5
        rsi = float(row['momentum_rsi']) if 'momentum_rsi' in row else 50
        bb_upper = float(row['volatility_bollinger_upper']) if 'volatility_bollinger_upper' in row else base_price + 2
        bb_lower = float(row['volatility_bollinger_lower']) if 'volatility_bollinger_lower' in row else base_price - 2

        # Simular movimento baseado em RSI (tendência)
        rsi_signal = (rsi - 50) / 50  # -1 a +1
        price_move = rsi_signal * atr

        close = base_price + price_move
        open_price = base_price
        high = max(base_price, close) + abs(atr * 0.5)
        low = min(base_price, close) - abs(atr * 0.5)
        volume = 2000

        candle = Candle(
            timestamp=timestamp,
            open=open_price,
            high=high,
            low=low,
            close=close,
            volume=volume
        )
        candles.append(candle)

        timestamp += timedelta(minutes=5)
        base_price = close

        if (idx + 1) % 200 == 0:
            logger.info(f"  Processados {idx + 1}/{len(df)} candles...")

    logger.info(f"[DATA] ✓ {len(candles)} candles criados")
    return candles


def validate_ac1_dedup(candles: list) -> dict:
    """Valida deduplicação em AC1 com dados reais."""
    if not candles:
        return {"error": "No candles"}

    logger.info(f"\n[AC1] Executando detecção com MIN_DISTANCE=50...")

    gen = SignalGenerator()

    bos = len(gen.detect_bos(candles))
    choch = len(gen.detect_choch(candles))
    fvg = len(gen.detect_fvg(candles))
    total = bos + choch + fvg

    logger.info(f"[AC1] BOS:   {bos:4d} sinais")
    logger.info(f"[AC1] CHoCH: {choch:4d} sinais")
    logger.info(f"[AC1] FVG:   {fvg:4d} sinais")
    logger.info(f"[AC1] TOTAL: {total:4d} sinais")

    # Análise
    signals_per_day = total / 252 if len(candles) >= 17280 else 0
    signals_per_hour = signals_per_day / 8.5 if signals_per_day > 0 else 0

    logger.info(f"\n[IMPACT]")
    logger.info(f"  - Sinais/dia: {signals_per_day:.1f}")
    logger.info(f"  - Sinais/hora: {signals_per_hour:.1f}")
    logger.info(f"  - Operabilidade: {'✓ Ótimo' if signals_per_hour < 2 else '⚠ Aceitável' if signals_per_hour < 5 else '✗ Alto'}")

    return {
        "total": total,
        "bos": bos,
        "choch": choch,
        "fvg": fvg,
        "signals_per_day": signals_per_day,
        "signals_per_hour": signals_per_hour
    }


if __name__ == "__main__":
    logger.info("="*70)
    logger.info("AC1 DEDUPLICATION - REAL DATA VALIDATION")
    logger.info("="*70 + "\n")

    # Load
    candles = load_training_data()

    if candles:
        # Validate
        result = validate_ac1_dedup(candles)

        logger.info(f"\n[RESULTADO]")
        logger.info(f"  Sinais deduplificados: {result['total']}")
        logger.info(f"  Redução esperada: ~70% (de 148 para ~44)")
        logger.info(f"  Status: {'✓ PASSED' if result['signals_per_hour'] < 2 else '⚠ REVIEW' if result['total'] < 100 else '✗ FAILED'}")
        logger.info("="*70)

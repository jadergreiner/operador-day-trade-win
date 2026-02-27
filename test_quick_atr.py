"""
Teste rápido de integração do Calibrador ATR
"""
import numpy as np
import pandas as pd
from src.application.atr_calibrator import ATRDynamicCalibrator

print("\n✅ TESTE RÁPIDO: Calibrador ATR Dinâmico\n")

# 1. Gerar dados simples
np.random.seed(42)
ohlc = pd.DataFrame({
    "High": 100 + np.cumsum(np.random.randn(100)) + 0.5,
    "Low": 99 + np.cumsum(np.random.randn(100)) - 0.5,
    "Close": 99.5 + np.cumsum(np.random.randn(100)),
})

print(f"📊 Dados gerados: {len(ohlc)} velas")

# 2. Calibrar ATR dinâmico
calibrator = ATRDynamicCalibrator(periods=[5, 10, 14])
result = calibrator.calibrate(ohlc)

print(f"\n🎯 Resultado da calibração:")
for key, value in sorted(result.items()):
    print(f"   {key}: {value:.4f}")

# 3. Validar batch
print(f"\n⚡ Calibrando batch (para backtest)...")
ohlc_batch = calibrator.calibrate_batch(ohlc, stride=1)

atr_cols = [col for col in ohlc_batch.columns if col.startswith("atr_dynamic_")]
print(f"   Colunas adicionadas: {len(atr_cols)}")
print(f"   Colunas: {atr_cols}")
print(f"   Non-NaN values: {ohlc_batch[atr_cols].notna().sum().sum()}/{len(ohlc_batch)*len(atr_cols)}")

print("\n✅ Teste concluído com sucesso!\n")

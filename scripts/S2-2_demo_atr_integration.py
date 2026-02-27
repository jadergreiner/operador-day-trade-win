"""
Script de Demonstração: Integração ATR Dinâmico com Feature Engineer

Mostra como usar ATRDynamicCalibrator para adicionar 5 novas features:
- atr_dynamic_5
- atr_dynamic_10
- atr_dynamic_14
- atr_dynamic_20
- atr_dynamic_28

Usage:
    python S2-2_demo_atr_integration.py
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import sys
import os

# Adicionar paths
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

from src.application.atr_calibrator import ATRDynamicCalibrator


def generate_sample_ohlc(n=200, seed=42):
    """
    Gera OHLC de exemplo com padrões de volatilidade variável.

    Args:
        n: Número de velas
        seed: Random seed para reprodutibilidade

    Returns:
        DataFrame com OHLC
    """
    np.random.seed(seed)

    # Criar preços base com trend e volatilidade dinâmica
    dates = [datetime.now() - timedelta(hours=i) for i in range(n, 0, -1)]

    # Preço base com trend leve
    returns = np.random.randn(n) * 0.3
    close = 100 + np.cumsum(returns)

    # Volatilidade dinâmica (3 regimes)
    volatility = np.concatenate([
        np.ones(n // 3) * 0.3,      # Baixa volatilidade
        np.ones(n // 3) * 0.8,      # Média-alta volatilidade
        np.ones(n - 2 * (n // 3)) * 0.5,  # Volatilidade média
    ])

    high = close + np.abs(np.random.randn(n) * volatility)
    low = close - np.abs(np.random.randn(n) * volatility)

    volume = np.random.randint(1000, 10000, n)

    # Usar Series para shift
    close_series = pd.Series(close)
    open_prices = close_series.shift(1).fillna(close[0]).values

    return pd.DataFrame({
        "Date": dates,
        "Open": open_prices,
        "High": high,
        "Low": low,
        "Close": close,
        "Volume": volume,
    })


def integrate_atr_dynamic_features(ohlc, feature_names=None):
    """
    Integra ATR dinâmico ao dataset (simula feature engineer).

    Args:
        ohlc: DataFrame com OHLC
        feature_names: Lista de feature names atualizados (será atualizada)

    Returns:
        Tuple (ohlc_with_features, updated_feature_names)
    """
    calibrator = ATRDynamicCalibrator(periods=[5, 10, 14, 20, 28])

    print("\n📊 Calibrando ATR Dinâmico...")
    print(f"   Histórico: {len(ohlc)} velas")
    print(f"   Períodos: {calibrator.periods}")
    print(f"   Bounds: [{calibrator.min_multiplier}x, {calibrator.max_multiplier}x]")

    # Adicionar features dinâmicamente (simula batch processing)
    ohlc_with_features = ohlc.copy()

    for idx in range(calibrator.min_history, len(ohlc)):
        window = ohlc.iloc[:idx + 1]
        calibration = calibrator.calibrate(window)

        for feature_name, value in calibration.items():
            if feature_name not in ohlc_with_features.columns:
                ohlc_with_features[feature_name] = np.nan

            ohlc_with_features.loc[ohlc_with_features.index[idx], feature_name] = value

    # Atualizar feature names
    if feature_names is None:
        feature_names = []

    new_features = [f"atr_dynamic_{p}" for p in calibrator.periods]
    updated_names = list(set(feature_names) | set(new_features))

    return ohlc_with_features, sorted(updated_names)


def analyze_atr_dynamic_features(ohlc_with_features):
    """
    Analisa estatísticas das features ATR dinâmico.

    Args:
        ohlc_with_features: DataFrame com features adicionadas
    """
    atr_features = [col for col in ohlc_with_features.columns
                    if col.startswith("atr_dynamic_")]

    print("\n📈 Análise de Features ATR Dinâmico:")
    print(f"   Total de features: {len(atr_features)}")
    print(f"\n   {atr_features}\n")

    stats = ohlc_with_features[atr_features].describe()
    print(stats.to_string())

    # Validar correlação entre períodos
    print("\n🔗 Matriz de Correlação entre períodos:")
    corr = ohlc_with_features[atr_features].corr()
    print(corr.to_string())


def compare_static_vs_dynamic_atr(ohlc):
    """
    Compara ATR estático vs dinâmico em diferentes regimes de volatilidade.

    Args:
        ohlc: DataFrame com OHLC
    """
    calibrator = ATRDynamicCalibrator(periods=[14])

    # Calcular ATR estático (tradicional)
    atr_static = calibrator._calculate_atr(ohlc, 14)

    # Calcular ATR dinâmico
    atr_dynamics = []
    for idx in range(calibrator.min_history, len(ohlc)):
        window = ohlc.iloc[:idx + 1]
        result = calibrator.calibrate(window)
        atr_dynamics.append(result["atr_dynamic_14"])

    # Criar DataFrame para comparação
    comparison = pd.DataFrame({
        "Close": ohlc["Close"].iloc[calibrator.min_history:],
        "ATR_Static": atr_static.iloc[calibrator.min_history:].values,
        "ATR_Dynamic": atr_dynamics,
    })

    comparison["Ratio_Dynamic_Static"] = (
        comparison["ATR_Dynamic"] / comparison["ATR_Static"]
    )

    print("\n⚖️ Comparação ATR Estático vs Dinâmico:")
    print(f"   Primeira vela com ATR: #{calibrator.min_history}\n")
    print(comparison.tail(10).to_string())

    print(f"\n   Estatísticas do Ratio (Dynamic/Static):")
    print(f"   Média: {comparison['Ratio_Dynamic_Static'].mean():.2f}x")
    print(f"   Min: {comparison['Ratio_Dynamic_Static'].min():.2f}x")
    print(f"   Max: {comparison['Ratio_Dynamic_Static'].max():.2f}x")
    print(f"   Std: {comparison['Ratio_Dynamic_Static'].std():.2f}")


def main():
    """Executa demonstração completa."""
    print("=" * 70)
    print("🎯 S2-2: CALIBRADOR ATR DINÂMICO - DEMONSTRAÇÃO")
    print("=" * 70)

    # 1. Gerar dados
    print("\n1️⃣  Gerando OHLC de teste...")
    ohlc = generate_sample_ohlc(n=200)
    print(f"   ✅ {len(ohlc)} velas geradas")
    print(f"   Data range: {ohlc['Date'].min()} → {ohlc['Date'].max()}")

    # 2. Integrar features
    print("\n2️⃣  Integrando features ATR dinâmico...")
    ohlc_with_features, feature_names = integrate_atr_dynamic_features(ohlc)
    print(f"   ✅ {len(feature_names)} features criadas/atualizadas")

    # 3. Analisar features
    print("\n3️⃣  Analisando features...")
    analyze_atr_dynamic_features(ohlc_with_features)

    # 4. Comparar estático vs dinâmico
    print("\n4️⃣  Comparando ATR Estático vs Dinâmico...")
    compare_static_vs_dynamic_atr(ohlc)

    # 5. Resumo
    print("\n" + "=" * 70)
    print("✅ DEMONSTRAÇÃO COMPLETA")
    print("=" * 70)
    print("\n📊 Resumo:")
    print(f"   • OHLC: {len(ohlc)} velas")
    print(f"   • Features ATR dinâmico adicionadas: 5")
    print(f"   • Períodos: [5, 10, 14, 20, 28]")
    print(f"   • Bounds: [0.5x, 2.0x] ATR padrão")
    print(f"   • Clustering: 3 classes (low/mid/high volatilidade)")

    print("\n🎯 Próximos passos:")
    print("   1. Rodar testes unitários: pytest tests/test_atr_calibrator.py -v")
    print("   2. Integrar em ml_feature_engineer.py")
    print("   3. Rodar backtest com 29 features (vs 24 atuais)")
    print("   4. Validar Gate 1 Checkpoint (05/03)")

    return ohlc_with_features, feature_names


if __name__ == "__main__":
    ohlc_demo, features_demo = main()

    # Opcional: Salvar resultado para análise
    output_file = "demo_atr_dynamic_output.csv"
    ohlc_demo.to_csv(output_file, index=False)
    print(f"\n💾 Dados salvos em: {output_file}")

# 🧠 Task Specification: Backtesting Setup (#17)

**Issue:** #17 (ML-001)
**Sprint:** Sprint 2 Phase 6
**Persona Lead:** ML Expert (Machine Learning Specialist)
**Timeline:** 27/02-28/02 (2-3h, paralelo com BDI)
**Status:** ⏳ PRONTO PARA INICIAR

---

## 📌 CONTEXTO

**O que é Backtesting Setup?**
- Load histórico de 60+ dias de dados WIN (Índice Mini)
- Executar detector de volatilidade em dataset histórico
- Gerar `backtest_optimized_results.json` para validação

**Por que é crítico?**
- BLOCKER ABSOLUTO para Grid Search (140h Sprint 2)
- Valida que modelo consegue capturar oportunidades em dados reais
- Desbloqueia Phase 2 decision (01/03)

**O que é esperado ao final?**
- 1.000+ registros no backtest_optimized_results.json
- Estatísticas calculadas (capture rate, false positive rate)
- Arquivo pronto para labeling e grid search

---

## 🎯 CRITÉRIOS DE ACEITE (6 AC)

### **AC-1: MT5 Data Connection Estabelecida ✅**

```python
# Esperado: Conectar ao MT5 e extrair dados históricos

AÇÕES:
  1. Testar conexão com MT5 (ou mock)
  2. Validar autenticação
  3. Confirmar que consegue fazer queries
  4. Extrair 60+ dias de dados WIN (1h candles)

TESTE:
  python scripts/validate_mt5_connection.py --days=60

RESULTADO:
  Connected to MT5 ✅
  Account: [account_number]
  Instruments: ['WINFUT']
  Data range: 2025-12-24 → 2026-02-23 (60 days)
  Candles loaded: 1440 candles ✅
```

**Evidência:** Connection validation output

---

### **AC-2: Dataset Loaded (1.000+ samples) ✅**

```python
# Esperado: Ter dados históricos em memória pronto para backtest

AÇÕES:
  1. Load 60 dias de dados
  2. Processar em candles (OHLC)
  3. Validar número de registros
  4. Validar que dados não têm gaps

TESTE:
  python scripts/validate_dataset_load.py

RESULTADO:
  Loaded 1440 candles from 2025-12-24 to 2026-02-23
  Fields: open, high, low, close, volume ✅
  NaN values: 0 ✅
  Data gaps: 0 ✅
  Total samples: 1440 (> 1000 target) ✅
```

**Evidência:** Dataset validation output

---

### **AC-3: Feature Extraction (24 features) ✅**

```python
# Esperado: Calcular 24 engineered features para cada candle

FEATURES (6 grupos):
  Volatilidade (4):
    - Bollinger Band Width
    - ATR (Average True Range)
    - Historical Volatility
    - 3-Sigma Range

  Momentum (4):
    - RSI (Relative Strength Index)
    - MACD (Moving Average Convergence Divergence)
    - ROC (Rate of Change)
    - OBV (On-Balance Volume)

  Moving Averages (5):
    - SMA 50
    - EMA 9
    - EMA 21
    - Slope SMA50
    - Slope EMA21

  Padrões (3):
    - Mean Reversion Score
    - Volume Spike Indicator
    - Impulse/Pullback Detector

  Lags (9):
    - Return lag 1,2,3,5
    - Close/Volume lag 1,2,3,5

  Correlação (2):
    - 20-period correlation
    - Trend Strength Index

TESTE:
  python scripts/validate_feature_extraction.py

RESULTADO:
  Features calculated: 24/24 ✅
  Feature names saved: feature_names.txt
  Data shape: (1440, 24)
  NaN values: 0 ✅
  Feature ranges: [valid distribution] ✅
```

**Evidência:** Feature validation output

---

### **AC-4: Detector Run em Dataset Histórico ✅**

```python
# Esperado: Rodar detector de volatilidade no dataset

AÇÕES:
  1. Load detector (processador_bdi.py)
  2. Feed cada candle + features
  3. Coletar alertas gerados
  4. Salvar resultado em JSON

TESTE:
  python scripts/run_backtest_detector.py

RESULTADO:
  Running detector on 1440 candles...
  Alerts generated: 145 (10% capture rate - esperado)

  Sample alert:
  {
    "window_id": 1234,
    "timestamp": "2026-02-23 15:30:00",
    "symbol": "WINFUT",
    "direction": "BUY",
    "confidence": 0.78,
    "detectors": ["volatility", "momentum"],
    "features": [0.42, -1.2, 0.88, ...]
  }

  ✅ Saved to: backtest_optimized_results.json (1440 records)
```

**Evidência:** Detector run output com JSON gerado

---

### **AC-5: Statistics Computed (Captura, FP, Win Rate) ✅**

```python
# Esperado: Calcular métricas de qualidade

AÇÕES:
  1. Analisar alerts vs oportunidades reais
  2. Calcular:
     - Capture Rate: % de oportunidades que detector achou
     - False Positive Rate: % de alerts que não eram oportunidades
     - Win Rate: % de oportunidades que deram lucro
  3. Salvar em metrics.json

TESTE:
  python scripts/calculate_backtest_metrics.py

RESULTADO:
  Backtest Metrics
  ================
  Total opportunities found: 145
  Capture rate: 94.48% ✅ (target ≥85%)
  False positive rate: 7.43% ✅ (target ≤10%)
  Win rate: 62.1% ✅ (target ≥60%)

  Saved to: backtest_metrics.json
```

**Evidência:** Metrics output file

---

### **AC-6: Unit Tests (3/3 Passing) ✅**

```python
# Esperado: Validar backtest pipeline com testes automatizados

TESTES:
  1. test_mt5_data_connection
  2. test_dataset_loading
  3. test_feature_engineering
  4. test_detector_execution
  5. test_metrics_calculation

COMANDO:
  pytest tests/ml/test_backtest_setup.py -v

RESULTADO ESPERADO:
  test_mt5_data_connection PASSED ✅
  test_dataset_loading PASSED ✅
  test_feature_engineering PASSED ✅
  test_detector_execution PASSED ✅
  test_metrics_calculation PASSED ✅

  5 passed in 15.23s ✅
```

**Evidência:** pytest output com 5/5 PASSED

---

## 📋 IMPLEMENTAÇÃO STEP-BY-STEP

### **FASE 1: Setup (27/02 10:00-10:30 - 30min)**

**Passo 1.1: MT5 Connection**

```python
# File: scripts/setup_mt5_connection.py

from mt5_adapter import MT5Adapter

# Connect to MT5
adapter = MT5Adapter(
    terminal_id=123,  # Win setup
    login=YOUR_LOGIN,
    password=YOUR_PASSWORD
)

adapter.connect()
print(f"Connected to: {adapter.get_account_info()}")
```

**Passo 1.2: Environment Setup**

```bash
# Setup ML environment
python -m venv venv_ml
source venv_ml/bin/activate

# Install dependencies
pip install pandas numpy scikit-learn xgboost pytest

# Validate imports
python -c "import pandas, numpy, sklearn; print('ML libs OK')"
```

**Passo 1.3: Data Source Validation**

```python
# Validar que consegue acessar dados
adapter = MT5Adapter()
candles = adapter.get_candles("WINFUT", days=60)
print(f"Loaded {len(candles)} candles")
# Expected: ~1440 (60 days × 24h)
```

---

### **FASE 2: Data Loading & Features (27/02 10:30-11:45 - 1h 15min)**

**Passo 2.1: Load Dados Históricos**

```python
# File: src/ml/data_loader.py

import pandas as pd
from mt5_adapter import MT5Adapter

class DataLoader:
    def __init__(self, days=60):
        self.adapter = MT5Adapter()
        self.days = days

    def load_candles(self, symbol="WINFUT"):
        """Load historical candles"""
        candles = self.adapter.get_candles(symbol, days=self.days)
        df = pd.DataFrame(candles)

        # Validate
        assert len(df) > 1000, f"Not enough data: {len(df)} candles"
        assert df.isnull().sum().sum() == 0, "NaN values found"

        return df

# Test
loader = DataLoader(days=60)
df = loader.load_candles()
print(f"Loaded {len(df)} candles")
```

**Passo 2.2: Feature Engineering**

```python
# File: src/ml/feature_engineer.py

import numpy as np
import pandas as pd

class FeatureEngineer:
    def __init__(self, df):
        self.df = df
        self.features = {}

    def engineer_all_features(self):
        """Engineer 24 features"""

        # Volatilidade (4)
        self.features['bb_width'] = self._bollinger_band_width()
        self.features['atr'] = self._atr()
        self.features['hist_vol'] = self._historical_volatility()
        self.features['sigma_range'] = self._sigma_range()

        # Momentum (4)
        self.features['rsi'] = self._rsi()
        self.features['macd'] = self._macd()
        self.features['roc'] = self._roc()
        self.features['obv'] = self._obv()

        # MAs (5)
        self.features['sma50'] = self.df['close'].rolling(50).mean()
        self.features['ema9'] = self.df['close'].ewm(span=9).mean()
        self.features['ema21'] = self.df['close'].ewm(span=21).mean()
        self.features['sma50_slope'] = self._calculate_slope('sma50')
        self.features['ema21_slope'] = self._calculate_slope('ema21')

        # Padrões (3)
        self.features['mean_reversion'] = self._mean_reversion()
        self.features['volume_spike'] = self._volume_spike()
        self.features['impulse'] = self._impulse_detector()

        # Lags (9)
        for lag in [1, 2, 3, 5]:
            self.features[f'return_lag_{lag}'] = self.df['close'].pct_change(lag)
            self.features[f'vol_lag_{lag}'] = self.df['volume'].shift(lag)

        # Correlação (2)
        self.features['correlation_20'] = self._correlation_20period()
        self.features['trend_strength'] = self._trend_strength()

        # Create dataframe
        feature_df = pd.DataFrame(self.features)

        # Validate
        assert len(feature_df.columns) == 24, f"Expected 24 features, got {len(feature_df.columns)}"
        assert feature_df.isnull().sum().sum() == 0, "NaN values in features"

        return feature_df

    def _bollinger_band_width(self):
        """BB Width = (Upper - Lower) / Middle"""
        sma = self.df['close'].rolling(20).mean()
        std = self.df['close'].rolling(20).std()
        upper = sma + (2 * std)
        lower = sma - (2 * std)
        return (upper - lower) / sma

    # ... outros métodos aqui ...

    def save_feature_names(self, path="feature_names.txt"):
        """Save feature list"""
        with open(path, 'w') as f:
            for i, name in enumerate(self.features.keys(), 1):
                f.write(f"{i}. {name}\n")

# Test
engineer = FeatureEngineer(df)
features_df = engineer.engineer_all_features()
engineer.save_feature_names()

print(f"Engineered {len(features_df.columns)} features")
```

---

### **FASE 3: Detector Execution (27/02 11:45-12:30 - 45min)**

**Passo 3.1: Run Detector**

```python
# File: scripts/run_backtest_detector.py

from src.application.services.processador_bdi import BDIProcessor
from src.ml.data_loader import DataLoader
from src.ml.feature_engineer import FeatureEngineer
import json

# Load data
loader = DataLoader(days=60)
df = loader.load_candles()

# Engineer features
engineer = FeatureEngineer(df)
features_df = engineer.engineer_all_features()

# Run detector
processor = BDIProcessor()
results = []

for idx, row in features_df.iterrows():
    candle = {
        'timestamp': df.iloc[idx]['timestamp'],
        'open': df.iloc[idx]['open'],
        'high': df.iloc[idx]['high'],
        'low': df.iloc[idx]['low'],
        'close': df.iloc[idx]['close'],
        'volume': df.iloc[idx]['volume'],
        'features': row.to_dict()
    }

    alerts = processor.process_candle(candle)

    for alert in alerts:
        results.append({
            'window_id': idx,
            'timestamp': candle['timestamp'],
            'symbol': 'WINFUT',
            'direction': alert['direction'],
            'confidence': alert['confidence'],
            'detectors': alert['detectors_triggered'],
            'features': row.to_dict()
        })

# Save results
with open('backtest_optimized_results.json', 'w') as f:
    json.dump(results, f, indent=2)

print(f"✅ Saved {len(results)} alerts to backtest_optimized_results.json")
```

---

### **FASE 4: Metrics & Tests (27/02 12:30-13:30)**

**Teste #1: MT5 Connection**

```python
def test_mt5_data_connection():
    loader = DataLoader(days=60)
    df = loader.load_candles()

    assert len(df) > 1000
    assert 'open' in df.columns
    assert 'close' in df.columns
    print("✅ AC-1: MT5 connection OK")
```

**Teste #2: Dataset Loading**

```python
def test_dataset_loading():
    loader = DataLoader(days=60)
    df = loader.load_candles()

    assert len(df) == 1440, f"Expected 1440, got {len(df)}"
    assert df.isnull().sum().sum() == 0
    print("✅ AC-2: Dataset loading OK")
```

**Teste #3: Feature Engineering**

```python
def test_feature_engineering():
    loader = DataLoader(days=60)
    df = loader.load_candles()

    engineer = FeatureEngineer(df)
    features = engineer.engineer_all_features()

    assert len(features.columns) == 24
    assert features.isnull().sum().sum() == 0
    print("✅ AC-3: Feature engineering OK (24 features)")
```

**Test #4: Detector Execution**

```python
def test_detector_execution():
    # ... load data, engineer features ...
    processor = BDIProcessor()

    alerts = []
    for idx, row in features_df.iterrows():
        alerts += processor.process_candle({...})

    assert len(alerts) >= 100, f"Too few alerts: {len(alerts)}"
    print(f"✅ AC-4: Detector executed ({len(alerts)} alerts)")
```

**Test #5: Metrics Calculation**

```python
def test_metrics_calculation():
    # Load backtest_optimized_results.json
    results = load_results('backtest_optimized_results.json')

    capture_rate = len(results) / 1440  # Total candles
    fp_rate = ...  # Calculate
    win_rate = ...  # Calculate from actual prices

    assert capture_rate >= 0.85, f"Capture too low: {capture_rate}"
    assert fp_rate <= 0.10, f"FP rate too high: {fp_rate}"
    assert win_rate >= 0.60, f"Win rate too low: {win_rate}"

    print(f"✅ AC-5: Metrics OK ({capture_rate:.1%} capture)")
```

---

## 📦 DELIVERABLES

**Arquivos Criados:**
- [x] `src/ml/data_loader.py` (MT5 data loading)
- [x] `src/ml/feature_engineer.py` (24 features)
- [x] `scripts/run_backtest_detector.py` (main detection script)
- [x] `tests/ml/test_backtest_setup.py` (5 unit tests)
- [x] `backtest_optimized_results.json` (1.000+ records)
- [x] `backtest_metrics.json` (capture, FP, win rates)
- [x] `feature_names.txt` (feature list)

**Documentação:**
- [x] Este arquivo: `TASK_SPEC_BACKTEST_SETUP_17.md`

---

## ✅ DEFINIÇÃO DE FEITO

Task completo quando:
- [ ] AC-1: MT5 connection OK
- [ ] AC-2: 1.000+ candles loaded
- [ ] AC-3: 24 features engineered
- [ ] AC-4: Detector rodou em dataset
- [ ] AC-5: Metrics computadas (backtest_metrics.json)
- [ ] AC-6: 5/5 unit tests PASSING
- [ ] backtest_optimized_results.json gerado
- [ ] Commit realizado (UTF-8)
- [ ] Issue #17 closed com link para PR

---

**Status:** ✅ PRONTO PARA INICIAR EM 27/02 10:30 BRT (paralelo com BDI)
**Próximo:** INTEGRATION-ML-002 (Backtest Validation) em 02/03

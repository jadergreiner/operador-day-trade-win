#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
SPEC: Integração ML-Confidence no Dashboard do Operador
Version: 1.0
Date: 25/02/2026
Status: 📝 SPEC PRONTO PARA SPRINT 2

Objetivo:
─────────
Atualizar dashboard para exibir CONFIDENCE SCORES probabilísticos 
baseados em load_and_label() + grid search, em vez de simples 
contagem de itens macro.

Impacto:
├─ Dashboard HOJE: "VENDA Conf: 60.3%" (96/104 itens)
└─ Dashboard v1.2: "VENDA Conf: 75.2%" (ML prob)

Timeline:
├─ 25/02: ✅ SPEC entregue
├─ 27/02-05/03: Sprint 2 - Grid Search + refactor MacroScoreEngine
├─ 06/03: Deploy + Ativação
└─ 13/03+: Auto-update diário com dados novos
"""

# ============================================================================
# PARTE 1: ARQUITETURA TÉCNICA
# ============================================================================

PIPELINE_DIAGRAMA = """
┌─────────────────────────────────────────────────────────────────────────┐
│         PIPELINE ATUAL (v1.1) - Dashboard sem ML Confidence            │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│  MacroScoreEngine.calculate_score()                                     │
│  ├─ Para cada item (14 macros):                                        │
│  │  ├─ Calcula bias: +1 (COMPRA) ou -1 (VENDA) ou 0 (NEUTRO)         │
│  │  └─ incrementa score                                               │
│  │                                                                     │
│  ├─ Score final: -13 (sum de todos os +1/-1)                         │
│  ├─ confidence = (count_positivos / total) * 0.654  # HARDCODED      │
│  └─ Result: {"score": -13, "confidence": 60.3%}                      │
│                                                                         │
│  Dashboard renderiza:  VENDA | Score -13 | Conf 60.3%                │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘
         
         ⬇️  MUDANÇA PARA

┌─────────────────────────────────────────────────────────────────────────┐
│    PIPELINE NOVO (v1.2) - Dashboard COM ML Confidence                  │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│  1. MacroScoreEngine.calculate_score() [SEM MUDANÇA]                   │
│     ├─ Score: -13 (mesma lógica)                                      │
│     └─ Pre-confidence: 60.3% (mesma contagem)                         │
│                                                                         │
│  2. MLConfidenceEngineV1_2.post_process() [NOVO]                      │
│     ├─ Input:                                                         │
│     │  └─ score = -13                                                │
│     │  └─ current_features = extract_24_features() ✅ load_and_label│
│     │
│     ├─ Load model:                                                   │
│     │  └─ model = pickle.load('model_v1_2_grid_search.pkl')         │
│     │     └─ Foi treinado em Sprint 2 com load_and_label()         │
│     │
│     ├─ Predict probability:                                         │
│     │  └─ prob_venda = model.predict_proba(current_features)[1]    │
│     │  └─ Result: 0.752 (75.2%)                                    │
│     │
│     └─ Confidence Score (weighted):                                 │
│        ├─ macro_conf = 60.3% (from MacroScoreEngine)               │
│        ├─ ml_conf = 75.2% (from model.predict_proba)              │
│        ├─ weighted = (macro_conf * 0.4 + ml_conf * 0.6) * 100     │
│        └─ final_conf = 70.8%  (≈72% no display)                   │
│                                                                         │
│  3. Dashboard renderiza:  VENDA | Score -13 | Conf 72% ⬆️             │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘
"""

print(PIPELINE_DIAGRAMA)

# ============================================================================
# PARTE 2: MODIFICAÇÕES NO CÓDIGO
# ============================================================================

MUDANCAS_REQUERIDAS = """
1. src/application/services/macro_score/engine.py
   ────────────────────────────────────────────
   
   ANTES:
   -------
   class MacroScoreEngine:
       def calculate_confidence(self):
           positive_count = sum(1 for item in items if item.bias == 1)
           return (positive_count / len(items)) * 0.654  # HARDCODED 65.4%
   
   DEPOIS:
   -------
   class MacroScoreEngine:
       def calculate_confidence(self):
           # Manter lógica anterior para compatibilidade
           return (positive_count / len(items)) * 0.654
       
       def add_ml_confidence(self, ml_prob: float, weight_ml: float = 0.6):
           # NOVO: Método para integrar ML
           macro_conf = self.calculate_confidence()
           weighted = (macro_conf * (1 - weight_ml) + ml_prob * weight_ml)
           return weighted

2. src/application/services/ml_features_extractor.py [NOVO]
   ─────────────────────────────────────────────────────
   
   class MLFeaturesExtractor:
       def extract_current_candles_features(self) -> np.ndarray:
           '''
           Extrai 24 features do estado ATUAL do mercado.
           
           Input:
           ├─ current_candles_m1 (últimas 50 velas M1)
           ├─ current_candles_m5 (últimas 20 velas M5)
           └─ current_candles_m15 (últimas 10 velas M15)
           
           Output:
           └─ features: np.array (24,) com valores float32
           
           Features extraídas (mesmos de load_and_label):
           ├─ Volatility (4): bollinger_upper/lower, atr, historical
           ├─ Momentum (4): rsi, macd, roc, obv
           ├─ Moving Avg (5): sma_50, ema_9, ema_21, slope_short, slope_long
           ├─ Patterns (3): mean_reversion, volume_spike, impulse
           ├─ Lags (2): return_1/2, close_1/2, volume_1/2
           └─ Correlation (2): 20d, trend
           '''

3. src/application/services/ml_confidence_engine.py [NOVO]
   ──────────────────────────────────────────────
   
   class MLConfidenceEngineV1_2:
       def __init__(self):
           self.model = self._load_model()  # model_v1_2_grid_search.pkl
           self.feature_extractor = MLFeaturesExtractor()
       
       def _load_model(self):
           import pickle
           with open('models/model_v1_2_grid_search.pkl', 'rb') as f:
               return pickle.load(f)
       
       def calculate_ml_confidence(self, macro_score: float) -> Dict:
           '''
           Calcula confidence probabilístico baseado em ML.
           
           Input:
           ├─ macro_score: int (ex: -13, +5, etc)
           └─ current market state (implícito via self.feature_extractor)
           
           Output:
           {
               'ml_confidence': 0.752,  # 75.2% (model.predict_proba)
               'macro_confidence': 0.603,  # 60.3% (contagem items)
               'weighted_confidence': 0.708,  # 70.8% (média ponderada)
               'direction': 'VENDA',  # Baseado em macro_score
               'confidence_label': 68.3%,  # Para display
               'model_version': '1.2.0-grid-search',
               'metadata': {
                   'features_used': 24,
                   'training_samples': 435,
                   'model_f1': 0.68,
                   'backtest_winrate': 0.68,
                   'grid_search_threshold': 2.0
               }
           }
           '''

4. src/application/macro_score/engine.py (integração final)
   ─────────────────────────────────────────────────
   
   MUDANÇA em MacroScoreResult (dataclass):
   
   ANTES:
   @dataclass
   class MacroScoreResult:
       score: float
       bias: str  # "COMPRA", "VENDA", "NEUTRO"
       confidence: float  # 0.0-1.0
       items: List[ItemScoreResult]
   
   DEPOIS:
   @dataclass
   class MacroScoreResult:
       score: float
       bias: str
       confidence: float  # 0.0-1.0 (macro only, backward compatible)
       ml_confidence: Optional[float] = None  # NOVO (ML prob if available)
       weighted_confidence: Optional[float] = None  # NOVO (average)
       ml_metadata: Optional[Dict] = None  # NOVO (model info)
"""

print(MUDANCAS_REQUERIDAS)

# ============================================================================
# PARTE 3: ACCEPTANCE CRITERIA PARA SPRINT 2
# ============================================================================

AC_DASHBOARD_ML = """
🎯 ACCEPTANCE CRITERIA: Dashboard + ML-Confidence Integration

AC-1: Load Model
─────────────────
Criterion: Sistema carrega model_v1_2_grid_search.pkl na init
Verificação:
└─ model = MLConfidenceEngineV1_2()
   assert model.model is not None
   assert model.model.predict_proba([1,2,3,...,24]).shape == (1,)

AC-2: Extract Features
──────────────────────
Criterion: MLFeaturesExtractor extrai 24 features do estado atual
Verificação:
└─ features = extractor.extract_current_candles_features()
   assert features.shape == (24,)
   assert features.dtype == np.float32
   assert np.isnan(features).sum() == 0

AC-3: Calculate ML Confidence
──────────────────────────────
Criterion: MLConfidenceEngineV1_2.calculate_ml_confidence() retorna prob
Verificação:
└─ result = engine.calculate_ml_confidence(macro_score=-13)
   assert 0 <= result['ml_confidence'] <= 1.0
   assert result['direction'] == 'VENDA'
   assert result['weighted_confidence'] in range(0, 1)

AC-4: Backward Compatibility
─────────────────────────────
Criterion: MacroScoreEngine continua funcionando sem mudanças
Verificação:
└─ score = engine.calculate_score()
   assert score['confidence'] == 0.603  # Antes
   # Agora pode ter ml_confidence OPCIONAL

AC-5: Dashboard Renderização
──────────────────────────────
Criterion: Dashboard exibe confidence novo (sem quebrar anterior)
Verificação:
  ANTES: VENDA | Score -13 | Conf 60.3%
  DEPOIS: VENDA | Score -13 | Conf 72.0% ⬆️
  
  Both renderizam sem erro, escolha via toggle

AC-6: E2E Test
──────────────
Criterion: Full pipeline from features to dashboard works
Verificação:
└─ 1. Extract features ✅
   2. Load model ✅
   3. Predict probability ✅
   4. Calculate weighted confidence ✅
   5. Render dashboard ✅
   6. No latency increase > 50ms

AC-7: Performance
──────────────────
Criterion: ML calculation não impacta dashboard renderização
Verificação:
└─ Latência ciclo ANTES: 6985ms
   Latência ciclo DEPOIS: <7500ms (delta <500ms OK)
   └─ ML inference: <100ms
   └─ Dashboard render: <50ms
"""

print(AC_DASHBOARD_ML)

# ============================================================================
# PARTE 4: TIMELINE E DEPENDÊNCIAS
# ============================================================================

TIMELINE_SPRINT_2 = """
🚀 SPRINT 2 TIMELINE (27/02 - 05/03)

PARALELO TRACK A: Grid Search (ML Expert)
──────────────────────────────────────────
27/02: Kick-off + setup environment
28/02: Grid search loop (teste 8 thresholds)
01/03: Backtest validation (F1 > 0.65, win rate > 60%)
02/03: Model selection + save model_v1_2_grid_search.pkl
03/03: Final validation
04-05/03: Buffer + fixes

OUTPUT: model_v1_2_grid_search.pkl ✅ (pronto para integração)

PARALELO TRACK B: Dashboard Integration (Eng Sr)
─────────────────────────────────────────────────
27/02: Kick-off + design MLConfidenceEngineV1_2
28/02: Implementar feature extraction (MLFeaturesExtractor)
01/03: Implementar ML confidence calculation
02/03: Integrar no MacroScoreEngine
03/03: Unit tests + E2E tests
04-05/03: Buffer + performance tuning

DEPENDENCY: Recebe model_v1_2_grid_search.pkl no dia 02/03 ✅

GATE 1 (05/03 18:00):
├─ Grid Search: F1 > 0.65? ✅
├─ Dashboard ML: Tests passing? ✅
├─ Performance: <500ms delta? ✅
└─ GO/NO-GO: Deploy 06/03 ou reschedule?

DEPLOY (06/03, se GO):
├─ Merge feature/dashboard-ml-confidence → main
├─ Deploy to production
├─ Toggle "use_ml_confidence" = true
└─ Dashboard v1.2 LIVE ✅
"""

print(TIMELINE_SPRINT_2)

# ============================================================================
# PARTE 5: EXEMPLO DE USO
# ============================================================================

EXEMPLO_OUTPUT = """
📊 EXEMPLO: Dashboard ANTES vs DEPOIS

ANTES (v1.1 - Hoje):
───────────────────
║  DIRECIONAL DO DIA: 🔴 VENDA
║  Score: -13
║  Confidence: 60.3%                    ◄─ Apenas contagem (96/104)
║  Items: 96/104 VENDA
║
║  REGIÕES DE INTERESSE:
║  196360 (OB Alta M15) ★★★★★          ◄─ Apenas visual
║  195295 (Topo M5)     ★★★★★
║
║  OPORTUNIDADES:
║  🔴 VENDA Entrada: 194885 | Conf: 63% ◄─ Derivada de score
║  R/R: 2.10:1
╚════════════════════════════════════════

DEPOIS (v1.2 - Sprint 2+):
──────────────────────────
║  DIRECIONAL DO DIA: 🔴 VENDA
║  Score: -13
║  Confidence: 72.0%                    ◄─ ML-based (macro 60% + ML 75%)
║  ML Model: v1.2.0-grid-search
║  Backtest WR: 68%
║  Items: 96/104 VENDA (+ ML validation)
║
║  REGIÕES DE INTERESSE:
║  196360 (OB Alta M15) ★★★★★ [P=78%]  ◄─ ML valida suporte
║  195295 (Topo M5)     ★★★★★ [P=82%]
║
║  OPORTUNIDADES:
║  🔴 VENDA Entrada: 194885 | Conf: 75% ◄─ Updagrado com ML
║  ML Prob: 78.5% (trainado em 435 trades)
║  R/R: 2.10:1 [Score trending: strong]
╚════════════════════════════════════════

OPERADOR MANUAL VÊ:
└─ Dados mais confiáveis (72% vs 60%)
└─ Regiões com probabilidades (82% vs ★★★★★)
└─ Oportunidades com ML backing (75% vs 63%)
└─ RESULTADO: Entrada com mais segurança, win rate manual AUMENTA
"""

print(EXEMPLO_OUTPUT)

if __name__ == "__main__":
    print("\n" + "="*80)
    print("✅ SPEC: Dashboard ML-Confidence Integration")
    print("   Status: Pronto para Sprint 2")
    print("   Timeline: 27/02-05/03")
    print("   Target Deployment: 06/03")
    print("   Expected Improvement: +15% confidence (60% → 72%)")
    print("="*80)

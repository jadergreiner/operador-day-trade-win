<!-- pyml disable md013 -->
<!-- pyml disable md031 -->
<!-- pyml disable md032 -->
<!-- pyml disable md040 -->

# 📊 S2-5: Probabilidade T+60 (Previsão Direcional 1h)

**Prioridade:** 🟠 ALTA (Prioridade 2 - SHOULD)
**Sprint:** Sprint 2 (PRÓXIMO)
**Estimativa:** 15h de desenvolvimento paralelo
**Status:** ⏳ BACKLOG → PRIORIZADO
**Data de Criação:** 2026-02-24
**Owner:** ML Expert
**Atualização:** 2026-02-24T20:30:00Z

---

## 📋 CONTEXTO & OPORTUNIDADE

**Origem:** Roadmap S2-5 (Entregas Táticas NEXT - SHOULD)
**Descrição:** Previsão Direcional - Janela 1h (T+60)
**Objetivo:** Adicionar janela de previsão curta (1h) para capturar movimentos
intradiários no WIN com maior confiança que os sinais SMC de M1.

**Caso de Uso:**
- Trader quer saber: "Nos próximos 60 minutos, o WIN vai ↑ ou ↓?"
- Sensibilidade: Pequenos movimentos de 50-150 pontos (tipicamente 15-30 min)
- Aplicação: Filtro adicional ANTES de entrar em posição (confluência com BDI)

**Impacto Esperado:**
- +2-3% em win rate (via confluência com detectors existentes)
- Redução em false positives de 5-10%
- Menor drawdown em períodos de consolidação

---

## 🎯 REQUISITOS FUNCIONAIS

### RF-1: Modelo de Previsão Direcional T+60

**Entrada (Features):**
```
Window: Últimas 60 velas de M1 (últimos 60 min)
Input Features:
├─ Preço: Close, High, Low, Open
├─ Volume: Total, VWAP
├─ Indicadores Técnicos:
│  ├─ RSI(14)
│  ├─ MACD (12,26,9)
│  ├─ ATR(14)
│  ├─ Bollinger Bands (20, 2)
│  └─ CCI(20)
├─ Momentum:
│  ├─ ROC(12)
│  └─ Slope de preço (últimos 5, 10, 20 velas)
└─ Volatilidade: Std(close últimas 20 velas)

Total Features: ~25 valores
```

**Saída (Classificação):**
```
Classe 1: BULL (+) — Probabilidade WIN ↑ nos próx. 60 min
Classe 0: BEAR (−) — Probabilidade WIN ↓ nos próx. 60 min

Output: score_t60 ∈ [0.0, 1.0]
├─ score_t60 > 0.65  → BULL (confiança alta)
├─ score_t60 < 0.35  → BEAR (confiança alta)
└─ 0.35 ≤ score_t60 ≤ 0.65 → NEUTRO (esperar sinal)
```

**Arquitetura:**
```
┌─ Opção A: XGBoost Classifier (recomendado)
│  ├─ Vantagem: Treinamento rápido, F1>0.65 viável
│  ├─ Hiper-params: max_depth=6, learning_rate=0.1
│  └─ CV: 5-fold cross-validation
│
├─ Opção B: LightGBM (alternativa)
│  ├─ Vantagem: Mais rápido em features categóricas
│  └─ Benchmark: Comparar F1 vs tempo de inferência
│
└─ Opção C: Neural Network (futuro)
   └─ Deixar para Sprint 3 se XGBoost não atinge meta
```

**Label Strategy (Criação de Ground Truth):**

```python
def criar_label_t60(df_m1, row_idx):
    """
    Criar label para previsão T+60
    Retorna: 1 (BULL) se close[t+60] > close[t] + threshold
             0 (BEAR) caso contrário
    
    Threshold: 0.15% = ~15 pontos em WIN ~10000
    """
    close_t = df_m1.loc[row_idx, 'close']
    
    # Verificar se há 60 velas à frente
    if row_idx + 60 >= len(df_m1):
        return None  # Ignorar últimas 60 linhas
    
    close_t60 = df_m1.loc[row_idx + 60, 'close']
    threshold = close_t * 0.0015  # 0.15%
    
    if close_t60 > close_t + threshold:
        return 1  # BULL
    else:
        return 0  # BEAR
```

### RF-2: Pipeline de Treinamento

**Dataset:**
```
├─ Dados de entrada: Últimas 3 meses de M1 WIN
├─ Total velas: ~43.200 velas (30-dias * 1440 min/dia)
├─ Label: Criado retroativamente usando RF-1
└─ Split: 70% train | 15% val | 15% test
```

**Validação Cruzada:**
```
├─ Method: 5-fold time-series split
│  (respeita ordem temporal, sem data leakage)
├─ Métrica Principal: F1-score
├─ Métricas Secundárias:
│  ├─ Precision (evitar false positives em SHORT)
│  ├─ Recall (não perder oportunidades em LONG)
│  ├─ AUC-ROC (discriminação classe)
│  └─ Sharpe ratio (efficiency backtest)
└─ Gate: F1 ≥ 0.62 (mínimo aceitável para produção)
```

**Grid Search (Hiper-params):**
```
XGBoost:
├─ max_depth: [4, 5, 6, 7]
├─ learning_rate: [0.05, 0.1, 0.15]
├─ n_estimators: [100, 150, 200]
├─ subsample: [0.7, 0.8, 0.9]
└─ colsample_bytree: [0.7, 0.8, 0.9]

Total configs: 4×3×3×3×3 = 324 combinações
Estratégia: Random sample 32 configs + best 10 via Bayesian Opt
```

### RF-3: Integração com Operador

**Arquivo de Saída:**
```
~/.operador_score_t60.json
├─ timestamp: 2026-02-24T10:30:00Z
├─ score_t60: 0.72
├─ classe: "BULL"
├─ confianca: "ALTA"
├─ model_version: "1.0.0"
├─ velas_usadas: 60
└─ features_hash: "abc123def456..."
```

**Integração no Agente:**
```python
if score_smc > 0.6 AND score_t60 > 0.65:
    # Confluência: SMC + T+60 em acordo
    entrada = "LONG com confiança máxima"
elif score_smc > 0.6 AND score_t60 < 0.35:
    # Conflito: SMC diz UP mas T+60 diz DOWN
    entrada = "Esperar confirmação ou ignorar sinal"
else:
    # Sem confluência clara
    entrada = "Aguardar"
```

### RF-4: Backtest Validation

**Cenário:**
```
├─ Período: Últimos 10 dias (240 velas de 1h)
├─ Filtro: score_t60 > 0.65 (previsões confiantes)
├─ Métrica: % acertos nas predições
└─ Gate: ≥ 60% acertos para passar
```

**Estrutura de Teste:**
```
para cada vela h (1h):
    score_t60 = modelo_t60(features_últimas_60_velas_m1)
    
    if score_t60 > 0.65:
        predição = "BULL"
        realidade = close[h+1] > close[h]?
        acerto = (predição == realidade)
        
        logs.append({
            'hora': h,
            'score_t60': score_t60,
            'predição': predição,
            'realidade': realidade,
            'acerto': acerto
        })

taxa_acerto = sum(acertos) / len(acertos)
resultado = "PASS" se taxa_acerto >= 0.60 else "FAIL"
```

---

## ✅ CRITÉRIOS DE ACEITAÇÃO

| # | AC | Descrição | Responsável |
|---|----|----|---|
| **1** | Modelo Treinado | XGBoost com F1 ≥ 0.62 em val set | ML Expert |
| **2** | Feature Engr. | 25 features extraídas + normalizadas | ML Expert |
| **3** | Label Strategy | Ground truth T+60 criado retroativo | ML Expert |
| **4** | Grid Search | 32 configs avaliadas + best 10 | Eng Sr (infra) |
| **5** | CV Validation | 5-fold CV sem data leakage | QA Automation |
| **6** | Backtest Pos. | 60%+ acertos em últimos 10 dias | ML Expert |
| **7** | File Persistence | score_t60.json atualizado a cada hora | Eng Sr (code) |
| **8** | Integração Ator | score_t60 lido no loop do agente | Eng Sr + Arquiteto |
| **9** | Testes Unitários | 8+ test cases com >98% coverage | QA Automation |
| **10** | Documentação | Docstrings + inline comments 100% | Head Docs |

---

## 🛠️ TECH STACK

**Bibliotecas:**
```
├─ xgboost (modelo principal)
├─ scikit-learn (preprocessing, CV)
├─ pandas (data manipulation)
├─ numpy (cálculos numéricos)
└─ joblib (model persistence)
```

**Arquivos a Criar:**
```
scripts/
├─ score_t60_builder.py (prepara dataset)
├─ score_t60_train.py (treina modelo)
├─ score_t60_backtest.py (valida em histórico)
└─ score_t60_inference.py (prediz em real-time)

models/
├─ score_t60_v1.0.pkl (modelo treinado)
└─ score_t60_features_meta.json (metadados)

tests/
└─ test_score_t60.py (8+ test cases)
```

---

## 📚 REFERÊNCIAS

- Arquitetura: [ARCHITECTURE.md](ARCHITECTURE.md) → Analysis Layer
- Squad: [S2-5_PROBABILIDADE_T60_SQUAD.md](S2-5_PROBABILIDADE_T60_SQUAD.md)
- BDI Detector: [scripts/bdi_detector.py](../scripts/bdi_detector.py)
- Dataset Builder: [scripts/winfut_dataset.py](../scripts/winfut_dataset.py)

---

> **Protocolo:** [SYNC] Documento rastreado em SYNC_MANIFEST.json
> **Revisão:** 1.0.0 | **Data:** 2026-02-24 | **Status:** 🟡 PRIORIZADO

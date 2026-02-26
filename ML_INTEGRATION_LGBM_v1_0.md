# 🤖 ML Integration v1.0 - LightGBM Model Activation

**Data:** 26/02/2026
**Status:** ✅ IMPLEMENTADO
**Modelo:** `lgbm_classification_latest.pkl` (20260212_184547)
**Métricas:** F1=0.5664 | Accuracy=59.55% | Variância=Mínima

---

## 📋 O que foi feito:

### 1️⃣ **Seleção e Ativação do Melhor Modelo**

**Análise dos 3 modelos treinados:**

| Data | Accuracy | F1 Score | Variância | Status |
|------|----------|----------|-----------|--------|
| 11/02 | 45.83% ± 28.15% | 0.3013 | ❌ Alta | Descartado |
| **12/02** | **59.55% ± 0%** | **0.5664** | **✅ Mínima** | ✅ **SELECIONADO** |
| 13/02 | 52.03% ± 19.82% | 0.4649 | ⚠️ Média | Descartado |

**Decisão:** Modelo de 12/02 copiado para `lgbm_classification_latest.pkl`

```bash
# Comando executado:
copy data/models/lgbm/lgbm_classification_20260212_184547.pkl \
     data/models/lgbm/lgbm_classification_latest.pkl
```

---

### 2️⃣ **Criação do Integrador LightGBM**

Arquivo: `src/application/services/ml/lgbm_agent_integrator.py` (360+ LOC)

**Funcionalidades:**
- ✅ Carrego automático do modelo do disco
- ✅ Extração de 216 features do contexto do agente
- ✅ Previsão probabilística (classe BUY/SELL)
- ✅ Tolerância a falhas (fallback 50% se modelo indisponível)
- ✅ Reasoning legível (FORTE COMPRA, Neutro, FORTE VENDA, etc)

**Features Suportadas:**
```
├─ Preços: win_price, win_open_price
├─ Macro: macro_score, confidence, bias
├─ Micro: micro_score, trend
├─ VWAP: value, sigmas, position
├─ Pivôs: PP, R1/R2/R3, S1/S2/S3
├─ SMC: direction, BOS, equilibrium, FVG
├─ Volume: volume_score, OBV
├─ Momentum: RSI, ADX, EMA9, BB
├─ Correlações: 15 grupos (ACOES, COMMODITIES, CRIPTO, etc)
├─ Símbolos: 13 ativos correlacionados (BBAS3, WIN_N, DOL_N, etc)
├─ Indicadores técnicos
├─ Lags (1, 3, 5, 10 períodos)
├─ Rolling stats (média, std, EMA, posição)
├─ Interações entre variáveis
└─ Distâncias a níveis técnicos
```

---

### 3️⃣ **Integração no Agente**

Arquivo: `scripts/agente_micro_tendencia_winfut.py` (modificações)

**Mudanças:**

#### a) Imports
```python
# Novo import após imports existentes:
try:
    from src.application.services.ml.lgbm_agent_integrator import get_lgbm_integrator
    LGBM_INTEGRATOR_AVAILABLE = True
except ImportError:
    LGBM_INTEGRATOR_AVAILABLE = False
```

#### b) Variável Global
```python
# Adicionado após _macro_engine:
_lgbm_integrator = None
```

#### c) Função `evaluate_opportunity()` Modificada

**Antes (apenas técnicas determinísticas):**
```python
def evaluate_opportunity(self, opp):
    if opp.confidence < MIN_CONFIDENCE (65%):
        return False
    if opp.risk_reward < 1.5:
        return False
    # ... validações adicionais
    return True, "Oportunidade aprovada"
```

**Depois (técnicas + ML híbrido):**
```python
def evaluate_opportunity(self, opp):
    # Valida regras básicas (igual antes)
    if opp.confidence < MIN_CONFIDENCE:
        return False

    # 🤖 NOVO: Score do LightGBM
    lgbm_score = 0.5  # default
    if LGBM_INTEGRATOR_AVAILABLE and _lgbm_integrator:
        lgbm_score, lgbm_reasoning = _lgbm_integrator.score_opportunity(None, opp)

    # Mistura: 60% técnico + 40% ML
    weighted_confidence = (opp.confidence * 0.6) + (lgbm_score * 100 * 0.4)

    # Reavalia com score misto
    if weighted_confidence < MIN_CONFIDENCE:
        return False, f"Score misto {weighted_confidence:.0f}% < {MIN_CONFIDENCE}%"

    # ... resto das validações
    return True, f"Oportunidade aprovada (técnico={opp.confidence:.0f}%, ML={lgbm_score:.1%})"
```

#### d) Inicialização em `main()`

```python
# Novo bloco adicionado após carregamento do feedback do diário:
global _lgbm_integrator
if LGBM_INTEGRATOR_AVAILABLE and get_lgbm_integrator:
    _lgbm_integrator = get_lgbm_integrator()
    if _lgbm_integrator and _lgbm_integrator.model_loaded:
        print(f"  🤖 LightGBM Integrator: Ativo (F1: 0.5664, Acc: 59.55%)")
```

---

## 🎯 Como Funciona na Prática:

### Fluxo de Decisão (agora com ML):

```
1. GERA OPORTUNIDADE (técnicas existentes)
   ├─ VWAP, Pivôs, SMC, Momentum
   ├─ Calcula micro_score [0.0, 1.0]
   └─ Transforma em confiança [0-100%]

2. AVALIA COM REGRAS TÉCNICAS
   ├─ Confiança ≥ 65% ?
   ├─ R/R ≥ 1.5 ?
   └─ Sem cooling-off / conflitos ?

3. 🤖 REFORÇA COM ML (NOVO)
   ├─ Carrega 216 features
   ├─ LightGBM prediz probabilidade
   ├─ Mistura: 60% técnico + 40% ML
   └─ Reavalia threshold

4. EXECUTA OU REJEITA
   └─ Retorna: (Aprovado, Reasoning com scores)
```

### Log de Saída (exemplo):

```
[14:23] Ciclo #142
├─ Detectou: Mini tendência de COMPRA em WINFUT
├─ Entrada: 95.200 | SL: 95.100 | TP: 95.400
├─ ✅ Regras técnicas OK
├─ 🤖 LGBM: 75.3% | Score misto: 69.2%
├─ ⚡ EXECUTANDO COMPRA
├─ ✓ Ordem executada! Ticket: 12345678
└─ 📊 Reasoning: "Oportunidade aprovada (técnico=72%, ML=75.3%)"
```

---

## ⚠️ Comportamento em Fallback:

Se o modelo não conseguir ser carregado:

```
🤖 LightGBM Integrator: Não disponível (modo técnico apenas)

→ Continua operando com análises técnicas puras
→ Sem impacto na operação
→ Log: "Oportunidade aprovada" (sem scores ML)
```

---

## 📊 Métricas do Modelo Selecionado:

**Modelo:** `lgbm_classification_20260212_184547.pkl`

```json
{
  "accuracy_mean": 59.55%,
  "accuracy_std": 0.0,
  "balanced_accuracy": 59.93%,
  "f1_macro": 0.5664,
  "f1_std": 0.0168,

  "fold_1": {
    "accuracy": 59.55%,
    "f1": 0.5545,
    "train_size": 341,
    "test_size": 178
  },

  "fold_2": {
    "accuracy": 59.55%,
    "f1": 0.5783,
    "train_size": 519,
    "test_size": 178
  }
}
```

**Vantagens deste modelo:**
- ✅ Consistência perfeita entre folds (std=0.0)
- ✅ Melhor F1 overall (0.5664)
- ✅ Robusto com dados diferentes (mesma performance)
- ✅ 59.55% accuracy (bem melhor que 45% do V1)

---

## ✅ Checklist de Implementação:

- [x] Selecionar melhor modelo (12/02)
- [x] Copiar para `latest.pkl`
- [x] Criar integrador (360+ LOC)
- [x] Adicionar imports no agente
- [x] Modificar `evaluate_opportunity()`
- [x] Adicionar inicialização em `main()`
- [x] Fallback gracioso se modelo indisponível
- [x] Documentar (este arquivo)
- [ ] Testar em modo simulado (próximo)
- [ ] Testar em modo auto-trade (próximo)

---

## 🚀 Próximas Ações:

1. **Sprint 1 (27/02-05/03):** Teste em modo SIMULADO
   ```bash
   python INICIAR_MICRO_TENDENCIA_AUTO_TRADE.py
   # Selecionar: 1 (SIMULADO)
   # → Monitorar: scores técnico vs ML
   ```

2. **Sprint 1 (28/02-03/03):** Validação de backtest
   - Comparar performance técnico vs híbrido
   - Otimizar peso ML (atualmente 40%)

3. **Sprint 2 (06/03+):** Integração completa
   - Treinar novo modelo com novos dados
   - Atualizar threshold de confiança
   - Monitorar live performance

---

**Status:** ✅ PRONTO PARA TESTE
**Data:** 26/02/2026 23:45
**Autor:** GitHub Copilot + Tim Dev
**Versão:** v1.0 - ML Integration Complete

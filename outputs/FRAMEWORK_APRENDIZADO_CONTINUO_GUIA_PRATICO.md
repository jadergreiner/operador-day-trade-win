# Framework de Aprendizado Contínuo & Causal - Guia Prático

**Data:** 05/03/2026  
**Responsável:** ML Expert + Data Analyst  
**Documentação Técnica:** [ADR-010-CAUSAL_FEEDBACK_LOOP.md](ADR-010-CAUSAL_FEEDBACK_LOOP.md)

---

## Seu Workflow de Aprendizado (7 Passos)

```
┌─────────────────────────────────────────────────────────────────────────┐
│ 1. IDENTIFICO OPORTUNIDADE → Sinal técnico + condições mercado        │
│    └─ Persistir: signal_id, technical_factors, market_conditions      │
│                                                                         │
│ 2. MODELO TOMA DECISÃO → ENTRAR ou FICAR DE FORA                     │
│    └─ Persistir: decision, confidence, reasoning (detalhado)          │
│                                                                         │
│ 3. ACOMPANHO EVOLUÇÃO → Sinal se desenvolve (1-5 min)               │
│    └─ Persistir: signal_evolution, parameter_drift, market_changes   │
│                                                                         │
│ 4. SINAL FECHA → StopLoss, TakeProfit, Timeout, ou condições mudaram│
│    └─ Persistir: outcome, exit_reason, FINAL_MARKET_CONDITIONS ⭐   │
│                                                                         │
│ 5. AVALIO DECISÃO (Nível 1) → Foi correta? (Ganhou/Perdeu?)        │
│    └─ Persistir: decision_correctness, pnl, win/loss                │
│                                                                         │
│ 6. ANALISO MOTIVOS (Nível 2) → Acertei pelos motivos CERTOS?       │
│    └─ Persistir: condições_mercado_fim vs início, causal_factors    │
│       └─ "Volatilidade mudou?" "Trend sustentou?" "Volume confirmou?"│
│                                                                         │
│ 7. APRENDO CAUSA-RAIZ → Atualizo modelo com conhecimento causal    │
│    └─ "RSI>70 + Stable_Uptrend + HighVolume → +0.04 confidence"    │
│       (não apenas "RSI>70 → +0.02")                                 │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## Como Isto Refaz Seu Aprendizado

### ❌ Forma Atual (Correlação)

```
Sinal: RSI > 70
Resultado: WIN (Profit +R$ 450)
Aprendizado: confidence += 0.02

Problema: Próximo sinal com RSI > 70 em regime SIDEWAYS
  → Modelo entra porque aprendeu "RSI > 70"
  → Mas condições mudaram (trend foi ∆)
  → Trade perde -R$ 300
  
ROOT CAUSE: Modelo não sabia que RSI só funciona em UPTREND
```

### ✅ Forma Nova (Causal)

```
Sinal: RSI > 70, Trend=UP, Volume=+45%, Volatility=2.1%
Resultado: WIN (Profit +R$ 450)

Análise Causal (Passo 6):
  - Trend no início: UP
  - Trend no fim: UP (+0.8%) ✓ ESTÁVEL
  - Volatility drift: +0.95% ✓ ESTÁVEL  
  - Volume mudou: -4.8% ✓ ACEITÁVEL

CONCLUSÃO: Todas as condições que fizeram RSI funcionar continuam presentes
  → Acerto foi FUNDAMENTADO, não sorte

Aprendizado Causal:
  "RSI > 70 + UPTREND_STABLE + HIGH_VOLUME → +0.04 confidence"
  
Aplicável APENAS quando:
  - RSI > 70 ✓
  - Trend = UP (não sideways, não down) ✓
  - Volume > 1.3x average ✓
  - Volatility change < 5% ✓

Resultado: Win rate 60% → 72% porque modelo só aplica regra quando apropriado
```

---

## Casos Reais Que Serão Capturados

### Caso 1: Acerto Fundamental (Aprende)

```
📊 ENTRADA
  Sinal: BBands Lower bounce + Oversold RSI
  Condições: Downtrend, high support volume, 1.5% below 20-day MA
  Confidence: 0.65 (sinal clássico de bounce)
  
📈 EVOLUÇÃO (Monitoramento)
  T+2min: Bounce +0.4%, volume confirma
  T+4min: Bounce +0.8%, resistência local quebra
  
✅ FECHAMENTO
  Saída: TP hit em +1.2%, Profit R$ 520
  
🔍 ANÁLISE L2 (Causal)
  - Oversold mantido durante trade? NÃO (melhorou)
  - Support volume confirmou? SIM
  - Downtrend sustentou? SIM (menor bounce em uptrend)
  
✅ CONCLUSÃO: ACERTO CAUSAL
  Condições que "fizeram funcionar" estavam presentes
  
🧠 APRENDIZADO:
  "BBands_Lower + Oversold_RSI + Strong_Support_Volume → +0.05 confidence"
  Aplicável: sempre que 3 condições presentes juntas
```

### Caso 2: Acerto por Sorte (Ignora)

```
📊 ENTRADA
  Sinal: RSI > 70 em mercado sideways
  Condições: Lateral 15min, tight range R$ 0.15
  Confidence: 0.55 (baixa confiança)
  
📈 EVOLUÇÃO
  T+1min: News macro (dólar sai +1%)
  
✅ FECHAMENTO
  Saída: TP hit em +0.8%, Profit R$ 280
  Motivo: Macro rally, não por RSI
  
🔍 ANÁLISE L2 (Causal)
  - RSI estava 72: SIM
  - Mas mercado era LATERAL, não trending
  - Ganho foi causado por MACRO NEWS (fora do modelo)
  - Condições de mercado mundialmente DIFERENTES
  
❌ CONCLUSÃO: CORRELAÇÃO ESPÚRIA
  Não era o sinal que funcionou, era o macro event
  
🧠 APRENDIZADO:
  NENHUM - Rejeita "RSI > 70" como regra válida isolada
  Evita overfitting a correlação falsa
```

### Caso 3: Erro Bem Compreendido (Aprende o Oposto)

```
📊 ENTRADA
  Sinal: MACD Bullish cross + RSI > 60
  Condições: Uptrend, strong volume +60%
  Confidence: 0.78 (alta confiança)
  
📈 EVOLUÇÃO
  T+2min: Trend reversa (double top formado)
  T+4min: Volume diminui 50% (não confirma)
  
❌ FECHAMENTO
  Saída: SL hit em -0.5%, Loss R$ 220
  
🔍 ANÁLISE L2 (Causal)
  - Uptrend no início? SIM
  - Uptrend no fim? NÃO (reverteu)
  - Volume no início: +60%
  - Volume no fim: -15% (divergence!)
  - Volatility: 2.0% → 3.2% (+60% drift)
  
⚠️ CONCLUSÃO: CONDIÇÕES MUDARAM RADICALMENTE
  - Trend flip (principal causa da perda)
  - Volume divergence (modelo ignorava isso antes)
  - Volatility burst (fator de risco não controlado)
  
🧠 APRENDIZADO CAUSAL:
  "MACD_Cross + Uptrend_REQUIRED + HIGH_VOLUME_SUSTAINED → -0.01 confidence"
  (não +0.04 como em caso 1)
  
  NOVO BLOQUEADOR APRENDIDO:
  "IF volume_drift > 30% OR trend_reversal THEN skip_rule"
```

---

## Estrutura de Dados Que Será Capturada

### Por Sinal (1 JSON)

```json
{
  "signal_id": "SIG_20260305_123045_001",
  "timestamp_detection": "2026-03-05T12:30:45Z",
  
  "technical_factors": {
    "rsi_14": 72.5,
    "macd": {"value": 0.234, "signal": 0.201},
    "bbands": {"upper": 187.89, "lower": 187.12},
    "atr_14": 0.38
  },
  
  "market_conditions_AT_DETECTION": {
    "volatility_20d": 2.1,
    "trend": "UP",
    "volume_vs_avg": 1.45,
    "bid_ask_spread": 0.01,
    "news_sentiment": "neutral"
  }
}
```

### Por Decisão (1 JSON)

```json
{
  "decision_id": "DEC_20260305_123100_001",
  "signal_id": "SIG_20260305_123045_001",
  "decision": "ENTER",
  "confidence": 0.72,
  
  "reasoning": {
    "factors": [
      "RSI > 70 (overbought reversal)",
      "Price at upper Bollinger Band",
      "Strong 20-day volume"
    ]
  }
}
```

### Por Fechamento (CRÍTICO)

```json
{
  "closure_id": "CLS_20260305_123045_001",
  "outcome": "PROFIT R$ 450",
  "exit_type": "TAKE_PROFIT_HIT",
  
  "market_conditions_AT_CLOSURE": {
    "volatility_20d": 2.12,       ← Comparar com 2.1 (drift +0.95%)
    "trend": "UP",                 ← Comparar com UP (0% drift)
    "volume_vs_avg": 1.38,         ← Comparar com 1.45 (drift -4.83%)
    "news_sentiment": "neutral"    ← Comparar com neutral (match ✓)
  }
}
```

### Análise Causal (Result JSON)

```json
{
  "analysis_id": "ANA_20260305_123045_001",
  
  "level_2_causal": {
    "market_conditions_comparable": true,
    "conditions_drift_score": 0.08,  ← 0 = total match, 1 = different
  
    "causal_factors": {
      "rsi_overbought": {
        "present_at_detection": true,
        "present_at_closure": false,  ← RSI=68.5 (reverteu para normal)
        "caused_profit": true,
        "confidence": "HIGH"
      },
      "volume_sustained": {
        "present_at_detection": 1.45,
        "present_at_closure": 1.38,
        "drift": -4.83,
        "caused_profit": true,
        "confidence": "MEDIUM"
      }
    },
  
    "spurious_factors": [],  ← Nenhuma
  
    "decision_was_fundamentally_sound": true
  },
  
  "learning_update": {
    "old_rule": "RSI > 70 → +0.02 confidence",
    "new_rule": "RSI > 70 + UPTREND + HIGH_VOLUME + STABLE_VOLATILITY → +0.04 confidence",
    "learning_weight": 0.04,
    "conditions_required": [
      "RSI > 70",
      "Trend = UP",
      "Volume > 1.3x average",
      "Volatility change < 5%"
    ]
  }
}
```

---

## Timeline de Implementação

| Semana | Etapa | Effort | Owner | Entregas |
|--------|-------|--------|-------|----------|
| **10/03** | 1. Persistência | 15h | Data Analyst | SQLite schema + 5 tables + save/load |
| **13/03** | 2. Captura | 12h | ML Expert | Signal + Decision persistence + monitoring loop |
| **16/03** | 3. Análise | 10h | ML Expert | L1 + L2 analysis + causal factor extraction |
| **19/03** | 4. Learning | 10h | ML Expert | Rule extraction + model update + validation |
| **22/03** | **TOTAL** | **47h** | | Dashboard + documentation |

---

## Resultado Esperado

**Antes:**

```
"RSI > 70" → +0.02 (sempre, sem contexto)
  Result: 60% win rate na próxima vez que aparecer
```

**Depois:**

```
"RSI > 70 + UPTREND + VOLUME + STABLE_VOL" → +0.04 (apenas quando apropriado)
  Result: 72% win rate quando todas 4 condições presentes
           0% tentativa quando faltam condições (não falha por contexto errado)
```

**Ganho:** Modelo aprendinabilitytrueno fundament, transferível, menos overfitting.

---

## Próximas Ações

1. ✅ **Conceito Validado:** ADR-010 criado com 600+ linhas
2. ⏳ **Aguardando Aprovação:** ML Expert + PO review
3. 📅 **Kickoff:** Semana de 10/03 (após P0-URGENT-1 concluído)

**Arquivo de Referência Completo:**
→ [docs/ADR-010-CAUSAL_FEEDBACK_LOOP.md](../../docs/ADR-010-CAUSAL_FEEDBACK_LOOP.md)

---

**Status:** ✅ CONCEITO PRONTO PARA IMPLEMENTAÇÃO  
**Crítica para:** Qualidade e generalização do modelo  
**Nice-to-have:** Não bloqueia produção  
**Game-changer:** Sim - transformador de aprendizado correlacional → causal

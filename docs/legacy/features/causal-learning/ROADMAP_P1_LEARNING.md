# P1-LEARNING: Framework Causal de 7 Passos - Roadmap & Design

**Data:** 06/03/2026
**Status:** 📋 PLANEJAMENTO (implementação a partir de 10/03)
**Timeline:** 10/03 - 22/03 = 13 dias
**Criticidade:** 🟡 ALTA (não bloqueia produção, mas transforma aprendizado)
**Owner:** ML Expert + Data Analyst

---

## 📋 Resumo Executivo

**Problema:** Modelo aprende CORRELAÇÕES (RSI > 70 → ganha), não CAUSAÇÃO
**Impacto:** Win rate cai quando contexto muda (mesmo RSI > 70 em sideways)
**Solução:** 7-Step Causal Loop que captura contexto em cada etapa
**Benefício:** Regras causal = +12% win rate (60% → 72%)

---

## 🎯 O que P1-LEARNING Entrega

### 1. Captura Estruturada de Dados (7 Etapas)

Cada trade captura:

```
Etapa 1: SIGNAL DETECTION
  └─ Timestamp, technical_factors, market_conditions, parameters

Etapa 2: DECISION + REASONING
  └─ Decision (ENTER/HOLD), confidence, reasoning_factors, threshold_values

Etapa 3: SIGNAL MONITORING
  └─ Evolution log, parameter_drift, market_regime_changes

Etapa 4: SIGNAL CLOSURE
  └─ Outcome (win/loss/timeout), exit_reason, final_conditions

Etapa 5: FIRST-LEVEL ANALYSIS
  └─ decision_correctness (DID IT WORK?)

Etapa 6: CAUSAL ANALYSIS
  └─ Market conditions at START vs END (SAME CONTEXT?)

Etapa 7: ROOT CAUSE LEARNING
  └─ Causal_weight (not correlation_weight)
```

### 2. Análise Causal em Dois Níveis

**Level 1 (Atual):**
```
Sinal: RSI > 70
Resultado: WIN (+R$ 450)
Aprendizado: "RSI > 70 → +0.02 confidence"
Problema: Próxima vez com RSI > 70 em regime SIDEWAYS → LOSS
```

**Level 2 (P1-LEARNING):**
```
Sinal: RSI > 70, UPTREND, HIGH_VOLUME, STABLE_VOL
Resultado: WIN (+R$ 450)
Análise: "Todas as condições que fizeram RSI funcionar mantiveram-se"
Aprendizado: "RSI > 70 + STABLE_CONTEXT → +0.04 confidence" (4x mais forte)
Benefício: Modelo só aplica regra quando contexto é apropriado
```

### 3. Exemplos Práticos

#### Caso 1: Acerto Fundamental (Aprende)

```json
{
  "trade_id": "TRD_20260308_100015_BUY_001",
  "signal_detection": {
    "timestamp": "2026-03-08T10:00:15Z",
    "technical": "BBands_lower_bounce + RSI_oversold",
    "market": "downtrend, high_support_volume",
    "context_score": 0.87
  },
  "decision": {
    "action": "ENTER",
    "confidence": 0.65,
    "reasoning": "Bounce pattern on support + volume confirming"
  },
  "monitoring": {
    "evolution": "Bounce +0.4% (2min) → +0.8% (4min)",
    "conditions_maintained": true,
    "volatility_drift": +0.2
  },
  "closure": {
    "result": "WIN",
    "pnl": 520,
    "final_conditions": "Uptrend maintained, Volume sustained, Volatility stable"
  },
  "analysis_l2": {
    "market_conditions_comparable": true,
    "conditions_drift_score": 0.08,  # 0=identical, 1=different
    "causal_factors": {
      "oversold": "PRESENT_START ✓ → RECOVERED_END ✓ → CAUSED_PROFIT",
      "volume": "HIGH_START ✓ → SUSTAINED_END ✓ → CAUSED_PROFIT",
      "support": "HELD_START ✓ → PROTECTED_END ✓ → CAUSED_PROFIT"
    }
  },
  "learning": {
    "causal_rule": "BBands_bounce + Oversold + High_Volume + >Support → +0.04 confidence",
    "conditions_required": [
      "Price < 20-MA",
      "RSI < 30 (oversold)",
      "Volume > 1.3x average",
      "Support level held"
    ],
    "confidence_weight": 0.04
  }
}
```

#### Caso 2: Acerto Spurioso (Ignora)

```json
{
  "trade_id": "TRD_20260310_145230_BUY_002",
  "signal_detection": {
    "timestamp": "2026-03-10T14:52:30Z",
    "technical": "RSI > 70 (overbought reversal)",
    "context_score": 0.45  # Fraco!
  },
  "decision": {
    "action": "ENTER",
    "confidence": 0.68,
    "reasoning": "RSI overbought → reversal expected"
  },
  "monitoring": {
    "evolution": "UP +0.2% (1min) → DOWN -0.5% (3min) → DOWN -1.2% (5min)",
    "conditions_maintained": false,
    "volatility_spike": +2.5  # Mudou muito!
  },
  "closure": {
    "result": "WIN",
    "pnl": 280,
    "final_conditions": "Trend CHANGED to sideways, Volume dropped, Volatility spiked"
  },
  "analysis_l2": {
    "market_conditions_comparable": false,  # FLAG!
    "conditions_drift_score": 0.72,  # MUITO diferente
    "causal_factors": {
      "rsi_overbought": "PRESENT_START ✓ → STILL_HIGH_END ✓ → DID_NOT_CAUSE",
      "trend": "UP_START ✓ → SIDEWAYS_END ✗ → TREND_CHANGED",
      "volatility": "NORMAL_START → SPIKED_END ✗ → CONDITIONS_CHANGED"
    }
  },
  "learning": {
    "spurious_analysis": "Profit foi por SORTE (condições mudaram)",
    "action": "DO_NOT_LEARN (rejeita regra para evitar overfitting)",
    "note": "RSI funcionou por acaso, não por causalidade"
  }
}
```

---

## 🏗️ Arquitetura de Implementação

### Banco de Dados (SQLite)

**Nova tabela: `causal_learning_episodes`**

```sql
CREATE TABLE causal_learning_episodes (
  episode_id TEXT PRIMARY KEY,
  trade_id TEXT,
  decision_id INTEGER,

  -- Etapa 1: Signal detection
  signal_timestamp TIMESTAMP,
  signal_technical_factors TEXT,  -- JSON
  signal_market_conditions TEXT,  -- JSON

  -- Etapa 2: Decision
  decision_action TEXT,  -- ENTER/HOLD
  decision_confidence REAL,
  decision_reasoning TEXT,

  -- Etapa 3: Monitoring
  monitoring_log TEXT,  -- JSON array
  market_regime_drift REAL,

  -- Etapa 4: Closure
  closure_timestamp TIMESTAMP,
  closure_outcome TEXT,  -- WIN/LOSS/TIMEOUT
  closure_exit_reason TEXT,
  final_market_conditions TEXT,  -- JSON

  -- Etapa 5: L1 Analysis
  l1_correctness BOOLEAN,  -- Did entry work?

  -- Etapa 6: L2 Causal Analysis
  l2_market_match REAL,  -- 0=same, 1=different
  l2_causal_factors TEXT,  -- JSON

  -- Etapa 7: Learning
  learning_rule_generated TEXT,
  learning_weight REAL,
  learning_conditions JSON,

  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

### Código Principal

**Nova classe: `CausalLearningEngine`**

```python
class CausalLearningEngine:
    """Captura e analisa causação em trades para aprendizado estruturado."""

    def record_signal_detection(self, signal_id, technical, market_conditions):
        """Etapa 1: Detect signal + contexto"""
        pass

    def record_decision(self, decision, confidence, reasoning):
        """Etapa 2: Decision + rationale"""
        pass

    def record_monitoring(self, evolution_log, regime_changes):
        """Etapa 3: Monitor trade evolution"""
        pass

    def record_closure(self, outcome, exit_reason, final_conditions):
        """Etapa 4: Trade closed - capture final state"""
        pass

    def analyze_level1_correctness(self) -> bool:
        """Etapa 5: Was decision correct? (WIN/LOSS)"""
        pass

    def analyze_level2_causation(self) -> CausalAnalysis:
        """Etapa 6: Were market conditions at END same as at START?"""
        pass

    def generate_causal_learning_rule(self) -> LearningRule:
        """Etapa 7: ROOT CAUSE + update model"""
        pass
```

---

## 📅 Timeline de Implementação

### Semana 1: Foundation (10-14/03)

**Segunda 10/03 (DB + Infrastructure)**
- Setup: `causal_learning_episodes` table
- Setup: `CausalLearningEngine` skeleton
- Setup: Integração com agente principal

**Terça-Quarta 11-12/03 (Etapas 1-3)**
- Implementar signal detection capture
- Implementar decision logging
- Implementar monitoring evolution

**Quinta-Sexta 13-14/03 (Etapas 4-5)**
- Implementar closure capture
- Implementar L1 correctness analysis
- Testes unitários

### Semana 2: Causal Analysis (15-22/03)

**Segunda-Terça 15-16/03 (Etapa 6)**
- Comparar start vs end market conditions
- Calcular drift score
- Identificar causal vs spurious

**Quarta-Quinta 17-18/03 (Etapa 7)**
- Gerar regras causais
- Integrar com confidence model
- Testes de regras

**Sexta 19/03 (Validação)**
- Análise de primeiras regras extraídas
- Backtest com regras causais vs correlacionais
- Gate 3 checkpoint

**Semana 3: Fine-tuning (20-22/03)**
- Ajustes baseados em resultados
- Documentação final
- Ready for 23/03 sprint review

---

## 🎯 Success Criteria

- [ ] 1. Todas 7 etapas capturando dados estruturados
- [ ] 2. Level 2 causal analysis funcionando
- [ ] 3. Mínimo 20 episódios com análise causal
- [ ] 4. Mínimo 5 regras causais extraídas
- [ ] 5. Backtest mostra win rate +12% vs correlacional
- [ ] 6. Model learns causal rules, ignores spurious
- [ ] 7. Documentação técnica completa
- [ ] 8. Gate 3 approval (23/03)

---

## 📚 Documentação Relacionada

- **ADR-010:** [docs/ADR-010-CAUSAL_FEEDBACK_LOOP.md](../ADR-010-CAUSAL_FEEDBACK_LOOP.md)
- **Framework Guide:** [outputs/FRAMEWORK_APRENDIZADO_CONTINUO_GUIA_PRATICO.md](../outputs/FRAMEWORK_APRENDIZADO_CONTINUO_GUIA_PRATICO.md)
- **Roadmap P0-P1:** [outputs/INTEGRACAO_P0_P1_ROADMAP_COMPLETO.md](../outputs/INTEGRACAO_P0_P1_ROADMAP_COMPLETO.md)

---

## 🔄 Próximos Passos (Agora)

1. ✅ **P0-URGENT-1 COMPLETO** (06/03, 17:00)
2. ⏳ **P1-LEARNING A PARTIR DE 10/03**
   - Kick-off meeting (10/03 14:00)
   - Setup infrastructure (DB, classes)
   - Iniciar captura de dados
3. 📊 **Validação em Produção** (10-22/03)
   - Trade por trade capturado
   - Análises realizadas
   - Regras extraídas

---

**Status:** 📋 PRONTO PARA KICK-OFF (10/03)

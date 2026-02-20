# 📋 US-001: Execução Automática de Trades com Validação ML

**Versão:** 1.2.0
**Data:** 20/02/2026
**Status:** ⏳ IN DEVELOPMENT (Sprint 1-4: 27/02 - 10/04)
**Prioridade:** P0 (Blocker para monetização)
**Estimativa:** 160h Eng Sr + 140h ML Expert

---

## 📊 Contexto Executivo

| Métrica | Baseline v1.1 | Target v1.2 | Delta |
|---------|---|---|---|
| **Capital Operacional** | 50k | 150k (rampado) | +200% |
| **Trades/dia** | 3 (manual) | 12 (automático) | +300% |
| **Win Rate** | 62% | 65-68% | +3-6pp |
| **Sharpe Ratio** | ~0.95 | >1.2 | +26% |
| **P&L mensal** | R$ 50-80k | R$ 150-250k | +3x |
| **ROI mensal** | 10-16% | 13-20% | +35% |
| **Latência Trade** | ~2-5 seg | <500ms P95 | 10x mais rápido |

---

## 🎯 User Story

```
Como OPERADOR DE TRADING (você),
Eu quero que o AGENTE AUTÔNOMO execute AUTOMATICAMENTE posições
quando uma OPORTUNIDADE VALIDADA for detectada,

Para que eu:
✓ Capture 100% das oportunidades (vs ~33% manual)
✓ Reduza latência de entrada (variabilidade humana → determinístico)
✓ Remova emoção das decisões (ML validation ≥80% confiança)
✓ Permita ramp-up de capital (150k vs 50k manual)
✓ Gere 3x mais P&L com mesmo risco absoluto
✓ Tenha controle total (veto manual sempre disponível)
```

---

## ✅ Definição de Pronto (DoR)

**Pré-requisitos que DEVEM estar prontos antes de começar:**

- [x] v1.1 (Alertas + WebSocket) ✅ COMPLETE (13/03)
- [x] Análise financeira aprovada ✅ HEAD FINANÇAS (20/02)
- [x] Risk framework especificado ✅ RISK_FRAMEWORK_v1.2.md
- [x] ML features engineered ✅ Sprint 1 (05/03)
- [x] Arquitetura técnica desenhada ✅ ARQUITETURA_MT5_INTEGRATION.md
- [ ] Backlog refinado pelo PO ✅ Esta US + tasks desdobradas

---

## 📋 Critérios de Aceitação (DoD - Definition of Done)

### **Gate 1: Detecção & Enfileiramento**

```gherkin
Given uma oportunidade detectada em WINFUT_1min
When o detector identifica padrão com score ML ≥80% confiança
Then o sistema enfileira para execução automática
And audit log registra [timestamp, padrão, score, human_approval]
And notificação é enviada ao trader (info, não bloqueio)

ACEITE METRICS:
✓ 95%+ das oportunidades válidas capturadas
✓ 0 falsos positivos acima de threshold
✓ Latência detecção <100ms P95
```

---

### **Gate 2: Validação de Risco & Ordem ao MT5**

```gherkin
Given uma oportunidade enfileirada para execução
When risk validator passa 3/3 gates:
  - Capital disponível ≥ (posição + stop loss)?
  - Correlação com posições abertas ≤ 70%?
  - Volatilidade dentro banda histórica?
And ML classifier confirma Sharpe >1.0 em backtest
Then order é enviada ao MT5 via REST API
And confirmação é logada em tempo real com ticket number
And trader recebe alert de execução (informativo)

ACEITE METRICS:
✓ 99%+ taxa de envio (falhas = trade perdido)
✓ 0 violações de capital limits
✓ 100% das validações auditadas (CVM)
```

---

### **Gate 3: Latência & Performance**

```gherkin
Given order enviada ao MT5
When execução acontece em mercado aberto
Then latência P95 < 500ms (detecção → execução)
And memory peak < 100MB durante operação
And CPU < 40% (permite múltiplas posições)

BREAKDOWN LATÊNCIA:
├─ Detecção volatilidade: ~5ms
├─ ML inference (classifier): ~50ms
├─ Risk validation: ~20ms
├─ MT5 REST request: ~100ms
├─ MT5 processing: ~50ms
├─ Response + logging: ~20ms
└─ TOTAL P95: ~322ms (well within 500ms)

ACEITE METRICS:
✓ P95 latência < 500ms
✓ P99 latência < 1000ms
✓ Zero timeouts em stress test (50 trades/min)
```

---

### **Gate 4: Gestão de Risco & Stops Automáticos**

```gherkin
Given posição aberta com loss criando-se
When stop loss é acionado (ordem hit by market move)
Then posição é FECHADA IMEDIATAMENTE via MT5
And alerta crítico é enviado para trader
And P&L final é registrado em audit log

When trader clica botão VETO em qualquer momento
Then ordem pendente é CANCELADA imediatamente
And motivo de cancelamento é logado
And capital fica disponível para próxima oportunidade

ACEITE METRICS:
✓ 100% das stops executadas automaticamente
✓ 0 "gap losses" (stop não executado)
✓ <50ms de resposta a veto manual
✓ Zero race conditions entre stops e vetos
```

---

### **Gate 5: Correlações & Hedging**

```gherkin
Given múltiplas oportunidades simultâneas
When score_pattern_1 = 0.85 E score_pattern_2 = 0.82
And correlacao_histórica(pattern_1, pattern_2) > 70%
Then sistema reduz exposure em 50% no padrão mais fraco
Or sistema aguarda fechamento da posição anterior

ACEITE METRICS:
✓ Diversificação mantida (max 2-3 posições paralelas)
✓ Correlação risk não ultrapassa 70%
✓ Drawdown máximo < 15% sob stress test
```

---

## 🏗️ Arquitetura E2E

```
MetaTrader5 (WINFUT_1min, live market data)
    ↓
ProcessadorBDI (v1.1 existente ✅)
    ↓
DetectorVolatilidade (threshold=2.0σ, v1.1 ✅)
    ├─→ Padrões detectados: 12-15/dia
    └─→ Confiança inicial: ~62% (baseado em v1.1)
    ↓
ML_ClassificadorPadroes 🆕 (v1.2)
    ├─→ Input: Features de 15-25 variáveis
    ├─→ Model: XGBoost/LightGBM (F1 > 0.68)
    ├─→ Output: Score confiança [0-100%]
    └─→ Filtra para TOP 6-8 ops/dia com score ≥80%
    ↓
RiscoValidator 🆕 (v1.2)
    ├─→ Gate 1: Capital suficiente?
    ├─→ Gate 2: Correlação aceitável?
    └─→ Gate 3: Volatilidade normal?
    ↓
OrdensExecutor 🆕 (v1.2)
    ├─→ Envia ordem ao MT5 via REST API
    ├─→ Recebe confirmação com ticket
    └─→ Atualiza status em real-time
    ↓
PosicoesMonitor 🆕 (v1.2)
    ├─→ Acompanha P&L em tempo real
    ├─→ Executa stops automáticos
    └─→ Envia alerts críticos
    ↓
TraderDashboard (v1.1 + v1.2)
    ├─→ Visualiza execuções automáticas
    ├─→ Botão VETO (sempre disponível)
    ├─→ P&L tracking + histórico
    └─→ Circuit breaker status (🟢/🟡/🟠/🔴)
```

---

## 💰 Projeção Financeira

### **FASE 1: Validação (10/04 - 24/04, 2 semanas)**

```
Capital: R$ 50k
Trades/dia: 12
Win Rate: 65% (vs 62% v1.1)
Ticket médio: ±1.5% do capital

Resultado esperado:
├─ Win traços: ~8/dia @ +1.5% = +6.0k/dia
├─ Loss traços: ~4/dia @ -1.0% = -2.0k/dia
├─ P&L diário: ~+4.0k (esperado)
├─ P&L semanal (5 dias): +20k
├─ P&L FASE 1 (2 sem): +40k
└─ ROI: 80% em 2 semanas ✅ (payback dev em 1 mês)

Gate para FASE 2:
├─ Win rate real ≥ 63% (vs projetado 65%) ✅
├─ Sharpe > 1.0 sustentado ✅
├─ Drawdown máximo < 10% ✅
├─ Zero circuit breakers acionados ✅
└─ Trader 100% confortável com automação ✅
```

### **FASE 2: Scale-up (25/04 - 08/05, 2 semanas)**

```
Capital: R$ 100k (+50k incremental)
Trades/dia: 12
Win Rate: 66% (ML melhora com més de dados)
Ticket médio: ~1.4% (correlação reduz aggression)

Resultado esperado:
├─ P&L semanal: +35-40k
├─ P&L FASE 2 (2 sem): +70-80k
└─ ROI acumulado: 110-120k em 4 semanas

Gate para FASE 3:
├─ Sharpe > 1.0 sustentado ✅
├─ Drawdown máximo < 12% ✅
├─ Win rate não divergiu de FASE 1 >2pp ✅
└─ Sistemas 99.5% uptime ✅
```

### **FASE 3: Full Scale (09/05+, ongoing)**

```
Capital: R$ 150k (+50k final)
Trades/dia: 12-15
Win Rate: 65-68% (stable, com ML tuning)
Ticket médio: ~1.5-2.0%

Resultado esperado:
├─ P&L mensal: +150-250k
├─ ROI: 13-20% mensal
└─ Anualizado: 156-240% (com reinvestimento)

Target Sharpe: >1.2 (production validated)
```

### **RESUMO 90 DIAS:**

```
Capital investido: R$ 50k (FASE 1)
Ganho P&L: R$ 255-430k
Payback: 1.3 meses
NPV (1 ano): ~R$ 1.5-2.0M
```

---

## ⚠️ Riscos & Mitigação

| Risco | Severidade | Mitigação |
|-------|-----------|-----------|
| **ML model drift** | 🔴 ALTO | Monthly retraining + backtest validation |
| **MT5 latency spike** | 🔴 ALTO | REST + fallback manual, circuit breakers |
| **Correlação não capturada** | 🟡 MÉDIO | Limitar 2-3 posições paralelas |
| **Volatilidade anormal (gap)** | 🟡 MÉDIO | Volatility band check, halt automático |
| **Capital insuficiente** | 🟢 BAIXO | Validação pré-ordem, reserva de margem |
| **Regulatory (CVM)** | 🔴 ALTO | Audit log completo, human override sempre |

---

## 📅 Timeline de Desenvolvimento

```
SPRINT 1 (27/02 - 05/03): Design & Setup
├─ Eng Sr: MT5 architecture + Risk framework
├─ ML: Feature engineering + dataset assembly
└─ Gate: Features + Risk rules APPROVED

SPRINT 2 (06/03 - 12/03): Development
├─ Eng Sr: Risk Validator + Orders Executor
├─ ML: Classifier training (grid search)
└─ Gate: ML model F1 > 0.68

SPRINT 3 (13/03 - 19/03): Integration
├─ Eng Sr: MT5 API + Dashboard
├─ ML: Backtest final (cross-validation)
└─ Gate: E2E integration OK

SPRINT 4 (20/03 - 10/04): UAT & Launch
├─ E2E testing + Staging deployment
├─ Trader acceptance testing (21/03)
└─ GO LIVE: 10/04/2026
```

---

## 📝 Notas Financeiras (Head de Finanças)

**Decisões Aprovadas:**

✅ **Rampa de Capital:** 50k → 100k → 150k (3 fases, gates obrigatórios)
✅ **ML Baseline:** Híbrido (v1.1 volatilidade + novo classifier)
✅ **Override Structure:** Trader ops full veto, CIO pause program, CFO capital
✅ **Circuit Breakers:** -3% (alerta) / -5% (slow mode) / -8% (halt)

**Custo Desenvolvimento:** ~R$ 50-100k (salários eng + ml expert)
**Payback:** 1.3 meses (FASE 1 profit já cobre)
**NPV 1 ano:** R$ 1.5-2.0M

---

## ✍️ Assinaturas de Aprovação

| Persona | Status | Data | Notas |
|---------|--------|------|-------|
| **Product Owner** | ⏳ Pending | - | Refinamento de US-001 |
| **Head de Finanças** | ✅ APPROVED | 20/02/2026 | Rampa + Risk aprovada |
| **Eng Sr** | ⏳ In Sprint 1 | 27/02 | Iniciando design MT5 |
| **ML Expert** | ⏳ In Sprint 1 | 27/02 | Iniciando feature eng |

---

**Próximo Checkpoint:** 05/03/2026 EOD
**Gate Critério:** Features + Risk rules + Baseline ML F1 > 0.65


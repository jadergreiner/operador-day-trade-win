# 🚀 SPRINT 2 - GUIA RÁPIDO & CHECKLIST

**Status:** ✅ **PRONTO PARA EXECUÇÃO IMEDIATA**

---

## 🎯 1 MINUTO SUMMARY

```
SPRINT 2 tem 3 TASKS PARALELOS:

✅ TRACK 1: API REST MT5 (Eng Sr + 3 Devs)
   └─ Prioridade: 🔴 P0-CRÍTICO
   └─ 8 AC, 14 endpoints, bloqueia ML-004

✅ TRACK 2: ML Feature Analysis (ML Expert + Data Sci)
   └─ Prioridade: 🟡 P1-Independente
   └─ 18 AC, SHAP + Drift Rules, paralelo com TRACK 1

✅ TRACK 3: Backtest 252 dias (ML Expert + Data Sci)
   └─ Prioridade: 🔴 P0-GATE 2 (Sequencial)
   └─ 20 AC, Sharpe/WR validation, inicia quando TRACK 1 OK

FILOSOFIA: Ready-When-Done (Sem pressão de data)
MODELO: TRACK 1+2 Paralelo → GATE 1 → TRACK 3 → GATE 2
```
```

---

## 📋 LEITURA OBRIGATÓRIA (Ordem)

### PARA COMEÇAR:

1. **✅ ESTE DOCUMENTO** (5 min)
2. **SPRINT2_RESUMO_EXECUTIVO_FINAL.md** (10 min)
3. **SPRINT2_PLANO_EXECUCAO_PARALELO.md** (30 min, technical)
4. **SPRINT2_MOBILIZACAO_SQUADS.md** (20 min, roles)

---

## 🎬 TIMELINE RÁPIDO

```
TODAY (26/02):
  [✅] Captura completa SPRINT 2
  [ ] Enviar docs para squad
  [ ] Confirmar disponibilidade

TOMORROW (27/02):
  [ ] 09:00: Kick-off meeting (30-60 min)
  [ ] 10:00: TRACK 1 + 2 START (paralelo)
  [ ] 15:00: Daily Standup #1

DIAS 2-7:
  [ ] Development paralelo TRACK 1 + 2
  [ ] Daily standups @ 15:00 BRT
  ✓ Sem blockers esperados

DIA 7-8:
  ✓ GATE 1: TRACK 1 + 2 complete
  ⏳ Start TRACK 3 (ML-004)

DIAS 8-14:
  [ ] TRACK 3: Backtest execution
  [ ] Daily monitoring
  ✓ TRACK 1+2 finished

DIA 14-15:
  ✓ GATE 2: TRACK 3 complete
  ✓ Capital decision (R$ 100k)
  🚀 Go-live if metrics OK

TOTAL: 10-15 dias (ready-when-done)
```

---

### FASE 2: KICK-OFF MEETING

- [ ] Confirma alocação 40-48h/semana de cada pessoa
- [ ] Confirma papéis + responsabilidades
- [ ] Confirma daily standup 15:00 BRT
- [ ] Confirma escalation contacts
- [ ] PO: Decisão GO/NO-GO
- [ ] Pessoa: Confirma papéis + responsabilidades
- [ ] Pessoa: Confirma blockers conhecidos
- [ ] All: Confirma daily standup 15:00 BRT
- [ ] All: Confirma escalation contacts
- [ ] Product Owner: Decisão GO/NO-GO

### FASE 3: EXECUÇÃO TRACK 1+2 (PARALELO)

**TRACK 1 (ENG-003) - CRÍTICO:**
- Eng Sr + 3 Devs iniciam IMEDIATAMENTE
- 8 AC para completar
- Bloqueador: Desbloqueia TRACK 3

**TRACK 2 (ML-003) - PARALELO:**
- ML Expert + Data Scientist iniciam SIMULTANEAMENTE
- 18 AC para completar
- GATE 1: Ambos tracks devem passar

---

## 👥 PAPÉIS RÁPIDO

### TRACK 1 (ENG-003 API)

| Persona | Role | Responsabilidade |
|---------|------|------------------|
| Eng Sr | Lead | Architecture + OAuth + coordination |
| Dev 1 | Auth | Login, token refresh |
| Dev 2 | Orders | Queue + retry logic |
| Dev 3 | Positions | WebSocket + real-time |
| QA | Tests | Unit + integration + E2E |

### TRACK 2 (ML-003 Features)

| Persona | Role | Responsabilidade |
|---------|------|------------------|
| ML Expert | Lead | SHAP + drift rules |
| Data Sci | Analytics | Correlation + thresholds |
| QA | Validation | Test coverage + reproducibility |

### TRACK 3 (ML-004 Backtest) - Standing by

| Persona | Role | Responsabilidade |
|---------|------|------------------|
| ML Expert | Lead | Backtest strategy |
| Data Sci | Engine | Loop + metrics |
| QA | Validation | Data + metrics validation |

---

## 🎯 SUCCESS CRITERIA (Quick)

### TRACK 1 & 2 (GATE 1)

```
✅ TRACK 1: 8/8 AC passing
   1. Auth validates credentials
   2. Token refresh auto
   3. Orders async
   4. Retry logic (3x)
   5. Order status real-time
   6. WebSocket < 100ms
   7. Account balance 30s
   8. Health check dependencies

✅ TRACK 2: 18/18 AC passing
   1-5: SHAP + correlation
   6-8: Drift rules (3)
   9-11: Alert thresholds + config
   12-18: Reports + validation
```

### TRACK 3 (GATE 2 - Capital Decision)

```
✅ GATE 2 MUST HAVE (ALL):
   1. Sharpe >= 1.0 ✅
   2. Win rate >= 59% ✅
   3. Drawdown < 15% ✅
   4. Consistency < 30% ✅
   5. 20/20 AC passing ✅
   6. UAT Operador approved ✅

🚀 IF ALL PASS: R$ 100k activated
```

---

## 🚨 BLOCKER PROTOCOL

### How to Report (Fast)

```
"🚨 BLOCKER: [TRACK] [issue] → [owner]"

Example:
"🚨 BLOCKER: TRACK1 MT5 mock not working → Eng Sr"

RESPONSE SLA:
• Acknowledge: < 15 min (next standup)
• Resolution: < 60 min (escalate if not)
• Escalation: CTO (tech) or PO (resource)
```

### Don't Wait - Report Immediately

```
❌ Wrong: Wait for standup to report blocker
✅ Right: Report now on Slack + escalate
```

---

## 📊 TRACKING (Daily Standup Format)

### 15:00 BRT Every Day (15 min, ~3 min per person)

```
EACH PERSON:
✅ "Yesterday: [What completed]"
🎯 "Today: [What planning]"
🚨 "Blockers: [Any issues?]"
📊 "AC Progress: [X/Y] AC done"

Example:
✅ "Yesterday: Auth endpoints (3 done)"
🎯 "Today: Unit tests for auth + token manager"
🚨 "Blockers: None"
📊 "AC Progress: 2/8 (25%)"
```

### What to Track

```
Daily (per track):
├─ % AC completed (cumulative)
├─ New commits merged
├─ Test coverage trend
├─ # blockers (new, resolved)
└─ Risk level (low/medium/high)
```

---

## 📌 GATES AT A GLANCE

### GATE 1 - Unblock TRACK 3

```
WHEN: Day 7-8 (when both tracks ready)

CRITERIA:
✅ TRACK 1: 8/8 AC done
✅ TRACK 2: 18/18 AC done
✅ Code reviewed (2+ per track)

DECISION:
🟢 GO → Start TRACK 3 immediately
🟡 CONDICIONAL → Fix 1-2 AC (+1-2 days)
🔴 NO-GO → Redo (3-5 days)
```

### GATE 2 - Capital Activation

```
WHEN: Day 14-15 (when TRACK 3 done)

CRITERIA (ALL MUST PASS):
✅ Sharpe >= 1.0
✅ Win rate >= 59%
✅ Drawdown < 15%
✅ 20/20 AC done
✅ UAT operator approved

DECISION:
🟢 GO → Ativar R$ 100k + Deploy
🟡 CONDICIONAL → Sharpe 0.95+ (need more analysis)
🔴 NO-GO → Iterate (5-10 days)
```

---

## 🔗 LINKS RÁPIDOS

```
📌 Master Plan:
   SPRINT2_PLANO_EXECUCAO_PARALELO.md

📌 Squad Assignments:
   SPRINT2_MOBILIZACAO_SQUADS.md

📌 Progress Tracking:
   SPRINT2_DASHBOARD_EXECUCAO.md

📌 Execution Framework:
   prompts/executa_task.md

📌 All SPRINT2 Files:
   SPRINT2_*.md (8 files total)
```

---

## 💬 COMMUNICATIONS

### Daily Standup

```
TIME: 15:00 BRT (sharp, no delays)
DURATION: 15 min max
PARTICIPANTS: All 8 personas + PO
FORMAT: 3 min per person
TOOL: Slack/Teams video call
```

### Escalation

```
TECH BLOCKER:
  → Slack: #sprint2-blockers
  → Alert: @eng-sr or @ml-expert
  → SLA: 30 min resolution

RESOURCE ISSUE:
  → Alert: @scrum-master
  → SLA: 60 min

CAPITAL DECISION:
  → Alert: @po
  → Escalate: @cfo (at GATE 2 only)
```

---

## ⚡ QUICK DOs & DON'Ts

```
✅ DO:
   • Report blockers immediately (don't wait)
   • Commit daily (even small changes)
   • Test as you code (TDD style)
   • Ask questions (no stupid questions)
   • Update AC status per day

❌ DON'T:
   • Wait for standup to report blocker
   • Skip code review (always 2+ reviewers)
   • Commit without tests
   • Ignore AC (these are your definition of done)
   • Miss standup (core ceremony)
```

---

## 📚 ONE-PAGE SUMMARY

```
┌────────────────────────────────────────────────────┐
│             SPRINT 2 SUMMARY PAGE                  │
├────────────────────────────────────────────────────┤
│                                                    │
│ 🎯 GOAL: Deliver P0-1, P1-1, P0-2 in parallel  │
│                                                    │
│ 📦 DELIVERABLES:                                  │
│   ├─ TRACK 1: 14 endpoints (8 AC)                │
│   ├─ TRACK 2: SHAP+Drift (18 AC)                │
│   └─ TRACK 3: Backtest (20 AC)                  │
│   = 46 AC total, ~2.100 lines code              │
│                                                    │
│ 👥 TEAM: 8 personas                              │
│   ├─ Eng Sr + 3 Devs (TRACK 1)                  │
│   ├─ ML Expert + Data Sci (TRACK 2/3)           │
│   └─ QA, DevOps, Docs support                   │
│                                                    │
│ ⏱️ TIMELINE: 10-15 days (ready-when-done)       │
│   ├─ TRACK 1+2 parallel: 7-10 days              │
│   ├─ GATE 1 checkpoint: Day 7-8                 │
│   ├─ TRACK 3 sequential: 5-7 days               │
│   └─ GATE 2 capital decision: Day 14-15         │
│                                                    │
│ 🎯 SUCCESS:                                       │
│   ├─ GATE 1: Both tracks 100% AC + code review │
│   ├─ GATE 2: All metrics passing + operator OK │
│   └─ RESULT: R$ 100k capital activated         │
│                                                    │
│ 🚀 STATUS: READY TO LAUNCH                       │
│   └─ Kick-off 27/02 09:00 BRT                   │
│   └─ Start 27/02 10:00 BRT                      │
│                                                    │
└────────────────────────────────────────────────────┘
```

---

## 🎊 NÃO ESQUEÇA!

```
1️⃣ LER DOCUMENTAÇÃO
   ✓ SPRINT2_RESUMO_EXECUTIVO_FINAL.md (10 min)
   ✓ Seu track em SPRINT2_PLANO_EXECUCAO_PARALELO.md
   ✓ Seu papel em SPRINT2_MOBILIZACAO_SQUADS.md

2️⃣ CONFIRMAR DISPONIBILIDADE
   ✓ Responder no Slack hoje (< 10 min)
   ✓ Bloquear calendário 27/02-13/03

3️⃣ APARECER NO KICK-OFF
   ✓ 27/02 09:00 BRT (sharp)
   ✓ 30-60 minutos (agenda)
   ✓ Estar pronto para START às 10:00

4️⃣ STANDUPS DIÁRIOS
   ✓ 15:00 BRT (não é negociável)
   ✓ 15 min (sharp, no delays)
   ✓ Todos os 8 personas
```

---

## 🤔 FAQ RÁPIDO

**P: Qual é meu papél?**
A: Veja SPRINT2_MOBILIZACAO_SQUADS.md, sua section

**P: Quando começa?**
A: Kick-off 27/02 09:00, Start 27/02 10:00

**P: Preciso entregar código?**
A: Depende do papél - veja SPRINT2_PLANO_EXECUCAO_PARALELO.md seu track

**P: Posso atrasar um pouco?**
A: Não - GATE 1 (Day 7-8) é imóvel, GATE 2 (Day 14-15) também

**P: E se tiver bloqueador?**
A: Report IMEDIATAMENTE (Slack #sprint2-blockers)

**P: Qual é o success criteria meu track?**
A: AC passing + code review + tests - veja SPRINT2_PLANO_EXECUCAO_PARALELO.md

---

**Gerado:** 26/02/2026
**Status:** ✅ PRONTO para USAR

🚀 **TE VER NO KICK-OFF! 27/02 09:00!**


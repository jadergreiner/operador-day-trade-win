# 📊 Daily Standup Configuration (Sprint 2)

**Sprint:** Sprint 2 Phase 6  
**Período:** 27/02-13/03/2026  
**Horário:** 15:00 BRT (não-negociável)  
**Duração:** 15 minutos  
**Participantes:** Eng Sr, ML Expert, QA Lead, Product Owner

---

## 📋 FORMATO PADRÃO (15 min)

### **Abertura (1 min) - 15:00-15:01**
- Product Owner: Status geral do sprint
- Bloqueadores identificados ontem?
- Ajustes no plano?

---

### **Cada Pessoa (3-5 min cada) - 15:01-15:16**

**TEMPLATE PARA CADA PESSOA:**

```
Name: [Eng Sr / ML Expert / QA Lead]

✅ O que completei ontem?
   - Task X: Status (DONE / IN-PROGRESS / BLOCKED)
   - Task Y: Progresso (% completo)
   - Unit tests: X/Y passing

🎯 O que planeio fazer hoje?
   - Task A: Planejado 2-3h
   - Task B: Paralelo com A
   - Review/Commit: EOD

🚨 Blockers?
   - [Nenhum] ✅ ou [Bloqueador X] - Mitigação?
```

**EXEMPLO REAL (Eng Sr em 27/02 15:00):**

```
Name: Eng Sr

✅ O que completei ontem?
   - BDI Integration (#16): 100% (fase 1-3 complete)
   - Unit tests: 5/5 passing ✅
   - Code review: Aprovado

🎯 O que planeio fazer hoje?
   - WebSocket Server (#17): Setup (2h)
   - Integration test: WebSocket + BDI (1h)
   - Commit + documentation (0.5h)

🚨 Blockers?
   - [Nenhum] ✅ - Sistema estável
```

---

## 📅 SCHEDULE DOS STANDUPS

| Data | Dia | Task Focus | Owner Priority |
|------|-----|-----------|-----------------|
| 27/02 | 2ª | Kickoff | Ambos iniciando |
| 28/02 | 3ª | BDI + Backtest | Completar tarefas |
| 01/03 | 4ª | WebSocket | Validação intermediária |
| 02/03 | 5ª | Backtest Validation | Eng Sr suportando ML |
| 03/03 | 6ª | E2E Testing | Ambos finalizando |
| 04/03 | 2ª | Email Config | Eng Sr solo |
| 05/03 | 3ª | Staging Deploy | DevOps + ambos |
| 06-13/03 | 4ª-5ª | Phase 2 prep | Planning próxima fase |

---

## 🎯 MÉTRICAS DIÁRIAS

### **Board Status (Atualizar todos os dias)**

```
SPRINT 2 STATUS BOARD - 27/02/2026

BLOCKER TASKS (MUST):
├─ [████████░░] 80% INTEGRATION-ENG-001 (BDI) — Eng Sr
│  ├─ AC-1: ✅ DONE
│  ├─ AC-2: ✅ DONE
│  ├─ AC-3: ✅ DONE
│  └─ AC-4-7: ⏳ IN-PROGRESS
│
├─ [██████░░░░] 60% INTEGRATION-ML-001 (Backtest) — ML Expert
│  ├─ AC-1: ✅ DONE
│  ├─ AC-2: ✅ DONE
│  ├─ AC-3: ⏳ IN-PROGRESS
│  └─ AC-4-6: ⏳ PENDING
│
├─ [░░░░░░░░░░] 0% INTEGRATION-ENG-002 (WebSocket) — Eng Sr
│  └─ Bloqueador: BDI-001 (ETA: 28/02 20:00)
│
└─ [░░░░░░░░░░] 0% INTEGRATION-ML-002 (Validation) — ML Expert
   └─ Bloqueador: ML-001 (ETA: 28/02 20:00)

SPRINT METRICS:
├─ Completion: 35% (4/8 tasks initiated)
├─ Tests Passing: 12/17 (70%)
├─ Blockers: 2 (ETA: 28/02)
└─ Team Health: 🟢 ON TRACK
```

### **Tracking Sheet**

| Date | Eng Sr Task | Eng Sr % | ML Task | ML % | Blockers | Notes |
|------|-------------|---------|---------|------|----------|-------|
| 27/02 | BDI-001 | 10% | ML-001 | 20% | None ✅ | Kickoff OK |
| 28/02 | BDI-001 | 90% | ML-001 | 80% | None ✅ | Nearly done |
| 01/03 | ENG-002 | 30% | ML-002 | 20% | None ✅ | Next phase |
| ... | ... | ... | ... | ... | ... | ... |

---

## 🚨 ESCALATION PROTOCOL

### **Se Bloqueador Identificado:**

```
1. ACKNOWLEDGE (1 min)
   - Confirm bloqueador no standup
   - Record no tracking board

2. ROOT CAUSE (15 min após standup)
   - Technical: Call CTO
   - Resource: Call Head Infra
   - Scope: Call Product Owner
   - Input needed: Call dependente

3. MITIGAÇÃO (30 min max from root cause)
   - Option A: Implementar workaround
   - Option B: Parallelizar outro task
   - Option C: Request extension (risky)

4. RESOLUTION (EOD)
   - Close bloqueador
   - Update tracking board
   - Communication to team
```

### **Exemplo Escalation:**

```
27/02 15:30 - Eng Sr identifica: "MT5 connection timeout"

1. ACKNOWLEDGE
   ✅ Adicionado ao tracking board
  
2. ROOT CAUSE
   - Call CTO (15:35)
   - Descoberta: Firewall bloqueando porta MT5
  
3. MITIGAÇÃO  
   - Option: Use mock MT5 temporário (30 min impl)
   - Continuar BDI com dados históricos
  
4. RESOLUTION
   - Mock MT5 pronto (16:00)
   - BDI rodando normal
   - Firewall agendado pra tomorrow
```

---

## 📞 COMUNICAÇÃO

### **Canais de Comunicação**
- **Daily Standup:** Slack videocall #standup-sprint2
- **Urgent Blocker:** @here in #sprint2-critical
- **Documentation:** GitHub issues comments
- **Decisions:** Slack thread (recorded)

### **Resposta SLA para Mensagens**
- Standup: Resposta em 1h (15:00 BRT)
- Blocker: Resposta em 15 min
- Decision request: Resposta em 1h
- Documentation: Resposta em 4h

---

## ✅ CHECKLIST ANTES DE CADA STANDUP

**Eng Sr:**
- [ ] Código commitado desde último standup?
- [ ] Unit tests rodando?
- [ ] Nenhum console error?
- [ ] Documentation atualizada?

**ML Expert:**
- [ ] Notebook/script executado com sucesso?
- [ ] Dados validados (shape, types)?
- [ ] Métricas calculadas e logadas?
- [ ] Nenhum NaN values?

**QA Lead:**
- [ ] Tests executados?  
- [ ] Coverage > 90%?
- [ ] Issues reportadas?

**Product Owner:**
- [ ] Legal/stakeholder sign-off?
- [ ] Next sprint planejado?
- [ ] Risk assessment OK?

---

## 📈 EXEMPLO DE STANDUP (27/02 15:00)

```
15:00 - Product Owner opens meeting
PO: "Sprint 2 kickoff official! Objective: Complete BDI + Backtest before 01/03.
     Any blockers preventing start?"
       Eng Sr: "No blockers" ✅
       ML Expert: "No blockers" ✅

15:01 - Eng Sr (3 min)
Eng Sr: "✅ Completei setup environment + code review da arquitetura.
        🎯 Vou começar BDI Integration agora (10:00-17:00), expecting 5/5
        tests by EOD. 🚨 Nenhum blocker."

15:04 - ML Expert (3 min)
ML Expert: "✅ Completei validação de dados históricos e feature list.
          🎯 Vou começar data loading agora (10:30-12:30), planning
          backtest_optimized_results.json by EOD. 🚨 Nenhum blocker."

15:07 - QA Lead (2 min)
QA: "✅ Validated test fixtures. 🎯 Vou estar ready para rodar qualquer
     test assim que código ficar pronto. 🚨 Clean slate, ready to roll."

15:09 - Product Owner (1 min)
PO: "Excelente. Team synchronized. Decisions? Questions? [Silence].
     Próximo standup amanhã 15:00. Let's go! 💪"

15:10 - Meeting encerrado
```

---

## 📋 DAILY STANDUP CHECKLIST (Para usar)

**Dia:** ___/02/2026  
**Hora Início:** 15:00 BRT  

### **Pre-Meeting (14:55)**
- [ ] Todos online 1 min antes?
- [ ] Recording ativado (se necessário)?
- [ ] Tracking board aberto?

### **Durante Meeting**
- [ ] PO abre (1 min)
  - [ ] Status geral
  - [ ] Blockers known?
  
- [ ] Eng Sr update (3-5 min)
  - [ ] Done yesterday
  - [ ] Plan today
  - [ ] Blockers
  
- [ ] ML Expert update (3-5 min)
  - [ ] Done yesterday
  - [ ] Plan today
  - [ ] Blockers
  
- [ ] QA Lead update (2-3 min)
  - [ ] Tests status
  - [ ] Issues
  
- [ ] Decisions needed?
  - [ ] Any go/no-go?
  
### **Post-Meeting (15:15)**
- [ ] Tracking board atualizado?
- [ ] Decisions logged?
- [ ] Next meeting scheduled?

---

**Status:** ✅ PRONTO PARA USAR A PARTIR DE 27/02 15:00 BRT

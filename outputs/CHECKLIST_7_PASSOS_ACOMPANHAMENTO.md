# ✅ CHECKLIST EXECUTIVO - 7 PASSOS (Acompanhamento)

Use este arquivo para rastrear progresso dos 7 passos.  
Atualize diariamente durante execução.

---

## 📊 VISTA GERAL DOS 7 PASSOS

```
HOJE:          [ Passos 1-3 ]
PRÓXIMOS 5d:   [ Passos 4-5 ]
SEMANA 2:      [ Passos 6-7 ]

Progresso: ████████░░░░░░░░░░░░░ 35% (design)  →  execução agora
```

---

## PASSO 1️⃣ : Revisar P0-URGENT-1 com Stakeholders

**Duração:** 45 min  
**Status:** ⏳ TODO  
**Owner:** Tech Lead / Apresentador  

| Item | Status | Data | Notas |
|------|--------|------|-------|
| Ler IMPLEMENTACAO_P0_URGENT_1.md | ❌ | - | 10 min |
| Rodar testes (10/10 pass) | ❌ | - | 5 min |
| Preparar slides | ❌ | - | 20 min |
| Agendar reunião stakeholders | ❌ | - | 15h antes |
| **Reunião realizada** | ❌ | - | 60 min |
| Aprovação de 3/4 personas | ❌ | - | Decisão |

**Checklist:**
- [ ] Apresentação preparada (Problema 2min, Solução 3min, Evidência 5min, Risks 10min)
- [ ] Screenshots de testes passando
- [ ] Rollback plan escrito
- [ ] Stakeholders confirmados presença

**Saída esperada quando ✅:**
```
✅ Aprovação obtida
✅ Luz verde para PASSO 2
```

**Notas:**
```
Data apresentação: ___________
Presentes: ___________
Questões: ___________
Decisão: [ ] SIM [ ] NÃO [ ] CONDICIONAL
```

---

## PASSO 2️⃣ : Deploy para Staging

**Duração:** 30 min  
**Status:** ⏳ TODO  
**Owner:** Operador Técnico  

| Item | Status | Data | Notas |
|------|--------|------|-------|
| Backup trading.db criado | ❌ | - | ✅ backup_06mar |
| Sintaxe validada (py_compile) | ❌ | - | Agent + tests |
| Testes 10/10 passando | ❌ | - | test_inactivity |
| Agent iniciado em staging | ❌ | - | Simulator mode ON |
| Logs exibem penalidades | ❌ | - | "INACTIVITY_PENALTY" |
| Sem crashes em 10 min | ❌ | - | Monitoramento |

**Checklist:**
- [ ] `copy data\db\trading.db data\db\trading.db.backup_06mar`
- [ ] `python -m py_compile scripts/agente_micro_tendencia_winfut.py`
- [ ] `python scripts/test_inactivity_penalty.py` → 10/10 PASS
- [ ] `python scripts/agente_micro_tendencia_winfut.py` rodando
- [ ] Logs sendo criados (outputs/trading_*.log)
- [ ] Penalty logs aparecendo

**Saída esperada quando ✅:**
```
✅ Agent rodando em staging
✅ Penalidades sendo calculadas
✅ Luz verde para PASSO 3
```

**Notas:**
```
Data deploy: ___________
Horário início: ___________
Primeira penalty vista: ___________
Erros encontrados: ___________
```

---

## PASSO 3️⃣ : Notificar Equipe P1-LEARNING

**Duração:** 20 min  
**Status:** ⏳ TODO  
**Owner:** Tech Lead  

| Item | Status | Data | Notas |
|------|--------|------|-------|
| Email template preparado | ❌ | - | Template no PASSO 3 |
| Emails enviados | ❌ | - | 4 pessoas |
| Confirmações recebidas | ❌ | - | 4/4 minimum |
| Calendário bloqueado | ❌ | - | Semana de kick-off |
| Documentação anexada | ❌ | - | ROADMAP + ERG-010 |

**Checklist:**
- [ ] Copia email template de `7_PASSOS_PLANO_EXECUCAO.md`
- [ ] ML Expert recebe confirmação
- [ ] Data Engineer recebe confirmação
- [ ] QA recebe confirmação
- [ ] Tech Lead recebe confirmação
- [ ] Reunião K.O. agendada para X data

**Saída esperada quando ✅:**
```
✅ Equipe notificada
✅ Calendário reservado
✅ Documentação distribuída
```

**Notas:**
```
Data envio: ___________
Confirmações: ___________
Data K.O. agendado: ___________
```

---

## PASSO 4️⃣ : Monitorar P0-URGENT-1 (Contínuo - 3-5 dias)

**Duração:** 3-5 dias (daily standups)  
**Status:** ⏳ APÓS PASSO 2  
**Owner:** Operador + ML Expert  

### Dia 1 (Data: _______):

| Métrica | Target | Atual | Status | Notas |
|---------|--------|-------|--------|-------|
| Trades | 2-3 | ? | ❌/⏳/✅ | |
| Confidence | Não cair | [0.XX] | ❌/⏳/✅ | |
| Penalties | Sim, logs | Sim/Não | ❌/⏳/✅ | |
| Erros | 0 | ? | ❌/⏳/✅ | |

Saída: ___________

### Dia 2 (Data: _______):

| Métrica | Target | Atual | Status | Notas |
|---------|--------|-------|--------|-------|
| Trades | 2-3 | ? | ❌/⏳/✅ | |
| Confidence | Não cair | [0.XX] | ❌/⏳/✅ | |
| Penalties | Sim, logs | Sim/Não | ❌/⏳/✅ | |
| Erros | 0 | ? | ❌/⏳/✅ | |

Saída: ___________

### Dia 3 (Data: _______):

[Repetir padrão]

### Dia 4 (Data: _______):

[Repetir padrão]

### Dia 5 (Data: _______):

[Repetir padrão]

**Status Final após 3-5 dias:**

```
[ ] SIM - P0-URGENT-1 validado com sucesso
    → Prosseguir para PASSO 6
    
[ ] NÃO - Problemas encontrados
    → Ativar P0-URGENT-2 (Forced Activation backup)
    → Estender monitoramento
```

---

## PASSO 5️⃣ : Preparar P1-LEARNING (Paralelo a Passo 4)

**Duração:** 5-6h (em paralelo)  
**Status:** ⏳ PARALELO COM PASSO 4  
**Owner:** Data Engineer + ML Expert + QA  

| Subtarefa | Status | Owner | Data | Notas |
|-----------|--------|-------|------|-------|
| DB schema criado | ❌ | Data Eng | - | table causal_learning_episodes |
| Classes skeleton | ❌ | ML Expert | - | CausalLearningEngine |
| Testes skeleton | ❌ | QA | - | 5 testes básicos |
| Git commit | ❌ | ML Expert | - | Primeiro commit P1 |

**Checklist:**

**Data Engineer (2h):**
- [ ] SQL script executado (crear tabela)
- [ ] Índices criados
- [ ] Conectividade validada
- [ ] Schema revisado

**ML Expert (3h):**
- [ ] CausalLearningEngine.py criado (200 LOC skeleton)
- [ ] 7 metodhs: record_signal, record_decision, etc (stubs)
- [ ] Type hints + docstrings
- [ ] Git pushed

**QA (3h):**
- [ ] test_causal_learning.py criado (150 LOC skeleton)
- [ ] 5 testes básicos
- [ ] Testes rodando (all PASS)
- [ ] Git pushed

**Saída esperada quando ✅:**
```
✅ Infrastructure pronta
✅ Classes skeleton criadas
✅ Testes OK
✅ Pronto para kick-off
```

**Notas:**
```
Data DB schema: ___________
Data classes: ___________
Data testes: ___________
Commits: ___________
```

---

## PASSO 6️⃣ : P1-LEARNING Kick-off

**Duração:** 60 min (reunião)  
**Status:** ⏳ QUANDO PASSO 4 VALIDADO  
**Owner:** ML Expert (facilitador)  

| Item | Status | Data | Notas |
|------|--------|------|-------|
| Reunião agendada | ❌ | - | 60 min |
| Pré-requisitos enviados | ❌ | - | ROADMAP + ERG-010 |
| Todos leram (confirmado) | ❌ | - | 4 pessoas confirmaram |
| **Reunião realizada** | ❌ | - | Todos presentes |
| Slides apresentados | ❌ | - | Contexto + Arch + Sprint |
| Sprint planning OK | ❌ | - | Semana 1-2 confirmada |
| Primeiro commit P1 etapas | ❌ | - | Inicia Etapa 1 |

**Checklist:**
- [ ] Calendário enviado (60 min)
- [ ] Slides preparadas
- [ ] Pré-requisitos enviados (30 min antes)
- [ ] ROADMAP discutido ponto a ponto
- [ ] Roles confirmados (ML lead, Data Eng, QA)
- [ ] Dailys agendados 15:00 BRT
- [ ] Primeiro commit feito (etapas 1-5 inicia)

**Saída esperada quando ✅:**
```
✅ Reunião OK
✅ Sprint iniciado
✅ Etapas 1-5 começadas
✅ Luz verde para PASSO 7
```

**Notas:**
```
Data reunião: ___________
Presentes: ___________
Decisões: ___________
Próximo sprint standup: ___________
```

---

## PASSO 7️⃣ : Extrair Regras Causais (Etapas 6-7)

**Duração:** 5-8h (semana 2 de P1)  
**Status:** ⏳ APÓS PASSO 6  
**Owner:** ML Expert + Data Engineer  

| Item | Status | Data | Notas |
|------|--------|------|-------|
| Etapas 1-5 capturando dados | ❌ | - | 20+ episódios |
| Etapa 6: Causal Analysis | ❌ | - | analyze_causation() |
| Etapa 7: Rule Generation | ❌ | - | generate_causal_rule() |
| Regras extraídas | ❌ | - | 5+ regras |
| Regras validadas | ❌ | - | Backtest OK |
| Git commit | ❌ | - | Etapas 6-7 complete |

**Checklist:**

**Semana 2 - Dia 1-2:**
- [ ] Etapas 1-5 com 20+ episódios processados
- [ ] Database com dados consistentes
- [ ] Análise L1 funcionando

**Semana 2 - Dia 2-3:**
- [ ] Etapa 6 implementada (context comparison)
- [ ] Etapa 7 implementada (rule extraction)
- [ ] 5+ regras extraídas

**Semana 2 - Dia 3-4:**
- [ ] Regras validadas (backtest OK)
- [ ] Win rate: +12% vs correlacional
- [ ] Testes finais OK
- [ ] Documentação atualizada

**Saída esperada quando ✅:**
```
✅ 7 etapas completas
✅ 5+ regras causais extraídas
✅ Backtest: +12% win rate
✅ Pronto para produção
```

**Notas:**
```
Data etapas 1-5 OK: ___________
Data etapa 6 OK: ___________
Data etapa 7 OK: ___________
Regras extraídas: ___________
Win rate melhoria: ___________
```

---

## 📈 PROGRESSO CONSOLIDADO

```
Passo 1: [░░░░░░░░░░] 0%   ⏳ TODO
Passo 2: [░░░░░░░░░░] 0%   ⏳ TODO
Passo 3: [░░░░░░░░░░] 0%   ⏳ TODO
Passo 4: [░░░░░░░░░░] 0%   ⏳ TODO
Passo 5: [░░░░░░░░░░] 0%   ⏳ TODO
Passo 6: [░░░░░░░░░░] 0%   ⏳ TODO
Passo 7: [░░░░░░░░░░] 0%   ⏳ TODO

TOTAL:   [░░░░░░░░░░] 0%   ⏳ PRONTO PARA COMEÇAR
```

---

## 🎯 KPIs

| KPI | Target | Atual | Status |
|-----|--------|-------|--------|
| Approvals P0 | 3/4 personas | - | ⏳ |
| Trades/dia | 2-3 | - | ⏳ |
| Confidence | Não cair | - | ⏳ |
| Penalidades | Ativas | - | ⏳ |
| P1 Kick-off | Quando P0 OK | - | ⏳ |
| Episódios P1 | 20+ | - | ⏳ |
| Regras causais | 5+ | - | ⏳ |
| Win rate delta | +12% | - | ⏳ |

---

## 🆘 BLOCKERS

```
Atual: NENHUM - Tudo pronto para execução

Se encontrar blocker:
1. Descreva aqui
2. Escalona
3. Document resolução
```

---

## 📝 NOTAS EXECUTIVAS

```
Data início: _______
Período cobertura: _______ até _______

Destaques:
_________________________________________________________________

Riscos identificados:
_________________________________________________________________

Decisões tomadas:
_________________________________________________________________

Próximas prioridades:
_________________________________________________________________
```

---

## 📍 ARQUIVOS DE REFERÊNCIA

```
📌 PASSO 1: Revisar
   → docs/features/inactivity-penalty/IMPLEMENTACAO_P0_URGENT_1.md
   → scripts/test_inactivity_penalty.py (evidence)

📌 PASSO 2: Deploy
   → config/settings.py (MT5_SIMULATOR_MODE)
   → scripts/agente_micro_tendencia_winfut.py

📌 PASSO 3: Notificar
   → 7_PASSOS_PLANO_EXECUCAO.md (email template)

📌 PASSO 4: Monitorar
   → outputs/trading_*.log (logs diários)
   → Métricas: trades, confidence, penalties

📌 PASSO 5: Preparar P1
   → 7_PASSOS_PLANO_EXECUCAO.md (SQL + classes)

📌 PASSO 6: Kick-off
   → docs/features/causal-learning/ROADMAP_P1_LEARNING.md
   → docs/ADR-010-CAUSAL_FEEDBACK_LOOP.md

📌 PASSO 7: Regras
   → src/application/services/causal_learning_engine.py
   → scripts/test_causal_learning.py
```

---

**Última atualização:** _______  
**Próxima revisão:** _______  
**Status geral:** 🟢 PRONTO PARA EXECUÇÃO

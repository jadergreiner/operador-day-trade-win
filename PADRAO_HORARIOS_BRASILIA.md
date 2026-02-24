# ⏰ PADRONIZAÇÃO DE HORÁRIOS - BRASÍLIA TIME (BRT)

**Data Vigência:** 23 de Fevereiro de 2026
**Fuso Horário Oficial:** BRT (Brasília Time) = UTC-3
**Padrão Aplicado:** Todos os horários em BRT, com UTC como referência secundária

---

## 🌍 CONVERSÃO UTC ↔ BRT

```
Brasília está em UTC-3 (fevereiro é verão brasileiro)

CONVERSÃO (subtrair 3 horas de UTC para obter BRT):

UTC            BRT              Evento
─────────────────────────────────────────────
23:00 UTC  →  20:00 BRT    Deploy Stage 1 INICIA
23:30 UTC  →  20:30 BRT    Componentes começam
00:30 UTC  →  21:30 BRT    Stage 1 LIVE
06:00 UTC  →  03:00 BRT    TODO-1 Labels COMPLETO
09:00 UTC  →  06:00 BRT    ML Expert acorda
12:00 UTC  →  09:00 BRT    Novo dia de trabalho
18:00 UTC  →  15:00 BRT    Daily Standup
03:00 UTC  →  00:00 BRT    Meia-noite (próx dia)
```

---

## 📋 TIMELINE OFICIAL DO PROJETO (HORÁRIO BRASÍLIA)

### 23 DE FEVEREIRO (HOJE À NOITE)

```
20:00 BRT  → Deployment Stage 1 INICIA
           ├─ ML Expert: TODO-1 labels começa (paralelo)
           ├─ Eng Sr + QA: Preparam componentes
           └─ Status: ⏱️ COMEÇANDO AGORA

20:30 BRT  → Componentes iniciam deployment
           ├─ WebSocket Server → PROD
           ├─ Risk Validator → PROD
           ├─ BDI Detector → PROD
           └─ Feature Pipeline → STAGING

21:00 BRT  → Validações & smoke tests
           └─ Status: Testando componentes

21:30 BRT  → 🟢 ESTÁGIO 1 LIVE & MONITORANDO
           ├─ WebSocket: Listen 127.0.0.1:8765
           ├─ Risk: Guards 3 gates
           ├─ BDI: Monitoring spikes
           ├─ Features: 17.280 velas carregadas
           └─ Status: ✅ PRODUÇÃO LOCAL ATIVA

03:00 BRT (24 FEV)  → 🔴 TODO-1 LABELS COMPLETO
                    ├─ Dataset rotulado (zero NaN)
                    ├─ Imbalance validado
                    └─ Status: ✅ Pronto para Grid Search
```

### 24 DE FEVEREIRO (AMANHÃ - DIA NORMAL)

```
06:00 BRT  → ☀️ Amanhecer
           └─ Status: TODO-1 já completado 3h atrás

09:00 BRT  → 🚀 NOVO DIA DE TRABALHO
           ├─ Eng Sr: OrdersExecutor START (implementação)
           ├─ ML Expert: Grid Search START
           ├─ QA: E2E Setup
           └─ Status: Produção + desenvolvimento

13:00 BRT  → 🍽️ Almoço
           └─ Status: Pausa trabalho

15:00 BRT  → 📊 DAILY STANDUP OFICIAL
           ├─ Todos presentes (Eng Sr, ML, QA, Arch, Risk)
           ├─ Report status: Orders, Grid Search
           ├─ Identificar bloqueadores
           └─ Status: Checkpoint oficial

17:00 BRT  → 📋 FIM JORNADA
           ├─ OrdersExecutor: ~50-80% esperado
           ├─ Grid Search: Rodando
           ├─ Plano: Continuar amanhã
           └─ Status: Fim dia 1 desenvolvimento

18:00 BRT  → 🚪 Saída do expediente
           └─ Status: Monitoramento automático ligado
```

### 25 DE FEVEREIRO (SEGUNDA-FEIRA)

```
09:00 BRT  → Continuação OrdersExecutor + Grid Search
           ├─ OrdersExecutor: Target 95%+ code
           ├─ E2E tests: Starting
           └─ Grid: Running in background

17:00 BRT  → FIM JORNADA - OrdersExecutor deve estar 100%
           ├─ Code complete
           ├─ Unit tests passing
           ├─ E2E tests validado
           └─ Code review aprovado

18:00+     → Overnight: Grid Search rodando

PRÓXIMO DIA (26 FEV):
09:00 BRT  → Review grid search results
           └─ Preparar UAT para 02/03
```

### 02 DE MARÇO (QUARTA-FEIRA)

```
09:00-14:00 BRT  → 🎯 TRADER UAT (Validação)
                  ├─ OrdersExecutor em staging
                  ├─ Risk + Circuit breakers
                  ├─ Trader testa manualmente
                  └─ Approval: GO/NO-GO

14:00-18:00 BRT  → Deploy Estágio 2 (se UAT OK)
                  ├─ Email Configuration
                  ├─ Audit Log
                  ├─ Circuit Breaker Triggers
                  └─ Status: Stage 2 LIVE
```

### 05 DE MARÇO (GATE 1 - CRÍTICO!)

```
09:00-17:00 BRT  → Grid Search validation final
                  ├─ F1 score: DEVE ser > 0.65
                  └─ Cross-validation: Verificado

17:00 BRT        → 🟢 GATE 1 DECISION MOMENT
                  ├─ Se F1 > 0.65: GO ✅ (Go-Live 10/04 viável)
                  └─ Se F1 ≤ 0.65: NO-GO ❌ (Atraso 7 dias)

STATUS: CRÍTICO - This is the go/no-go for entire project
```

### 10 DE ABRIL (GO-LIVE v1.2)

```
09:00 BRT  → 🚀 GO-LIVE EXECUÇÃO AUTOMÁTICA
           ├─ v1.1 (alertas) já está em BETA desde 13/03
           ├─ v1.2 (execução automática) ativa
           ├─ Capital ramp: R$ 50k inicial
           ├─ Circuit breakers: -3%/-5%/-8% ATIVO
           └─ Status: OPERACIONAL
```

---

## 🕐 HORÁRIOS RECORRENTES

### Standups Diários (até novo aviso)

```
Horário: 15:00 BRT (segunda a sexta)
Duração: 15-30 minutos
Pessoas: Eng Sr, ML Expert, QA, Architect, Risk
Local: Conforme configurado
Agenda:
  ├─ Status último 24h
  ├─ Plano próximas 24h
  ├─ Bloqueadores identificados
  └─ Riscos
```

### Health Checks Automáticos

```
Frequência: 30 segundos (durante Stage 1)
Métricas:
  ├─ WebSocket: Port 8765 respondendo
  ├─ Risk: Guards ativos, memória OK
  ├─ BDI: Detector respondendo < 100ms
  └─ Features: Data integridade validada
```

### Monitores Contínuos

```
Monitoramento 24/7:
  └─ Sistema local rodando indefinidamente
  └─ Logs sendo coletados
  └─ Status via logs/deployment_status.txt
  └─ Alertas críticos: Notificação imediata
```

---

## 📅 CALENDÁRIO SPRINT 1

```
FEVEREIRO 2026 (Semana 1-2):

23/02 (DOM)  ├─ 19:00: Final reunião executiva (Brasília)
(Fim Semana) ├─ 20:00: Deploy Stage 1 INICIA
             ├─ 21:30: Stage 1 LIVE
             └─ 03:00 (24/02): TODO-1 COMPLETO

24/02 (SEG)  ├─ 09:00: OrdersExecutor + Grid INICIA
             ├─ 15:00: Daily Standup
             └─ 17:00: Fim jornada

25/02 (TER)  ├─ 09:00: Continuação
             ├─ 15:00: Daily Standup
             ├─ 17:00: OrdersExecutor deve ser 100%
             └─ E2E tests rodando

26-27/02     ├─ Continuação desenvolvimento
(QUA-JEU)    └─ Grid search rodando background

28/02 (SEX)  ├─ Last day feedback Sprint 1
             └─ Prepare UAT para 02/03

01/03 (SAB)  ├─ Audit log implementation
(Fim Semana) └─ Final prep Stage 2

MARÇO 2026 (Semana 2):

02/03 (DOM)  ├─ 09:00-14:00: Trader UAT
(Fim Semana) ├─ 14:00-18:00: Deploy Stage 2
             └─ Status: v1.1 BETA ready, v1.2 partial

03/03 (SEG)  ├─ Circuit breaker finalization
             ├─ CVM compliance check
             └─ Status: Pre-beta

05/03 (QUA)  └─ 17:00 BRT: 🎯 GATE 1 DECISION (F1 > 0.65)

13/03 (JEU)  └─ 🎉 BETA LAUNCH v1.1 (se Gate 1 OK)

10/04 (FRI)  └─ 🚀 GO-LIVE v1.2 (se tudo OK)
```

---

## 🎯 REGRAS DE HORÁRIO

### Regra 1: Sempre use BRT como padrão

✅ **CORRETO:**
```
Deploy começa 20:00 BRT
Standup 15:00 BRT
Gate 1: 05/03 17:00 BRT
```

❌ **EVITAR:**
```
Deploy começa 23:00 UTC (sem mencionar BRT)
Standup 18:00 UTC (confunde)
Gate 1: 05/03 20:00 UTC (não é padrão)
```

### Regra 2: Use UTC apenas como referência secundária

✅ **BOM:**
```
Deploy: 20:00 BRT (23:00 UTC)
Standup: 15:00 BRT (18:00 UTC)
```

❌ **ÉVITAR:**
```
Em UTC: Deploy às 23:00 (converter para BRT: 20:00)
```

### Regra 3: Sempre especifique o dia para madrugadas

✅ **CLARO:**
```
TODO-1 completa em 03:00 BRT do dia 24/02
Deploy inicia 20:00 BRT de 23/02
```

❌ **AMBÍGUO:**
```
TODO-1 completa em 03:00 BRT
Deploy inicia 20:00 BRT
(qual dia?)
```

### Regra 4: Use formato consistente

✅ **PADRÃO DO PROJETO:**
```
HH:MM BRT (dia completo)
Exemplos:
  - 20:00 BRT de 23/02
  - 09:00 BRT (implícito = próximo dia útil)
  - 15:00 BRT (daily standup, repetido)
```

---

## 📝 CHECKLIST - Atualizar documentação

Após esta padronização, verificar:

```
[ ] ATA_REUNIAO_EXECUTIVA_PRODUCAO_23FEV_PT.md
    └─ Todos horários em BRT
    └─ UTC mencionado entre parênteses (opcional)

[ ] STATUS_CONSOLIDADO_FINAL_23FEV_2026.md
    └─ Timeline usa BRT
    └─ Gate 1: 05/03 17:00 BRT

[ ] CHECKLIST_DEPLOYMENT_STAGE1_23FEV.md
    └─ Timeline detalhada em BRT
    └─ Conversões removidas

[ ] COMECE_DEPLOYMENT_AGORA.md
    └─ Instructions em BRT
    └─ Horários locais Brasília

[ ] scripts/DEPLOY_STAGE1_PRODUCAO.sh
    └─ Mensagens em BRT
    └─ Timestamps locais

[ ] scripts/TODO1_LABEL_BACKTEST.py
    └─ Logs em BRT
    └─ 'Data Execução' atualizada

[ ] README.md
    └─ Timeline oficial aponta este documento
    └─ Link para PADRÃO_HORARIOS_BRASILIA.md
```

---

## 🔗 INTEGRAÇÃO CONTÍNUA

**Todos os novos commits devem:**
- Usar BRT em mensagens de deploy
- Timestamps em estruturas de dados: ISO 8601 (ex: `2026-02-23T20:00:00-03:00`)
- Documentos: BRT em legível, ISO em programático

---

**Documento criado:** 23 de Fevereiro de 2026
**Vigência:** Até fim do projeto
**Última revisão:** 23/02 20:00 BRT
**Status:** ✅ PADRÃO OFICIAL

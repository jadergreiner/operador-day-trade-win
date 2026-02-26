# 🚀 SPRINT 2 - ATIVIDADES & PRIORIDADES

**Status:** ✅ **PRONTO PARA EXECUÇÃO**
**Squad:** 8 personas
**Objetivo:** Phase 2 Execution & Deployment (Capital escalation 50k → 100k)
**Format:** Organizado por **Prioridade** (P0 > P1), não por datas

---

## 📊 VISÃO GERAL

```
┌─────────────────────────────────────────────────┐
│        SPRINT 2: PHASE 2 EXECUTION               │
├─────────────────────────────────────────────────┤
│                                                 │
│  3 TASKS PARALELAS:                            │
│  ├─ P0-1: ENG-003 - MT5 REST API               │
│  ├─ P1-1: ML-003 - Feature Analysis            │
│  └─ P0-2: ML-004 - Extended Backtest           │
│           (bloqueado até ENG-003 pronto)       │
│                                                 │
│  GATES CRÍTICOS:                                │
│  ├─ GATE 1: ENG-003 + ML-003 completos         │
│  └─ GATE 2: ML-004 completo + UAT sign-off     │
│                                                 │
│  🚀 GO-LIVE: Quando tudo pronto                │
│     Capital: R$ 50k → R$ 100k (if GATE 2 GO)  │
│                                                 │
└─────────────────────────────────────────────────┘
```

---

## 🎯 TAREFAS (3 Tasks P0)

### Task 1: ENG-003 - MT5 REST API Implementation
**Priority:** P0 (CRÍTICO)
**Lead:** Eng Sr (Backend)
**Squad:** 3 Backend Developers
**Status:** Ready for execution

**O que entregar:**
- FastAPI REST server com 5 endpoints core
- OAuth 2.0 authentication
- Async order queue (RabbitMQ)
- WebSocket real-time positions
- Error handling + retry logic
- 100% unit/integration/E2E tests
- Performance: P95 latency < 200ms

**Critérios de Sucesso (8 ACs):**
- AC-1: Authentication valida credenciais MT5
- AC-2: Token refresh sem re-auth
- AC-3: Orders enviados async (non-blocking)
- AC-4: Retry logic (3x exponential backoff)
- AC-5: Order status tracked real-time
- AC-6: Positions updated < 100ms (WebSocket)
- AC-7: Account balance updated 30s
- AC-8: Healthcheck inclui todas dependencies

---

### Task 2: ML-003 - Feature Importance Analysis
**Priority:** P1 (IMPORTANTE)
**Lead:** ML Expert
**Squad:** ML Expert + Data Scientist
**Status:** Ready for execution

**O que entregar:**
- SHAP values (top 10 features identified)
- Correlation matrix analysis (24×24)
- Drift detection rules (3 rules: mean shift, distribution, correlation)
- Threshold sensitivity analysis
- Production monitoring config
- Detailed reports (20+ pages)

**Critérios de Sucesso (18 ACs):**
- AC-1 through AC-18 covering:
  - Feature importance ranking
  - Correlation pairs (r > 0.8)
  - Drift alert rules
  - Monitoring thresholds
  - Explainability for traders

---

### Task 3: ML-004 - Extended Backtest (252 Trading Days)
**Priority:** P0 (CRÍTICO)
**Lead:** ML Expert
**Dependency:** Espera ENG-003 estar pronto
**Status:** Bloqueado até ENG-003 completo

**O que entregar:**
- 252-day historical backtest (1 year)
- Performance metrics (Sharpe, Win Rate, Drawdown)
- Monthly breakdown + consistency analysis
- Feature importance during trades
- Market regime analysis
- Detailed reports (20+ pages)

**Critérios de Sucesso (GATE 2 - 20 ACs):**
- **AC-10: Sharpe ratio >= 1.0** ✅
- **AC-11: Win rate >= 59%** ✅
- **AC-12: Drawdown < 15%** ✅
- AC-13 through AC-20: Consistency, reports, visualizations

---

## � SEQUÊNCIA DE EXECUÇÃO (SEM DATAS)

### Execução Paralela:
```
┌────────────────────────────────────────────┐
│ Track 1: ENG-003 (Infrastructure)          │
│ ├─ Design & architecture                  │
│ ├─ Authentication layer                   │
│ ├─ Order execution endpoints              │
│ ├─ Position tracking service              │
│ ├─ Error handling & retry logic           │
│ └─ Integration testing                    │
│    WHEN DONE: Unblocks ML-004             │
│                                           │
│ Track 2: ML-003 (Analytics)                │
│ ├─ SHAP values computation                │
│ ├─ Correlation analysis                   │
│ ├─ Drift detection rules                  │
│ ├─ Alert thresholds                       │
│ └─ Monitoring configuration               │
│    NO DEPENDENCIES                        │
│                                           │
│ Track 3: ML-004 (Validation)               │
│ ├─ Wait: ENG-003 complete                 │
│ ├─ Load 252-day data                       │
│ ├─ Run backtest simulation                │
│ ├─ Compute metrics (Sharpe, WR, DD)      │
│ └─ Generate reports                       │
│    GATE 2 DECISION POINT                  │
└────────────────────────────────────────────┘
```

---

## 🎯 GATES & DECISÕES CRÍTICAS

### 🟢 GATE 1: ENG-003 + ML-003 Completos

**Critérios de Aprovação:**
- ✅ ENG-003: 8/8 CA passando
- ✅ ML-003: 18/18 CA passando
- ✅ Integração: API ↔ Modelo testado
- ✅ Desempenho: API P95 latencia < 500ms
- ✅ Revisão código: 2+ revisores aprovados

**Decisão:**
- **GO:** Iniciar ML-004 imediatamente
- **CONDICIONAL GO:** Correções menores (1-2 CA), refazer 1-2 dias
- **NÃO-GO:** Problemas maiores, refazer 3+ dias, retentar GATE 1

---

### 🟢 GATE 2: ML-004 Completo + UAT Pronto

**Critérios de Aprovação (TODOS DEVEM PASSAR):**
- ✅ Taxa de Sharpe >= 1.0
- ✅ Taxa de Vitória >= 59%
- ✅ Redução Máxima < 15%
- ✅ Consistência de redução < 30% std
- ✅ 20/20 CA passando
- ✅ Aprovação UAT do Operador
- ✅ Todos os relatórios aprovados

**Decisão (Ativação de Capital):**
- **GO:** Ativar capital R$ 100k Phase 2
- **CONDICIONAL GO:** Sharpe >= 0.95 ou Taxa >= 58%, mais análise
- **REFAZER:** < 2 critérios atendidos, retornar ao dev
- **NÃO-GO:** Tempo expirado ou < 1 critério, adiar Phase 2

---

## 👥 ALOCAÇÃO DE EQUIPE

| Função | Nome | Horas | Tarefas |
|---------|------|-------|----------|
| **Eng Sr** | Engenheiro Sínior | 48h | ENG-003 (design + liderança) |
| **Dev 1** | Dev Backend | 40h | ENG-003 (Auth + Ordens) |
| **Dev 2** | Dev Backend | 40h | ENG-003 (Posições + WS) |
| **Dev 3** | Dev Backend | 40h | ENG-003 (Fila + retry) |
| **Especialista ML** | ML Lead | 48h | ML-003 + ML-004 |
| **Cientista Dados** | Data Scientist | 40h | ML-003 + ML-004 |
| **Responsável QA** | Test Lead | 32h | Testes + validação |
| **Engenheiro Testes** | Test Engineer | 32h | Automação de testes |
| **DevOps** | DevOps Eng | 16h | Infraestrutura |
| **Total** | 8 personas | 336h | (21 dias × 16 h/dia) |

---

## 📊 MÉTRICAS DE SUCESSO

### Metas Gerais Sprint 2
```
Entrega de Código:
✅ 800 linhas código API
✅ 400 linhas código análise ML
✅ 600 linhas código testes
✅ Total: 1.800 linhas novo

Documentação:
✅ Especificação API (OpenAPI/Swagger)
✅ Relatório importância features (20 páginas)
✅ Relatório backtest estendido (20 páginas)
✅ Config + regras monitoramento

Qualidade:
✅ Cobertura teste unitário 100%
✅ 8/8 testes integração passando
✅ 5/5 testes E2E passando
✅ Teste carga: 100 req/sec sustentado

Testes:
✅ Revisão código: 2+ revisores
✅ Desempenho: P95 < 200ms (API)
✅ Confiabilidade: 99.9% uptime
✅ Segurança: HTTPS + OAuth 2.0
```

### Métricas de Decisão GATE 2
```
VALIDAÇÃO DE BACKTEST:
  Taxa de Sharpe:     >= 1.0     (alvo: retornos ajustados risco)
  Taxa de Vitória:    >= 59%     (alvo: probabilidade lucro)
  Redução Máxima:     < 15%      (alvo: controle risco)
  Consistência:       < 30% std  (alvo: regularidade)

DESEMPENHO ESPERADO:
  Retorno Médio Diário:  +0.25% - 0.35%
  P&L Mensal:            R$ 3.700 - 5.200
  Retorno Anual:         +60% - +88%
  Ajustado Risco:        Sharpe 1.0+ (excelente)
```

---

## ⚠️ RISCOS & MITIGAÇÕES

| Risco | Impacto | Mitigação |
|-------|---------|----------|
| MT5 API instável | P0 | Servidor mock, retry logic, circuit breaker |
| Overfitting do modelo | P0 | Validação out-of-sample, CV incluído |
| Lacunas dados (feriados) | P1 | Validar completude, excluir feriados |
| Degradação desempenho | P1 | Teste carga, alertas monitoramento |
| Expiração token trading | P2 | Auto-refresh, cache longa duração |

---

## 📚 DOCUMENTAÇÃO

Todos os arquivos de especificação estão prontos:

1. **SPRINT2_KICKOFF_DASHBOARD.py** (Executável)
   - Overview, timeline, gates, success criteria
   - Gera SPRINT2_DASHBOARD.json

2. **SPRINT2_TASK_ENG003_MT5_API.py** (Executável)
   - Especificação técnica completa (API spec)
   - 8 acceptance criteria
   - Timeline + risk mitigation

3. **SPRINT2_TASK_ML003_FEATURE_ANALYSIS.py** (Executável)
   - SHAP analysis, correlation, drift detection
   - 18 acceptance criteria
   - Monitoring config

4. **SPRINT2_TASK_ML004_EXTENDED_BACKTEST.py** (Executável)
   - 252-day backtest specification
   - GATE 2 decision criteria
   - 20 acceptance criteria

---

## ✅ CHECKLIST PRÉ-PARTIDA

**Antes de começar:**

- [x] Especificações técnicas finalizadas
- [x] Squad alocado (8 personas)
- [x] Documentação pronta
- [x] Setup repositório Git
- [x] Setup monitoramento/logging
- [x] Ambiente staging pronto
- [x] Dados históricos disponíveis (252 dias)
- [x] Modelo salvo do Sprint 1 (scale_pos_weight=1.476)
- [x] Framework de risco documentado
- [x] Briefing do operador agendado

---

## 🎯 INSIGHTS-CHAVE DO SPRINT 1

**Aplicar em Sprint 2:**

1. **Sintonia do Modelo:** scale_pos_weight=1.476 é ótimo - NÃO MUDAR
2. **Limiar:** 0.30 é bem posicionado - considerar análise sensibilidade
3. **Overfitting:** Gap de 28% é aceitável para finanças - monitorar via CV
4. **Estabilidade CV:** std=0.0233 é excelente - esperar similar no backtest
5. **Testes:** 7/7 testes passando = confiança alta no modelo

---

## 🚀 PRÓXIMOS PASSOS

### Para Começar Agora:

1. **Montagem do Time**
   - Confirmar todas as 8 personas estão disponíveis
   - Briefar sobre atividades (não datas!)
   - Esclarecer critérios CA

2. **Validação do Ambiente**
   - Setup repositório API
   - Dependências instaladas
   - Todos serviços rodando (mock MT5, RabbitMQ, Redis, PG)

3. **Desenvolvimento Começa**
   - ENG-003: Scaffold API + auth
   - ML-003: Carregamento dados + SHAP
   - Primeiros commits

### Checkpoints (Quando Pronto, Sem Datas):

- **Quando ENG-003 pronto:** Revisão GATE 1
- **Quando ML-004 pronto:** Revisão GATE 2 + decisão capital
- **Se GATE 2 GO:** Deployment produção + ativação Phase 2

### Ritual Diário:

- [ ] Standup: 15:00 UTC (15 min)
- [ ] Identificação de bloqueadores
- [ ] Atualização de progresso
- [ ] Próximas prioridades

---

## 📞 CONTATOS & ESCALAÇÃO

| Função | Contato | Escalação |
|---------|---------|--------|
| **Sprint Lead** | Eng Sr | - |
| **Tech Lead (API)** | Eng Sr | CTO |
| **ML Lead** | Especialista ML | Head de Dados |
| **QA Lead** | Responsável QA | Test Manager |
| **Product Owner** | PO | CFO (aprovação capital) |

**Standups:** Diário 15:00 UTC
**Gates:** 05/03 & 10/03 17:00 UTC (revisões formais)
**Escalação:** Imediato se bloqueadores detectados

---

## 🎊 STATUS FINAL

**Sprint 2 está 100% pronto para execução**

- ✅ Especificações técnicas completas
- ✅ Squad alocado (8 personas)
- ✅ Gates bem definidos (GATE 1, GATE 2)
- ✅ Riscos mitigados
- ✅ Documentação síncrona
- ✅ Formato: **Prioridade-Primeiro** (prioridades, não datas)

**Próximo passo:** Kick off quando squad estiver pronto.

---

*Formato: Prioridade-Primeiro (Sem Datas, Baseado em Prioridades)*

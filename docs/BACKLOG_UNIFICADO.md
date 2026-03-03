# Backlog Operacional - Operador Day Trade WIN

**Versão:** 4.0 (Refatorado - Tarefas Independentes de Datas)
**Formato:** Backlog Priorizado de Atividades Entregáveis
**Foco:** Valor de Negócio + Viabilidade Técnica + Zero Dependência Temporal
**Proprietária:** Product Owner em coordenação com Head de Finanças (Mercado Brasil)
**Atualização:** 03/03/2026

⭐ **OBJETIVO FINAL:** Dois operadores autônomos de trading:
- `INICIAR_DIARIOS.bat` - Sistema base (Journais + RL Training)
- `INICIAR_MICRO_TENDENCIA_AUTO_TRADE.bat` - Engine automático execution

---

## 🎯 FILOSOFIA v4.0 - BEM-VINDO!

Bem-vindo ao backlog refatorado. **Aqui não há datas**. Por quê?

✅ **Tarefas Independentes:** Cada uma vale por si mesma (valor entregue imediato)

✅ **Dependencies Lógicas:** Se precisa de outra, é porque funcionalidade depende, não porque calendário diz

✅ **Priorização Clara:** P0 (críticas) → P1 (importantes) → P2 (nice-to-have)

✅ **ROI Transparente:** Cada tarefa avaliada pelo PO + CFO (risco/retorno)

✅ **Execução Flexível:** Comece pelos P0, paralelize P1, séquencie P4 (se necessário)

---

## 👥 Avaliadores (Dupla de Decisão)

| Persona | Foco | Responsabilidade |
|---------|------|------------------|
| **Product Owner** | Missão do negócio, valor entregue, priori zação, viabilidade técnica | GO/NO-GO execução, desbloquear dependências, re-priori zação |
| **Head de Finanças (Brasil)** | ROI, risco capital, escala de deploy, decisões de investimento | ROI validado? Risco aceitável? Capital suficiente? |

---

## 📋 COMO USAR ESTE DOCUMENTO

**Escolha um caminho:**

### 1️⃣ **Começar Agora (Recomendado)**
- Vá a **P0 - CRÍTICAS**
- Selecione P0-1 (ENG-003 API REST)
- Leia: Impacto, Bloqueadores, Entregas, AC
- Execute: 160h, 14 endpoints, 8 AC PASSAR
- Depois desbloqueia tudo

### 2️⃣ **Análise Executiva (CFO/Board)**
- Vá a **P0-2 - GATE 2 (Decisão Capital)**
- Leia: ROI, Risco, Métricas Backtest
- Decide: Ativa R$ 100k Fase 2 ou mantém R$ 50k?

### 3️⃣ **Planejamento Tech (Eng Sr)**
- Vá a **MODELO DE EXECUÇÃO**
- Veja: Dependências Lógicas (SEM datas)
- Paralelize: P0-1 + P1-1 → depois P0-2 → depois P4-1,2,3

---

## 🔴 P0 - CRÍTICAS (Bloqueadores Absolutos)

### P0-1: ENG-003 - API REST MT5 (Infraestrutura Execução)

**Missão:** Construir servidor REST que executa ordens via MT5, gerencia posições, valida risco

**Impacto (PO + CFO):**
- ✅ **ROI:** +R$ 150-250k/mês (automação remove latência manual)
- ✅ **Viabilidade:** 160h realista com 3 devs
- ⚠️ **Risco:** API instável = capital em risco (mitigado: timeout + circuit breaker)
- 🎯 **Bloqueador:** Desbloqueia P0-2, P1-2 até P1-6 (tudo de execução)

**Equipe:** Eng Sr (tech lead) + 3 Dev-Backend

**Entregas (Servidor FastAPI):**
- 14 endpoints (Auth×2, Orders×4, Positions×4, Account×2, Health×2)
- WebSocket tempo real (<100ms posições)
- Cache Redis (30s TTL)
- Fila RabbitMQ async
- Audit trail PostgreSQL (CVM 7 anos)
- Retry 3× exponencial
- Error handling completo

**Acceptance Criteria (8 Testes):**
- [ ] AC-1: Autenticação valida credenciais MT5 (OAuth token)
- [ ] AC-2: Token refresh sem re-auth
- [ ] AC-3: Ordens fila async (não-bloqueante)
- [ ] AC-4: Retry 3× exponencial (1s, 2s, 4s delays)
- [ ] AC-5: Status ordem rastreado tempo real
- [ ] AC-6: Posições atualizam <100ms (WebSocket)
- [ ] AC-7: Saldo conta atualizada 30s
- [ ] AC-8: Healthcheck inclui 4 dependências (MT5, Broker, DB, Cache)

**Testes Necessários:**
- 20+ unitários (Auth, Fila, Cache, Erro)
- 10+ integração (API ↔ mock MT5)
- 5+ performance (carga 500 users, P95 <500ms)
- 2+ revisões código

---

### P0-2: ML-004 - Backtest Validação (12 Meses + GATE 2)

**Missão:** Validar modelo ML com dados reais 252 dias → desbloqueia escala capital Fase 2

**Impacto (PO + CFO):**
- ✅ **ROI:** Validação = confiança para ativar R$ 100k (2× capital)
- ✅ **Viabilidade:** 88h, 2 pessoas, dados já existem
- ⚠️ **Risco:** Backtest com bias = validação falsa (mitigado: walk-forward)
- 🎯 **Bloqueador:** GATE 2 decide: Ativa r$ 100k ou mantém R$ 50k?

**Equipe:** ML Expert + Data Scientist

**Pré-Requisito:** P0-1 completo (precisa de endpoints /orders, /positions)

**Entregas:**
- Backtest 252 dias (1 ano completo trading)
- Métricas: Sharpe, Win Rate, Max Drawdown
- Breakdown P&L mensal (consistência check)
- Mapa calor features (importância durante trades)
- Análise 3 regimes mercado
- Relatório 20+ páginas
- Visualizações (curva patrimônio, drawdown gráfico)

**GATE 2 - Critérios Decisão (BLOQUEADORES):**
```
SE todos 4 PASS:
  ✅ Sharpe ≥ 1.0
  ✅ Win Rate ≥ 59%
  ✅ Max Drawdown < 15%
  ✅ Consistência mensal (σ < 30%)
  
ENTÃO:
  →  ATIVA R$ 100k Fase 2 (2× capital)
  →  DESBLOQUEIA P4-1 Staging Deploy
SENÃO:
  →  MANTÉM R$ 50k Fase 1
  →  REPLAN ML features (volta P1-1)
```

**Acceptance Criteria (20 Testes):**
- [ ] AC-1 until AC-20: Dataset, Features, Lógica Backtest, Métricas, Relatórios, Gate PASS

---

## 🟡 P1 - IMPORTANTES (Não-Bloqueadores, Paralelo P0)

### P1-1: ML-003 - Análise Features & Drift Detection

**Missão:** Explainabilidade ML (SHAP) + detectar quando modelo degrada

**Impacto:** Trader toma decisões informadas, sabe quando confiar/desconfiar do sistema

**Equipe:** ML Expert + Data Scientist

**Entregas:**
- Top 10 features SHAP analysis
- Matriz correlação 24×24
- 3 regras drift (KS test, média drift, correlação change)
- Limiares alerta (Verde/Amarelo/Vermelho)
- Relatório explainabilidade

**AC:** 18/18 PASS

---

### P1-2: Dashboard Ordens Real-Time

**Missão:** CEO/CIO vê TODAS ordens tempo real, rastreia P&L

**Impacto:** Visibilidade = confiança em automação

**Dependência:** P0-1 (endpoints /orders, /positions)

**Equipe:** Eng Sr + 1 Dev-Backend (40h)

**Entregas:**
- Dashboard WebSocket (<100ms update)
- Statu ordem: pendente → enviada → preenchida
- P&L por ordem
- Histórico + filtros
- Export CSV/JSON

**AC:** 8/8 PASS

---

### P1-3 até P1-6: OAuth, RabbitMQ, WebSocket, Position Monitor

Todas com **dependência:** P0-1 (API endpoints disponíveis)

**Status:** Pronto para começar em paralelo assim que P0-1 ✅

---

## 🟢 P2 - MÉDIOS (Independentes, Depois de GATE 2)

Começam quando **GATE 2 aprovado** (P0-2 ✅)

### P2-1: Detection Engine - Padrões Técnicos
### P2-2: RL Training Automation
### P2-3 até P2-7: Vários componentes...

---

## 🔵 P3 - FUTURO (Phase 3+)

Começam quando Phase 2 estável. Não commitir agora.

### P3-1: Production Deployment Setup
### P3-2 até P3-14: Componentes avançados...

---

## 🟣 P4 - PHASE 4: STAGING → UAT → GO-LIVE

**IMPORTANTE:** P4-1, P4-2, P4-3 são **SEQUENCIAIS** (não paralelo)

### P4-1: Staging Deployment

**Pré-Requisito:** GATE 2 PASS (P0-2 ✅)

**Missão:** Deploy production-grade em staging, teste com traders reais

**AC:** 8/8 (Azure resources, tests 25+, load test 500 users, zero critical errors)

---

### P4-2: UAT & Approval

**Pré-Requisito:** P4-1 ✅

**Missão:** Trader aprova signals, CIO aprova security, CFO aprova capital transfer

**AC:** 8/8 (Trader approval, CIO security, CFO capital R$ 50k, zero blockers)

---

### P4-3: Go-Live Production

**Pré-Requisito:** P4-2 ✅

**Missão:** Deploy em produção, inicia capital R$ 50k, primeiro trades reais

**AC:** 8/8 (Environment UP, trading ONLINE, capital transferido, P&L tracking OK)

---

## 📊 MODELO DE EXECUÇÃO (SEM DATAS)

```
┌─ PARALELO (Sem Dependência Temporal):
│
├─ [P0-1] ENG-003 API REST
│  └─ Bloqueador central (todos querem isso)
│
└─ [P1-1] ML-003 Análise Features
   └─ Independente (roda em paralelo com P0-1)


┌─ PRÓXIMO (Aguarda P0-1 Completo):
│
├─ [P1-2, P1-3, P1-4, P1-5, P1-6] Dashboard, OAuth, RabbitMQ, WebSocket, Monitor
│  ├─ Todos dependem de P0-1
│  └─ Todos podem rodar em paralelo entre si
│
└─ [P0-2] ML-004 Backtest Validation
   ├─ Dependência: P0-1
   └─ GATE 2 Decision Point (capital scale)
   

┌─ SEQUENCIAL (Produção):
│
├─ [P4-1] Staging Deploy → GATE 4.1 Check
│  ├─ Precisa: P0-2 ✅ (GATE 2 PASS)
│  └─ Desbloqueia: P4-2
│
├─ [P4-2] UAT & Approval → GATE 4.2 Check
│  ├─ Precisa: P4-1 ✅
│  └─ Desbloqueia: P4-3
│
└─ [P4-3] Go-Live Production
   ├─ Precisa: P4-2 ✅
   └─ Ativa capital R$ 50k
```

**Resumão:** 
- P0 = bloqueadores críticos
- P1 = paralelo após P0-1
- GATE 2 = decide escala capital
- P4 = sequencial (produção rígida)

---

## 💼 ALOCAÇÃO DE RECURSOS

### Equipe Sprint 1 (Paralelo)

| Função | Horas | Tarefas | Status |
|--------|-------|---------|--------|
| Eng Sr | 48h | P0-1 (design + tech lead) | 🟡 Pronto |
| Dev-Backend 1 | 40h | P1-3 OAuth | 🟡 Pronto |
| Dev-Backend 2 | 40h | P1-4 RabbitMQ | 🟡 Pronto |
| Dev-Backend 3 | 40h | P1-5 WebSocket | 🟡 Pronto |
| Dev-Backend 4 | 40h | P1-2 Dashboard | 🟡 Pronto |
| ML Expert | 48h | P1-1 + P0-2 | 🟡 Pronto |
| Data Scientist | 40h | P1-1 + P0-2 | 🟡 Pronto |
| QA Lead | 32h | Estratégia teste | 🟡 Pronto |
| QA Engenheiro | 32h | Automação teste | 🟡 Pronto |
| DevOps | 20h | Ambiente + CI/CD | 🟡 Pronto |
| Tech Writer | 15h | Documentação | 🟡 Pronto |

**Total:** 395h | **Período:** Quando começar (0 datas fixas)

---

## ⚡ GATES & DECISÕES

### GATE 1: P0-1 + P1-1 COMPLETADOS

**Quem:** CTO + Head Finanças + PO

**Decisão:** GO/NO-GO Phase 2?

**Critérios:**
- ✅ P0-1: 8/8 AC PASS
- ✅ P1-1: 18/18 AC PASS
- ✅ Latência P95 < 500ms validado
- ✅ Testes E2E executados
- ✅ Código revisado

---

### GATE 2: P0-2 COMPLETADO (★ CRÍTICA PARA CAPITAL ★)

**Quem:** CFO + Board

**Decisão:** Ativa R$ 100k (Fase 2) ou mantém R$ 50k?

**Critérios (Bloqueadores):**
- ✅ Sharpe ≥ 1.0
- ✅ Win Rate ≥ 59%
- ✅ Max Drawdown < 15%
- ✅ Consistência σ mensal < 30%

**Ação:**
- SE PASS: R$ 100k liberado → P4-1 começa
- SE FAIL: Replan ML, tenta novamente

---

### GATE 4.1: P4-1 COMPLETADO (Staging Readiness)

**Quem:** CTO + Eng Sr + QA

**Decisão:** Staging pronto para UAT?

**Critérios:**
- ✅ 8/8 recursos Azure healthy
- ✅ 25+ tests PASS
- ✅ Load 500 users: P95 < 2s
- ✅ Zero critical errors

---

### GATE 4.2: P4-2 COMPLETADO (Go-Live Ready)

**Quem:** Trader + CIO + CFO (3 sign-offs obrigatórios)

**Decisão:** Go-live produção?

**Critérios:**
- ✅ Trader APROVA (signal accuracy OK)
- ✅ CIO APROVA (security posture OK)
- ✅ CFO APROVA (capital R$ 50k transferido)
- ✅ Zero blocking issues

---

## 📚 DOCUMENTAÇÃO COMPLEMENTAR

**Leitura Obrigatória (Antes de Iniciar):**
1. [ARCHITECTURE.md](ARCHITECTURE.md) - Vision 7 camadas
2. [CODING_STANDARDS.md](CODING_STANDARDS.md) - SOLID + DDD mandatory
3. [REGRAS_NEGOCIO.md](REGRAS_NEGOCIO.md) - 6 regras críticas P0

**Referência Técnica:**
4. [ADRs.md](ADRs.md) - 7 decisões arquiteturais
5. [DATA_MODELS.md](DATA_MODELS.md) - Schema detalhado

---

## ✅ PRÉ-REQUISITOS PARA COMEÇAR

Valide AGORA:

- [ ] Python 3.11+
- [ ] Docker (para PostgreSQL, Redis, RabbitMQ)
- [ ] Git com branches (feature/ pattern)
- [ ] Editor VS Code + extensions Python
- [ ] Acesso MT5 (paper/live)
- [ ] Slack configurado (notificações CI/CD)
- [ ] Jira board criado (rastreamento)

---

## 🚀 PRÓXIMOS PASSOS (Comece AGORA!)

### **PO / Eng Sr - DECISÃO 1:**
```
1. Leia esta seção até P1-6
2. Decida: Começamos por P0-1 hojje?
   SIM? → Aloque 3 devs, start tech design
   NÃO? → Identifique bloqueador
```

### **CFO / Head Finanças - PREPARAÇÃO:**
```
1. Leia P0-2 (GATE 2 criteria)
2. Prepare aprovação capital (R$ 50k inicial)
3. Identifique limite risco (drawdown máximo?)
```

### **ML Expert - PARALELO P0-1:**
```
1. Comece P1-1 (Análise Features) AGORA
2. Não precisa esperar P0-1
3. Seu código dos P1-1 alimenta P0-2
```

---

## 📞 ESCALATION

| Questão | Escalate Para |
|---------|---------------|
| P0-1 blocker técnico | CTO |
| ML metrics off target | Head Data |
| GATE 1 FAIL | Board |
| GATE 2 FAIL | Board + CFO |
| P4-1 falha | CTO + DevOps lead |
| P4-2 trader rejeita | CTO + CFO |
| Go-live issue | CTO + CEO |

---

**Versão Final:** v4.0 Refatorada
**Data Atualização:** 03/03/2026
**Status:** ✅ Pronto para Execução
**Próxima Revisão:** Quando GATE 1 PASS ou quando houver mudanças estratégicas


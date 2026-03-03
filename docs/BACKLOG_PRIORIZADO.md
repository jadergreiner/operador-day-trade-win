# Backlog Priorizado - Operador Day Trade WIN

**Versão:** 3.1
**Formato:** Tarefas Entregáveis Independentes
**Foco:** Valor de Negócio + Viabilidade Técnica
**Status:** Pronto para Execução

---

## 👥 Avaliação Dupla - Personas Decisoras

- **Product Owner (PO):** Alinhamento com necessidades do negócio, user stories, priorização
- **Head de Finanças (CFO):** ROI, risco operacional, capital allocation, gates de decisão

> **Como Usar:** Cada tarefa é **independentemente entregável**. Prioridades são absolutas: P0 > P1 > P2 > P3 > P4. Comece sempre por P0.

---

## 📋 Padrões de Desenvolvimento Obrigatórios

Todos os desenvolvedores DEVEM cumprir:
- [ARCHITECTURE.md](ARCHITECTURE.md) - Estrutura 7-camadas
- [CODING_STANDARDS.md](CODING_STANDARDS.md) - SOLID, DDD, Clean Code
- [REGRAS_NEGOCIO.md](REGRAS_NEGOCIO.md) - 6 regras críticas P0
- 100% type hints (mypy --strict)
- Testes: unitário + integração + E2E

---

## ✅ P0 - CRÍTICAS (Bloqueadores de Valor)

Tarefas que definem caminho crítico. Sem estas, nada avança.

### P0-1: ENG-003 API REST MT5 - Infraestrutura de Execução

**Impacto de Negócio (PO + Head Finanças):**
- **ROI:** Habilita trading automático + reduz latência manual (2-5 seg → <200ms)
- **Risco Operacional:** API instável = falha de execução = drawdown capital
  Mitigação: timeout + circuit breaker + retry exponencial
- **Bloqueador para:** P0-2, P1-2, P1-3, P1-4, P1-5, P1-6, P1-11, P1-12
- **Estimativa:** 160h
- **Equipe:** Eng Sr (lead) + 3 Dev-Backend

**Entregas Esperadas:**
- Servidor FastAPI REST (async, alta performance)
- 14 endpoints REST (Auth, Ordens, Posições, Conta, Health)
- Autenticação OAuth 2.0 (token MT5-based)
- Fila async RabbitMQ (processamento ordens)
- WebSocket tempo real (<100ms atualização posições)
- Cache Redis (TTL 30s para posições/conta)
- Audit trail PostgreSQL (todas operações)
- Tratamento erros + retry logic (3× exponencial)
- Cobertura 100% testes (unitário/integração/E2E)
- Performance: P95 < 200ms (ordem), P95 < 100ms (WebSocket)

**Critérios de Aceite (8 - todos DEVEM passar):**
- [ ] CA-1: Autenticação valida credenciais MT5
- [ ] CA-2: Token JWT refresh sem re-auth
- [ ] CA-3: Ordens enviadas async (não-bloqueante)
- [ ] CA-4: Retry logic 3× exponencial funcionando
- [ ] CA-5: Status ordem rastreado tempo real
- [ ] CA-6: Posições atualizadas <100ms via WebSocket
- [ ] CA-7: Saldo conta atualizado a cada 30s
- [ ] CA-8: Health check inclui todas dependências

**Testes Necessários:**
- 20+ testes unitários (Auth, Fila, Cache, Erros)
- 10+ testes integração (API ↔ mock MT5)
- 5+ testes desempenho (carga, estresse, failover)
- Revisão código: mínimo 2 revisores

**Success Criteria:**
- ✅ 8/8 CA passando
- ✅ P95 < 200ms verificado
- ✅ Todos testes passando (35+)
- ✅ Código revisado + aprovado

---

### P0-2: ML-004 Backtest Validação Estendida (12 Meses)

**Impacto de Negócio (PO + Head Finanças):**
- **ROI:** Validação modelo com dados reais = confiança para ativar R$ 100k+ (Fase 2)
- **Risco Técnico:** Backtest com look-ahead bias = validação falsa = capital perdido
  Mitigação: walk-forward validation, purging, embargo 60min
- **Bloqueador para:** P4-1 (staging deployment), decisão capital Fase 2
- **Pré-requisito:** P0-1 completo
- **Estimativa:** 88h
- **Equipe:** ML Expert + Data Scientist

**Entregas Esperadas:**
- Backtest histórico 252 dias (1 ano completo)
- Métricas desempenho: Sharpe, Taxa Vitória, Redução Máxima
- Breakdown P&L mensal + análise consistência
- Mapa importância features (durante negociações)
- Análise regime mercado (3 regimes identificados)
- Análise padrões sazonais
- Relatório detalhado 20+ páginas
- Visualização curva patrimônio
- Validação integridade dados (zero leakage)

**Critérios de Decisão de Capital (DEVE PASSAR todos 4):**
- ✅ Razão Sharpe ≥ 1.0
- ✅ Taxa Vitória ≥ 59%
- ✅ Redução Máxima < 15%
- ✅ Consistência < 30% std (mensal)

**Resultado Esperado (após passar gates):**
- ✅ Ativar R$ 100k Capital Fase 2
- ✅ Aprovação CFO + CTO para staging
-✅ Confiança trader implementação

---

## 🟡 P1 - IMPORTANTES (Suporte a P0)

Tarefas que habilitam infraestrutura P0. Muitas rodam em paralelo com P0.

### P1-1: ML-003 Análise Features & Drift Detection

**Impacto de Negócio (PO + Head Finanças):**
- **ROI:** Explainabilidade ML = trader toma decisões informadas = risco reduzido
- **Risco Operacional:** Modelo drift não-detectado = execuções ruins sem awareness
  Mitigação: SHAP analysis + 3 drift rules + limiares alerta
- **Independente de:** P0-1 (pode começar em paralelo)
- **Estimativa:** 88h
- **Equipe:** ML Expert + Data Scientist

**Entregas Esperadas:**
- Valores SHAP (top 10 features ordenadas)
- Mapa correlação 24×24
- 3 regras detecção drift (média, KS test, correlação delta)
- Limiares alerta (Verde/Amarelo/Laranja/Vermelho)
- Análise sensibilidade limiar (±0.05)
- Config monitoramento produção
- Explainabilidade traders (decision trees, IF-THEN)
- Relatório 20+ páginas

**Critérios de Aceite (6 - todos DEVEM passar):**
- [ ] CA-1: Análise SHAP completa (top 10 features)
- [ ] CA-2: Matriz correlação 24×24 gerada
- [ ] CA-3: 3 regras drift configuradas
- [ ] CA-4: Limiares alerta validados (4 cores)
- [ ] CA-5: Análise sensibilidade feita (±0.05)
- [ ] CA-6: Config monitoramento pronta para produção

---

### P1-2: Dashboard Ordens Real-Time

**Impacto de Negócio (PO + Head Finanças):**
- **ROI:** Visibilidade tempo real = trader monitora automação = confiança operação
- **Risco:** CEO/CIO sem visibility = perda confiança no sistema
  Mitigação: audit trail completo, timestamp em tudo
- **Dependência:** P0-1 (endpoints /orders, /positions)
- **Estimativa:** 40h
- **Equipe:** Eng Sr + 1 Dev-Backend

**Entregas Esperadas:**
- Dashboard integrado mostrando todas ordens real-time
- WebSocket integration (<100ms atualização)
- Status ordem: pendente → enviada → preenchida
- Preço entrada, saída, lucro/prejuízo por ordem
- Tempo execução por ordem
- Histórico completo com audit trail
- Filtros (símbolo, status, período, ticket)
- Relatórios exportáveis (CSV, JSON)
- UX responsivo (desktop + mobile)
- Alertas mudança status

**Critérios de Aceite (8):**
- [ ] CA-1: Dashboard exibe 100% ordens (ativo + histórico)
- [ ] CA-2: Updates via WebSocket (<100ms)
- [ ] CA-3: Filtros funcionando (5 tipos)
- [ ] CA-4: Audit trail completo (timestamp, user, ação)
- [ ] CA-5: Relatórios CSV/JSON exportáveis
- [ ] CA-6: UX responsivo (tested em mobile)
- [ ] CA-7: Histórico persistente em PostgreSQL
- [ ] CA-8: Alertas status mudança funcionando

---

### P1-3: Autenticação OAuth 2.0 JWT

**Impacto de Negócio (PO + Head Finanças):**
- **ROI:** Autenticação segura = compliance CVM/B3 (obrigatório produção)
- **Risco:** Sem autenticação = risco regulatório + dados expostos + auditoria falha
  Mitigação: bcrypt hashing + rate limiting + audit logging
- **Dependência:** P0-1 (mesmo servidor FastAPI)
- **Estimativa:** 40h
- **Equipe:** 2 Dev-Backend

**Entregas Esperadas:**
- Login OAuth 2.0 (email/password)
- Token JWT (8h validade)
- Refresh token (sem logout necessário)
- Password hashing (bcrypt 10+ rounds)
- Rate limiting (10 tentativas/5min)
- Logout revoga token Redis
- Session management (múltiplos devices)
- Audit logging (login/logout/refresh com timestamp)

**Critérios de Aceite (8):**
- [ ] CA-1: Login POST /auth/login retorna JWT
- [ ] CA-2: JWT com claims + 8h validade
- [ ] CA-3: Refresh token POST /auth/refresh-token
- [ ] CA-4: Password hashing bcrypt (10+ rounds)
- [ ] CA-5: Rate limiting 10/5min funcionando
- [ ] CA-6: Logout revoga token em Redis
- [ ] CA-7: Multi-device support (mesmo user, múltiplos tokens)
- [ ] CA-8: Audit trail logging completo

---

### P1-4: Fila Async RabbitMQ

**Impacto de Negócio (PO + Head Finanças):**
- **ROI:** Async orders = API não bloqueia = trader pode cancelar rápido
- **Risco:** Síncrono = timeout = ordem perdida
  Mitigação: DLQ + retry 3× + idempotência garantida
- **Dependência:** P0-1 (no mesmo servidor/infraestrutura)
- **Estimativa:** 40h
- **Equipe:** 2 Dev-Backend

**Entregas Esperadas:**
- Producer async (envio fila)
- Consumer sequential (1 ordem por vez)
- QoS = 1 (one at a time)
- Message acknowledgment (manual)
- Dead letter queue (DLQ) routing
- Error handler + audit trail
- Health check endpoint
- Queue depth monitoring
- Retry logic 3× exponencial
- Cobertura 100% testes

**Critérios de Aceite (8):**
- [ ] CA-1: Producer envio async (não-bloqueante)
- [ ] CA-2: Consumer processa sequencial (1 de cada vez)
- [ ] CA-3: QoS = 1 configurado e funcionando
- [ ] CA-4: Acknowledgment manual após sucesso
- [ ] CA-5: DLQ routing para falhas finais
- [ ] CA-6: Health check endpoint /health/queue OK
- [ ] CA-7: Monitoramento queue depth ativo
- [ ] CA-8: Retry 3× com backoff exponencial (1s, 2s, 4s)

---

### P1-5: WebSocket Position Monitoring

**Impacto:**
- **ROI:** Latência <100ms = trader reage rápido
- **Risco:** Dados stale = decisões informadas ruins
  Mitigação: heartbeat 30s, auto-reconnect, zero message loss
- **Dependência:** P0-1
- **Estimativa:** 40h
- **Equipe:** 1 Dev-Backend

**Entregas:**
- WebSocket endpoint posições tempo real
- Heartbeat 30s (ping/pong)
- Auto-disconnect missed heartbeats (após 90s)
- Reconnection logic automática
- Message format OHLCV + Orders
- JWT validation por mensagem
- Suporta 500+ conexões simultâneas
- Teste carga + estresse
- P95 latência <100ms
- Graceful disconnect

**Critérios de Aceite (6):**
- [ ] CA-1: Conexão persiste >99.5% uptime
- [ ] CA-2: P95 latência <100ms
- [ ] CA-3: 500+ conexões simultâneas suportadas
- [ ] CA-4: Zero message loss
- [ ] CA-5: Graceful disconnect sem perda dados
- [ ] CA-6: Heartbeat 30s ativo + auto-reconnect

---

### P1-6: Position Monitoring Automático

**Impacto:**
- **ROI:** SL/TP automático = nenhuma posição descoberta
- **Risco:** Esquecimento = grandes perdas acidentais
  Mitigação: trailing stop + alertas + log completo
- **Dependência:** P0-1
- **Estimativa:** 32h
- **Equipe:** 1 Dev-Backend

**Entregas:**
- Monitoramento posições abertas tempo real
- SL/TP automático na abertura
- Cálculo P&L em tempo real
- Stop loss condicional (preço ou tempo)
- Take profit condicional
- Trailing stop opcional (protege lucros)
- Alertas quando hit SL/TP
- Histórico posições fechadas
- Cobertura 100% testes

**Critérios de Aceite (6):**
- [ ] CA-1: Posições abertas monitoradas
- [ ] CA-2: SL/TP automático na abertura
- [ ] CA-3: P&L tempo real (atualizado a cada candle)
- [ ] CA-4: Stop loss condicional (preço/tempo)
- [ ] CA-5: Trailing stop opcional
- [ ] CA-6: Alertas hit SL/TP enviados

---

### P1-7: S2-6 Analytics Integration - Tests & Batch

**Impacto:**
- **ROI:** Validação integração = confiança antes de produção
- **Risco:** Integração falha = trading parado em produção
  Mitigação: E2E tests + batch processing + validação 100%
- **Dependência:** P1-1 (análise básica completa)
- **Estimativa:** 32h
- **Equipe:** Eng Sr + ML Expert

**Entregas:**
- Suite E2E testes (`test_agente_s2_6_integration.py`)
- Batch processing para backtest S2-6
- Dashboard real-time (Grafana/Streamlit)
- Validação sincronização (100% antes go-live)
- Monitoramento stats (win rate, sharpe, drawdown)

**Critérios de Aceite (6):**
- [ ] CA-1: Testes E2E implementados (10+ testes)
- [ ] CA-2: Todos testes passam 100% (10/10)
- [ ] CA-3: Batch processing pronto e testado
- [ ] CA-4: Dashboard stats tempo real
- [ ] CA-5: Latência integração <500ms
- [ ] CA-6: Sincronização validada 100%

---

### P1-8: Sistema de Alertas - Testes & Deploy

**Impacto:**
- **ROI:** Alertas confiáveis = nenhuma oportunidade perdida
- **Risco:** Alertas perdidos = trader não sabe oportunidades
  Mitigação: webhook + retry + fallback SMS
- **Dependência:** Nenhuma (paralelo)
- **Estimativa:** 40h
- **Equipe:** Dev-Backend + QA

**Entregas:**
- Testes unitários Sistema Alertas (8 testes)
- Testes integração WebSocket/Email/SMS (3 testes)
- Validação latência P95 <30s
- Config para v1.1.1+ (Produção)
- Setup CI/CD deployment contínuo
- Monitoramento alertas sistema

**Critérios de Aceite (7):**
- [ ] CA-1: 8 testes unitários PASS
- [ ] CA-2: 3 testes integração PASS
- [ ] CA-3: Latência P95 <30s validada
- [ ] CA-4: Taxa captura ≥85%
- [ ] CA-5: False positive <10%
- [ ] CA-6: Taxa entrega >98%
- [ ] CA-7: Deployment v1.1.1+ pronto

---

### P1-9: Trade Sync Verification (TradeSyncVerifier)

**Impacto:**
- **ROI:** Reconciliação MT5 ↔ SQLite = auditoria CVM/B3 completa
- **Risco:** Mismatch trades = perdas não-localizadas + auditoria falha
  Mitigação: daily reconciliation + alertas + DLQ
- **Dependência:** P0-1 (API MT5), P1-2 (persistência)
- **Estimativa:** 10h
- **Equipe:** 1 Dev-Backend

**Entregas:**
- TradeSyncVerifier class (validação 1:1 MT5 ↔ SQLite)
- Daily reconciliation job
- Comparação hash trades
- Reportar missing trades
- Reportar mismatches (entry price, etc)
- Alert system discrepâncias
- TradeSyncReport geração
- Discrepancy log persistência

**Critérios de Aceite (6):**
- [ ] CA-1: TradeSyncVerifier implementado
- [ ] CA-2: Daily job agendado
- [ ] CA-3: Comparação hash OK
- [ ] CA-4: Missing trades detectados
- [ ] CA-5: Mismatches reportados
- [ ] CA-6: 3 integration tests PASS

---

### P1-10: RL Feedback System - Resultados Reais

**Impacto:**
- **ROI:** Feedback RL = modelo melhora com dados reais
- **Risco:** RL sem feedback = modelo não evolui
  Mitigação: historical outcome tracking + A/B testing
- **Dependência:** P0-2 (persistência trades)
- **Estimativa:** 15h
- **Equipe:** ML Expert + Dev-Backend

**Entregas:**
- TradeClosedEvent listener
- Cálculo PnL real vs previsão
- Feedback loop para RL model
- RL model update pipeline
- Retraining com novos outcomes
- Version control modelos
- Historical outcome tracking
- A/B testing preparado

**Critérios de Aceite (6):**
- [ ] CA-1: TradeClosedEvent listener implementado
- [ ] CA-2: PnL cálculo validado
- [ ] CA-3: RL model update pipeline pronto
- [ ] CA-4: Retraining automático funciona
- [ ] CA-5: Historical tracking completo
- [ ] CA-6: 4 integration tests PASS

---

## 🟢 P2 - FUTURO (Próximas Prioridades)

Tarefas para depois de P0-P1 validados em produção.

### P2-1: Performance Benchmarking

**Estimativa:** 40h | **Equipe:** Eng Sr + QA

Entregas:
- Load testing (carga, estresse)
- Latency profiling (P95, P99)
- Memory profiling
- Database optimization
- Cache hit ratio análise
- Escalabilidade validação

---

### P2-2: Monitoring & Observability

**Estimativa:** 20h | **Equipe:** DevOps + Dev-Backend

Entregas:
- Prometheus metrics export
- Grafana dashboards
- PagerDuty integration
- Logs centralizados

---

### P2-3: Staging Deployment

**Estimativa:** 32h | **Equipe:** DevOps

Entregas:
- Ambiente staging (idêntico produção)
- CI/CD pipeline
- Automated testing pre-deploy
- Health checks
- Rollback procedures

---

## 📈 P3 - ANÁLISES DE MERCADO

Históricos, compilados para referência.

---

## 🚀 P4 - STAGING & GO-LIVE

### P4-1: Staging Deployment (Após P0-2 PASS todos gates)

**Estimativa:** 40h | **Equipe:** Eng Sr + DevOps + QA

Pré-requisitos:
- P0-1 ✅ completo
- P0-2 ✅ PASS todos 4 critérios (Sharpe ≥1.0, Win ≥59%, Drawdown <15%, Consistência <30%)
- P1-2, P1-3, P1-4, P1-5, P1-6 ✅ completo

Entregas:
- Azure Resource Group (8 recursos)
- App Service + PostgreSQL + Redis + Key Vault
- Code deployment (FastAPI + WebSocket)
- Integration testing (25+ testes)
- Load testing (3 cenários)
- Monitoring + alerting
- Backup strategy

Critérios de Aceite (8 - TODOS DEVEM PASSAR):
- [ ] CA-1: 8/8 recursos Azure healthy
- [ ] CA-2: Health check endpoint PASS
- [ ] CA-3: 25+ testes integração PASS
- [ ] CA-4: Load test 500 users: P95 <2s
- [ ] CA-5: Zero critical errors logs
- [ ] CA-6: Auto-scaling configurado
- [ ] CA-7: Daily backups automated
- [ ] CA-8: AppInsights monitoring active

Gates para prosseguir a P4-2:
- ✅ Todos 8 CA passando
- ✅ P95 latência <200ms validado
- ✅ Uptime >99.9% em staging
- ✅ CTO pre-flight approval

---

### P4-2: UAT & Approval (Após P4-1 PASS)

**Estimativa:** 24h | **Equipe:** Trader + CIO + CFO

Entregas:
- Trader acceptance testing (6 test cases)
- CIO security validation (12 security points)
- CFO financial approval (capital authorization)
- Sign-off documents (3: Trader, CIO, CFO)
- Final readiness checklist (50+ items)

Critérios de Aceite (8 - TODOS DEVEM PASSAR):
- [ ] CA-1: Trader APROVA (signal accuracy ≥80%)
- [ ] CA-2: CIO APROVA (security posture OK)
- [ ] CA-3: CFO APROVA (capital R$ 50k authorized)
- [ ] CA-4: Zero blocking issues reportados
- [ ] CA-5: Todos 3 sign-offs assinados
- [ ] CA-6: Risk framework validado
- [ ] CA-7: Override procedures testado 100%
- [ ] CA-8: 24/7 support contacts confirmado

Gates para Go-Live:
- ✅ Todos 8 CA passando
- ✅ 3 sign-offs autorizados (Trader/CIO/CFO)
- ✅ Zero critical findings security
- ✅ Capital R$ 50k disponível transferência

---

### P4-3: Go-Live Production (Após P4-2 PASS)

**Estimativa:** 8h (durante go-live) | **Equipe:** Eng Sr + DevOps + Trader

Go-Live Time: Determinado após P4-2 aprovação

Entregas:
- Production infrastructure deployment
- Cutover execution (staging → production)
- Capital transfer R$ 50k
- 24/7 monitoring + alerting
- Post-go-live validation (1h)

Critérios de Aceite (8 - TODOS DEVEM PASSAR):
- [ ] CA-1: Production environment UP
- [ ] CA-2: Trading system ONLINE
- [ ] CA-3: Capital R$ 50k transferido
- [ ] CA-4: Primeiros 5+ trades executados
- [ ] CA-5: P&L tracking funcionando
- [ ] CA-6: Alerts configurados
- [ ] CA-7: Support team briefed
- [ ] CA-8: Post-go-live validation PASS

---

## ✅ Tarefas Complementares Já Implementadas

### Diários Automáticos (Sistema Feedback)

**Status:** ✅ Implementado | **Código:** scripts/start_automated_journals.py

Sistema gera automaticamente dois tipos de diário durante pregão:
1. Diário Trading Storytelling (15 min)
2. Diário Reflexão IA (10 min)

**Uso:**
```bash
python scripts/start_automated_journals.py
INICIAR_DIARIOS.bat
```

---

### Persistence Fix (Auditoria)

**Status:** ✅ Implementado

Componentes:
- TransactionLogService (append-only log)
- MT5SynchronizationService (sincronização)
- Recovery script (retroativa 7 dias)

**Uso:**
```bash
python scripts/recovery_and_audit.py
```

---

## 📊 Modelo de Execução Paralelizado

```
FASE 1: P0 + P1 Paralelos (Início)
├─ P0-1 ENG-003         [BLOQUEADOR CENTRAL]
│  └─ Desbloqueia: P0-2, P1-2, P1-3, P1-4, P1-5, P1-6
├─ P1-1 ML-003          [PARALELO - sem depend P0]
├─ P1-7 S2-6 Tests      [APÓS P1-1]
├─ P1-8 Alertas         [PARALELO]
├─ P1-9 TradeSyncVerifier [APÓS P0-1]
└─ P1-10 RL Feedback    [APÓS P0-2]

FASE 2: P0-2 Validação (Após P0-1)
└─ P0-2 ML-004 Backtest [BLOQUEADOR CAPITAL]
   └─ Desbloqueia: P4-1 (Staging)

FASE 3: P2 + P3 Otimizações (Após P0-P1)
├─ P2-1 Performance
├─ P2-2 Monitoring
└─ P2-3 Staging

FASE 4: Go-Live (Após P0-2 PASS)
├─ P4-1 Staging Deploy     [SEQUENCIAL]
├─ P4-2 UAT & Approval     [SEQUENCIAL]
└─ P4-3 Production Go-Live [SEQUENCIAL]

REGRA CRÍTICA: P0-2 backtest DEVE PASSAR todos 4 gates:
  ✅ Sharpe ≥ 1.0
  ✅ Win-rate ≥ 59%
  ✅ Drawdown < 15%
  ✅ Consistência < 30% std (mensal)
Sem isto: BLOQUEADO para produção
```

---

## 🎯 Alinhamento PO + Head Finanças

| Aspecto | PO | Head Finanças |
|---------|----|----|
| **P0-1 ROI** | Automação = velocidade | Execução = sem slippage |
| **P0-2 Gate** | Modelo robusto | Capital liberado (R$ 100k) |
| **P1-1 Drift** | Trader informado | Risco mitigado |
| **P1-2 Dashboard** | Visibilidade = confiança | Auditoria CVM/B3 |
| **P4-1,2,3** | Features = LIVE | Capital = gerido |

---

## 📞 Próximos Passos

1. Selecione P0-1 ou P1-1 para começar
2. Aloque equipe conforme tabela
3. Execute critérios de aceite
4.  Marque como ✅ quando completo
5. Prossiga para próxima tarefa (respeitando dependências)

**Perguntas?** Consulte ARCHITECTURE.md ou CODING_STANDARDS.md.


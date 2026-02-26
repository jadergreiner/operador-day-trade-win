# 🚀 EXECUÇÃO DE TODAS AS 10 ATIVIDADES - Sprint 2

**Status:** 🟢 **PLANO DE EXECUÇÃO PARALELO COMPLETO**
**Framework:** {{prompts\executa_task.md}} aplicado a cada ATI
**Squad:** 11 personas | **356 horas** | **3 tracks paralelos**
**Timeline:** 6-8 semanas | **Gates:** 2 imóveis

---

## 📌 ESTRUTURA DE EXECUÇÃO

Cada atividade segue o framework **executa_task.md** com 4 etapas:

1. **Design Review** - Validação de arquitetura
2. **Development** - Implementação com TDD
3. **Testing** - AC validation + coverage >90%
4. **Integration** - E2E testing + deployment

---

# 🎯 ATI-1: DASHBOARD DE ORDENS EM TEMPO REAL

## 📌 Contexto

**Prioridade:** 🔴 **P0-CRÍTICO**
**Lead:** Eng Sr (40h)
**Squad:** Dev-Backend-3 (WebSocket), QA Manager (32h), Test Automation (16h)
**Duração:** ~4-5 semanas
**Valor:** ⭐⭐⭐⭐⭐ Visibilidade 100% das ordens ao operador

## 👥 Alocação de Personas

```
Lead: Eng Sr (ID #3) - 40h
├─ Especialidade: Arquitetura SystemsSTL + Dashboard
├─ Responsabilidades:
│  ├─ Design arquitetura frontend (Vue.js + WebSocket)
│  ├─ API endpoints (/orders/list, /orders/{id}, etc)
│  ├─ Persistência (PostgreSQL audit trail)
│  ├─ Code review + escalação
│  └─ Performance validation (<100ms WebSocket)
│
Suporte: Dev-Backend-3 (ID #....) - 40h
├─ Especialidade: Frontend + WebSocket integração
├─ Responsabilidades:
│  ├─ Implementar componentes Vue.js (OrderTable, Status)
│  ├─ WebSocket client (real-time updates)
│  ├─ Unit tests (8+ testes frontend)
│  └─ UX responsivo (mobile + desktop)
│
Suporte: QA Manager (ID #12) - 32h
├─ Especialidade: QA Strategy + Test Automation
├─ Responsabilidades:
│  ├─ Test plan (unit + integration + E2E)
│  ├─ Fixture design (mock orders, WebSocket)
│  ├─ AC validation checklist
│  └─ Coverage >95% target
│
Suporte: Test Automation Engineer (..) - 16h
├─ Especialidade: E2E Testing + Sellenium/Playwright
├─ Responsabilidades:
│  ├─ E2E tests (load orders, filter, export)
│  ├─ Performance tests (latency <100ms)
│  └─ Regression testing
```

## 🎯 Acceptance Criteria (AC)

```
1. [ ] AC-1: Dashboard exibe 100% das ordens
   - Load 50+ ordens da DB
   - Verificar totalização (pendentes + executadas)
   - Tests: test_dashboard_load_orders

2. [ ] AC-2: Atualização real-time via WebSocket
   - Latência <100ms (P95)
   - Suporte múltiplas conexões
   - Tests: test_websocket_latency

3. [ ] AC-3: Filtros por símbolo, status, período
   - Filtro por símbolo (WIN$N, PETR4, etc)
   - Filtro por status (pendente, executada, cancelada)
   - Filtro por data range
   - Tests: test_dashboard_filtering (5 tipos)

4. [ ] AC-4: Audit trail completo
   - Cada ação registrada (criação, execução, mudança)
   - Timestamp preciso
   - User attribution
   - Tests: test_audit_trail_complete

5. [ ] AC-5: Relatórios exportáveis
   - CSV export (Excel compatible)
   - JSON export (structured data)
   - PDF export (printable)
   - Tests: test_export_formats

6. [ ] AC-6: UX responsivo
   - Desktop: 1920x1080+
   - Tablet: 768x1024
   - Mobile: 375x667
   - Tests: test_responsive_design

7. [ ] AC-7: Persistência em PostgreSQL
   - Histórico completo
   - Recovery após crash
   - ACID compliance
   - Tests: test_persistence_recovery

8. [ ] AC-8: Alertas de mudança
   - Notificação quando status muda
   - Visual highlight
   - Sound notification (opcional)
   - Tests: test_alert_notifications
```

## 🧪 Testes Especificados

```python
# tests/test_dashboard_orders.py

class TestDashboardLoad:
    def test_dashboard_load_orders(self):
        # Load 50+ ordens
        # Verificar render correto
        # Assert todas ordensvisíveis
        pass

    def test_dashboard_empty_state(self):
        # Load 0 ordens
        # Verificar mensagem "Nenhuma ordem"
        pass

class TestWebSocket:
    def test_websocket_connect(self):
        # Connect ao /ws/orders
        # Verificar handshake
        pass

    def test_websocket_update_latency(self):
        # Send 100 updates
        # Medir latência P95
        # Assert <100ms
        pass

    def test_websocket_disconnect_reconnect(self):
        # Desconectar
        # Reconectar automático
        # Resync de dados
        pass

class TestFiltering:
    def test_filter_by_symbol(self):
        # Load ordens variadas
        # Filter por WIN$N
        # Verificar resultado
        pass

    # ... 4 testes adicionais

class TestExport:
    def test_export_csv(self):
        # Export 50 ordens
        # Verificar CSV format
        # Validar headers + data
        pass

    # ... 2 testes adicionais

class TestAudit:
    def test_audit_trail_complete(self):
        # Create order
        # Modify status
        # Verificar todas ações em audit log
        pass

class TestResponsive:
    def test_responsive_mobile(self):
        # Load em mobile (375x667)
        # Verificar layout correto
        # Testar filtros funcionam
        pass

    # ... testes para tablet + desktop

# Total: 8+ unit tests
# Target: >95% coverage
```

## 📊 Entrega (Artifacts)

```
frontend/
├─ dashboard_orders.vue (350+ LOC)
│  ├─ OrdersTable component
│  ├─ OrderFilter component
│  ├─ OrderStats component
│  └─ WebSocket connection manager
│
├─ dashboard_orders.js (150+ LOC)
│  ├─ API client methods
│  ├─ WebSocket client
│  └─ State management
│
└─ dashboard_orders.css (100+ LOC)
   ├─ Responsive grid
   ├─ Dark/light theme
   └─ Mobile optimization

api/
├─ orders_api.py (100+ LOC)
│  ├─ GET /orders (list all)
│  ├─ GET /orders/{id} (single)
│  ├─ WebSocket /ws/orders (real-time)
│  └─ POST /orders/export (CSV/JSON)

persistence/
├─ orders_persistence.py
│  ├─ Store order history
│  ├─ Audit trail logging
│  ├─ Recovery logic
│  └─ Migration scripts

tests/
├─ test_dashboard_orders.py (150+ LOC)
├─ conftest.py (fixtures)
│  ├─ Mock orders data
│  ├─ WebSocket fixtures
│  └─ Database fixtures
└─ e2e_dashboard_orders.py (100+ LOC)

docs/
├─ DASHBOARD_ORDERS_GUIDE.md
├─ DASHBOARD_ORDERS_API.md
└─ DASHBOARD_ORDERS_ARCHITECTURE.md
```

## 🔄 Timeline de Execução

```
SEMANA 1 (Dias 1-5):
├─ Dia 1: Design review + Setup ambiente
├─ Dia 2-3: Frontend development (Vue.js components)
├─ Dia 4: WebSocket integration + unit tests
└─ Dia 5: Code review + documentation

SEMANA 2 (Dias 6-10):
├─ Dia 6: E2E testing + performance validation
├─ Dia 7: Integration com API + persistence
├─ Dia 8: Responsiveness testing (mobile + tablet)
├─ Dia 9: Bug fixes + optimization
└─ Dia 10: Final review + merge

VALIDAÇÃO:
├─ AC-1 thru AC-8: 100% passing
├─ Tests: 8+/8+ passing
├─ Coverage: >95%
└─ Latência P95: <100ms WebSocket
```

---

# 🔐 ATI-2: API DE AUTENTICAÇÃO OAUTH 2.0

## 📌 Contexto

**Prioridade:** 🔴 **P0-CRÍTICO**
**Lead:** Dev-Backend-1 (Auth Specialist) (40h)
**Squad:** QA Manager, Doc Advocate
**Duração:** ~3-4 semanas
**Valor:** ⭐⭐⭐⭐⭐ Segurança + Multi-operadores

## 👥 Alocação

```
Lead: Dev-Backend-1 (Auth Specialist)
├─ Design OAuth 2.0 flow
├─ JWT token implementation
├─ Password hashing (bcrypt)
├─ Rate limiting (Redis)
├─ Session management

Suporte: QA Manager
├─ Security testing (OWASP top 10)
├─ Unit + integration tests
├─ AC validation

Suporte: Doc Advocate
├─ API documentation
├─ Sequrity guide
├─ OAuth flow diagram
```

## 🎯 Acceptance Criteria

```
1. [ ] AC-1: Login POST /auth/login (email + password)
2. [ ] AC-2: Token JWT com claims (operador_id, permissions)
3. [ ] AC-3: Token refresh POST /auth/refresh-token (8h validade)
4. [ ] AC-4: Password hashing bcrypt (10+ rounds)
5. [ ] AC-5: Rate limiting (10 tentativas/5 min)
6. [ ] AC-6: Logout revoga token em Redis
7. [ ] AC-7: Session management (múltiplos devices)
8. [ ] AC-8: Auditoria de acesso (logs com timestamp)
```

## 🧪 Testes (8+)

```python
test_auth_login_success
test_auth_login_failure
test_token_refresh
test_rate_limiting
test_password_hashing
test_concurrent_sessions
test_token_expiry
test_audit_logging
```

## 📊 Entrega

```
src/auth/
├─ oauth2_provider.py (120+ LOC)
├─ jwt_handler.py (80+ LOC)
├─ password_utils.py (50+ LOC)
├─ rate_limiter.py (60+ LOC)
└─ session_manager.py (70+ LOC)

tests/
├─ test_auth_oauth2.py (150+ LOC)
└─ conftest.py (fixtures)

docs/
├─ AUTH_OAUTH2_API.md
├─ AUTH_SECURITY_GUIDE.md
└─ OAuth2_Flow_Diagram.png
```

---

# 📡 ATI-3: FILA ASYNC DE ORDENS (RABBITMQ)

## 📌 Contexto

**Prioridade:** 🔴 **P0-CRÍTICO**
**Lead:** Dev-Backend-2 (Queue Specialist) (40h)
**Squad:** Infra DevOps, QA Manager
**Duração:** ~4 semanas
**Valor:** ⭐⭐⭐⭐⭐ Confiabilidade 99.9%

## 👥 Alocação

```
Lead: Dev-Backend-2 (Queue Specialist)
├─ RabbitMQ client design
├─ Order consumer implementation
├─ Retry mechanism (3x exponential backoff)
├─ Dead-letter queue processing
└─ Health check monitoring

Suporte: Infra DevOps
├─ Docker setup (RabbitMQ container)
├─ Monitoring + alerting
├─ Scaling strategy

Suporte: QA Manager
├─ Fila tests (message handling)
├─ Reliability tests (no message loss)
├─ Performance tests (throughput)
```

## 🎯 Acceptance Criteria

```
1. [ ] AC-1: Ordem entra em fila RabbitMQ (async não-bloqueante)
2. [ ] AC-2: Consumer processa com confirmação ACK (no loss)
3. [ ] AC-3: Dead-letter queue para ordens falhadas
4. [ ] AC-4: Rastreamento de estado (queued → processing → completed)
5. [ ] AC-5: Persistência de fila (disco, não RAM)
6. [ ] AC-6: Consumer paralelo (5+ workers)
7. [ ] AC-7: Monitoramento de fila (tamanho, latência)
8. [ ] AC-8: Health check de RabbitMQ
```

## 📊 Entrega

```
src/queue/
├─ rabbitmq_client.py (120+ LOC)
├─ order_consumer.py (100+ LOC)
└─ dlq_processor.py (80+ LOC)

src/monitoring/
└─ queue_monitor.py (80+ LOC)

infra/
├─ docker-compose.yml (RabbitMQ service)
└─ rabbitmq.conf (configuration)

tests/
├─ test_queue_orders.py (150+ LOC)
├─ test_rabbitmq_reliability.py (100+ LOC)
└─ conftest.py (fixtures)

docs/
└─ QUEUE_ARCHITECTURE.md
```

---

# 🔄 ATI-4: WEBSOCKET REAL-TIME POSITIONS

## 📌 Contexto

**Prioridade:** 🔴 **P0-CRÍTICO**
**Lead:** Dev-Backend-3 (WebSocket Specialist) (40h)
**Squad:** Arquiteto de Sistemas, QA Manager
**Duração:** ~4 semanas
**Valor:** ⭐⭐⭐⭐⭐ Real-time <100ms

## 👥 Alocação

```
Lead: Dev-Backend-3 (WebSocket Specialist)
├─ WebSocket server setup (FastAPI + aiohttp)
├─ Position update streaming
├─ Reconnection logic (heartbeat + ping/pong)
├─ Subscription management
└─ TLS/WSS encryption

Suporte: Arquiteto de Sistemas
├─ Performance architecture review
├─ Scalability design (<100ms P95)
├─ Load testing strategy

Suporte: QA Manager
├─ WebSocket tests
├─ Latency validation
├─ Stress tests (1000+ concurrent)
```

## 🎯 Acceptance Criteria

```
1. [ ] AC-1: WebSocket /ws/positions conecta (handshake)
2. [ ] AC-2: Atualizações de preço <100ms
3. [ ] AC-3: Atualizações de P&L recalculadas em tempo real
4. [ ] AC-4: SL/TP ajustes transmitidos instantaneamente
5. [ ] AC-5: Reconexão automática (heartbeat + ping/pong)
6. [ ] AC-6: Suporte a múltiplas conexões (1 operador N devices)
7. [ ] AC-7: Filtragem por símbolo (subscribe/unsubscribe)
8. [ ] AC-8: Criptografia TLS/WSS
```

## 📊 Entrega

```
src/api/
├─ websocket_positions.py (150+ LOC)
├─ position_broadcaster.py (100+ LOC)
└─ connection_manager.py (80+ LOC)

tests/
├─ test_websocket_positions.py (150+ LOC)
├─ test_websocket_latency.py (100+ LOC)
└─ load_test_websocket.py (stress tests)

docs/
├─ WEBSOCKET_API.md
└─ WEBSOCKET_ARCHITECTURE.md
```

---

# 📊 ATI-5: ANÁLISE DE FEATURES SHAP + CORRELAÇÃO

## 📌 Contexto

**Prioridade:** 🟡 **P1-IMPORTANTE (Independente)**
**Lead:** ML Expert (44h)
**Squad:** Data Scientist, QA Manager
**Duração:** ~2-3 semanas
**Valor:** ⭐⭐⭐⭐ Inteligência do modelo

## 👥 Alocação

```
Lead: ML Expert
├─ SHAP values calculation
├─ Feature importance ranking
├─ Multicollinearity detection (VIF)
├─ Dependence plot generation
└─ Report writing

Suporte: Data Scientist
├─ Correlation matrix computation
├─ Heatmap visualization
├─ Statistical analysis

Suporte: QA Manager
├─ Data quality validation
├─ AC verification
├─ Report audit
```

## 🎯 Acceptance Criteria

```
1. [ ] AC-1: SHAP values calculados para todo o dataset
2. [ ] AC-2: Top 10 features identificadas e classificadas
3. [ ] AC-3: Gráfico waterfall (feature contribution)
4. [ ] AC-4: Dependence plots (relação feature × prediction)
5. [ ] AC-5: Matriz de correlação 24×24 com heatmap
6. [ ] AC-6: Detecção de multicollinearidade (VIF > 5)
7. [ ] AC-7: Análise de importância agregada
8. [ ] AC-8: Relatório executivo (20+ páginas)
```

## 📊 Entrega

```
src/ml/
├─ feature_analysis.py (120+ LOC)
├─ shap_analyzer.py (100+ LOC)
└─ correlation_analyzer.py (80+ LOC)

outputs/
├─ shap_analysis_report.md (20+ páginas)
├─ correlation_heatmap.png
├─ feature_importance.json
├─ top_10_features.png
└─ dependence_plots/ (14+ plots)

tests/
└─ test_feature_analysis.py (120+ LOC)

docs/
└─ FEATURE_ANALYSIS_GUIDE.md
```

---

# ⚠️ ATI-6: REGRAS DE DRIFT + ALERTAS

## 📌 Contexto

**Prioridade:** 🟡 **P1-IMPORTANTE (Independente)**
**Lead:** Data Scientist (44h)
**Squad:** ML Expert, Infra DevOps
**Duração:** ~2-3 semanas
**Valor:** ⭐⭐⭐⭐ Monitoramento contínuo

## 👥 Alocação

```
Lead: Data Scientist
├─ Drift detection rules (3 rules)
├─ Statistical tests implementation
├─ Alert threshold tuning
├─ Monitoring dashboard

Suporte: ML Expert
├─ KS test implementation
├─ Correlation change detection
├─ Report generation

Suporte: Infra DevOps
├─ Alert system setup
├─ Email/Slack integration
├─ Scheduling (hourly check)
```

## 🎯 Acceptance Criteria

```
1. [ ] AC-1: Regra 1 - Teste de mudança de média implementado
2. [ ] AC-2: Regra 2 - Teste KS implementado
3. [ ] AC-3: Regra 3 - Mudança de correlação implementada
4. [ ] AC-4: Alertas em 4 níveis (Verde/Amarelo/Laranja/Vermelho)
5. [ ] AC-5: Monitoramento contínuo (check a cada hora)
6. [ ] AC-6: Histórico de alertas (persistência)
7. [ ] AC-7: Limiares configuráveis (tunáveis)
8. [ ] AC-8: Relatório semanal de drift
```

## 📊 Entrega

```
src/monitoring/
├─ drift_detector.py (120+ LOC)
├─ alert_system.py (100+ LOC)
└─ alert_scheduler.py (60+ LOC)

tests/
└─ test_drift_detection.py (120+ LOC)

docs/
└─ DRIFT_MONITORING_GUIDE.md
```

---

# 📈 ATI-7: BACKTEST DE 252 DIAS COMPLETO [BLOQUEADO]

## 📌 Contexto

**Prioridade:** 🔴 **P0-CRÍTICO (Sequencial)**
**Lead:** ML Expert (44h)
**Status:** 🟡 **Bloqueado (aguarda ENG-003)**
**Squad:** Data Scientist, QA Manager, CFO
**Duração:** ~2-3 semanas (após GATE 1)
**Valor:** ⭐⭐⭐⭐⭐ Validação científica

## 👥 Alocação

```
Lead: ML Expert
├─ Backtest engine implementation
├─ Sharpe ratio calculation
├─ Win rate calculation
├─ Equity curve generation
└─ Report writing

Suporte: Data Scientist
├─ Feature extraction validation
├─ Regime detection
├─ Cross-validation (5-fold)

Suporte: QA Manager + CFO
├─ AC validation
├─ Metrics approval
├─ Capital decision
```

## 🎯 Acceptance Criteria (20 AC)

```
1. [ ] AC-1: Dataset de 252 dias (17.280 velas) carregado
2. [ ] AC-2: Validação de datas (sem gaps)
3. [ ] AC-3: Cálculo de Sharpe ratio
4. [ ] AC-4: Cálculo de taxa de vitória
5. [ ] AC-5: Cálculo de redução máxima
6. [ ] AC-6: Análise de regime de mercado
7. [ ] AC-7: Importância de features
8. [ ] AC-8: Curva de patrimônio (equity curve)
9. [ ] AC-9: Gráfico de redução
10. [ ] AC-10: Consistência mensal

... (AC-11 thru AC-20)

⭐ GATE 2 Critério:
- Sharpe >= 1.0 ✅
- Win Rate >= 59% ✅
- Drawdown < 15% ✅
- Consistency < 30% ✅
```

## 📊 Entrega

```
src/ml/
├─ backtester.py (200+ LOC)
└─ metrics_calculator.py (150+ LOC)

outputs/
├─ backtest_report_252days.md
├─ backtest_results.json
├─ equity_curve.png
├─ drawdown_chart.png
└─ monthly_returns.csv

tests/
└─ test_backtester.py (150+ LOC)

docs/
└─ BACKTEST_METHODOLOGY.md
```

---

# 🔧 ATI-8: RETRY LOGIC (3X BACKOFF EXPONENCIAL)

## 📌 Contexto

**Prioridade:** 🔴 **P0-CRÍTICO**
**Lead:** Dev-Backend-2 (Reliability Specialist) (32h)
**Squad:** QA Manager, Doc Advocate
**Duração:** ~2-3 semanas
**Valor:** ⭐⭐⭐⭐ Resiliência

## 👥 Alocação

```
Lead: Dev-Backend-2
├─ Retry handler implementation
├─ Backoff algorithm (exponential)
├─ Error classification
├─ DLQ processing
└─ Monitoring

Suporte: QA Manager
├─ Retry tests
├─ Backoff timing validation
├─ DLQ tests

Suporte: Doc Advocate
├─ Retry strategy documentation
└─ Error classification guide
```

## 🎯 Acceptance Criteria

```
1. [ ] AC-1: Retry automático até 3 tentativas
2. [ ] AC-2: Backoff exponencial (1s → 2s → 4s)
3. [ ] AC-3: Detecção de erro transitório vs permanente
4. [ ] AC-4: Logging de cada tentativa
5. [ ] AC-5: Dead-letter queue para falhas
6. [ ] AC-6: Notificação ao operador após 3 falhas
7. [ ] AC-7: Histórico de retries (auditável)
8. [ ] AC-8: Monitoramento de taxa de retry
```

## 📊 Entrega

```
src/reliability/
├─ retry_handler.py (100+ LOC)
├─ backoff_strategy.py (60+ LOC)
└─ dlq_processor.py (80+ LOC)

tests/
└─ test_retry_logic.py (120+ LOC)

docs/
└─ RETRY_STRATEGY.md
```

---

# 📍 ATI-9: POSITION MONITORING + SL/TP AUTOMÁTICO

## 📌 Contexto

**Prioridade:** 🔴 **P0-CRÍTICO**
**Lead:** Dev-Backend-3 (Position Specialist) (32h)
**Squad:** QA Manager, Arquiteto
**Duração:** ~3-4 semanas
**Valor:** ⭐⭐⭐⭐ Controle automático de risco

## 👥 Alocação

```
Lead: Dev-Backend-3
├─ Position manager implementation
├─ SL/TP monitoring loop
├─ Automatic execution logic
├─ History tracking
└─ Notifications

Suporte: QA Manager
├─ Position tests
├─ SL/TP execution tests
├─ Edge case testing

Suporte: Arquiteto
├─ Performance review
├─ Safety mechanism validation
```

## 🎯 Acceptance Criteria

```
1. [ ] AC-1: GET /positions (todas as abertas)
2. [ ] AC-2: GET /positions/{id} (posição específica)
3. [ ] AC-3: PUT /positions/{id}/sl-tp (atualizar)
4. [ ] AC-4: GET /positions/{id}/history (histórico)
5. [ ] AC-5: Monitoramento contínuo (tick by tick)
6. [ ] AC-6: Execução automática de SL
7. [ ] AC-7: Execução automática de TP
8. [ ] AC-8: Notificação de execução
```

## 📊 Entrega

```
src/positions/
├─ position_manager.py (120+ LOC)
├─ sl_tp_monitor.py (100+ LOC)
└─ position_executor.py (80+ LOC)

tests/
└─ test_position_monitoring.py (130+ LOC)

docs/
└─ POSITION_MANAGEMENT_GUIDE.md
```

---

# 🔐 ATI-10: CAPITAL DECISION FRAMEWORK (GATE 2) [BLOQUEADO]

## 📌 Contexto

**Prioridade:** 🔴 **P0-CRÍTICO**
**Lead:** ML Expert + CFO (40h total)
**Status:** 🟡 **Bloqueado (aguarda ML-004)**
**Squad:** QA Manager, Doc Advocate
**Duração:** ~1-2 semanas (após GATE 1)
**Valor:** ⭐⭐⭐⭐⭐ **Ativa R$ 100k Fase 2**

## 👥 Alocação

```
Lead: ML Expert (20h)
├─ Metrics aggregation
├─ Validation logic
├─ Dashboard generation
└─ Decision report

Co-Lead: CFO (20h)
├─ Financial review
├─ Capital approval
├─ Risk sign-off

Suporte: QA Manager
├─ AC validation
├─ Approval workflow testing

Suporte: Doc Advocate
├─ Decision documentation
├─ Audit trail
```

## 🎯 Acceptance Criteria (10 AC)

```
1. [ ] AC-1: Validação de Sharpe >= 1.0
2. [ ] AC-2: Validação de Win Rate >= 59%
3. [ ] AC-3: Validação de Drawdown < 15%
4. [ ] AC-4: Validação de consistência < 30%
5. [ ] AC-5: Dashboard de métricas (visual)
6. [ ] AC-6: Relatório de decisão (GO/NO-GO)
7. [ ] AC-7: Aprovação de CFO (assinatura)
8. [ ] AC-8: Documentação de decisão (audit trail)
9. [ ] AC-9: Notificação ao presidente
10. [ ] AC-10: Ativação automática de capital se GO
```

## 📊 Entrega

```
src/decision/
├─ gate2_validator.py (100+ LOC)
├─ capital_framework.py (80+ LOC)
└─ approval_workflow.py (70+ LOC)

outputs/
├─ gate2_decision_report.md
├─ gate2_metrics_dashboard.html
└─ capital_activation.json

tests/
└─ test_gate2_decision.py (100+ LOC)

docs/
└─ GATE2_DECISION_FRAMEWORK.md
```

---

## 🎯 ESTRUTURA PARALELA COMPLETA

```
┌─────────────────────────────────────────────────────────────┐
│ EXECUÇÃO PARALELA - 3 TRACKS / 6-8 SEMANAS                │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│ TRACK 1: INFRAESTRUTURA (ENG-003) - 224h                  │
│ ├─ ATI-1: Dashboard Ordens (40h) ✓ 8 AC                   │
│ ├─ ATI-2: OAuth 2.0 (40h) ✓ 8 AC                          │
│ ├─ ATI-3: RabbitMQ Queue (40h) ✓ 8 AC                   │
│ ├─ ATI-4: WebSocket Positions (40h) ✓ 8 AC             │
│ ├─ ATI-8: Retry Logic (32h) ✓ 8 AC                      │
│ └─ ATI-9: Position Monitor (32h) ✓ 8 AC                │
│    └─ GATE 1: Todos os 8+8 AC PASSANDO               │
│                                                             │
│ TRACK 2: ANÁLISE (ML-003) - 88h                           │
│ ├─ ATI-5: SHAP Features (44h) ✓ 8 AC                     │
│ └─ ATI-6: Drift Detection (44h) ✓ 8 AC                   │
│    └─ GATE 1: Todos os 18 AC PASSANDO                    │
│                                                             │
│ TRACK 3: VALIDAÇÃO (ML-004) - 84h [SEQUENCIAL]           │
│ ├─ Aguarda: GATE 1 PASS (TRACK 1 + 2)                   │
│ ├─ ATI-7: Backtest 252d (44h) ✓ 20 AC                   │
│ └─ ATI-10: Gate 2 Decision (40h) ✓ 10 AC                │
│    └─ GATE 2: Sharpe >=1.0 + Win Rate >=59% + DD <15%   │
│       └─ **CAPITAL ACTIVATION: R$ 100k FASE 2**        │
│                                                             │
└─────────────────────────────────────────────────────────────┘

TIMELINE DETALHADO:

Semana 1-2: TRACK 1 + 2 paralelo (ramp-up)
├─ Design reviews completados
├─ Ambientes de dev/test prontos
└─ 30% de progresso esperado

Semana 3-4: TRACK 1 + 2 aceleração
├─ Implementação em ritmo máximo
├─ Testes contínuos
└─ 70% de progresso esperado

Semana 5: GATE 1 CHECKPOINT
├─ TRACK 1 + 2: 100% AC validados
├─ Decisão: GO → TRACK 3 inicia
└─ Review: Nenhum bloqueador

Semana 6-7: TRACK 3 execução
├─ Backtest 252d rodando
├─ Métricas validadas
└─ Capital decision framework

Semana 8: GATE 2 CHECKPOINT
├─ GATE 2 validation (Sharpe, Win Rate, DD)
├─ **Decisão: GO → R$ 100k ativado**
└─ Beta Phase 2 pronto para 13/03
```

---

## ✅ CHECKLIST DE EXECUÇÃO

### Antes de Começar

- [ ] Todos os 10 documentos ATI disponíveis
- [ ] 11 personas confirmadas disponíveis
- [ ] Ambientes de dev/test criados
- [ ] CI/CD pipeline configurada
- [ ] Testes fixtures preparadas
- [ ] Documentação templates prontos

### Durante Execução

- [ ] Daily standups (15:00 BRT)
- [ ] AC validation (conforme progresso)
- [ ] Test automation (TDD)
- [ ] Documentation sync
- [ ] Code reviews (2+ reviewers)
- [ ] Risk tracking

### GATE 1 Checkpoint (6-8 semanas)

- [ ] TRACK 1: 6/6 ATI com 8 AC cada = 48 AC ✅
- [ ] TRACK 2: 2/2 ATI com 8 AC cada = 18 AC ✅
- [ ] Tests: 98+/98+ PASSED ✅
- [ ] Coverage: >90% ✅
- [ ] Code reviewed: 100% ✅
- [ ] Decisão: GO/NO-GO

### GATE 2 Checkpoint (após GATE 1 + 2-3 semanas)

- [ ] TRACK 3: ATI-7 Backtest ✅
- [ ] Sharpe >= 1.0 ✅
- [ ] Win Rate >= 59% ✅
- [ ] Drawdown < 15% ✅
- [ ] ATI-10: Gate 2 Decision ✅
- [ ] CFO Approval ✅
- [ ] **Capital Activation: R$ 100k**

---

## 🎊 RESULTADO FINAL

**Ao completar as 10 atividades:**

✅ Operador `INICIAR_MICRO_TENDENCIA_AUTO_TRADE.bat` tem:
- Dashboard 100% visível
- Autenticação segura multi-operador
- Ordens confiáveis (99.9%)
- Real-time <100ms
- Inteligência do modelo explícita
- Monitoramento de degradação
- Validação científica (Sharpe ≥1.0)
- Resiliência automática
- Controle de risco automático
- **Capital escalado para R$ 100k (Fase 2)**

✅ Governança mantida 100%
✅ Documentação sincronizada
✅ Testes abrangentes (>90% coverage)
✅ Code quality (100% type hints)
✅ Audit trail completo

---

*Documento: EXECUCAO_10_ATIVIDADES_SPRINT2_FRAMEWORK.md*
**Status:** 🟢 Ready for Execution | **Framework:** {{prompts\executa_task.md}} Applied to All 10 ATI

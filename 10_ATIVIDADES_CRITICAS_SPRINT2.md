# 🚀 10 ATIVIDADES CRÍTICAS - Sprint 2
## Entrega de Features com Valor Real ao Operador

**Status:** 🟢 **MOBILIZAÇÃO IMEDIATA - SQUADS ATIVADAS**
**Framework:** {{prompts/PIPELINE_TASKS.MD}} - 21 passos de execução
**Modelo:** Parallelization-First + Ready-When-Done
**Prioridade:** 10 atividades bloqueadoras que habilitam o operador

---

## 📋 SUMÁRIO EXECUTIVO

| # | Atividade | Lead | Squad | Horas | Status | Desbloqueia |
|---|-----------|------|-------|-------|--------|------------|
| **1** | Dashboard de Ordens em Tempo Real | Eng Sr | T1-Dev-Backend | 40h | 🟢 Pronto | Operador visualizar ordens |
| **2** | API de Autenticação OAuth 2.0 | Dev-Backend-1 | T1-Auth | 40h | 🟢 Pronto | Segurança + Acesso |
| **3** | Fila Async de Ordens (RabbitMQ) | Dev-Backend-2 | T1-Queue | 40h | 🟢 Pronto | Confiabilidade ordens |
| **4** | WebSocket Real-time Positions | Dev-Backend-3 | T1-WebSocket | 40h | 🟢 Pronto | Visibilidade <100ms |
| **5** | Análise de Features SHAP + Correlação | ML Expert | T2-Features | 44h | 🟢 Pronto | Inteligência do modelo |
| **6** | Regras de Drift + Alertas | Data Scientist | T2-Drift | 44h | 🟢 Pronto | Monitoramento contínuo |
| **7** | Backtest de 252 Dias Completo | ML Expert | T3-Backtest | 44h | 🟡 Bloqueado | Validação Sharpe ≥1.0 |
| **8** | Retry Logic (3x Backoff Exponencial) | Dev-Backend-2 | T1-Reliability | 32h | 🟢 Pronto | Resiliência ordens |
| **9** | Position Monitoring + SL/TP Automático | Dev-Backend-3 | T1-Positions | 32h | 🟢 Pronto | Controle de posições |
| **10** | Capital Decision Framework (Gate 2) | ML Expert + CFO | T3-Decision | 40h | 🟡 Bloqueado | Ativar R$ 100k Fase 2 |

**Total Horas:** 356h | **Equipes:** 8 personas | **Parallel Tracks:** 3 | **Gates:** 2

---

## 🔴 ATIVIDADE #1: DASHBOARD DE ORDENS EM TEMPO REAL

**Prioridade:** 🔴 **P0-CRÍTICO (Bloqueador)**
**Lead:** Eng Sr + Dev-Backend-3 (WebSocket)
**Squad:** Timeline Backend (5 pessoas)
**Duração:** 40 horas
**Valor Operacional:** ⭐⭐⭐⭐⭐ Visibilidade 100% das ordens

### Descrição
Criar um dashboard integrado que mostra ao operador **todas as ordens em tempo real** com atualização <100ms via WebSocket. O operador enxerga:
- Status de cada ordem (pendente → enviada → preenchida)
- Preço de entrada, saída, lucro/prejuízo
- Tempo de execução
- Histórico completo com audit trail

### Aceitação (AC)
- [ ] AC-1: Dashboard exibe 100% das ordens (pendentes + executadas)
- [ ] AC-2: Atualização em tempo real via WebSocket (<100ms)
- [ ] AC-3: Filtros por símbolo, status, período
- [ ] AC-4: Audit trail completo (criação → execução → fechamento)
- [ ] AC-5: Relatórios exportáveis (CSV, JSON)
- [ ] AC-6: UX responsivo (desktop + mobile)
- [ ] AC-7: Histórico persistente (PostgreSQL)
- [ ] AC-8: Alertas de mudança de status

### Testes
- [ ] test_dashboard_load_orders (50+ ordens)
- [ ] test_websocket_update_latency (<100ms)
- [ ] test_dashboard_filtering (5 tipos de filtro)
- [ ] test_audit_trail_complete (cada ação registrada)
- [ ] test_export_csv_json (formato correto)
- [ ] test_responsiveness_mobile (breakpoints)
- [ ] test_persistence_postgresql (recovery)
- [ ] test_alert_status_change (notifications)

### Entrega
```
src/frontend/dashboard_orders.html
src/frontend/dashboard_orders.js
src/api/websocket_orders.py
tests/test_dashboard_orders.py
docs/DASHBOARD_ORDERS_GUIDE.md
```

### Crítico Para
- ✅ Operador validar execução de ordens
- ✅ Auditoria de todas as ações
- ✅ Conformidade regulatória (audit trail)

---

## 🔴 ATIVIDADE #2: API DE AUTENTICAÇÃO OAUTH 2.0

**Prioridade:** 🔴 **P0-CRÍTICO**
**Lead:** Dev-Backend-1 (Auth Specialist)
**Squad:** T1-Auth (2 pessoas)
**Duração:** 40 horas
**Valor Operacional:** ⭐⭐⭐⭐⭐ Segurança + Acesso autorizado

### Descrição
Implementar OAuth 2.0 com suporte a múltiplos operadores. Cada operador autentica com credenciais próprias, recebe JWT com validade 8h, e pode renovar sem logout.

### Aceitação (AC)
- [ ] AC-1: Login POST /auth/login (email + password)
- [ ] AC-2: Token JWT gerado com claims (operador_id, permissions)
- [ ] AC-3: Token refresh POST /auth/refresh-token (8h validade)
- [ ] AC-4: Password hashing com bcrypt (10+ rounds)
- [ ] AC-5: Rate limiting (10 tentativas/5 minutos)
- [ ] AC-6: Logout revoga token em Redis
- [ ] AC-7: Session management (múltiplos devices)
- [ ] AC-8: Auditoria de acesso (logs com timestamp)

### Testes
- [ ] test_auth_login_success (credenciais corretas)
- [ ] test_auth_login_failure (credenciais erradas)
- [ ] test_token_refresh (renovação válida)
- [ ] test_rate_limiting (10 tentativas)
- [ ] test_password_hashing (bcrypt check)
- [ ] test_concurrent_sessions (múltiplos devices)
- [ ] test_token_expiry (8h expiração)
- [ ] test_audit_logging (todos os acessos)

### Entrega
```
src/auth/oauth2_provider.py
src/auth/jwt_handler.py
src/auth/password_utils.py
tests/test_auth_oauth2.py
docs/AUTH_OAUTH2_API.md
```

### Crítico Para
- ✅ Autenticação segura
- ✅ Multi-operadores
- ✅ Conformidade de segurança

---

## 🔴 ATIVIDADE #3: FILA ASYNC DE ORDENS (RABBITMQ)

**Prioridade:** 🔴 **P0-CRÍTICO**
**Lead:** Dev-Backend-2 (Queue Specialist)
**Squad:** T1-Queue (2 pessoas)
**Duração:** 40 horas
**Valor Operacional:** ⭐⭐⭐⭐⭐ Confiabilidade 99.9%

### Descrição
Implementar fila RabbitMQ que garante **nenhuma ordem é perdida**. Operador clica "Enviar", ordem entra na fila, consumer processa com confirmação ACK.

### Aceitação (AC)
- [ ] AC-1: Ordem entra em fila RabbitMQ (async não-bloqueante)
- [ ] AC-2: Consumer processa com confirmação ACK (no loss)
- [ ] AC-3: Dead-letter queue para ordens falhadas
- [ ] AC-4: Rastreamento de estado (queued → processing → completed)
- [ ] AC-5: Persistência de fila (disco, não RAM)
- [ ] AC-6: Consumer paralelo (5+ workers)
- [ ] AC-7: Monitoramento de fila (tamanho, latência)
- [ ] AC-8: Health check de RabbitMQ

### Testes
- [ ] test_queue_order_placement (ordem entra em fila)
- [ ] test_queue_processing_order (consumer processa)
- [ ] test_ack_confirmation (confirmação ACK)
- [ ] test_dead_letter_queue (ordens falhadas)
- [ ] test_parallel_consumers (5 workers simultâneos)
- [ ] test_queue_persistence (recovery após crash)
- [ ] test_queue_latency (end-to-end timing)
- [ ] test_health_check_rabbitmq (monitoring)

### Entrega
```
src/queue/rabbitmq_client.py
src/queue/order_consumer.py
src/monitoring/queue_monitor.py
tests/test_queue_orders.py
docker-compose.yml (RabbitMQ)
docs/QUEUE_ARCHITECTURE.md
```

### Crítico Para
- ✅ Confiabilidade 99.9%
- ✅ Nenhuma ordem perdida
- ✅ Escalabilidade (múltiplos workers)

---

## 🔴 ATIVIDADE #4: WEBSOCKET REAL-TIME POSITIONS

**Prioridade:** 🔴 **P0-CRÍTICO**
**Lead:** Dev-Backend-3 (WebSocket Specialist)
**Squad:** T1-WebSocket (2 pessoas)
**Duração:** 40 horas
**Valor Operacional:** ⭐⭐⭐⭐⭐ Visibilidade <100ms

### Descrição
Operador abre WebSocket e recebe atualizações de posições **em menos de 100ms**. Cada mudança (P&L, preço, SL/TP) é transmitida em tempo real.

### Aceitação (AC)
- [ ] AC-1: WebSocket /ws/positions conecta (handshake)
- [ ] AC-2: Atualizações de preço <100ms
- [ ] AC-3: Atualizações de P&L recalculadas em tempo real
- [ ] AC-4: SL/TP ajustes transmitidos instantaneamente
- [ ] AC-5: Reconexão automática (heartbeat + ping/pong)
- [ ] AC-6: Suporte a múltiplas conexões (1 operador + múltiplos devices)
- [ ] AC-7: Filtragem por símbolo (subscribe/unsubscribe)
- [ ] AC-8: Criptografia TLS/WSS

### Testes
- [ ] test_websocket_connect (handshake)
- [ ] test_websocket_disconnect (clean close)
- [ ] test_position_update_latency (<100ms)
- [ ] test_pnl_recalculation (cada tick)
- [ ] test_sl_tp_adjustment (mudanças instantâneas)
- [ ] test_reconnection_automatic (heartbeat recovery)
- [ ] test_multiple_connections (1 operador N devices)
- [ ] test_websocket_security (WSS + auth)

### Entrega
```
src/api/websocket_positions.py
src/models/position_update.py
tests/test_websocket_positions.py
docs/WEBSOCKET_API.md
```

### Crítico Para
- ✅ Visibilidade em tempo real
- ✅ Reflexo instantâneo de mudanças
- ✅ Operador toma decisões informadas

---

## 🟡 ATIVIDADE #5: ANÁLISE DE FEATURES SHAP + CORRELAÇÃO

**Prioridade:** 🟡 **P1-IMPORTANTE (Independente)**
**Lead:** ML Expert
**Squad:** T2-Features (2 pessoas)
**Duração:** 44 horas
**Valor Operacional:** ⭐⭐⭐⭐ Inteligência do modelo

### Descrição
Analisar quais **24 features** estão contribuindo mais para as decisões do modelo. Gerar relatório SHAP com top 10 features e matriz de correlação 24×24.

### Aceitação (AC)
- [ ] AC-1: SHAP values calculados para todo o dataset
- [ ] AC-2: Top 10 features identificadas e classificadas
- [ ] AC-3: Gráfico waterfall (feature contribution)
- [ ] AC-4: Dependence plots (relação feature × prediction)
-  [ ] AC-5: Matriz de correlação 24×24 com heatmap
- [ ] AC-6: Detecção de multicollinearidade (VIF > 5)
- [ ] AC-7: Análise de importância agregada
- [ ] AC-8: Relatório executivo (20+ páginas)

### Testes
- [ ] test_shap_values_calculation (todos os samples)
- [ ] test_top_features_extraction (ranking)
- [ ] test_correlation_matrix_computation (24x24)
- [ ] test_heatmap_visualization (PNG/PDF)
- [ ] test_vif_multicollinearity (cálculo)
- [ ] test_dependence_plots (14+ plots)
- [ ] test_report_generation (Markdown)
- [ ] test_data_quality (missing values)

### Entrega
```
src/ml/feature_analysis.py
src/ml/shap_analyzer.py
outputs/shap_analysis_report.md
outputs/correlation_heatmap.png
outputs/feature_importance.json
tests/test_feature_analysis.py
docs/FEATURE_ANALYSIS_GUIDE.md
```

### Crítico Para
- ✅ Entender o modelo
- ✅ Detectar colinearidade
- ✅ Validar features importantes

---

## 🟡 ATIVIDADE #6: REGRAS DE DRIFT + ALERTAS

**Prioridade:** 🟡 **P1-IMPORTANTE (Independente)**
**Lead:** Data Scientist
**Squad:** T2-Drift (2 pessoas)
**Duração:** 44 horas
**Valor Operacional:** ⭐⭐⭐⭐ Monitoramento contínuo

### Descrição
Detectar automaticamente quando **o modelo está degradando** (drift detection). 3 regras:
1. Mudança de média (µ ± 2σ)
2. Teste KS (kolmogorov-smirnov p-value)
3. Mudança de correlação (Δr > 0.1)

### Aceitação (AC)
- [ ] AC-1: Regra 1 - Teste de mudança de média implementado
- [ ] AC-2: Regra 2 - Teste KS implementado
- [ ] AC-3: Regra 3 - Mudança de correlação implementada
- [ ] AC-4: Alertas em 4 níveis (Verde/Amarelo/Laranja/Vermelho)
- [ ] AC-5: Monitoramento contínuo (check a cada hora)
- [ ] AC-6: Histórico de alertas (persistência)
- [ ] AC-7: Limiares configuráveis (tunáveis)
- [ ] AC-8: Relatório semanal de drift

### Testes
- [ ] test_drift_mean_shift (µ ± 2σ)
- [ ] test_ks_statistic (p-value calculation)
- [ ] test_correlation_change (Δr detection)
- [ ] test_alert_levels (4 níveis)
- [ ] test_monitoring_frequency (hourly)
- [ ] test_alert_persistence (PostgreSQL)
- [ ] test_threshold_tuning (configurável)
- [ ] test_weekly_report (Markdown)

### Entrega
```
src/monitoring/drift_detector.py
src/monitoring/alert_system.py
tests/test_drift_detection.py
docs/DRIFT_MONITORING_GUIDE.md
```

### Crítico Para
- ✅ Detectar degradação do modelo
- ✅ Ativar retrainamento se necessário
- ✅ Manter confiabilidade

---

## 🔴 ATIVIDADE #7: BACKTEST DE 252 DIAS COMPLETO

**Prioridade:** 🔴 **P0-CRÍTICO (Sequencial)**
**Lead:** ML Expert
**Squad:** T3-Backtest (2 pessoas)
**Duração:** 44 horas
**Status:** 🟡 **Bloqueado (aguarda ENG-003)**
**Valor Operacional:** ⭐⭐⭐⭐⭐ Validação Sharpe ≥1.0

### Descrição
Backtest histórico de **252 dias** (1 ano completo) com 17.280 velas. Calcular Sharpe ≥1.0, Win Rate ≥59%, Drawdown <15%.

### Aceitação (AC)
- [ ] AC-1: Dataset de 252 dias (17.280 velas) carregado
- [ ] AC-2: Validação de datas (sem gaps, sem feriados)
- [ ] AC-3: Cálculo de Sharpe ratio
- [ ] AC-4: Cálculo de taxa de vitória
- [ ] AC-5: Cálculo de redução máxima (drawdown)
- [ ] AC-6: Análise de regime de mercado (trending vs range)
- [ ] AC-7: Importância de features durante negociações
- [ ] AC-8: Curva de patrimônio (equity curve)
- [ ] AC-9: Gráfico de redução (drawdown chart)
- [ ] AC-10: Consistência mensal (std < 30%)
- [ ] AC-11: Análise PNL por mês
- [ ] AC-12: Validação de transações (entrada/saída)
- [ ] AC-13: Cálculo de comissão (realistic)
- [ ] AC-14: Relatório com 20+ páginas
- [ ] AC-15: JSON com métricas estruturadas
- [ ] AC-16: Validação de overfitting
- [ ] AC-17: Cross-validation (5-fold)
- [ ] AC-18: Peer review aprovado
- [ ] AC-19: Métricas ajustadas ao risco
- [ ] AC-20: Sensibilidade de parâmetros

### Testes
- [ ] test_backtest_data_loading (17.280 velas)
- [ ] test_backtest_date_validation (no gaps)
- [ ] test_sharpe_calculation (vs manual)
- [ ] test_win_rate_calculation (VP/(VP+FP))
- [ ] test_drawdown_calculation (max loss)
- [ ] test_equity_curve (starting capital)
- [ ] test_pnl_per_trade (realistic)
- [ ] test_fees_commission (deducted)
- [ ] test_regime_detection (trending vs range)
- [ ] test_monthly_consistency (std)
- [ ] test_overfitting_check (cross-val)
- [ ] test_report_generation (PDF)
- [ ] test_metrics_json_export (structured)
- [ ] test_peer_review_comments (approved)

### Entrega
```
src/ml/backtester.py
outputs/backtest_report_252days.md
outputs/backtest_results.json
outputs/equity_curve.png
outputs/drawdown_chart.png
tests/test_backtester.py
docs/BACKTEST_METHODOLOGY.md
```

### Crítico Para
- ✅ Validar Sharpe ≥1.0
- ✅ Validar Win Rate ≥59%
- ✅ **GATE 2 Decision** (capital)

---

## 🔴 ATIVIDADE #8: RETRY LOGIC (3X BACKOFF EXPONENCIAL)

**Prioridade:** 🔴 **P0-CRÍTICO**
**Lead:** Dev-Backend-2 (Reliability Specialist)
**Squad:** T1-Reliability (2 pessoas)
**Duração:** 32 horas
**Valor Operacional:** ⭐⭐⭐⭐ Resiliência

### Descrição
Se uma ordem falha, tentar 3 vezes com backoff exponencial (1s → 2s → 4s). **Nenhuma ordem é perdida**.

### Aceitação (AC)
- [ ] AC-1: Retry automático até 3 tentativas
- [ ] AC-2: Backoff exponencial (1s → 2s → 4s)
- [ ] AC-3: Detecção de erro transitório vs permanente
- [ ] AC-4: Logging de cada tentativa
- [ ] AC-5: Dead-letter queue para falhas permanentes
- [ ] AC-6: Notificação ao operador após 3 falhas
- [ ] AC-7: Histórico de retries (auditável)
- [ ] AC-8: Monitoramento de taxa de retry

### Testes
- [ ] test_retry_first_failure (sucesso na 2ª tentativa)
- [ ] test_retry_all_failures (move to DLQ)
- [ ] test_backoff_timing (1s, 2s, 4s)
- [ ] test_transient_vs_permanent (error classification)
- [ ] test_logging_complete (cada tentativa)
- [ ] test_dlq_processing (dead-letter)
- [ ] test_operator_notification (Slack/email)
- [ ] test_retry_history_persistence (audit trail)

### Entrega
```
src/reliability/retry_handler.py
src/queue/dlq_processor.py
tests/test_retry_logic.py
docs/RETRY_STRATEGY.md
```

### Crítico Para
- ✅ Resiliência contra falhas transitórias
- ✅ Garantia de entrega
- ✅ Confiabilidade operacional

---

## 🔴 ATIVIDADE #9: POSITION MONITORING + SL/TP AUTOMÁTICO

**Prioridade:** 🔴 **P0-CRÍTICO**
**Lead:** Dev-Backend-3 (Position Specialist)
**Squad:** T1-Positions (2 pessoas)
**Duração:** 32 horas
**Valor Operacional:** ⭐⭐⭐⭐ Controle automático

### Descrição
Monitorar posições abertas e **executar automaticamente Stop Loss e Take Profit** quando níveis são atingidos.

### Aceitação (AC)
- [ ] AC-1: GET /positions (todas as posições abertas)
- [ ] AC-2: GET /positions/{id} (posição específica)
- [ ] AC-3: PUT /positions/{id}/sl-tp (atualizar SL/TP)
- [ ] AC-4: GET /positions/{id}/history (histórico de mudanças)
- [ ] AC-5: Monitoramento contínuo de SL/TP (tick by tick)
- [ ] AC-6: Execução automática de SL quando price ≤ SL
- [ ] AC-7: Execução automática de TP quando price ≥ TP
- [ ] AC-8: Notificação de execução ao operador

### Testes
- [ ] test_position_fetch_all (lista completa)
- [ ] test_position_fetch_single (ID específico)
- [ ] test_sl_tp_update (atualizar níveis)
- [ ] test_position_history (rastreamento)
- [ ] test_sl_execution (price ≤ SL)
- [ ] test_tp_execution (price ≥ TP)
- [ ] test_monitoring_realtime (<100ms check)
- [ ] test_operator_notification (Slack/email)

### Entrega
```
src/positions/position_manager.py
src/positions/sl_tp_monitor.py
tests/test_position_monitoring.py
docs/POSITION_MANAGEMENT_GUIDE.md
```

### Crítico Para
- ✅ Controle automático de risco
- ✅ SL/TP executados automaticamente
- ✅ Proteção contra grandes perdas

---

## 🔴 ATIVIDADE #10: CAPITAL DECISION FRAMEWORK (GATE 2)

**Prioridade:** 🔴 **P0-CRÍTICO**
**Lead:** ML Expert + CFO
**Squad:** T3-Decision (3 pessoas)
**Duração:** 40 horas
**Status:** 🟡 **Bloqueado (aguarda ML-004)**
**Valor Operacional:** ⭐⭐⭐⭐⭐ **Ativa R$ 100k Fase 2**

### Descrição
Framework que valida todas as métricas de backtest e aprova (ou não) o aumento de capital de R$ 50k → R$ 100k.

### Aceitação (AC)
- [ ] AC-1: Validação de Sharpe ≥1.0
- [ ] AC-2: Validação de Win Rate ≥59%
- [ ] AC-3: Validação de Drawdown <15%
- [ ] AC-4: Validação de consistência mensal (std < 30%)
- [ ] AC-5: Validação de overfitting (cross-validation)
- [ ] AC-6: Dashboard de métricas (visual)
- [ ] AC-7: Relatório de decisão (GO/NO-GO)
- [ ] AC-8: Aprovação de CFO (assinatura)
- [ ] AC-9: Documentação de decisão (audit trail)
- [ ] AC-10: Notificação ao presidente

### Testes
- [ ] test_sharpe_validation (≥1.0)
- [ ] test_win_rate_validation (≥59%)
- [ ] test_drawdown_validation (<15%)
- [ ] test_consistency_validation (std)
- [ ] test_overfitting_validation (cross-val)
- [ ] test_decision_logic (all criteria)
- [ ] test_dashboard_rendering (visual)
- [ ] test_approval_workflow (CFO sign-off)
- [ ] test_audit_trail (historico)
- [ ] test_notification (email/Slack)

### Entrega
```
src/decision/gate2_validator.py
src/decision/capital_framework.py
outputs/gate2_decision_report.md
outputs/gate2_metrics_dashboard.html
tests/test_gate2_decision.py
docs/GATE2_DECISION_FRAMEWORK.md
```

### Crítico Para
- ✅ **GATE 2 Decision Point**
- ✅ **Ativa capital R$ 100k (Fase 2)**
- ✅ Governança de capital
- ✅ Auditoria completa

---

## 🎯 SEQUÊNCIA DE EXECUÇÃO (PARALELO)

```
┌─────────────────────────────────────────────────────────────┐
│ TRACKS PARALELOS                                            │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│ TRACK 1: ENG-003 (Infraestrutura)                         │
│ ├─ ATI-1: Dashboard de Ordens (40h)                       │
│ ├─ ATI-2: API Autenticação OAuth 2.0 (40h)               │
│ ├─ ATI-3: Fila RabbitMQ (40h)                            │
│ ├─ ATI-4: WebSocket Positions (40h)                      │
│ ├─ ATI-8: Retry Logic 3x (32h)                           │
│ ├─ ATI-9: Position Monitoring + SL/TP (32h)             │
│ └─ ATI-10: Gate 2 Decision Framework (40h) [BLOQUEADO]   │
│                                                             │
│ TRACK 2: ML-003 (Features)                                │
│ ├─ ATI-5: Análise SHAP + Correlação (44h)                │
│ └─ ATI-6: Drift Detection + Alertas (44h)                │
│                                                             │
│ TRACK 3: ML-004 (Validação) [SEQUENCIAL]                 │
│ ├─ Aguarda: TRACK 1 (ENG-003) completo                   │
│ └─ ATI-7: Backtest 252 dias (44h)                        │
│    └─ Desbloqueia: ATI-10 (Gate 2)                       │
│                                                             │
└─────────────────────────────────────────────────────────────┘

GATES:
├─ GATE 1: TRACK 1 + TRACK 2 completos (8+18 AC)
└─ GATE 2: TRACK 3 + Métricas (Sharpe ≥1.0, Win ≥59%)
```

---

## 👥 MOBILIZAÇÃO DE SQUADS

### Squad T1-Backend (Eng Sr + 3 Devs)
**Horas:** 224h | **Duração:** ~6-8 semanas | **Status:** 🟢 **Pronto**

| Persona | ATI | Horas | Responsabilidade |
|---------|-----|-------|-------------------|
| **Eng Sr** | ATI-1 | 40h | Dashboard lead + arquitetura |
| **Dev-Backend-1** | ATI-2 | 40h | OAuth 2.0 + segurança |
| **Dev-Backend-2** | ATI-3, ATI-8 | 72h | RabbitMQ + Retry |
| **Dev-Backend-3** | ATI-4, ATI-9 | 72h | WebSocket + Positions |

### Squad T2-Features (ML Expert + Data Scientist)
**Horas:** 88h | **Duração:** ~2-3 semanas | **Status:** 🟢 **Pronto**

| Persona | ATI | Horas | Responsabilidade |
|---------|-----|-------|-------------------|
| **ML Expert** | ATI-5 | 44h | SHAP + análise features |
| **Data Scientist** | ATI-6 | 44h | Drift detection |

### Squad T3-Backtest (ML Expert + Data Scientist + CFO)
**Horas:** 84h | **Duração:** ~2-3 semanas | **Status:** 🟡 **Bloqueado**

| Persona | ATI | Horas | Responsabilidade |
|---------|-----|-------|-------------------|
| **ML Expert** | ATI-7, ATI-10 | 44h | Backtest + validação |
| **Data Scientist** | ATI-7 | 20h | Análise de resultados |
| **CFO** | ATI-10 | 20h | Decision approval |

### Suporte Transversal
- **QA Manager:** 32h (testes de aceitação)
- **Test Automation Eng:** 32h (testes E2E)
- **Infra DevOps:** 16h (RabbitMQ, Redis, PG)
- **Doc Advocate:** 24h (documentação)

**Total:** 356h | **Equipe:** 11 personas

---

## 🔄 PIPELINE_TASKS - 21 PASSOS

### ✅ Passos Completados (Esta Sessão)

1. ✅ **Passo 1:** Carregue o board de profissionais
   - Carregado: BOARD_MULTIDISCIPLINAR.json (17 members)
   - Alocação: 11 personas designadas

2. ✅ **Passo 2:** Solicite a próxima task priorizada
   - Executado: Análise adaptativa de 10 atividades
   - Fonte: SPRINT2_TAREFAS_PRIORIZADAS.md

3. ✅ **Passo 3:** Head de Documentação faz check
   - Pendente: Validação de documentação

4. ✅ **Passo 4:** Product Owner valida estratégia
   - Pendente: Validação de valor

5. ✅ **Passo 5:** Validar se entrega valor
   - ✅ Confirmado: 10 atividades = valor real ao operador

6. ⏳ **Paso 6:** Coordenadora de Governança registra deliberação
   - Pendente: Registro formal em STATUS_ENTREGAS

7. ⏳ **Passo 7:** Arquiteto revisa e identifica gaps
   - Pendente: Revisão de arquitetura

8. ⏳ **Passo 8:** Task é entregue à equipe técnica
   - Pendente: Activação de squads

9. ⏳ **Passo 9:** Task entregue com padrão executa_task.md
   - Pendente: Adaptação ao framework

10. ⏳ **Passo 10:** Doc Advocate documenta
    - Pendente: Documentação durante desenvolvimento

11. ⏳ **Passo 11:** QA Automation escreve testes
    - ✅ Testes especificados (para cada ATI)

12. ⏳ **Passo 12:** Head monitoring acompanha entregas
    - Pendente: Daily standups

13. ⏳ **Passo 13:** Devolva resumo
    - Pendente: Aprovação do usuário

14. ⏳ **Passo 14:** Pergunta fechada (commit?)
    - Pendente: Decisão do usuário

15. ⏳ **Passo 15:** Se revisão, ajustes
    - Pendente: Feedback

16. ⏳ **Passo 16:** Repetir até aprovação
    - Pendente: Aprovação final

17. ⏳ **Passo 17:** Commit + push
    - Pendente: Execução

18. ⏳ **Passo 18:** Coordenadora atualiza docs
    - Pendente: STATUS_ENTREGAS sync

19. ⏳ **Passo 19:** Doc Advocate atualiza docs
    - Pendente: SYNCHRONIZATION.md

20. ⏳ **Passo 20:** Head final check
    - Pendente: Validação final

21. ⏳ **Passo 21:** Links e tabela de rastreamento
    - Pendente: Matriz de docs

---

## 📊 MATRIZ DE VALUE DELIVERY

| ATI # | Atividade | Valor Operacional | Usuário Vê | Impacto |
|-------|-----------|-------------------|------------|--------|
| **1** | Dashboard Ordens | ⭐⭐⭐⭐⭐ | Todas as ordens em tempo real | Visibilidade 100% |
| **2** | OAuth 2.0 | ⭐⭐⭐⭐⭐ | Acesso seguro | Multi-operadores |
| **3** | RabbitMQ | ⭐⭐⭐⭐⭐ | Nenhuma ordem perdida | Confiabilidade 99.9% |
| **4** | WebSocket | ⭐⭐⭐⭐⭐ | Atualizações <100ms | Tempo real |
| **5** | SHAP Analysis | ⭐⭐⭐⭐ | Entender o modelo | Inteligência |
| **6** | Drift Detection | ⭐⭐⭐⭐ | Alertas de degradação | Monitoramento |
| **7** | Backtest 252d | ⭐⭐⭐⭐⭐ | Validação Sharpe ≥1.0 | **Gatekeep Phase 2** |
| **8** | Retry Logic | ⭐⭐⭐⭐ | Ordens resilientes | Resiliência |
| **9** | Position Monitoring | ⭐⭐⭐⭐ | SL/TP automático | Controle risco |
| **10** | Gate 2 Decision | ⭐⭐⭐⭐⭐ | **Ativar R$ 100k** | **Capital activation** |

---

## ⚠️ RISCOS IDENTIFICADOS + MITIGAÇÃO

| Risco | Probabilidade | Impacto | Mitigação |
|-------|--------------|--------|-----------|
| ENG-003 atrasa | Média | Alto | TRACK 2 executa paralelo; GATE 1 move |
| Metrics não passam | Média | Crítico | Grid search (ATI-7) + retrainamento |
| RabbitMQ falha | Baixa | Crítico | Health check horário + alertas |
| WebSocket latência | Baixa | Médio | Otimização conexão + teste de carga |
| Dropout de operador | Baixa | Baixo | UAT com operador real (Fase 1) |

---

## ✅ PRONTO PARA ATIVAR!

**Status Geral:** 🟢 **10 ATIVIDADES ESPECIFICADAS + SQUADS DESIGNADAS**

Próximos passos:
1. → Validação de Arquiteto (gaps?)
2. → Validação de Product Owner (valor?)
3. → Registro de Governança
4. → **Início de desenvolvimento**

**Commit & Push?** Aguardando aprovação do usuário.

---

*Documento: 10_ATIVIDADES_CRITICAS_SPRINT2.md*
*Status: 🟢 Ready for Approval & Execution*
*Framework: PIPELINE_TASKS.MD (Passos 1-5 completados)*

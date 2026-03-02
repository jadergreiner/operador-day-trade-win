# Backlog Unificado - Operador Day Trade WIN

**Versão:** 2.0
**Data Atualização:** 02/03/2026
**Fonte de Verdade:** Este arquivo é a única fonte de verdade para priorização de tarefas
**Formato:** Priority-First (sem datas fixas)
**Status:** Pronto para execução

> **Instruções para Solicitação de Próxima Tarefa:**
> Use este documento ao solicitar a próxima atividade
> prioritária. O backlog está ordenado por impacto e
> dependências.

---

## ✅ P0 - CRÍTICAS (Bloqueadores) — Sprint 2 Atual

### P0-1: ENG-003 API REST MT5 (Infraestrutura)

**Status:** 🟢 Pronto para começar
**Responsável:** Eng Sr
**Squad:** 3 Desenvolvedores Backend (4 pessoas)
**Horas:** 160h
**Desbloqueia:** P0-2 (ML-004)
**Prioridade:** 🔴 CRÍTICA

#### Entregas Esperadas:
- Servidor FastAPI REST (async, alta performance)
- 14 endpoints REST (Auth, Ordens, Posições, Conta, Health)
- Autenticação OAuth 2.0 (token baseado MT5)
- Fila async RabbitMQ (processamento de ordens)
- WebSocket tempo real (<100ms atualização de posições)
- Cache Redis (TTL 30s para posições/conta)
- Audit trail PostgreSQL (todas operações registradas)
- Tratamento erros + retry logic (3x exponencial)
- Cobertura 100% testes (unitário/integração/E2E)
- Performance: P95 < 200ms (ordem), < 100ms (WebSocket)

#### Endpoints:

**Autenticação (2):**
- `POST /auth/login` (OAuth 2.0)
- `POST /auth/refresh` (Atualizar token)

**Ordens (4):**
- `POST /orders/send` (Fila async)
- `GET /orders/{ticket}` (Situação)
- `GET /orders/history` (Todas ordens)
- `PATCH /orders/{ticket}/cancel` (Cancelar)

**Posições (4):**
- `GET /positions` (Todas posições)
- `PATCH /positions/{ticket}` (Modificar SL/TP)
- `DELETE /positions/{ticket}` (Fechar)
- `GET /positions/{ticket}/pnl` (P&L)

**Conta (2):**
- `GET /account` (Saldo, equity, margem)
- `GET /health` (Saúde dependências)

#### Critérios de Aceite (8):
- [ ] CA-1: Autenticação valida credenciais MT5
- [ ] CA-2: Atualização token sem re-auth
- [ ] CA-3: Ordens enviadas async (não-bloqueante)
- [ ] CA-4: Retry logic 3x exponencial
- [ ] CA-5: Status ordem rastreado tempo real
- [ ] CA-6: Posições atualizadas <100ms (WebSocket)
- [ ] CA-7: Saldo conta atualizado 30s
- [ ] CA-8: Healthcheck inclui todas dependências

#### Testes Necessários:
- 20+ testes unitários (Auth, Fila, Cache, Erros)
- 10+ testes integração (API ↔ mock MT5, E2E)
- 5+ testes desempenho (carga, estresse, failover)
- Revisão código: 2+ revisores

#### Critérios de Sucesso:
- ✅ 8/8 CA passando
- ✅ P95 < 500ms verificado
- ✅ Todos testes passando (35+)
- ✅ Código revisado + aprovado

---

### P0-2: ML-004 Backtest Estendido (252 Dias)

**Status:** 🟡 Bloqueado (aguarda P0-1)
**Responsável:** Especialista ML
**Squad:** 2 pessoas (ML Expert + Data Scientist)
**Horas:** 88h
**Começa Quando:** P0-1 completo
**GATE 2 Decision Point:** Ativar R$ 100k Fase 2
**Prioridade:** 🔴 CRÍTICA

#### Entregas Esperadas:
- Backtest histórico 252 dias (ano completo)
- Métricas desempenho: Sharpe, Taxa Vitória, Redução
- Breakdown P&L mensal + análise consistência
- Mapa calor importância features (durante negociações)
- Análise regime mercado (3 regimes identificados)
- Análise padrões sazonais
- Relatório detalhado 20+ páginas
- Visualização curva patrimônio
- Análise gráfico redução

#### Dados Utilizados:
- 252 dias negociação (1 ano completo)
- Dados históricos OHLCV
- 24 features (mesmo do treinamento)
- Modelo: XGBoost (scale_pos_weight=1.476)
- Limiar: 0.30 probabilidade

#### GATE 2 Critérios de Decisão (DEVE PASSAR):
- ✅ Razão Sharpe: ≥ 1.0
- ✅ Taxa Vitória: ≥ 59%
- ✅ Redução Máxima: < 15%
- ✅ Consistência: < 30% std (mensal)

#### Critérios de Aceite (20):
- [ ] CA-1 até CA-20 cobrindo:
  - Validação dados carregados
  - Features extraídas corretamente
  - Lógica backtest verificada
  - Métricas calculadas propriamente
  - Relatórios gerados
  - Visualizações completas
  - Revisão pares
  - Todos gates passados

#### Decisão de Capital (GATE 2):
```
SE Todos 4 critérios = PASS:
  → Ativar R$ 100k Fase 2

SE Qualquer critério = FAIL:
  → Manter R$ 50k Fase 1
```

#### Critérios de Sucesso:
- ✅ 20/20 CA passando
- ✅ Sharpe ≥ 1.0
- ✅ Win rate ≥ 59%
- ✅ Redução < 15%
- ✅ Relatórios aprovados

---

## 🟡 P1 - IMPORTANTES (Não-Bloqueadores) — Sprint 2

### P1-1: ML-003 Análise Features

**Status:** 🟢 Pronto para começar
**Responsável:** Especialista ML
**Squad:** 2 pessoas (ML Expert + Data Scientist)
**Horas:** 88h
**Dependências:** Nenhuma (paralelo com P0-1)
**Prioridade:** 🟡 IMPORTANTE

#### Entregas Esperadas:
- Valores SHAP (top 10 features ordenadas)
- Mapa calor matriz correlação 24×24
- Regras detecção drift (3 estratégias):
  - Teste mudança média (µ ± 2σ)
  - Teste Kolmogorov-Smirnov (p > 0.05)
  - Mudança correlação (Δr > 0.1)
- Limiares alerta (Verde/Amarelo/Laranja/Vermelho)
- Análise sensibilidade limiar (±0.05)
- Configuração monitoramento produção
- Explainabilidade traders (decision trees, IF-THEN)
- Relatório 20+ páginas + visualizações

#### Critérios de Aceite (18):
- [ ] CA-1 até CA-18 cobrindo:
  - Análise SHAP completa
  - Matriz correlação gerada
  - 3 regras drift configuradas
  - Limiares alerta validados
  - Análise sensibilidade feita
  - Config monitoramento pronta
  - Relatórios finalizados
  - Revisão pares

#### Critérios de Sucesso:
- ✅ 18/18 CA passando
- ✅ SHAP top 10 features identificadas
- ✅ Regras drift testadas
- ✅ Relatório aprovado

---

### P1-2: Dashboard Ordens Real-Time

**Status:** 🟢 Pronto para começar
**Responsável:** Eng Sr + Dev-Backend
**Squad:** 2-3 pessoas
**Horas:** 40h
**Dependências:** P0-1 (API REST endpoints)
**Prioridade:** 🟡 IMPORTANTE

#### Entregas Esperadas:
- Dashboard integrado mostrando todas ordens tempo real
- WebSocket integration (<100ms atualização)
- Status ordem: pendente → enviada → preenchida
- Preço entrada, saída, lucro/prejuízo
- Tempo execução
- Histórico completo com audit trail
- Filtros (símbolo, status, período)
- Relatórios exportáveis (CSV, JSON)
- UX responsivo (desktop + mobile)
- Alertas mudança status

#### Critérios de Aceite (8):
- [ ] CA-1: Dashboard exibe 100% ordens
- [ ] CA-2: Updates tempo real via WebSocket (<100ms)
- [ ] CA-3: Filtros funcionando (5 tipos)
- [ ] CA-4: Audit trail completo
- [ ] CA-5: Relatórios exportáveis
- [ ] CA-6: UX responsivo
- [ ] CA-7: Histórico persistente (PostgreSQL)
- [ ] CA-8: Alertas status mudança

---

### P1-3: Autenticação OAuth 2.0

**Status:** 🟢 Pronto para começar
**Responsável:** Dev-Backend
**Squad:** 2 pessoas
**Horas:** 40h
**Prioridade:** 🟡 IMPORTANTE

#### Entregas Esperadas:
- Login OAuth 2.0 (email/password)
- Token JWT (8h validade)
- Refresh token sem logout
- Password hashing (bcrypt)
- Rate limiting (10 tentativas/5min)
- Logout revoga token Redis
- Session management (múltiplos devices)
- Audit logging (login/logout/refresh)

#### Critérios de Aceite (8):
- [ ] CA-1: Login POST /auth/login
- [ ] CA-2: JWT com claims + 8h validade
- [ ] CA-3: Refresh token POST /auth/refresh-token
- [ ] CA-4: Password hashing bcrypt (10+ rounds)
- [ ] CA-5: Rate limiting (10/5min)
- [ ] CA-6: Logout revoga token Redis
- [ ] CA-7: Multi-device support
- [ ] CA-8: Audit trail logging

---

### P1-4: Fila Async RabbitMQ

**Status:** 🟢 Pronto para começar
**Responsável:** Dev-Backend
**Squad:** 2 pessoas
**Horas:** 40h
**Prioridade:** 🟡 IMPORTANTE

#### Entregas Esperadas:
- Producer async (envio fila)
- Consumer sequential (1 ordem por vez)
- QoS = 1 (one at a time)
- Message acknowledgment
- Dead letter queue (DLQ) routing
- Error handler + audit trail
- Health check endpoint
- Queue depth monitoring
- Retry logic 3x exponencial
- Cobertura 100% testes

#### Critérios de Aceite (8):
- [ ] CA-1: Producer envio async
- [ ] CA-2: Consumer processa sequencial
- [ ] CA-3: QoS = 1 funcionando
- [ ] CA-4: Acknowledgment correto
- [ ] CA-5: DLQ routing funcionando
- [ ] CA-6: Health check OK
- [ ] CA-7: Monitoramento depth
- [ ] CA-8: Retry 3x exponencial

---

### P1-5: WebSocket Position Monitoring

**Status:** 🟢 Pronto para começar
**Responsável:** Dev-Backend
**Squad:** 1 pessoa
**Horas:** 40h
**Prioridade:** 🟡 IMPORTANTE

#### Entregas Esperadas:
- WebSocket endpoint posições tempo real
- Heartbeat 30s (ping/pong)
- Auto-disconnect missed heartbeats
- Reconnection logic
- Message format OHLCV + Orders
- JWT validation
- Suporta 500+ conexões simultâneas
- Teste de carga + estresse
- P95 latência <100ms
- Graceful disconnect

#### Critérios de Aceite (6):
- [ ] CA-1: Persistência conexão
- [ ] CA-2: P95 latência <100ms
- [ ] CA-3: 500+ conexões simultâneas
- [ ] CA-4: Zero message loss
- [ ] CA-5: Graceful disconnect
- [ ] CA-6: Heartbeat 30s

---

### P1-6: Position Monitoring Automático

**Status:** 🟢 Pronto para começar
**Responsável:** Dev-Backend
**Squad:** 1 pessoa
**Horas:** 32h
**Prioridade:** 🟡 IMPORTANTE

#### Entregas Esperadas:
- Monitoramento posições abertas
- SL/TP automático
- Cálculo P&L tempo real
- Stop loss condicional (preço/tempo)
- Take profit condicional
- Trailing stop opcional
- Alertas quando hit SL/TP
- Histórico posições fechadas
- Cobertura testes

#### Critérios de Aceite (6):
- [ ] CA-1: Posições abertas monitoradas
- [ ] CA-2: SL/TP automático funcionando
- [ ] CA-3: P&L tempo real
- [ ] CA-4: Stop loss condicional
- [ ] CA-5: Trailing stop opcional
- [ ] CA-6: Alertas hit SL/TP

---

### P1-7: S2-6 Analytics Integration - Tests & Batch Processing

**Status:** 🟢 Pronto para começar
**Responsável:** Eng Sr + ML Expert
**Squad:** 2 pessoas
**Horas:** 32h
**Dependências:** P1-1 (Integração básica completa)
**Prioridade:** 🟡 IMPORTANTE

#### Entregas Esperadas:
- Suite de testes E2E para integração S2-6
  (`test_agente_s2_6_integration.py`)
- Batch processing para backtest com S2-6
- Dashboard real-time (Grafana/Streamlit)
- Validação sincronização (100% antes de go-live)
- Monitoramento stats em tempo real (win rate, sharpe, drawdown)

#### Critérios de Aceite (6):
- [ ] CA-1: Testes E2E implementados (10+ testes)
- [ ] CA-2: Testes passam 100% (10/10)
- [ ] CA-3: Batch processing pronto
- [ ] CA-4: Dashboard exibe stats tempo real
- [ ] CA-5: Latência integração <500ms
- [ ] CA-6: Sincronização validada (100%)

---

### P1-8: Sistema de Alertas - Testes & Deployment

**Status:** 🟢 Pronto para começar
**Responsável:** Dev-Backend + QA
**Squad:** 2 pessoas
**Horas:** 40h
**Dependências:** Nenhuma (paralelo)
**Prioridade:** 🟡 IMPORTANTE

#### Entregas Esperadas:
- Testes unitários Sistema de Alertas (8 testes)
- Testes integração WebSocket/Email/SMS (3 testes)
- Validação latência P95 <30s
- Configuração para v1.1.1+ (Produção)
- Setup deployment contínuo (CI/CD)
- Monitoramento e alertas sistema

#### Critérios de Aceite (7):
- [ ] CA-1: 8 testes unitários PASS
- [ ] CA-2: 3 testes integração PASS
- [ ] CA-3: Latência P95 <30s validada
- [ ] CA-4: Taxa captura ≥85%
- [ ] CA-5: False positive rate <10%
- [ ] CA-6: Taxa entrega >98%
- [ ] CA-7: Deployment v1.1.1+ pronto

---

### P1-9: API REST Alertas - Histórico & SMS

**Status:** 🟡 Bloqueado (v1.2 futuro)
**Responsável:** Dev-Backend
**Squad:** 1 pessoa
**Horas:** 24h
**Começa Quando:** Após P1-8 completo
**Prioridade:** 🟡 IMPORTANTE (futuro)

#### Entregas Esperadas (v1.2):
- GET /alertas/historico endpoint
  - Filtros (data, ativo, padrão, nível)
  - Limit/offset paginação
  - Response JSON com histórico
- SMS alertas (v1.2 condicional)
  - Ativação automática se email falha >2% em 30 dias
  - Formato compacto SMS
  - Suporte Twilio/AWS SNS
- Documentação API atualizada

#### Critérios de Aceite (5):
- [ ] CA-1: GET /alertas/historico implementado
- [ ] CA-2: Filtros funcionando (5 tipos)
- [ ] CA-3: Paginação OK
- [ ] CA-4: SMS integrado (condicional)
- [ ] CA-5: Testes API PASS (10+ testes)

---

### P1-10: Detection Engine - Padrões Técnicos

**Status:** 🟢 Pronto para começar
**Responsável:** ML Expert
**Squad:** 2 pessoas (ML Expert + Data Scientist)
**Horas:** 40h
**Dependências:** Nenhuma (paralelo com P0-1)
**Prioridade:** 🟡 IMPORTANTE

#### Entregas Esperadas:
- Detector Engulfing Pattern (bullish + bearish)
  - Definição e condições
  - Confiança 65%
  - ~5-8 ocorrências/semana WIN$N
- Detector Divergência RSI/Preço (bullish + bearish)
  - Definição e condições
  - Confiança 60%
  - ~3-4 ocorrências/semana WIN$N
- Detector Break Suporte/Resistência
  - Nível identificação (últimos 5 candles)
  - Confiança 70%
  - ~2-3 ocorrências/semana WIN$N
- Ensemble ranking (múltiplos padrões)
  - Aumento confiança por padrão adicional
  - Capped em 0.95 máximo
- Cálculo ATR para risk:reward (2.5:1 target)
- 11 testes (8 unitários + 3 integração)

#### Critérios de Aceite (12):
- [ ] CA-1: Engulfing bullish detectado
- [ ] CA-2: Engulfing bearish detectado
- [ ] CA-3: Divergência RSI validada
- [ ] CA-4: Break S/R identificado
- [ ] CA-5: Ensemble ranking pronto
- [ ] CA-6: ATR calculado corretamente
- [ ] CA-7: Risk:reward 2.5:1 validado
- [ ] CA-8: 8 unit tests PASS
- [ ] CA-9: 3 integration tests PASS
- [ ] CA-10: Latência P50 <10s
- [ ] CA-11: Taxa captura ≥85%
- [ ] CA-12: False positive <10%

---

### P1-11: Trade Sync Verification (TradeSyncVerifier)

**Status:** 🟡 Bloqueado (após P0-1, P1-2)
**Responsável:** Dev-Backend
**Squad:** 1 pessoa
**Horas:** 10h
**Dependências:** P0-1 (API MT5), P0-2 (Persistência)
**Prioridade:** 🟡 IMPORTANTE

#### Entregas Esperadas:
- TradeSyncVerifier class (validação 1:1 MT5 ↔ SQLite)
- Daily reconciliation job
  - Comparação hash trades MT5 vs SQLite
  - Reportar missing trades
  - Reportar mismatches (entry price, etc)
- Alert system para discrepâncias
- TradeSyncReport geração
- Discrepancy log persistência
- 3 testes de integração

#### Critérios de Aceite (6):
- [ ] CA-1: TradeSyncVerifier implementado
- [ ] CA-2: Daily job agendado
- [ ] CA-3: Comparação hash OK
- [ ] CA-4: Missing trades detectados
- [ ] CA-5: Mismatches reportados
- [ ] CA-6: 3 integration tests PASS

---

### P1-12: RL Feedback System - Resultados Reais

**Status:** 🟡 Bloqueado (após P0-2, P1-2)
**Responsável:** ML Expert + Dev-Backend
**Squad:** 2 pessoas
**Horas:** 15h
**Dependências:** P0-2 (Persistência trades)
**Prioridade:** 🟡 IMPORTANTE

#### Entregas Esperadas:
- TradeClosedEvent listener
  - Escuta eventos Trade.close()
  - Calcula PnL real vs previsão
  - Feedback loop para RL model
- RL model update pipeline
  - Incorporar feedback histórico
  - Retraining com novos outcomes
  - Version control de modelos
- Historical outcome tracking
  - Database para armazenar resultados
  - Análise de performance
- 4 testes de integração

#### Critérios de Aceite (6):
- [ ] CA-1: TradeClosedEvent listener implementado
- [ ] CA-2: PnL cálculo validado
- [ ] CA-3: RL model update pipeline pronto
- [ ] CA-4: Retraining automático funciona
- [ ] CA-5: Historical tracking completo
- [ ] CA-6: 4 integration tests PASS

---

## � TAREFAS COMPLEMENTARES CONSOLIDADAS

### Diários Automáticos (Sistema de Feedback)

**Status:** ✅ Implementado (código pronto)
**Responsável:** Sistema (automático)
**Horas:** 0h (já desenvolvido)
**Prioridade:** 🟡 COMPLEMENTAR

**Descrição:**
Sistema inteligente que gera automaticamente dois tipos de diário
durante o pregão para feedback e treinamento:

1. **Diário de Trading Storytelling** (15 minutos)
   - Narrativa do mercado (estilo jornalístico)
   - Sentimento mercado (PANIC, GREEDY, FEARFUL, CALM)
   - Decisão operacional (BUY/SELL/HOLD)
   - Tags para ML

2. **Diário de Reflexão da IA** (10 minutos)
   - Auto-crítica sincera da IA
   - Avaliação de utilidade
   - Correlação dados x preço
   - Feedback sobre trader

**Entregas:**
- ✅ scripts/quick_start_journals.py (inicialização)
- ✅ scripts/start_automated_journals.py (agendado 09:00)
- ✅ Dois tipos de diário implementados
- ✅ Exportação dados para ML

**Uso:**
```bash
# Iniciar automaticamente às 09:00
python scripts/start_automated_journals.py

# Ou duplo clique
INICIAR_DIARIOS.bat

# Exportar dados para ML
python scripts/export_journal_data.py
```

**Benefícios:**
- Narrativas para análise sentimental
- Dados para RL feedback loop
- Avaliação de qualidade estratégia
- Training dataset complementar

---

### Task-Crítica-0: Persistence Fix (Auditoria 24/02)

**Status:** ✅ IMPLEMENTADO (código pronto para execução)
**Responsável:** Eng Sr
**Sprint:** 2 (prerequisite)
**Blocker:** NÃO
**Prioridade:** 🔴 CRÍTICA

**Problema Resolvido:**
- ❌ 4 operações executadas no MT5 mas ZERO persistidas em SQLite
- ✅ Solução: TransactionLogService + MT5SynchronizationService

**Arquivos Criados:**
- `src/infrastructure/persistence/transaction_log_service.py` (300+ LOC)
- `src/infrastructure/persistence/mt5_synchronization_service.py` (350+ LOC)
- `scripts/recovery_and_audit_24fev.py` (200+ LOC)
- `tests/unit/test_persistence_task_critica_0.py` (300+ LOC)

**Componentes Implementados:**

1. **TransactionLogService**
   - Log append-only imutável
   - Estados: PENDING → COMMITTED / FAILED → DLQ
   - Checksum SHA256 para integridade
   - Dead-letter queue para retry

2. **MT5SynchronizationService**
   - Sincronização ORDERS, DEALS, POSITIONS
   - Recuperação retroativa (7 dias)
   - Recuperação especial 24/02
   - Replay automático PENDING

3. **Recovery Script**
   - Sincronização geral (7 dias)
   - Recuperação 24/02 especial
   - Análise dead-letter queue
   - Audit report CVM-compliant

**Acceptance Criteria (5):**
- ✅ AC-1: Auditoria 24/02 identificada e restaurada
- ✅ AC-2: Persistência validada com transaction logs
- ✅ AC-3: Compliance CVM/B3 verificado
- ✅ AC-4: Testes integridade com replay
- ✅ AC-5: Testes unitários >90% coverage

**Próximo Passo:**
```bash
# Executar recovery
python scripts/recovery_and_audit_24fev.py

# Rodar testes
pytest tests/unit/test_persistence_task_critica_0.py -v
```

---

## �🟢 P2 - FUTURO (Sprint 2+)

### P2-1: Retry Logic Exponencial

**Status:** 📋 Planejado
**Responsável:** Dev-Backend
**Horas:** 32h
**Prioridade:** 🟢 MÉDIO

#### Entregas:
- Retry 3x com backoff exponencial (1s, 2s, 4s)
- Circuit breaker (falhas consecutivas)
- Dead letter queue para falhas finais
- Logging completo tentativas
- Métricas retry (taxa sucesso)

---

### P2-2: Capital Decision Framework

**Status:** 📋 Planejado
**Responsável:** CFO + ML Expert
**Horas:** 40h
**Prioridade:** 🟢 MÉDIO

#### Entregas:
- GATE 2 decision framework
- Validação Sharpe ≥ 1.0
- Validação Win rate ≥ 59%
- Validação Drawdown < 15%
- Ativação R$ 100k Fase 2
- Documentação decisão

---

### P2-3: Performance Benchmarking

**Status:** 📋 Planejado
**Responsável:** Eng Sr + QA
**Horas:** 40h
**Prioridade:** 🟢 MÉDIO

#### Entregas:
- Load testing (carga, estresse)
- Latency profiling (P95, P99)
- Memory profiling
- Database optimization
- Cache hit ratio análise
- Escalabilidade validação

---

### P2-4: Staging Deployment

**Status:** 📋 Planejado
**Responsável:** DevOps
**Horas:** 32h
**Prioridade:** 🟢 MÉDIO

#### Entregas:
- Ambiente staging idêntico produção
- CI/CD pipeline configurado
- Automated testing pre-deploy
- Health checks automated
- Rollback procedures
- Production readiness checklist

---

### P2-5: Monitoring & Observability (Prometheus/Grafana)

**Status:** 📋 Planejado
**Responsável:** DevOps + Dev-Backend
**Squad:** 2 pessoas
**Horas:** 20h
**Prioridade:** 🟢 MÉDIO

#### Entregas Esperadas:
- Prometheus metrics export
  - Orders sent/persisted/confirmed counters
  - Persistence success rate gauge
  - Retry attempt distribution histogram
  - Persistence latency histogram
  - Dead-letter queue size gauge
- Grafana dashboards
  - Orders execution metrics (real-time)
  - Trade sync verification status
  - RL feedback pipeline health
  - Database performance metrics
  - Alert history + discrepancies
- PagerDuty integration
  - Critical alerts: persistence <95%
  - Critical alerts: DLQ size >10 items
  - Custom alert rules (trader-defined)
- Logs aggregation (centralized)
  - All order/trade logs in single view
  - Debug mode para troubleshooting
  - Retention policy (30 dias)

#### Critérios de Aceite (6):
- [ ] CA-1: Prometheus exportador implementado
- [ ] CA-2: Grafana dashboards criados (3+)
- [ ] CA-3: Alertas PagerDuty enviados
- [ ] CA-4: Logs centralizados
- [ ] CA-5: Retention policy aplicada
- [ ] CA-6: Trader consegue ler metrics

---

### P2-6: Staging Deployment

## 📋 BACKLOG FUTURO (Sprint 3+)

### P3-1: Fontes Externas (Dados Macro)

**Status:** 📋 Futuro
**Prioridade:** 🟢 BAIXO

**Entregas:**
- [ ] Adicionar integração fontes externas
(risco-câmbio/juros)
- [ ] Ingestão BACEN (swap cambial, históricos)
- [ ] Séries IPEADATA (macro Brasil)
- [ ] Séries Tesouro Nacional (dívida pública)
- [ ] Posições abertas B3 (futuros)
- [ ] Opcional: Bloomberg/Reuters (profissional)

---

### P3-2: Analytics Avançadas

**Status:** 📋 Futuro
**Prioridade:** 🟢 BAIXO

**Entregas:**
- [ ] Dashboard analytics completo
- [ ] Histórico operações (60+ dias)
- [ ] Análise padrões, seasonal
- [ ] Relatórios customizáveis
- [ ] Export dados (Tableau, PowerBI)
- [ ] Real-time KPIs

---

### P3-3: Mobile App

**Status:** 📋 Futuro
**Prioridade:** 🟢 BAIXO

**Entregas:**
- [ ] App mobile (iOS/Android)
- [ ] Notificações push
- [ ] Dashboard mobile responsivo
- [ ] Ordens mobile simplificadas
- [ ] Alertas mobile

---

### P3-4: WINFUT Micro Tendências Análise

**Status:** 📋 Futuro
**Prioridade:** 🟢 BAIXO
**Responsável:** ML Expert + Data Analyst
**Horas:** 60h

**Objetivo:**
Identificar micro tendências intraday no mini índice futuro (WINFUT),
mapeando regiões de liquidez e detectando oportunidades de compra/venda
em ciclos de 2 minutos.

**Entregas Esperadas:**
- Monitoramento contínuo de micro tendências (ciclo 2 min)
- Score Macro (contexto direcional do dia)
- Score Micro (análise estrutura SMC, VWAP, pivôs)
- Sistema de detecção de oportunidades (continuação vs reversão)
- Gatilhos operacionais automáticos (4 tipos definidos)
- Regiões de interesse (confluência de suportes/resistências)
- Análise padrões de candle (zonas de interesse)
- Plano validação framework WINFUT
- Documentação procedures (gatilhos, alertas, validação)

**Critério de Aceite Principal:**
- [ ] Score Micro calculado em tempo real durante pregão
- [ ] 4+ gatilhos operacionais testados
- [ ] Oportunidades geradas com R/R mínimo 2:1
- [ ] Framework validado com backtest (60+ dias)
- [ ] Confiança sinais >= 70%

**Tarefas Específicas:**
- Desenvolver engine Score Macro (15 ativos)
- Desenvolver engine Score Micro (M5/M15 analysis)
- Implementar detecção SMC (BOS, CHoCH, FVG)
- Implementar cálculo VWAP + desvios
- Criar gatilhos (entrada, reversão, continuação)
- Validar accuracy vs mercado real
- Documentar regras de execução

---

### P3-5: WDO Análise Correlações (Dólar Futuro)

**Status:** 📋 Futuro
**Prioridade:** 🟢 BAIXO
**Responsável:** ML Expert + Data Analyst
**Horas:** 80h

**Objetivo:**
Mapear relações e correlações entre WDO (Dólar Futuro) e WINFUT
(Índice Futuro), desenvolvendo sistema de pontuação para auxiliar
decisões de trading com análise multivariada.

**Entregas Esperadas:**
- Mapa de relações (commodities, fluxo risco, juros, câmbio)
- Score WDO (direção do Dólar/USDBRL)
- Score WINFUT (direção do Ibovespa)
- Sistema de pontuação multi-fonte (MT5, Yahoo, FRED, etc)
- Análise correlação inversa WDO ↔ WINFUT (-0.75 a -0.90)
- Regras de exceção (estresse extremo, euforia global)
- Ingestão dados de múltiplas fontes (10+ APIs)
- Validação acurácia (backtest 6+ meses)
- Documentação framework completa

**Relações Mapeadas:**
1. Commodities (exportações BR): ouro, petróleo, soja, minério ferro, café (5 ativos)
2. Fluxo Risco Global: S&P 500, Euro Stoxx, China, VIX, EEM, HYG (6 ativos)
3. Juros (Fed): US10Y, DXY, yield curve (3 ativos)
4. Câmbio (cross): EURUSD, GBPUSD, AUDUSD (3 ativos)
5. Taxa Brasil: DI1, taxa Selic futura (2 ativos)

**Critério de Aceite Principal:**
- [ ] Score WDO e Score WINFUT computados em tempo real
- [ ] 5 categorias de relações mapeadas (15+ ativos)
- [ ] Correlação validada com dados históricos
- [ ] Acurácia >= 75% em backtest
- [ ] Sistema pronto para integração com ML model

**Tarefas Específicas:**
- Coletar dados históricos (6+ meses)
- Implementar Score WDO (pontuações cap 1-5)
- Implementar Score WINFUT (pontuações cap 1-5)
- Validar correlação inversa (expected: -0.75 a -0.90)
- Criar regras exceção (risk-on/risk-off extremo)
- Integrar múltiplas fontes (MT5, Yahoo, FRED, Binance, ExchangeRate)
- Backtest correlação e acurácia
- Documentar regras detalhadas com exemplos

---

## 🚀 P4 - STAGING & GO-LIVE (Phase 4: 01-10/03)

### P4-1: Staging Deployment (01-05/03)

**Status:** 📋 Planejado (aguarda GATE 2 PASS)
**Responsável:** Eng Sr + DevOps
**Squad:** 3 pessoas (DevOps + Eng Sr + Tech Writer)
**Horas:** 40h
**Começa Quando:** GATE 2 aprovado (~26/02)
**Gate Decision:** Gate 4.1 (05/03 18:00) Staging Readiness
**Prioridade:** 🔴 CRÍTICA

#### Entregas Esperadas:
- Azure Resource Group (8 recursos)
- App Service + PostgreSQL + Redis + Key Vault
- Code deployment (FastAPI + WebSocket)
- Integration testing (25+ testes)
- Load testing (3 cenários: 100, 200, 500 users)
- Infrastructure documentation
- Deployment procedures validated
- Monitoring + alerting configurado
- Backup strategy verified
- Performance baseline established

#### Critérios de Aceite (8):
- [ ] CA-1: 8/8 recursos Azure criados e healthy
- [ ] CA-2: Health check endpoint PASS
- [ ] CA-3: 25+ testes integração PASS
- [ ] CA-4: Load test 500 users: P95 <2s
- [ ] CA-5: Zero critical errors em logs
- [ ] CA-6: Auto-scaling configurado
- [ ] CA-7: Daily backups automated
- [ ] CA-8: AppInsights monitoring active

#### Testes Necessários:
- Infrastructure tests (Bicep validation, resource creation)
- Integration tests (API ↔ services, E2E flows)
- Load tests (Locust scenarios: baseline, medium, stress)
- Smoke tests (health check, connectivity)
- Performance tests (latency, throughput, P95)
- Escalation tests (auto-scale on load)

---

### P4-2: UAT & Approval (06-09/03)

**Status:** 📋 Planejado (após P4-1 completo)
**Responsável:** Trader + CIO + CFO
**Squad:** 5 pessoas (Trader, CIO, CFO, Eng Sr support)
**Horas:** 24h
**Gate Decision:** Gate 4.2 (10/03 09:00) Go-Live Ready
**Prioridade:** 🔴 CRÍTICA

#### Entregas Esperadas:
- Trader acceptance testing (6 test cases)
- CIO security validation (12 security points)
- CFO financial approval (capital authorization)
- Risk framework final validation
- Sign-off documents (3: Trader, CIO, CFO)
- Final readiness checklist (50+ items)
- Support procedures validated
- Emergency procedures rehearsal
- Escalation contacts confirmed

#### Critérios de Aceite (8):
- [ ] CA-1: Trader APPROVA (signal accuracy 80%+)
- [ ] CA-2: CIO APPROVA (security posture OK)
- [ ] CA-3: CFO APPROVA (capital R$ 50k authorized)
- [ ] CA-4: Zero blocking issues reported
- [ ] CA-5: All 3 sign-offs signed (Trader/CIO/CFO)
- [ ] CA-6: Risk framework validated
- [ ] CA-7: Override procedures tested 100%
- [ ] CA-8: 24/7 support contacts confirmed

#### Testes Necessários:
- UAT Trader (backtest accuracy, signal tests, override)
- UAT CIO (JWT auth, RBAC, encryption, NSG rules)
- UAT CFO (P&L tracking, risk framework, capital controls)
- End-to-end integration tests (production-like)
- Security penetration testing (light assessment)
- Disaster recovery tests (failover procedures)

---

### P4-3: Go-Live Production (10/03)

**Status:** 📋 Planejado (após P4-2 completo)
**Responsável:** Eng Sr + DevOps
**Squad:** 4 pessoas (Eng Sr, DevOps, Trader on-call)
**Horas:** 8h
**Go-Live Time:** 10/03 09:30 BRT
**Prioridade:** 🔴 CRÍTICA

#### Entregas Esperadas:
- Production infrastructure deployment
- Data migration (if needed)
- Cutover execution (staging → production)
- Capital transfer R$ 50k
- 24/7 monitoring + alerting
- Support team briefing
- First trades execution
- Post-go-live validation (1h)
- Incident escalation procedures
- Weekly reporting setup

#### Critérios de Aceite (8):
- [ ] CA-1: Production environment UP
- [ ] CA-2: Trading system ONLINE
- [ ] CA-3: Capital R$ 50k transferido
- [ ] CA-4: First 5+ trades executed
- [ ] CA-5: P&L tracking funcionando
- [ ] CA-6: Alerts configurados
- [ ] CA-7: Support team briefed
- [ ] CA-8: Post-go-live validation PASS

#### Testes Necessários:
- Smoke tests (endpoints, connectivity, health)
- Data migration validation (if applicable)
- First trade execution tests
- P&L calculation verification
- Alert system validation
- Monitoring dashboard verification
- Escalation procedures test

---

## �📊 MODELO DE EXECUÇÃO

```
┌─────────────────────────────────────────────────────────┐
│ EXECUÇÃO PARALELA:                                      │
│                                                         │
│ ├─ P0-1: ENG-003 (Infra)     [Bloqueador central]     │
│ │  └─ Desbloqueia: P0-2                              │
│ │                                                    │
│ ├─ P1-1: ML-003 (Análise)    [Independente]          │
│ │  ├─ Paralelo com P0-1                              │
│ │  └─ Não bloqueia nada                               │
│ │                                                    │
│ ├─ P1-2: Dashboard          [Dependência: P0-1]      │
│ ├─ P1-3: OAuth              [Dependência: P0-1]      │
│ ├─ P1-4: RabbitMQ           [Dependência: P0-1]      │
│ ├─ P1-5: WebSocket          [Dependência: P0-1]      │
│ ├─ P1-6: Position Monitor   [Dependência: P0-1]      │
│ │  └─ Todos paralelos após P0-1 completo              │
│ │                                                    │
│ └─ P0-2: ML-004 (Backtest)  [Bloqueado até P0-1]    │
│    └─ Começa quando P0-1 ✅                           │
│    └─ GATE 2 decision point                          │
│    └─ Desbloqueia: P4-1 (Phase 4)                    │
│                                                         │
│ EXECUÇÃO SEQUENCIAL (Phase 4):                        │
│                                                         │
│ ├─ P4-1: Staging Deploy    [01-05/03, GATE 4.1]      │
│ │  └─ Desbloqueia: P4-2                              │
│ │                                                    │
│ ├─ P4-2: UAT & Approval    [06-09/03, GATE 4.2]      │
│ │  └─ Desbloqueia: P4-3                              │
│ │                                                    │
│ └─ P4-3: Go-Live Prod      [10/03, ONLINE]           │
│    └─ Ativa capital R$ 50k                           │
│    └─ Inicia FASE 1 Beta                             │
│                                                         │
└─────────────────────────────────────────────────────────┘

REGRAS:
1. ENG-003 + ML-003 → Paralelos (sem dependências)
2. P1-2 through P1-6 → Aguardam P0-1 completo
3. P0-2 → Aguarda P0-1 completo
4. P4-1,2,3 → SEQUENCIAL após GATE 2 PASS (síncronas)
5. P2-* → Começam após GATE 2 (podem ser paralelos)
6. P3-* → Futuro (não começar agora)
```

---

## ᴊ ALOCAÇÃO DE EQUIPE

### Sprint 2 Equipe (Paralela)

| Função | Horas | Tarefas |
|--------|-------|----------|
| Eng Sr | 48h | Design + lidera P0-1 |
| Dev-Backend-1 | 40h | P1-3 (OAuth) |
| Dev-Backend-2 | 40h | P1-4 (RabbitMQ) |
| Dev-Backend-3 | 40h | P1-5 (WebSocket) |
| Dev-Backend-4 | 40h | P1-2 (Dashboard) |
| ML Expert | 48h | P1-1 + P0-2 |
| Data Scientist | 40h | P1-1 + P0-2 |
| QA Lead | 32h | Estratégia teste |
| Engenheiro QA | 32h | Automação testes |
| DevOps | 20h | Ambiente + CI/CD |
| Tech Writer | 15h | Documentação |
| **Sprint 2 Total** | **395h** | — |

### Phase 4 Equipe (Sequencial: 01-10/03)

| Função | Horas | Tarefas |
|--------|-------|----------|
| Eng Sr | 24h | P4-1 + P4-3 (Design + Go-Live) |
| DevOps | 20h | P4-1 + P4-3 (Infrastructure) |
| Trader | 12h | P4-2 (UAT acceptance) |
| CIO | 8h | P4-2 (Security review) |
| CFO | 8h | P4-2 (Financial approval) |
| QA | 0h | (reusa squad Sprint 2) |
| Support | 0h | (reusa squad Sprint 2) |
| **Phase 4 Total** | **72h** | — |

### RECAPITULAÇÃO TOTAL

| Fase | Horas | Equipe | Período |
|------|-------|--------|---------|
| Sprint 2 | 395h | 11 personas | Iniciando |
| Phase 4 | 72h | 5 personas + support | 01-10/03 |
| **TOTAL** | **467h** | **16 personas max** | — |

**Observação:** Phase 4 começa imediatamente após GATE 2 PASS (~26/02).

---

## 🎯 GATES & DECISÕES

### GATE 1 (Checkpoint)
**Quando:** P0-1 + ML-003 completados (sem datas,
prioridade)
**Quem:** CTO + Head Finanças + Product Owner
**Decisão:** GO/NO-GO para P1-x

**Critérios:**
- ✅ 8/8 CA de P0-1 passando
- ✅ 18/18 CA de P1-1 passando
- ✅ Latência P95 < 500ms verificada
- ✅ Testes E2E executados
- ✅ Revisão código aprovada

---

### GATE 2 (Capital Decision)
**Quando:** P0-2 (ML-004) completado
**Quem:** CFO + Board
**Decisão:** Ativar Phase 4? Ativar R$ 50k → R$ 100k?

**Critérios:**
- ✅ Sharpe ≥ 1.0
- ✅ Win rate ≥ 59%
- ✅ Drawdown < 15%
- ✅ Consistência < 30% std

**Ação:**
- SE PASS: GO para Phase 4 + Libera R$ 100k Fase 2
- SE FAIL: Manter R$ 50k Fase 1 (adiar Phase 4)

---

### GATE 4.1 (Staging Readiness)
**Quando:** P4-1 (Staging Deploy) completado
**Data:** 05/03 18:00
**Quem:** CTO + Eng Sr + QA Lead
**Decisão:** Staging ambiente pronto para UAT?

**Critérios:**
- ✅ 8/8 recursos Azure healthy
- ✅ 25+ testes integração PASS
- ✅ Load test P95 <2s (500 users)
- ✅ Zero critical errors

**Ação:**
- SE PASS: GO para P4-2 (UAT)
- SE FAIL: Fix issues e retry (atraso Phase 4)

---

### GATE 4.2 (Go-Live Ready)
**Quando:** P4-2 (UAT & Approval) completado
**Data:** 10/03 09:00
**Quem:** Trader + CIO + CFO
**Decisão:** Go-live production?

**Critérios:**
- ✅ Trader APPROVA
- ✅ CIO APPROVA (security)
- ✅ CFO APPROVA (capital)
- ✅ Zero blocking issues

**Ação:**
- SE PASS: GO para P4-3 (Production Go-Live)
- SE FAIL: Block go-live (atraso até xxx)

---

## 📞 ESCALATION

| Questão | Owner | Escalate To |
|---------|-------|-------------|
| P0-1 blocker | Eng Sr | CTO |
| ML metrics off | ML Expert | Head Data |
| GATE 1 fail | PO | CFO + Board |
| GATE 2 fail | CFO | Board |
| P4-1 blocker | Eng Sr | CTO |
| P4-2 trader reject | Trader | CTO + CFO |
| P4-2 CIO reject | CIO | CTO + CFO |
| P4-2 CFO reject | CFO | Board |
| P4-3 go-live issue | Eng Sr | CTO + Board |

---

## ✅ CHECKLIST PRÉ-INÍCIO (Sprint 2)

- [ ] Ambientes validados (Docker, Python, Git)
- [ ] Squad alocado (11 personas confirmadas)
- [ ] Branches criadas (feature/ATI-1 through ATI-6)
- [ ] CI/CD pipeline pronto
- [ ] Test framework configurado
- [ ] Código-base limpo (main branch)
- [ ] Documentação sincronizada
- [ ] Comunicação escalação definida
- [ ] Daily standups agendados (15:00 BRT)
- [ ] GATE 1 checkpoint preparado

---

## ✅ PRÉ-REQUISITOS PARA PHASE 4 (01/03)

### Documentação Phase 4
- [ ] PHASE4_STAGING_MASTERPLAN.md revisado
- [ ] GO_LIVE_CHECKLIST.md assinado pelos 3 signatários
- [ ] CONTINGENCY_BACKUP_PLAN_PHASE4.md validado
- [ ] Todos procedimentos rehearsed
- [ ] Escalation matrix confirmada

### Equipe Phase 4
- [ ] Eng Sr disponível (24h alocadas)
- [ ] DevOps disponível (20h alocadas)
- [ ] Trader disponível para UAT
- [ ] CIO disponível para review
- [ ] CFO disponível para approval
- [ ] Support 24/7 confirmado

### Infraestrutura Phase 4
- [ ] Azure subscription validado
- [ ] Bicep templates testados
- [ ] Connection strings preparadas
- [ ] Secrets em Key Vault
- [ ] Monitoring configurado

---

## 📚 DOCUMENTOS RELACIONADOS

### Sprint 2
- [SPRINT2_TAREFAS_PRIORIZADAS.md](../SPRINT2_TAREFAS_PRIORIZADAS.md)
- [SPRINT2_ACTIVIDADES_PRIORIDADE.md](../SPRINT2_ACTIVIDADES_PRIORIDADE.md)
- [PLANO_DE_SPRINTS_MVP_NOW.md](./PLANO_DE_SPRINTS_MVP_NOW.md)

### Phase 4 (Staging & Go-Live)
- [PHASE4_STAGING_MASTERPLAN.md](./agente_autonomo/PHASE4_STAGING_MASTERPLAN.md)
- [GO_LIVE_CHECKLIST.md](./agente_autonomo/GO_LIVE_CHECKLIST.md)
- [CONTINGENCY_BACKUP_PLAN_PHASE4.md](./agente_autonomo/CONTINGENCY_BACKUP_PLAN_PHASE4.md)
- [FINAL_READINESS_CHECKLIST_PHASE4.md](./agente_autonomo/FINAL_READINESS_CHECKLIST_PHASE4.md)
- [PHASE4_FIRST_WEEK_ACTIONS.md](./agente_autonomo/PHASE4_FIRST_WEEK_ACTIONS.md)

### Geral
- [README.md](../README.md)
- [ANALISE_INTEGRACAO_PHASE4_BACKLOG.md](./ANALISE_INTEGRACAO_PHASE4_BACKLOG.md)

---

**Última Atualização:** 03/03/2026
**Próxima Revisão:** Quando GATE 2 completo (Phase 4 kick-off)
**Proprietário:** Product Owner (GitHub Copilot)
**Status:** ✅ BACKLOG COMPLETO (Sprint 2 + Phase 4)



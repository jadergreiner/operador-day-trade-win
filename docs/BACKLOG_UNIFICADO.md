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

## 🟢 P2 - FUTURO (Sprint 2+)

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

## 📊 MODELO DE EXECUÇÃO

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
│                                                         │
└─────────────────────────────────────────────────────────┘

REGRAS:
1. ENG-003 + ML-003 → Paralelos (sem dependências)
2. P1-2 through P1-6 → Aguardam P0-1 completo
3. P0-2 → Aguarda P0-1 completo
4. P2-* → Começam após GATE 2 aprovado
5. P3-* → Futuro (não começar agora)
```

---

## ᴊ ALOCAÇÃO DE EQUIPE

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
| **Total** | **395h** | — |

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
**Decisão:** Ativar R$ 50k → R$ 100k Fase 2?  

**Critérios:**
- ✅ Sharpe ≥ 1.0
- ✅ Win rate ≥ 59%
- ✅ Drawdown < 15%
- ✅ Consistência < 30% std

**Ação:**
- SE PASS: Libera R$ 100k Fase 2
- SE FAIL: Manter R$ 50k Fase 1

---

## 📞 ESCALATION

| Questão | Owner | Escalate To |
|---------|-------|-------------|
| P0-1 blocker | Eng Sr | CTO |
| ML metrics off | ML Expert | Head Data |
| Gate criteria fail | PO | CFO + Board |
| Capital decision | CFO | Board |
| Performance issue | Eng Sr | CTO |

---

## ✅ CHECKLIST PRÉ-INÍCIO

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

## 📚 DOCUMENTOS RELACIONADOS

- [SPRINT2_TAREFAS_PRIORIZADAS.md](../SPRINT2_TAREFAS_PRIORIZADAS.md)
- [SPRINT2_ACTIVIDADES_PRIORIDADE.md]
(../SPRINT2_ACTIVIDADES_PRIORIDADE.md)
- [PLANO_DE_SPRINTS_MVP_NOW.md](./PLANO_DE_SPRINTS_MVP_NOW.md)
- [README.md](../README.md)

---

**Última Atualização:** 02/03/2026  
**Próxima Revisão:** Quando P0-1 completo  
**Proprietário:** Product Owner (GitHub Copilot)

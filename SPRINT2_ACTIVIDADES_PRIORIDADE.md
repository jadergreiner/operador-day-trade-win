# 🚀 SPRINT 2 - ATIVIDADES POR PRIORIDADE

**Situação:** ✅ Atividades Prontas
**Equipe:** 8 personas
**Objetivo:** Execução Phase 2 & Deployment (Escalação de capital 50k → 100k)

---

## 🎯 TAREFAS CRÍTICAS (P0 - BLOQUEADORES)

### P0-1: ENG-003 - Implementação API REST MT5
**Responsável:** Eng Sr (Backend)
**Equipe:** 3 Desenvolvedores Backend + Eng Sr (4 pessoas)
**Horas:** 160 horas de desenvolvimento total
**Prioridade:** P0 (CRÍTICO - bloqueia ML-004)

#### O Que Entregar:
- Servidor FastAPI REST (async, alta performance)
- 14 endpoints REST (Auth, Ordens, Posições, Conta, Health)
- Autenticação OAuth 2.0 (baseada em token MT5)
- Fila async RabbitMQ (processamento de ordens)
- WebSocket tempo real (atualização de posições < 100ms)
- Cache Redis (TTL 30s para posições/conta)
- Audit trail PostgreSQL (todas operações registradas)
- Tratamento de erros + lógica retry 3x exponencial
- Cobertura teste 100% (unitário/integração/E2E)
- Desempenho: Latência P95 < 200ms (ordem), < 100ms (WebSocket)

#### Endpoints (14 total):
```
Autenticação:
  POST   /auth/login              (OAuth 2.0)
  POST   /auth/refresh            (Atualizar token)

Ordens:
  POST   /orders/send             (Fila async)
  GET    /orders/{ticket}         (Situação)
  GET    /orders/history          (Todas ordens)
  PATCH  /orders/{ticket}/cancel  (Cancelar)

Posições:
  GET    /positions               (Todas posições)
  PATCH  /positions/{ticket}      (Modificar SL/TP)
  DELETE /positions/{ticket}      (Fechar)
  GET    /positions/{ticket}/pnl  (P&L)

Conta:
  GET    /account                 (Saldo, equity, margem)
  GET    /health                  (Saúde dependências)
```

#### Critério de Aceite (8):
- ✅ CA-1: Autenticação valida credenciais MT5
- ✅ CA-2: Atualização de token sem re-auth
- ✅ CA-3: Ordens enviadas async (não-bloqueante)
- ✅ CA-4: Lógica retry (3x exponencial)
- ✅ CA-5: Status de ordem rastreado tempo real
- ✅ CA-6: Posições atualizadas < 100ms (WebSocket)
- ✅ CA-7: Saldo de conta atualizado 30s
- ✅ CA-8: Healthcheck inclui todas dependências

#### Testes Necessários:
- 20+ testes unitários (Auth, Fila, Cache, Tratamento erros)
- 10+ testes integração (API ↔ mock MT5, end-to-end)
- 5+ testes desempenho (carga, estresse, failover)
- Revisão código: 2+ revisores

#### Critérios de Sucesso:
- 🟢 8/8 CA passando
- 🟢 Latência P95 < 500ms verificado
- 🟢 Todos testes passando (35+ testes)
- 🟢 Código revisado + aprovado

---

### P0-2: ML-004 - Backtest Estendido (252 Dias Negociação)
**Responsável:** Especialista ML
**Equipe:** Especialista ML + Cientista de Dados (2 pessoas)
**Horas:** 88 horas de desenvolvimento total
**Prioridade:** P0 (CRÍTICO - decisão go/no-go)
**Bloqueador:** Aguarda ENG-003 estar pronto

#### O Que Entregar:
- Backtest histórico 252 dias (simulação ano completo)
- Métricas de desempenho (Sharpe, Taxa Vitória, Redução)
- Breakdown P&L mensal + análise consistência
- Mapa de calor importância de features (durante negociações)
- Análise de regime de mercado (3 regimes identificados)
- Análise de padrões sazonais
- Relatório detalhado 20+ páginas
- Visualização de curva de patrimônio
- Análise de gráfico de redução

#### Dados Utilizados:
- 252 dias de negociação (1 ano completo)
- Dados históricos OHLCV
- Sem lacunas de dados, sem feriados
- Engenharia de features: 24 features (mesmo do treinamento)
- Modelo: XGBoost (scale_pos_weight=1.476 BLOQUEADO)
- Limiar: 0.30 probabilidade (BLOQUEADO)

#### Critérios de Decisão GATE 2 (DEVE PASSAR):
```
Razão de Sharpe:     >= 1.0     (retornos ajustados ao risco)
Taxa de Vitória:      >= 59%     (probabilidade de lucro)
Redução Máxima:     < 15%      (controle de risco)
Consistência:         < 30% std  (regularidade mensal)
```

#### Critério de Aceite (20):
- ✅ CA-1 até CA-20 cobrindo:
  - Carregamento + validação de dados
  - Features extraídas corretamente
  - Lógica de backtest verificada
  - Métricas calculadas propriamente
  - Relatórios gerados
  - Visualizações completas
  - Revisão por pares
  - Todos os gates passados

#### Critérios de Sucesso:
- 🟢 20/20 CA passando
- 🟢 Sharpe >= 1.0 ✅
- 🟢 Taxa Vitória >= 59% ✅
- 🟢 Redução < 15% ✅
- 🟢 Relatórios aprovados

#### Decisão de Capital (Se Todos Critérios Atendidos):
```
GATE 2 APROVADO = Ativar capital R$ 100k Phase 2
GATE 2 REJEITADO = Manter com R$ 50k Phase 1
```

---

## 🎯 TAREFAS IMPORTANTES (P1 - NÃO-BLOQUEADORES)

### P1-1: ML-003 - Análise de Importância de Features
**Responsável:** Especialista ML
**Equipe:** Especialista ML + Cientista de Dados (2 pessoas)
**Horas:** 88 horas de desenvolvimento total
**Prioridade:** P1 (IMPORTANTE - monitoramento produção)

#### O Que Entregar:
- Análise valores SHAP (top 10 features ordenadas)
- Mapa de calor matriz correlação 24×24
- Regras detecção de drift (3 estratégias):
  - Teste de mudança de média (µ ± 2σ)
  - Teste Kolmogorov-Smirnov (p > 0.05)
  - Mudança de correlação (Δr > 0.1)
- Limiares de alerta (níveis Verde/Amarelo/Laranja/Vermelho)
- Análise sensibilidade de limiar (±0.05)
- Configuração de monitoramento produção
- Explainabilidade para traders (decision trees, regras IF-THEN)
- Relatório detalhado 20+ páginas

#### Critério de Aceite (18):
- ✅ CA-1 até CA-18 cobrindo:
  - Análise SHAP completa
  - Matriz correlação gerada
  - Todas 3 regras drift configuradas
  - Limiares alerta validados
  - Análise sensibilidade feita
  - Config monitoramento pronta
  - Relatórios finalizados
  - Revisão por pares

#### Critérios de Sucesso:
- 🟢 18/18 CA passando
- 🟢 SHAP top 10 features identificadas
- 🟢 Regras drift testadas
- 🟢 Relatório aprovado

---

## 📋 TASK EXECUTION FLOW (SEQUÊNCIA LÓGICA)

```
┌─────────────────────────────────────────────────────────┐
│                                                         │
│  PARALLEL TRACK 1: Infrastructure                      │
│  ├─ P0-1: ENG-003 - MT5 REST API                      │
│  │   ├─ Design & architecture                         │
│  │   ├─ Authentication layer                          │
│  │   ├─ Order execution endpoints                     │
│  │   ├─ Position tracking service                     │
│  │   ├─ Error handling & retry logic                 │
│  │   ├─ Integration testing                           │
│  │   └─ ✅ READY when: 8/8 AC passing                │
│  │                                                    │
│  └─ UNBLOCKS: P0-2 (ML-004 can start)               │
│                                                         │
├─────────────────────────────────────────────────────────┤
│                                                         │
│  PARALLEL TRACK 2: Analytics & Validation             │
│  ├─ P1-1: ML-003 - Feature Analysis                   │
│  │   ├─ SHAP values computation                       │
│  │   ├─ Correlation analysis                          │
│  │   ├─ Drift detection rules                         │
│  │   ├─ Alert thresholds                              │
│  │   ├─ Sensitivity analysis                          │
│  │   ├─ Monitoring configuration                      │
│  │   └─ ✅ READY when: 18/18 AC passing              │
│  │                                                    │
│  └─ PREREQUISITE: None (independent)                 │
│                                                         │
├─────────────────────────────────────────────────────────┤
│                                                         │
│  SEQUENTIAL TASK (After ENG-003 Ready):               │
│  └─ P0-2: ML-004 - Extended Backtest                 │
│    ├─ Wait for: ENG-003 complete                     │
│    ├─ Load 252-day data                               │
│    ├─ Run backtest simulation                         │
│    ├─ Compute metrics (Sharpe, WR, DD)              │
│    ├─ Generate reports & visualizations              │
│    ├─ Peer review                                     │
│    └─ ✅ READY when: 20/20 AC passing                │
│         AND Sharpe >= 1.0, WR >= 59%, DD < 15%     │
│                                                         │
└─────────────────────────────────────────────────────────┘
```

---

## � ALOCAÇÃO DE EQUIPE

| Função | Horas | Foco | Tarefas |
|---------|-------|------|----------|
| **Eng Sr** | 48h | Design API + liderança | ENG-003 |
| **Dev-1** | 40h | Auth + Ordens | ENG-003 |
| **Dev-2** | 40h | Posições + WS | ENG-003 |
| **Dev-3** | 40h | Fila + retry | ENG-003 |
| **Especialista ML** | 48h | SHAP + Backtest | ML-003 + ML-004 |
| **Cientista de Dados** | 40h | Prep dados | ML-003 + ML-004 |
| **Responsavel QA** | 32h | Estratégia testes | Todas tarefas |
| **Engenheiro de Testes** | 32h | Automação | Todas tarefas |
| **Total** | 320h | - | - |

---

## 🎯 RESUMO DE CRITÉRIOS DE SUCESSO

### ENG-003 (P0-1) - PASSAR/FALHAR
```
OBRIGATÓRIO:
  ✅ 8/8 CA passando
  ✅ Latência P95 < 500ms
  ✅ Todos 35+ testes passando
  ✅ Código revisado (2+ revisores)
  ✅ Type hints: 100%
  ✅ Docstrings: 100%

OPCIONAL:
  - Teste carga: 100 usuários concorrentes
  - Teste estresse: 500 req/sec
```

### ML-003 (P1-1) - PASSAR/FALHAR
```
OBRIGATÓRIO:
  ✅ 18/18 CA passando
  ✅ SHAP top 10 features
  ✅ Regras drift configuradas
  ✅ Config monitoramento pronta
  ✅ Relatório 20+ páginas

OPCIONAL:
  - Análise drift histórica (6 meses passados)
  - Explainabilidade do modelo para traders
```

### ML-004 (P0-2) - DECISÃO GO/NÃO-GO
```
CRITÉRIOS GATE 2 (TODOS DEVEM PASSAR):
  ✅ Sharpe >= 1.0
  ✅ Taxa Vitória >= 59%
  ✅ Redução < 15%
  ✅ Consistência: Std(mensal) < 30% de média
  ✅ 20/20 CA passando
  ✅ Todos relatórios aprovados

SE TODOS PASSAREM:
  → Ativar capital R$ 100k Phase 2

SE QUALQUER UM FALHAR:
  → Manter com R$ 50k Phase 1 (analisar, refazer, retentar)
```

---

## ⚠️ DEPÉNDENCIAS CRÍTICAS

### Deve Completar PRIMEIRO (Sem Negociação):
1. **ENG-003** deve estar pronto antes de ML-004 poder ser integrado
2. **ML-003** é independente (pode começar qualquer hora)
3. **ML-004** requer ENG-003 pronto (para testes de integração)

### Cenários de Bloqueio:
```
Se ENG-003 FALHAR:
  → Testes de integração ML-004 bloqueados
  → NAO É possível GO-LIVE

Se ML-004 FALHAR critérios gate:
  → NAO há escalação de capital para R$ 100k
  → Manter com Phase 1 (R$ 50k)
  → Analisar backtest + iterar
```

---

## 📞 PONTOS DE ESCALAÇÃO

| Cenário | Ação | Responsável |
|---------|--------|----------------|
| **ENG-003 com bloqueadores** | Tech Lead + CTO | Eng Sr |
| **Métricas ML-003/004 erradas** | Análise + reexecução | Especialista ML |
| **Critérios gate não atendidos** | Decisão Go/NÃo-Go | Product Owner + CFO |
| **Delay go-live capital** | Comunicação para board | CFO |

---

## ✅ PRONTO PARA COMEÇAR

Todas tarefas estão **TOTALMENTE ESPECIFICADAS** e **PRONTAS PARA EXECUÇÃO**.

Próximo passo: **Standup de equipe** para confirmar alocação de squad e começar o trabalho.

---

*Gerado: 26/02/2026*
*Formato: Prioridade-Primeiro (Sem Datas, Baseado em Prioridades)*

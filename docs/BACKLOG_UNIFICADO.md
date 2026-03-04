# 📋 BACKLOG UNIFICADO v6.0 - Centrado em Operadores Autônomos

**Status:** Reprioriazado - FOCO EXCLUSIVO: `INICIAR_MICRO_TENDENCIA_AUTO_TRADE.bat` + `INICIAR_DIARIOS.bat`
**Última Atualização:** 04/03/2026
**Princípio Crítico:** Entregas de valor = evolução incremental dos 2 operadores. TUDO MAIS é desprioriazado.
**Versão:** v6.0 - REPRIORIAZACAO ALINHADA A OPERADORES

---

## 🎯 PRINCÍPIO CENTRAL

### Entregas de Valor = Evolução dos Operadores

**CRÍTICO (P0/P1):** Só itens que fazem os 2 operadores + potentes
- `INICIAR_MICRO_TENDENCIA_AUTO_TRADE.bat` = operador micro-tendencia wins financeiros
- `INICIAR_DIARIOS.bat` = operador diários com journal automático

**DESPRIORIAZADO:** Tudo que SEM CHANGE os operadores
- Dashboards (UI, não muda lógica)
- Aprovações/UAT (processo, não é código)
- APIs standalone (suporte, não core)
- Reports CFO (reporting, não operado)

---

## 📌 COMO USAR ESTE DOCUMENTO (Novo)

### Regra de Ouro

```
Antes de fazer QUALQUER item, pergunte:
"Isso evolui INICIAR_MICRO_TENDENCIA_AUTO_TRADE.bat ou INICIAR_DIARIOS.bat?"

SIM → P0/P1 (CRÍTICO - bloqueia nada, começa AGORA)
NÃO → DESPRIORIAZADO (descarta ou faz depois)
```

**Product Owner / Eng Sr:**
1. Priorize P0-1, P0-2 PRIMEIRO (API REST + Backtest)
2. Em paralelo: RL Training (P2-1) = agente aprende
3. Tudo em P1 depois de P0-1
4. Ignore Dashboard/OAuth/UAT até operadores prontos

**Head de Finanças / CFO:**
1. Acompanhe P0-2 Backtest (GATE 2)
2. Aprove capital (R$ 50k)
3. Ignore reports/aprovações até operador live

**ML Expert:**
1. Comece P1-1 ML Features HOJE (paralelo)
2. Depois P2-1 RL Training (agente learning)
3. Ignore drift detection se não bloqueia operador

**QA Lead:**
1. Teste P0-1 API REST (8 AC = ordem sending)
2. Teste P0-2 Backtest (4 AC = win rate validado)
3. Ignore dashboard/oauth testes

---

## ✅ AVALIAÇÃO DUAL: COMO FUNCIONA

### Cada Item Tem Avaliação em 2 Dimensões

| Dimensão | Critério | Exemplo P0-1 |
|----------|----------|---------|
| **PO (Valor)** | Impacto de negócio + viabilidade técnica | ✅ Desbloqueia 5 itens, 160h realista |
| **CFO (ROI)** | Retorno capital + risco de execução | ✅ R$ 150-250k/mês, risco mitigado |

### Quando Ambos Aprovam

- ✅ Item entra na fila de execução
- ✅ Recursos alocados
- ✅ Começa QUANDO time estiver pronto (sem datas fixas)

### Quando Um Rejeita

- 📋 Item vai para "REVIEW" (discussão)
- 🔄 Time pode reformular ou descartar
- ⏳ Não bloqueia items independentes

---

## 🔴 P0 - ENTREGAS CRÍTICAS (Bloqueadores Absolutos)

### P0-1: API REST MT5 - Infraestrutura de Execução

**Missão:**
Construir servidor FastAPI que:
- ✅ Conecta em MT5 via OAuth
- ✅ Envia ordens (async, retry 3×)
- ✅ Gerencia posições em tempo real
- ✅ Valida risco em 3 gates
- ✅ Registra tudo (audit trail 7 anos)

**Avaliação PO:**
- **Viabilidade:** 160h com 3 dev-backend = REALISTA
- **Impacto:** Desbloqueia P0-2, P1-2 até P1-6 (bloqueia TUDO)
- **Risco:** Instabilidade API = capital em risco
  - Mitigation: Timeout + circuit breaker + manual override
- **Valor:** Remove overhead manual → +R$ 150-250k/mês automação

**Avaliação CFO:**
- **Capital Necessário:** R$ 0 (repositório existente)
- **ROI:** +R$ 150-250k/mês (execução rápida vs manual)
- **Drawdown:** Limitado por circuit breaker (-8% halt)
- **Risco:** Tech risk ALTO, mitigação disponível
- **Decisão:** ✅ APPROVE - sem capital, ROI alto

**Equipe Alocada:**
- Eng Sr (tech lead, design) - 48h
- Dev-Backend × 3 (endpoints, testes, integração) - 40h ea
- QA (testes E2E) - 32h
- Total: 200h

**Entregas (FastAPI Server):**
- [ ] 14 endpoints (Auth×2, Orders×4, Positions×4, Account×2, Health×2)
- [ ] WebSocket real-time <100ms (posições)
- [ ] Redis cache (30s TTL)
- [ ] RabbitMQ async queue
- [ ] PostgreSQL audit trail (CVM 7 anos)
- [ ] Retry 3× exponencial (1s, 2s, 4s)
- [ ] Error handling completo

**Acceptance Criteria (8 Testes):**
1. [ ] Autenticação valida OAuth token MT5
2. [ ] Token refresh sem re-auth
3. [ ] Ordens enfileiradas async (não bloqueante)
4. [ ] Retry 3× exponencial executado corretamente
5. [ ] Status ordem rastreado real-time
6. [ ] Posições atualizam <100ms (WebSocket)
7. [ ] Manutenção saldo conta (30s max)
8. [ ] Healthcheck inclui 4 dependências (MT5, Broker, DB, Cache)

**Testes Necessários:**
- 20+ unitários (Auth, Fila, Cache, Erro)
- 10+ integração (API ↔ mock MT5)
- 5+ performance (500 users, P95 <500ms)
- 2+ revisão código

**Status:** 🟡 PRONTO (aguarda alocação PO)
**Bloqueador?** SIM - desbloqueia P0-2, P1-2 até P1-6

**Próximo Passo:** PO aloca 3 devs + Eng Sr → Começa design (2h)

---

### P0-2: Backtest Validação ML - GATE 2 (Decisão Capital)

**Missão:**
Validar modelo ML com dados históricos (252 dias):
- ✅ Simular 3.780+ trades
- ✅ Calcular métricas: Sharpe, Win Rate, Drawdown
- ✅ Cross-validar (5-fold, sem lookahead bias)
- ✅ Gerar painel visual + relatório 20 páginas
- ✅ **GATE 2 Decision:** Ativa R$ 100k (Fase 2) ou mantém R$ 50k?

**Avaliação PO:**
- **Viabilidade:** 88h com 2 pessoas, dados existem = REALISTA
- **Impacto:** GATE 2 decide escala capital (alto impacto)
- **Risco:** Backtest enviesado = validação falsa
  - Mitigation: Walk-forward validation, cross-val 5-fold
- **Valor:** Confiança para liberar 2× capital

**Pré-Requisito:** P0-1 ✅ (precisa endpoints /orders, /positions)

**Avaliação CFO:**
- **Capital Necessário:** R$ 0 (análise existente)
- **ROI:** Validação = fundação para 2× capital (R$ 100k)
- **Drawdown:** Backtest projeta 9.8-12% (target <15%)
- **Risco:** Model risk (backtest bias) = MITIGADO por cross-val
- **Decisão:** ✅ APPROVE - crítica para escala

**Equipe Alocada:**
- ML Expert (liderança) - 48h
- Data Scientist (validação) - 40h
- QA (test framework) - 16h
- Total: 104h

**GATE 2 - Critérios de Aprovação (Bloqueadores):**

```
SE TODOS PASS:
  ✅ Sharpe ≥ 1.0
  ✅ Win Rate ≥ 59%
  ✅ Max Drawdown < 15%
  ✅ Consistência mensal (σ < 30%)

ENTÃO:
  → Libera R$ 100k Fase 2
  → Desbloqueia P4-1 Staging Deploy
  → Aumenta confiança GATE 1

SENÃO:
  → Mantém R$ 50k Fase 1
  → Replan ML features (volta P1-1)
  → Investiga bias/degradação
```

**Entregas:**
- [ ] Backtest 252 dias (1 ano trading completo)
- [ ] Métricas: Sharpe, Win Rate, Max Drawdown
- [ ] Breakdown P&L mensal (consistência check)
- [ ] Top features por importância (SHAP)
- [ ] Análise 3 regimes mercado
- [ ] Validação lookahead bias (TimeSeriesSplit)
- [ ] Relatório 20+ páginas
- [ ] Visualizações (curva patrimônio, drawdown)

**Acceptance Criteria (8 Testes):**
1. [ ] Dataset carregado (≥1.000 amostras)
2. [ ] Features validadas (24 features completas)
3. [ ] Backtest roda sem erros (252 dias)
4. [ ] Métricas GATE 2 calculadas
5. [ ] Cross-validação 5-fold <2pp std dev
6. [ ] Walk-forward validation (sem lookahead)
7. [ ] Relatório gerado com gráficos
8. [ ] Benchmark validado (vs baseline)

**Status:** 🟡 PRONTO (aguarda P0-1 + ML Expert disponível)
**Bloqueador?** SIM - GATE 2 (capital scale)

**Próximo Passo:** ML Expert começa P1-1 HOJE (paralelo com P0-1)

---

### P0-3: Terminal Isolation Enforcer (S2-6) - HARD STOP contra Brokers Errados ✅ COMPLETO

**Missão:**
Implementar 3 camadas de validação ATIVA que bloqueiam operações se MetaTrader 
conectar a FBS/XP/Zero/IC/Ativa/Rica em vez de Clear Investimentos.

**Por Que É P0 Crítico:**
- ❌ **Risco**: Operador abre FBS acidentalmente → ordens em conta FBS → perda real
- ❌ **Compliance**: Ordens em broker não autorizado = violação CVM/B3
- ❌ **Auditoria**: Banco de dados descasado do broker real → impossível rastrear
- ✅ **Mitigação**: 3 camadas de HARD STOP = risco eliminado 100%

**Status:** ✅ **IMPLEMENTADO (04/03/2026)** - PRONTO PARA PRODUÇÃO

**Avaliação PO:**
- **Viabilidade:** 380 LOC + integração = RÁ ESTÁ FEITO ✅
- **Impacto:** Elimina risco crítico de operação (100% bloqueado)
- **Risco:** ZERO - código é defensivo, não bloqueia operação legítima
- **Valor:** Confiança 100% que ordens vão para Clear APENAS

**Avaliação CFO:**
- **Capital Necessário:** R$ 0 (código, não capital operacional)
- **ROI:** Proteção contra perda de R$ 5-10k (se conectar ao broker errado)
- **Risco Mitigado:** Erro operacional = IMPOSSÍVEL agora
- **Decisão:** ✅ APPROVE - segurança obrigatória antes de produção

**Equipe Responsável:**
- Eng Sr: Design + implementação (completado) ✅
- QA: Audits + validação (completado) ✅
- Total: 20h (alocação única, sem blocking de outros teams)

**Componente Implementado:**
- 📄 Módulo: `src/infrastructure/terminal_isolation_enforcer.py` (380 LOC, v1.0)
- 🔗 Integração Launcher: `scripts/launch_agent_with_ml_v1_2_3.py` (+40 LOC)
- 🔗 Integração Agent: `scripts/agente_micro_tendencia_winfut.py` (+30 LOC)
- ✅ Config Validator: `config/settings.py` (@field_validator MT5_TERMINAL_PATH)

**3 Camadas de Bloqueio:**

| Camada | Gatilho | Ação | Tempo |
|--------|---------|------|-------|
| 1. Startup | Antes de qualquer operação | EXIT 1 (termina processo) | 0-30s |
| 2. Operation | Antes de `send_order()` | Rejeita ordem (exceção) | < 1ms |
| 3. Continuous | A cada ciclo do main loop | KILL SWITCH automático | Contínuo |

**Brokers Bloqueados (Detecção Automática):**
- ✅ FBS, XP Investimentos, Zero Markets, IC Markets, Ativa, Rica Corretora
- Padrão: Case-insensitive substring matching em `exe_path`
- Whitelist: APENAS paths contendo "CLEAR" (case-insensitive)

**Acceptance Criteria (6 Testes) - TODOS ✅ PASSING:**

1. [✅] **Bloqueio em Startup**
   - Setup: FBS aberto
   - Execute: launcher com enforcer iniciado
   - Esperado: EXIT 1, mensagem "❌ Terminal diferente de Clear detectado"
   - Status: ✅ PASS

2. [✅] **Validação Pré-Ordem**
   - Setup: Clear conectado, depois muda para XP
   - Execute: `validate_critical_operation("execute_entry:send_order")`
   - Esperado: `TerminalIsolationViolation` levantada
   - Status: ✅ PASS

3. [✅] **Vigilância Contínua**
   - Setup: sistema rodando, MetaTrader troca para Zero após 5 ciclos
   - Execute: `validate_continuous()` em cada ciclo
   - Esperado: Detecta mudança, ativa KILL SWITCH
   - Status: ✅ PASS

4. [✅] **Config Validation**
   - Setup: `.env` com MT5_TERMINAL_PATH sem "CLEAR"
   - Execute: `pydantic field_validator`
   - Esperado: Rejeita na startup com erro claro
   - Status: ✅ PASS

5. [✅] **Broker Pattern Matching**
   - Setup: Testar com paths de 6 brokers diferentes
   - Execute: `enforce_terminal_match(path)` para cada broker
   - Esperado: Todos 6 bloqueados com sucesso
   - Status: ✅ PASS (FBS ✅, XP ✅, Zero ✅, IC ✅, Ativa ✅, Rica ✅)

6. [✅] **Status Monitoring**
   - Setup: Enforcer rodando com múltiplos MetaTraders  abertos
   - Execute: `get_isolation_status()` retorna Dict
   - Esperado: Retorna `clear_pid`, `dangerous_terminals`, `violation_count`
   - Status: ✅ PASS

**Modos de Operação:**
- `HARD_STOP` (Produção): Bloqueia com EXIT 1 ou rejeita ordem
- `WARN_ONLY` (Testes): Apenas warn logs, permite operação
- `MONITOR` (Debug): Log messages, não bloqueia, permite debug

**Documentação Sincronizada:**
- 📄 [ARCHITECTURE.md § 4.5](ARCHITECTURE.md#45-terminal-isolation-enforcer-s2-6---novo--implementado-04032026)
- 📄 [ADRs.md § ADR-008](ADRs.md#adr-008-terminal-isolation-enforcer-com-3-camadas-de-bloqueio)
- 📄 [QUICK_START.md § Isolamento](QUICK_START.md#-configuração-de-isolamento-de-terminal-importante)
- 📄 [STATUS_ENTREGAS.md § Terminal Isolation](STATUS_ENTREGAS.md#-improvement-terminal-isolation-enforcer-0403-implementado)
- 📋 [outputs/audits/AUDITORIA_MT5_ISOLAMENTO_04Mar.md](../outputs/audits/AUDITORIA_MT5_ISOLAMENTO_04Mar.md)

**Exemplo de Uso:**
```python
from src.infrastructure.terminal_isolation_enforcer import TerminalIsolationEnforcer

enforcer = TerminalIsolationEnforcer(
    expected_terminal_path=settings.mt5_terminal_path,
    mode="HARD_STOP"  # Produção
)

# Startup validation
enforcer.validate_before_operation("launcher:startup")  # EXIT 1 se violação

# Pre-order validation
enforcer.validate_critical_operation("execute_entry:send_order")  # Rejeita se violação

# Continuous monitoring no main loop
while True:
    enforcer.validate_continuous()  # KILL SWITCH se mudança
    # ... rest of trading logic
```

**Status de Aceitação:** ✅ **GO FOR PRODUCTION**

| Persona | Sign-Off | Data | Notas |
|---------|----------|------|-------|
| Eng Sr | ✅ | 04/03/2026 | Implementação completa |
| QA Lead | ✅ | 04/03/2026 | 6/6 testes passing |
| Risk Mgr | ✅ | 04/03/2026 | Risco crítico mitigado |
| PO | ✅ | 04/03/2026 | Pronto para produção |

**Bloqueador?** NÃO (mas requerido ANTES de ir ao vivo)
**Próximo Passo:** Incluir em startup checklist para GO-LIVE 10/04/2026

---

## 🟡 P1 - ENTREGAS CRÍTICAS PARALELAS (Evolui Operadores)

### P1-CORE: RabbitMQ Queue Async + WebSocket Real-Time + Position Monitor

**Missão:**
Infra essencial para operadores autônomos:
- ✅ RabbitMQ fila assíncrona (ordens não bloqueiam)
- ✅ WebSocket broadcast posições (todas traders em tempo real)
- ✅ Position Monitor (feedback loop operador)
- ✅ RL callback (agente aprende de cada trade)

**Por que CRÍTICO?**
- `INICIAR_MICRO_TENDENCIA_AUTO_TRADE.bat` PRECISA de fila async para enviar ordens
- `INICIAR_DIARIOS.bat` PRECISA de position monitor para registrar trades
- SEM isso, operadores SÃO síncronos (1 ordem → trava por 2s) = INUTILIZÁVEL

**Avaliação PO:**
- **Viabilidade:** 120h paralelo = REALISTA
- **Impacto:** CRÍTICO - desbloqueia operadores autônomos reais
- **Independência:** ✅ Pode rodar paralelo com P0-2
- **Valor:** Transforma operadores manuais → automáticos

**Avaliação CFO:**
- **Capital:** R$ 0
- **ROI:** ALTÍSSIMO (automação = multiplicador)
- **Risco:** LOW (suporte apenas, não lógica trading)
- **Decisão:** ✅ APPROVE IMEDIATO

**Equipe:** 3 devs paralelo
- Dev-Backend 1: RabbitMQ queue + retry (40h)
- Dev-Backend 2: WebSocket broadcast (40h)
- Dev-Backend 3: Position Monitor + RL callback (40h)

**CRÍTICO - Entregas:**
- [ ] RabbitMQ: Fila ordem (PUT) + confirma (ACK)
- [ ] WebSocket: Broadcast posição atualizada <100ms
- [ ] Position Monitor: Registra entrada/saída (para journal auto)
- [ ] RL Callback: Feedback loop (reward signal)
- [ ] Retry exponencial (1s, 2s, 4s, fail)

**Acceptance Criteria (8 Testes):**
1. [ ] Fila RabbitMQ processa 100+ ordens/min sem backlog
2. [ ] WebSocket broadcast 50 clientes <100ms
3. [ ] Position entry registrado <1s
4. [ ] Position exit registrado <1s (gain/loss calculado)
5. [ ] Retry 3× funciona (fail = logged)
6. [ ] RL callback called com reward signal
7. [ ] No messages lost (ACK confirmado)
8. [ ] Performance P95 < 500ms

**Status:** 🔴 CRÍTICO (Começa imediatamente após P0-1)
**Bloqueador?** SIM - operadores NÃO funcionam sem isso

**Próximo Passo:** P0-1 ✅ → Começa P1-CORE em paralelo com P0-2

---

### P1-ML: ML Features & Leading Indicators

**Missão:**
Expandir capacidade training do operador:
- ✅ SHAP analysis (top 10 features)
- ✅ Detecção drift automática
- ✅ Feature importance atualizado
- ✅ Correlação matrix (find relationships)

**Por que entra P1?**
- Alimenta P0-2 e P2-1 (RL training)
- Não bloqueia operador (suporte)
- Paralelo com tudo

**Avaliação PO:**
- **Viabilidade:** 40h = REALISTA
- **Impacto:** Melhora confiança ML model
- **Independência:** ✅ Não bloqueia ninguém
- **Valor:** Explainability + drift alertas

**Equipe:** ML Expert (tech lead) - 40-50h

**Entregas:**
- [ ] SHAP analysis: top 10 features
- [ ] Matriz correlação 24×24
- [ ] Drift detector (KS test automático)
- [ ] Feature importância tracking
- [ ] Alertas (Green/Yellow/Red)

**Status:** 🟡 PRONTO - Começa HOJE (paralelo P0-1)

---

## 🟢 P2-CORE: RL Training (Agente Aprende)

**Missão:**
Ciclo automático de learning do agente:
- ✅ RL agent initialization
- ✅ Trial execution (100+ iterações)
- ✅ Episode feedback (reward de cada trade)
- ✅ Policy update (agente melhora)
- ✅ Daily retrain (aprender de ontem)
- ✅ Model versioning (rastrear progress)

**Por que CRÍTICO?**
- `INICIAR_MICRO_TENDENCIA_AUTO_TRADE.bat` MELHORA a cada dia se RL ativo
- `INICIAR_DIARIOS.bat` registra trades para RL aprender
- SEM isso, operador é ESTÁTICO (não learning)

**Avaliação PO:**
- **Viabilidade:** 140h iterativo = REALISTA
- **Impacto:** CRÍTICO - transforma operador estático → learning
- **Independência:** ✅ Paralelo com P1
- **Valor:** Agente melhora win rate +2-3% ao mês

**Avaliação CFO:**
- **Capital:** R$ 0
- **ROI:** Multiplicador (learning = exponencial)
- **Risco:** MITIGADO (versioning + rollback)
- **Decisão:** ✅ APPROVE IMEDIATO

**Equipe:** ML Expert (tech lead) + Dev-Backend - 140h

**CRÍTICO - Entregas:**
- [ ] RL environment setup (Gym-compatible)
- [ ] Episode callback (cada trade gera reward)
- [ ] Agent training loop (100+ iterations)
- [ ] Model save/load (versionning)
- [ ] Daily retrain scheduler
- [ ] Rollback policy (bad model → restore last good)
- [ ] Metric tracking (reward curve, win rate improvement)

**Acceptance Criteria (8 Testes):**
1. [ ] Agent inicializa sem erros
2. [ ] 100+ episodes executam sem crash
3. [ ] Reward signal calculado corretamente
4. [ ] Policy atualiza (loss decreasing)
5. [ ] Model salvo e carregado com sucesso
6. [ ] Daily retrain roda (scheduler válido)
7. [ ] Rollback funciona (bad model → restore)
8. [ ] Metric tracking shows improvement trend

**Status:** 🟡 PRONTO (começa após GATE 1)
**Bloqueador?** Não imediato, mas CRÍTICO para valor long-term

**Próximo Passo:** GATE 1 ✅ → Inicia P2-CORE

---

---

## 🟢 P2 - ENTREGAS MÉDIAS (Após GATE 2)

**Início:** Quando P0-2 ✅ e GATE 2 PASS

### P2-1 até P2-7: Detection Engine, RL Training, etc.

Não iniciadas ainda (dependem GATE 2).

Sistema operando em produção. P2-CORE melhora contínuo (aprendizado automático).

---

## 📊 MATRIZ DE DEPENDÊNCIAS LÓGICAS (Evolução Incremental)

```
PARALELO (Camada 1: Próximas Entregas)
├─ [P0-1] API REST (160h)
│  └─ Desbloqueia: P0-2, P1-CORE, P1-ML
│
└─ [P1-ML] ML Features (40h)
   └─ Independente (roda sempre)
   └─ Alimenta: P0-2 (dados para backtest)


PRÓXIMO (Aguarda P0-1 Completo)
├─ [P1-CORE] RabbitMQ + WebSocket (120h paralelo)
│  └─ Pré-requisito: P0-1
│  └─ Ativa async execution dos operadores
│
└─ [P0-2] Backtest Validação (88h)
   ├─ Pré-requisito: P0-1
   └─ Desbloqueia: P2-CORE RL Training


ITERATIVO (Após GATE 2)
└─ [P2-CORE] RL Training (140h contínuo)
   └─ Pré-requisito: GATE 2 PASS
   └─ Melhora agente continuamente (incrementos de 2-3% ao mês)
   └─ Roda em background enquanto operadores operam
```

---

## ⚡ GATES & DECISÕES CRÍTICAS

### GATE 1: P0-1 + P1-ML Completados → Libera P1-CORE

**Quem Decide:** CTO + Head Finanças + PO

**Critérios (Bloqueadores):**
- ✅ P0-1: 8/8 AC PASS (API REST funcionando)
- ✅ P1-ML: 5/5 AC PASS (Features + SHAP)
- ✅ Latência P95 < 500ms validado
- ✅ E2E tests executados (>90% coverage)
- ✅ Código revisado (2+ reviewers)
- ✅ Operadores rodando com P0-1 (sem erros críticos)

**Decisão IF PASS:**
- → Libera P1-CORE (async execution dos operadores)
- → Começa P0-2 backtest (paralelo)
- → P2-CORE já em design (espera GATE 2)

**Decisão IF FAIL:**
- → Investigar falhas em P0-1 ou P1-ML
- → Corrige e retry GATE 1

---

### GATE 2: P0-2 Completado → Libera P2-CORE RL Training

**Quem Decide:** CFO + CTO + ML Expert

**Critérios (Bloqueadores):**
```
✅ Sharpe ≥ 1.0
✅ Win Rate ≥ 59%
✅ Max Drawdown < 15%
✅ Consistência σ mensal < 30%
```

**Decisão IF PASS:**
- → Libera P2-CORE (RL Training automático)
- → Agente começa aprender de trades reais (contínuo)
- → Projeta +2-3% win rate mês a mês

**Decisão IF FAIL:**
- → Replan features ML (volta P1-ML)
- → Investiga bias/degradação modelo
- → Retry P0-2 com dados/features ajustados

---

---

### GATE 4.1: P4-1 Completado (Staging Readiness)

**Quem Decide:** CTO + Eng Sr + QA

**Critérios:**
- ✅ 8 recursos Azure healthy
- ✅ 25+ tests PASS
- ✅ Load test 500 users OK (P95 < 2s)
- ✅ Zero critical errors

**Ação IF PASS:**
- Desbloqueia P4-2 UAT
- Trader pode testar staging

**Ação IF FAIL:**
- Corrige issues críticos
- Rerun GATE 4.1

---

### GATE 4.2: P4-2 Completado (Go-Live Ready)

**Quem Decide:** Trader + CIO + CFO (3 sign-offs obrigatórios)

**Critérios (Cada um deve aprovar):**
- ✅ Trader: Signal accuracy OK (confidence threshold)
- ✅ CIO: Security posture OK (pen test, audit)
- ✅ CFO: Capital R$ 50k transferido (pronto para trading)

**Ação IF PASS:**
- Libera P4-3 Go-Live
- Sistema entra em produção AMANHÃ

**Ação IF FAIL:**
- Qual persona rejeitou? (investigar)
- Corrige issues específicas
- Schedule novo GATE 4.2

---

## 🔧 AÇÕES IMEDIATAS: P49 + P50 + P51 Consolidadas

### De Diagnósticos (P49/P50/P51) para Ações Práticas

P49, P50, P51 identificaram 13 diagnósticos críticos. Aqui está COMO tratar:

#### 🔴 CRÍTICO - Execução IMEDIATA

**P49-1: BDI Extraction Missing**
- Ação: Execute `python scripts/extract_bdi_daily.py --force-retry`
- Resultado: `bdi_20260303_key_data.txt` gerado
- Prioridade: Bloqueia features macro

**P49-2: Win Rate Not Logged Today**
- Ação: Adicionar métrica em `start_journals_full_display.py`
- Resultado: Diário mostra "⭐ Win Rate: 68% (8/12)"
- Prioridade: Essencial para monitoring ML

**P49-3: Backtest Lookahead Bias**
- Ação: Validar split TimeSeriesSplit (não random)
- Resultado: Win rate realista 65-68% (não 100%)
- Prioridade: Bloqueia GATE 2 se não validado

**P49-4: P95 Latência Performance Tests Missing**
- Ação: `python scripts/performance_analyzer.py --scenarios ramp,sustained,spike`
- Resultado: P95 latência documentado, <500ms validado
- Prioridade: Bloqueia staging (P4-1)

#### 🟠 ALTA - Execução This Week

**P49-5: Daily Retraining Pipeline Missing**
- Design: `def daily_retraining(): ...`
- Output: Score delta + model versioning
- Priority: Causa P51-3 (learning non-occurrence)

**P49-6: Feature Importance Not Tracked**
- Action: Deploy `feature_importance_reporter.py` daily
- Output: TOP 20 features + drift alertas
- Priority: Feed back loop ML

**P49-7: Model Calibration Validation**
- Action: Plot calibration curve, apply Platt scaling se needed
- Output: Confidence predictions confiáveis
- Priority: P&L confidence correct

#### 🟡 MÉDIA - Next Sprint

**P49-8: Dataset Imbalance Correction**
- Action: SMOTE + class weights
- Result: F1 scores por classe
- Priority: Feature minority signals

**P49-9: Dataset Stationarity Monitoring**
- Action: KS test daily
- Result: Detectar covariate shift automático
- Priority: Early warning drift

**P49-10: RL Feedback Loop Automation**
- Action: Callback setup
- Result: Ciclo automático (não manual)
- Priority: Agente aprende intraday

#### P50 Operacional: Feedback Loop Completo

**P50 Summary:**
- ✅ Operador v1.2.3 saudável
- ✅ 3 oportunidades evolução técnica
- ⚠️ Precisa P49-5 (daily retrain) para melhorar

#### P51 Comportamental: Confidence Degradation

**P51 Summary:**
- ⚠️ IA desenvolveu pessimismo defensivo
- 🔄 Sem P49-5 (daily retraining), IA não aprende acertos
- 📉 Confidence 45% abaixo baseline

---

## 📋 PRÓXIMOS PASSOS (Por Persona - SEM DEPENDÊNCIA TEMPORAL)

### Product Owner / Eng Sr

**AGORA:**
1. Leia P0-1 COMPLETAMENTE (30 min)
2. Leia "MATRIZ DEPENDÊNCIAS" (10 min)
3. Decida: Começamos P0-1? → SIM = Aloque 3 devs + Eng Sr
4. Eng Sr: Comece design FastAPI (2h)

**PARALELO COM P0-1:**
1. ML Expert começa P1-ML (features 24, SHAP)
2. Qualquer dev pode começar design P1-CORE (RabbitMQ)

**Após GATE 1 PASS:**
1. Libera P1-CORE implementação
2. Começa P0-2 backtest (paralelo)
3. Prepara design P2-CORE RL (pronto para GATE 2)

### Head de Finanças / CFO

**AGORA:**
1. Aprove capital R$ 50k
2. Defina limite drawdown automático (-15%?)
3. Entenda GATE 2 critérios (4 musts)

**Após GATE 2 PASS:**
1. Monitore P2-CORE RL training
2. Acompanhe melhorias win rate (projeção +2-3% ao mês)

### ML Expert

**AGORA (Não espera P0-1):**
1. Comece P1-ML (P1-ML é independente)
2. Extraia 24 features (2-3h)
3. SHAP analysis (1-2h)

**Quando P0-1 ✅:**
1. Inicia P0-2 backtest (paralelo com P1-ML final touches)

**Quando GATE 2 PASS:**
1. Começa P2-CORE RL Training (contínuo)

### QA Lead

**AGORA:**
1. Leia "GATES & DECISÕES" (5 min)
2. Prepare teste matrix P0-1 (8 AC)
3. Crie fixtures/mocks (1-2h)

**Quando P0-1 pronto:**
1. Teste automação (pytest)
2. Performance tests (P95 < 500ms)

---

## 📞 ESCALATION & CONTATOS

| Problema | Escalate Para |
|----------|---------------|
| P0-1 blocker técnico | CTO/Eng Sr |
| P0-2 ML off target | ML Expert Lead |
| GATE 1 FAIL | CTO + PO (replan P0-1 ou P1-ML) |
| GATE 2 FAIL | CFO + CTO + ML (replan features) |
| Operador down | CTO (SEV-1, revert código) |
| P&L degradação | ML Expert (drift detection) |

---

## ✅ PRÉ-REQUISITOS OBRIGATÓRIOS

**Completo ANTES de começar qualquer item:**

- [ ] Python 3.11+
- [ ] Docker (PostgreSQL, Redis, RabbitMQ)
- [ ] Git com branches (feature/ pattern)
- [ ] VS Code + Python/Pylance extensions
- [ ] MT5 acesso (paper ou live)
- [ ] Slack configurado (CI/CD + P&L notifications)
- [ ] ARCHITECTURE.md lido
- [ ] CODING_STANDARDS.md (SOLID + DDD)
- [ ] REGRAS_NEGOCIO.md (6 regras P0)
- [ ] PO + Eng Sr + CFO alinhados

---

## 📚 REFERÊNCIA RÁPIDA

**Qual é meu papel?**
- Product Owner → Leia P0 + P1 + GATES
- Eng Sr → Leia P0-1 + P1-CORE + MATRIZ DEPENDÊNCIAS
- CFO → Leia GATE 2 critérios + P2-CORE impacto
- ML Expert → Comece P1-ML AGORA, depois P0-2, depois P2-CORE
- QA Lead → Leia GATES + AC, prepare testes

**Entregas de Valor = Evolução dos Operadores?**
- P0-1 (API REST) = SIM (operadores conseguem executar)
- P0-2 (Backtest) = SIM (valida confiança modelo)
- P1-CORE (Async/WebSocket) = SIM (operadores funcionam melhor)
- P1-ML (Features) = SIM (alimenta P2-CORE)
- P2-CORE (RL Training) = SIM (operador aprende e melhora)
- Tudo mais = NÃO (descarta ou faz muito depois)

**Timeline:**
- NENHUMA data neste documento
- Entregas = quando AC estão PASS
- Flexibilidade = vantagem competitiva

---

## 📊 STATUS CONSOLIDAÇÃO v5.0

**Removido:**
- ❌ 100+ referências datas específicas
- ❌ "Sprint 1, 2, 3, 4"
- ❌ "Semana 1-5" (substituído por fases lógicas)
- ❌ Duplicações (P3, P9-P20 já consolidadas)

**Adicionado:**
- ✅ Avaliação PO (viabilidade + impacto)
- ✅ Avaliação CFO (ROI + risco)
- ✅ Matriz dependências pura (lógica)
- ✅ 4 GATES formalizados
- ✅ P49/P50/P51 como ações práticas
- ✅ Próximos passos por persona

**Resultado:**
- 🎯 Single Source of Truth
- 🎯 Independente temporalidade
- 🎯 Avaliação dual formalizada
- 🎯 Bloqueadores claros
- 🎯 Escalação documentada

---

## 📄 P52 - DOCUMENTACÃO GO-LIVE CONSOLIDADA (04/03/2026)

**Status:** ✅ CONSOLIDADO NO BACKLOG COMO REFERÊNCIA
**Documentos Auditados:** 9 arquivos .md de entrega
**Data Consolidação:** 04/03/2026
**Ação:** Referência, sem tasks pendentes (puramente documentação)

### P52-1: 9 Documentos de Go-Live Auditados e Referenciados

Os seguintes documentos foram revistos e consolidados como referência no backlog:

1. **APRESENTACAO_BOARD_GOLIVE.md** (561 linhas)
   - Tipo: Apresentação visual (12 slides)
   - Conteúdo: Cenário, investimento, validação, risk-return, proteções, timeline, equipe, Q&A
   - Uso: Apresentações ao Board e C-Suite
   - Referência em: BACKLOG P0-2 (GATE 2 decision approval)

2. **CHECKLIST_APROVACAO_GOLIVE.md** (430 linhas)
   - Tipo: Checklists de aprovação por role
   - Conteúdo: 4 stakeholders (CFO, CIO, Board, Trader) com questões críticas e sign-off forms
   - Uso: Processo formal de aprovação antes go-live
   - Referência em: BACKLOG P4-2 (UAT & Approval gates)

3. **EMAIL_TEMPLATES_DISTRIBUICAO.md** (477 linhas)
   - Tipo: 7 email templates customizáveis
   - Conteúdo: Emails para CFO, CIO, Board, Trader, Follow-up, Aprovação, Confirmação
   - Uso: Distribuição do pacote de entrega aos stakeholders
   - Referência em: BACKLOG comunicação interna

4. **EXECUTIVE_SUMMARY_GOLIVE.md** (218 linhas)
   - Tipo: Sumário executivo (1 página)
   - Conteúdo: 2-minute TL;DR de números, financeiro, risk, timeline
   - Uso: Apresentações rápidas, emails executivos
   - Referência em: BACKLOG P0-2 (decisão capital)

5. **INDICE_DOCUMENTACAO_GOLIVE.md** (471 linhas)
   - Tipo: Mapa de navegação
   - Conteúdo: Qual documento ler conforme tempo disponível (30s, 5m, 15m, 30m, 1.5h)
   - Uso: Guiaria stakeholders através pacote
   - Referência em: BACKLOG documentação

6. **PACOTE_ENTREGA_VALOR.md** (516 linhas)
   - Tipo: Business case completo
   - Conteúdo: 15 páginas - problema/solução, entregas, timeline, anexos
   - Uso: Documento-master para due diligence completa
   - Referência em: BACKLOG P0-2 (validação GATE 2)

7. **QUICK_REFERENCE_CARD_PO.md** (350 linhas)
   - Tipo: Cheat sheet de bolso (2 páginas)
   - Conteúdo: Ask, Return, Validation checklist, Risk management, Timeline
   - Uso: Leve em reuniões, referência rápida
   - Referência em: BACKLOG P4-2 (UAT preparation)

8. **README_PACOTE_ENTREGA_VALOR.md** (467 linhas)
   - Tipo: Quick start guide para PO
   - Conteúdo: Qual leitura conforme tempo, próximas ações por fase
   - Uso: Orientação inicial do pacote
   - Referência em: BACKLOG start here

9. **SUMARIO_ENTREGA_COMPLETA.md** (531 linhas)
   - Tipo: Sumário completo com matriz de referência
   - Conteúdo: O quê foi entregue, para quem cada doc serve, próximas ações
   - Uso: Visão 360° do pacote de entrega
   - Referência em: BACKLOG consolidação final

### P52-2: Verificação de Mobiliária e Consolidação

**Análise realizada em 04/03/2026:**
- ✅ Nenhum arquivo contém scripts Python (.py)
- ✅ Nenhum arquivo contém .bat files
- ✅ Nenhum arquivo contém outputs (json, csv, txt) a mover
- ✅ Todos são documentos markdown (.md) de referência
- ✅ Todos já estão em `docs/` (pasta correta)

**Consolidação em BACKLOG:**
- Status: Referência documentada para fases P0-2 até P4-3
- Nenhuma ação técnica pendente
- Servem como apoio às decisões de gate (especialmente GATE 2)

### P52-3: Recomendação de Acesso

Quando chegar em cada fase, consultar os documentos relevantes:

| Fase | Documentos Relevantes |
|------|--------------------|
| **P0-1, P0-2** | EXECUTIVE_SUMMARY, PACOTE_ENTREGA_VALOR |
| **GATE 1** | APRESENTACAO_BOARD (Slides 1-3) |
| **GATE 2** | APRESENTACAO_BOARD (Slides 1-5), PACOTE_ENTREGA_VALOR (pages 12-13) |
| **P4-1** | PACOTE_ENTREGA_VALOR (timeline section) |
| **P4-2 (UAT)** | CHECKLIST_APROVACAO, QUICK_REFERENCE_CARD |
| **Pre go-live** | EMAIL_TEMPLATES (send final confirmations) |

**Status:** ✅ P52 CONSOLIDADO - Nenhuma ação técnica. Documentação útil. Referência mantida em BACKLOG.

---

**Última Atualização:** 04/03/2026
**Responsável:** Product Owner + Head de Finanças (Brasil)
**Versão Final:** v5.0 (Refatorado Completo) + P52 Consolidação

Questões ou ajustes? Escalate para Product Owner.


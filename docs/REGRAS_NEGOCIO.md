# Regras de Negócio - Operador Day Trade WIN

**Data**: 06/03/2026 (AC1 Real Implementation Validated)
**Status**: ✅ COMPLETO
**Referência**: [ARCHITECTURE.md](ARCHITECTURE.md) | [DIAGRAMA_CLASSES.md](DIAGRAMA_CLASSES.md) | [ADRs.md](ADRs.md)

⭐ **CORE DO PRODUTO**: [INICIAR_DIARIOS.bat](../INICIAR_DIARIOS.bat) → [INICIAR_MICRO_TENDENCIA_AUTO_TRADE.bat](../INICIAR_MICRO_TENDENCIA_AUTO_TRADE.bat) na raiz implementam TODAS estas regras.

---

## 📋 Classificação de Regras

| Crítica | Risco | Otimização |
|---------|-------|-----------|
| 🔴 Devem ser implementadas | 🟡 Devem ser monitoradas | 🟢 Podem ser ajustadas |
| Violação = Sistema falha | Violação = Prejuízo | Violação = Performance reduzida |

---

## 🔴 REGRAS CRÍTICAS (P0 - Bloqueadores)

### R-CRÍTICA-001: Capital Adequacy Gate (Gate 1)

**Regra**: Saldo disponível deve ser ≥ (Ticket Size × Preço Entrada × 1.5)

**Cálculo**:
```
saldo_minimo = ticket_size × entry_price × 1.5
saldo_disponivel = account_balance - margin_utilizado
APROVADO se: saldo_disponivel ≥ saldo_minimo
```

**Implementação**: RiskValidator.validate_capital_adequacy()
**Violação**: Ordem REJEITADA imediatamente
**Timeout**: < 10ms (deve ser rápido)
**Testing**: test_risk_validator_gates.py (AC-1.1 a AC-1.5)

---

### R-CRÍTICA-002: Correlation Limit Gate (Gate 2)

**Regra**: Correlação máxima entre posições abertas ≤ 70%

**Cálculo**:
```
Para cada par de posições (A, B):
  correlation(returns_A, returns_B) ≤ 0.70
Se violar: Rejeitar nova ordem
```

**Contexto**: Evitar hedge inadequado ou double-sided risk
**Implementação**: RiskValidator.validate_correlation()
**Violação**: Ordem REJEITADA
**Timeout**: < 50ms
**Testing**: test_correlation_validation.py

**Comportamento**:
- ✅ Posição A (WIN spot) + Posição B (WDO correlated): REJEITA se corr > 0.70
- ✅ Posição A (WIN) + Posição B (outro símbolo): APROVA (correlação baixa)
- ✅ Nenhuma posição aberta: APROVA (sem correlação)

---

### R-CRÍTICA-003: Volatility Band Gate (Gate 3)

**Regra**: Volatilidade atual deve estar entre (ATR-3σ) e (ATR+3σ)

**Cálculo**:
```
atr_15min = Average True Range de 15 minutos
volatility_band_lower = atr_15min - (atr_15min × 3σ)
volatility_band_upper = atr_15min + (atr_15min × 3σ)

Se current_volatility < lower OU current_volatility > upper:
  REJECTED (mercado muito calmo ou caótico)
```

**Contexto**: Evitar operar em mercados extremos
**Implementação**: RiskValidator.validate_volatility()
**Violação**: Ordem REJEITADA
**Timeout**: < 20ms
**Testing**: test_volatility_validation.py

---

### R-CRÍTICA-004: MT5 Terminal Isolation (3 Camadas)

**Regra**: Sistema DEVE conectar sempre ao mesmo terminal MetaTrader 5

**Camada 1: Pre-flight Validation**
```
Ao startup:
  - Valida path do terminal executable
  - Testa conexão com isolamento check
  - Se falha → Bloqueia startup com mensagem clara
```

**Camada 2: Path Validation**
```
Ao conectar:
  - Verificar os.path.isfile() no path configurado
  - Validar que é terminal "CLEAR" (não FBS, Zero, etc)
  - Se falhar → BrokerConnectionError com detalhes
```

**Camada 3: Runtime Isolation Monitoring**
```
A cada ~30 segundos durante trading:
  - mt5._validate_terminal_isolation() verifica:
    * PID do terminal64.exe
    * Account login corrente
    * Server name
  - Se muda → Retry com exponential backoff (5s, 10s, 20s)
  - Se 3 retries falham → HALT automático
```

**Implementação**: MT5Adapter (3 métodos)
**Violação**: HALT imediato + log crítico + operador manual intervention
**Recovery**: Manual restart necessário
**Timeout**: < 100ms por check

**Referência**: [ADR-005: MT5 Terminal Protection](ADRs.md#adr-005-por-que-3-camadas-de-mt5-clear-protection)

---

### R-CRÍTICA-005: Order Execution Atomicity

**Regra**: Ordem DEVE ser persistida em SQLite ANTES de ser considerada executada

**Fluxo Garantido**:
```
1. MT5Adapter.send_order() → ticket obtido
2. ExecutionOrder.to_trade(ticket) → conversão
3. Repository.save_trade() com retry (3x exponential backoff: 0.5s, 1s, 2s)
4. Audit log atualizado
5. APENAS ENTÃO: return success

Se qualquer passo falha → REJECTED status + log detalhado
```

**Implementação**: SendToMT5Command.execute()
**Violação**: Ordem marcada como REJECTED, retry agendado
**Recovery**: Manual reconciliation se persistência falhar 3x
**Compliance**: CVM/B3 - audit trail completo

---

### R-CRÍTICA-006: Learning Loop Closure (P33)

**Regra**: HOLD rejections devem ser validadas contra outcome real

**Processo**:
```
1. Padrão registrado como HOLD
2. Após 1-5 min, trade é fechado
3. PredictionTracker.evaluate_last_prediction() valida acerto
4. IntraDayLearner.validate_hold(pattern, resultado.acertou)
5. Hit rate é calculado com dado REAL (não simulado)
```

**Implementação**: IntraDayLearner + PredictionTracker
**Status Atual**: P32 implementado (silencioso), P33 integração futura
**Violação**: RL aprende com dados incorretos → degradação de model
**SLA**: Integração P33 (04/03)

---

### R-CRÍTICA-007: Terminal Isolation Enforcer (S2-6) ✅ NOVO

**Regra**: Sistema DEVE bloquear 100% das tentativas de conectar a de brokers FBS/XP/Zero/IC/Ativa/Rica

**Objetivo**: Impedir erro operacional onde análise está em Clear mas ordem vai para broker errado.

**3 Camadas de Bloqueio:**

**Camada 1: Startup Validation (PRÉ-OPERAÇÃO)**
```
Ao iniciar launcher:
  - Enforcer valida MT5_TERMINAL_PATH (deve conter "CLEAR")
  - Config validator rejeita paths sem "CLEAR"
  - Se falha → EXIT 1 (termina processo imediatamente)
  - Timing: < 30s (pré-operação)
```

**Camada 2: Operation-Critical Validation (PONTO CRÍTICO)**
```
Antes de execute_entry:send_order():
  - Enforcer.validate_critical_operation("execute_entry:send_order")
  - Detecta automaticamente 6 brokers perigosos
  - Se falha → TerminalIsolationViolation levantada
  - RESULTADO: Ordem é REJEITADA (não envia para broker)
  - Timing: < 1ms (negligenciável)
```

**Camada 3: Continuous Monitoring (VIGILÂNCIA)**
```
A cada ciclo do main loop:
  - Enforcer.validate_continuous() monitora isolamento
  - Se MetaTrader muda para broker errado → KILL SWITCH
  - Sistema para automaticamente (sem enviar orderL)
  - Timing: Contínuo (cada ciclo ~100ms)
```

**Brokers Bloqueados (Detecção Automática):**
- FBS (www.fbs.com)
- XP Investimentos (www.xp.com.br)
- Zero Markets (zeromercado.io)
- IC Markets (icmarkets.com)
- Ativa (www.ativa.com.br)
- Rica Corretora (www.rica.com.br)

**Padrão de Detecção**: Case-insensitive substring matching no caminho exe do MT5.

**Implementação**: `src/infrastructure/terminal_isolation_enforcer.py` (380 LOC, v1.0)
**Violação**: HARD STOP - EXIT 1 ou rejeita operação (não permite continuar)
**Exceção**: `TerminalIsolationViolation` (tratada em CODING_STANDARDS.md § 6)
**Status**: ✅ IMPLEMENTADO 04/03/2026 - 6/6 testes PASSING

**Configuração Obrigatória**:
```bash
# .env (OBRIGATÓRIO)
MT5_TERMINAL_PATH="/path/to/Clear_Investimentos/terminal.exe"

# Validação
settings.mt5_terminal_path → Pydantic rejeita path sem "CLEAR"
```

**Monitoramento**:
- Método: `enforcer.get_isolation_status()` → Dict com estado completo
- Retorna: clear_pid, dangerous_terminals, violation_count, mode

**Referência**: [ADR-008: Terminal Isolation Enforcer](ADRs.md#adr-008-terminal-isolation-enforcer-com-3-camadas-de-bloqueio)
**Documentação**: [ARCHITECTURE.md § 4.5](ARCHITECTURE.md#45-terminal-isolation-enforcer-s2-6---novo--implementado-04032026)

---

## 🟡 REGRAS DE RISCO (Devem ser Monitoradas)

### R-RISCO-001: Maximum Drawdown Circuit Breaker

**Regra**: Se drawdown de sessão ≥ 3%, sistema entra em SLOW MODE. Se ≥ 5%, HALT.

**Três Níveis**:
```
🟡 -3%: ALERTA
  → Trader notificado via email/SMS
  → Sistema continua operando
  → Aumentar vigilância

🟠 -5%: SLOW MODE
  → Reduz volume para 50% do normal
  → Aumenta min_confidence_trade em 10%
  → Aguarda manual approval para grandes ordens

🔴 -8%: HALT AUTOMÁTICO
  → Sistema pausa todas as ordens
  → Posições abertas mantidas com SL
  → Requer manual restart
```

**Implementação**: CircuitBreaker em main loop
**Violação**: Executa ação automática (ALERT/SLOW/HALT)
**Recovery**: Manual intervention ou aguardar reset de sessão
**Compliance**: Risk management obrigatório

---

### R-RISCO-002: Position Size Limit

**Regra**: Máximo 2 posições simultâneas POR SÍMBOLO

**Cálculo**:
```
posicoes_abertas_WIN = count(open_positions where symbol='WIN')
Se posicoes_abertas_WIN ≥ 2:
  REJETA nova ordem para WIN

Máximo exposure (todos símbolos) = account_balance × 5%
```

**Implementação**: PositionMonitor.get_current_exposure()
**Violação**: Ordem REJEITADA
**Monitoragem**: Dashboard em tempo real

---

### R-RISCO-003: Stop Loss / Take Profit Obrigatorios

**Regra**: Toda ordem DEVE ter SL e TP definidos

**Cálculo**:
```
SL = entry_price ± (atr_15min × 1.5)
TP = entry_price ± (atr_15min × 2.5)

% Risk/Reward = (TP - entry) / (entry - SL)
Mínimo: 1:2 (para cada $ em risco, ganha $2)
```

**Implementação**: ATRCalibrator.calculate_trailing_stop()
**Violação**: Ordem REJEITADA se SL/TP não definidos
**Ajuste Dinâmico**: ATR recalculado a cada 5 min

---

### R-RISCO-004: Confidence Threshold Dinâmico

**Regra**: MIN_CONFIDENCE_TRADE pode ser ajustado por IntraDayLearner baseado em hit_rate

**Comportamento**:
```
Base: MIN_CONFIDENCE_TRADE = 0.65 (configurável em .env)

Hit Rate Tracking:
  - Se 5+ padrões com hit_rate > 80% → boost (+5%)
  - Se 5+ padrões com hit_rate < 40% → penalty (-10%)

Limite: Não pode variar mais que ±30% do base value
  Min: 0.65 × 0.70 = 0.455
  Max: 0.65 × 1.30 = 0.845

Aplicação: [P35] Esse ajuste entra em vigor na próxima ordem

Reverta: Sempre que nova sessão inicia (reset diário)
```

**Implementação**: IntraDayLearner.get_current_adjustments()
**Monitoragem**: Audit log em outputs/intraday_audit_{SESSION_ID}.log
**Impact Esperado**: +1-2% win rate após validação (P35-P36)

---

## � REGRAS P50: PESSIMISM DETECTION & AUTO-RECOVERY

### R-RISCO-P50-001: Confidence Threshold Minimum (Detecção Pessimismo)

**Regra**: Quando confidence < 0.45 por 10+ ciclos consecutivos, sistema detectou pessimismo

**Cálculo**:
```
pessimism_detected = (confidence_value < 0.45) AND (consecutive_cycles ≥ 10)
Se pessimism_detected = TRUE:
  → Trigger: ConfidenceHealthChecker.detect_pessimism()
  → Action: Iniciar reset gradual de thresholds
  → Notification: Log alerta de pessimismo detectado
```

**Implementação**: `scripts/check_confidence_health.py` | **Validação Automática**: ✅ ConfidenceHealthChecker | **Monitoramento**: Pessimism flag
**Violação (não resolvida)**: Sistema continua operando com pessimismo por > 48h = prejuízo
**Timeout**: < 5s no ciclo de detecção
**Testing**: test_p50_full.py (11 test cases covering detection)

---

### R-RISCO-P50-002: Threshold Adjustment Recovery (Reset Pessimismo)

**Regra**: Quando pessimismo detectado, reduzir thresholds gradualmente até sistema recuperar confiança

**Cálculo**:
```
Estratégia GRADUAL (padrão):
  Ciclo 1-8:    TP reduced by 25% (-1%), SL reduced by 25% (-1%)
  Ciclo 9-16:   Confidence retraining 25% dos dados recentes
  Ciclo 17-24:  Gradual restore de TP/SL original (1% a cada ciclo)

Se win_rate recupera para > 0.62: Early exit (pular ciclos restantes)
```

**Implementação**: `scripts/reset_pessimism_mode.py` | **Validação Automática**: ✅ PessimismResetManager | **Monitoramento**: Threshold adjustments
**Trigger**: Automático quando pessimism_detected = TRUE
**Duration**: 24 ciclos (ajustável via pessimism_mode.json reset_strategy)

---

### R-RISCO-P50-003: Confidence Retraining Trigger (Retraining Automático)

**Regra**: Quando confidence está degradando (< win_rate por N ciclos), disparar retraining automático

**Cálculo**:
```
degradation_detected = confidence_value < (win_rate_recent - 0.05)

Se degradation_detected AND pessimism_recovery_in_progress:
  → Trigger: ConfidenceRetrainer.calculate_win_rate()
  → Adjust: confidence_threshold = win_rate_recent - margin_safety(0.03)
  → Update: confidence_history.json + pessimism_mode.json
```

**Implementação**: `scripts/daily_confidence_retraining.py` | **Validação Automática**: ✅ ConfidenceRetrainer | **Monitoramento**: Retraining logs
**Frequency**: Diário às 00:00 UTC (após fechamento do mercado)
**Backtest Period**: 20 ciclos (últimos dias de trading)
**Safety Margin**: 3% (não deixar confidence muito próximo de win_rate)

---
## 🔴 REGRAS DE PROTEÇÃO P0-3 (Circuit Breaker - Planejado 06/03)

### R-RISCO-P0-3-001: Circuit Breaker Amarelo (-3%)

**Regra**: Quando capital loss alcança -3%, disparar ALERTA (trading continua)

**Implementação**:
```
drawdown_percentual = (session_balance_minimo - session_balance_inicio) / session_balance_inicio
Se drawdown_percentual <= -0.03 AND drawdown_percentual > -0.05:
  → Status: YELLOW
  → Ação: Log alerta | Dashboard warning | Notificação trader
  → Trading: Continua (sem restrições)
  → Duração: Até recuperação (manual reset)
```

**Trigger**: Contínuo (monitorado a cada ciclo)
**Ação Trader**: Pode parar manualmente sistema se julgar necessário
**Revert**: Automático quando drawdown volta acima de -3%
**Validação**: CIRCUIT_BREAKER_HISTORY table

---

### R-RISCO-P0-3-002: Circuit Breaker Laranja (-5%)

**Regra**: Quando capital loss alcança -5%, ativar SLOW MODE (50% ticket, ML ≥90%)

**Implementação**:
```
Se drawdown_percentual <= -0.05 AND drawdown_percentual > -0.08:
  → Status: ORANGE
  → Ação:
    1. Reduzir ticket size a 50% do normal
    2. Aumentar ML confidence threshold para 0.90
    3. Desabilitar oportunidades < 0.90
  → Trading: Continua com restrições
  → Duração: Até -3% ou -8% (gate transition)
```

**Entrada (Trigger)**: Drawdown -5%
**Saída (Recovery)**: Drawdown volta para -3% (volta a YELLOW)
**Fallback**: Se continuar piorando → RED threshold
**Validação**:
- CIRCUIT_BREAKER_CONFIG.ticket_reduction_percent_slow_mode = 50
- CIRCUIT_BREAKER_CONFIG.ml_score_threshold_slow_mode = 0.90

---

### R-RISCO-P0-3-003: Circuit Breaker Vermelho (-8%)

**Regra**: Quando capital loss alcança -8%, HALTAR todas as operações

**Implementação**:
```
Se drawdown_percentual <= -0.08:
  → Status: RED
  → Ação:
    1. Haltar todas as operações em tempo real
    2. Fechar todas posições abertas (stop-loss)
    3. Sistema em standby (aguardando análise)
  → Trading: BLOQUEADO completamente
  → Duração: Até decisão manual do trader/CIO/CFO
```

**Trigger**: Drawdown -8% (BLOQUEANTE)
**Recovery**: Manual (requer aprovação CIO/CFO para reativação)
**Fallback**: Email + SMS alerta para stakeholders
**Timeline**: Imediato (< 100ms de detecção a halt)
**Validação**: CIRCUIT_BREAKER_HISTORY + sistema_halt_status

---

### R-RISCO-P0-3-004: Circuit Breaker Reset Protocol

**Regra**: Recuperação da Red → Orange → Yellow seguindo drawdown recovery

**Implementação**:
```
recovery_check = drawdown_percentual > last_worst_drawdown_em_sessao

Se recovery_detected:
  Se drawdown > -0.08: permanecer RED (até < -0.08)
  Se drawdown ≤ -0.05: transicionar para RED→ORANGE
  Se drawdown ≤ -0.03: transicionar para ORANGE→YELLOW
  Se drawdown > -0.03: transicionar para YELLOW→GREEN (normal)
```

**Automatismo**: 100% automático (não requer ação manual)
**Incrementalidade**: Cada gate transition logged separately
**Validação**: CIRCUIT_BREAKER_HISTORY.recovery_timestamp atualizado
**Auditoria**: recovery_timestamp field para compliance

---
## �🟢 REGRAS DE OTIMIZAÇÃO

### R-OTI-001: Latência Máxima de Execução

**Target P95**: < 500ms (end-to-end)

**Breakdown**:
```
T1: Feature Calculation     < 100ms
T2: Decision Making         < 100ms
T3: Order Transmission      < 300ms
T_TOTAL: < 500ms
```

**Monitoramento**: Cada ordem log timestamp (envio + confirmação MT5)
**Violação**: Log + alertar se > 500ms persistentemente

---

### R-OTI-002: Database Query Performance

**Target**:
```
SELECT trades (historical) : < 100ms
INSERT new trade         : < 50ms
UPDATE position status   : < 30ms
```

**Índices Obrigatórios**:
- trades(symbol, timestamp)
- positions(symbol, status)
- decisions(timestamp)

---

### R-OTI-003: Memory Footprint

**Target**: < 100MB RAM durante operação (exclui market data)

**Monitoramento**:
```python
import psutil
memory_usage = psutil.Process().memory_info().rss / 1024**2
if memory_usage > 100:
    log.warning(f"Memory usage high: {memory_usage}MB")
```

---

## 📊 Matriz de Validação

| Regra | Crítica | Layer | Validação Automática | Monitoramento |
|-------|---------|-------|----------------------|----------------|
| **R-CRÍTICA-001** | 🔴 SIM | Decision | ✅ RiskValidator | Gate 1 pass/fail |
| **R-CRÍTICA-002** | 🔴 SIM | Decision | ✅ RiskValidator | Gate 2 pass/fail |
| **R-CRÍTICA-003** | 🔴 SIM | Decision | ✅ RiskValidator | Gate 3 pass/fail |
| **R-CRÍTICA-004** | 🔴 SIM | Execution | ✅ MT5Adapter (3 camadas) | Health check 30s |
| **R-CRÍTICA-005** | 🔴 SIM | Execution | ✅ SendToMT5Command | Retry count |
| **R-CRÍTICA-006** | 🔴 SIM | Learning | ⏳ P33 | Audit log |
| **R-CRÍTICA-007** | 🔴 SIM | Security | ✅ TerminalIsolationEnforcer (3 camadas) | Violation count |
| **R-RISCO-001** | 🟡 SIM | Execution | ✅ CircuitBreaker | Dashboard |
| **R-RISCO-002** | 🟡 SIM | Decision | ✅ PositionMonitor | Current exposure |
| **R-RISCO-003** | 🟡 SIM | Execution | ✅ ATRCalibrator | Order details |
| **R-RISCO-004** | 🟡 SIM | Learning | ✅ IntraDayLearner [P35] | Intraday audit |
| **R-RISCO-P50-001** | 🟡 SIM | Detection | ✅ ConfidenceHealthChecker | Pessimism flag |
| **R-RISCO-P50-002** | 🟡 SIM | Recovery | ✅ PessimismResetManager | Threshold adjustments |
| **R-RISCO-P50-003** | 🟡 SIM | Learning | ✅ ConfidenceRetrainer | Retraining logs |
| **R-OTI-001** | 🟢 NÃO | Monitoring | 📊 Manual check | Latency logs |
| **R-OTI-002** | 🟢 NÃO | Data | ✅ Query analyzer | Slow query log |
| **R-OTI-003** | 🟢 NÃO | Monitoring | 📊 psutil check | Memory monitor |

---

## 🔗 Referências Cruzadas

| Regra | Referência em Código | ADR |
|-------|-------------------   |-----|
| R-CRÍTICA-001 | `src/application/risk_validator.py:40` | [ADR-002](ADRs.md#adr-002-por-que-3-gates-de-risco-sequenciais) |
| R-CRÍTICA-002 | `src/application/risk_validator.py:80` | [ADR-002](ADRs.md#adr-002-por-que-3-gates-de-risco-sequenciais) |
| R-CRÍTICA-003 | `src/application/risk_validator.py:120` | [ADR-002](ADRs.md#adr-002-por-que-3-gates-de-risco-sequenciais) |
| R-CRÍTICA-004 | `src/infrastructure/providers/mt5_adapter.py:387-440` | [ADR-005](ADRs.md#adr-005-por-que-3-camadas-de-mt5-clear-protection) |
| R-CRÍTICA-005 | `src/application/orders_executor.py:206-315` | [ADR-003](ADRs.md#adr-003-por-que-mt5-rest-adapter-vs-direct-dll) |
| R-CRÍTICA-006 | `scripts/agente_micro_tendencia_winfut.py:2489-2618` | [ADR-004](ADRs.md#adr-004-por-que-intradaylearner-em-memoria-vs-sqlite-imediato) |
| R-CRÍTICA-007 | `src/infrastructure/terminal_isolation_enforcer.py:1-380` | [ADR-008](ADRs.md#adr-008-terminal-isolation-enforcer-com-3-camadas-de-bloqueio) |
| R-RISCO-001 | `scripts/agente_micro_tendencia_winfut.py:4377+` | [ADR-006](ADRs.md#adr-006-circuit-breaker-strategy) |
| R-RISCO-004 | `scripts/agente_micro_tendencia_winfut.py:2489-2618` | [ADR-004](ADRs.md#adr-004-por-que-intradaylearner-em-memoria-vs-sqlite-imediato) |
| R-RISCO-P50-001 | `scripts/check_confidence_health.py:100-150` | [ADR-010](ADRs.md#adr-010-por-que-pessimism-detection-p50-urgente) |
| R-RISCO-P50-002 | `scripts/reset_pessimism_mode.py:1-180` | [ADR-010](ADRs.md#adr-010-por-que-pessimism-detection-p50-urgente) |
| R-RISCO-P50-003 | `scripts/daily_confidence_retraining.py:50-120` | [ADR-010](ADRs.md#adr-010-por-que-pessimism-detection-p50-urgente) |
| R-RISCO-P0-3-001 | `(Planejado P0-3 06/03)` | [ADR-011](ADRs.md#adr-011-gate-2-fail---risk-management-prioritization-vs-model-tuning) |
| R-RISCO-P0-3-002 | `(Planejado P0-3 06/03)` | [ADR-011](ADRs.md#adr-011-gate-2-fail---risk-management-prioritization-vs-model-tuning) |
| R-RISCO-P0-3-003 | `(Planejado P0-3 06/03)` | [ADR-011](ADRs.md#adr-011-gate-2-fail---risk-management-prioritization-vs-model-tuning) |
| R-RISCO-P0-3-004 | `(Planejado P0-3 06/03)` | [ADR-011](ADRs.md#adr-011-gate-2-fail---risk-management-prioritization-vs-model-tuning) |

---

## 📝 Histórico de Mudanças

| Data | Regra | Mudança | Razão |
|------|-------|---------|-------|
| 03/03/2026 | R-CRÍTICA-001 a 006 | Criação | P32 IntraDayLearner + MT5 Protection |
| 03/03/2026 | R-RISCO-004 | Adição | Confidence threshold dinâmico |
| 05/03/2026 | R-RISCO-P50-001,002,003 | Adição | P50 implementado e operacional |
| 05/03/2026 | R-RISCO-P0-3-001 a 004 | Planejamento | ADR-011 GATE 2 FAIL - Risk Management Priority |
| TBD | R-CRÍTICA-006 | Atualização | P33 integração com PredictionTracker |
| TBD | R-RISCO-P0-3-001 a 004 | Implementação | P0-3 Circuit Breaker (06-10/03/2026) |

---

**ÚLTIMA ATUALIZAÇÃO:** 05/03/2026 12:32 BRT | **STATUS**: ✅ COMPLETO (P50 + P0-3 planning)

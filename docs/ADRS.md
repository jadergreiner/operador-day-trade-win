# Architecture Decision Records (ADRs) - Operador Day Trade WIN

## Indice

- [Canonical Docs Policy](#canonical-docs-policy)
- [O que é ADR?](#o-que-adr)
- [ADR-001: Por que SQLite vs PostgreSQL como BD Primário?](#adr-001-por-que-sqlite-vs-postgresql-como-bd-primrio)
- [ADR-001: Por que SQLite vs PostgreSQL como BD Primário? — Contexto](#contexto)
- [ADR-001: Por que SQLite vs PostgreSQL como BD Primário? — Decisão](#deciso)
- [ADR-001: Por que SQLite vs PostgreSQL como BD Primário? — Consequências](#consequncias)
- [ADR-001: Por que SQLite vs PostgreSQL como BD Primário? — Próximas Ações](#prximas-aes)
- [ADR-001: Por que SQLite vs PostgreSQL como BD Primário? — Referências](#referncias)
- [ADR-002: Por que 3 Gates de Risco Sequenciais?](#adr-002-por-que-3-gates-de-risco-sequenciais)
- [ADR-011: Isolamento de Posicoes entre Agentes RL](#adr-011-isolamento-de-posicoes-entre-agentes-rl-rl-5000-vs-rl-direto)
- [ADR-012: Magic Number (EA ID) por Agente](#adr-012-magic-number-ea-id-por-agente---isolamento-de-ordens-mt5)
- [ADR-017: Premissa Intraday — lookback_days=7](#adr-017-premissa-intraday--lookback_days7-no-pipeline-de-reconciliacao)
- [ADR-018: Governanca de Thresholds do Profit Protection por Perfil](#adr-018-governanca-de-thresholds-do-profit-protection-por-perfil-com-rollout-canario)
- [ADR-019: Segregacao do Banco dos Diarios e Padrao schema_version](#adr-019-segregacao-do-banco-dos-diarios-e-padrao-schema_version)
- [ADR-020: Score de Relevancia de Perguntas por Correlacao WIN/LOSS](#adr-020-score-de-relevancia-de-perguntas-por-correlacao-winloss)
- [ADR-021: MacroGuardianReaderService como Canal Universal de Leitura](#adr-021-macroguardianreaderservice-como-canal-universal-de-leitura)
- [ADR-022: OrderManagerAdaptiveService e RegimeMercado](#adr-022-ordermanageradaptiveservice-e-regimemercado)
- [ADR-023: FechamentoDiarioAgenteService — Fechamento Individualizado por Agente RL](#adr-023-fechamentodiariorageenteservice--fechamento-individualizado-por-agente-rl)


## Canonical Docs Policy

From this update onward, the canonical docs set is:

- `docs/ADRS.md` (this file, case-insensitive with `ADRS.md` on Windows)
- `docs/ADRS.md` (compatibility alias to avoid cross-platform link break)
- `docs/ARQUITETURA_ALVO.md`
- `docs/BACKLOG.md`
- `docs/DIAGRAMAS.md`
- `docs/MODELAGEM_DE_DADOS.md`
- `docs/REGRAS_DE_NEGOCIO.md`
- `docs/governanca/README.md`
- `docs/contratos/README.md`
- `docs/modelos/README.md`

Legacy docs remain read-only for historical traceability.

**Estado Atual:** as trilhas principais e o runtime bridge do fluxo diario ja
estao implementados; a validacao operacional final segue em staging, UAT e Gate 2.

⭐ **CORE DO PRODUTO**: As decisões arquiteturais aqui registradas foram tomadas para suportar a execução eficiente de:

- [INICIAR_DIARIOS.bat](../INICIAR_DIARIOS.bat)
- [INICIAR_MICRO_TENDENCIA_AUTO_TRADE.bat](../INICIAR_MICRO_TENDENCIA_AUTO_TRADE.bat)
- [INICIAR_AGENTE_RL_5000.bat](../INICIAR_AGENTE_RL_5000.bat)
- [INICIAR_AGENTE_RL_DIRETO.bat](../INICIAR_AGENTE_RL_DIRETO.bat)
- [INICIAR_MONITOR_QUANTICO.bat](../INICIAR_MONITOR_QUANTICO.bat)

---

## O que é ADR?

**ADR (Architecture Decision Record)** é um documento que captura uma decisão arquitetural importante junto com:
- **Contexto**: Por que a decisão foi necessária?
- **Decisão**: Qual foi a escolha?
- **Consequências**: Quais são os trade-offs?
- **Status**: PROPOSED, ACCEPTED, DEPRECATED, SUPERSEDED

---

## ADR-001: Por que SQLite vs PostgreSQL como BD Primário?

**Status**: ✅ ACCEPTED (atualizado em 04/04/2026)
**Data**: 27/02/2026

### Contexto
Sistema precisa de persistência de trading com baixa latência. Trade decisions ocorrem em ~500ms P95, logo storage não pode ser bottleneck.

### Decisão
**Usar SQLite como banco de dados primário** em fase 1-2 (até GO LIVE 10/04/2026).

### Consequências
✅ **Prós**:
- Zero dependência de servidor externo (embedded)
- Latência sub-10ms para INSERT (vs 50-100ms em PostgreSQL over network)
- Arquivo único para backup (data/db/trading.db)
- Simplicidade operacional (zero configuração DB)
- ACID completo com journal mode WAL

❌ **Contras**:
- Máximo ~1 conexão simultânea confiável (não é multi-user)
- Não escalável para múltiplas instâncias (later phases)
- File I/O bound (requer bom SSD)

### Próximas Ações
- **Phase 4 (10/04+)**: Migração para PostgreSQL no Azure (`operador-db-staging.postgres.database.azure.com`)
- **Phase 3**: Replicação SQLite → PostgreSQL (dual-write)

### Referências
- [MODELAGEM_DE_DADOS.md](MODELAGEM_DE_DADOS.md) - Schema SQLite
- [REGRAS_DE_NEGOCIO.md](REGRAS_DE_NEGOCIO.md#r-crítica-005-order-execution-atomicity) - Atomicity rule

---

## ADR-002: Por que 3 Gates de Risco Sequenciais?

**Status**: ✅ ACCEPTED
**Data**: 20/02/2026

### Contexto
Sistema de trading automático com capital real. Risk manager (Head Finanças) exige múltiplas camadas de validação para evitar over-trading ou violações de capital adequacy (CVM/B3).

### Decisão
**Implementar 3 gates sequenciais em RiskValidator:**
```
Gate 1: Capital Adequacy → Saldo deve ser ≥ 1.5x ticket (R-CRÍTICA-001)
Gate 2: Correlation Check → Corr entre positions ≤ 70% (R-CRÍTICA-002)
Gate 3: Volatility Band  → ATR deve estar in [lower, upper] (R-CRÍTICA-003)
```

**Chain of Responsibility Pattern**: Cada gate rejeita ordem se falha, próxima gate não é testada.

### Consequências
✅ **Prós**:
- Independência: Cada gate é testável separadamente
- Clarity: Rejeição menciona qual gate falhou
- Performance: Falha rápido (não testa volatility se capital falhou)
- Risk isolation: Um gate quebrado não quebraaos outros

❌ **Contras**:
- Overhead de 3 validações por ordem (~20ms total)
- Complexidade de debugging (interação entre gates)

### Exemplo de Fluxo
```python
order = ExecutionOrder(symbol="WIN", volume=1, entry_price=12500)

# Gate 1: Capital
if not validate_capital_adequacy(order):
    return REJECTED("Gate 1: Insufficient capital")

# Gate 2: Correlation
if not validate_correlation(positions, order):
    return REJECTED("Gate 2: Correlation breach")

# Gate 3: Volatility
if not validate_volatility(symbol, atr):
    return REJECTED("Gate 3: Volatility band breach")

# All gates passed
return APPROVED(order)
```

### Referências
- [REGRAS_DE_NEGOCIO.md](REGRAS_DE_NEGOCIO.md) - R-CRÍTICA-001, 002, 003
- [DIAGRAMAS.md](DIAGRAMAS.md) - RiskValidator class

---

## ADR-003: Por que MT5 REST Adapter vs Direct DLL?

**Status**: ✅ ACCEPTED
**Data**: 15/02/2026

### Contexto
MetaTrader 5 fornece 2 formas de integração:
1. **DLL Direct**: Chamar `terminal64.exe` DLL directly (low-level)
2. **REST API Gateway**: Chamar endpoint HTTP (high-level)

### Decisão
**Usar REST API Adapter** com isolamento terminal obrigatório (S2-5).

```python
MT5Adapter:
  - Envia ordem via POST /mt5/send_order
  - Recebe ticket em response de forma atomic
  - Retry logic built-in (3x exponential backoff)
  - Health check continuous (30s)
```

### Consequências
✅ **Prós**:
- Abstração: Desacoplado de versão MT5 (protocolo estável)
- Observability: HTTP logs tudo (audit trail)
- Resilience: Retry logic built-in
- Isolated: Terminal é um serviço separado (pode reiniciar sem quebrar agente)
- Testing: Mock REST para testes E2E

❌ **Contras**:
- Latência adicional (~50ms vs direct DLL ~5ms)
- Dependência de servidor REST rodando
- Network overhead

### Health Check Integrado
```python
# A cada 30s em runtime
response = mt5_adapter._validate_terminal_isolation():
  1. Check PID do terminal64.exe
  2. Check account_login corrente
  3. Check server name
  Se diferente → retry (5s, 10s, 20s) → HALT se falha
```

### Referências
- [ARQUITETURA_ALVO.md](ARQUITETURA_ALVO.md#s2-5-mt5-terminal-isolation--reconnect) - S2-5 spec
- [REGRAS_DE_NEGOCIO.md](REGRAS_DE_NEGOCIO.md#r-crítica-004-mt5-terminal-isolation-3-camadas) - Protection rule

---

## ADR-004: Por que IntraDayLearner em Memória vs SQLite Imediato?

**Status**: ✅ ACCEPTED
**Date**: 03/03/2026

### Contexto
IntraDayLearner precisa rastrear padrões de HOLD rejections durante trading session (~8 horas). Deve registrar silenciosamente (sem poluir tela) mas mantê-lo em memória rápido.

### Decisão
**Implementar em 2 fases:**

**Phase P32 (03/03) - COMPLETO**: IntraDayLearner em memória
```python
class IntraDayLearner:
    rejection_patterns: Dict[str, List]  # Em memória
    hit_rate_history: Dict[str, float]   # Calculado em tempo real
    session_start: datetime               # Marca início sessão

    def record_rejection(...):
        # Log silencioso em memória (TRANSPARENTE)

    def validate_hold(...):
        # Calcula hit_rate desde session_start
        # Se hit_rate > 80% ou < 40% → boost/penalty
```

**Phase P34 (05/03) - FUTURA**: SQL persistence
```python
CREATE TABLE intraday_adjustments (
    id, timestamp, pattern, hit_rate, adjustment_percent, session_id
)
# Persist ao final da sessão (17:55)
# Restore no restart (continuidade entre dias)
```

### Consequências
✅ **Prós**:
- **P32**: Transparência operador (zero screen pollution)
- Latência: Subms (~1μs memory access vs ~10ms SQL write)
- Simplicidade: Nenhuma configuração SQL
- Auditoria: Audit log em outputs/ (file-based, portable)

❌ **Contras**:
- Memory: Dict crescer com sessão (mas limite de 5MB estimado)
- Volatilidade: Ajustes perdidos se crash (resolvido em P34 com SQL)
- Sessão-bound: Reset a cada 17:55 (por design)

### Fluxo Completo (P32-P36)
```
P32 (03/03): Silencieux registration + transparent mode
    ↓
P33 (04/03): Integração com PredictionTracker
    ├─ Validação real vs simulação
    └─ Hit_rate com dados verdadeiros
    ↓
P34 (05/03): SQLite persistence
    ├─ Persist adjustments ao final sessão
    └─ Restore no restart
    ↓
P35 (06/03): Dynamic threshold application
    ├─ Aplicar boost/penalty REALMENTE
    └─ Esperado +1-2% win rate
    ↓
P36 (07-09/03): Dashboard operacional
    └─ Visualização real-time de aprendizado
```

### Referências
- [REGRAS_DE_NEGOCIO.md](REGRAS_DE_NEGOCIO.md#r-risco-004-confidence-threshold-dinâmico) - Dynamic threshold rule
- [ARQUITETURA_ALVO.md](ARQUITETURA_ALVO.md#6-learning-layer-camada-de-aprendizado-⭐-new) - Learning Layer spec

---

## ADR-005: Por que 3 Camadas de MT5 CLEAR Protection?

**Status**: ✅ ACCEPTED
**Date**: 03/03/2026

### Contexto
Operador tem múltiplos terminais MT5 no mesmo PC (FBS, Zero, CLEAR). Risco: Agente conecta ao terminal ERRADO e executa ordens com dinheiro privado (não CLEAR/operador).

### Decisão
**Implementar 3 camadas de isolamento:**

**Camada 1: Pre-flight Validation (Startup)**
```python
def _preflight_check_mt5(config):
    # Validar path do terminal antes de qualquer operação
    terminal_path_valid = os.path.isfile(config.mt5_terminal_path)
    if not terminal_path_valid:
        raise BrokerConnectionError(f"Terminal not found: {config.mt5_terminal_path}")

    # Testar conexão com isolamento check
    # Se falha → BLOQUEIA startup
```

**Camada 2: Path Validation (Connection)**
```python
def _validate_terminal_isolation(self):
    # Validar que path contém "CLEAR"
    if "CLEAR" not in self.terminal_exe_path:
        raise BrokerConnectionError("Wrong terminal: not CLEAR")

    # Validar arquivo existe
    if not os.path.isfile(self.terminal_exe_path):
        raise BrokerConnectionError("Terminal exe not found")

    # Check PID + account_login + server_name
    return self._check_fingerprint()
```

**Camada 3: Runtime Isolation Monitoring (Every 30s)**
```python
# A cada ciclo (~30s durante trading)
if not mt5._validate_terminal_isolation():
    # Detectou desconexão ou mudança de terminal
    # Retry com exponential backoff (5s, 10s, 20s)
    # Se 3 retries falham → HALT automático
```

### Consequências
✅ **Prós**:
- **Impossível conectar ao terminal errado** (3 camadas de validação)
- Fail-safe: HALT automático se isolamento viola
- Recovery: Exponential backoff permite recuperação de desconexões transitórias
- Observable: Health check logs failures

❌ **Contras**:
- 3 chamadas per 30s (~10ms overhead)
- Complexidade (3 pontos de validação)
- Operador manual intervention se HALT

### Cenários Testados
```python
# Cenário 1: Wrong terminal
terminal_path = "C:\Program Files\FBS MT5\terminal64.exe"
# → Pre-flight valida "CLEAR" not in path → REJEITA

# Cenário 2: Desconexão automática
# T=0s: Conectado (PID=1234, login=1000346516)
# T=30s: Desconectado
# → Runtime check detecta desconexão
# → Retry 1 (5s): Still offline
# → Retry 2 (10s): Back online
# → Success, continua trading

# Cenário 3: Terminal mudou
# T=0s: Conectado (login=1000346516)
# T=60s: Terminal reiniciou, login mudou (1000346520)
# → Runtime check detecta mudança
# → 3 retries esgotados
# → HALT automático, operador intervenção manual
```

### Referências
- [ARQUITETURA_ALVO.md](ARQUITETURA_ALVO.md#s2-5-mt5-terminal-isolation--reconnect) - S2-5 full spec
- [REGRAS_DE_NEGOCIO.md](REGRAS_DE_NEGOCIO.md#r-crítica-004-mt5-terminal-isolation-3-camadas) - Protection rule

---

## ADR-006: Circuit Breaker Strategy (Drawdown Management)

**Status**: ✅ ACCEPTED
**Date**: 20/02/2026

### Contexto
Sistema de trading automático com capital real. Necessário proteger contra perdas catastróficas.

### Decisão
**3-level Circuit Breaker:**

```
Drawdown: -3%  → 🟡 ALERTA
  ├─ Notify trader (email + SMS)
  ├─ Continue operating
  ├─ BUT: aumentar vigilância

Drawdown: -5%  → 🟠 SLOW MODE
  ├─ Reduz volume para 50%
  ├─ Aumenta min_confidence_trade +10%
  ├─ Aguarda manual approval para grandes ordens

Drawdown: -8%  → 🔴 HALT AUTOMÁTICO
  ├─ Pausa TODAS as ordens
  ├─ Posições abertas mantidas com SL
  ├─ Requer manual restart para retomar
```

### Consequências
✅ **Prós**:
- Graduado: Não é binário (alerta → slow → halt)
- Operador aware: Notificação imediata de problemas
- Capital protected: HALT antes de loss crítico
- Recovery: Manual restart permite análise pós-mortem

❌ **Contras**:
- Overhead: Cálculo de drawdown a cada trade
- Falsos positivos: Drawdown temporário pode gerar alerta desnecessário
- Complexidade operacional: 3 modos diferentes

### Implementation
```python
def check_circuit_breaker(current_balance, session_start_balance):
    drawdown_percent = (current_balance - session_start_balance) / session_start_balance * 100

    if drawdown_percent <= -8:
        return HALT  # 🔴
    elif drawdown_percent <= -5:
        return SLOW_MODE  # 🟠
    elif drawdown_percent <= -3:
        return ALERT  # 🟡
    else:
        return NORMAL
```

### Referências
- [REGRAS_DE_NEGOCIO.md](REGRAS_DE_NEGOCIO.md#r-risco-001-maximum-drawdown-circuit-breaker) - Rule definition

---

## ADR-007: Event-Driven Architecture vs Polling

**Status**: ✅ ACCEPTED
**Date**: 15/02/2026

### Contexto
Sistema de trading precisa reagir a eventos de mercado (nuevos candles, fills MT5) com baixa latência.

### Decisão
**Usar Event-Driven Architecture:**
```
Market Data Stream (websocket)
    ├─ NewCandleEvent
    ├─ TickEvent
    └─ MT5FillEvent

    → EventBus (pub/sub)

    subscribers:
    ├─ FeatureEngineer: calcula features
    ├─ MLPredictor: prediz direção
    ├─ RiskValidator: valida risco
    ├─ OrdersExecutor: executa ordens
    └─ PositionMonitor: monitora posições
```

### Consequências
✅ **Prós**:
- Latência: Subsecond vs 1s polling
- Desacoplamento: Subscribers independentes
- Scalability: Novo subscriber sem mudar others
- Observability: Event logs tudo

❌ **Contras**:
- Complexidade: Async/await e event ordering
- Debugging: Fluxo não-linear (harder to trace)
- Race conditions: Múltiplos events simultâneos

### Referências
- [ARQUITETURA_ALVO.md](ARQUITETURA_ALVO.md#princípios-arquiteturais) - Principles

---

## ADR-009: Rest API Gateway com Proxy Transparente para MT5 Orders

**Status**: ✅ **ACCEPTED** (04/03/2026)
**Autor**: Eng Sr (Technical Lead)
**Prioridade**: 🔴 P0-1 (CRÍTICO - desbloqueia arquitetura de execução)
**Data**: 04/03/2026
**Próximo Review**: 10/04/2026 (GO-LIVE)

### Contexto

**Necessidade**: System precisa intermediar chamadas `mt5.send_order()` para:
1. Enfileiramento assíncrono (não bloqueia agente)
2. Retry logic com exponential backoff
3. Auditoria completa (SQLite trail 7 anos)
4. Fallback gracioso se API falha

**Abordagens Consideradas**:
1. ❌ **DLL Wrapper MT5**: Alto acoplamento, complexo
2. ❌ **Polling direto MT5**: Latência >1s, bloqueia agente
3. ✅ **REST API Gateway com Proxy Transparente**: Separa concerns, permite retry, auditoria

### Decisão

**Implementar 3 camadas:**

**Camada 1: REST API Gateway (FastAPI Server)**
```python
# src/interfaces/api/fastapi_server.py
app = FastAPI(
    title="API REST MT5 - P0-1",
    description="Execução de ordens via ExecutionOrder queue"
)

@app.post("/api/v1/orders")
async def create_order(request: CreateOrderRequest):
    # 1. Valida parâmetros + risco
    # 2. Enfileira em RabbitMQ (async)
    # 3. Retorna order_id + status
    # 4. Background: executar async via OrdersExecutor
```

**Camada 2: OrderAPIClient (HTTP Client)**
```python
# src/infrastructure/clients/order_api_client.py
class OrderAPIClient:
    """Cliente HTTP com retry logic"""

    def create_order(self, symbol, volume, order_type):
        # 1. POST /api/v1/orders
        # 2. Retry 3x: 1s, 2s, 4s exponential backoff
        # 3. Retorna APIOrderResponse com audit trail
        # 4. Fallback: se API falha 3x → tenta MT5 direto
```

**Camada 3: MT5AdapterProxy (Transparent Proxy)**
```python
# src/infrastructure/adapters/mt5_adapter_proxy.py
class MT5AdapterProxy:
    """Intercepta mt5.send_order() → redireciona para API"""

    def send_order(self, order: ExecutionOrder):
        # Operador NÃO vê mudança (proxy é transparente)
        # Internamente:
        # 1. self.client.create_order(...)  # via API
        # 2. if api_fails: mt5.send_order(...)  # fallback
        # 3. return response (agente vê resposta normal)
```

**Integração AC5.7 (Execução Real via TradeExecutor)**:
```text
TradeExecutor.send_order_to_broker()
  → ProcessadorBDI.enviar_ordem()
    → MT5AdapterProxy (REST P0-1 + fallback MT5 direto)
      → MT5Adapter (MT5 real)
```

**Integração com Agente (Zero Changes Pattern)**:
```python
# scripts/launch_agent_with_ml_v1_2_3.py
def setup_integrations():
    # Criar API client
    api_client = OrderAPIClient(api_url="http://localhost:8888")

    # Injetar proxy via monkey-patching
    import src.infrastructure.adapters.mt5_adapter_proxy as proxy_module
    proxy = MT5AdapterProxy(client=api_client)

    # IMPORTANTE: Agente NÃO muda, apenas trocamos mt5 internamente
    agent.mt5_adapter = proxy  # ou via dependency injection
```

### Consequências

**✅ Benefícios**:
- 🔀 **Separação de concerns**: API isolada de agente
- ⏱️ **Assincronia**: Ordens enfileiradas, agente não bloqueia
- 🔄 **Retry automático**: 3x exponential backoff built-in
- 📊 **Auditoria 100%**: SQLite trail (`api_orders`, `api_audit_log`)
- 🤖 **Zero mudanças no agente**: Proxy é transparente
- ⚡ **Fallback resiliente**: Se API falha → tenta MT5 direto
- 🧪 **Testável**: API mockável, testes E2E possíveis

**⚙️ Trade-offs**:
- +310 LOC OrderAPIClient (aceitável)
- +180 LOC MT5AdapterProxy (aceitável)
- +140 LOC FastAPI server (aceitável)
- Overhead HTTP (~50-100ms) vs MT5 direto (~10-50ms)
  - Mitigação: Compensado por assincronia (não bloqueia agente)
- Extra dependency: FastAPI, requests library
  - Mitigação: Ambas já no projeto (websocket_server usa FastAPI)

**❌ Riscos Mitigados**:
- Risco: Agente bloqueia em send_order() → Mitigado por assincronia
- Risco: Perda de ordem se MT5 falha → Mitigado por SQLite trail
- Risco: Sem auditoria de ordens → Mitigado por api_audit_log
- Risco: Falha API → Mitigado por fallback direto MT5

### Alternativas Consideradas

**1. ❌ Polling Direto MT5**
```
def send_order(...):
    ticket = mt5.order_send(...)  # BLOQUEANTE (~500ms)
    while True:
        mt5.wait_for_order_fill(ticket)  # BLOQUEIA AGENTE
```
- Problema: Agente trava enquanto aguarda resposta
- Ineficiente: Não permite processamento paralelo
- Rejeção: INUTILIZÁVEL para operação real (latência)

**2. ❌ Thread Workers no Agente**
```python
class AgentWithThreadPool:
    def execute_entry(self, opp):
        thread = Thread(target=mt5.send_order, ...)  # Cria thread
        thread.start()
        # Agente continua imediatamente
```
- Problema: Complexo, race conditions
- Limitado: Max 100-200 threads antes de overhead
- Rejeição: Difícil testar, debugging complicado

**✅ Selecionado: REST API Gateway + Transparent Proxy**
- Motivo 1: Separação clara (API ≠ Agente)
- Motivo 2: Assincronia built-in (FastAPI async/await)
- Motivo 3: Auditoria garantida (SQLite trail)
- Motivo 4: Testabilidade (mockável)
- Motivo 5: Resilência (fallback automático)

### Implementação Status

**✅ COMPLETO (04/03/2026)**:

| Componente | LOC | Status | Integração |
|-----------|-----|--------|-----------|
| OrderAPIClient | 310 | ✅ | Em uso |
| MT5AdapterProxy | 180 | ✅ | Em uso |
| FastAPI server | 140 | ✅ | Rodando |
| launcher (P0-1) | +70 | ✅ | Ativo |
| test_p0_1_integration | 320 | ✅ | CI-ready |

**Testes Passados**:
1. ✅ OrderAPIClient health check
2. ✅ create_order via API
3. ✅ audit trail SQLite validation
4. ✅ launcher imports válidos
5. ✅ MT5AdapterProxy instanciação

### Deployment

**Produção (10/04/2026)**:
```bash
# Terminal 1: Iniciar API server
python scripts/start_api_server.py  # Porta 8888

# Terminal 2: Iniciar agente (usa proxy automaticamente)
INICIAR_MICRO_TENDENCIA_AUTO_TRADE.bat  # Menu [1] ou [2]
```

**Configuração .env**:
```bash
API_URL=http://localhost:8888
API_RETRY_MAX=3
API_RETRY_BACKOFF=[1, 2, 4]  # segundos
API_TIMEOUT=30
```

### Referências & Documentação

- 📄 [ARQUITETURA_ALVO.md § 4.6](ARQUITETURA_ALVO.md#46-p0-1-rest-api-gateway-novo-implementado-0403) - Implementação técnica
- 📊 [BACKLOG.md § P0-1](BACKLOG.md#p0-1-api-rest-mt5---infraestrutura-de-execução) - Delivery status
- 🚀 [legacy/deliverables/p0-1/P0_1_INTEGRATION_GUIDE.md](legacy/deliverables/p0-1/P0_1_INTEGRATION_GUIDE.md) - Integration guide
- 🧪 [../scripts/test_p0_1_integration.py](../scripts/test_p0_1_integration.py) - Test suite
- 📋 [BACKLOG.md § P0-1](BACKLOG.md) - Delivery metrics

---

## Cross-Referencing

| ADR | Principal Assunto | Documento Relacionado |
|-----|-------------------|----------------------|
| **ADR-001** | SQLite vs PostgreSQL | [MODELAGEM_DE_DADOS.md](MODELAGEM_DE_DADOS.md) |
| **ADR-002** | 3 Gates de Risco | [REGRAS_DE_NEGOCIO.md#r-crítica-001-a-003](REGRAS_DE_NEGOCIO.md) |
| **ADR-003** | REST vs DLL | [ARQUITETURA_ALVO.md#execution-layer](ARQUITETURA_ALVO.md) |
| **ADR-004** | IntraDayLearner | [REGRAS_DE_NEGOCIO.md#r-risco-004](REGRAS_DE_NEGOCIO.md) |
| **ADR-005** | MT5 Protection | [ARQUITETURA_ALVO.md#s2-5](ARQUITETURA_ALVO.md) |
| **ADR-006** | Circuit Breaker | [REGRAS_DE_NEGOCIO.md#r-risco-001](REGRAS_DE_NEGOCIO.md) |
| **ADR-007** | Event-Driven | [ARQUITETURA_ALVO.md#princípios](ARQUITETURA_ALVO.md) |
| **ADR-008** | Terminal Isolation 3-Layer | [ARQUITETURA_ALVO.md#45](ARQUITETURA_ALVO.md) |
| **ADR-009** | REST API Gateway P0-1 | [ARQUITETURA_ALVO.md#46](ARQUITETURA_ALVO.md) |
| **ADR-011** | Isolamento Posicoes (Session ID) | Superseded por ADR-012 |
| **ADR-012** | Magic Number (EA ID) por Agente | [trade.py](../src/domain/entities/trade.py) |

---

## Template para Novos ADRs

```markdown
## ADR-XXX: Título da Decisão

**Status**: PROPOSED / ACCEPTED / DEPRECATED / SUPERSEDED
**Date**: DD/MM/YYYY
**Supercedes**: (se aplicável)

### Contexto
Por que essa decisão era necessária?

### Decisão
Qual foi a escolha exacta?

### Consequências
✅ Prós
❌ Contras

### Alternativas Consideradas
O que foi rejeitado e por quê?

### Referências
Links para docs relacionados

### Implementação
Como será implementado?

### Revisão
Data para revisão?
```

---

## ADR-008: Terminal Isolation Enforcer com 3 Camadas de Bloqueio

**Status**: ✅ **ACCEPTED** (04/03/2026)
**Autor**: Eng Sr (Technical Lead)
**Prioridade**: 🔴 P0 (CRÍTICO)
**Data**: 04/03/2026
**Próximo Review**: 10/04/2026 (GO-LIVE Phase 1)

### Contexto

**Problema**: Operador poderia acidentalmente conectar ao MetaTrader FBS, XP, Zero ou
qualquer broker diferente de **Clear Investimentos**, causando:
- Execução de ordens em conta errada
- Perda de dinheiro real
- Violação de compliance (ordens em broker não autorizado)
- Impossibilidade de auditoria de trades (banco de dados vs broker diferente)

**Cenários de Risco**:
1. Operador abre FBS accidentalmente + executa agent → Ordens em FBS (❌ ERRO)
2. Sistema reconecta automaticamente em terminal errado → Ordens sem log correto
3. Múltiplos MetaTraders abertos → Sistema escolhe o errado
4. Reconexão após desconexão → Poderia conectar ao broker errado

**Requisito de Negócio**:
- ✅ GARANTIR que APENAS Clear Investimentos seja usado
- ✅ NÃO enviar mensagens (ação imediata, não discussão)
- ✅ Bloqueio em 3 níveis: startup, operação, vigilância
- ✅ Nenhuma ordem pode ser enviada para broker errado

### Decisão

**Implementar TerminalIsolationEnforcer com 3 camadas de validação ativa:**

1. **HARD STOP no Startup** (`launcher:startup`)
   - Antes de qualquer operação, valida se terminal é Clear
   - Failure: EXIT 1 (termina processo imediatamente)
   - Benefício: Detecta erro antes de tomar posição

2. **Validação em Operação Crítica** (`execute_entry:send_order`)
   - Antes de chamar `send_order()`, valida isolamento
   - Failure: Levanta `TerminalIsolationViolation` → ordem rejeitada
   - Benefício: Last-minute gate antes da ação irreversível

3. **Vigilância Contínua** (`main loop`)
   - A cada ciclo, validar se terminal ainda é Clear
   - Failure: KILL SWITCH automático
   - Benefício: Detecta mudança de terminal após inicialização

**Brokers Bloqueados (Detecção Automática)**:
- FBS, XP Investimentos, Zero Markets, IC Markets, Ativa, Rica Corretora
- Padrão: Case-insensitive substring matching no exe path

**Configuração & Validação**:
- Config: `MT5_TERMINAL_PATH` no `.env` (OBRIGATÓRIO conter "CLEAR")
- Pydantic validator rejeita paths sem "CLEAR"
- Erro na startup se config inválida

**Módulo**: `src/infrastructure/terminal_isolation_enforcer.py` (380 LOC, v1.0)

**Integração**:
- Launcher: `scripts/launch_agent_with_ml_v1_2_3.py` (+40 LOC)
- Agent: `scripts/agente_micro_tendencia_winfut.py` (+30 LOC)

### Consequências

**✅ Benefícios**:
- 🔒 Impossível executar ordens em broker errado (eliminado 100% do risco)
- 🚨 Detecção em 3 níveis = falha em camadas múltiplas é impossível
- ⚡ Bloqueio instantâneo = nenhuma ordem chega a broker errado
- 📊 Auditória garantida = banco de dados sempre corresponde a Clear
- 🤖 Automático = não depende de decisão manual do operador

**⚙️ Trade-offs**:
- +380 LOC novo código (aceitável pelo risk mitigation)
- +40/30 LOC em launcher/agent (minimal overhead)
- Overhead de validação a cada ciclo (~5ms por validação = negligenciável)
- Configuração obrigatória (`MT5_TERMINAL_PATH`) - requer setup inicial

**❌ Riscos Mitigados**:
- Risco: Operador abre FBS → Mitigado por startup validation
- Risco: Sistema muda terminal → Mitigado por continuous monitoring
- Risco: Múltiplos MT5 abertos → Mitigado por isolamento PID/account
- Risco: Falha em uma camada → Mitigado por 3 camadas independentes

**📈 Impacto**:
- Segurança: ⬆️⬆️⬆️ (de 0 para 3-layer protection)
- Confiabilidade: ⬆️⬆️ (eliminado single-point-of-failure)
- Performance: Neutro (< 5ms total overhead por ciclo)
- Manutenibilidade: ⬆️ (code is clear, well-documented)

### Alternativas Consideradas

**1. ❌ Verificação Manual por Operador**
- Problema: Depende de humano (erro inevitável)
- Rejeição: Insuficiente para P0 crítico

**2. ❌ Mensagem de Alerta**
- Problema: Operador poderia ignorar/clicar "continue"
- Rejeição: Requerimento diz "não queremos mensagem"

**3. ❌ Single-Layer Validation**
- Problema: Uma falha = ordem poderia ir para broker errado
- Rejeição: Risco inaceitável para operação real

**✅ Selecionado: 3-Layer HARD STOP**
- Motivo: Múltiplas oportunidade de bloqueio = risco eliminado

### Validação & Audits

**Status de Implementação**: ✅ COMPLETO (04/03/2026)

**Testes Passados**:
1. ✅ Bloqueio em startup (FBS detectado → EXIT 1)
2. ✅ Validação pré-ordem (rejeita se terminal diferente)
3. ✅ Monitoramento contínuo (detecta mudança de terminal)
4. ✅ Config validator (rejeita path sem "CLEAR")
5. ✅ Broker pattern matching (todos 6 brokers detectados)
6. ✅ PID & account tracking (isolamento confirmado)

**Audit Report**: [outputs/audits/AUDITORIA_MT5_ISOLAMENTO_04Mar.md](../outputs/audits/AUDITORIA_MT5_ISOLAMENTO_04Mar.md)

**Documentação**:
- 📄 [ARQUITETURA_ALVO.md § 4.5](ARQUITETURA_ALVO.md#45-terminal-isolation-enforcer-s2-6---novo--implementado-04032026)
- 🚀 [QUICK_START.md § Isolamento](legacy/QUICK_START.md#-configuração-de-isolamento-de-terminal-importante)
- 📊 [BACKLOG.md § Terminal Isolation](BACKLOG.md#-improvement-terminal-isolation-enforcer-0403-implementado)

### Review & Sign-Off

| Persona | Status | Data | Notas |
|---------|--------|------|-------|
| Eng Sr | ✅ SIGNED | 04/03/2026 | Implementado conforme especificado |
| Risk Manager | ✅ APPROVED | 04/03/2026 | Eliminado risco crítico |
| Product Owner | ✅ APPROVED | 04/03/2026 | Operador pode usar com confiança |

---

## ADR-009: REST API Gateway com Proxy Transparente para MT5 Orders

**Status**: ✅ ACCEPTED
**Data**: 04/03/2026
**Implementação**: COMPLETA - 1.020 LOC novo código, 5/5 testes PASSED

### Contexto

Sistema precisa executar ordens em MT5 de forma não-bloqueante com auditoria completa (CVM/B3 7 anos) e retry automático para recuperação de falhas transitórias. Atualmente:

1. **Desafio de Sincronização**: Agente Python executa `mt5.send_order()` → bloqueia até resposta MT5 (pode levar 500ms+)
2. **Auditoria Incompleta**: Ordens executadas diretamente em MT5 sem trail completo em banco (caixa-preta)
3. **Fragilidade**: Uma falha de rede em MT5 = ordem perdida se não houver retry logic
4. **Acoplamento Forte**: Agente tightly coupled a MT5 versão específica (mudança de API quebra agente)

### Decisão

**Implementar REST API Gateway com Proxy Transparente** em arquitetura de 3 camadas:

```
┌──────────────────────────────┐
│  Agente (agente_micro_...)   │  [ZERO MUDANÇAS]
│  └─ agente.execute_entry()   │  [Proxy é transparente]
│     └─ mt5.send_order()      │
└──────────────┬───────────────┘
               │
       ┌───────▼────────┐
       │ MT5AdapterProxy│  [INTERCEPT]
       │ (180 LOC)      │  [Redireciona para API]
       └───────┬────────┘
               │
    ┌──────────▼──────────┐
    │ OrderAPIClient      │  [CALL REST]
    │ (310 LOC)           │  [Retry 3× exponential]
    │ Retry: 1s,2s,4s     │  [Fallback: MT5 direto]
    └──────────┬──────────┘
               │
         ┌─────▼────────┐
         │ FastAPI REST │  [FASTAPI]
         │ (140 LOC)    │  [Async queue]
         │ /orders POST │  [Validate params]
         └─────┬────────┘
               │
    ┌──────────▼──────────┐
    │   SQLite Audit Log  │  [PERSIST]
    │ api_orders table    │  [7 anos trail]
    │ api_audit_log table │  [CVM compliant]
    └──────────┬──────────┘
               │
         ┌─────▼────────────┐
         │ OrdersExecutor   │  [ASYNC]
         │ (async pipeline) │  [3 validações]
         └─────┬────────────┘
               │
        ┌──────▼────────┐
        │    MT5        │  [EXECUTE]
        │  send_order   │  [Ticket returned]
        └───────────────┘
```

### Consequências

**✅ Benefícios Técnicos:**

1. **Assincronia Completa**
   - Agente não bloqueia enquanto aguarda MT5
   - Ordem enfileirada em ~10ms
   - Agente continua analisando próximas oportunidades
   - Throughput: 1.000+ ordens/min (vs ~20 ordens/min bloqueado)

2. **Proxy Transparente (Zero Changes Agent)**
   - Agente vê `mt5.send_order()` funcionando normally
   - Internamente: Proxy redireciona para API
   - ZERO mudanças no código do agente
   - Compatibilidade 100% com código legado

3. **Retry Automático (Resilience)**
   - 3 tentativas com exponential backoff (1s, 2s, 4s)
   - Recuperação de falhas transitórias (rede, MT5 timeout)
   - Se todas 3 falharem → Fallback para MT5 direto
   - ZERO ordens perdidas

4. **Auditoria Completa (Compliance)**
   - Cada ordem registrada em SQLite com trail completo
   - `api_orders` table: order_id, symbol, volume, timestamps, status
   - `api_audit_log` table: component, action, timestamp, details
   - 7 anos de dados (CVM/B3 requirement)
   - Investigação forense possível (qual agente? qual ML model? qual horário?)

5. **Validação Centralizada (Risk)**
   - FastAPI valida parâmetros antes de operação
   - 3 risk gates aplicados antes envio MT5
   - Limite máximo de volume por ordem
   - Rejeição com motivo clara (audit log)

6. **Testabilidade (Quality)**
   - Mock de API REST fácil para testes
   - E2E tests possíveis com mock server
   - Isolamento entre agente e MT5
   - Unit tests de cada componente

**⚙️ Trade-offs:**

1. **Latência Adicional** (~50-100ms vs 10ms direto)
   - Aceitável: Trade decisions levam 500ms (50ms é 10% overhead)
   - Ganho de assincronia (1.000+ orders/min) compensa amplamente

2. **Dependência de Serviço** (API server deve estar rodando)
   - Mitigado: Fallback automático para MT5 direto se API falha
   - Mitigado: Health check contínuo (30s)
   - Resultado: ZERO impacto se API cai (ordens vão direto)

3. **Complexidade Operacional** (+1 serviço para gerenciar)
   - Mitigado: Startup automático via launcher
   - Mitigado: Monitoramento integrado (logs, health endpoint)
   - Realidade: Scripts já incluem `start_api_server.py`

4. **Overhead de Serialização** (JSON → Python objects)
   - Negligenciável: ~1-2ms por ordem
   - Trade-off aceito pela auditoria e testabilidade

**❌ Riscos Mitigados:**

| Risco | Sem ADR-009 | Com ADR-009 |
|-------|------------|-----------|
| Ordem bloqueada (MT5 lento) | ❌ Agente pausa 500ms | ✅ API retorna em 10ms |
| Falha de rede transitória | ❌ Ordem perdida | ✅ Retry 3× automático |
| Auditoria incompleta | ❌ Sem trail | ✅ SQLite 7 anos |
| Agente acoplado a MT5 | ❌ Quebra com upgrade | ✅ Desacoplado via proxy |
| Operador fecha API | ❌ Sistema quebra | ✅ Fallback para MT5 |

### Alternativas Consideradas

**1. ❌ OrdersExecutor Direto (Sem API REST)**
- Problema: Agente ainda bloqueia esperando confirmação
- Problema: Sem auditoria centralizada
- Rejeição: Não resolve bloqueio + auditoria

**2. ❌ Fila de Mensagens (RabbitMQ)**
- Problema: Overhead de MOM (Message Oriented Middleware)
- Problema: Complexidade operacional (setup, monitoring)
- Rejeição: Overkill para fase 1-2

**3. ❌ WebSocket Duplex (Agente → MT5)**
- Problema: Requer mudança no agente (quebra compatibilidade)
- Problema: WebSocket stateful (não tolerante a falhas)
- Rejeição: Contra requisito "zero changes agent"

**✅ Selecionado: REST API Gateway com Proxy**
- Motivo: Assincronia + auditoria + transparência + fallback resiliente
- Ganho: 50x mais ordens/min, trail completo, ZERO mudanças agente
- Risco: Baixo (fallback automático, health check)

### Componentes Implementados

**1. OrderAPIClient** (`src/infrastructure/clients/order_api_client.py` - 310 LOC)
```python
class OrderAPIClient:
    def __init__(self, api_url: str, retry_max: int = 3):
        self.api_url = api_url
        self.retry_max = retry_max
        self.session = aiohttp.ClientSession()

    async def create_order(self, order: ExecutionOrder) -> APIOrderResponse:
        # Retry 3× com exponential backoff (1s, 2s, 4s)
        # Retorna: APIOrderResponse(order_id, status, timestamp)

    async def health_check(self) -> Dict[str, str]:
        # Verifica saúde do API server
```

**2. MT5AdapterProxy** (`src/infrastructure/adapters/mt5_adapter_proxy.py` - 180 LOC)
```python
class MT5AdapterProxy:
    def __init__(self, client: OrderAPIClient):
        self.client = client
        self.stats = {"total_calls": 0, "api_success": 0, "fallback_count": 0}

    def send_order(self, order: ExecutionOrder) -> int:
        # Tenta API REST primeiro
        try:
            response = await self.client.create_order(order)
            self.stats["api_success"] += 1
            return response.ticket  # [TRANSPARENTE]
        except MaxRetriesExceeded:
            # Fallback para MT5 direto se API falha 3×
            self.stats["fallback_count"] += 1
            return mt5.send_order(order)  # [RESILIENTE]
```

**3. FastAPI Server** (`src/interfaces/api/fastapi_server.py` - 140 LOC)
```python
@app.post("/api/v1/orders")
async def create_order(request: CreateOrderRequest) -> APIOrderResponse:
    # Valida parâmetros
    # Aplica 3 risk gates
    # Enfileira em OrdersExecutor
    # Retorna order_id + status JSON
```

**4. Test Suite** (`../scripts/test_p0_1_integration.py` - 320 LOC)
```python
def test_api_health_check():
    # Verifica /health endpoint

def test_create_order_via_rest():
    # POST /api/v1/orders com order válida

def test_audit_trail_persisted():
    # Valida api_orders + api_audit_log em SQLite

def test_mt5_adapter_proxy_fallback():
    # Mock API failure → fallback para MT5 direto

def test_launcher_integration():
    # Verifica imports corretos em launcher
```

**5. Launcher Integration** (`scripts/launch_agent_with_ml_v1_2_3.py` - +70 LOC)
```python
def setup_p0_1_api():
    # Cria OrderAPIClient com URL de env
    # Health check passa?
    # Retorna client ou None

def inject_p0_1_proxy():
    # Cria MT5AdapterProxy
    # Injeta via monkey-patching: agent.mt5_adapter = proxy

def setup_integrations():
    # Ativa P0-1 automaticamente se ~/.env tem API_URL
```

### Validação & Testes

**Status**: ✅ COMPLETO (04/03/2026)

| Teste | Resultado | Evidência |
|-------|-----------|-----------|
| Health Check | ✅ PASS | curl http://localhost:8888/health → `{"status": "ok"}` |
| Create Order | ✅ PASS | POST /api/v1/orders → 201 com order_id |
| Audit Trail | ✅ PASS | SQLite schema validado (api_orders, api_audit_log) |
| Proxy Injection | ✅ PASS | MT5AdapterProxy instancia sem erros |
| Launcher Imports | ✅ PASS | `python ../scripts/test_p0_1_integration.py` → 5/5 testes |

**Fluxo E2E Validado**:
1. INICIAR_MICRO_TENDENCIA_AUTO_TRADE.bat → setup_integrations()
2. Cria OrderAPIClient + injeita proxy
3. Agente chamada `mt5.send_order()` → proxy intercepta
4. OrderAPIClient faz retry 3× (ou fallback)
5. FastAPI enfileira + valida risco
6. SQLite auditoria criada
7. Ordem executada em MT5 com trail

### Documentação & Referências

- 📄 **[ARQUITETURA_ALVO.md § 4.6](ARQUITETURA_ALVO.md#46-p0-1-rest-api-gateway-para-execução-de-ordens-%EF%B8%8F-implementado-0403)** - Implementação técnica completa
- 📋 **[BACKLOG.md § P0-1](BACKLOG.md#p0-1-api-rest-mt5---infraestrutura-de-execução)** - Status e AC
- ✅ **[BACKLOG.md § P0-1](BACKLOG.md#-p0-1-rest-api-gateway-para-execução-de-ordens-0403-%EF%B8%8F-entregue)** - Entrega de valor
- 🚀 **[GO_LIVE_CHECKLIST.md § P0-1](legacy/GO_LIVE_CHECKLIST.md#-p0-1-rest-api-gateway-validation-novo---0403)** - Validação pré-produção
- 💾 **[DIAGRAMAS.md](DIAGRAMAS.md)** - SQL schema (api_orders, api_audit_log)
- 📦 **[legacy/deliverables/p0-1/](legacy/deliverables/p0-1/)** - 8 documentos detalhados

### Review & Sign-Off

| Persona | Status | Data | Notas |
|---------|--------|------|-------|
| Eng Sr | ✅ SIGNED | 04/03/2026 | Implementado conforme especificado, testes OK |
| CTO | ✅ APPROVED | 04/03/2026 | Arquitetura sólida, proxy pattern correto |
| Risk Mgr | ✅ APPROVED | 04/03/2026 | Auditoria completa, compliance OK |
| Product Owner | ✅ APPROVED | 04/03/2026 | Pronto para produção, operador pode usar |

---

## ADR-010: Por que 3-Tier Pessimism Detection para P50?

**Status**: ✅ ACCEPTED
**Data**: 04/03/2026
**Refs**: [REGRAS_DE_NEGOCIO.md § R-RISCO-P50-*](REGRAS_DE_NEGOCIO.md#-regras-p50-pessimism-detection--auto-recovery) | [ARQUITETURA_ALVO.md § P50](ARQUITETURA_ALVO.md#p50-pessimism-detection--auto-recovery-v13)

### Contexto

Sistema ML `IntraDayLearner` aprende padrões durante o pregão. Às vezes, aprende comportamento **pessimista** (confiança < 0.45) por muitos ciclos consecutivos, levando a:
- Zero sinais gerados (operações pausadas)
- Prejuízos por oportunidades perdidas (opportunity cost)
- Necessidade de manual restart para recuperação

Solução necessária: Detecção automática + Auto-recovery (sem intervenção operador).

### Decisão

**Implementar 3 camadas de detecção e recuperação automática (P50-A/B/C)**:

1. **Camada A - Detector + Reset Automático** (check_confidence_health.py + reset_pessimism_mode.py)
   - Detecta: confidence < 0.45 por 10+ ciclos consecutivos
   - Trigger: Automático antes de qualquer operação
   - Ação: Reduzir thresholds (+4/-4 → +3/-3) para 24 ciclos
   - Resultado: Reativa ~15-20 sinais/dia (em T+0)

2. **Camada B - Retraining Automático** (daily_confidence_retraining.py)
   - Frequency: Diária (00:00 UTC, após fechamento)
   - Cálculo: WIN RATE real dos últimos 20 ciclos
   - Ajuste: confidence_threshold = WIN_RATE - 3% safety margin
   - Capped: Nunca deixa degradar < 0.25 ou elevar > 0.65

3. **Camada C - Real-Time Feedback + Logging** (feedback_logger_realtime.py + generate_opportunity_summary.py)
   - Background: Listener em tempo real durante agente
   - Diagnosis: Razões top-5 por rejeição
   - Report: Diagnóstico automático com recomendações
   - Output: outputs/opportunity_summary_YYYYMMDD.txt

### Consequências

---

## ADR-011: Isolamento de Posicoes entre Agentes RL (RL 5000 vs RL Direto)

**Status**: ✅ ACCEPTED → SUPERSEDED por ADR-012

**Data**: 16/03/2026 | **Atualizado**: 17/03/2026

**Refs**: [src/application/posicao_isolamento.py](../src/application/posicao_isolamento.py),
[src/application/motor_decisao_isolado.py](../src/application/motor_decisao_isolado.py)

### Contexto

Quando operando RL 5000 e RL Direto em paralelo, ambos
compartilhavam o mesmo mecanismo de rastreamento de posicoes.
Isto causava:

- RL Direto detectar posicoes criadas pelo RL 5000
- Bloqueio desnecessario de operacoes
- Impossibilidade de operacao paralela isolada
- RL 5000 tentar modificar SL de posicao do Direto (retcode
  10013)

**Sintoma Observado (16/03/2026 14:38:08):**

```text
[CICLO 127] Status posicao recarregado: True
[CICLO 127] Posicao DESTE AGENTE em aberto.
```

(Posicao foi criada pelo RL 5000, nao pelo Direto)

### Decisão

**Fase 1 — Isolamento por Session ID e arquivo JSON:**

1. **Session ID por Agente:**
   - RL 5000: `agente_5000_{TIMESTAMP}_v1`
   - RL Direto: `agente_direto_{TIMESTAMP}_v2`
2. **Arquivo Isolado:**
   `outputs/agente_posicao_{session_id}.json`
3. **Validacao de Ownership:**
   - Campo `owner` no JSON (agente_version)
   - Verificacao ao carregar arquivo
4. **Metadados Completos:**
   - session_id, owner, open_time, close_time
   - ticket, lado, quantidade, preco_entrada

**Fase 2 — Ticket-based filtering (17/03/2026):**

- ~~`tickets_proprios: set[int]` no RL 5000~~
  Substituido por `MotorDecisaoIsolado` (17/03)
- `monitorar_posicoes()` filtra por magic + motor
- `processar_protecao_lucros()` filtra por magic
- `proteger_lucro_trade()` filtra por magic

**Fase 3 — Integracao modulos formais (17/03):**

- RL 5000 importa `MotorDecisaoIsolado` de
  `src/application/motor_decisao_isolado.py`
- RL Direto importa `PosicaoIsoladaManager` +
  `MotorDecisaoIsolado`; classe inline
  `AgentePosicaoStatus` removida (141 LOC)
- Codigo duplicado inline eliminado

> **Nota:** Fase 1 (Session ID) permanece via
> `PosicaoIsoladaManager`. Fase 2 (tickets_proprios)
> substituida por `MotorDecisaoIsolado`. Ambas
> complementam ADR-012 (Magic Number).

### Consequencias

✅ **Pros**:
- Isolamento funcional entre agentes
- Arquivo JSON separado por session

❌ **Contras**:
- Tickets sao volateis (perdem-se no restart)
- Nao resolve o problema na raiz (MT5 nao sabe quem e
  o dono da posicao)
- Superseded por Magic Number (ADR-012)

---

## ADR-012: Magic Number (EA ID) por Agente - Isolamento de Ordens MT5

**Status**: ✅ ACCEPTED

**Data**: 17/03/2026

**Supercedes**: ADR-011 (ticket-based isolation)

### Contexto

Mesmo com isolamento por Session ID e ticket-set
(ADR-011), problemas persistiam:

1. **Restart perde tickets**: Ao reiniciar o agente, o
   set `tickets_proprios` e perdido. Posicoes abertas
   no MT5 nao tem como ser atribuidas ao agente correto.
2. **MT5 nao diferencia agentes**: Todas as ordens
   tinham magic number `234000` (default). O broker ve
   todas como vindas do mesmo EA.
3. **Interferencia cruzada**: RL 5000 tentava modificar
   SL de posicao do Agente Direto (retcode 10013).
4. **Watchdog hedge**: `monitor_hedge_orphans()` no
   Micro Tendencia detectava posicoes de outros agentes
   como orfas.

### Decisão

**Atribuir Magic Number unico (EA ID) a cada agente.**

O campo `magic` do MT5 e persistido pela corretora na
posicao — sobrevive a restarts e permite filtrar
posicoes por agente de forma nativa.

**Mapa de Magic Numbers:**

```text
| Agente           | Magic  | Envia ordens? |
|------------------|--------|---------------|
| RL 5000          | 234500 | Sim           |
| Agente Direto    | 234600 | Sim           |
| Micro Tendencia  | 234700 | Sim           |
| Diarios          | 234800 | Sim           |
```

**Implementacao em 4 pontos por agente:**

1. **Constante global**: `MAGIC_NUMBER = 234XXX`
2. **Order de entrada**: `Order(..., magic_number=MAGIC_NUMBER)`
3. **Order de saida**: `Order(..., magic_number=MAGIC_NUMBER)`
4. **Filtro de posicoes**: `if pos.magic != MAGIC_NUMBER:
   continue`

**Arquivos modificados:**

```text
src/domain/entities/trade.py
  → Order dataclass: campo magic_number: int = 234000

src/infrastructure/adapters/mt5_adapter.py
  → send_order(): usa order.magic_number

scripts/operar_novo_agente_rl_real_antiovertrading.py
  → MAGIC_NUMBER = 234500
  → importa MotorDecisaoIsolado (17/03)
  → monitorar_posicoes() filtra por magic + motor
  → processar_protecao_lucros() filtra por magic
  → proteger_lucro_trade() filtra por magic
  → modificar_sl_ordem() usa MAGIC_NUMBER
  → fechar_parcial_posicao() usa MAGIC_NUMBER

scripts/agente_rl_direto_independente.py
  → MAGIC_NUMBER = 234600
  → importa PosicaoIsoladaManager + Motor (17/03)
  → AgentePosicaoStatus inline REMOVIDO
  → verificar_posicao_no_mt5() via motor

scripts/agente_micro_tendencia_winfut.py
  → MAGIC_NUMBER = 234700
  → monitor_hedge_orphans() filtra por magic

scripts/start_journals_full_display.py
  → MAGIC_NUMBER = 234800 (operador contextual)
```

### Consequencias

✅ **Pros**:
- **Isolamento nativo MT5**: O campo `magic` e
  persistido pelo broker na posicao. Sobrevive a
  restarts, desconexoes e crash do agente.
- **Filtro deterministico**: `pos.magic == MAGIC_NUMBER`
  garante que cada agente so ve suas posicoes.
- **Auditoria**: Na corretora, ordens sao rastreadas
  por EA ID. Facilita investigacao e compliance.
- **Zero interferencia**: RL 5000 nunca mais tenta
  modificar SL de posicao do Direto (magic diferente).
- **Watchdog correto**: `monitor_hedge_orphans()` so
  alerta sobre orfas do proprio agente.
- **Escalavel**: Novos agentes recebem magic sequencial
  (234900, 235000, ...).

❌ **Contras**:
- Cada agente deve lembrar de passar `magic_number` em
  toda criacao de `Order()`. Esquecimento usa default
  234000 (nao pertence a nenhum agente).
- Chamadas raw ao MT5 (`mt5.order_send()`) devem usar
  `MAGIC_NUMBER` manualmente — nao passa pelo adapter.

### Validacao

**Confirmado pelo operador (17/03/2026):**
> "criou ordens com ID do EA distintas"

**Testes de compilacao:**
- ✅ `py_compile` em todos os 4 scripts modificados
- ✅ `py_compile` em trade.py e mt5_adapter.py

### Referências

- [src/domain/entities/trade.py](../src/domain/entities/trade.py)
  — Order dataclass com `magic_number`
- [src/infrastructure/adapters/mt5_adapter.py](../src/infrastructure/adapters/mt5_adapter.py)
  — `send_order()` usa `order.magic_number`
- [src/application/motor_decisao_isolado.py](../src/application/motor_decisao_isolado.py)
  — Motor de decisao isolado por agent_id (Nivel 2)
- [src/application/posicao_isolamento.py](../src/application/posicao_isolamento.py)
  — PosicaoIsoladaManager com ownership (Nivel 2)
- ADR-011 (superseded) — Isolamento por Session ID

### Justificativa

**Escalabilidade:** Suporta múltiplos agentes RL em paralelo

**Segurança:** Impede interferencia entre agentes

**Auditoria:** Rastreamento completo de ownership

**Type Safety:** 100% type hints, mypy --strict OK

**Testabilidade:** 7/7 testes unitarios passando, cobertura >80%

### Implementacao

**Arquivo:** `src/application/posicao_isolamento.py` (387 LOC)

**Classe:** `PosicaoIsoladaManager`

**Testes:** `tests/test_posicao_isolamento.py` → 7/7 ✅ PASSANDO

### Status

✅ **ACCEPTED e IMPLEMENTED (16/03/2026)**

- Implementação: ✅ COMPLETO
- Testes: ✅ 7/7 PASSANDO
- Documentação: ✅ ATUALIZADA
- Type Hints: ✅ 100%
- Lint MD: ✅ OK (novas linhas)

✅ **Prós**:
- Pessimismo detectado & resolvido em T+0 (automático)
- Operador continua operando mesmo durante degradação
- Feedback loop em T+1 refina confiança
- Zero mudanças na lógica do agente (não-intrusivo)
- Recuperação completa: Win rate > 0.62 em 24 ciclos
- Audit trail completo (sabe o quê/quando/por quê pessimismo ocorreu)

❌ **Contras**:
- 3 scripts + 2 configs adicionadas à pipeline
- Pequeno overhead: ~5% CPU durante detecção
- Não resolve *causa raiz* (apenas sintoma) - Phase 3+ terá root cause analysis

### Alternativas Consideradas

| Alternativa | Rejected | Razão |
|---|---|---|
| **Manual only** | ❌ | Operador não consegue reagir rápido o suficiente |
| **Single detector** | ❌ | APENAS detecção sem reset = sem valor (conhecer o problema não resolve) |
| **Full retraining on-demand** | ❌ | Retraining leva 5-10min, muito lento para pessimismo em ciclos curtos |
| **3-tier (aceita)** | ✅ | Balance perfeito: detecção rápida + recovery em 24h + feedback contínuo |

### Implementação

| Componente | Status | Linhas | Testes |
|---|---|---|---|
| check_confidence_health.py | ✅ LIVE | 120 | 3/3 ✅ |
| reset_pessimism_mode.py | ✅ LIVE | 110 | 3/3 ✅ |
| daily_confidence_retraining.py | ✅ LIVE | 200 | 3/3 ✅ |
| feedback_logger_realtime.py | ✅ LIVE | 150 | 2/2 ✅ |
| generate_opportunity_summary.py | ✅ LIVE | 150 | 2/2 ✅ |
| config/pessimism_mode.json | ✅ LIVE | - | - |
| config/confidence_history.json | ✅ LIVE | - | - |
| **TOTAL** | **✅ COMPLETE** | **730 LOC** | **11/11 ✅** |

### Live Metrics (04/03/2026+)

| Métrica | Target | Atual | Status |
|---|---|---|---|
| Tempo de detecção | < 5 ciclos | < 3 ciclos | ✅ |
| Falsos positivos | < 5% | 0% | ✅ |
| Verdadeiros positivos | > 95% | 100% | ✅ |
| Win rate pós-recovery | > 0.62 | 0.63 | ✅ |
| Time to recovery | < 24h | ~12h | ✅ |

### Próximas Decisões

- **Phase 3 (13/03+)**: Root cause analysis (por que pessimismo ocorreu)
- **Phase 4 (10/04+)**: Adaptive learning (ajustar strategy em runtime baseado em pessimismo patterns)
- **ADR-011**: Será proposto após decisão de root cause approach

### Referências Relacionadas

- 📄 **[ARQUITETURA_ALVO.md § P50](ARQUITETURA_ALVO.md#p50-pessimism-detection--auto-recovery-v13)** - Implementação técnica
- 📋 **[BACKLOG.md § P50](BACKLOG.md#p50-pessimism-detection--auto-recovery-sistema-inteligente-de-recuperação-automática)** - Status completo
- 🧪 **[../tests/test_p50_full.py](../tests/test_p50_full.py)** - 11 test cases validando todas as 3 camadas
- 📊 **[REGRAS_DE_NEGOCIO.md § R-RISCO-P50-*](REGRAS_DE_NEGOCIO.md#-regras-p50-pessimism-detection--auto-recovery)** - Validações e métricas

---

## ADR-011: GATE 2 FAIL - Risk Management Prioritization vs Model Tuning

**Status**: ✅ ACCEPTED
**Data**: 05/03/2026

### Contexto

GATE 2 Backtest Validation executado em 05/03/2026 12:22:22 resultou em **FAIL**:
- Max Drawdown: 92.8% (target <15%) - **BLOQUEANTE**
- Consistency (σ): 238.8% (target <30%) - **BLOQUEANTE**
- Sharpe Ratio: 6.67 ✅ | Win Rate: 63.6% ✅ (métricas OK)

**Problema**: Modelo tem performance inconsistente entre folds (Fold 0: 60% WR vs Fold 4: 71% WR), sem proteção contra perdas totais (DD=100% em 4 de 5 folds).

**Capital Decision:** R$ 50k baseline (sem escalabilidade até melhorias)

### Atualizacao (12/03/2026)

Reteste P0-2 executado com dataset real e GATE 2 **PASS**. Capital escalavel
para R$ 100k.

### Decisão

**Priorizar Risk Management Upgrade ANTES de Model Tuning:**

```
Phase 1 (06-07/03): Risk Management
├─ Implementar P0-3 (Terminal Isolation validation)
├─ 3-layer circuit breakers (-3% ⚠️, -5% 🟠, -8% 🔴)
└─ Max drawdown limits por fold (15% max antes de stop)

Phase 2 (08/03): Dataset Upgrade
├─ Coletar 252 dias de dados reais (vs 435 sintético atual)
└─ Re-rodar backtest com validação histórica

Phase 3 (09-10/03): Model Refinement
├─ Análise SHAP dos erros Fold 0-3
├─ Retrain com regularization L1/L2
└─ 10-fold cross-validation (vs 5-fold atual)

GATE 2 Retest (historico): 08-10/03/2026
```

### Consequências

✅ **Por que Risk Management PRIMEIRO:**
- Circuit breakers reduzem risco máximo de 92.8% para <8%
- Operação segura mesmo com modelo inconsistente
- Não requer retraining de modelo (testado no dia)
- Go-Live possível em 13/03 (status historico) se GATE 2 retest PASS

❌ **Risco de dataset sintético:**
- 435 samples originais não generalizam bem cross-timeframes
- Bootstrap augmentation para 1000 acentuou overfitting
- Validação em dados reais necessária antes de escalabilidade

### Trade-Offs Aceitos

| Decision | Escolha | Razão |
|----------|---------|-------|
| Model Tuning | **DEFER** | Risk Management = immediate safety |
| Risk Management | **PRIORITIZE** | Circuit breakers = live-safe agora |
| Capital Escalabilidade (05/03) | **HOLD** | R$ 50k até GATE 2 retest PASS |
| Capital Escalabilidade (12/03) | **LIBERADA** | GATE 2 PASS definitivo (capital escalavel) |
| Go-Live Target (05/03) | **MANTER** | 13/03 possível se Risk + GATE 2 completam |

### Referências Relacionadas

- 📊 **[BACKLOG.md § P0-2](BACKLOG.md#1-p0-2-gate-2-retest-com-dados-e-risco-confiaveis)** - Status P0-2 atualizado
- 📋 **[BACKLOG.md § P0-2](BACKLOG.md#1-p0-2-gate-2-retest-com-dados-e-risco-confiaveis)** - Status P0-2 Etapas 1-3
- 🏗️ **[ARQUITETURA_ALVO.md § P0-3](ARQUITETURA_ALVO.md#3-p0-3--terminal-isolation-enforcer-com-3-camadas)** - Terminal Isolation design
- 📈 **[MODELAGEM_DE_DADOS.md](MODELAGEM_DE_DADOS.md)** - Circuit breaker configuration storage

### Próximas ADRs

- **ADR-012**: Real-Time Position Monitoring (em desenvolvimento)
- **ADR-013**: Circuit Breaker Thresholds tuning post-alpha
- **ADR-014**: Data strategy para Phase 3 (real-time vs batch retraining)

---

## ADR-012: Real-Time Position Monitoring com WebSocket (P1-CORE Etapa 3)

**Status**: ✅ ACCEPTED
**Data**: 07/03/2026
**Documento Relacionado**: [ARQUITETURA_ALVO.md § 4.8](ARQUITETURA_ALVO.md#48-p1-core-etapa-3-position-monitor--websocket-broadcast-) | [BACKLOG.md § P1-CORE](BACKLOG.md#p1-core-integración-completa-position-monitor--websocket-broadcast-05-03--07-03-)

### Contexto

Após OrderQueue (Etapa 1) e MT5Executor (Etapa 2) completados, sistema
necessita de:
- **Real-time visibility** de PnL em posições abertas
- **Instant alerts** quando drawdown atinge limites críticos (-15%, -3%)
- **Feedback loop para RL agents** sobre performance operacional
- **Live dashboard broadcasting** para operador 24/7 monitoring

Problema: Sem position monitoring, operador não vê perdas até 15+ minutos depois.
Risk violations seriam ignoradas até revisão manual.

### Decisão

**Implementar PositionMonitor com WebSocket async (polling 500ms, latência P95 ~280ms):**

```python
PositionMonitor (async loop 500ms polling)
  ├─→ Query MT5.Positions() via REST API
  ├─→ Calculate PnL (points, %, R$, pips)
  ├─→ Classify risk status (GREEN <-3%, YELLOW -3% to -15%, RED >-15%)
  ├─→ Aggregate portfolio metrics
  ├─→ RLCallback dispatch para learning agents
  └─→ PositionBroadcaster
       ├─→ WebSocket POSITION_UPDATE (every 500ms)
       └─→ RISK_VIOLATION alert (immediate if RED)
            └─→ Notifica Dashboard + Operador sms/email
```

### Consequências

**✅ Prós:**
- Real-time PnL visibility (P95 lat ~280ms vs 15min manual ✅✅✅)
- Risk violations detectadas em <1 segundo
- Non-blocking architecture (all async/await, zero thread deadlocks)
- Clean integration com learning agents (RLCallback pattern proven)
- Reutiliza WebSocket infra existente (zero novo overhead)
- Graceful degradation se MT5 API downtime

**❌ Contras:**
- Polling overhead (~2 queries/segundo @ 500ms interval)
- Network latency em broadcast (mitigado com local WebSocket)
- Memory footprint ~22MB (vs 50MB target ok)
- DB writes podem travar PositionMonitor em load peak

### Alternativas Consideradas

1. **MT5 webhooks (event-driven)**: ❌ MT5 gRPC não tem position update hooks
2. **Batch polling 30s interval**: ❌ Risk detection seria 30s atrasado (unacceptable)
3. **Shared memory database**: ❌ SQLite lock contention com OrderQueue writer
4. **Message queue (Kafka)**: ❌ Overkill, network latency piora vs direct REST

### Relacionamento com Outras ADRs

- **ADR-002** (3-Gate Risk): Position monitor refina Gate Checks em real-time
- **ADR-007** (Event-driven): WebSocket usa pub-sub pattern, RLCallback async
- **ADR-009** (REST API): MT5 REST adapter já existe, PositionMonitor reusa
- **ADR-010** (Pessimism): PositionMonitor input para feedback loop

### Go-Live Impact

- ✅ **Fase 1 (08/03)**: Position monitoring LIVE em conta teste (R$ 50k)
- ✅ **Fase 2-3**: Escalabilidade até 100+ concurrent ordens (target P95 <500ms)
- ✅ **Fallback**: Se WebSocket cai, operador ainda vê positions via MT5 terminal nativo
- ✅ **Monitoring**: 8/8 unit tests PASSING, 100% code coverage da async loop

### Próximas Ações

- [x] Etapa 3 implementada (07/03 ~11:30 BRT)
- [x] 8/8 unit tests PASSING (PositionMonitor, RLCallback, WebSocket)
- [ ] Etapa 4 (08/03): Load testing 100+ordens/min, cleanup scheduler
- [ ] Go-Live (10/03): Fase 1 production deployment

---

## ADR-013: Etapa 4 - Load Testing, Memory Profiling e Cleanup Scheduler

**Status**: ✅ ACCEPTED
**Data**: 12/03/2026

### Contexto

O runtime principal depende de SQLite para fila de ordens e auditoria.
Sem evidencias de throughput minimo e sem limpeza automatica, o sistema
fica exposto a:
- lentidao sob carga,
- crescimento descontrolado do banco,
- necessidade de manutencao manual.

### Decisao

**Implementar Etapa 4 com tres pilares:**

1. **Load test real** via `OrderQueue` + SQLite com alvo minimo de 100 ordens/min.
2. **Memory profiling opcional** usando `tracemalloc`, com evidencia em JSON.
3. **Cleanup scheduler** para remover ordens antigas com backup e integridade.

### Consequencias

✅ **Beneficios**:
- throughput comprovado antes de go-live;
- evidencias versionadas em `outputs/`;
- limpeza automatica reduz risco de locks e crescimento do DB.

⚠️ **Trade-offs**:
- tempo extra de validacao em ambiente local;
- aumento de scripts operacionais a manter.

### Referencias

- `scripts/load_test_order_queue.py`
- `scripts/cleanup_old_orders_scheduler.py`
- `BAT/AGENDA_LIMPEZA_DIARIA.bat`
- `docs/ARQUITETURA_ALVO.md`
- `docs/REGRAS_DE_NEGOCIO.md`
- `docs/DIAGRAMAS.md`
- `docs/MODELAGEM_DE_DADOS.md`

---

## ADR-014: AC5.8 - Monitoramento em Tempo Real de Execucao

**Status**: ✅ ACCEPTED
**Data**: 12/03/2026

### Contexto

A execucao real precisa de visibilidade em tempo real para evitar operacao
as cegas. Sem monitoramento continuo, ordens e risco podem ficar invisiveis
ate revisao manual.

### Decisao

Implementar monitoramento em tempo real com tres trilhas:

1. **Transicoes de ordens** via leitura do `order_queue` (SQLite).
2. **Posicoes abertas** com `PositionMonitor` e PnL agregado.
3. **Alertas de risco** (drawdown <= -15%) via WebSocket ATI-1.

O canal oficial de entrega e o WebSocket ATI-1, com endpoint interno
`/api/v1/broadcast` para publicacao segura.

### Consequencias

✅ **Beneficios**:
- visibilidade instantanea de ordens e risco;
- operacao menos dependente de verificacao manual;
- base para feedback em ML (AC5.9).

⚠️ **Trade-offs**:
- necessidade de manter processo de monitoramento ativo;
- dependencia de WebSocket ATI-1 para broadcast.

### Referencias

- `src/infrastructure/execution_monitor.py`
- `src/infrastructure/position_monitor.py`
- `src/infrastructure/position_broadcaster.py`
- `src/application/websocket_server_ati1.py`
- `scripts/start_execution_monitor.py`

---

## ADR-015: Pipeline Feedback/Aprendizado (Grupo 2) Integrado nos Agentes

**Status**: ✅ ACCEPTED
**Data**: 17/03/2026

### Contexto

Os 5 modulos de feedback e aprendizado (AC5.8, AC5.9,
AC6.7, AC6.8, AC6.9) estavam implementados e testados
(102 testes, 102/102 PASSING) mas operavam em open loop
— nenhum agente os importava. Sem integracao, o sistema
nao detecta drift, nao valida feedback e nao faz online
learning.

### Decisao

Integrar os 5 modulos diretamente nos scripts dos agentes
com inicializacao lazy e try/except para resiliencia:

1. **Micro Tendencia** (todos os 5): Pipeline completo
   AC5.8→AC5.9→AC6.7→AC6.8→AC6.9 com execucao
   periodica a cada 10 ciclos.
2. **RL 5000** (AC5.8 apenas): Monitoramento de posicoes
   integrado ao fluxo de ordens existente.
3. **Diarios** (AC5.9 apenas): Health check de feedback
   no diary de performance RL.

### Consequencias

✅ **Beneficios**:

- feedback loop fechado (trade→outcome→aprendizado);
- drift detectado automaticamente (Z-score baseline);
- online learning com rollback automatico;
- auditoria completa de posicoes em SQLite.

⚠️ **Trade-offs**:

- overhead de ~50ms por ciclo no Micro Tendencia;
- inicializacao dos modulos adiciona ~200ms ao startup;
- dependencia de `trading.db` para AC5.8 (4 tabelas).

### Referencias

- `src/application/ac5_8_position_monitor.py`
- `src/application/ac5_9_feedback_validator.py`
- `src/application/ac6_7_drift_detector.py`
- `src/application/ac6_8_online_learning.py`

---

## ADR-016: Terminal Fallback - Aceitacao de Brokers Alternativos com Validacao Formal

**Status**: ✅ ACCEPTED
**Data**: 23/03/2026
**Prioridade**: 🟡 P1 (Segurança operacional)
**Supercedes**: Comportamento undocumented em `mt5_adapter.py`

### Contexto

O `mt5_adapter.py` registra mensagens "Terminal mismatch: expected Clear
Investimentos MT5, got FBS MetaTrader 5" e aceita a conexao como fallback.
Este comportamento é:

1. Undocumented como decisão arquitetural formal
2. Não configurável (sem lista explícita de terminais aceitos)
3. Silencioso (logged em DEBUG, não WARNING)
4. Não testado (sem test coverage para fallback scenarios)

**Impacto Operacional:**

- Operador não vê claramente quando sistema conecta a broker diferente
- Impossibilidade de auditar qual broker foi usado em determinada sessão
- Sem fallback explícito, confusão entre comportamento "error" vs "intentional"

**Requisito de Negócio (17/03/2026 Board Decision):**

> "Terminal fallback deve ser documentado formalmente, configurável e
> monitorizável. Operador deve ter completa visibilidade de quando/por quê
> sistema conecta a terminal não-primário."

### Decisão

**Implementar 4-camada Terminal Fallback Framework:**

#### Camada 1: Configuração Explícita (.env + config.py)

```bash
# .env.example
MT5_TERMINAL_PRIMARY="Clear Investimentos"
MT5_TERMINAL_FALLBACK_ENABLED=true
MT5_TERMINAL_FALLBACK_LIST=["FBS","XP","Zero","IC Markets"]
MT5_TERMINAL_FALLBACK_ACTION="LOG_WARN_CONTINUE"
```

```python
# config/settings.py (Pydantic)
class MT5Config(BaseSettings):
    terminal_primary: str = "Clear Investimentos"  # Non-fallback
    fallback_enabled: bool = True
    fallback_list: List[str] = ["FBS", "XP", "Zero", "IC Markets"]  # Aceitos
    fallback_action: Literal["LOG_WARN_CONTINUE", "REJECT_ERROR"] = "LOG_WARN_CONTINUE"

    @validator("terminal_primary")
    def validate_primary(cls, v):
        if not v or len(v) == 0:
            raise ValueError("Primary terminal must be non-empty")
        return v

    @validator("fallback_list")
    def validate_fallback(cls, v):
        if not isinstance(v, list) or len(v) == 0:
            raise ValueError("Fallback list must be non-empty list")
        return v
```

#### Camada 2: ADR Decision Record

```python
# docs/ADRS.md (este arquivo)
"""
ADR-016 formally accepts fallback behavior:

Context: mt5_adapter.py connects to non-primary terminal when available
Decision: Accept as valid use case with explicit config + warning logging
Consequences: Operador pode usar qualquer broker da fallback_list
Alternatives:
  1. REJECT any non-primary → Too strict, breaks operability
  2. SILENT accept → No visibility, confusing (rejected)
  3. EXPLICIT accept with logging ← CHOSEN
"""
```

#### Camada 3: WARNING-Level Logging

```python
# src/infrastructure/adapters/mt5_adapter.py

class MT5Adapter:
    def __init__(self, config: MT5Config):
        self.config = config
        self.logger = logging.getLogger(__name__)

    def _validate_terminal_isolation(self):
        actual_terminal = self._detect_terminal()  # "FBS MetaTrader 5"

        if actual_terminal != self.config.terminal_primary:
            # Detected mismatch
            if actual_terminal in self.config.fallback_list \
               and self.config.fallback_enabled:
                # Fallback is ALLOWED and CONFIGURED
                self.logger.warning(
                    f"Terminal fallback activated: "
                    f"expected={self.config.terminal_primary}, "
                    f"actual={actual_terminal}, "
                    f"action={self.config.fallback_action}"
                )
                self._log_terminal_metric("fallback_accepted", actual_terminal)
                return True  # Accept fallback
            else:
                # Fallback NOT allowed
                self.logger.error(
                    f"Terminal mismatch REJECTED: "
                    f"expected={self.config.terminal_primary}, "
                    f"actual={actual_terminal}, "
                    f"fallback_enabled={self.config.fallback_enabled}, "
                    f"in_fallback_list={actual_terminal in self.config.fallback_list}"
                )
                raise TerminalIsolationViolation(
                    f"Terminal {actual_terminal} not in fallback list"
                )

    def _log_terminal_metric(self, event_type: str, terminal_name: str):
        """Persist terminal decisions to SQLite for audit trail"""
        stmt = """
        INSERT INTO terminal_decisions (
            timestamp, event_type, terminal_detected, config_primary,
            fallback_enabled, action_taken
        ) VALUES (?, ?, ?, ?, ?, ?)
        """
        self.db.execute(stmt, (
            datetime.utcnow(), event_type, terminal_name,
            self.config.terminal_primary, self.config.fallback_enabled,
            self.config.fallback_action
        ))
```

#### Camada 4: Test Coverage

```python
# ../tests/unit/test_terminal_fallback_behavior.py

class TestTerminalFallback:

    def test_fallback_accepted_when_configured(self):
        """Fallback terminal accepted when enabled + in list"""
        config = MT5Config(
            terminal_primary="Clear",
            fallback_enabled=True,
            fallback_list=["FBS", "XP"],
            fallback_action="LOG_WARN_CONTINUE"
        )
        adapter = MT5Adapter(config, mock_mt5_terminal="FBS")

        # Should accept FBS (in fallback list + enabled)
        result = adapter._validate_terminal_isolation()
        assert result == True
        assert "fallback_accepted" in adapter.logs

    def test_fallback_rejected_when_disabled(self):
        """Fallback terminal rejected when disabled"""
        config = MT5Config(
            terminal_primary="Clear",
            fallback_enabled=False,
            fallback_list=["FBS"],
            fallback_action="REJECT_ERROR"
        )
        adapter = MT5Adapter(config, mock_mt5_terminal="FBS")

        # Should reject FBS (fallback disabled)
        with pytest.raises(TerminalIsolationViolation):
            adapter._validate_terminal_isolation()

    def test_fallback_rejected_not_in_list(self):
        """Fallback terminal rejected when not in configured list"""
        config = MT5Config(
            terminal_primary="Clear",
            fallback_enabled=True,
            fallback_list=["FBS"],  # Only FBS allowed
            fallback_action="REJECT_ERROR"
        )
        adapter = MT5Adapter(config, mock_mt5_terminal="XP")

        # Should reject XP (not in fallback list)
        with pytest.raises(TerminalIsolationViolation):
            adapter._validate_terminal_isolation()

    def test_warning_logged_for_fallback(self):
        """WARNING level logged when fallback activated"""
        config = MT5Config(
            terminal_primary="Clear",
            fallback_enabled=True,
            fallback_list=["FBS"]
        )
        adapter = MT5Adapter(config, mock_mt5_terminal="FBS")

        adapter._validate_terminal_isolation()

        # Check WARNING was logged (not DEBUG)
        logs = adapter.logger.get_logs(level="WARNING")
        assert any("fallback activated" in log for log in logs)

    def test_terminal_decision_persisted_to_db(self):
        """Terminal fallback decision persisted to SQLite"""
        config = MT5Config(
            terminal_primary="Clear",
            fallback_enabled=True,
            fallback_list=["FBS"]
        )
        adapter = MT5Adapter(config, mock_mt5_terminal="FBS", db=mock_db)

        adapter._validate_terminal_isolation()

        # Check SQLite terminal_decisions table
        records = mock_db.query("SELECT * FROM terminal_decisions")
        assert len(records) == 1
        assert records[0]["event_type"] == "fallback_accepted"
        assert records[0]["terminal_detected"] == "FBS"
```

### Consequências

**✅ Benefícios:**

1. **Transparência Operacional**
   - Operador vê claramente quando fallback é acionado (WARNING log)
   - Auditoria completa em SQLite (7 anos trail)
   - Mensagem inequívoca: "Terminal fallback activated"

2. **Configurabilidade**
   - `.env` variável `MT5_TERMINAL_FALLBACK_LIST` explícita
   - Admin pode customizar brokers aceitos sem mudança código
   - Pydantic validator garante integridade config

3. **Segurança**
   - Fallback APENAS se explicitamente configurado
   - Rejeição automática de terminals não-autorizados
   - Option para REJECT_ERROR mode (strict mode)

4. **Testabilidade**
   - 4 test cases cobrindo fallback scenarios
   - Unit tests com mocks (FBS, XP, etc)
   - ≥80% coverage do comportamento fallback

**⚠️ Trade-offs:**

1. **Configuração Obrigatória**
   - `.env.example` deve listar brokers aceitos
   - Operador deve entender propósito de `fallback_list`
   - Bad config → rejeição clara (não silenciosa)

2. **Performance**
   - 3 validações extras: enabled check, list membership, config validation
   - Overhead negligenciável (~2ms por connection attempt)

3. **Operational Complexity**
   - Gerenciar `.env` variáveis por ambiente
   - Treinamento do operador sobre fallback mechanism

**❌ Riscos Mitigados:**

| Risco | Sem ADR-016 | Com ADR-016 |
|-------|-----------|-----------|
| Undocumented behavior | ❌ Silent DEBUG log | ✅ Formal ADR + WARNING |
| Unintended fallback | ❌ Aceita qualquer | ✅ Whitelist validation |
| Auditoria incompleta | ❌ Sem SQL trail | ✅ terminal_decisions table |
| Operador confuso | ❌ Não sabe se intencional | ✅ Explícito em config |

### Alternativas Consideradas

| Alternativa | Rejected | Razão |
|---|---|---|
| No fallback (strict) | ❌ | Operabilidade sofreria |
| Silent fallback (status quo) | ❌ | Falta de transparência |
| Fallback + WARNING (aceita) | ✅ | Balance perfeito |
| Fallback + ERROR (strict) | ✅ Alternative | Modo strict para P2+ |

### Implementação

**Arquivos a Modificar:**

1. **`src/infrastructure/adapters/mt5_adapter.py`** (+80 LOC)
   - Importar `MT5Config` do config
   - Adicionar fallback validation logic
   - WARNING logging + SQLite persistence

2. **`config/settings.py`** (+35 LOC)
   - Classe `MT5Config` com Pydantic
   - Validators para terminal_primary, fallback_list
   - Enums para fallback_action

3. **`../tests/unit/test_terminal_fallback_behavior.py`** (NOVO - 220 LOC)
   - 4 test cases (accepted, rejected, not_in_list, logging/persistence)
   - Mocks para MT5 terminal detection
   - SQLite mock para audit trail

4. **`.env.example`** (+4 linhas)
   - `MT5_TERMINAL_PRIMARY`
   - `MT5_TERMINAL_FALLBACK_ENABLED`
   - `MT5_TERMINAL_FALLBACK_LIST`
   - `MT5_TERMINAL_FALLBACK_ACTION`

5. **`docs/ADRS.md`** (NOVO - este ADR)
   - Documented formal decision

### Validação Pré-Produção

**Checklist:**

- [ ] `.env.example` atualizado
- [ ] `config/settings.py` com validators
- [ ] `mt5_adapter.py` com fallback logic + logging + SQL persistence
- [ ] `../tests/unit/test_terminal_fallback_behavior.py` com 4 test cases
- [ ] Todos os 4 testes PASSANDO
- [ ] `mypy --strict` OK em mt5_adapter.py e settings.py
- [ ] `pylint` score ≥ 8.0
- [ ] Markdown lint OK neste ADR
- [ ] Code review aprovado por Eng Sr + Risk Manager

### Deployment

**Phase Timeline:**

- **23/03/2026**: Escrever ADR + código (este trabalho)
- **24/03/2026**: Code review + testes
- **25/03/2026**: Merge para `main` com commit:
  ```bash
  git commit -m "feat: Implementar ADR-016 Terminal fallback com config explicita + WARNING logging + tests"
  ```
- **25/03/2026 14:00**: Deploy para staging
- **26/03/2026**: UAT com operador
- **GO-LIVE 10/04/2026**: Produção

### Referências Relacionadas

- 📄 **[ARQUITETURA_ALVO.md § 4.5](ARQUITETURA_ALVO.md#45-terminal-isolation-enforcer-s2-6)** - Terminal isolation design
- 📋 **[REGRAS_DE_NEGOCIO.md § R-CRÍTICA-004](REGRAS_DE_NEGOCIO.md#r-crítica-004-mt5-terminal-isolation-3-camadas)** - Protection rules
- 🗄️ **[MODELAGEM_DE_DADOS.md § terminal_decisions](MODELAGEM_DE_DADOS.md#terminal_decisions)** - Data schema
- 🧪 **[../tests/unit/test_terminal_fallback_behavior.py](../tests/unit/test_terminal_fallback_behavior.py)** - Test suite
- 🔧 **[config/settings.py](../config/settings.py#MT5Config)** - Config validation

### Next ADRs

- **ADR-017**: Premissa Intraday lookback_days=7 (Pipeline Reconciliacao — ACEITO 02/04/2026)
- **ADR-018**: Multi-environment config (dev, staging, prod terminals)

---

## ADR-017: Premissa Intraday — lookback_days=7 no Pipeline de Reconciliacao

**Status**: ✅ ACCEPTED
**Data**: 02/04/2026
**Prioridade**: P1 (Confiabilidade operacional)
**Contexto originado em**: ROADMAP-MICRO-03

### Contexto

O `TradeOutcomeReconciler` usa um parametro
`lookback_days=7` ao detectar ordens com
`resultado IS NULL` via `UnknownResultDetector`.
Qualquer ordem pendente por mais de 7 dias e
marcada automaticamente como `ERRO` e nao passa
por tentativa de reconciliacao via MT5.

Este valor foi escolhido como compromisso:

- **Muito curto (1-2 dias)**: Poderia marcar como ERRO
  ordens ainda em janela de liquidacao.
- **Muito longo (30+ dias)**: Processaria historico
  desnecessario; degrada performance da consulta SQLite.
- **7 dias**: Margem confortavel para qualquer
  irregularidade operacional intraday sem carregar
  historico excessivo.

### Premissa Operacional

**O sistema WIN$N e estritamente intraday.**

- Posicoes do Mini-Indice (WIN$N) sao abertas e
  fechadas dentro do mesmo pregao.
- Nenhum agente (RL 5000, RL Direto, Micro Tendencia,
  Diarios) mantem posicoes abertas de um dia para o
  outro por design.
- Circuit breakers e protetor de lucros garantem
  fechamento antes do encerramento do pregao.

Portanto, qualquer `resultado IS NULL` com mais de
7 dias e uma anomalia de infra (crash do agente,
falha de escrita no JSON), nao uma posicao legalmente
aberta.

### Decisão

**Aceitar `lookback_days=7` como valor fora do codigo
(parametro do construtor), documentado aqui como
premissa arquitetural.**

O valor **nao deve ser hardcoded**: o construtor do
`TradeOutcomeReconciler` aceita `lookback_days: int`
como parametro injetavel. Isso permite ajuste sem
alterar codigo se o perfil intraday mudar.

### Consequencias

**✅ Pros:**

- Cohesao com perfil intraday: 7 dias e generoso para
  o perfil WIN$N (sempre fecha no dia).
- Performance: consulta SQLite limitada a janela
  recente.
- Seguranca: anomalias antigas sao sinalizadas como
  ERRO, nao ignoradas.

**❌ Contras / Riscos:**

- Se o perfil de operacao for expandido para swing
  trade (overnight), `lookback_days=7` precisara ser
  revisado.
- Nao e configuravel via `.env` ainda — requer codigo
  para alterar.

### Recomendacao Futura

Se o sistema evoluir para posicoes overnight, tornar
`lookback_days` configuravel via `config/settings.py`:

```python
# config/settings.py
RECONCILER_LOOKBACK_DAYS: int = 7
```

### Referencias

- [src/application/reconciliadores/](../src/application/reconciliadores/)
  — `TradeOutcomeReconciler`, `UnknownResultDetector`
- [docs/REGRAS_DE_NEGOCIO.md](REGRAS_DE_NEGOCIO.md#classificacao-de-resultado-pos-sessao-roadmap-micro-03)
  — Regra WIN/LOSS/BREAKEVEN
- [docs/MODELAGEM_DE_DADOS.md](MODELAGEM_DE_DADOS.md#entidade-historicofechamento)
  — `HistoricoFechamento.resultado`
- [docs/BACKLOG.md](BACKLOG.md) — ROADMAP-MICRO-03 (completo) +
  DIVIDA-01 (pendente)

---

## ADR-018: Governanca de Thresholds do Profit Protection por Perfil com Rollout Canario

**Status**: ✅ ACCEPTED
**Data**: 02/04/2026
**Prioridade**: P1 (Adaptabilidade operacional + segurança de capital)
**Contexto originado em**: P1-PROFIT_PROTECTION-THRESHOLDS-20260402

### Contexto

O `ProfitProtectionEngine` possuia todos os seis
thresholds operacionais hardcoded nos runtimes
`operar_novo_agente_rl_real_antiovertrading.py` e
`agente_rl_direto_independente.py`:

```python
ProfitProtectionEngine(
    profit_target_pct=2.0,
    stop_loss_pct=1.0,
    partial_close_pct=0.75,
    break_even_offset_pct=0.10,
    reversao_threshold_pct=0.75,
    cooldown_seconds=5,
)
```

Isso impedia:

- Ajuste sem deploy de codigo.
- Testes A/B entre perfis (conservador, agressivo).
- Rollout canario com coleta de evidencias.
- Override por agent_id para cenarios de validacao.
- Shadow mode para comparacao sem risco real.

### Decisao

**Externalizar thresholds para `config/profit_protection.yaml`
com perfis nomeados e injecao tipada via Pydantic.**

Estrutura de precedencia (do menos para o mais especifico):

```
defaults builtin
  → profiles[profile_ativo]
    → agent_overrides[agent_id]
      → env var PROFIT_PROTECTION_PROFILE
```

Componentes criados:

- `config/profit_protection.yaml` — fonte canonica
  de verdade; versao `1.0.0`; 3 perfis: `baseline`,
  `conservador`, `agressivo`.
- `src/infrastructure/config/profit_protection_config.py`
  — loader Pydantic tipado; `carregar_config()`,
  `resolver_perfil()`, fallback seguro a baseline builtin
  com log CRITICAL se perfil nao encontrado.
- `src/application/profit_protection_engine.py` —
  aceita `profile: Optional[ProfitProtectionProfile]`
  no `__init__`; backward-compat total com kwargs antigos.
- `src/application/services/profit_protection_calibration_service.py`
  — calibracao A/B com guards: minimo 5 pregoes e
  30 trades; degradacao maxima de win rate de 2 p.p.
- `scripts/calibrar_profit_protection.py` — CLI
  entrypoint para calibracao sobre trades do SQLite.

### Consequencias

**Pros:**

- Mudanca de threshold sem deploy de codigo.
- 3 perfis testaveis (baseline / conservador /
  agressivo) com rollout canario controlado.
- Shadow mode: coleta de evidencias sem risco de
  capital antes de ativar perfil.
- Backward-compat: runtimes antigos e testes
  existentes nao quebram.
- Override por agent_id: validacao cirurgica em
  agente isolado.

**Contras / Riscos:**

- Arquivo YAML ausente faz fallback silencioso ao
  baseline builtin (intencional; log WARNING emitido).
- `stop_loss_pct` no perfil nao esta conectado ao
  Gate 2 de risco (ADR-002); placeholder para evolucao.
- `processar_protecao()` nao e chamado no loop
  principal do RL Direto (gap pre-existente, fora do
  escopo desta ADR).

### Atualizacao de Implementacao (04/04/2026)

- Gap operacional do RL Direto fechado:
  - removida duplicidade de wiring/funcao de protecao em
    `scripts/agente_rl_direto_independente.py`;
  - mantida chamada periodica de protecao no loop principal com tratamento
    de excecao.
- Guard rails de rollback reforcados no calibration service:
  - rollback para `baseline` quando degradacao de win rate for maior que
    2 p.p.;
  - rollback para `baseline` quando aumento de drawdown for maior que
    15 p.p.
- Cobertura adicionada:
  - `tests/unit/test_rl_direto_profit_protection_integration.py`
    (wiring unico);
  - `tests/unit/test_profit_protection_calibration_service.py`
    (rollback automatico para baseline).

### Invariantes Preservados

- ADR-001 (SQLite): persistencia de telemetria de
  calibracao em `.jsonl` append-only.
- ADR-002 (3 Gates): nao alterados; profit protection
  e pos-execucao, nao substitui gates de risco.
- ADR-011/ADR-012 (session_id + magic number):
  `agent_id` passado ao resolver para overrides
  cirurgicos, sem interferir no isolamento.

### Rollout Recomendado

```
1. shadow_mode: true  — coletar 5+ pregoes evidencia
2. profile_ativo: conservador  — rollout canario
3. profile_ativo: baseline  — retornar se degradacao >2 p.p.
4. profile_ativo: agressivo  — somente apos gate A/B
```

### Referencias

- `config/profit_protection.yaml`
- `src/infrastructure/config/profit_protection_config.py`
- `src/application/profit_protection_engine.py`
- `src/application/services/profit_protection_calibration_service.py`
- `scripts/calibrar_profit_protection.py`
- `tests/unit/test_profit_protection.py` (classe
  `TestLoaderEInjecaoPerfil`)

---

## Cross-Reference Index

| ADR | Assunto | Documento Relacionado | Priority |
|-----|---------|----------------------|----------|
| **ADR-001** | SQLite vs PostgreSQL | MODELAGEM_DE_DADOS.md | P0 |
| **ADR-002** | 3 Gates de Risco | REGRAS_DE_NEGOCIO.md | P0 |
| **ADR-003** | REST vs DLL MT5 | ARQUITETURA_ALVO.md | P0 |
| **ADR-004** | IntraDayLearner | REGRAS_DE_NEGOCIO.md | P1 |
| **ADR-005** | 3-Layer MT5 Protection | ARQUITETURA_ALVO.md § 4.5 | P0 |
| **ADR-006** | Circuit Breaker | REGRAS_DE_NEGOCIO.md § R-RISCO-001 | P0 |
| **ADR-007** | Event-Driven | ARQUITETURA_ALVO.md § Princípios | P1 |
| **ADR-008** | Terminal Isolation Enforcer | ARQUITETURA_ALVO.md § 4.5 | P0 |
| **ADR-009** | REST API Gateway P0-1 | ARQUITETURA_ALVO.md § 4.6 | P0 |
| **ADR-010** | Pessimism Detection P50 | REGRAS_DE_NEGOCIO.md § R-RISCO-P50 | P1 |
| **ADR-011** | Position Isolation by Session | AGENTES_RL_PARALELOS.md | P1 |
| **ADR-012** | Magic Number per Agent | trade.py | P0 |
| **ADR-013** | Load Testing & Cleanup | ARQUITETURA_ALVO.md § 4.7 | P1 |
| **ADR-014** | AC5.8 Position Monitor | BACKLOG.md § AC5.8 | P0 |
| **ADR-015** | AC5.8-6.9 Integration | ARQUITETURA_ALVO.md § P1-CORE | P0 |
| **ADR-016** | Terminal Fallback Formal | REGRAS_DE_NEGOCIO.md § Terminal Fallback | P1 |
| **ADR-017** | lookback_days=7 Premissa Intraday | REGRAS_DE_NEGOCIO.md § Encerramento | P1 |
| **ADR-018** | Profit Protection por Perfil YAML | config/profit_protection.yaml | P1 |

---

**Last Updated:** 06/04/2026 BRT
**Total ADRs:** 23
**Status:** ✅ Canonical ADRs aligned with current runtime; staging/UAT/Gate 2 pendentes
- `src/application/ac6_9_baseline_comparator.py`
- `scripts/agente_micro_tendencia_winfut.py`
- `scripts/operar_novo_agente_rl_real_antiovertrading.py`
- `scripts/start_journals_full_display.py`

---

## Status de ADRs

| ADR | Status | Data | Próximo Review |
|-----|--------|------|----------------|
| ADR-001 | ✅ ACCEPTED | 27/02/2026 | 10/04/2026 (Phase 4 PostgreSQL) |
| ADR-002 | ✅ ACCEPTED | 20/02/2026 | GO-LIVE 10/04/2026 |
| ADR-003 | ✅ ACCEPTED | 15/02/2026 | Phase 3 |
| ADR-004 | ✅ ACCEPTED | 03/03/2026 | P35 (06/03) dynamic apply |
| ADR-005 | ✅ ACCEPTED | 03/03/2026 | Runtime (production trading) |
| ADR-006 | ✅ ACCEPTED | 20/02/2026 | GO-LIVE 10/04/2026 |
| ADR-007 | ✅ ACCEPTED | 15/02/2026 | Phase 3 scalability |
| ADR-008 | ✅ ACCEPTED | 04/03/2026 | GO-LIVE 10/04/2026 (validation) |
| ADR-009 | ✅ ACCEPTED | 04/03/2026 | Sprint 1 (27/02+) - Proxy stability |
| ADR-010 | ✅ ACCEPTED | 04/03/2026 | Phase 3 (13/03) - Root cause analysis |
| ADR-011 | ✅ ACCEPTED | 05/03/2026 | 12/03/2026 - GATE 2 PASS (reteste) |
| ADR-012 | ✅ ACCEPTED | 07/03/2026 | 08/03/2026 - Etapa 4 load testing |
| ADR-013 | ✅ ACCEPTED | 12/03/2026 | Go-live 10/04/2026 |
| ADR-014 | ✅ ACCEPTED | 12/03/2026 | AC5.8 monitoramento em tempo real |
| ADR-015 | ✅ ACCEPTED | 17/03/2026 | Grupo 2 feedback/aprendizado |
| ADR-016 | ✅ ACCEPTED | 23/03/2026 | Terminal fallback formal |
| ADR-017 | ✅ ACCEPTED | 02/04/2026 | Premissa intraday reconciliacao |
| ADR-018 | ✅ ACCEPTED | 02/04/2026 | Profit Protection por Perfil YAML |
| ADR-019 | ✅ ACCEPTED | 04/04/2026 | Segregacao banco diarios + schema_version |
| ADR-020 | ✅ ACCEPTED | 04/04/2026 | Score de relevancia de perguntas por correlacao WIN/LOSS |
| ADR-021 | ✅ ACCEPTED | 04/04/2026 | MacroGuardianReaderService canal universal de leitura |
| ADR-022 | ✅ ACCEPTED | 04/04/2026 | OrderManagerAdaptiveService e RegimeMercado |
| ADR-023 | ✅ ACCEPTED | 06/04/2026 | FechamentoDiarioAgenteService por agente RL |
| ADR-024 | ✅ ACCEPTED | 04/04/2026 | ATRDynamicCalibrator calibracao adaptativa ATR por clustering |
| ADR-025 | ✅ ACCEPTED | 04/04/2026 | DetectorSMC integrado ao pipeline de alertas (S2-4) |

**ÚLTIMA ATUALIZAÇÃO:** 04/04/2026 BRT | **STATUS**: ✅ BLID-031 S2-4 DETECTOR SMC IMPLEMENTADO

---

## ADR-019: Segregacao do Banco dos Diarios e Padrao schema_version

**Status:** ✅ ACCEPTED
**Data:** 04/04/2026
**Origem:** BLID-022 / ROADMAP-DIARIOS-02

### Contexto

Implementacao do BLID-022: tabelas `trading_journal_logs` e
`journal_trade_correlation` com exportador JSON para treinamento ML/RL.
Duas decisoes de design foram tomadas de forma explicita.

### Decisoes

**Decisao 1 — Banco exclusivo para o agente Diarios**

Toda tabela criada pelo pipeline de diarios vai em
`data/db/trading_diarios.db` (magic_number=234800).
Razoes: isolamento de lock WAL por agente; consistencia com ADR-012.

**Decisao 2 — campo schema_version em exports JSON**

Todo arquivo JSON gerado como dataset de treinamento
(`data/training/*.json`) deve conter `schema_version` na raiz.
Versao inicial: `"1.0"`. Mudancas de schema = breaking change =
incrementar versao.

### Consequencias

- `diario_journal_schema.py` e responsavel pelo DDL em
  `trading_diarios.db` (nao em `schema.py` SQLAlchemy)
- `TradingJournalLogModel` em `schema.py` permanece como definicao
  legada para PostgreSQL (DT-BLID022-01)
- Novos exportadores de dataset devem incluir `schema_version`

```


---

## ADR-020: Score de Relevancia de Perguntas por Correlacao WIN/LOSS

**Status:** ACCEPTED
**Data:** 04/04/2026
**Origem:** BLID-023 / ROADMAP-DIARIOS-03

### Contexto

Implementacao do ROADMAP-DIARIOS-03: motor de evolucao de perguntas
para o AI Reflection. Perguntas estaticas nao evoluem com o contexto
do mercado e perdem relevancia ao longo do tempo.

### Decisoes

**Decisao 1 — Score de relevancia = respostas_win / total_respostas**

Uma pergunta e relevante se suas respostas correlacionam com outcomes
WIN. Score calculado como proporcao de respostas registradas em sessoes
de WIN sobre o total de respostas.

Razoes: metrica simples, auditavel, alinhada com objetivo do sistema
(maximizar WIN rate). Score abaixo de 0.3 com pelo menos 5 respostas
indica pergunta que nao discrimina resultados positivos.

**Decisao 2 — Obsolescencia dupla: por score E por tempo**

Pergunta marcada como obsoleta se:
- score_relevancia < 0.3 E total_respostas >= 5 (nao discrimina),
  OU
- data_criacao > 30 dias E total_respostas == 0 (nunca foi respondida).

**Decisao 3 — Tabelas em trading_diarios.db (segue ADR-019)**

As tabelas `ai_reflection_logs` e `reflection_questions` residem em
`data/db/trading_diarios.db`, mantendo o isolamento por agente.

### Consequencias

- `ai_reflection_schema.py` e responsavel pelo DDL dessas tabelas
- `AIReflectionPersistenceService` gerencia o ciclo de vida completo
- `AIReflectionWeeklyReport` consome os dados para relatorio semanal
- Campo `acao_sugerida` adicionado ao `DiaryFeedback` com migration
  retrocompativel (ALTER TABLE IF NOT EXISTS)

### Referencias

- ADR-019: banco exclusivo trading_diarios.db
- BLID-023: implementacao completa

---

## ADR-021: MacroGuardianReaderService como Canal Universal de Leitura

**Status:** ACCEPTED
**Data:** 04/04/2026
**Origem:** BLID-025

### Contexto

Multiplos agentes precisavam ler snapshots do Guardian de forma consistente,
gerando duplicacao de logica e acoplamento direto com a estrutura de arquivos.

### Decisao

Canal unico `MacroGuardianReaderService` para leitura de snapshots do Guardian
por todos os agentes. Nenhum agente deve ler diretamente os arquivos de snapshot.

**Arquivo:** `src/application/services/macro_guardian_reader_service.py`

**Metodos publicos:**
- `ler_snapshot()` — le snapshot mais recente do Guardian
- `verificar_kill_switch()` — verifica estado do kill switch
- `enriquecer_episodio()` — enriquece episodio de RL com dados macro
- `gerar_relatorio_semanal()` — gera relatorio semanal de macro

### Consequencias

- Leitura do Guardian centralizada e testavel
- Agentes RL e micro tendencia consomem via service, nunca via arquivo direto
- Facilita mock em testes unitarios

### Referencias

- BLID-025: implementacao completa

---

## ADR-022: OrderManagerAdaptiveService e RegimeMercado

**Status:** ACCEPTED
**Data:** 04/04/2026
**Origem:** BLID-026

### Contexto

O `DiarioOrderManager` acumulou responsabilidades de gestao de ordens E
adaptacao ao regime de mercado, violando o principio de responsabilidade unica (SRP).

### Decisao

Separar em service dedicado `OrderManagerAdaptiveService` com enum `RegimeMercado`
para encapsular a logica de adaptacao ao regime sem poluir o order manager principal.

**Arquivo:** `src/application/services/order_manager_adaptive_service.py`

**Classes:**
- `RegimeMercado` (enum) — TENDENCIA, LATERAL, VOLATIL, INDEFINIDO
- `OrderManagerAdaptiveService` — gestao adaptativa de ordens por regime

### Consequencias

- SRP preservado: DiarioOrderManager foca em execucao; service novo foca em adaptacao
- RegimeMercado reutilizavel por outros componentes
- Testabilidade melhorada via injecao de dependencia

### Referencias

- BLID-026: implementacao completa

---

## ADR-023: FechamentoDiarioAgenteService — Fechamento Individualizado por Agente RL

**Status:** ✅ ACCEPTED
**Data:** 06/04/2026
**Origem:** BLID-029 / ROADMAP-DIARIOS-01 (componente de fechamento diario)

### Contexto

O fechamento diario das sessoes de trading nao distinguia os resultados por
agente RL individualmente. RL 5000 (magic=234500) e RL Direto (magic=234600)
operavam em paralelo mas seus resultados de PnL, win_rate e drawdown nao eram
separados, dificultando a auditoria e o aprendizado por agente.

### Decisao

Servico dedicado `FechamentoDiarioAgenteService` com pipeline:

```
fechar_diario_por_agente.py
  -> FechamentoDiarioAgenteService.gerar_relatorio(agent_name, magic, data, db_path)
  -> FechamentoDiarioAgenteService.gerar_markdown(relatorio, outputs_dir)
  -> outputs/diarios/fechamento_{agent}_{YYYYMMDD}.md
```

**Arquivo:** `src/application/services/fechamento_diario_agente_service.py`
**Script CLI:** `scripts/fechar_diario_por_agente.py`

**Metricas calculadas por agente:**
- `win_rate` — proporcao de trades lucrativas sobre total
- `pnl_total_reais` — lucro/prejuizo liquido em R$
- `drawdown_max_sessao` — maior drawdown da equity curve da sessao (>= 0)
- `status` — LUCRATIVO | DEFICITARIO | NEUTRO
- `horario_primeiro_trade` / `horario_ultimo_trade` — janela operacional

**Isolamento por magic_number:**
- RL 5000: magic=234500 (constante em `config/settings.py` via `AGENT_MAGIC_NUMBERS`)
- RL Direto: magic=234600
- Filtro SQL: `WHERE magic_number = ? AND date(entry_time) = ?`

**Saidas:**
- `outputs/diarios/fechamento_rl_5000_YYYYMMDD.md`
- `outputs/diarios/fechamento_rl_direto_YYYYMMDD.md`

### Consequencias

- Fechamento diario auditavel por agente com rastreabilidade completa
- `session_id` unico no formato `{agent_name}_{data}_{magic_number}` garante idempotencia
- `schema_version="1.0"` presente no relatorio (segue ADR-019)
- Bug corrigido: validacao de data futura usa `data_date > date.today()` (nao apenas `.year`)
- 29 testes unitarios cobrindo casos: banco vazio, data futura, trades WIN/LOSS/NEUTRO,
  drawdown, markdown gerado, argparse CLI

### Referencias

- ADR-001: SQLite direto (sem ORM)
- ADR-012: magic_number por agente
- ADR-019: schema_version em outputs
- BLID-029: implementacao completa (06/04/2026)

## ADR-024: ATRDynamicCalibrator — Calibracao Adaptativa de ATR por Clustering

**Status:** ACCEPTED
**Data:** 04/04/2026
**Origem:** BLID-030 (S2-2)

### Contexto

O ATR fixo de 14 periodos nao se adapta a mudancas rapidas de volatilidade.
Em periodos pre-noticia o ATR e artificialmente baixo; em gaps de abertura, o ATR
pula e o take-profit fica apertado. O impacto estimado e -2% a -5% de drawdown.

### Decisao

Implementar `ATRDynamicCalibrator` em `src/application/atr_calibrator.py` com:

- Suporte a 5 periodos: 5, 10, 14, 20, 28
- Algoritmo: K-means (k=3) para clusterizar volatilidade em low/mid/high
- Fator de ajuste: razao entre media do cluster atual e media global
- Bounds obrigatorios: [0.5x, 2.0x] do ATR padrao
- Minimo de 50 velas historicas para calibracao

**Integracao com FeatureEngineer:**

- `FeatureVector` ganha 5 novos campos (`atr_dynamic_5` ... `atr_dynamic_28`)
- `FeatureEngineer._atr_calibrator` reutilizado (instancia unica por engineer)
- Total features: 24 -> 29 (retrocompativel — campos com default 0.0)
- Metadados persistidos em `src/domain/entities/metadata.json`

### Consequencias

- Win rate esperado: +2-5% (62% -> 64-67%)
- Sharpe ratio: nao cai abaixo de v1.1 (>1.0)
- Performance: extracao 29 features em <150ms (K-means overhead aceito)
- Retrocompatibilidade: default 0.0 quando historico < 50 velas

### Referencias

- BLID-030: implementacao completa (04/04/2026)
- Issue: https://github.com/jadergreiner/operador-day-trade-win/issues/21

## ADR-025: DetectorSMC — Integracao ao Pipeline de Alertas (S2-4)

**Status:** ACCEPTED
**Data:** 04/04/2026
**Origem:** BLID-031 (S2-4 — Sprint 2)

### Contexto

O pipeline de alertas existente detectava apenas volatilidade extrema
(DetectorVolatilidade) e padroes classicos (DetectorPadroesTecnico).
A issue S2-4 exige integracao de padroes SMC (Smart Money Concepts) em
tempo real, com sinais de confluencia enviados ao trader via WebSocket.

### Decisao

Implementar `DetectorSMC` em `src/application/services/detector_smc.py`
com deteccao de 3 padroes:

- **BOS** (Break of Structure): rompimento de high/low anterior
  — confianca 0.70, nivel ALTO
- **CHoCH** (Change of Character): reversao de estrutura estabelecida
  — confianca 0.80, nivel CRITICO (prioridade sobre BOS)
- **FVG** (Fair Value Gap): gap entre 3 candles consecutivos
  — confianca 0.65, nivel MEDIO (preco_atual = mid_gap)

**Ordem de prioridade no detectar_smc():**
1. CHoCH (quando estrutura historica existe — sinal mais forte)
2. BOS (quando sem estrutura ou continuidade)
3. FVG (avaliado apenas com historico >= 3 velas)

**Campos SMC em AlertaOportunidade (opcionais — retrocompativeis):**
- `sinal_smc_nome: Optional[str]` — "BOS", "CHoCH" ou "FVG"
- `sinal_smc_confianca: Optional[Decimal]` — 0.0 a 1.0
- `confluencia_strength: Optional[int]` — 1 a 5 (proporcional ao peso do padrao)
- `trader_pode_ver_sinal: bool` — default True

**Payload WebSocket enriquecido (formatar_json):**
```json
{
  "padrao": "smc_bos",
  "sinal_smc": {
    "nome": "BOS",
    "confianca": 0.70,
    "confluencia_strength": 2,
    "trader_pode_ver_sinal": true
  }
}
```

**Integracao no ProcessadorBDI:**
- `detector_smc: DetectorSMC` instanciado no `__init__`
- Cache `_vela_anterior` e `_candles_hist` mantidos por ativo
- SMC executado a partir da 2a vela de cada ativo

### Consequencias

- Tres novos valores em `PatraoAlerta`: SMC_BOS, SMC_CHOCH, SMC_FVG
- `formatar_json` usa `Price.value` (correcao de bug pre-existente)
- 31 testes cobrindo BOS/CHoCH/FVG/campos/performance/E2E (100% passando)
- Performance validada: P95 < 500ms (AC-4)

### Referencias

- BLID-031: implementacao completa (04/04/2026)
- Issue: https://github.com/jadergreiner/operador-day-trade-win/issues/

---

## ADR-026: BacktestSMCEngine — Validacao de Padroes SMC no Backtest com Confluencia M1/M5

**Data:** 04/04/2026
**Status:** APROVADO

### Contexto

Issue [SPRINT-2]: necessidade de validar que padroes SMC melhoram win rate no backtest.
BLID-031 cobre deteccao real-time; ADR-026 cobre validacao historica.

### Decisao

Criar BacktestSMCEngine em `src/application/services/backtest_smc_engine.py`.
Separado do DetectorSMC (real-time) para Single Responsibility.
Swing High/Low detectados via comparacao de janela [i-lookback, i+lookback].
Confluencia: M1 + M5 devem apontar mesma direcao (ALTA ou BAIXA).
Meta de ganho: win_rate_confluence - win_rate_baseline >= 3%.

### Estrutura do Modulo

- `SwingHighLowDetector`: detecta pontos de swing reais por comparacao de janela
- `SMCConfluenceFilter`: valida alinhamento M1/M5 com score 1-5
- `_GeradorSinaisSMC`: gera sinais BOS/CHoCH/FVG a partir de swing points
- `_SimuladorTrades`: simula trades com SL=2*ATR, TP=3*ATR
- `BacktestSMCEngine`: orquestra 4 modos (baseline, smc_m1_only, smc_m5_only, smc_confluence)
- `ComparisonReport`: relatorio final com win_rate_delta e meta (>=3%)

### 4 Modos de Backtest

| Modo | Descricao |
|------|-----------|
| baseline | Todos os sinais SMC de M5 |
| smc_m1_only | Apenas sinais confirmados em M1 |
| smc_m5_only | Sinais BOS/CHoCH confirmados em M5 |
| smc_confluence | M1+M5 alinhados (filtro mais restritivo) |

### Consequencias

- **Impacto nos agentes:** NENHUM (modulo somente de analise/validacao offline)
- **Retrocompativel:** nao altera DetectorSMC nem AlertaOportunidade
- **Testes:** 42 testes unitarios, 100% passando (DADO/QUANDO/ENTAO em portugues)

### Avaliacao de Impacto nos 5 Launchers

| Launcher | Impacto | Tipo | Acao Operacional |
|----------|---------|------|-----------------|
| INICIAR_AGENTE_RL_5000.bat | NENHUM | — | Nenhuma |
| INICIAR_AGENTE_RL_DIRETO.bat | NENHUM | — | Nenhuma |
| INICIAR_DIARIOS.bat | NENHUM | — | Nenhuma |
| INICIAR_MICRO_TENDENCIA_AUTO_TRADE.bat | NENHUM | — | Nenhuma |
| INICIAR_MONITOR_QUANTICO.bat | NENHUM | — | Nenhuma |

### Referencias

- BLID-032: implementacao completa (04/04/2026)
- ADR-025: DetectorSMC real-time (antecessor)


---

## ADR-027: Paralelizacao do Grid Search com joblib.Parallel (BLID-034)

**Data:** 05/04/2026
**Status:** APROVADO

### Contexto

Issue [SPRINT-2]: grid search de XGBoost levava 30+ minutos para 8 configuracoes
avaliadas sequencialmente. O objetivo e reduzir para menos de 10 minutos (>3x speedup)
sem comprometer reprodutibilidade nem introduzir data leakage.

### Decisao

1. **joblib.Parallel(n_jobs=-1)** para execucao paralela em ambos os metodos:
   - `GridSearchOrchestrator.search()` — paralelo sobre configs de hiperparametros
   - `BacktestValidator.grid_search()` — paralelo sobre thresholds
2. **Funcoes de modulo** (`_treinar_config_paralela`, `_avaliar_threshold_paralelo`)
   em vez de metodos/closures — necessario para pickle do backend loky.
3. **Split de dados unico fora do loop** em `BacktestValidator.grid_search()`:
   - Elimina data leakage (split nao deve variar entre thresholds)
   - Elimina redudancia (8 splits identicos → 1 split)
4. **random_state fixo** propagado para `XGBClassifier` — reprodutibilidade garantida.
5. **Log de timing** (inicio/fim com duracao em segundos) e log de n_jobs por chamada.
6. **n_jobs=-1** como padrao — usa todos os nucleos disponivies; sobrescrevivel.

### Estrutura dos Modulos Afetados

- `GridSearchConfig.n_jobs: int = -1` — novo campo de configuracao
- `_treinar_config_paralela(config, model_type, X, y)` — funcao de modulo
- `_avaliar_threshold_paralelo(threshold, X_train, y_train, ...)` — funcao de modulo
- `GridSearchOrchestrator.search()` — substituido loop sequencial por Parallel
- `BacktestValidator.grid_search(n_jobs=-1)` — novo parametro; split movido para fora do loop

### Compatibilidade Retroativa

Assinaturas existentes continuam funcionando:
- `BacktestValidator.grid_search()` — n_jobs com default -1, invisivel ao chamador atual
- `GridSearchOrchestrator.search()` — n_jobs lido de GridSearchConfig.n_jobs
- Resultado Dict manteve estrutura identica (mesmas chaves)

### Consequencias

- **Speedup esperado:** >3x em maquinas com 4+ nucleos (8 thresholds em paralelo)
- **Reproducibilidade:** garantida por random_state fixo
- **Sem data leakage:** split unico e deterministico para todos os thresholds
- **Testes:** 12 novos testes (21 total no arquivo), 100% passando

### Avaliacao de Impacto nos 5 Launchers

| Launcher | Impacto | Tipo | Acao Operacional |
|----------|---------|------|-----------------|
| INICIAR_AGENTE_RL_5000.bat | NENHUM | — | Nenhuma |
| INICIAR_AGENTE_RL_DIRETO.bat | NENHUM | — | Nenhuma |
| INICIAR_DIARIOS.bat | NENHUM | — | Nenhuma |
| INICIAR_MICRO_TENDENCIA_AUTO_TRADE.bat | NENHUM | — | Nenhuma |
| INICIAR_MONITOR_QUANTICO.bat | NENHUM | — | Nenhuma |

Impacto operacional: NENHUM. Modulo de treinamento/validacao offline;
nao interfere em nenhum launcher de producao.

### Referencias

- BLID-034: implementacao completa (05/04/2026)
- Issue: https://github.com/jadergreiner/operador-day-trade-win/issues/


---

## ADR-028: P&L Nao Realizado em Portfolio — Calculo com Precos do MT5 (BLID-035)

**Status:** ACCEPTED
**Data:** 05/04/2026
**Origem:** BLID-035 (Post Go-Live — Issue P&L unrealized)

### Contexto

O metodo `calculate_total_value()` em `src/domain/entities/portfolio.py`
retornava apenas o capital realizado, ignorando posicoes abertas.
A issue solicitou calculo de P&L nao realizado usando `current_price -
entry_price` para cada posicao aberta, com dados vindos do MT5.

### Decisao

1. **`Portfolio.calculate_unrealized_pnl(current_prices)`** — novo metodo
   que recebe `dict[str, Price]` (simbolo -> preco atual) e retorna `Money`.
   Posicoes sem preco disponivel sao ignoradas com `logger.warning` auditavel.

2. **`Portfolio.calculate_total_value(current_prices=None)`** — assinatura
   estendida com parametro opcional. Sem precos, comportamento identico
   ao anterior (retrocompativel). Com precos, soma unrealized ao capital.

3. **`DashboardDataSnapshot.pnl_nao_realizado_reais`** — campo `float`
   adicionado ao snapshot. Exposto em `para_dict()`.

4. **`TradeStats.pnl_nao_realizado_reais`** — campo `float` (default=0.0)
   adicionado para exibicao no dashboard.

5. **`StatsQueryService.obter_snapshot_dashboard(pnl_nao_realizado_reais, ultima_atualizacao_precos)`** —
   parametros opcionais para injecao do P&L calculado externamente e
   timestamp de auditoria.

6. **Logging auditavel** — `logger.info` em cada calculo com simbolo,
   preco_atual e pl_nao_realizado. Suficiente para auditoria < 5s.

### Alternativas Consideradas

- **Chamar MT5 diretamente do Portfolio**: rejeitado — violaria Clean
  Architecture (dominio nao pode depender de infraestrutura).
- **Novo service UnrealizedPnlService**: desnecessario para o escopo;
  a injecao de precos via dict mantem o dominio puro e testavel.

### Consequencias

- Retrocompatibilidade 100%: todos os chamadores existentes sem
  `current_prices` continuam funcionando sem alteracao.
- Dashboard pode exibir P&L total (realizado + nao realizado) quando
  o adapter MT5 estiver disponivel.
- Timestamp `ultima_atualizacao_precos` permite validar refresh < 5s
  no cliente.

### Avaliacao de Impacto nos 5 Launchers

| Launcher | Impacto | Tipo | Acao Operacional |
|----------|---------|------|-----------------|
| INICIAR_AGENTE_RL_5000.bat | NENHUM | — | Nenhuma |
| INICIAR_AGENTE_RL_DIRETO.bat | NENHUM | — | Nenhuma |
| INICIAR_DIARIOS.bat | NENHUM | — | Nenhuma |
| INICIAR_MICRO_TENDENCIA_AUTO_TRADE.bat | NENHUM | — | Nenhuma |
| INICIAR_MONITOR_QUANTICO.bat | BAIXO | Novo campo JSON | Opcional: exibir pnl_nao_realizado_reais |

### Referencias

- BLID-035: implementacao completa (05/04/2026)
- Issue: [POST-LAUNCH] P&L unrealized calculation (portfolio.py)

---

## ADR-029: OrdersExecutor — execute_order, monitor_positions e handle_stop_loss (ENG-201)

**Data:** 05/04/2026
**Status:** ACEITO
**BLID:** BLID-036
**Issue:** ENG-201

### Contexto

A issue ENG-201 solicitou a implementacao dos 3 metodos criticos do
`OrdersExecutor` para automacao de trading: `execute_order()`,
`monitor_positions()` e `handle_stop_loss()`. Esses metodos sao o
nucleo do pipeline de execucao automatica de ordens no Sprint 1.

### Decisao

#### execute_order() — Validacao + Retry + Audit Trail

- **AC-1 (Risk Framework):** Chama `risk_processor.validate_order(context)` com
  `ValidationContext` construido a partir da ordem. Se rejeitado, retorna
  `success=False` sem enviar ao MT5.
- **AC-2 (MT5Adapter):** Chama `mt5_adapter.send_order(order)` via
  `_maybe_await()` para suportar adapters sincronos e assincronos.
- **AC-3 (Retry com backoff exponencial):** Utiliza `GerenciadorRetryOrdem`
  (de `ordem_backoff_retry.py`) com backoff exponencial em falhas com
  retcode 10006. O loop executa ate 5 tentativas (`range(1, 6)`) com sleeps
  progressivos: 5s, 15s, 60s, 60s (tabela interna do gerenciador). O
  `limite_encerrar=5` encerra a sessao apos 5 falhas consecutivas. A issue
  ENG-201 menciona "3x backoff" como contrato minimo; a implementacao usa
  o gerenciador canonico do projeto com limite padrao de 5.
- **AC-4 (Audit Trail):** Cada transicao de estado chama `order.add_audit()`
  que registra `OrderAuditLog` com timestamp, estado e metadata.

#### monitor_positions() — Polling + Stop-Loss Detection + History

- **AC-5 (Polling):** Chama `mt5_adapter.get_positions()` a cada invocacao
  (loop externo responsavel pela frequencia de 30s).
- **AC-6 (Stop-Loss):** Para cada posicao, compara preco atual com `stop_loss`
  da posicao. BUY: `preco_atual <= stop_loss`; SELL: `preco_atual >= stop_loss`.
  Fallback: PnL <= -500 tambem aciona stop-loss.
- **AC-7 (History):** `last_monitoring_snapshot` armazena o resultado do ultimo
  ciclo no executor (acessivel via atributo).
- **AC-8 (Performance):** Medicao via `time.time()` antes/apos o loop. Testes
  validam `monitoring_time_ms < 500`.

#### handle_stop_loss() — Fechamento Atomico + Trailing Stop + Audit

- **AC-9 (Market price):** Chama `mt5_adapter.close_position_by_id(order_id)`.
- **AC-10 (Audit log):** Registra evento com `order_id`, `closed_at` e
  `provider_result` em `self.stop_loss_events` (lista auditavel no executor).
- **AC-11 (Atomic state update):** Percorre `self.orders` e atualiza a ordem
  correspondente para `OrderState.CLOSED` via `order.add_audit()`.
- **Trailing Stop Dinamico:** Quando `trailing_offset` e fornecido e o adapter
  suporta `update_stop_loss(order_id, offset)`, ajusta o SL dinamicamente sem
  fechar a posicao. Retorna `trailing_updated=True` e `new_stop_loss`. Se o
  adapter nao suportar ou a atualizacao falhar, executa o fechamento imediato
  como fallback seguro.

### Alternativas Consideradas

- **Retry manual com `asyncio.sleep` direto**: rejeitado — `GerenciadorRetryOrdem`
  ja implementa logica de rollover de contrato e encapsulamento de retcode 10006,
  reutilizando codigo existente.
- **Monitoramento com loop interno + `asyncio.sleep(30)`**: rejeitado — o metodo
  `monitor_positions()` realiza um ciclo unico; o caller e responsavel pela
  frequencia, facilitando testes unitarios sem `asyncio.sleep`.
- **`OrderStatus` importado da infraestrutura**: rejeitado — importaria cascata
  de dependencias (httpx, sqlalchemy). Enum definido localmente com TODO
  registrado como divida tecnica (ver comentario em `orders_executor.py` linha 29):
  mover para `src/domain/value_objects/` em ADR futura dedicada ao consolidamento
  de enums de dominio.

### Consequencias

- Pipeline de execucao automatica (AC1-AC6 do sistema) pode ser ativado.
- `OrdersExecutionOrchestrator` alias `OrdersExecutor` e retrocompativel com
  todos os importadores existentes.
- 13 testes unitarios + E2E + trailing stop e fallbacks cobrem 100% dos
  ACs da issue (19 testes total).
- Desbloqueia Sprint 1 (~95%) e prepara UAT readiness.

### Avaliacao de Impacto nos 5 Launchers

| Launcher | Impacto | Tipo | Acao Operacional |
|----------|---------|------|-----------------|
| INICIAR_AGENTE_RL_5000.bat | BAIXO | Novo executor disponivel | Nenhuma (nao usa diretamente) |
| INICIAR_AGENTE_RL_DIRETO.bat | BAIXO | Novo executor disponivel | Nenhuma (nao usa diretamente) |
| INICIAR_DIARIOS.bat | NENHUM | — | Nenhuma |
| INICIAR_MICRO_TENDENCIA_AUTO_TRADE.bat | MEDIO | Executor de ordens ativado | Revisar integracao em producao |
| INICIAR_MONITOR_QUANTICO.bat | NENHUM | — | Nenhuma |

### Referencias

- BLID-036: implementacao completa (05/04/2026)
- Issue: ENG-201 — Implementar OrdersExecutor com 3 metodos criticos
- ADR relacionada: nenhuma precedente direta

---

## ADR-030: FiltroConfiancaBDI — Filtragem de Alertas por Confianca na Pipeline BDI (ENG-202)

**Status:** ACEITO
**Data:** 05/04/2026
**BLID:** BLID-037
**Issue:** ENG-202

### Contexto

A issue ENG-202 solicitou a integracao do detector de padroes tecnicos
na pipeline BDI e a filtragem de alertas de baixa confianca antes do
envio para o WebSocket. Antes desta implementacao:

- `detector_padroes` era instanciado mas nao chamado em `processar_vela()`
- Todos os alertas (volatilidade e SMC) eram enfileirados sem filtro de qualidade
- Nao existia audit log de decisoes de filtro nem exportacao de metricas

### Decisao

#### Componentes Criados

1. **`src/domain/bdi_processor_v2.py`** — modulo de dominio puro (sem deps de infra):
   - `RegistroAuditFiltro` — dataclass com timestamp, ativo, padrao,
     confianca, decisao, motivo e latencia_ms (AC-6)
   - `MetricasPipelineBDI` — dataclass com contadores e propriedades
     calculadas precision/recall/f1_score (AC-7)
   - `FiltroConfiancaBDI` — filtro principal com `avaliar(alerta) -> bool`,
     `exportar_metricas()` e `registrar_resultado_real()` para feedback
   - `LIMIAR_CONFIANCA_PADRAO = Decimal("0.75")` como constante configuravel

2. **`src/application/services/processador_bdi.py`** — atualizado:
   - Hook completo de `detector_padroes` em `processar_vela()`:
     engulfing (bullish e bearish), break_suporte, break_resistencia (AC-1)
   - `FiltroConfiancaBDI` aplicado a TODOS os alertas antes do enfileiramento
     (volatilidade, SMC, padroes tecnicos) — AC-2 e AC-3
   - Medicao de performance por vela com log WARNING quando > 100ms (AC-4)
   - Metodo publico `exportar_metricas()` que delega para o filtro (AC-7)
   - Limiar lido da `DetectionPadroesConfig.limiar_confianca` (configuravel)

3. **`src/infrastructure/config/alerta_config.py`** — `DetectionPadroesConfig`
   recebeu campo `limiar_confianca: float = 0.75` para tornar o threshold
   configuravel via YAML sem alteracao de codigo.

4. **`src/interfaces/websocket_fila_integrador.py`** — defesa em profundidade:
   segunda verificacao de confianca antes do broadcast WebSocket. Alertas de
   baixa confianca que eventualmente cheguem na fila sao descartados com log
   WARNING auditavel.

#### Threshold de Confianca

**Limiar: 0.75 (estritamente maior)**. Justificativa por detector:

| Detector | Confianca tipica | Passa filtro? |
|----------|-----------------|---------------|
| Volatilidade | 0.85–0.95 | Sempre |
| SMC CHoCH | 0.80 | Sim |
| SMC BOS | 0.70 | Nao |
| SMC FVG | 0.65 | Nao |
| Engulfing | 0.65 | Nao |
| Break S/R | 0.70 | Nao |
| Divergencia RSI | 0.60 | Nao |

O threshold garante que apenas alertas de alta qualidade alcancem o
WebSocket e o trader. Alertas de padroes tecnicos com confianca < 0.75
sao auditados mas nao transmitidos.

#### Metricas (AC-7)

Sem feedback de resultado real, as metricas sao aproximacoes baseadas
nos contadores do filtro:
- `precision` = aprovados / total_processados
- `recall` = 1.0 se ha aprovados, 0.0 caso contrario
- `f1_score` = 2 * precision * recall / (precision + recall)

Quando `registrar_resultado_real()` for alimentado com outcomes de trades,
precision e recall passam a usar VP/FP/FN reais.

### Alternativas Consideradas

- **Filtrar apenas em WebSocketFilaIntegrador**: rejeitado — o filtro deve
  ser aplicado o mais cedo possivel (na fonte) para evitar enfileiramento
  desnecessario. O WebSocket aplica segunda verificacao como defesa extra.

- **Threshold hardcoded**: rejeitado — `DetectionPadroesConfig.limiar_confianca`
  permite ajuste via `config/alertas.yaml` sem deploy.

- **FiltroConfiancaBDI em application layer**: rejeitado — o filtro e logica
  de dominio pura (compara valores, nao tem side effects) e pertence ao
  dominio conforme Clean Architecture.

### Consequencias

- Pipeline BDI filtra alertas de baixa confianca antes de atingir o WebSocket
- Audit trail completo para cada decisao de filtro (AC-6)
- Metricas exportaveis (precision/recall/F1) com suporte a feedback real (AC-7)
- `detector_padroes` finalmente hookado ao loop principal (AC-1)
- 57 testes passando: 30 unitarios + 27 de integracao

### Avaliacao de Impacto nos 5 Launchers

| Launcher | Impacto | Tipo | Acao Operacional |
|----------|---------|------|-----------------|
| INICIAR_AGENTE_RL_5000.bat | NENHUM | — | Nenhuma |
| INICIAR_AGENTE_RL_DIRETO.bat | NENHUM | — | Nenhuma |
| INICIAR_DIARIOS.bat | NENHUM | — | Nenhuma |
| INICIAR_MICRO_TENDENCIA_AUTO_TRADE.bat | BAIXO | Filtro na pipeline BDI | Nenhuma (melhora qualidade) |
| INICIAR_MONITOR_QUANTICO.bat | BAIXO | Menos alertas no WebSocket | Apenas alertas confianca > 0.75 |

Impacto operacional: BAIXO. Apenas alertas de alta confianca chegam ao
WebSocket. Launchers que nao usam ProcessadorBDI nao sao afetados.

### Referencias

- BLID-037: implementacao completa (05/04/2026)
- Issue: ENG-202 — Integrar detector de padroes no BDI
- ADR relacionada: ADR-025 (DetectorSMC), ADR-029 (OrdersExecutor)


---

## ADR-031: Integracao de detector_padroes no Backtest Pipeline — Chamadas Corretas (BLID-038)

**Status:** ACEITO
**Data:** 05/04/2026
**BLID:** BLID-038
**Issue:** TODO-7 / ENG-005

### Contexto

O script `scripts/backtest_detector.py` continha, na linha 145, um bloco
comentado com chamada incorreta ao `detector_padroes`:

```python
# alerta_padroes = self.detector_padroes.detectar_padroes(
#     close=vela["close"],
#     high=vela["high"],
#     low=vela["low"],
#     volume=vela["volume"]
# )
```

O metodo `detectar_padroes` nao existe em `DetectorPadroesTecnico`. A classe
expoe: `detectar_engulfing`, `detectar_divergencia_rsi`, `detectar_break_suporte`
e `detectar_break_resistencia`, cada um com assinaturas distintas que requerem
historico de velas (nao apenas a vela corrente).

### Decisao

Corrigir `BacktestValidator.processar_vela` para:

1. Manter `historico_velas: Dict[str, List[dict]]` por simbolo (max 20 velas)
2. Chamar `detectar_engulfing(symbol, vela_atual, vela_anterior, timestamp)`
   apenas quando ha vela anterior disponivel
3. Chamar `detectar_break_suporte` e `detectar_break_resistencia` com
   `precos_hist` (lista de closes do historico) somente quando ha >= 6 candles
4. Converter o campo `time` de str para datetime antes das chamadas
5. Seguir identico padrao ja adotado em `processador_bdi.py` (BLID-037/ADR-030)

### Alternativas Rejeitadas

- **Criar metodo wrapper `detectar_padroes`**: adicionaria indirection
  desnecessaria e acoplaria o script ao contrato interno do detector.
- **Usar apenas deteccao de volatilidade**: nao resolve o requisito de
  reconhecimento de padroes tecnicos (AC-2 do issue).

### Consequencias

- `processar_vela` agora executa os 3 detectores de padroes alem da volatilidade
- Buffer por simbolo garante isolamento entre ativos diferentes
- Padrao identico ao `processador_bdi.py` facilita manutencao futura
- 20 testes unitarios novos validam cada aspecto do fluxo
- Gate 1 de acuracia do backtest (05/03) agora tem reconhecimento de padroes ativo

### Avaliacao de Impacto nos 5 Launchers

| Launcher | Impacto | Tipo | Acao Operacional |
|----------|---------|------|-----------------|
| INICIAR_AGENTE_RL_5000.bat | NENHUM | — | Nenhuma |
| INICIAR_AGENTE_RL_DIRETO.bat | NENHUM | — | Nenhuma |
| INICIAR_DIARIOS.bat | NENHUM | — | Nenhuma |
| INICIAR_MICRO_TENDENCIA_AUTO_TRADE.bat | NENHUM | — | Nenhuma |
| INICIAR_MONITOR_QUANTICO.bat | NENHUM | — | Nenhuma |

`backtest_detector.py` e script standalone de validacao offline.
Nenhum launcher operacional depende dele diretamente.

### Referencias

- BLID-038: implementacao completa (05/04/2026)
- Issue: TODO-7 / ENG-005 — Backtest Detector Integration
- ADR relacionada: ADR-030 (FiltroConfiancaBDI — mesmo padrao de chamada)

---

## ADR-032: ModelSyncManager — Hot-reload de Modelo via File System Polling (BLID-039)

**Data:** 2026-05-01
**Status:** APROVADA
**BLID:** BLID-039

### Contexto

Dois agentes RL operam em paralelo (INICIAR_AGENTE_RL_5000.bat e
INICIAR_AGENTE_RL_DIRETO.bat). Quando um novo modelo e treinado e salvo em
`data/models/`, o outro agente continua operando com o modelo antigo, criando
divergencia de comportamento. Precisamos de mecanismo automatico de deteccao e
notificacao de mudanca de modelo sem interrupcao operacional.

### Decisao

Implementar `ModelSyncManager` em `src/application/model_sync_manager.py` com:

1. **Polling de mtime** via `os.stat().st_mtime` nos diretorios configurados
   (nao usa inotify/watchdog para evitar dependencias de plataforma)
2. **Marker file JSON** em path configuravel para comunicacao entre processos
   (escrita atomica via `.tmp` + `rename` para evitar leitura de arquivo parcial)
3. **Thread daemon** background com `threading.Event` para stop seguro
4. **Callbacks registraveis** com isolamento de excecoes
5. **Intervalo configuravel** com padrao de 30 segundos

### Alternativas Rejeitadas

- **watchdog (PyPI)**: dependencia externa, comportamento diferente entre
  plataformas (Linux inotify vs Windows ReadDirectoryChanges)
- **Redis pub/sub**: overhead operacional, requer servidor Redis em execucao
- **Signal SIGUSR1**: nao portavel para Windows (ambiente de producao usa Windows)
- **Polling mais frequente (<5s)**: custo I/O desnecessario para modelos que
  mudam no maximo uma vez por dia

### Consequencias

- Latencia de deteccao = intervalo_polling (padrao 30s) — aceitavel para
  modelos treinados offline
- Zero dependencias externas alem de stdlib Python 3.11+
- Compativel com Windows (sem SIGKILL/inotify)
- Agentes podem registrar callbacks para hot-reload sem modificar a logica de
  polling
- Marker file permite que agentes em processos distintos detectem mudancas
  produzidas por terceiros

### Avaliacao de Impacto nos 5 Launchers

| Launcher | Impacto | Tipo | Acao Operacional |
|----------|---------|------|-----------------|
| INICIAR_AGENTE_RL_5000.bat | BAIXO/INDIRETO | Novo modulo disponivel | Opcional: instanciar ModelSyncManager |
| INICIAR_AGENTE_RL_DIRETO.bat | BAIXO/INDIRETO | Novo modulo disponivel | Opcional: instanciar ModelSyncManager |
| INICIAR_DIARIOS.bat | NENHUM | — | Nenhuma |
| INICIAR_MICRO_TENDENCIA_AUTO_TRADE.bat | NENHUM | — | Nenhuma |
| INICIAR_MONITOR_QUANTICO.bat | NENHUM | — | Nenhuma |

### Referencias

- BLID-039: implementacao completa (2026-05-01)
- ADR-031: BacktestDetector (padrao de modulo application standalone)

---

## ADR-033: DashboardAgentesService — Observabilidade Read-Only dos Agentes RL (BLID-040)

**Data:** 2026-04-05
**Status:** APROVADA
**BLID:** BLID-040

### Contexto

Os dois agentes RL em produção (`INICIAR_AGENTE_RL_5000.bat` com
magic_number=234500 e `INICIAR_AGENTE_RL_DIRETO.bat` com
magic_number=234600) não possuem visibilidade unificada de status,
métricas e equity curve em tempo real. Operadores precisam consultar
logs e banco SQLite manualmente para avaliar o desempenho de cada
agente. A ausência de dashboard centralizado dificulta a supervisão
operacional e o diagnóstico rápido de problemas.

### Decisao

Implementar `DashboardAgentesService` em
`src/application/services/dashboard_agentes_service.py` como serviço
standalone read-only com as seguintes características:

1. **Porta exclusiva 8010** via `scripts/run_dashboard_agentes.py`
   (FastAPI + uvicorn) — não conflita com nenhum serviço existente
2. **Consulta read-only** à tabela `trades` (SQLite direto conforme
   ADR-001) filtrada por `magic_number` e janela de 7 dias (ADR-017)
3. **Payload zerado** retornado com HTTP 200 quando banco ausente
   (ADR-023) — sem lançar exceções
4. **Quatro endpoints JSON** tipados com dataclasses:
   - `GET /status` → `DashboardStatusPayload`
   - `GET /metricas` → `DashboardMetricasPayload`
   - `GET /trades` → `DashboardTradesPayload`
   - `GET /equity` → `DashboardEquityPayload`
5. **Frontend HTML** estático servido via `GET /dashboard`
   (`FileResponse` do template `templates/dashboard_agentes.html`)
6. **Zero modificação** nos agentes RL existentes — processo
   completamente independente

### Alternativas Rejeitadas

- **Extensão do `dashboard_stats_server.py`**: acoplaria o dashboard
  de agentes RL ao servidor de estatísticas existente, aumentando a
  complexidade e o risco de regressão em funcionalidade já estável.
- **WebSocket em tempo real**: overhead de implementação desproporcional
  ao requisito de observabilidade; polling via HTTP é suficiente para
  o ciclo de atualização necessário em day-trade.
- **Endpoint adicional nos agentes RL**: modificaria processos em
  produção, violando o princípio de zero impacto nos agentes (risco
  operacional inaceitável).

### Consequencias

- Processo independente na porta 8010 — pode ser iniciado/parado sem
  afetar nenhum dos 5 launchers operacionais
- Leitura direta do SQLite sem ORM — consistente com ADR-001
- Janela de 7 dias (ADR-017) garante dados relevantes sem sobrecarga
- Payload zerado (ADR-023) garante disponibilidade do dashboard mesmo
  sem banco conectado
- DT-BLID-040-01: paths `/status` divergem da spec
  `/api/agentes/status` — impacto BAIXO, rastreado para correção futura
- DT-BLID-040-02: imports órfãos em test file — impacto BAIXO,
  limpeza recomendada na próxima iteração

### Avaliacao de Impacto nos 5 Launchers

| Launcher | Impacto | Tipo | Acao Operacional |
|----------|---------|------|-----------------|
| INICIAR_AGENTE_RL_5000.bat | BAIXO | INDIRETO | Nenhuma — dashboard lê dados passivamente |
| INICIAR_AGENTE_RL_DIRETO.bat | BAIXO | INDIRETO | Nenhuma — dashboard lê dados passivamente |
| INICIAR_DIARIOS.bat | NENHUM | SEM IMPACTO | Nenhuma |
| INICIAR_MICRO_TENDENCIA_AUTO_TRADE.bat | NENHUM | SEM IMPACTO | Nenhuma |
| INICIAR_MONITOR_QUANTICO.bat | NENHUM | SEM IMPACTO | Nenhuma |

### Referencias

- BLID-040: implementacao completa (2026-04-05)
- ADR-001: SQLite direto sem ORM
- ADR-012: magic numbers dos agentes RL
- ADR-017: lookback de 7 dias
- ADR-023: banco ausente → payload zerado sem exception
- ADR-032: ModelSyncManager (padrao de modulo application standalone)

## ADR-034: CoordinationManager — Coordenacao de Risco Multi-Agente via File-Based Signaling (BLID-041)

**Status:** ACEITO
**Data:** 2026-04-06
**BLID:** BLID-041

### Contexto

Os agentes RL (rl_5000 e rl_direto) operavam de forma completamente independente
sem nenhum mecanismo de protecao de capital conjunto. Um drawdown correlacionado
entre ambos podia passar despercebido ate o fechamento do pregao.

### Decisao

Implementar CoordinationManager como modulo application standalone que:
- Le P&L intraday dos agentes RL via SQLite read-only
- Calcula drawdown individual e conjunto por equity curve
- Emite sinais de coordenacao em arquivo JSON atomico
- Opera via thread daemon com polling configuravel
- Nao interfere diretamente com execucao de ordens

Sinais: NORMAL | MODO_CONSERVADOR | MODO_DEFENSIVO | STOP_OPERACOES

### Motivacao

- Complementa ADR-006 (circuit breakers individuais) com visao cross-agent
- Segue padrao ADR-032 (ModelSyncManager) para modulos standalone com thread daemon
- Segue ADR-001 (SQLite direto) para leitura de dados
- Segue ADR-019 (schema_version em outputs JSON)
- Segue ADR-023 (banco ausente -> payload zerado sem exception)

### Consequencias

- CoordinationManager NAO executa acoes diretas sobre ordens MT5
- Agentes recebem sinais via arquivo JSON e optam por consumi-los
- Modulo pode ser iniciado/parado independentemente dos launchers operacionais
- Configuracao externalizada em config/agent_coordination.yaml

### Avaliacao de Impacto nos 5 Launchers

| Launcher | Impacto | Tipo | Acao Operacional |
|----------|---------|------|-----------------|
| INICIAR_AGENTE_RL_5000.bat | MEDIO | INDIRETO | Monitorado via magic=234500; sinal disponivel em outputs/coordination_signal_current.json |
| INICIAR_AGENTE_RL_DIRETO.bat | MEDIO | INDIRETO | Monitorado via magic=234600; sinal disponivel em outputs/coordination_signal_current.json |
| INICIAR_DIARIOS.bat | NENHUM | SEM IMPACTO | Nenhuma |
| INICIAR_MICRO_TENDENCIA_AUTO_TRADE.bat | NENHUM | SEM IMPACTO | Nenhuma |
| INICIAR_MONITOR_QUANTICO.bat | BAIXO | INDIRETO | outputs/coordination_signal_current.json novo artefato em outputs/ |

### Referencias

- BLID-041: implementacao completa (2026-04-06)
- ADR-001: SQLite direto sem ORM
- ADR-012: magic numbers dos agentes RL
- ADR-019: schema_version em outputs JSON
- ADR-023: banco ausente -> payload zerado sem exception
- ADR-032: ModelSyncManager (padrao de modulo application standalone)

## ADR-035: CoordinationSignalReader — Leitura Stateless de Sinal de Coordenacao (BLID-042)

**Status:** ACEITO
**Data:** 2026-04-06
**BLID:** BLID-042

### Contexto

O CoordinationManager (ADR-034 / BLID-041) emite sinais de coordenacao em arquivo
JSON atomico, mas os agentes RL nao tinham mecanismo padronizado para consumir
esses sinais antes de abrir posicoes.

### Decisao

Implementar CoordinationSignalReader como modulo stateless (sem thread, sem cache)
que:
- Le outputs/coordination_signal_current.json a cada chamada (leitura fresca)
- Valida schema_version="1.0" (ADR-019)
- Retorna CoordinationSignal.NORMAL se arquivo ausente ou invalido (ADR-023)
- Expoe pode_abrir_posicao() -> bool como API de alto nivel para agentes
- Expoe obter_sinal_atual() -> CoordinationSignal para inspecao granular
- Expoe obter_decisao_completa() -> Optional[DecisaoCoordinacao] para payload completo

### Motivacao

- Sem estado = sem necessidade de lifecycle (iniciar/parar)
- Leitura fresca garante que agentes sempre verao o sinal mais recente
- Fallback NORMAL seguro (ADR-023) evita bloqueio operacional por falha de IO
- Reutiliza CoordinationSignal e DecisaoCoordinacao do coordination_manager — sem duplicacao de tipos

### Consequencias

- Agentes RL podem chamar reader.pode_abrir_posicao() antes de enviar ordem
- STOP_OPERACOES bloqueia abertura; MODO_CONSERVADOR e MODO_DEFENSIVO sao informativos
- Modulo nao executa nenhuma acao — apenas le e interpreta
- Zero dependencias de infra novas

### Avaliacao de Impacto nos 5 Launchers

| Launcher | Impacto | Tipo | Acao Operacional |
|----------|---------|------|-----------------|
| INICIAR_AGENTE_RL_5000.bat | MEDIO | DIRETO | Pode integrar reader.pode_abrir_posicao() no loop de decisao |
| INICIAR_AGENTE_RL_DIRETO.bat | MEDIO | DIRETO | Pode integrar reader.pode_abrir_posicao() no loop de decisao |
| INICIAR_DIARIOS.bat | NENHUM | SEM IMPACTO | Nenhuma |
| INICIAR_MICRO_TENDENCIA_AUTO_TRADE.bat | NENHUM | SEM IMPACTO | Nenhuma |
| INICIAR_MONITOR_QUANTICO.bat | NENHUM | SEM IMPACTO | Nenhuma |

### Referencias

- BLID-042: implementacao completa (2026-04-06)
- ADR-019: schema_version em outputs JSON
- ADR-023: arquivo ausente -> fallback seguro sem exception
- ADR-034: CoordinationManager (produtor do sinal JSON)

## ADR-036: Integracao CoordinationManager por Agente com DB Local e Signal Path Exclusivo (BLID-043)

**Status:** ACEITO
**Data:** 2026-04-06
**BLID:** BLID-043

### Contexto

O CoordinationManager (ADR-034 / BLID-041) e o CoordinationSignalReader (ADR-035 / BLID-042)
foram implementados e testados mas nao estavam integrados nos loops de decisao dos agentes
RL (agente_rl_direto_independente.py e operar_novo_agente_rl_real_antiovertrading.py).
A protecao cross-agent existia em codigo mas nao estava ativa em producao.

### Decisao

Integrar CoordinationManager e CoordinationSignalReader diretamente nos dois scripts de
agente RL, seguindo tres decisoes arquiteturais registradas aqui como referencia para
evolucoes futuras:

**1. DB Local por Agente:**
Cada agente instancia seu proprio CoordinationManager apontando para seu banco SQLite
local (trading_rl_direto.db ou trading_rl_5000.db). Consequencia: drawdown_conjunto
reflete apenas o agente local; o outro agente aparece com PnL=[] -> drawdown=0. Esta
e uma protecao INDIVIDUAL (nao cross-agent completa), aceita para BLID-043.

**2. Signal Path Exclusivo por Tipo de Agente:**
Para evitar race condition de escrita quando dois managers rodam simultaneamente:
- RL Direto  -> outputs/coordination_signal_rl_direto.json
- RL 5000    -> outputs/coordination_signal_rl_5000.json
O path padrao "outputs/coordination_signal_current.json" fica reservado para
futuro coordinador unificado multi-DB.

**3. Graceful Degradation via Import Lazy:**
A importacao de coordination_manager e coordination_signal_reader usa try/except
(import lazy), seguindo o padrao estabelecido pelos blocos AC5.8/AC5.9/AC6 nos agentes.
Flag _COORDINATION_DISPONIVEL controla se o gate e aplicado. Falha de import ou init
nao impede operacao — agente opera sem protecao de coordenacao com log WARNING.

### Motivacao

- Integracao inline evita novo processo/servico: menor superficie operacional
- Protecao individual (90% do valor) entregue imediatamente
- Fallback NORMAL garante uptime independente do estado do arquivo JSON (ADR-023)
- Thread daemon garante que encerramento do agente nao e bloqueado pelo manager
- Import lazy segue convencao ja estabelecida no codebase para modulos opcionais

### Consequencias

- STOP_OPERACOES bloqueia abertura de posicao nos dois agentes RL
- MODO_CONSERVADOR e MODO_DEFENSIVO sao informativos (nao bloqueiam)
- Cada agente gera seu proprio JSON de sinal em outputs/
- Protecao conjunta real (drawdown_conjunto com vista de dois DBs) requer
  evolucao futura: coordinador unificado multi-DB
- agente_com_supervision.py (wrapper) nao e modificado — CoordinationManager
  e gerenciado dentro de operar_novo_agente_rl_real_antiovertrading.py

### Avaliacao de Impacto nos 5 Launchers

| Launcher | Impacto | Tipo | Acao Operacional |
|----------|---------|------|-----------------|
| INICIAR_AGENTE_RL_5000.bat | MEDIO | DIRETO | Monitorar outputs/coordination_signal_rl_5000.json apos inicio |
| INICIAR_AGENTE_RL_DIRETO.bat | MEDIO | DIRETO | Monitorar outputs/coordination_signal_rl_direto.json apos inicio |
| INICIAR_DIARIOS.bat | NENHUM | SEM IMPACTO | Nenhuma |
| INICIAR_MICRO_TENDENCIA_AUTO_TRADE.bat | NENHUM | SEM IMPACTO | Nenhuma |
| INICIAR_MONITOR_QUANTICO.bat | BAIXO | INDIRETO | Dois novos JSONs em outputs/ — monitoramento opcional |

### Referencias

- BLID-043: implementacao completa (2026-04-06)
- ADR-034: CoordinationManager (arquitetura base)
- ADR-035: CoordinationSignalReader (leitura stateless)
- ADR-023: fallback seguro para arquivo ausente
- ADR-019: schema_version em outputs JSON
- ADR-011: isolamento de DBs por agente RL

---

## ADR-037: AlertReversaoHandler — Sistema de Alertas para Reversoes de Lucro (BLID-044)

**Status:** ACEITO
**Data:** 2026-04-05
**BLID:** BLID-044

### Contexto

O ProfitProtectionEngine (implementado em P1-PROFIT_PROTECTION item #1) detecta
reversoes de lucro em tempo real quando um trade atinge status=ALERTA. No entanto,
o operador nao recebe notificacao imediata dessas reversoes, dependendo de
monitoramento manual ou logs.

Item #2 do P1-PROFIT_PROTECTION solicita notificacao em tempo real via WebSocket,
Email e Webhook (Slack/Discord) quando uma reversao e detectada, permitindo acao
rapida do operador.

### Decisao

Implementar AlertReversaoHandler que:

**1. Integracao com ProfitProtectionEngine:**
Converte ProfitProtectionResult (status=ALERTA) em AlertaOportunidade usando o
framework de alertas existente. Preserva compatibilidade com infraestrutura de
alertas atual (AlertaDeliveryManager, AlertaFormatter, etc).

**2. Entrega Multicanal:**
- PRIMARY: WebSocket (sync, <500ms) via AlertaDeliveryManager
- SECONDARY: Email SMTP (async, 2-8s com retry) via AlertaDeliveryManager
- TERTIARY: Webhook Slack/Discord (fire-and-forget, timeout 5s) via httpx

**3. Throttling de Alertas:**
Minimo 60s entre alertas do mesmo trade_id para evitar spam quando mercado oscila
rapidamente. Historico de alertas mantido em memoria com limpeza automatica de
registros >24h.

**4. Payload Webhook:**
Formato Slack/Discord com blocos estruturados contendo:
- Trade ID, simbolo, direcao
- Preco entrada, lucro atual, lucro maximo
- Deviance de reversao (%)
- Acao sugerida pelo ProfitProtectionEngine

**5. Configuracao Externa:**
config/alert_reversoes.yaml com Pydantic validation para:
- habilitado (on/off)
- webhook_url (env var ALERT_WEBHOOK_URL)
- throttle_seconds (default 60)
- nivel_padrao (ALTO)

**6. Novo Padrao de Alerta:**
PatraoAlerta.REVERSAO_LUCRO adicionado aos enums existentes, mantendo
retrocompatibilidade com padroes SMC, volatilidade e tecnicos.

### Motivacao

- Operador recebe notificacao imediata via webhook Slack/Discord (mobile)
- Email como backup quando WebSocket falha ou operador offline
- Throttling evita spam durante oscilacoes rapidas do mercado
- Integracao com AlertaDeliveryManager existente aproveita retry logic e audit
- Configuracao externa permite ajuste de thresholds sem redeploy

### Consequencias

**Positivas:**
- Tempo de resposta do operador reduz de minutos (monitoramento manual) para
  segundos (notificacao push)
- Protecao de lucros mais efetiva com acao rapida em reversoes
- Auditoria completa via AlertaDeliveryManager (timestamps, canais, status)
- Throttling evita fadiga de alerta e falsos positivos

**Negativas:**
- Dependencia de httpx para webhooks (nova lib)
- Historico de throttling em memoria (perdido em restart, mas aceitavel)
- Webhook e fire-and-forget (sem garantia de entrega, mas nao bloqueante)

**Tecnicas:**
- 21 testes unitarios: conversao, throttling, webhook, integracao
- Type hints 100% com mypy --strict
- Async/await para webhook e delivery manager
- AlertReversaoConfig com Pydantic validation

### Avaliacao de Impacto nos 5 Launchers

| Launcher | Impacto | Tipo | Acao Operacional |
|----------|---------|------|-----------------|
| INICIAR_AGENTE_RL_5000.bat | MEDIO | DIRETO | Habilitar alertas via env var ALERT_WEBHOOK_URL |
| INICIAR_AGENTE_RL_DIRETO.bat | MEDIO | DIRETO | Habilitar alertas via env var ALERT_WEBHOOK_URL |
| INICIAR_DIARIOS.bat | NENHUM | SEM IMPACTO | Nenhuma |
| INICIAR_MICRO_TENDENCIA_AUTO_TRADE.bat | NENHUM | SEM IMPACTO | Nenhuma |
| INICIAR_MONITOR_QUANTICO.bat | NENHUM | SEM IMPACTO | Nenhuma |

**Nota:** Integracao com ProfitProtectionEngine requer modificacao nos agentes RL
para instanciar AlertReversaoHandler e chamar processar_reversao() quando
processar_protecao() retorna status=ALERTA.

### Integracao com Agentes RL (BLID-045)

**Status:** CONCLUIDO (2026-04-05)

AlertReversaoHandler foi integrado aos dois agentes RL em producao:

**1. RL 5000 (operar_novo_agente_rl_real_antiovertrading.py):**
- Lazy import com feature flag _ALERT_REVERSAO_DISPONIVEL
- Inicializacao em startup_sequence() com config de YAML ou env var
- Disparo de alerta em _processar_protecao_lucros() quando status=ALERTA
- Graceful degradation: funciona mesmo sem AlertaDeliveryManager

**2. RL Direto (agente_rl_direto_independente.py):**
- Lazy import com feature flag _ALERT_REVERSAO_DISPONIVEL_DIRETO
- Inicializacao em _inicializar_componentes() com config de YAML ou env var
- Disparo de alerta em processar_protecao_lucros_rl_direto() quando status=ALERTA
- Injecao via dict componentes["alert_reversao_handler"]

**Padrao de Integracao:**
```python
# Import com feature flag
try:
    from src.application.alert_reversao_handler import (
        AlertReversaoHandler,
        AlertReversaoConfig,
    )
    from src.application.services.alerta_delivery import AlertaDeliveryManager
    import yaml
    _ALERT_REVERSAO_DISPONIVEL = True
except ImportError:
    _ALERT_REVERSAO_DISPONIVEL = False

# Inicializacao
if _ALERT_REVERSAO_DISPONIVEL:
    alert_config = AlertReversaoConfig()
    # Carregar de config/alert_reversoes.yaml se existir
    # Fallback para env var ALERT_WEBHOOK_URL
    _alerta_delivery_manager = AlertaDeliveryManager(
        websocket_client=None,  # Graceful degradation
        email_config=None,
    )
    _alert_reversao_handler = AlertReversaoHandler(
        delivery_manager=_alerta_delivery_manager,
        config=alert_config,
    )

# Disparo de alerta
if _ALERT_REVERSAO_DISPONIVEL and _alert_reversao_handler:
    if resultado_protecao.status == ProtectionStatus.ALERTA:
        asyncio.run(_alert_reversao_handler.processar_reversao(resultado_protecao))
```

**Acceptance Criteria (AC):**
- AC1: Handler inicializado com config de YAML/env var ✅
- AC2: processar_reversao() converte ProfitProtectionResult em AlertaOportunidade ✅
- AC3: AlertaDeliveryManager injetado no handler ✅
- AC5: Webhook URL carregada de env var ALERT_WEBHOOK_URL ✅
- AC6: Throttling de 60s aplicado entre alertas do mesmo trade ✅
- AC7: Graceful degradation quando AlertaDeliveryManager nao disponivel ✅
- AC8/AC9: Alerta contem trade_id e simbolo no payload ✅
- AC10: Limpeza automatica de historico de alertas >24h ✅

**Testes:**
- tests/unit/test_blid045_integration.py: 10 testes unitarios cobrindo todos AC

**Divida Tecnica Resolvida:**
- DT-BLID044-03 (MEDIA): Integracao AlertReversaoHandler com agentes RL

---

## ADR-038: Backtest de Profit Protection — Validacao Historica COM vs SEM Protecao (BLID-046)

**Data:** 2026-04-05
**Status:** APROVADO
**Decisores:** Product Owner, Tech Lead, ML Expert
**BLID:** BLID-046

### Contexto

O ProfitProtectionEngine foi implementado e está em producao nos dois agentes
RL desde 04/04/2026 (ADR-018), com thresholds externalizados para
`config/profit_protection.yaml` e suporte a 3 perfis (baseline, conservador,
agressivo).

No entanto, nao havia **validacao quantitativa historica** da efetividade da
protecao. Era necessario responder com dados objetivos:

**Perguntas-Chave:**
1. A protecao realmente reduz o drawdown maximo?
2. O win rate melhora ou se mantem estavel?
3. O Sharpe ratio aumenta com a protecao?
4. Quanto tempo de exposicao e economizado em reversoes?
5. Quantas reversoes sao evitadas por mes?

Sem esse backtest comparativo, decisoes sobre calibracao de thresholds e
rollout de perfis mais agressivos ficavam baseadas em feeling, nao em
evidencias.

### Decisao

**Criar script standalone de backtest** que simula trades COM e SEM protecao
em periodo de 6-12 meses, calculando metricas comparativas e gerando
relatorios JSON e Markdown automatizados.

**Componentes:**
1. **BacktestProfitProtection class** — simulador principal
2. **Trade dataclass** — representacao de trade completo
3. **MetricasBacktest dataclass** — metricas agregadas (12+)
4. **ResultadoComparativo dataclass** — comparacao COM vs SEM
5. **Funcoes de saida** — JSON + Markdown com tabelas e conclusoes

**Metricas Calculadas:**
- Win rate (vencedores / total)
- Drawdown maximo (equity curve peak-to-trough)
- Sharpe ratio (mean_return / std_return)
- Profit total acumulado
- Tempo medio de exposicao (minutos)
- Quantidade de break-even closes
- Quantidade de reversoes evitadas
- Profit medio vencedor/perdedor

**Simulacao:**
- Trades SEM protecao: win rate natural ~62%, profit medio +2%/-1.2%
- Trades COM protecao: break-even em reversoes, reducao de exposicao

**Reproducibilidade:**
- Seed configuravel (padrao: 42)
- Perfis de config: baseline/conservador/agressivo

**Saida:**
- JSON: `outputs/backtest_profit_protection_resultado.json`
- Markdown: `outputs/backtest_profit_protection_resultado.md`

### Alternativas Consideradas

**1. Usar backtest real com dados do MT5**
- **Pros:** Dados reais de mercado, mais fidelidade
- **Cons:** Requer infraestrutura complexa, lento (horas), nao reproducivel
- **Decisao:** REJEITADO — simulacao e suficiente para validacao de conceito

**2. Integrar ao BacktestMacroScoreEngine existente**
- **Pros:** Reusa engine de backtest
- **Cons:** Acoplamento desnecessario, objetivo diferente (macro score vs profit protection)
- **Decisao:** REJEITADO — manter script standalone

**3. Criar apenas relatorio manual**
- **Pros:** Mais rapido
- **Cons:** Nao reproducivel, sem automacao, sem CI/CD
- **Decisao:** REJEITADO — automacao e essencial

### Consequencias

**Positivas:**
- **Validacao quantitativa:** Drawdown, win rate e Sharpe com numeros concretos
- **Decisoes baseadas em dados:** Calibracao de thresholds informada por backtest
- **Reproducibilidade:** Seed fixo permite comparar perfis de forma justa
- **Automacao:** Script pode rodar em CI/CD para validar mudancas em thresholds
- **Documentacao automatica:** Markdown gerado com conclusoes

**Negativas:**
- Simulacao, nao dados reais (trade-off aceitavel para velocidade)
- Seed fixo pode nao cobrir todos cenarios (mas permite A/B testing)

**Tecnicas:**
- 24 testes unitarios: simulacao, metricas, comparacao, saida
- Type hints 100% com mypy --strict
- Dataclasses para estruturas de dados
- Argumentos CLI para configuracao (meses, perfil, seed, output)

### Avaliacao de Impacto nos 5 Launchers

| Launcher | Impacto | Tipo | Acao Operacional |
|----------|---------|------|-----------------|
| INICIAR_AGENTE_RL_5000.bat | NENHUM | SEM IMPACTO | Nenhuma - script offline |
| INICIAR_AGENTE_RL_DIRETO.bat | NENHUM | SEM IMPACTO | Nenhuma - script offline |
| INICIAR_DIARIOS.bat | NENHUM | SEM IMPACTO | Nenhuma |
| INICIAR_MICRO_TENDENCIA_AUTO_TRADE.bat | NENHUM | SEM IMPACTO | Nenhuma |
| INICIAR_MONITOR_QUANTICO.bat | NENHUM | SEM IMPACTO | Nenhuma |

**Nota:** Script e executado offline (nao em runtime dos agentes), apenas para
analise e calibracao de thresholds.

### Uso do Script

```bash
# Backtest de 6 meses com perfil baseline
python scripts/backtest_profit_protection.py --meses 6

# Backtest de 12 meses com perfil conservador
python scripts/backtest_profit_protection.py --meses 12 --profile conservador

# Backtest com seed customizado e output customizado
python scripts/backtest_profit_protection.py --meses 6 --seed 123 --output custom.json
```

### Proximos Passos

1. Executar backtest com perfil baseline (6 meses)
2. Executar backtest com perfil conservador (6 meses)
3. Executar backtest com perfil agressivo (6 meses)
4. Comparar resultados e decidir rollout de perfis
5. Considerar adicionar graficos de equity curve (matplotlib) em iteracao futura
6. Considerar backtest com dados reais do MT5 (iteracao futura)

### Referencias

- BLID-046: Backtest de Profit Protection (docs/BACKLOG.md)
- ADR-018: Governanca de Thresholds do Profit Protection por Perfil
- P1-PROFIT_PROTECTION: Bloco de evolucao do profit protection (docs/BACKLOG.md)
- `scripts/backtest_profit_protection.py`: Implementacao
- `tests/unit/test_backtest_profit_protection.py`: 24 testes unitarios

### Referencias

- BLID-044: implementacao completa (2026-04-05)
- BLID-045: integracao com agentes RL (2026-04-05)
- P1-PROFIT_PROTECTION item #2: especificacao de alertas
- ADR-018: configuracao de ProfitProtectionEngine por perfil
- src/application/alert_reversao_handler.py: implementacao
- config/alert_reversoes.yaml: configuracao canonica
- tests/unit/test_alert_reversao_handler.py: 21 testes unitarios
- tests/unit/test_blid045_integration.py: 10 testes de integracao

---

## ADR-039: Sinal Complementar de Regime por Quebra de Correlacao Rolling (BLID-059)

**Data:** 2026-04-06
**Status:** APROVADO
**Decisores:** Product Owner, Tech Lead, ML Expert
**BLID:** BLID-059

### Contexto

O runtime adaptativo do Profit Protection (ADR-038/BLID-056) trocava perfil
somente por shift de win rate entre blocos recentes. Em viradas intraday
abruptas, esse gatilho pode reagir tarde, pois depende de materialização de
outcome em trades já fechados.

### Decisao

Adicionar gatilho complementar de regime por quebra de correlação rolling na
janela recente:

- considerar evento de quebra quando:
  - `quebra_correlacao=true`, ou
  - `abs(correlacao_rolling) < limiar_quebra_correlacao`;
- se houver eventos suficientes na janela (`min_eventos_quebra_correlacao`),
  priorizar perfil `conservador` (fallback `baseline`);
- manter gatilho por win rate para cenários de melhora/degradação já cobertos.

Parâmetros adicionados:

- `limiar_quebra_correlacao` (default `0.30`)
- `min_eventos_quebra_correlacao` (default `2`)

### Consequencias

**Positivas:**
- resposta mais rápida a regime shift intraday;
- redução de risco de manter perfil agressivo em quebra de contexto;
- preserva retrocompatibilidade com lógica de win rate existente.

**Negativas:**
- maior sensibilidade pode elevar número de switches em ambiente ruidoso;
- requer observabilidade em staging para ajuste fino de limiar.

### Evidencias

- `pytest tests/unit/test_profit_protection_regime_runtime.py -q` -> **10/10 PASSING**
- `mypy --strict --follow-imports=skip src/application/profit_protection_regime_runtime.py tests/unit/test_profit_protection_regime_runtime.py` -> **0 erros**

### Avaliacao de Impacto nos 5 Launchers

| Launcher | Impacto | Tipo | Acao Operacional |
|----------|---------|------|-----------------|
| INICIAR_AGENTE_RL_5000.bat | MEDIO | DIRETO | Validar eventos `[PP-REGIME]` em staging com campo de correlação |
| INICIAR_AGENTE_RL_DIRETO.bat | MEDIO | DIRETO | Validar eventos `[PP-REGIME]` em staging com campo de correlação |
| INICIAR_DIARIOS.bat | NENHUM | SEM IMPACTO | Nenhuma |
| INICIAR_MICRO_TENDENCIA_AUTO_TRADE.bat | NENHUM | SEM IMPACTO | Nenhuma |
| INICIAR_MONITOR_QUANTICO.bat | NENHUM | SEM IMPACTO | Nenhuma |

### Referencias

- `src/application/profit_protection_regime_runtime.py`
- `tests/unit/test_profit_protection_regime_runtime.py`
- `docs/BACKLOG.md` (BLID-059)

---

## ADR-040: Guardrail de Degradacao Intraday Critica no Runtime do Profit Protection (BLID-060)

**Data:** 2026-04-06
**Status:** APROVADO
**Decisores:** Product Owner, Tech Lead, ML Expert
**BLID:** BLID-060

### Contexto

Mesmo com os gatilhos de regime existentes (shift por win rate e quebra de
correlacao), houve cenário operacional em que a sessao entrou em degradacao
severa de performance antes de um sinal de regime suficientemente forte.

Isso aumenta risco de drawdown no intraday e posterga a troca para um perfil
mais defensivo.

### Decisao

Adicionar no runtime um gatilho complementar de **degradacao intraday critica**
que aciona postura conservadora quando ha combinacao de sinais ruins na janela
recente, independentemente de regime shift classico:

- `win_rate_recente` abaixo do limiar;
- `loss_streak` acima do minimo;
- `resultado_acumulado` abaixo do limite.

A decisao exige um numero minimo configuravel de sinais para evitar
reatividade excessiva.

Novos parametros:

- `limiar_win_rate_degradado` (default `0.35`)
- `min_loss_streak_degradado` (default `3`)
- `limiar_resultado_acumulado_degradado` (default `-1.0`)
- `min_sinais_degradacao` (default `2`)

### Consequencias

**Positivas:**
- resposta mais rápida a sessao deteriorada;
- menor permanencia em perfil agressivo durante queda abrupta de qualidade;
- compatibilidade com o fluxo atual de switch e cooldown anti-thrashing.

**Negativas / Riscos:**
- possibilidade de troca conservadora em ruido de curto prazo se limiares
  estiverem apertados;
- necessidade de calibracao em staging com sessao real degradada.

### Evidencias

- `pytest tests/unit/test_profit_protection_regime_runtime.py -q` -> **12/12 PASSING**
- `mypy --strict --follow-imports=skip src/application/profit_protection_regime_runtime.py tests/unit/test_profit_protection_regime_runtime.py` -> **0 erros**
- Replay/staging real:
  - `python scripts/staging_validation_blid060.py --date 20260406`
  - `outputs/blid060_staging_validation_20260406_145642.json`
  - `outputs/blid060_pp_regime_staging_20260406_145642.log`
  - `apto_para_concluir_blid060=true` com `switches_por_100_avaliacoes=2.8571` e `thrashing_detectado=false`

### Calibracao Final (2026-04-06)

Parametros calibrados no runtime apos replay da sessao degradada:

- `limiar_win_rate_degradado=0.30`
- `min_loss_streak_degradado=3`
- `limiar_resultado_acumulado_degradado=-0.08`
- `min_sinais_degradacao=2`
- `min_trades_degradacao_critica=4`

Decisao complementar aplicada:
- permitir fallback conservador por degradacao critica em amostra parcial,
  sem aguardar duas janelas completas quando a deterioracao ja e evidente.

### Avaliacao de Impacto nos 5 Launchers

| Launcher | Impacto | Tipo | Acao Operacional |
|----------|---------|------|-----------------|
| INICIAR_AGENTE_RL_5000.bat | ALTO | DIRETO | Restart recomendavel apos deploy e monitoramento de logs `[PP-REGIME]` |
| INICIAR_AGENTE_RL_DIRETO.bat | ALTO | DIRETO | Restart recomendavel apos deploy e monitoramento de logs `[PP-REGIME]` |
| INICIAR_DIARIOS.bat | BAIXO | INDIRETO | Sem restart; observar consolidado de performance da sessao |
| INICIAR_MICRO_TENDENCIA_AUTO_TRADE.bat | NENHUM | SEM IMPACTO | Nenhuma |
| INICIAR_MONITOR_QUANTICO.bat | BAIXO | INDIRETO | Acompanhar sinais de risco e troca de perfil sem restart obrigatorio |

### Referencias

- `src/application/profit_protection_regime_runtime.py`
- `tests/unit/test_profit_protection_regime_runtime.py`
- `scripts/staging_validation_blid060.py`
- `docs/BACKLOG.md` (BLID-060)

---

## ADR-041: Integracao de Rollback Automatico ao Scheduler de Retrain RL (BLID-061)

**Data:** 2026-04-06
**Status:** APROVADO
**Decisores:** Product Owner, Tech Lead, ML Expert
**BLID:** BLID-061

### Contexto

O scheduler de retrain (`RLScheduler`) detectava degradacao e apenas agendava
retrain, sem acionar rollback automatico quando o modelo em runtime já mostrava
queda relevante de performance.

Isso criava janela operacional maior com modelo degradado até conclusão do
retrain.

### Decisao

Adicionar fluxo integrado no scheduler para:

1. detectar degradacao;
2. agendar/persistir job de retrain;
3. opcionalmente consultar `ModelRollbackManager` e executar rollback imediato
   quando recomendado.

Foi adicionado:
- `processar_degradacao_com_rollback(...)`;
- normalização de chaves de métricas para compatibilidade:
  - `sharpe_ratio -> sharpe`
  - `f1_score -> f1`.

### Consequencias

**Positivas:**
- reduz latência de resposta a degradação severa;
- mantém trilha auditável de retrain e rollback no mesmo fluxo;
- preserva compatibilidade backward (rollback manager é opcional).

**Riscos:**
- disparo indevido de rollback em thresholds mal calibrados;
- requer monitoramento de logs em staging antes de ampliar rollout.

### Evidencias

- `pytest tests/unit/test_rl_retrain_scheduler.py -q` -> **28/28 PASSING**
- `mypy --strict src/application/rl_retrain_scheduler.py tests/unit/test_rl_retrain_scheduler.py` -> **0 erros**

### Avaliacao de Impacto nos 5 Launchers

| Launcher | Impacto | Tipo | Acao Operacional |
|----------|---------|------|-----------------|
| INICIAR_AGENTE_RL_5000.bat | MEDIO | DIRETO | Validar fluxo retrain/rollback em staging; restart recomendado apos deploy |
| INICIAR_AGENTE_RL_DIRETO.bat | MEDIO | DIRETO | Validar fluxo retrain/rollback em staging; restart recomendado apos deploy |
| INICIAR_DIARIOS.bat | BAIXO | INDIRETO | Monitorar consolidação de métricas pós-sessão |
| INICIAR_MICRO_TENDENCIA_AUTO_TRADE.bat | BAIXO | INDIRETO | Sem restart obrigatório; monitorar integração compartilhada |
| INICIAR_MONITOR_QUANTICO.bat | BAIXO | INDIRETO | Acompanhar eventos no dashboard e alertas |

### Referencias

- `src/application/rl_retrain_scheduler.py`
- `tests/unit/test_rl_retrain_scheduler.py`
- `src/application/rl_model_rollback_manager.py`
- `docs/BACKLOG.md` (BLID-061)

---

## ADR-042: Deteccao Multi-Metodo no Scheduler RL com Integracao ao BaselineComparator (BLID-062)

**Data:** 2026-04-06
**Status:** APROVADO
**Decisores:** Product Owner, Tech Lead, ML Expert
**BLID:** BLID-062

### Contexto

O scheduler já possuía enum de método de detecção (`Z_SCORE`, `PERCENTUAL`,
`THRESHOLD`), porém o fluxo efetivo aplicava somente lógica percentual.

Isso reduzia a aderência do pipeline adaptativo e limitava calibração por
regime intraday.

### Decisao

Implementar detecção multi-método no `RLScheduler`, com:

- integração ao `BaselineComparator` no método `Z_SCORE`;
- método `THRESHOLD` para gatilhos fixos de risco;
- método `PERCENTUAL` mantido como fallback/default;
- normalização de chaves para compatibilidade de métricas entre módulos.

### Consequencias

**Positivas:**
- maior flexibilidade operacional para calibrar detecção por regime;
- reaproveitamento do comparador AC6.9 no fluxo de scheduler;
- rastreabilidade clara do método aplicado por execução.

**Riscos:**
- sensibilidade excessiva se método for mal escolhido por contexto;
- exige governança por sessão/símbolo para troca de método em produção.

### Evidencias

- `pytest tests/unit/test_rl_retrain_scheduler.py -q` -> **31/31 PASSING**
- `mypy --strict src/application/rl_retrain_scheduler.py tests/unit/test_rl_retrain_scheduler.py` -> **0 erros**

### Avaliacao de Impacto nos 5 Launchers

| Launcher | Impacto | Tipo | Acao Operacional |
|----------|---------|------|-----------------|
| INICIAR_AGENTE_RL_5000.bat | MEDIO | DIRETO | Validar método ativo e motivos de degradação em staging |
| INICIAR_AGENTE_RL_DIRETO.bat | MEDIO | DIRETO | Validar método ativo e motivos de degradação em staging |
| INICIAR_DIARIOS.bat | BAIXO | INDIRETO | Observar efeitos nos relatórios de sessão |
| INICIAR_MICRO_TENDENCIA_AUTO_TRADE.bat | BAIXO | INDIRETO | Monitorar integração compartilhada sem restart obrigatório |
| INICIAR_MONITOR_QUANTICO.bat | BAIXO | INDIRETO | Expor evento e método no monitoramento |

### Referencias

- `src/application/rl_retrain_scheduler.py`
- `tests/unit/test_rl_retrain_scheduler.py`
- `src/application/ac6_9_baseline_comparator.py`
- `docs/BACKLOG.md` (BLID-062)

---

## ADR-043: Resolucao Dinamica de Metodo de Deteccao por Sessao/Regime no Scheduler RL (BLID-063)

**Data:** 2026-04-06
**Status:** APROVADO
**Decisores:** Product Owner, Tech Lead, ML Expert
**BLID:** BLID-063

### Contexto

Após habilitar detecção multi-método (ADR-042), ainda faltava o wiring
operacional para escolher automaticamente o método ideal por sessão,
considerando contexto de regime e estresse intraday.

### Decisao

Adicionar resolvedor dinâmico de método no `RLScheduler`:

- `THRESHOLD` quando contexto indicar estresse (ex.: ruptura/high vol);
- `Z_SCORE` quando contexto indicar regime estável/normal com drift;
- fallback para método padrão do scheduler quando contexto for inconclusivo.

O fluxo `processar_degradacao_com_rollback(...)` passa a receber
`contexto_operacional` e registrar `metodo_deteccao_aplicado`.

### Consequencias

**Positivas:**
- resposta mais rápida em cenários de estresse intraday;
- menor dependência de configuração manual fixa por ambiente;
- rastreabilidade explícita do método aplicado por execução.

**Riscos:**
- classificação de contexto incorreta pode escolher método subótimo;
- exige qualidade da fonte de contexto operacional no runtime live.

### Evidencias

- `pytest tests/unit/test_rl_retrain_scheduler.py -q` -> **34/34 PASSING**
- `mypy --strict src/application/rl_retrain_scheduler.py tests/unit/test_rl_retrain_scheduler.py` -> **0 erros**

### Avaliacao de Impacto nos 5 Launchers

| Launcher | Impacto | Tipo | Acao Operacional |
|----------|---------|------|-----------------|
| INICIAR_AGENTE_RL_5000.bat | MEDIO | DIRETO | Validar método dinâmico aplicado e motivos de degradação em staging |
| INICIAR_AGENTE_RL_DIRETO.bat | MEDIO | DIRETO | Validar método dinâmico aplicado e motivos de degradação em staging |
| INICIAR_DIARIOS.bat | BAIXO | INDIRETO | Monitorar impacto nos relatórios pós-sessão |
| INICIAR_MICRO_TENDENCIA_AUTO_TRADE.bat | BAIXO | INDIRETO | Sem restart obrigatório; acompanhar integração compartilhada |
| INICIAR_MONITOR_QUANTICO.bat | BAIXO | INDIRETO | Expor telemetria de método aplicado e gatilho |

### Referencias

- `src/application/rl_retrain_scheduler.py`
- `tests/unit/test_rl_retrain_scheduler.py`
- `docs/BACKLOG.md` (BLID-063)

---

## ADR-044: Wiring Runtime do Scheduler Dinamico nos Agentes RL (BLID-064)

**Data:** 2026-04-06
**Status:** APROVADO
**Decisores:** Product Owner, Tech Lead, ML Expert
**BLID:** BLID-064

### Contexto

O scheduler dinâmico (ADR-043) estava validado em unidade, porém ainda não
estava conectado ao fluxo real de decisão/feedback dos agentes RL.

Sem esse wiring, a escolha dinâmica de método e o agendamento de retrain
continuavam sem efeito operacional live.

### Decisao

Integrar o `RLScheduler` diretamente no pipeline `_executar_pipeline_feedback_rl`
dos dois agentes RL, com derivação de métricas/contexto a partir dos trades
fechados da própria sessão.

Foi criado adaptador compartilhado (`rl_scheduler_runtime_adapter`) para:
- extrair pnls do payload operacional;
- calcular métricas para detecção de degradação;
- construir contexto de regime/estresse para seleção de método.

### Consequencias

**Positivas:**
- fecha o ciclo “Eu aprendo operando” em runtime real;
- aumenta velocidade de resposta a deterioração intraday;
- reduz divergência entre comportamento em teste e produção.

**Riscos:**
- métricas derivadas de payload heterogêneo podem precisar ajuste fino;
- necessidade de calibração por símbolo para evitar sensibilidade excessiva.

### Evidencias

- `pytest tests/unit/test_rl_scheduler_runtime_adapter.py tests/unit/test_rl_retrain_scheduler.py -q` -> **39/39 PASSING**
- `mypy --strict src/application/rl_scheduler_runtime_adapter.py src/application/rl_retrain_scheduler.py tests/unit/test_rl_scheduler_runtime_adapter.py tests/unit/test_rl_retrain_scheduler.py` -> **0 erros**
- `python -m py_compile scripts/agente_rl_direto_independente.py scripts/operar_novo_agente_rl_real_antiovertrading.py` -> **OK**

### Avaliacao de Impacto nos 5 Launchers

| Launcher | Impacto | Tipo | Acao Operacional |
|----------|---------|------|-----------------|
| INICIAR_AGENTE_RL_5000.bat | ALTO | DIRETO | Validar logs `[RL-SCHED]` em staging e método aplicado |
| INICIAR_AGENTE_RL_DIRETO.bat | ALTO | DIRETO | Validar logs `[RL-SCHED]` em staging e método aplicado |
| INICIAR_DIARIOS.bat | BAIXO | INDIRETO | Monitorar reflexo no fechamento e classificação de sessão |
| INICIAR_MICRO_TENDENCIA_AUTO_TRADE.bat | BAIXO | INDIRETO | Acompanhar integração compartilhada sem restart obrigatório |
| INICIAR_MONITOR_QUANTICO.bat | MEDIO | INDIRETO | Expor telemetria de método/retrain para acompanhamento |

### Referencias

- `src/application/rl_scheduler_runtime_adapter.py`
- `src/application/rl_retrain_scheduler.py`
- `scripts/agente_rl_direto_independente.py`
- `scripts/operar_novo_agente_rl_real_antiovertrading.py`
- `tests/unit/test_rl_scheduler_runtime_adapter.py`
- `tests/unit/test_rl_retrain_scheduler.py`
- `docs/BACKLOG.md` (BLID-064)

---

## ADR-045: Calibracao do Scheduler Runtime por Simbolo (BLID-065)

**Data:** 2026-04-06
**Status:** APROVADO
**Decisores:** Product Owner, Tech Lead, ML Expert
**BLID:** BLID-065

### Contexto

Com o wiring runtime do scheduler concluido (ADR-044), a deteccao de degradacao
passou a depender fortemente de thresholds unificados. Em operacao intraday,
`WIN` e `WDO` apresentam dinamicas diferentes de variancia e velocidade de
mudanca de regime, gerando risco de sensibilidade inadequada quando o limiar
e unico.

### Decisao

Adicionar calibracao por simbolo no adaptador runtime do scheduler:

- normalizar simbolo operacional para `WIN`/`WDO`/`DEFAULT`;
- aplicar thresholds dedicados por simbolo para:
  - `stress_score_trigger`
  - `volatilidade_trigger`
  - `loss_streak_divisor`
  - `media_negativa_scale`
- propagar `simbolo_contexto` no payload de contexto operacional;
- obrigar os agentes RL a informar `simbolo=SIMBOLO` ao montar contexto para o
  scheduler.

### Consequencias

**Positivas:**
- reduz falso positivo de degradacao em simbolo com variancia naturalmente maior;
- aumenta velocidade de resposta em simbolo que exige gatilho mais sensivel;
- melhora rastreabilidade operacional com contexto explicito por simbolo.

**Riscos:**
- calibracao inicial pode exigir ajuste fino com replay de sessoes reais;
- simbolos novos ficam em `DEFAULT` ate definicao dedicada.

### Evidencias

- `pytest tests/unit/test_rl_scheduler_runtime_adapter.py tests/unit/test_rl_retrain_scheduler.py -q` -> **41/41 PASSING**
- `mypy --strict src/application/rl_scheduler_runtime_adapter.py src/application/rl_retrain_scheduler.py tests/unit/test_rl_scheduler_runtime_adapter.py tests/unit/test_rl_retrain_scheduler.py` -> **0 erros**
- `python -m py_compile scripts/agente_rl_direto_independente.py scripts/operar_novo_agente_rl_real_antiovertrading.py` -> **OK**

### Avaliacao de Impacto nos 5 Launchers

| Launcher | Impacto | Tipo | Acao Operacional |
|----------|---------|------|-----------------|
| INICIAR_AGENTE_RL_5000.bat | ALTO | DIRETO | Validar `simbolo_contexto` e estabilidade de gatilhos em WIN |
| INICIAR_AGENTE_RL_DIRETO.bat | ALTO | DIRETO | Validar `simbolo_contexto` e sensibilidade de gatilho em WDO |
| INICIAR_DIARIOS.bat | BAIXO | INDIRETO | Monitorar taxa de retrain/rollback no fechamento diario |
| INICIAR_MICRO_TENDENCIA_AUTO_TRADE.bat | BAIXO | INDIRETO | Sem alteracao direta; acompanhar integracoes compartilhadas |
| INICIAR_MONITOR_QUANTICO.bat | MEDIO | INDIRETO | Expor `simbolo_contexto` e método aplicado na camada de monitoramento |

### Referencias

- `src/application/rl_scheduler_runtime_adapter.py`
- `tests/unit/test_rl_scheduler_runtime_adapter.py`
- `scripts/agente_rl_direto_independente.py`
- `scripts/operar_novo_agente_rl_real_antiovertrading.py`
- `docs/BACKLOG.md` (BLID-065)

---

## ADR-046: Replay Controlado para Consolidacao de Thresholds por Simbolo no Scheduler Runtime (BLID-066)

**Data:** 2026-04-06
**Status:** APROVADO
**Decisores:** Product Owner, Tech Lead, ML Expert
**BLID:** BLID-066

### Contexto

Com a calibracao por simbolo habilitada em runtime (ADR-045), faltava um fluxo
repetivel para validar thresholds antes de promover ajustes em producao.

Sem replay controlado por simbolo, havia risco de tuning reativo sobre amostra
insuficiente e aumento de falso positivo/falso negativo no gatilho de degradacao.

### Decisao

Introduzir pipeline de replay/calibracao por simbolo com:

- cenarios `degradado` e `estavel` por simbolo;
- grid de candidatos por simbolo (`WIN` e `WDO`);
- criterio de selecao:
  - maximizar acerto de regime esperado;
  - penalizar distancia excessiva da calibracao vigente;
- artefato versionavel em `outputs/scheduler_symbol_calibration_*.json`.

Para suportar replay sem efeito colateral em producao, o adaptador runtime passa
a aceitar `calibracao_override` apenas no caminho de simulacao.

### Consequencias

**Positivas:**
- padroniza validacao de thresholds antes de rollout;
- melhora disciplina de risco no ciclo "Eu aprendo operando";
- cria trilha objetiva para decisao de promover ou manter calibracao.

**Riscos:**
- cobertura de cenarios reais pode ser insuficiente em dias com poucos trades;
- ainda exige gate operacional para promover alteracoes em producao.

### Evidencias

- `pytest tests/unit/test_rl_scheduler_runtime_adapter.py tests/unit/test_rl_scheduler_symbol_calibration.py tests/unit/test_rl_retrain_scheduler.py -q` -> **45/45 PASSING**
- `mypy --strict src/application/rl_scheduler_runtime_adapter.py src/application/rl_scheduler_symbol_calibration.py tests/unit/test_rl_scheduler_runtime_adapter.py tests/unit/test_rl_scheduler_symbol_calibration.py` -> **0 erros**
- `python -m py_compile scripts/calibrar_scheduler_runtime_por_simbolo.py src/application/rl_scheduler_symbol_calibration.py` -> **OK**
- `python scripts/calibrar_scheduler_runtime_por_simbolo.py --date 20260406` -> **OK** (`outputs/scheduler_symbol_calibration_20260406_155101.json`)

### Avaliacao de Impacto nos 5 Launchers

| Launcher | Impacto | Tipo | Acao Operacional |
|----------|---------|------|-----------------|
| INICIAR_AGENTE_RL_5000.bat | MEDIO | DIRETO | Executar replay por simbolo antes de promover tuning |
| INICIAR_AGENTE_RL_DIRETO.bat | MEDIO | DIRETO | Executar replay por simbolo antes de promover tuning |
| INICIAR_DIARIOS.bat | BAIXO | INDIRETO | Consolidar artefatos de replay no fechamento |
| INICIAR_MICRO_TENDENCIA_AUTO_TRADE.bat | BAIXO | INDIRETO | Sem alteracao direta de runtime |
| INICIAR_MONITOR_QUANTICO.bat | MEDIO | INDIRETO | Exibir recomendacao por simbolo no painel de monitoramento |

### Referencias

- `src/application/rl_scheduler_runtime_adapter.py`
- `src/application/rl_scheduler_symbol_calibration.py`
- `scripts/calibrar_scheduler_runtime_por_simbolo.py`
- `tests/unit/test_rl_scheduler_runtime_adapter.py`
- `tests/unit/test_rl_scheduler_symbol_calibration.py`
- `docs/BACKLOG.md` (BLID-066)

---

## ADR-047: Gate Manual de Promocao da Calibracao por Simbolo para Runtime (BLID-067)

**Data:** 2026-04-06
**Status:** APROVADO
**Decisores:** Product Owner, Tech Lead, ML Expert
**BLID:** BLID-067

### Contexto

O BLID-066 produziu replay e recomendacao por simbolo, mas faltava um mecanismo
formal para promover essa recomendacao ao runtime real com governanca.

Sem gate manual, o processo ficava dependente de ajuste de codigo ou alteracao
ad-hoc de thresholds, elevando risco operacional.

### Decisao

Implementar gate manual de promocao com tres componentes:

- validacao de criterios minimos por simbolo (`WIN` e `WDO`):
  - cobertura minima de cenarios;
  - acuracia minima no replay;
- promocao para arquivo runtime versionado em disco:
  - `data/scheduler/symbol_calibration_runtime.json`;
- consumo automatico pelo adaptador runtime com fallback:
  - se arquivo ausente/invalido, usar calibracao embutida segura.

O gate registra decisao em `outputs/scheduler_symbol_promotion_*.json` para
rastreabilidade operacional.

### Consequencias

**Positivas:**
- elimina necessidade de deploy de codigo para promover calibracao;
- adiciona trilha auditavel de aprovacao/reprovacao;
- mantém robustez: runtime continua operando com fallback seguro.

**Riscos:**
- gate manual pode atrasar promocao em dias de alta volatilidade;
- criterios de aprovacao podem precisar ajuste com ganho de historico.

### Evidencias

- `pytest tests/unit/test_rl_scheduler_runtime_adapter.py tests/unit/test_rl_scheduler_symbol_calibration.py tests/unit/test_rl_scheduler_calibration_promotion.py tests/unit/test_rl_retrain_scheduler.py -q` -> **50/50 PASSING**
- `mypy --strict src/application/rl_scheduler_runtime_adapter.py src/application/rl_scheduler_symbol_calibration.py src/application/rl_scheduler_calibration_promotion.py tests/unit/test_rl_scheduler_runtime_adapter.py tests/unit/test_rl_scheduler_symbol_calibration.py tests/unit/test_rl_scheduler_calibration_promotion.py` -> **0 erros**
- `python -m py_compile scripts/calibrar_scheduler_runtime_por_simbolo.py scripts/promover_calibracao_scheduler_runtime.py src/application/rl_scheduler_calibration_promotion.py` -> **OK**
- `python scripts/promover_calibracao_scheduler_runtime.py --approver operador_blid067` -> **APROVADO**

### Avaliacao de Impacto nos 5 Launchers

| Launcher | Impacto | Tipo | Acao Operacional |
|----------|---------|------|-----------------|
| INICIAR_AGENTE_RL_5000.bat | ALTO | DIRETO | Aplicar calibracao promovida automaticamente e monitorar estabilidade |
| INICIAR_AGENTE_RL_DIRETO.bat | ALTO | DIRETO | Aplicar calibracao promovida automaticamente e monitorar estabilidade |
| INICIAR_DIARIOS.bat | BAIXO | INDIRETO | Consolidar resultado do gate no fechamento |
| INICIAR_MICRO_TENDENCIA_AUTO_TRADE.bat | BAIXO | INDIRETO | Sem alteracao direta de runtime |
| INICIAR_MONITOR_QUANTICO.bat | MEDIO | INDIRETO | Exibir status de promocao (aprovado/reprovado) |

### Referencias

- `src/application/rl_scheduler_runtime_adapter.py`
- `src/application/rl_scheduler_calibration_promotion.py`
- `scripts/promover_calibracao_scheduler_runtime.py`
- `tests/unit/test_rl_scheduler_runtime_adapter.py`
- `tests/unit/test_rl_scheduler_calibration_promotion.py`
- `docs/BACKLOG.md` (BLID-067)

---

## ADR-048: Observabilidade do Gate de Promocao no Monitor Quantico (BLID-068)

**Data:** 2026-04-06
**Status:** APROVADO
**Decisores:** Product Owner, Tech Lead, ML Expert
**BLID:** BLID-068

### Contexto

O gate manual de promocao (ADR-047) passou a gerar artefatos de aprovacao/
reprovacao, mas o status ainda nao estava visivel no monitor operacional em
tempo real.

Sem essa visibilidade, bloqueios de promocao podiam passar despercebidos
durante a sessao.

### Decisao

Integrar no `monitor_quantico_tendencia.py` a leitura do ultimo artefato
`scheduler_symbol_promotion_*.json` e publicar no payload HTTP `/dados` um
bloco dedicado `scheduler_symbol_promotion`.

O leitor foi implementado em modo resiliente:
- nao propaga excecoes;
- classifica estados de ausencia/invalidez de artefato;
- informa se o arquivo runtime promovido esta presente.

### Consequencias

**Positivas:**
- eleva observabilidade operacional do ciclo "replay -> gate -> promocao";
- acelera resposta a bloqueios de promocao;
- melhora rastreabilidade entre monitor e artefatos de runtime.

**Riscos:**
- depende da disciplina de geracao dos artefatos em `outputs/`;
- sem realce visual no HTML, o operador ainda precisa consultar o JSON bruto.

### Evidencias

- `pytest tests/unit/test_monitor_quantico.py tests/unit/test_rl_scheduler_runtime_adapter.py tests/unit/test_rl_scheduler_calibration_promotion.py tests/unit/test_rl_scheduler_symbol_calibration.py tests/unit/test_rl_retrain_scheduler.py -q` -> **96/96 PASSING**
- `mypy --strict --explicit-package-bases scripts/monitor_quantico_tendencia.py tests/unit/test_monitor_quantico.py src/application/rl_scheduler_runtime_adapter.py src/application/rl_scheduler_calibration_promotion.py tests/unit/test_rl_scheduler_runtime_adapter.py tests/unit/test_rl_scheduler_calibration_promotion.py` -> **0 erros**
- `python -m py_compile scripts/monitor_quantico_tendencia.py` -> **OK**

### Avaliacao de Impacto nos 5 Launchers

| Launcher | Impacto | Tipo | Acao Operacional |
|----------|---------|------|-----------------|
| INICIAR_AGENTE_RL_5000.bat | BAIXO | INDIRETO | Sem mudanca de execucao; observar status de promocao no monitor |
| INICIAR_AGENTE_RL_DIRETO.bat | BAIXO | INDIRETO | Sem mudanca de execucao; observar status de promocao no monitor |
| INICIAR_DIARIOS.bat | BAIXO | INDIRETO | Consolidar o estado do gate no fechamento |
| INICIAR_MICRO_TENDENCIA_AUTO_TRADE.bat | BAIXO | INDIRETO | Sem impacto direto |
| INICIAR_MONITOR_QUANTICO.bat | ALTO | DIRETO | Exibir status e motivo do gate de promocao em runtime |

### Referencias

- `scripts/monitor_quantico_tendencia.py`
- `tests/unit/test_monitor_quantico.py`
- `src/application/rl_scheduler_calibration_promotion.py`
- `outputs/scheduler_symbol_promotion_*.json`
- `docs/BACKLOG.md` (BLID-068)

---

## ADR-049: Alerta Visual de Promocao no Monitor Quantico HTML (BLID-069)

**Data:** 2026-04-06
**Status:** APROVADO
**Decisores:** Product Owner, Tech Lead, ML Expert
**BLID:** BLID-069

### Contexto

O BLID-068 inseriu o status da promocao no payload do monitor, mas ainda faltava
um destaque visual no HTML para leitura operacional imediata.

Sem elemento visual dedicado, operadores poderiam ignorar bloqueios de promocao
durante a sessao.

### Decisao

Adicionar no `outputs/monitor_quantico.html` um card dedicado ao gate de
promocao com tres estados visuais:

- `promocao--aprovado` (verde);
- `promocao--reprovado` (vermelho);
- `promocao--atencao` (amarelo para `sem_promocao` e outros estados de alerta).

O card foi integrado ao render principal por meio de
`renderizarPromocaoScheduler(...)`, lendo `scheduler_symbol_promotion` do
payload recebido.

### Consequencias

**Positivas:**
- melhora tempo de resposta operacional a bloqueios;
- reduz chance de operar sem calibracao promovida;
- reforca visibilidade do ciclo "replay -> gate -> runtime".

**Riscos:**
- exige manter consistencia entre payload backend e IDs/classes do HTML;
- sem endpoint resumido em `/status`, automacoes externas ainda consultam `/dados`.

### Evidencias

- `pytest tests/unit/test_monitor_quantico.py tests/unit/test_monitor_quantico_html.py tests/unit/test_rl_scheduler_runtime_adapter.py tests/unit/test_rl_scheduler_calibration_promotion.py tests/unit/test_rl_scheduler_symbol_calibration.py tests/unit/test_rl_retrain_scheduler.py -q` -> **97/97 PASSING**
- `mypy --strict --explicit-package-bases scripts/monitor_quantico_tendencia.py tests/unit/test_monitor_quantico.py tests/unit/test_monitor_quantico_html.py src/application/rl_scheduler_runtime_adapter.py src/application/rl_scheduler_calibration_promotion.py tests/unit/test_rl_scheduler_runtime_adapter.py tests/unit/test_rl_scheduler_calibration_promotion.py` -> **0 erros**
- `python -m py_compile scripts/monitor_quantico_tendencia.py` -> **OK**

### Avaliacao de Impacto nos 5 Launchers

| Launcher | Impacto | Tipo | Acao Operacional |
|----------|---------|------|-----------------|
| INICIAR_AGENTE_RL_5000.bat | BAIXO | INDIRETO | Consultar sinal visual antes de promover ajuste por simbolo |
| INICIAR_AGENTE_RL_DIRETO.bat | BAIXO | INDIRETO | Consultar sinal visual antes de promover ajuste por simbolo |
| INICIAR_DIARIOS.bat | BAIXO | INDIRETO | Registrar status visual no fechamento |
| INICIAR_MICRO_TENDENCIA_AUTO_TRADE.bat | BAIXO | INDIRETO | Sem impacto direto |
| INICIAR_MONITOR_QUANTICO.bat | ALTO | DIRETO | Passa a exibir alerta visual de bloqueio de promocao |

### Referencias

- `outputs/monitor_quantico.html`
- `scripts/monitor_quantico_tendencia.py`
- `tests/unit/test_monitor_quantico.py`
- `tests/unit/test_monitor_quantico_html.py`
- `docs/BACKLOG.md` (BLID-069)

---

## ADR-050: Contrato Enxuto de Health-Check em /status com Resumo do Gate de Promocao (BLID-070)

**Data:** 2026-04-06
**Status:** APROVADO
**Decisores:** Product Owner, Tech Lead, ML Expert
**BLID:** BLID-070

### Contexto

Após BLID-069, o monitor passou a exibir visualmente o status da promoção, mas
automações de health-check ainda precisavam consumir o payload completo `/dados`.

Isso aumentava acoplamento e custo de parsing para verificações operacionais.

### Decisao

Evoluir o endpoint `/status` para expor resumo do gate de promoção:

- `ok`
- `ultima_atualizacao`
- `scheduler_symbol_promotion`:
  - `status`
  - `aprovado`
  - `runtime_config_presente`
  - `motivo`

Foi introduzido o helper `_build_status_payload()` para manter contrato único e
testável. O helper prioriza cache local e usa fallback para leitura dos
artefatos quando necessário.

### Consequencias

**Positivas:**
- reduz custo de integração de health-check;
- aumenta robustez de observabilidade operacional;
- mantém compatibilidade com consumidores existentes de `/status`.

**Riscos:**
- duplicidade semântica entre `/dados` e `/status` requer disciplina de contrato;
- monitor externo pode interpretar estado stale se cache local estiver atrasado.

### Evidencias

- `pytest tests/unit/test_monitor_quantico.py tests/unit/test_monitor_quantico_html.py tests/unit/test_rl_scheduler_runtime_adapter.py tests/unit/test_rl_scheduler_calibration_promotion.py tests/unit/test_rl_scheduler_symbol_calibration.py tests/unit/test_rl_retrain_scheduler.py -q` -> **99/99 PASSING**
- `mypy --strict --explicit-package-bases scripts/monitor_quantico_tendencia.py tests/unit/test_monitor_quantico.py tests/unit/test_monitor_quantico_html.py src/application/rl_scheduler_runtime_adapter.py src/application/rl_scheduler_calibration_promotion.py tests/unit/test_rl_scheduler_runtime_adapter.py tests/unit/test_rl_scheduler_calibration_promotion.py` -> **0 erros**
- `python -m py_compile scripts/monitor_quantico_tendencia.py` -> **OK**

### Avaliacao de Impacto nos 5 Launchers

| Launcher | Impacto | Tipo | Acao Operacional |
|----------|---------|------|-----------------|
| INICIAR_AGENTE_RL_5000.bat | BAIXO | INDIRETO | Permite health-check externo mais simples |
| INICIAR_AGENTE_RL_DIRETO.bat | BAIXO | INDIRETO | Permite health-check externo mais simples |
| INICIAR_DIARIOS.bat | BAIXO | INDIRETO | Pode ler /status para consolidacao leve |
| INICIAR_MICRO_TENDENCIA_AUTO_TRADE.bat | BAIXO | INDIRETO | Sem impacto direto |
| INICIAR_MONITOR_QUANTICO.bat | MEDIO | DIRETO | /status passa a refletir estado operacional do gate |

### Referencias

- `scripts/monitor_quantico_tendencia.py`
- `tests/unit/test_monitor_quantico.py`
- `outputs/monitor_quantico.html`
- `docs/BACKLOG.md` (BLID-070)

---

## ADR-051: Guard Automatizado para Bloqueio de Janela por Status de Promocao (BLID-071)

**Data:** 2026-04-06
**Status:** APROVADO
**Decisores:** Product Owner, Tech Lead, ML Expert
**BLID:** BLID-071

### Contexto

Com BLID-070, o endpoint `/status` passou a expor resumo do gate de promoção.
Ainda faltava um mecanismo automatizado para transformar esse status em decisão
operacional de bloqueio/liberação de janela.

### Decisao

Criar check automatizado (`script/CI`) com contrato simples:

- entrada:
  - URL de status (default `http://localhost:8765/status`) ou
  - arquivo de snapshot JSON;
- regra padrão:
  - falhar quando `scheduler_symbol_promotion.status == reprovado`;
- saída:
  - log textual/JSON;
  - exit code padronizado (`0` ok, `2` bloqueado).

### Consequencias

**Positivas:**
- operacionaliza o gate de promoção para automações;
- reduz risco de iniciar sessão com promoção reprovada;
- facilita integração com CI e pre-flight local.

**Riscos:**
- endpoint indisponível pode exigir fallback por arquivo;
- regra de bloqueio pode precisar endurecimento futuro para `sem_promocao`.

### Evidencias

- `pytest tests/unit/test_scheduler_promotion_healthcheck.py tests/unit/test_monitor_quantico.py tests/unit/test_monitor_quantico_html.py tests/unit/test_rl_scheduler_runtime_adapter.py tests/unit/test_rl_scheduler_calibration_promotion.py tests/unit/test_rl_scheduler_symbol_calibration.py tests/unit/test_rl_retrain_scheduler.py -q` -> **103/103 PASSING**
- `mypy --strict --explicit-package-bases src/application/scheduler_promotion_healthcheck.py scripts/check_scheduler_promotion_gate.py scripts/monitor_quantico_tendencia.py tests/unit/test_scheduler_promotion_healthcheck.py tests/unit/test_monitor_quantico.py tests/unit/test_monitor_quantico_html.py src/application/rl_scheduler_runtime_adapter.py src/application/rl_scheduler_calibration_promotion.py tests/unit/test_rl_scheduler_runtime_adapter.py tests/unit/test_rl_scheduler_calibration_promotion.py` -> **0 erros**
- `python -m py_compile scripts/check_scheduler_promotion_gate.py src/application/scheduler_promotion_healthcheck.py scripts/monitor_quantico_tendencia.py` -> **OK**
- `python scripts/check_scheduler_promotion_gate.py --status-file outputs/tmp_status_reprovado.json` -> **exit code 2**

### Avaliacao de Impacto nos 5 Launchers

| Launcher | Impacto | Tipo | Acao Operacional |
|----------|---------|------|-----------------|
| INICIAR_AGENTE_RL_5000.bat | MEDIO | INDIRETO | Pode adicionar pre-flight que bloqueia em `reprovado` |
| INICIAR_AGENTE_RL_DIRETO.bat | MEDIO | INDIRETO | Pode adicionar pre-flight que bloqueia em `reprovado` |
| INICIAR_DIARIOS.bat | BAIXO | INDIRETO | Pode registrar resultado do check em trilha operacional |
| INICIAR_MICRO_TENDENCIA_AUTO_TRADE.bat | BAIXO | INDIRETO | Sem impacto direto |
| INICIAR_MONITOR_QUANTICO.bat | MEDIO | DIRETO | Fornece status consumível para o check |

### Referencias

- `src/application/scheduler_promotion_healthcheck.py`
- `scripts/check_scheduler_promotion_gate.py`
- `scripts/monitor_quantico_tendencia.py`
- `tests/unit/test_scheduler_promotion_healthcheck.py`
- `docs/BACKLOG.md` (BLID-071)

---

## ADR-052: Enforcement do Gate de Promocao no Pre-flight dos Launchers RL (BLID-072)

**Data:** 2026-04-06
**Status:** APROVADO
**Decisores:** Product Owner, Tech Lead, ML Expert
**BLID:** BLID-072

### Contexto

O BLID-071 criou o check automatizado, mas ele ainda nao estava integrado aos
launchers operacionais dos agentes RL. Sem enforcement no pre-flight, o bloqueio
continuava dependente de disciplina manual.

### Decisao

Integrar `check_scheduler_promotion_gate.py` no pre-flight de:

- `INICIAR_AGENTE_RL_5000.bat`
- `INICIAR_AGENTE_RL_DIRETO.bat`

Regra aplicada:
- bloquear launch quando status for `reprovado` (exit code != 0).

Para robustez operacional, foi adotado fallback:
- tentativa principal via endpoint `/status`;
- fallback para ultimo artefato local `scheduler_symbol_promotion_*.json`.

### Consequencias

**Positivas:**
- enforcement real do gate na borda operacional;
- reduz risco de operar com promocao reprovada;
- mantem continuidade em cenarios de indisponibilidade temporaria do monitor.

**Riscos:**
- pode bloquear inicio em ambiente sem artefatos e sem monitor;
- requer manutencao do contrato CLI no script de check.

### Evidencias

- `pytest tests/unit/test_scheduler_promotion_healthcheck.py tests/unit/test_rl_5000_launcher_contract.py tests/unit/test_rl_direto_launcher_contract.py tests/unit/test_monitor_quantico.py tests/unit/test_monitor_quantico_html.py tests/unit/test_rl_scheduler_runtime_adapter.py tests/unit/test_rl_scheduler_calibration_promotion.py tests/unit/test_rl_scheduler_symbol_calibration.py tests/unit/test_rl_retrain_scheduler.py -q` -> **106/106 PASSING**
- `mypy --strict --explicit-package-bases src/application/scheduler_promotion_healthcheck.py scripts/check_scheduler_promotion_gate.py scripts/monitor_quantico_tendencia.py tests/unit/test_scheduler_promotion_healthcheck.py tests/unit/test_rl_5000_launcher_contract.py tests/unit/test_rl_direto_launcher_contract.py tests/unit/test_monitor_quantico.py tests/unit/test_monitor_quantico_html.py src/application/rl_scheduler_runtime_adapter.py src/application/rl_scheduler_calibration_promotion.py tests/unit/test_rl_scheduler_runtime_adapter.py tests/unit/test_rl_scheduler_calibration_promotion.py` -> **0 erros**
- `python -m py_compile scripts/check_scheduler_promotion_gate.py src/application/scheduler_promotion_healthcheck.py scripts/monitor_quantico_tendencia.py` -> **OK**

### Avaliacao de Impacto nos 5 Launchers

| Launcher | Impacto | Tipo | Acao Operacional |
|----------|---------|------|-----------------|
| INICIAR_AGENTE_RL_5000.bat | ALTO | DIRETO | Pre-flight passa a bloquear em `reprovado` |
| INICIAR_AGENTE_RL_DIRETO.bat | ALTO | DIRETO | Pre-flight passa a bloquear em `reprovado` |
| INICIAR_DIARIOS.bat | BAIXO | INDIRETO | Pode reaproveitar check em compliance |
| INICIAR_MICRO_TENDENCIA_AUTO_TRADE.bat | BAIXO | INDIRETO | Sem impacto direto |
| INICIAR_MONITOR_QUANTICO.bat | MEDIO | INDIRETO | Continua fonte online de status para o check |

### Referencias

- `INICIAR_AGENTE_RL_5000.bat`
- `INICIAR_AGENTE_RL_DIRETO.bat`
- `src/application/scheduler_promotion_healthcheck.py`
- `scripts/check_scheduler_promotion_gate.py`
- `tests/unit/test_rl_5000_launcher_contract.py`
- `tests/unit/test_rl_direto_launcher_contract.py`
- `docs/BACKLOG.md` (BLID-072)

---

## ADR-053: Enforcement do Gate de Promocao no Pipeline de Release/CI (BLID-073)

**Data:** 2026-04-06
**Status:** APROVADO
**Decisores:** Product Owner, Tech Lead, ML Expert
**BLID:** BLID-073

### Contexto

Com BLID-072, o gate de promocao passou a bloquear os launchers RL no pre-flight
local. Faltava fechar o mesmo guardrail na esteira de release/CI para impedir
autorizacao de deploy quando o status estivesse `reprovado`.

### Decisao

Aplicar o gate de promocao em duas camadas da esteira:

- **Camada de release gate (BL-08):**
  - `OperationalUATService` passa a executar o check
    `scheduler_promotion_gate`;
  - bloquear quando `scheduler_symbol_promotion.status == reprovado`;
  - manter fallback seguro para `sem_promocao` na ausencia de artefato local.
- **Camada de workflow CI:**
  - novo job `promotion-gate-check` no workflow principal
    `.github/workflows/ci-cd-pipeline.yml`;
  - `deploy-staging` depende explicitamente desse job;
  - workflow `.github/workflows/tests.yml` inclui etapa obrigatoria
    `Gate de promocao antes do deploy`.

### Consequencias

**Positivas:**
- reduz risco de promover release com calibracao reprovada;
- unifica contrato de decisao entre pre-flight local e CI;
- aumenta rastreabilidade do gate em artefatos de release.

**Riscos:**
- ambientes sem artefato e sem endpoint podem exigir fallback controlado;
- endurecimento futuro para `sem_promocao` pode elevar taxa de bloqueio.

### Evidencias

- `pytest tests/unit/test_release_gates.py tests/unit/test_scheduler_promotion_healthcheck.py tests/unit/test_validate_go_live_gates.py -q` -> **21/21 PASSING**
- `python scripts/check_scheduler_promotion_gate.py --fallback-latest-promotion --fail-on reprovado --json-output` -> **OK (exit code 0)**

### Avaliacao de Impacto nos 5 Launchers

| Launcher | Impacto | Tipo | Acao Operacional |
|----------|---------|------|-----------------|
| INICIAR_AGENTE_RL_5000.bat | ALTO | DIRETO | Deploy/release bloqueia quando promocao estiver `reprovado` |
| INICIAR_AGENTE_RL_DIRETO.bat | ALTO | DIRETO | Deploy/release bloqueia quando promocao estiver `reprovado` |
| INICIAR_DIARIOS.bat | BAIXO | INDIRETO | Pode consumir evidencia do gate em trilha de compliance |
| INICIAR_MICRO_TENDENCIA_AUTO_TRADE.bat | BAIXO | INDIRETO | Sem impacto direto |
| INICIAR_MONITOR_QUANTICO.bat | MEDIO | INDIRETO | Mantem endpoint/status como fonte de verdade para o gate |

### Referencias

- `src/application/release_gates.py`
- `tests/unit/test_release_gates.py`
- `.github/workflows/ci-cd-pipeline.yml`
- `.github/workflows/tests.yml`
- `scripts/check_scheduler_promotion_gate.py`
- `docs/BACKLOG.md` (BLID-073)

---

## ADR-054: Gate Estrito de Promocao no Release/CI (BLID-074)

**Data:** 2026-04-06
**Status:** APROVADO
**Decisores:** Product Owner, Tech Lead, ML Expert
**BLID:** BLID-074

### Contexto

O BLID-073 integrou o gate de promocao ao release/CI, mas mantinha
`sem_promocao` como estado tolerado. Isso permitia autorizacao de deploy sem
evidencia clara de promocao valida por simbolo.

### Decisao

Endurecer o gate para modo estrito em release:

- considerar bloqueadores:
  - `reprovado`
  - `sem_promocao`
- aplicar em:
  - `OperationalUATService` (BL-08)
  - workflows CI (`ci-cd-pipeline.yml` e `tests.yml`)

### Consequencias

**Positivas:**
- reduz risco de promover versao sem calibracao/promocao confirmada;
- reforca guardrail de risco alinhado ao lema "Eu aprendo operando";
- melhora disciplina de rollout por simbolo.

**Riscos:**
- maior chance de bloqueio em ambientes sem monitor/artefato atualizado;
- exige governanca de janela operacional para estados transitórios.

### Evidencias

- `pytest tests/unit/test_release_gates.py tests/unit/test_scheduler_promotion_healthcheck.py tests/unit/test_validate_go_live_gates.py -q` -> **22/22 PASSING**
- `python scripts/check_scheduler_promotion_gate.py --fallback-latest-promotion --fail-on reprovado,sem_promocao --json-output` -> **bloqueio esperado em `sem_promocao`**

### Avaliacao de Impacto nos 5 Launchers

| Launcher | Impacto | Tipo | Acao Operacional |
|----------|---------|------|-----------------|
| INICIAR_AGENTE_RL_5000.bat | ALTO | DIRETO | Deploy so autorizado com promocao valida (nao `sem_promocao`) |
| INICIAR_AGENTE_RL_DIRETO.bat | ALTO | DIRETO | Deploy so autorizado com promocao valida (nao `sem_promocao`) |
| INICIAR_DIARIOS.bat | BAIXO | INDIRETO | Pode validar prontidao de promocao antes de consolidar sessao |
| INICIAR_MICRO_TENDENCIA_AUTO_TRADE.bat | BAIXO | INDIRETO | Sem impacto direto |
| INICIAR_MONITOR_QUANTICO.bat | MEDIO | INDIRETO | Disponibilidade de status/artefato vira precondicao de release |

### Referencias

- `src/application/release_gates.py`
- `tests/unit/test_release_gates.py`
- `.github/workflows/ci-cd-pipeline.yml`
- `.github/workflows/tests.yml`
- `scripts/check_scheduler_promotion_gate.py`
- `docs/BACKLOG.md` (BLID-074)



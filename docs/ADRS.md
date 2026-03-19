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


## Canonical Docs Policy

From this update onward, the canonical docs set is:

- `docs/ADRS.md` (this file, case-insensitive with `ADRS.md` on Windows)
- `docs/ARQUITETURA_ALVO.md`
- `docs/BACKLOG.md`
- `docs/DIAGRAMAS.md`
- `docs/MODELAGEM_DE_DADOS.md`
- `docs/REGRAS_DE_NEGOCIO.md`

Legacy docs remain read-only for historical traceability.

**Estado Atual:** as trilhas principais e o runtime bridge do fluxo diario ja
estao implementados; a validacao operacional final segue em staging, UAT e Gate 2.

⭐ **CORE DO PRODUTO**: As decisões arquiteturais aqui registradas foram tomadas para suportar a execução eficiente de:

- [INICIAR_DIARIOS.bat](../INICIAR_DIARIOS.bat)
- [INICIAR_MICRO_TENDENCIA_AUTO_TRADE.bat](../INICIAR_MICRO_TENDENCIA_AUTO_TRADE.bat)
- [INICIAR_AGENTE_RL_5000.bat](../INICIAR_AGENTE_RL_5000.bat)
- [INICIAR_AGENTE_RL_5000_FIXED.bat](../INICIAR_AGENTE_RL_5000_FIXED.bat)

---

## O que é ADR?

**ADR (Architecture Decision Record)** é um documento que captura uma decisão arquitetural importante junto com:
- **Contexto**: Por que a decisão foi necessária?
- **Decisão**: Qual foi a escolha?
- **Consequências**: Quais são os trade-offs?
- **Status**: PROPOSED, ACCEPTED, DEPRECATED, SUPERSEDED

---

## ADR-001: Por que SQLite vs PostgreSQL como BD Primário?

**Status**: ✅ ACCEPTED
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
- 🚀 [docs/deliverables/p0-1/P0_1_INTEGRATION_GUIDE.md](docs/legacy/deliverables/p0-1/P0_1_INTEGRATION_GUIDE.md) - Integration guide
- 🧪 [scripts/test_p0_1_integration.py](scripts/test_p0_1_integration.py) - Test suite
- 📋 [BACKLOG.md § P0-1](docs/legacy/ BACKLOG.md) - Delivery metrics

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

**Audit Report**: [outputs/audits/AUDITORIA_MT5_ISOLAMENTO_04Mar.md](docs/legacy/../outputs/audits/AUDITORIA_MT5_ISOLAMENTO_04Mar.md)

**Documentação**:
- 📄 [ARQUITETURA_ALVO.md § 4.5](ARQUITETURA_ALVO.md#45-terminal-isolation-enforcer-s2-6---novo--implementado-04032026)
- 🚀 [QUICK_START.md § Isolamento](docs/legacy/QUICK_START.md#-configuração-de-isolamento-de-terminal-importante)
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

**4. Test Suite** (`scripts/test_p0_1_integration.py` - 320 LOC)
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
| Launcher Imports | ✅ PASS | `python scripts/test_p0_1_integration.py` → 5/5 testes |

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
- 🚀 **[GO_LIVE_CHECKLIST.md § P0-1](docs/legacy/GO_LIVE_CHECKLIST.md#-p0-1-rest-api-gateway-validation-novo---0403)** - Validação pré-produção
- 💾 **[DIAGRAMAS.md](DIAGRAMAS.md)** - SQL schema (api_orders, api_audit_log)
- 📦 **[docs/deliverables/p0-1/](docs/deliverables/p0-1/)** - 8 documentos detalhados

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
- 🧪 **[tests/test_p50_full.py](tests/test_p50_full.py)** - 11 test cases validando todas as 3 camadas
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
# tests/unit/test_terminal_fallback_behavior.py

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

3. **`tests/unit/test_terminal_fallback_behavior.py`** (NOVO - 220 LOC)
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
- [ ] `tests/unit/test_terminal_fallback_behavior.py` com 4 test cases
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
- 🧪 **[tests/unit/test_terminal_fallback_behavior.py](tests/unit/test_terminal_fallback_behavior.py)** - Test suite
- 🔧 **[config/settings.py](config/settings.py#MT5Config)** - Config validation

### Next ADRs

- **ADR-017**: Terminal fallback strategies for Phase 2 (AWS failover, load balancing)
- **ADR-018**: Multi-environment config (dev, staging, prod terminals)

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

---

**Last Updated:** 18/03/2026 BRT
**Total ADRs:** 16
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

**ÚLTIMA ATUALIZAÇÃO:** 17/03/2026 BRT | **STATUS**: ✅ GRUPO 2 INTEGRADO

```


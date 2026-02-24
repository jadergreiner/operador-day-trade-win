# Monitor Operador Integrado v2.0 - Arquitetura Visual

## 🏗️ Diagrama de Integração

```
┌──────────────────────────────────────────────────────────────────────────┐
│                        OPERADOR AUTO-TRADE FLOW                          │
│                   (INICIAR_MICRO_TENDENCIA_AUTO_TRADE.py)                │
├──────────────────────────────────────────────────────────────────────────┤
│                                                                          │
│  1. EXECUTE TRADE                                                       │
│     ↓                                                                    │
│     operador.on_trade_executed(symbol, action, decision, price)        │
│     ↓                                                                    │
│  2. ANALYTICS ADAPTER (OperadorComAnalytics wrapper)                   │
│     ↓                                                                    │
│     adapter.log_intervention(TradeEvent)                               │
│     ↓                                                                    │
│  3. S2-6 ANALYTICS API (POST /api/intervention/log)                    │
│     ↓  Returns: intervention_id                                         │
│  4. TRADE CLOSES (WIN/LOSS/PARTIAL)                                    │
│     ↓                                                                    │
│     operador.on_trade_closed(symbol, p_and_l, result)                  │
│     ↓                                                                    │
│  5. UPDATE RESULT (AnalyticsAdapter.update_result)                     │
│     ↓                                                                    │
│     POST /api/intervention/{id}/result → (result, p_and_l)             │
│     ↓                                                                    │
│  6. DATA PERSISTED in SQLite / PostgreSQL                              │
│                                                                          │
└──────────────────────────────────────────────────────────────────────────┘
                                    ↓ (Every 5 seconds)
┌──────────────────────────────────────────────────────────────────────────┐
│              MONITOR OPERADOR INTEGRADO v2.0 (Real-time)                │
│                      (MONITOR_OPERADOR.bat [1])                         │
├──────────────────────────────────────────────────────────────────────────┤
│                                                                          │
│  ┌─── SEÇÃO 1: OPERADOR STATUS ────────────────────────────────┐       │
│  │  [OPERADOR DE EXECUÇÃO] Status geral + componentes          │       │
│  │  - API Server: [LIVE] 8001                                  │       │
│  │  - MT5 Connection: [ACTIVE]                                 │       │
│  │  - Risk Validators: [READY]                                 │       │
│  └─────────────────────────────────────────────────────────────┘       │
│                                                                          │
│  ┌─── SEÇÃO 2: S2-6 ANALYTICS (GET /api/analytics/stats) ────┐       │
│  │  [✓] S2-6 Analytics ONLINE                                  │       │
│  │  - Total Interventions: 157                                 │       │
│  │  - Win Rate: 64.33% 🟢                                      │       │
│  │  - P&L Total: R$ 18.750,00 🟢                              │       │
│  │  - Avg Ticket: R$ 119,43                                    │       │
│  │  - Top 5 Symbols:                                           │       │
│  │    WDOIT    → 45 ops | WR: 65% | PnL: R$ 8.500             │       │
│  │    WINFUT   → 38 ops | WR: 61% | PnL: R$ 5.200             │       │
│  └─────────────────────────────────────────────────────────────┘       │
│                                                                          │
│  ┌─── SEÇÃO 3: ACTION BREAKDOWN ───────────────────────────────┐       │
│  │  [EXECUTE]       Executar Ordem           → 89x             │       │
│  │  [OVERRIDE]      Override Manual          → 45x             │       │
│  │  [PAUSE]         Pausar Operação          → 12x             │       │
│  │  [CANCEL]        Cancelar Ordem           → 4x              │       │
│  └─────────────────────────────────────────────────────────────┘       │
│                                                                          │
│  ┌─── SEÇÃO 4: ÚLTIMAS OPERAÇÕES (Recent 10) ─────────────────┐       │
│  │  1. 14:32:30 | WDOIT | EXECUTE | 🟢 WIN | +R$ 150,00      │       │
│  │  2. 14:31:45 | WINFUT| OVERRIDE| 🟢 WIN | +R$ 120,50      │       │
│  │  3. 14:30:22 | MDIA3 | EXECUTE | 🔴 LOSS| -R$ 45,20       │       │
│  │  ...                                                          │       │
│  └─────────────────────────────────────────────────────────────┘       │
│                                                                          │
│  ┌─── SEÇÃO 5: RISK VALIDATORS ────────────────────────────────┐       │
│  │  🟢 ATIVO Gate 1: Capital Adequacy                          │       │
│  │  🟢 ATIVO Gate 2: Correlation Check                         │       │
│  │  🟢 ATIVO Gate 3: Volatility Band                           │       │
│  │  🟢 MONITORANDO Circuit Breaker (-3%)                       │       │
│  └─────────────────────────────────────────────────────────────┘       │
│                                                                          │
│  [UPDATE CYCLE] Cada 5 segundos:                                        │
│  GET /api/analytics/stats → Render dashboard                           │
│                                                                          │
└──────────────────────────────────────────────────────────────────────────┘
```

---

## 🔌 Stack Técnico

```
CAMADA DE APRESENTAÇÃO
┌─────────────────────────────────────────────────────────────┐
│ Terminal Console (Windows PowerShell / Bash)                │
│   │                                                          │
│   ├─ MONITOR_OPERADOR.bat (Menu)                           │
│   │    ├─ [1] monitor_operador_integrado.py               │
│   │    ├─ [2] monitor_s2_6_dashboard.py                   │
│   │    └─ [3] deploy_status.json parser                    │
│   │                                                          │
└─────────────────────────────────────────────────────────────┘
                            ↓
CAMADA DE LÓGICA
┌─────────────────────────────────────────────────────────────┐
│ Monitor Classes (Python)                                     │
│                                                              │
│ MonitorOperadorIntegrado                                    │
│   - _load_operador_status()          [operador state]       │
│   - _format_operador_status()        [render section]       │
│   - _format_analytics_stats()        [S2-6 section]        │
│   - _format_action_breakdown()       [actions section]      │
│   - _format_recent_trades()          [timeline section]     │
│   - _format_risk_validators()        [gates section]        │
│   - display()                        [main loop]            │
│                                                              │
│ MonitorS2_6Dashboard (variant)                              │
│   - Simplified version (analytics only)                     │
│   - Useful for dedicated analytics monitoring               │
│                                                              │
└─────────────────────────────────────────────────────────────┘
                            ↓
CAMADA DE ADAPTERS
┌─────────────────────────────────────────────────────────────┐
│ AnalyticsAdapter (Singleton, HTTP Client)                  │
│   - get_stats()           [GET /stats]                      │
│   - get_dashboard()       [GET /dashboard]                  │
│   - log_intervention()    [POST /log]                       │
│   - update_result()       [POST /{id}/result]               │
│   - health_check()        [GET /health]                     │
│                                                              │
│ File Reader                                                 │
│   - load_json(deployment_status.json)                       │
│                                                              │
└─────────────────────────────────────────────────────────────┘
                            ↓
CAMADA DE DADOS
┌─────────────────────────────────────────────────────────────┐
│ S2-6 Analytics API (FastAPI)                               │
│   - Base URL: http://localhost:8000                         │
│   - GET /api/analytics/stats                                │
│   - GET /api/analytics/dashboard                            │
│   - GET /health                                             │
│                                                              │
│ Operador Status File                                        │
│   - logs/deployment_status.json                             │
│     {                                                       │
│       "status": "LIVE",                                     │
│       "components": { "API": {...}, "MT5": {...} }         │
│     }                                                       │
│                                                              │
│ Backend Database                                            │
│   - SQLite: data/analytics_staging.db                       │
│   - PostgreSQL: analytics_prod (production)                 │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

---

## 🔄 Ciclo de Sincronização (Detalhado)

### Momento T0: Trade Executado
```python
# Em: scripts/agente_micro_tendencia_winfut.py
evento = {
    "symbol": "WDOIT",
    "action": "EXECUTE",
    "decision": "Sinal BDI + Confluence Bollinger",
    "entry_price": 125.50,
    "timestamp": datetime.now()
}
operador.on_trade_executed(**evento)
```

### Momento T1: Registrar em Analytics
```python
# Em: OperadorComAnalytics.on_trade_executed()
event = TradeEvent(
    symbol="WDOIT",
    action="EXECUTE",
    trader_decision="Sinal BDI + Confluence",
    p_and_l=0.0  # ainda não sabemos ganho/perda
)
intervention_id = adapter.log_intervention(event)
# Returns: intervention_id = 42
self.active_trades["WDOIT"] = intervention_id
```

### Momento T2: Analytics API persiste
```python
# Em: S2-6 Analytics API
POST /api/intervention/log
{
    "symbol": "WDOIT",
    "action": "EXECUTE",
    "trader_decision": "Sinal BDI + Confluence",
    "timestamp": "2026-02-24T14:32:30Z",
    "p_and_l": 0.0
}
# Resposta:
{
    "intervention_id": 42,
    "status": "created"
}
```

### Momento T3: Trade Fecha (30 min depois)
```python
# Em: scripts/agente_micro_tendencia_winfut.py (ou manual intervention)
trade_close = {
    "symbol": "WDOIT",
    "entry_price": 125.50,
    "exit_price": 126.70,
    "p_and_l_final": 150.00,  # (126.70 - 125.50) * 100
    "reason": "Take Profit (Bollinger Band Upper)"
}
operador.on_trade_closed(**trade_close)
```

### Momento T4: Atualizar Resultado
```python
# Em: OperadorComAnalytics.on_trade_closed()
intervention_id = self.active_trades.get("WDOIT")  # = 42
adapter.update_result(
    intervention_id=42,
    result="WIN",  # porque p_and_l > 0
    p_and_l=150.00
)
del self.active_trades["WDOIT"]
```

### Momento T5: Analytics API atualiza
```python
# Em: S2-6 Analytics API
POST /api/intervention/42/result
{
    "result": "WIN",
    "p_and_l": 150.00
}

# Atualiza DB:
UPDATE trader_interventions
SET result='WIN', p_and_l=150.00
WHERE intervention_id=42
```

### Momento T6: Monitor Carrega Stats (cada 5s)
```python
# Em: MonitorOperadorIntegrado.display() → _format_analytics_stats()
stats = adapter.get_stats()
# Returns:
{
    "total_interventions": 42,
    "win_rate": 0.6428,  # (27 wins / 42 total)
    "total_pnl": 6150.00,
    "avg_pnl": 146.42,
    "symbols": {
        "WDOIT": {
            "count": 12,
            "win_rate": 0.75,
            "total_pnl": 2100.00
        }
    },
    "actions": {
        "EXECUTE": 27,
        "OVERRIDE": 10,
        "PAUSE": 3,
        "CANCEL": 2
    },
    "recent_interventions": [
        {
            "timestamp": "2026-02-24T14:32:30Z",
            "symbol": "WDOIT",
            "action": "EXECUTE",
            "result": "WIN",
            "p_and_l": 150.00
        },
        ...
    ]
}
```

### Momento T7: Monitor Renderiza Dashboard
```
[S2-6 ANALYTICS] Estatísticas em Tempo Real
────────────────────────────────────────────────────
  [✓] S2-6 Analytics ONLINE
    └─ Total de Intervenções: 42
    └─ 🟢 Win Rate: 64.28%
    └─ 🟢 P&L Total: R$ 6.150,00
    └─ Ticket Médio: R$ 146,42

  Top Símbolos Monitorados:
    WDOIT    →  12ops | WR: 75.00% | 🟢 R$+2.100,00

[ÚLTIMAS OPERAÇÕES] Timeline Recente
────────────────────────────────────────────────────
  1. 14:32:30 | WDOIT  | EXECUTE | 🟢 WIN | +R$150,00
```

---

## 🎛️ Modos de Operação

### Modo 1: Monitor Integrado (RECOMENDADO)
```bash
MONITOR_OPERADOR.bat
[1]
```
**Exibe:**
- Operador status (1 seção)
- S2-6 analytics (4 seções)
- Total: 5 seções em um painel
- Ideal para: Visão holística da operação

### Modo 2: Analytics Dashboard (ISOLADO)
```bash
MONITOR_OPERADOR.bat
[2]
```
**Exibe:**
- Apenas S2-6 analytics
- Estatísticas, símbolos, ações, operações, saúde
- Ideal para: Traders focados 100% em analytics

### Modo 3: Status Operador (ISOLADO)
```bash
MONITOR_OPERADOR.bat
[3]
```
**Exibe:**
- Apenas status do operador
- Componentes (API, MT5, etc)
- Ideal para: Troubleshooting de operador

---

## 📊 Exemplo de Saída Completa

```
╔════════════════════════════════════════════════════════════════════════════╗
║           MONITOR OPERADOR INTEGRADO v2.0 - Operador Auto-Trade WIN        ║
║  Operador←→S2-6 Analytics | Governança ROADMAP: Sincronia 100% Tempo Real │
║  14:32:51.234 24/02/2026                                                  ║
╚════════════════════════════════════════════════════════════════════════════╝

[OPERADOR DE EXECUÇÃO] Status Geral
────────────────────────────────────────────────────────────────────────────
  [LIVE] LIVE

  Componentes Operacionais:
    [✓] WEBSOCKET SERVER
        └─ status: ACTIVE
        └─ port: 8001
    [✓] MT5 CONNECTION
        └─ status: READY
        └─ account: 333-456

[S2-6 ANALYTICS] Estatísticas em Tempo Real
────────────────────────────────────────────────────────────────────────────
  [✓] S2-6 Analytics ONLINE
    └─ Total de Intervenções: 157
    └─ 🟢 Win Rate: 64.33%
    └─ 🟢 P&L Total: R$ 18.750,00
    └─ Ticket Médio: R$ 119,43

  Top Símbolos Monitorados:
    WDOIT       →  57ops | WR: 67.00% | 🟢 R$+8.500,00
    WINFUT      →  38ops | WR: 63.00% | 🟢 R$+5.200,00
    MDIA3       →  35ops | WR: 60.00% | 🟢 R$+3.050,00
    PETR4       →  18ops | WR: 50.00% | 🟡 R$+1.200,00
    VALE3       →  9ops  | WR: 44.00% | 🔴 R$-200,00

[BREAKDOWN DE AÇÕES] Tipos de Intervenção
────────────────────────────────────────────────────────────────────────────
  [EXECUTE    ] Executar Ordem              → 89x
  [OVERRIDE   ] Override Manual             → 45x
  [PAUSE      ] Pausar Operação             → 12x
  [CANCEL     ] Cancelar Ordem              → 4x

[ÚLTIMAS OPERAÇÕES] Timeline Recente
────────────────────────────────────────────────────────────────────────────
  1. 14:32:30 | WDOIT   | EXECUTE    | 🟢 🟢 R$+150,00
  2. 14:31:45 | WINFUT  | OVERRIDE   | 🟢 🟢 R$+120,50
  3. 14:30:22 | MDIA3   | EXECUTE    | 🔴 🔴 R$-45,20
  4. 14:28:15 | WDOIT   | EXECUTE    | 🟢 🟡 R$+89,00
  5. 14:25:40 | PETR4   | OVERRIDE   | 🟡 🟢 R$+75,30
  6. 14:23:12 | WINFUT  | PAUSE      | 🔴 ⏳ R$0,00
  7. 14:20:55 | MDIA3   | EXECUTE    | 🟢 🟢 R$+200,50
  8. 14:18:30 | WDOIT   | CANCEL     | 🟡 ⏳ R$0,00

[RISK VALIDATORS] Gates de Segurança
────────────────────────────────────────────────────────────────────────────
  🟢 ATIVO Gate 1: Capital Adequacy
  🟢 ATIVO Gate 2: Correlation Check
  🟢 ATIVO Gate 3: Volatility Band
  🟢 MONITORANDO Circuit Breaker (-3%)
  🟢 PRONTO Circuit Breaker (-5%)
  🟢 PRONTO Circuit Breaker (-8%)

════════════════════════════════════════════════════════════════════════════
[STATUS] Sincronização: 100% | Atualização a cada 5s
[ATALHOS] Ctrl+C = Sair | Status = Operador | Analytics = S2-6 Dashboard
[LEGENDAS] 🟢=OK | 🟡=Atenção | 🔴=Crítico | ✓=Ativo | ✗=Inativo
════════════════════════════════════════════════════════════════════════════

** Digite Ctrl+C para encerrar... Dashboard atualiza a cada 5 segundos **
```

---

## ✅ Checklist de Validação

- [x] Monitor inicializa sem erros
- [x] Carrega status do operador (arquivo JSON)
- [x] Conecta com S2-6 Analytics API
- [x] Renderiza dashboard completo
- [x] Atualiza a cada 5 segundos
- [x] Trata API offline graciosamente
- [x] Trata arquivo corrompido graciosamente
- [x] Formatação de números (Win rate, P&L)
- [x] Cores e ícones Unicode
- [x] 100% em Português
- [x] Thread-safe (múltiplas leituras)
- [x] Resiliência a falhas
- [x] Testes de integração (20+ casos)
- [x] Documentação completa

---

**Status:** ✅ PRONTO PARA PRODUÇÃO | **Data:** 24/02/2026 | **Linguagem:** 100% PT-BR

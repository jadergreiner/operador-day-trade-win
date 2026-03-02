# S2-6: Analytics de Intervencao Manual

**Status:** MVP Skeleton Ready (27/02/2026)
**Completion:** 20% (design + structure)
**Target:** 100% by 28/02 EOD
**Owner:** Eng Sr

---

## 📋 Visao Geral

S2-6 é o modulo de analytics que monitora a operacao em tempo real com foco em:

1. **Dashboard em tempo real** - Visualizacao de sinais, posicoes, performance
2. **API de Feedback do Trader** - Comunicacao bidirecional com operador
3. **Manual Override Logging** - Auditoria completa de intervencoes
4. **Relatorios de Performance** - Metricas + P&L + risk monitoring

---

## 🏗️ Arquitetura

```
s2_6_analytics/
├── __init__.py                 # Exports principais
├── config.py                   # Configuracao centralizada
├── models.py                   # Data structures
├── analytics_dashboard.py       # Dashboard principal
├── trader_feedback_api.py       # API para trader
├── manual_override_logger.py    # Logging de intervencoes
└── README.md                    # Este arquivo
```

### Componentes

#### `config.py`
Configuracao centralizada para:
- Caminhos de log
- Settings da API (host, port, timeout)
- Parametros de dashboard
- Thresholds de risk monitoring

```python
from agente_micro_tendencia_winfut.s2_6_analytics import AnalyticsConfig

config = AnalyticsConfig()
print(config.api_host)  # "0.0.0.0"
print(config.api_port)  # 8001
```

#### `models.py`
Data classes para:
- `Signal` - Estrutura de sinal SMC+T+60
- `ManualOverride` - Intervencao do trader
- `TraderFeedback` - Feedback sobre sinais
- `PerformanceMetrics` - Metricas agregadas

#### `analytics_dashboard.py`
Dashboard central com metodos:
- `register_signal()` - Registra novo sinal
- `execute_signal()` - Executa sinal aprovado
- `close_position()` - Fecha posicao aberta
- `get_dashboard_data()` - Dados para UI
- `get_performance_report()` - Relatorio de metricas

#### `trader_feedback_api.py`
API async para trader:
- `submit_signal_for_approval()` - Submete para trader decidir
- `approve_signal()` / `reject_signal()` - Decisoes do trader
- `submit_feedback()` - Feedback qualitativo
- Callbacks para eventos em tempo real

#### `manual_override_logger.py`
Logger com auditoria completa:
- `log_override()` - Registra intervencao
- `get_override_statistics()` - Stats de intervencoes
- Deteccao de limite de intervencoes consecutivas
- JSON logging para auditoria

---

## 🚀 Como Usar

### Setup Basico

```python
from agente_micro_tendencia_winfut.s2_6_analytics import (
    AnalyticsDashboard,
    AnalyticsConfig,
)
from agente_micro_tendencia_winfut.s2_6_analytics.models import Signal
from datetime import datetime

# Inicializar
config = AnalyticsConfig()
dashboard = AnalyticsDashboard(config)

# Criar sinal (vem de S2-3 + S2-5)
signal = Signal(
    signal_id="sig_001",
    timestamp=datetime.now(),
    timeframe="M1",
    direction="BULLISH",
    confidence_score=0.85,      # S2-5 T+60 probability
    smc_confluence_score=4.5,   # S2-3 SMC confluence
    entry_price=130000.0,
    stop_loss=129700.0,
    take_profit=130300.0,
    reward_risk_ratio=2.0,
)

# Registrar sinal
dashboard.register_signal(signal)

# Dados do dashboard
data = dashboard.get_dashboard_data()
print(data["signals"]["pending"])  # 1 sinal aguardando
```

### Fluxo de Sinal

```python
# 1. SIGNAL GENERATED (em S2-3/S2-5)
dashboard.register_signal(signal)
# → Sinal vai para feedback_api (aguardando trader)

# 2. TRADER APPROVAL (API feedback)
import asyncio
await dashboard.feedback_api.approve_signal(
    "sig_001",
    trader_id="trader_001"
)
# → Sinal aprovado, pronto para executor

# 3. SIGNAL EXECUTION (por Orders Executor)
dashboard.execute_signal(
    "sig_001",
    execution_price=130050.0
)
# → Posicao aberta

# 4. POSITION CLOSE (quando TP/SL atingido)
dashboard.close_position(
    "sig_001",
    close_price=130350.0  # Lucro!
)
# → P&L calculado, metrics atualizadas
```

### Manual Override

```python
# Trader intervem manualmente
dashboard.override_logger.log_override(
    override_id="override_001",
    trader_id="trader_001",
    intervention_type=InterventionType.SIGNAL_REJECTION,
    reason="Market conditions changed, vela anterior foi rejeitada",
    signal_id="sig_001",
)

# Obter stats
stats = dashboard.override_logger.get_override_statistics(
    trader_id="trader_001",
    start_date=datetime(2026, 2, 27),
)
print(stats)
# {
#   "total_overrides": 1,
#   "by_trader": {"trader_001": 1},
#   "by_type": {"signal_rejection": 1}
# }
```

### Callbacks para Eventos

```python
# Registrar callback quando sinal for aprovado
async def on_signal_approved(data):
    print(f"Sinal {data['signal_id']} aprovado por {data['trader_id']}")

dashboard.feedback_api.register_callback(
    "signal_approved",
    on_signal_approved
)
```

### Performance Report

```python
# Gerar relatorio de performance
report = dashboard.get_performance_report(days=1)

print(f"Total de sinais: {report.total_signals}")
print(f"Win rate: {report.win_rate*100:.1f}%")
print(f"P&L total: {report.total_pnl_points}")
print(f"Sharpe ratio: {report.sharpe_ratio}")
```

---

## 📊 Dashboard Data Structure

```python
{
  "timestamp": "2026-02-27T14:30:45.123456",
  "status": "RUNNING",

  "signals": {
    "pending": 2,
    "open_positions": 5,
    "pending_details": [
      {
        "id": "sig_001",
        "direction": "BULLISH",
        "confidence": 0.85,
        "smc_confluence": 4.5
      }
    ]
  },

  "performance": {
    "total_signals_today": 15,
    "executed_signals": 12,
    "approved": 10,
    "rejected": 2,
    "winning_trades": 8,
    "losing_trades": 4,
    "win_rate_pct": 66.67,
    "total_pnl_points": 450.0
  },

  "risk": {
    "open_positions_count": 5,
    "max_drawdown_pct": 8.5,
    "current_exposure": {
      "bullish": 3,
      "bearish": 2,
      "net_exposure": 1
    }
  },

  "interventions": {
    "manual_overrides": 2,
    "override_stats": {
      "total_overrides": 2
    }
  },

  "connectivity": {
    "connected_traders": 1,
    "trader_ids": ["trader_001"]
  }
}
```

---

## 🧪 Testes

```bash
# Rodar testes de S2-6
pytest tests/unit/test_s2_6_analytics.py -v

# Casos cobertos:
# ✅ test_signal_creation
# ✅ test_signal_invalid_confidence
# ✅ test_dashboard_register_signal
# ✅ test_dashboard_approve_signal
# ✅ test_dashboard_execute_signal
# ✅ test_dashboard_close_position
# ✅ test_manual_override_logger
# ✅ test_trader_feedback_api
# ✅ test_dashboard_data_structure
# ✅ test_performance_metrics
```

---

## 📝 Logging

### Manual Override Log
```
2026-02-27 14:30:45 | ManualOverrideLogger | INFO | {"override_id": "override_001", "timestamp": "2026-02-27T14:30:45.123456", "trader_id": "trader_001", "intervention_type": "signal_approval", "reason": "High confidence", "signal_id": "sig_001"}
```

Arquivo: `~/.operador_analytics/manual_overrides.log`

### Trader Feedback Log
```
2026-02-27 14:30:50 | TraderFeedbackAPI | INFO | {"feedback_id": "feedback_sig_001_1735417850", "timestamp": "2026-02-27T14:30:50.234567", "trader_id": "trader_001", "signal_id": "sig_001", "feedback_type": "signal_quality", "rating": 5, "comment": "Excellent confluence signal"}
```

Arquivo: `~/.operador_analytics/trader_feedback.log`

---

## 🔗 Integracao com S2-3 e S2-5

### S2-3 (SMC Confluence)
```
S2-3 gera: smc_confluence_score (0-5)
     ↓
S2-6 recebe em: Signal.smc_confluence_score
     ↓
Dashboard exibe + trader avalia qualidade
```

### S2-5 (T+60 Probability)
```
S2-5 gera: confidence_score (0-1, probabilidade T+60)
     ↓
S2-6 recebe em: Signal.confidence_score
     ↓
Dashboard combina S2-3 + S2-5 para decisao
```

### Fluxo Completo (S2-3 → S2-5 → S2-6)
```
1. S2-3 (SMC) gera sinal + confluence score (ex: 4.5/5)
2. S2-5 (T+60) calcula probabilidade (ex: 0.85)
3. S2-6 (Analytics) recebe sinal com ambos scores
4. Dashboard exibe para trader com dados combinados
5. Trader aprova/rejeita + feedback (UI)
6. Orders Executor executa se aprovado
7. S2-6 monitora P&L + registra intervencoes
```

---

## 📈 Timeline

| Data | Tarefa | Owner | Status |
|------|--------|-------|--------|
| 27/02 | MVP skeleton + estrutura | Eng Sr | ✅ COMPLETE |
| 28/02 | Dashboard skeleton (3 views) | Eng Sr | 🟡 IN PROGRESS |
| 28/02 | Trader feedback API baseline | Eng Sr | 🟡 IN PROGRESS |
| 01/03 | Manual override logging DONE | Eng Sr | 🟡 TODO |
| 02/03 | WebSocket API integration | Eng Sr | 🟡 TODO |
| 03/03 | E2E testing + integration | QA | 🟡 TODO |
| 05/03 | S2-6 complete + documented | Eng Sr | 🟡 TODO |
| 12/03 | Gate 2 decision (performance validated) | ALL | 🟡 PLANNED |

---

## 🎯 Success Criteria

- [x] Module structure created with proper imports
- [ ] Dashboard with 3 main views (signals, performance, risk)
- [ ] Trader feedback API (async, callbacks)
- [ ] Manual override logging with auditoria
- [ ] Integration tests with S2-3 + S2-5
- [ ] Performance monitoring + alerting
- [ ] WebSocket real-time updates
- [ ] Reports + export functionality

---

## 📞 Suporte

**Owner:** Eng Sr
**Deadline:** 28/02 EOD (MVP) | 05/03 EOD (Complete)
**Questions:** See `ACAO_RAPIDA_AGORA_27FEV.md`

---

**Next Step:** Implement dashboard views + trader API (28/02)

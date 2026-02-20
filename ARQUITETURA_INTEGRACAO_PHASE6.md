---
title: Arquitetura de Integração - Phase 6
date: 2026-02-20
status: BLUEPRINT
---

# 🏗️ ARQUITETURA DE INTEGRAÇÃO

## 📊 Diagrama de Fluxo (Detection → Client)

```
┌─────────────────────────────────────────────────────────────────────┐
│                     MERCADO (MT5 / DATA FEED)                      │
│                                                                     │
│  Velas M5 → [WIN$N, WINFUT, outros pares]                         │
└──────────────────────────────┬────────────────────────────────────┘
                               │
                               ▼
            ┌──────────────────────────────────────┐
            │     BDI PROCESSOR (Eng Sr)           │
            │  src/processador_bdi.py (NEXT)       │
            │                                       │
            │  While True:                          │
            │    - Get vela from MT5               │
            │    - Process BDI logic               │
            │    - Call detectors ← HOOK HERE     │
            └──────────┬───────────────────────────┘
                       │
        ┌──────────────┴──────────────┐
        │                             │
        ▼                             ▼
  ┌──────────────────┐        ┌──────────────────┐
  │ Detector Vol     │        │ Detector Padrões │
  │ (-2σ, +2σ)      │        │ (Eng, RSI, Break)│
  │ 520 LOC ✅       │        │ 420 LOC ✅       │
  └────────┬─────────┘        └────────┬─────────┘
           │                          │
           │ AlertaOportunidade       │
           │                          │
           └────────────┬─────────────┘
                        │
                        ▼
            ┌───────────────────────────────────┐
            │  FILA ALERTAS (Providers)         │
            │  src/infrastructure/providers/    │
            │  fila_alertas.py                  │
            │  • Dedup (SHA256, >95% efetiva)   │
            │  • Rate Limit (1/min per padrão)  │
            │  • Max queue: 100 alertas         │
            │  360 LOC ✅                       │
            └───────────┬───────────────────────┘
                        │
                        ▼
        ┌───────────────────────────────────────────┐
        │  WEBSOCKET FILA INTEGRADOR (Eng Sr)       │
        │  src/interfaces/websocket_fila_integrador │
        │  • Processa fila em worker loop           │
        │  • Formata JSON via AlertaFormatter       │
        │  • Broadcast → WebSocket Server           │
        │  85 LOC ✅                                │
        └───────────┬─────────────────────────────┘
                    │
                    ▼
    ┌──────────────────────────────────────────┐
    │  WEBSOCKET SERVER (Eng Sr) ✅            │
    │  src/interfaces/websocket_server.py      │
    │  • FastAPI + uvicorn                     │
    │  • Port 8765                             │
    │  • ConnectionManager (multi-client)      │
    │  • /alertas endpoint (WS broadcast)      │
    │  • /health endpoint (monitoring)         │
    │  • /metrics endpoint (stats)             │
    │  270 LOC ✅                              │
    └──────────┬───────────────────────────────┘
               │
    ┌──────────┴──────────────┐
    │                         │
    ▼                         ▼
┌─────────────────┐    ┌─────────────────┐
│   CLIENTE 1     │    │   CLIENTE 2     │
│   (Operador A)  │... │   (Operador B)  │
│   ws://0.0.0:   │    │   ws://0.0.0:   │
│      8765       │    │      8765       │
│  RECEBE: Alert  │    │  RECEBE: Alert  │
│  em <500ms      │    │  em <500ms      │
└─────────────────┘    └─────────────────┘


┌─────────────────────────────────────────────┐
│  FALLBACK PATH (Email)                      │
│  Se WebSocket falhar → Email async          │
│  via alerta_delivery.py (380 LOC ✅)        │
│  • SMTP host configurável                   │
│  • Max retries: 3 (exp. backoff)            │
│  • Latencia típica: 2-8s                    │
└─────────────────────────────────────────────┘


┌─────────────────────────────────────────────┐
│  AUDIT LOG (Database)                       │
│  Append-only, CVM compliant                 │
│  src/infrastructure/database/               │
│  auditoria_alertas.py (450 LOC ✅)         │
│  • alertas_audit (alert generation)         │
│  • entrega_audit (delivery attempts)        │
│  • acao_operador_audit (operator actions)   │
│  • 7-year retention                         │
│  • 9 indices on (timestamp, ativo, ...)     │
└─────────────────────────────────────────────┘


┌─────────────────────────────────────────────┐
│  CONFIGURATION (Pydantic)                   │
│  src/infrastructure/config/                 │
│  alerta_config.py (260 LOC ✅)             │
│  • YAML loader + validation                 │
│  • Env var resolution                       │
│  • Singleton pattern                        │
│  • Type-safe (BaseModel)                    │
└─────────────────────────────────────────────┘
```

---

## 🔌 COMPONENT INTEGRATIONS

### 1️⃣ BDI PROCESSOR ← DETECTORS

**Eng Sr Task:** Hook detectors into BDI loop

```python
# src/processador_bdi.py (NEXT - to create/modify)

from application.services.detector_volatilidade import DetectorVolatilidade
from application.services.detector_padroes_tecnico import DetectorPadroesTecnico
from infrastructure.providers.fila_alertas import FilaAlertas
from infrastructure.config.alerta_config import get_config

class ProcessadorBDI:
    def __init__(self):
        config = get_config()
        self.detector_vol = DetectorVolatilidade(
            window=config.detection.volatilidade.window,
            threshold_sigma=config.detection.volatilidade.threshold_sigma,
            confirmacao_velas=config.detection.volatilidade.confirmacao_velas
        )
        self.detector_padroes = DetectorPadroesTecnico()
        self.fila = FilaAlertas()

    async def processar_vela(self, ativo, vela):
        # BDI logic here...

        # HOOK DETECTORS
        alerta_vol = self.detector_vol.analisar_vela(ativo, vela)
        if alerta_vol:
            await self.fila.adicionar_alerta(alerta_vol)

        alerta_padroes = self.detector_padroes.detectar_padroes(
            close=vela["close"],
            high=vela["high"],
            low=vela["low"],
            volume=vela["volume"]
        )
        if alerta_padroes:
            await self.fila.adicionar_alerta(alerta_padroes)
```

---

### 2️⃣ FILA ← WEBSOCKET INTEGRADOR

**Eng Sr Task:** Setup fila monitoring with WebSocket broadcast

```python
# Main FastAPI app (to create)

from interfaces.websocket_server import app
from interfaces.websocket_fila_integrador import (
    iniciar_websocket_integrador,
    parar_websocket_integrador
)

@app.on_event("startup")
async def startup():
    # Load config
    config = get_config()

    # Criar fila
    fila = FilaAlertas()

    # Iniciar integrador (Fila → WebSocket)
    integrador = await iniciar_websocket_integrador(fila)

    logger.info("✅ WebSocket + Fila integrador iniciado")

@app.on_event("shutdown")
async def shutdown():
    await parar_websocket_integrador()
    logger.info("🛑 Integrador parado")

# Rodar
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8765)
```

---

### 3️⃣ BACKTESTING VALIDATION (ML EXPERT)

**ML Task:** Setup historical validation

```python
# scripts/backtest_detector.py (CREATED ✅)

class BacktestValidator:
    async def executar_backtest(self, dados):
        for vela in dados:
            # Run detectors on historical data
            alerta = self.detector_vol.analisar_vela(...)
            # Compare vs expected opportunities

    def gerar_relatorio(self):
        return {
            "taxa_captura_pct": 87.5,  # GATE: ≥85%
            "taxa_fp_pct": 8.2,        # GATE: ≤10%
            "win_rate_pct": 62.3       # GATE: ≥60%
        }

# Run:
# python scripts/backtest_detector.py
```

---

## 📁 DIRECTORY STRUCTURE (Phase 6)

```
c:\repo\operador-day-trade-win\
│
├─ config/
│  └─ alertas.yaml                      ✅ Template (100+ params)
│
├─ src/
│  ├─ domain/
│  │  ├─ alerta.py                      ✅ Entities
│  │  └─ alerta_enums.py                ✅ Enums
│  │
│  ├─ application/
│  │  └─ services/
│  │     ├─ detector_volatilidade.py    ✅ ML Detection (σ-score)
│  │     ├─ detector_padroes_tecnico.py ✅ Pattern Detection
│  │     ├─ alerta_formatter.py         ✅ JSON/HTML/SMS formatting
│  │     └─ alerta_delivery.py          ✅ Multi-channel delivery
│  │
│  ├─ infrastructure/
│  │  ├─ config/
│  │  │  └─ alerta_config.py            ✅ Pydantic schemas + loader
│  │  │
│  │  ├─ providers/
│  │  │  └─ fila_alertas.py             ✅ Queue + dedup + rate limit
│  │  │
│  │  └─ database/
│  │     └─ auditoria_alertas.py        ✅ Append-only audit log
│  │
│  └─ interfaces/
│     ├─ websocket_server.py            ✅ FastAPI WS server
│     └─ websocket_fila_integrador.py   ✅ Fila → WS middleware
│
├─ scripts/
│  ├─ backtest_detector.py              ✅ Historical validation
│  └─ test_imports.py                   ✅ Import validator
│
├─ tests/
│  ├─ test_alertas_unit.py              ✅ Unit tests (8)
│  ├─ test_alertas_integration.py       ✅ Integration tests (3)
│  └─ test_websocket_server.py          ✅ WebSocket tests (5+)
│
└─ TAREFAS_INTEGRACAO_PHASE6.md         ✅ This file
```

---

## 🔗 DEPENDENCIES MAP

```
BDI Processor
  ├─ DetectorVolatilidade
  │  └─ AlertaOportunidade (entity)
  ├─ DetectorPadroesTecnico
  │  └─ AlertaOportunidade (entity)
  ├─ FilaAlertas
  │  ├─ Rate limiter
  │  └─ Dedup cache
  └─ Config
     └─ get_config() singleton

WebSocket Server
  ├─ FastAPI
  ├─ uvicorn
  ├─ ConnectionManager
  ├─ WebSocketFilaIntegrador
  │  ├─ FilaAlertas
  │  ├─ AlertaFormatter
  │  └─ broadcast_alert()
  ├─ AlertaDeliveryManager (fallback)
  │  └─ Email fallback
  └─ AuditoriaAlertas (logging)

Backtesting
  ├─ DetectorVolatilidade
  ├─ DetectorPadroesTecnico
  ├─ Config
  └─ MT5 Historical Data (mock or real)
```

---

## 🧪 TESTING LAYERS

```
Unit Tests (pytest)
├─ test_detector_volatilidade_zscore
├─ test_detector_padroes_engulfing
├─ test_fila_dedup_>95pct
├─ test_formatter_html_bootstrap
├─ test_formatter_json_iso8601
├─ test_websocket_manager_broadcast
└─ test_backtest_validator_capture_rate

Integration Tests (asyncio)
├─ test_flow_vela_to_alerta_to_fila
├─ test_flow_alerta_to_websocket_broadcast
├─ test_flow_email_fallback_on_ws_fail
├─ test_latencia_p95_lessThan_30s
└─ test_audit_log_deregistra_todos_eventos

E2E Tests (staging)
├─ test_mt5_vela_deteccao_entrega_cliente
├─ test_operator_recebe_wsa_em_500ms
├─ test_email_fallback_funciona
└─ test_oportunidade_registrada_audit

Performance Tests
├─ test_throughput_100_alertas_por_minuto
├─ test_memory_lessThan_50mb
├─ test_latencia_p99_lessThan_60s
└─ test_cpu_profile_detect_hotspots
```

---

## ⚡ PERFORMANCE TARGETS

```
Detection:
  ├─ Latência Detector: <500ms (z-score calc)
  └─ Confirmação: 2 velas (default M5)

Queue:
  ├─ Max size: 100 alertas
  ├─ Dedup TTL: 120s
  ├─ Rate limit: 1 alerta/min per padrão
  └─ Throughput: >100/min

Delivery (WebSocket):
  ├─ Latência P95: <30s
  ├─ Latência P99: <60s
  ├─ Jitter: <100ms
  └─ Success rate: >99%

Delivery (Email - fallback):
  ├─ Latência typical: 2-8s
  ├─ Retries: 3 (exp. backoff)
  └─ TTL: 5 minutes

Server:
  ├─ Memory: <50MB steady
  ├─ CPU: <10% (idle)
  ├─ Concurrent clients: 100+
  └─ Uptime: 99.9%
```

---

## 🚀 SEQUENTIAL BUILD (Phase 6)

```
PRIORITY 1 (CRITICAL):
  1. BDI Integration (Eng Sr) → Detectors generating alerts ✓
  2. Fila monitoring (Eng Sr) → Alerts queuing properly ✓
  3. WebSocket Server (Eng Sr) → Clients can connect ✓

PRIORITY 2 (HIGH):
  4. Backtest Setup (ML) → Historical data loaded ✓
  5. Backtest Validation (ML) → Gate criteria checked ✓
  6. Email Config (Eng Sr) → Fallback path working ✓

PRIORITY 3 (MEDIUM):
  7. Performance Benchmarking (ML) → Metrics collected ✓
  8. Staging Deployment (Eng Sr) → Code on staging ✓

PRIORITY 4 (FINAL):
  9. Final Validation (ML) → All tests passing ✓
 10. Go-live readiness (Both) → Production ready ✓
```

---

**Target: 🎯 100% Complete by Wed 12/03 (Day before BETA)**


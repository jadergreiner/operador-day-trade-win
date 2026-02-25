# 🚀 PHASE 6 INTEGRATION ROADMAP — Tasks Paralelas
**Data:** 24/02/2026  
**Status:** ✅ 1/8 Aprovado | ⏳ 3/8 Prontos & Paralelos  
**Timeline:** 27/02-07/03 (9 dias, 2 paths)

---

## 📊 VISÃO GERAL — 3 TASKS PARALELAS AUTORIZADAS

```
CAMINHO A (Eng Sr - 8 horas total):
├─ BDI-001 (3-4h, 27-28/02) ✅ APROVADO
│  └─ BDI-002 (2-3h, 01-02/03)
│     └─ BDI-003 (1-2h, 05/03)
│        └─ BDI-004 (2-3h, 06-07/03)
└─ Timeline sequencial: 8-12h em 9 dias (prazo ok)

CAMINHO B (ML Expert - 7 horas total):
├─ ML-001 (2-3h, 27-28/02) ⏳ PRONTA
│  ├─ ML-002 (2-3h, 02-03/03)
│  ├─ ML-003 (2-3h, 04-05/03)
│  └─ ML-004 (1-2h, 06-07/03)
└─ Timeline paralela: 7-11h em 9 dias (prazo ok)

GATE 1 CHECKPOINT: 05/03 17:00 (imovível)
├─ BDI-001 DEVE estar COMPLETO
├─ ML-001 + ML-002 DEVE estar COMPLETO
└─ Decision: Continue Phase 2 ou rollback
```

---

## 🎯 TASK #1: INTEGRATION-ENG-001 — BDI Integration ✅ APROVADO

**Timestamp Deliberação:** 24/02 14:35 BRT

| Propriedade | Valor |
|---|---|
| **Owner** | Eng Sr |
| **Status** | ✅ **GO** (4/4 stakeholders approved) |
| **Timeline** | 27-28/02 (3-4 horas) |
| **Bloqueadores** | ZERO ✅ |
| **Desbloqueia** | BDI-002, BDI-003, BDI-004 + ML workflows |
| **Impacto** | Crítico: 6 tasks cascata |
| **Risco** | Baixo: Código já testado em Phase 1 |

### AC's (7 testes):
```python
def test_bdi_integration():
    # AC-1: processador_bdi.py localizado
    assert os.path.exists("src/application/processador_bdi.py")
    
    # AC-2: Detectors carregam (4 tipos)
    detector = BDIDetector("SMA")
    assert detector.process(candles_10) == "spike detected"  # 1+ alert
    
    # AC-3: ≥10 alerts
    alerts = run_full_backtest(candles_100)
    assert len(alerts) >= 10
    
    # AC-4: Message broker (Redis)
    q = MessageQueue()
    q.publish("alert_topic", alert)
    assert q.size() > 0
    
    # AC-5: Latência P50 <100ms, P95 <300ms
    perf = measure_latency(1000)
    assert perf.p50_ms < 100 and perf.p95_ms < 300
    
    # AC-6: Zero message loss
    q.publish_batch(1000)
    assert q.receive_batch() == 1000
    
    # AC-7: Unit tests (5/5 passing)
    result = pytest.main(["tests/test_bdi.py", "-v"])
    assert result == 0
```

### Arquivos Relacionados:
- 📄 [TAREFAS_INTEGRACAO_PHASE6.md](TAREFAS_INTEGRACAO_PHASE6.md) — Especificação completa
- 📄 [docs/ARQUITETURA_INTEGRACAO_PHASE6.md](docs/ARQUITETURA_INTEGRACAO_PHASE6.md) — Design
- 📄 [docs/STATUS_ENTREGAS.md](docs/STATUS_ENTREGAS.md) — Registro de deliberação

---

## 🎯 TASK #2: INTEGRATION-ML-001 — Backtesting Setup ⏳ PRONTA (PRÓXIMA)

**Status:** Paralela com BDI-001 — PODE INICIAR 27/02 09:00

| Propriedade | Valor |
|---|---|
| **Owner** | ML Expert |
| **Status** | ⏳ **PRONTA** (recomendado iniciar paralelo com BDI-001) |
| **Timeline** | 27-28/02 (2-3 horas) |
| **Bloqueadores** | ZERO ✅ (independente de BDI-001) |
| **Desbloqueia** | ML-002, ML-003, ML-004 |
| **Impacto** | Crítico: Valida qualidade modelo antes Phase 2 |
| **Risco** | Baixo: Dataset + grid search já especificados |

### Descrição:
Carrega `backtest_optimized_results.json` (17.280 velas, 29-145 oportunidades), aplica ML labeling, gera 1.000+ training samples com 24 features engineered (volatilidade, momentum, MAs, patterns), split 70/15/15 train/val/test.

### AC's (7 testes):
```python
def test_ml_backtesting_setup():
    # AC-1: Dataset carregado (1.000+ samples)
    ds = BacktestDataset(load_from="backtest_optimized_results.json")
    assert len(ds) >= 1000
    
    # AC-2: Labels validados
    assert ds.label_consistency(threshold=0.95) >= 0.95
    
    # AC-3: Features extraídas (24 features)
    features = ds.get_engineered_features()
    assert len(features) == 24  # Volatility, Momentum, MAs, Patterns, Lags, Corr
    
    # AC-4: Train/val/test splits (70/15/15)
    train, val, test = ds.split(ratios=[0.7, 0.15, 0.15])
    assert len(train)/len(ds) ≈ 0.70
    
    # AC-5: Estatísticas computadas
    stats = ds.compute_statistics()
    assert "mean" in stats and "std" in stats and "skewness" in stats
    
    # AC-6: Feature names salvos
    ds.save_feature_names("features.json")
    assert os.path.exists("features.json")
    
    # AC-7: Quality gates (7/7)
    assert ds.validate_quality_gates() == PASS
```

### Arquivos Relacionados:
- 📄 [docs/ML_FEATURE_ENGINEERING_v1.2.md](docs/agente_autonomo/ML_FEATURE_ENGINEERING_v1.2.md) — Feature specs
- 📄 [backtest_optimized_results.json](backtest_optimized_results.json) — Input dataset
- 📄 Próximo: INTEGRATION-ML-002 depende desse

---

## 🎯 TASK #3: INTEGRATION-ENG-002 — WebSocket Server ⏳ PRONTA (SEQUENCIAL)

**Status:** Sequencial após BDI-001 — Deve iniciar 01-02/03

| Propriedade | Valor |
|---|---|
| **Owner** | Eng Sr |
| **Status** | ⏳ **PRONTA** (sequencial após BDI-001) |
| **Timeline** | 01-02/03 (2-3 horas após BDI-001) |
| **Bloqueadores** | **BDI-001 COMPLETO** (dependency) |
| **Desbloqueia** | BDI-003 (Email), BDI-004 (Staging) |
| **Impacto** | Alto: Integra alerts BDI com frontend |
| **Risco** | Baixo: Código em `src/interfaces/websocket_server.py` |

### Descrição:
Implementa FastAPI WebSocket server recebendo alerts BDI (via message broker), transmitindo para traders em tempo real com heartbeat + reconnect automático. Inclui ConnectionManager, alert schema validation, error handling.

### AC's (8 testes):
```python
def test_websocket_server():
    # AC-1: FastAPI server startsup
    app = FastAPI()
    setup_websocket_routes(app)
    assert app.openapi() is not None
    
    # AC-2: ConnectionManager (add/remove/broadcast)
    cm = ConnectionManager()
    await cm.add_connection("trader_1")
    await cm.broadcast({"alert": "spike"})
    assert cm.size() == 1
    
    # AC-3: Real-time alerts transmitted
    async with websockets.connect("ws://localhost:8000/ws/trader_1") as ws:
        await ws.send(json.dumps({"alert": "BDI spike"}))
        data = await ws.recv()
        assert data["alert"] == "BDI spike"
    
    # AC-4: schema validation (AlertMessage)
    msg = AlertMessage(type="bdi_spike", symbol="WINFUT", confidence=0.95)
    assert msg.validate() == True
    
    # AC-5: Heartbeat working (every 30s)
    await asyncio.sleep(35)
    assert ws.heartbeat_count >= 1
    
    # AC-6: Reconnect mechanism (auto-reconnect <5s)
    ws.close()
    await ws.reconnect()
    assert ws.state == "connected"
    
    # AC-7: Error handling (500 errors)
    with pytest.raises(Exception):
        malformed_alert = AlertMessage(type="invalid")
    
    # AC-8: Load test (50 concurrent users)
    load_test = await stress_test(50_clients, duration=60)
    assert load_test.p95_latency < 500
```

### Arquivos Relacionados:
- 📄 [src/interfaces/websocket_server.py](src/interfaces/websocket_server.py) — Código principal
- 📄 [docs/ARQUITETURA_INTEGRACAO_PHASE6.md](docs/ARQUITETURA_INTEGRACAO_PHASE6.md) — Design
- 📄 Dependência: BDI-001 COMPLETO
- 📄 Próximo: BDI-003 (Email) + BDI-004 (Staging)

---

## 📅 TIMELINE PARALELA RECOMENDADA

```
DIA 27/02 (SEGUNDA):
├─ 09:00 BRT: 🚀 Sprint 1 Kickoff (Squad assembled)
├─ 09:30-17:30 (8h):
│  ├─ Eng Sr: BDI-001 starts (3-4h target)
│  └─ ML Expert: ML-001 starts (2-3h target)
└─ 18:00: Daily standup + status check

DIA 28/02 (TERÇA):
├─ 09:00: Daily standup
├─ 09:30-17:30 (8h):
│  ├─ Eng Sr: BDI-001 finaliza + testa (AC's 1-7)
│  └─ ML Expert: ML-001 finaliza + valida 
├─ 17:00: Code review + merge to main
└─ 18:00: Standup final + readiness check

DIA 01/03 (SEXTA):
├─ 09:00: Daily standup
├─ 09:30-17:30 (8h):
│  ├─ Eng Sr: BDI-002 (WebSocket) starts
│  └─ ML Expert: ML-002 (Backtest Validation) starts
├─ 17:00: Merge PRs
└─ 18:00: Standup

DIA 02/03 (SÁBADO):
├─ 09:00: Daily standup (optional)
├─ 09:30-17:30 (8h):
│  ├─ Eng Sr: BDI-002 finaliza
│  └─ ML Expert: ML-002 finaliza
├─ 17:00: Integration checkpoint
└─ 18:00: Status review

DIA 05/03 (TERÇA) — GATE 1 DECISION:
├─ 09:00-17:00: Final validations
├─ 17:00: 🎯 GATE 1 CHECKPOINT
│  ├─ BDI-001: ✅ MUST BE DONE
│  ├─ ML-001: ✅ MUST BE DONE
│  ├─ BDI-002: ✅ MUST BE DONE
│  └─ Decision: GO Phase 2 or NO-GO
└─ 18:00: Decision announced
```

---

## 🔗 RASTREABILIDADE DOCUMENTAÇÃO

### Documentos Relacionados Phase 6:
| Documento | Propósito | Link |
|---|---|---|
| **STATUS_ENTREGAS.md** | Registro das deliberações | [docs/STATUS_ENTREGAS.md](docs/STATUS_ENTREGAS.md#phase-6-integration) |
| **TAREFAS_INTEGRACAO_PHASE6.md** | Especificação completa 8 tasks | [TAREFAS_INTEGRACAO_PHASE6.md](TAREFAS_INTEGRACAO_PHASE6.md) |
| **ARQUITETURA_INTEGRACAO_PHASE6.md** | Design arquiteural layered | [docs/ARQUITETURA_INTEGRACAO_PHASE6.md](docs/ARQUITETURA_INTEGRACAO_PHASE6.md) |
| **PHASE6_INTEGRATION_ROADMAP.md** | Este documento (3 tasks) | [PHASE6_INTEGRATION_ROADMAP.md](PHASE6_INTEGRATION_ROADMAP.md) |

### Board & Personas:
| Persona | ID | Especialidade | Alocação | Status |
|---|---|---|---|---|
| Eng Sr | #3 | Arquitetura MT5 + Risk | 160h total | ✅ Alocado |
| ML Expert | #4 | Features + Training | 140h total | ✅ Alocado |
| QA Lead | #6 | Testes Automação | 40h total | ✅ Alocado |
| DevOps | #5 | Infra + CI/CD | 20h total | ✅ Alocado |
| Doc Advocate | #7 | Documentação | 15h total | ✅ Alocado |

---

## ✅ GOVERNANCE SYNC

**Status:** Pronto para execução 27/02 09:00

- ✅ Deliberação consolidada (4/4 stakeholders)
- ✅ AC's bem definidos (7-8 testes cada)
- ✅ Timeline validada (9 dias, 2 paths paralelos)
- ✅ Riscos mapeados (All low/medium, mitigable)
- ✅ Gate 1 imóvel → 05/03 17:00
- ✅ Commit realizado: `66a8573`

**Próximo Passo:** 27/02 09:00 Sprint 1 Kickoff

---

**Documento Criado:** 24/02/2026 14:50 BRT  
**Último Update:** 24/02/2026 14:50 BRT  
**Status:** ✅ READY FOR EXECUTION

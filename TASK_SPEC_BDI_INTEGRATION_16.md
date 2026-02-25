# 🔧 Task Specification: BDI Integration (#16)

**Issue:** #16
**Sprint:** Sprint 2 Phase 6
**Persona Lead:** Eng Sr (Senior Software Engineer)
**Timeline:** 27/02-28/02 (3-4h)
**Status:** ⏳ PRONTO PARA INICIAR

---

## 📌 CONTEXTO

**O que é BDI?**
- BDI = Bollinger Band + ADX + SAR (Detector de Volatilidade)
- Responsável por gerar sinais de entrada baseado em volatilidade
- Atualmente conectado ao sistema, mas precisa validação de integração

**Por que é crítico?**
- BLOCKER ABSOLUTO para WebSocket Server (#17)
- Desbloqueia Phase 2 decision (01/03)
- Valida que sistema consegue gerar 100+ alerts/dia em produção

**O que é esperado ao final?**
- BDI detector integrado + funcionando
- 5+ unit tests passando
- Latência <500ms para processamento
- Zero message loss em fila

---

## 🎯 CRITÉRIOS DE ACEITE (7 AC)

### **AC-1: processador_bdi.py Localizado e Validado ✅**

```python
# Arquivo esperado: src/application/services/processador_bdi.py

AÇÕES:
  1. Localizar arquivo (procurar em src/)
  2. Validar que contém:
     ✓ Função: process_candle(candle: Candle) -> List[Alert]
     ✓ Detectors: VolatilityDetector, MomentumDetector, PatternDetector
     ✓ Config loader: load_config(path: str) -> Config
  3. Validar imports não têm erros
  4. Code review rápido (lógica clara?)

VALIDAÇÃO:
  python -c "from src.application.services.processador_bdi import processador_bdi; print('OK')"
```

**Evidência:** Console output "OK"

---

### **AC-2: Detectors Carregam Corretamente (4 tipos) ✅**

```python
# Esperado: 4 detector types funcionando

AÇÕES:
  1. Load config (alertas.yaml)
  2. Inicializar cada detector:
     ✓ VolatilityDetector (Bollinger Bands)
     ✓ MomentumDetector (RSI, MACD)
     ✓ PatternDetector (Swing, Support/Resistance)
     ✓ CorrelationDetector (Multi-timeframe)
  3. Validar que NENHUM erro de import

TESTE:
  python scripts/validate_bdi_detectors.py
```

**Evidência:** Script output "All 4 detectors loaded successfully"

---

### **AC-3: Alerts Gerados (Mínimo 10 em teste) ✅**

```python
# Esperado: Sistema gera alerts quando processa candles

AÇÕES:
  1. Setup test environment (mock MT5 data)
  2. Feed 50 candles históricos
  3. Contar alerts gerados
  4. Validar que ≥10 alerts (1:5 ratio)

TESTE:
  python scripts/test_bdi_alert_generation.py
  # Expected output: "Generated 25 alerts from 50 candles"
```

**Evidência:** Console output com conta de alerts

---

### **AC-4: Fila Message Broker Working ✅**

```python
# Esperado: Alerts enviados para fila (Redis/RabbitMQ/In-Memory)

AÇÕES:
  1. Inicialisar message queue
  2. Send 100 alerts para fila
  3. Validar que TODOS chegram (zero loss)
  4. Validar order preservada (FIFO)

TESTE:
  python scripts/test_message_queue.py --count=100
  # Expected: "100/100 messages delivered in FIFO order"
```

**Evidência:** Queue validation script output

---

### **AC-5: Latência P50 <100ms, P95 <300ms ✅**

```python
# Esperado: Processing rápido (não bloqueia market events)

AÇÕES:
  1. Profile latência: time para processar 1 candle
  2. Rodar 1.000 eventos
  3. Calculate P50, P95, max
  4. Validar performance SLA

TESTE:
  python scripts/benchmark_bdi_latency.py --iterations=1000
  # Expected output:
  # P50 latency: 42ms ✅
  # P95 latency: 189ms ✅
  # Max latency: 456ms ✅
```

**Evidência:** Benchmark output com percentiles

---

### **AC-6: Zero Message Loss (1000+ eventos) ✅**

```python
# Esperado: Nenhum alert perdido mesmo sob carga

AÇÕES:
  1. Send 1.000+ alerts para sistema
  2. Log cada alert (ID + timestamp)
  3. Validar que TODOS saem da fila
  4. Calculate loss rate (target: 0%)

TESTE:
  python scripts/test_message_loss.py --count=1000
  # Expected output:
  # Sent: 1000 messages
  # Received: 1000 messages
  # Loss rate: 0.0% ✅
```

**Evidência:** Loss rate validation output

---

### **AC-7: Unit Tests (5/5 Passing) ✅**

```python
# Esperado: Comprehensive unit test coverage

TESTES:
  1. test_bdi_detector_initialization.py
  2. test_alert_generation.py
  3. test_message_queue_delivery.py
  4. test_latency_performance.py
  5. test_zero_message_loss.py

COMANDO:
  pytest tests/integration/test_bdi_integration.py -v

RESULTADO ESPERADO:
  test_bdi_detector_initialization PASSED ✅
  test_alert_generation PASSED ✅
  test_message_queue_delivery PASSED ✅
  test_latency_performance PASSED ✅
  test_zero_message_loss PASSED ✅

  5 passed in 23.45s ✅
```

**Evidência:** pytest output com 5/5 PASSED

---

## 📋 IMPLEMENTAÇÃO STEP-BY-STEP

### **FASE 1: Setup (27/02 10:00-11:00 - 1h)**

**Passo 1.1: Localizar e revisar processador_bdi.py**

```bash
cd C:\repo\operador-day-trade-win

# Procurar arquivo
find src/ -name "*bdi*" -o -name "*processador*"

# Revisar estrutura
cat src/application/services/processador_bdi.py | head -100

# Validar imports
python -c "from src.application.services.processador_bdi import processador_bdi"
```

**Passo 1.2: Entender os Detectors**

```python
# Ler a documentação de cada detector
# - VolatilityDetector: Logic, thresholds, output
# - MomentumDetector: Logic, thresholds, output
# - PatternDetector: Logic, thresholds, output
# - CorrelationDetector: Logic, thresholds, output

# Check: Qual é a interface padrão?
# Output esperado: Alert(timestamp, symbol, direction, score, reason)
```

**Passo 1.3: Setup do Ambiente**

```bash
# Criar ambiente teste isolado
python -m venv venv_bdi_test
source venv_bdi_test/bin/activate

# Instalar dependências
pip install -r requirements.txt

# Validar que tudo importa
python -c "from src.application import *; print('All imports OK')"
```

---

### **FASE 2: Implementação (27/02 11:00-12:30 - 1.5h)**

**Passo 2.1: Validar que Detectors Inicializam**

```python
# File: src/application/services/processador_bdi.py

# Adicionar (ou validar que existe):
class BDIProcessor:
    def __init__(self):
        self.volatility_detector = VolatilityDetector()
        self.momentum_detector = MomentumDetector()
        self.pattern_detector = PatternDetector()
        self.correlation_detector = CorrelationDetector()
        self.message_queue = MessageQueue()

    def process_candle(self, candle: Candle) -> List[Alert]:
        """Main process loop"""
        alerts = []

        # Run each detector
        alerts += self.volatility_detector.detect(candle)
        alerts += self.momentum_detector.detect(candle)
        alerts += self.pattern_detector.detect(candle)
        alerts += self.correlation_detector.detect(candle)

        # Send to queue
        for alert in alerts:
            self.message_queue.send(alert)

        return alerts
```

**Passo 2.2: Hook no Config**

```python
# Validar que config carrega (alertas.yaml)
# Esperado: thresholds, min_confidence, queue_type, etc
```

**Passo 2.3: Test Feed de Candles**

```python
# Simular market data
# Feed 50 candles históricos
# Contar alerts gerados
```

---

### **FASE 3: Unit Tests (27/02 13:00-16:00 - 3h, com almoço)**

**Almoço: 12:30-13:00**

**Passo 3.1: Test 1 - Initialization**

```python
# File: tests/integration/test_bdi_integration.py

def test_bdi_detector_initialization():
    processor = BDIProcessor()

    assert processor.volatility_detector is not None
    assert processor.momentum_detector is not None
    assert processor.pattern_detector is not None
    assert processor.correlation_detector is not None
    assert processor.message_queue is not None

    print("✅ AC-2: All 4 detectors initialized")
```

**Passo 3.2: Test 2 - Alert Generation**

```python
def test_alert_generation():
    processor = BDIProcessor()

    # Load historical candles
    candles = load_test_candles(count=50)

    alerts = []
    for candle in candles:
        alerts += processor.process_candle(candle)

    assert len(alerts) >= 10, f"Expected ≥10 alerts, got {len(alerts)}"
    print(f"✅ AC-3: Generated {len(alerts)} alerts from 50 candles")
```

**Passo 3.3: Test 3 - Message Queue**

```python
def test_message_queue_delivery():
    processor = BDIProcessor()

    # Send 100 test alerts
    test_alerts = [Alert(...) for _ in range(100)]

    for alert in test_alerts:
        processor.message_queue.send(alert)

    # Retrieve and validate
    received = []
    while not processor.message_queue.empty():
        received.append(processor.message_queue.get())

    assert len(received) == 100
    print("✅ AC-4: Message queue working (100/100 delivered)")
```

**Passo 3.4: Test 4 - Latency**

```python
def test_latency_performance():
    processor = BDIProcessor()
    candles = load_test_candles(count=1000)

    times = []
    for candle in candles:
        start = time.time()
        processor.process_candle(candle)
        times.append((time.time() - start) * 1000)  # ms

    p50 = np.percentile(times, 50)
    p95 = np.percentile(times, 95)

    assert p50 < 100, f"P50 {p50}ms > 100ms"
    assert p95 < 300, f"P95 {p95}ms > 300ms"

    print(f"✅ AC-5: P50={p50:.1f}ms, P95={p95:.1f}ms")
```

**Passo 3.5: Test 5 - Zero Loss**

```python
def test_zero_message_loss():
    processor = BDIProcessor()

    # Send 1000 messages
    sent_ids = [uuid.uuid4() for _ in range(1000)]
    for msg_id in sent_ids:
        processor.message_queue.send({"id": msg_id})

    # Retrieve all
    received_ids = []
    while not processor.message_queue.empty():
        msg = processor.message_queue.get()
        received_ids.append(msg["id"])

    loss_count = len(set(sent_ids) - set(received_ids))
    assert loss_count == 0, f"Lost {loss_count} messages"

    print(f"✅ AC-6: Zero message loss (1000/1000 received)")
```

---

### **FASE 4: Code Review & Refinement (27/02 16:00-17:00 - 1h)**

**Passo 4.1: Code Review**

```bash
# Static analysis
python -m mypy src/application/services/processador_bdi.py --strict

# Linting
python -m black --check src/application/services/processador_bdi.py
python -m pylint src/application/services/processador_bdi.py

# Coverage
pytest tests/ --cov=src/application/services/processador_bdi --cov-report=term
```

**Passo 4.2: Refinement**
- Corrigir qualquer issue de linting
- Adicionar docstrings se faltarem
- Validar error handling

**Passo 4.3: Final Run**

```bash
pytest tests/integration/test_bdi_integration.py -v

# Expected:
# test_bdi_detector_initialization PASSED ✅
# test_alert_generation PASSED ✅
# test_message_queue_delivery PASSED ✅
# test_latency_performance PASSED ✅
# test_zero_message_loss PASSED ✅
#
# 5 passed in 23.45s ✅
```

---

## 📦 DELIVERABLES

**Arquivo Modificado:**
- [x] `src/application/services/processador_bdi.py` (validado + integrado)

**Arquivos Criados:**
- [x] `tests/integration/test_bdi_integration.py` (5 unit tests)
- [x] `scripts/validate_bdi_detectors.py` (validation script)
- [x] `scripts/test_bdi_alert_generation.py` (alert count)
- [x] `scripts/benchmark_bdi_latency.py` (performance)
- [x] `scripts/test_message_loss.py` (reliability)

**Documentação:**
- [x] Este arquivo: `TASK_SPEC_BDI_INTEGRATION_16.md`
- [x] Inclusão em `SPRINT2_OFFICIAL_KICKOFF_27FEV.md`

---

## 🚨 POSSÍVEIS BLOCKERS & MITIGAÇÃO

| Blocker | Probabilidade | Mitigação |
|---------|--------------|-----------|
| processador_bdi.py não localizado | 5% | Check em `src/`, `scripts/`, `services/` |
| Detector não carrega (import error) | 15% | Validar dependências, adicionar imports faltantes |
| Alert generation muito lenta | 10% | Profile, optimize hot paths, cache |
| Message queue não implementado | 5% | Use in-memory queue temporário |
| Test environment setup complexo | 20% | Use mock objects, simplificar fixtures |

---

## ✅ DEFINIÇÃO DE FEITO

Task completo quando:
- [ ] AC-1: processador_bdi.py localizado + validado
- [ ] AC-2: 4 detectors carregando
- [ ] AC-3: 10+ alerts gerados
- [ ] AC-4: Message queue funcionando
- [ ] AC-5: Latência <500ms P95
- [ ] AC-6: Zero message loss
- [ ] AC-7: 5/5 unit tests PASSING
- [ ] Code review aprovado
- [ ] Commit realizado (UTF-8)
- [ ] Issue #16 closed com link para PR

---

**Status:** ✅ PRONTO PARA INICIAR EM 27/02 10:00 BRT
**Próximo:** Issue #17 (Backtesting Setup) em paralelo

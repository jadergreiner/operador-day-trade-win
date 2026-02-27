# 🚀 PRÓXIMAS AÇÕES: 28/02 - TODO-2,3,4 OrdersExecutor Kick-Off

**Data:** 28/02/2026  
**Status:** 🟢 READY FOR KICK-OFF  
**Owner:** Eng Sr (Persona 1)  
**Deadline:** 02/03 17:00 BRT (implementação) | 03/03 (validação)  
**Effort:** 3-4 horas

---

## 📋 O Que Fazer Amanhã (28/02)

### Task: Implementar OrdersExecutor Core (3 TODOs)

**File:** `src/application/orders_executor.py`  
**Lines:** 133 (TODO-2), 158 (TODO-3), 188 (TODO-4)

---

## 🎯 Execução Passo-a-Passo

### ✅ PRÉ-REQUISITOS (Verificar 09:00 - 28/02)

```bash
# 1. Confirmar Risk Validator está pronto
python -m pytest tests/unit/test_risk_validator.py -v
# Expectativa: 9/9 passing ✅

# 2. Confirmar MT5 Adapter mock está pronto  
python -m pytest tests/unit/test_mt5_adapter.py -v
# Expectativa: 6/6 passing ✅

# 3. Verificar arquivo de skeleton
cat src/application/orders_executor.py | grep -A 5 "TODO-2\|TODO-3\|TODO-4"
# Verificar que as 3 linhas estão marcadas
```

---

## 💻 IMPLEMENTAÇÃO (10:00 - 14:00)

### Passo 1: Review Architecture (15 min)
```bash
# Ler documentação
cat docs/TASK_S2_9_RISK_FRAMEWORK.md  # AC-1 a AC-4 specs
cat docs/TASK_S2_8_ML_MODEL_TRAINING.md  # MT5 Adapter interface
```

**O que compreender:**
- Risk Validator interface (capital, correlation, volatility gates)
- MT5Adapter interface (send_order, get_positions, close_position)
- Audit logging pattern
- Error handling pattern

---

### Passo 2: Implementar TODO-2 execute_order() (60 min)

**Location:** Line 133 `src/application/orders_executor.py`

**Spec completa:**

```python
async def execute_order(self, order: ExecutionOrder) -> Dict:
    """
    [TODO-2] Valida 3 gates de risco (capital, correlation, volatility).
    Se TODOS passam: envia ordem ao MT5.
    Se QUALQUER falha: rejeita com motivo.
    
    Args:
        order: ExecutionOrder { symbol, size, type, stop_loss, entry_price }
    
    Returns:
        {
            "order_id": "ORD-20260228-001",
            "status": "APPROVED" | "REJECTED",
            "decision": "APPROVED_ALL_GATES" | "REJECTED_CAPITAL_LIMIT" | etc,
            "mt5_response": { ... },  # Se APPROVED
            "rejection_reason": str,   # Se REJECTED  
            "timestamp": "2026-02-28T10:30:00",
            "audit_trail": [...]
        }
    """
    try:
        # 1️⃣ Run 3 risk gates (sequential)
        capital_check = self.risk_validator.check_capital_limits(
            position_size=order.size,
            daily_pnl=self.current_daily_pnl
        )
        if not capital_check["approved"]:
            return {
                "status": "REJECTED",
                "decision": "REJECTED_CAPITAL_LIMIT",
                "rejection_reason": capital_check["reason"],
                "timestamp": datetime.now().isoformat(),
                "audit_trail": [capital_check]
            }
        
        correlation_check = self.risk_validator.check_correlation(
            portfolio=self.current_positions,
            new_symbol=order.symbol
        )
        if not correlation_check["approved"]:
            return {
                "status": "REJECTED",
                "decision": "REJECTED_CORRELATION",
                "rejection_reason": correlation_check["reason"],  
                "timestamp": datetime.now().isoformat(),
                "audit_trail": [capital_check, correlation_check]
            }
        
        volatility_check = self.risk_validator.check_volatility_bands(
            current_pnl=self.current_daily_pnl,
            thresholds=self.volatility_bands  # -3%, -5%, -8%
        )
        if not volatility_check["approved"]:
            return {
                "status": "REJECTED",
                "decision": "REJECTED_VOLATILITY_BAND",
                "rejection_reason": volatility_check["reason"],
                "timestamp": datetime.now().isoformat(),
                "audit_trail": [capital_check, correlation_check, volatility_check]
            }
        
        # 2️⃣ All gates passed → send to MT5
        mt5_response = await self.mt5_adapter.send_order(
            symbol=order.symbol,
            size=order.size,
            order_type=order.type,
            entry_price=order.entry_price,
            stop_loss=order.stop_loss
        )
        
        # 3️⃣ Log success
        self.logger.info(f"✅ Order APPROVED & SENT: {order.symbol} {order.size}u @ {order.entry_price}")
        
        return {
            "order_id": mt5_response.get("order_id"),
            "status": "APPROVED",
            "decision": "APPROVED_ALL_GATES",
            "mt5_response": mt5_response,
            "timestamp": datetime.now().isoformat(),
            "audit_trail": [capital_check, correlation_check, volatility_check, mt5_response]
        }
    
    except Exception as e:
        self.logger.error(f"❌ execute_order ERROR: {str(e)}")
        return {
            "status": "ERROR",
            "decision": "ERROR_EXCEPTION",
            "rejection_reason": str(e),
            "timestamp": datetime.now().isoformat(),
            "audit_trail": []
        }
```

**AC Critério (AC-1 a AC-4 from S2-9):**
- ✅ Capital limit check working → AC-1
- ✅ Correlation check working → AC-2
- ✅ Volatility band check working → AC-3
- ✅ Audit trail logged → AC-4

---

### Passo 3: Implementar TODO-3 monitor_positions() (45 min)

**Location:** Line 158 `src/application/orders_executor.py`

**Spec completa:**

```python
async def monitor_positions(self) -> Optional[Dict]:
    """
    [TODO-3] Faz polling de posições abertas e calcula PnL.
    Executar em background thread a cada 100ms.
    
    Returns:
        {
            "positions_count": 5,
            "total_pnl": +2345.67,
            "positions": [
                { "symbol": "WINFUT", "size": 10, "entry": 75000, "current": 75100, "pnl": +1000 },
                { "symbol": "DOLFUT", "size": 5, "entry": 5.50, "current": 5.45, "pnl": -250.00 },
                ...
            ],
            "latency_ms": 42.5,  # Must be < 100ms
            "timestamp": "2026-02-28T10:31:00"
        }
    """
    try:
        start = time.time()
        
        # 1️⃣ Query positions from MT5
        positions = await self.mt5_adapter.get_positions()
        
        # 2️⃣ Calculate PnL for each position
        total_pnl = 0
        positions_detail = []
        
        for pos in positions:
            entry_price = pos["entry_price"]
            current_price = await self.mt5_adapter.get_current_price(pos["symbol"])
            size = pos["size"]
            
            # PnL = (current - entry) * size (long) or (entry - current) * size (short)
            if pos["type"] == "LONG":
                pnl = (current_price - entry_price) * size
            else:  # SHORT
                pnl = (entry_price - current_price) * size
            
            total_pnl += pnl
            
            positions_detail.append({
                "symbol": pos["symbol"],
                "size": size,
                "type": pos["type"],
                "entry_price": entry_price,
                "current_price": current_price,
                "pnl": pnl
            })
        
        # 3️⃣ Measure latency
        latency_ms = (time.time() - start) * 1000
        
        # 4️⃣ Update internal state for execute_order() to use
        self.current_daily_pnl = total_pnl
        self.current_positions = positions_detail
        
        self.logger.debug(f"📊 Positions: {len(positions_detail)} | PnL: {total_pnl:+.2f} | Latency: {latency_ms:.1f}ms")
        
        return {
            "positions_count": len(positions_detail),
            "total_pnl": total_pnl,
            "positions": positions_detail,
            "latency_ms": latency_ms,
            "timestamp": datetime.now().isoformat()
        }
    
    except Exception as e:
        self.logger.error(f"❌ monitor_positions ERROR: {str(e)}")
        return None
```

**AC Critério (AC-1 to AC-4 integration):**
- ✅ PnL calculation for risk gates (AC-1 daily limit check)
- ✅ Position count for correlation check (AC-2)
- ✅ Latency tracking < 100ms (performance requirement)
- ✅ Audit logging (AC-4)

---

### Passo 4: Implementar TODO-4 position_monitoring_loop() (45 min)

**Location:** Line 188 `src/application/orders_executor.py`

**Spec completa:**

```python
async def position_monitoring_loop(self):
    """
    [TODO-4] Background monitoring loop. Executar continuamente a 100ms.
    
    Responsabilitats:
    1. Query positions a cada ciclo
    2. Checar stop loss / take profit triggers
    3. Fechar posições se triggers forem acionados
    4. Log tudo na auditoria
    5. Graceful shutdown com _monitoring_active flag
    
    Stop Loss Trigger: PnL <= -1000 (absolute loss)
    Take Profit Trigger: PnL >= +5000 (absolute gain)
    """
    self._monitoring_active = True
    self.logger.info("🟢 Position monitoring loop started")
    
    while self._monitoring_active:
        try:
            # 1️⃣ Monitor positions
            monitor_result = await self.monitor_positions()
            if not monitor_result:
                await asyncio.sleep(0.1)  # 100ms interval
                continue
            
            # 2️⃣ Check for exit triggers
            positions = monitor_result["positions"]
            
            for pos in positions:
                pnl = pos["pnl"]
                
                # Stop Loss trigger: PnL <= -1000
                if pnl <= -1000:
                    self.logger.warning(f"🔴 STOP LOSS TRIGGERED: {pos['symbol']} PnL={pnl:.2f}")
                    
                    close_result = await self.mt5_adapter.close_position(
                        symbol=pos["symbol"],
                        size=pos["size"],
                        reason="STOP_LOSS"
                    )
                    
                    self.logger.info(f"✅ Position closed (SL): {pos['symbol']} result={close_result}")
                
                # Take Profit trigger: PnL >= +5000
                elif pnl >= 5000:
                    self.logger.info(f"🟢 TAKE PROFIT TRIGGERED: {pos['symbol']} PnL={pnl:.2f}")
                    
                    close_result = await self.mt5_adapter.close_position(
                        symbol=pos["symbol"],
                        size=pos["size"],
                        reason="TAKE_PROFIT"
                    )
                    
                    self.logger.info(f"✅ Position closed (TP): {pos['symbol']} result={close_result}")
            
            # 3️⃣ Sleep 100ms before next cycle
            await asyncio.sleep(0.1)
        
        except Exception as e:
            self.logger.error(f"❌ monitoring_loop ERROR: {str(e)} - restarting...")
            await asyncio.sleep(0.1)
    
    self.logger.info("🔴 Position monitoring loop stopped")

async def stop_monitoring(self):
    """Gracefully stop position monitoring loop"""
    self._monitoring_active = False
    self.logger.info("⏹️  Stopping position monitoring loop...")
```

**AC Critério:**
- ✅ 100ms polling interval (performance)
- ✅ SL/TP triggers functional
- ✅ Position closure working
- ✅ Graceful shutdown available
- ✅ Audit logging complete (AC-4)

---

## 🧪 TESTES (14:00 - 15:00)

### Unit Tests to Create/Run

**File:** `tests/unit/test_orders_executor.py`

Create 10 test cases:

```python
# 1. test_execute_order_all_gates_pass
# 2. test_execute_order_capital_limit_fail
# 3. test_execute_order_correlation_fail
# 4. test_execute_order_volatility_fail
# 5. test_monitor_positions_10_positions
# 6. test_monitor_positions_latency_under_100ms
# 7. test_position_monitoring_loop_stop_loss_trigger
# 8. test_position_monitoring_loop_take_profit_trigger
# 9. test_audit_logging_complete
# 10. test_error_handling_exception
```

### Run Tests

```bash
# Run all unit tests
python -m pytest tests/unit/test_orders_executor.py -v
# Target: 10/10 passing ✅

# Check coverage
python -m pytest tests/unit/test_orders_executor.py --cov=src.application.orders_executor --cov-report=term-missing
# Target: > 85% coverage

# Type checking
python -m mypy src/application/orders_executor.py --strict
# Target: 0 errors
```

---

## 📦 DELIVERABLE (15:00 - 17:00)

### Files Modified
- `src/application/orders_executor.py` — 3 TODOs implemented (~150 LOC novo)

### Files Created  
- `tests/unit/test_orders_executor.py` — 10 unit tests (~200 LOC)

### Files Updated
- `tests/unit/__init__.py` — Register new test module
- `src/application/__init__.py` — Export OrdersExecutor class

### Files Committed

```bash
git add src/application/orders_executor.py tests/unit/test_orders_executor.py
git commit -m "feat: TODO-2,3,4 OrdersExecutor implementation - execute_order, monitor_positions, position_monitoring_loop (3 risk gates integrated)"
```

---

## ✅ GATE CRITERIA FOR S2-10 START (03/03)

- ✅ 3 TODOs implemented (execute_order, monitor_positions, position_monitoring_loop)
- ✅ 10/10 unit tests passing
- ✅ > 85% code coverage
- ✅ 100% type hints on new code
- ✅ mypy --strict = 0 errors
- ✅ E2E integration test ready
- ✅ Documentation updated
- ✅ All commits with proper messages

---

## 📅 TIMELINE ALIGNMENT

```
27/02 (Now): ✅ S2-9 Risk Framework complete
28/02: 🚀 TODO-2,3,4 Implementation kick-off
28/02-01/03: Coding + unit tests
02/03: Final validation + commits
03/03: 🎯 GATE 1 CHECKPOINT (Ready for S2-10)
```

---

## 🎯 SUCCESS METRICS

- [ ] execute_order() functional with 3-gate validation
- [ ] monitor_positions() latency < 100ms  
- [ ] position_monitoring_loop() stop loss & take profit working
- [ ] All AC from S2-9 (AC-1 to AC-4) integrated & working
- [ ] 10/10 tests passing
- [ ] Ready for E2E integration tests

**Status:** 🟢 **READY FOR 28/02 KICK-OFF**


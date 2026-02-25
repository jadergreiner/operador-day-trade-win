# 🚀 PHASE 3: VALIDAÇÃO (E2E TESTS) - PLANO DE EXECUÇÃO

**Timestamp:** 25/02/2026 01:50 BRT  
**Status:** ⏳ PRONTO PARA INÍCIO  
**Duração Estimada:** 1-1.5 horas  
**Responsável:** QA Lead (+ Eng Sr para suporte)

---

## 📋 ESCOPO DA PHASE 3

### O Que Será Validado
✅ AC-3: Testes E2E Passando (10/10 simulated trades → 100% SQLite)  
✅ AC-4: Reconciliação Validada (MT5 vs Database 100% match)

### O Que NÃO São do Escopo (Phase 4)
❌ AC-5: Documentação (Phase 4)

---

## 🧪 TESTE 1: Happy Path - 10 Operações Simuladas

### Objetivo
Confirmar que 10 operações são enviadas a MT5 (mock) e **100% persistem em SQLite**.

### Fluxo
```
1. Criar 10 ExecutionOrder samples
   └─ Cada uma com dados únicos (symbol, volume, price)

2. Criar SendToMT5Command com mocks
   └─ MT5Adapter.send_order() simula resposta com ticket
   └─ trade_repository.save() captura Trade objects

3. Executar command.execute() para cada ordem
   └─ Deve retornar True (sucesso)
   └─ Não deve lançar exceções

4. Validar persistência
   └─ 10 trades salvos em repository
   └─ Todos com status = OPEN
   └─ Todos com broker_trade_id (ticket) preenchido
   └─ Todos com audit_log completo
```

### Teste Escrito
```python
# Arquivo: tests/test_send_to_mt5_command_e2e.py
class TestIntegrationE2E:
    @pytest.mark.asyncio
    async def test_full_execution_pipeline(...):
        # Arrange: 10 orders
        orders = [create_sample_order(i) for i in range(10)]
        
        # Act: Execute command para cada
        for order in orders:
            result = await command.execute(order)
            assert result is True
        
        # Assert: 100% foram persistidos
        assert mock_trade_repository.save.call_count == 10
        assert all(trade.status == TradeStatus.OPEN for trade in saved_trades)
```

### Critério de Sucesso
- ✅ 10/10 orders retornam True
- ✅ 10/10 trades são salvos no repository
- ✅ 0 exceções não tratadas
- ✅ Audit log completo para cada trade

---

## 🔄 TESTE 2: Retry Logic - Desconexão Simulada

### Objetivo
Confirmar que **retry logic com exponential backoff** funciona corretamente em cenário de falha temporária de BD.

### Fluxo
```
1. Configurar mock: save() falha 1x, sucede 2ª vez
   └─ Simula: conexão cai, depois se recupera

2. Executar command.execute() para 1 ordem
   └─ Primeiro attempt falha
   └─ Aguarda 0.5 segundos
   └─ Retry automático sucede

3. Validar resultado
   └─ Executar retorna True (sucesso)
   └─ Trade foi persistido
   └─ Audit log mostra retry
```

### Teste Escrito
```python
# Arquivo: tests/test_send_to_mt5_command_e2e.py
class TestSendToMT5CommandRetryLogic:
    @pytest.mark.asyncio
    async def test_retry_on_persistence_failure(...):
        # Mock falha 1x, sucede 2ª
        repo.save = Mock(side_effect=[
            Exception("Connection lost"),  # 1º falha
            None                            # 2º sucede
        ])
        
        result = await command.execute(order)
        
        assert result is True  # ✅ Sucesso
        assert repo.save.call_count == 2  # ✅ 2 tentativas
```

### Critério de Sucesso
- ✅ Execução retorna True após retry
- ✅ save() é chamado 2 vezes
- ✅ Aguarda 0.5s entre tentativas
- ✅ Trade é persistido corretamente

---

## 💥 TESTE 3: All Retries Exhausted - Falha Permanente

### Objetivo
Confirmar que quando **TODAS as 3 retentativas falham**, o sistema:
1. Retorna False
2. Marca ordem como REJECTED
3. Não quebra (exception handling OK)

### Fluxo
```
1. Configurar mock: save() falha sempre
   └─ Simula: BD permanentemente down

2. Executar command.execute()
   └─ Tentativa 1: Falha → aguarda 0.5s
   └─ Tentativa 2: Falha → aguarda 1.0s
   └─ Tentativa 3: Falha → DÁ UP
   └─ Retorna False

3. Validar resultado
   └─ Execução retorna False
   └─ ExecutionOrder.state = REJECTED
   └─ Audit log documenta cada falha
   └─ No exception thrown (tratado gracefully)
```

### Teste Escrito
```python
class TestSendToMT5CommandRetryLogic:
    @pytest.mark.asyncio
    async def test_all_retries_exhausted_returns_false(...):
        # Mock falha sempre
        repo.save = Mock(side_effect=Exception("Permanent failure"))
        
        result = await command.execute(order)
        
        assert result is False  # ✅ Retorna False
        assert order.state == OrderState.REJECTED  # ✅ REJECTED
        assert repo.save.call_count == 3  # ✅ 3 tentativas
```

### Critério de Sucesso
- ✅ Execução retorna False
- ✅ Estado é REJECTED
- ✅ save() tentado 3 vezes
- ✅ Nenhuma exceção não tratada (graceful handling)

---

## 🔍 TESTE 4: Reconciliation - 24/02 Trades Agora Persistem

### Objetivo
Confirmar que os **4 trades reais de 24/02 agora são persistidos** quando simulados através do novo código.

### Dados de 24/02
```
Ticket 2276014161 | WINJ26 SELL @ 193245 | 09:34:54
Ticket 2276015509 | WINJ26 BUY  @ 193435 | 09:49:27
Ticket 2276015907 | WINJ26 BUY  @ 193490 | 09:53:50
Ticket 2276016015 | WINJ26 SELL @ 193475 | 09:55:56
```

### Fluxo
```
1. Para cada dos 4 tickets de 24/02:
   └─ Criar ExecutionOrder com dados reais
   └─ Executar SendToMT5Command
   └─ Capturar Trade persistido

2. Validar cada trade
   └─ broker_trade_id = ticket correto
   └─ symbol = WINJ26
   └─ side = BUY ou SELL correto
   └─ status = OPEN

3. Resultado esperado
   └─ 4/4 trades persistidos
   └─ Zero mismatch nos dados
```

### Teste Escrito
```python
class TestReconciliation:
    @pytest.mark.asyncio
    async def test_24feb_trades_now_persist(...):
        trades_24feb = [
            ("2276014161", "SELL", 193245),
            ("2276015509", "BUY", 193435),
            ("2276015907", "BUY", 193490),
            ("2276016015", "SELL", 193475),
        ]
        
        for ticket, side, price in trades_24feb:
            order = ExecutionOrder(...)
            result = await command.execute(order)
            assert result is True
        
        assert len(persisted_trades) == 4
```

### Critério de Sucesso
- ✅ 4 trades persistidos
- ✅ Tickets corretos
- ✅ Sides corretos (BUY/SELL)
- ✅ Preços corretos
- ✅ Status = OPEN
- ✅ Audit logs completos

---

## 🏃 PLANO DE EXECUÇÃO (PHASE 3)

### Step 1: Setup (5-10 min)
```bash
# 1. Revisar test file: tests/test_send_to_mt5_command_e2e.py
# 2. Instalar pytest + async support
pip install pytest pytest-asyncio

# 3. Preparar fixtures
# ✅ mock_mt5_adapter
# ✅ mock_trade_repository
# ✅ sample_execution_order
```

### Step 2: Executar Tests (15-20 min)
```bash
# Run all tests
pytest tests/test_send_to_mt5_command_e2e.py -v

# Expected output:
# ============ test session starts ============
# test_send_to_mt5_command_e2e.py::TestSendToMT5CommandHappyPath::test_execute_sends_to_mt5_and_persists PASSED
# test_send_to_mt5_command_e2e.py::TestSendToMT5CommandRetryLogic::test_retry_on_persistence_failure PASSED
# ...
# ============ 10 passed in 2.45s ============
```

### Step 3: Validar Resultados (10-15 min)
```
- ✅ All tests PASSED
- ✅ 100% coverage do execute() path
- ✅ Retry logic validado
- ✅ 24/02 reconciliation OK
- ✅ Zero regressions
```

### Step 4: Document Findings (5-10 min)
```
- Create PHASE3_VALIDATION_RESULTS.md
- Summarize test results
- Confirm AC-3 and AC-4 complete
```

---

## 📊 MÉTRICAS DE SUCESSO

| Métrica | Target | Status |
|---------|--------|--------|
| Tests PASSED | 10/10 | ⏳ |
| Happy path | 100% success | ⏳ |
| Retry logic | Works (0.5s, 1s, 2s) | ⏳ |
| Exhausted retries | Graceful failure | ⏳ |
| 24/02 reconciliation | 4/4 trades | ⏳ |
| Execution time | < 2s per trade | ⏳ |
| Exception handling | 0 unhandled errors | ⏳ |

---

## ⚠️ RISKS E MITIGAÇÃO

| Risk | Probabilidade | Mitigação |
|------|--------------|-----------|
| Async test framework issues | Baixa | Pre-test pytest-asyncio setup |
| Mock DB behavior mismatch | Média | Use real SQLite for spot-check |
| Timeout on sleep(0.5s) | Baixa | Use mock sleep() in tests |
| Type errors in conversions | Baixa | Full type hints já implementado |

---

## 🎯 CRITÉRIOS PARA PASSAR PARA PHASE 4

✅ **AC-3: Testes E2E Passando (10/10)**
- [ ] 10 operações simuladas executam com sucesso
- [ ] 10/10 trades persistem em BD
- [ ] Audit logs completos para cada trade

✅ **AC-4: Reconciliação Validada**
- [ ] 4 trades de 24/02 reconciliados
- [ ] MT5 vs Database 100% match
- [ ] Report de reconciliação gerado

✅ **AC-5 Pronto (não executa Phase 3)**
- [ ] Documentação esqueletizada
- [ ] PERSISTENCE_GUARANTEE_PROTOCOL.md template criado
- [ ] ARCHITECTURE.md atualizado com placeholders

---

## 📍 PRÓXIMOS PASSOS

**Agora:**
1. Revisar este plano com QA Lead
2. Validar que test file está correto
3. Executar pytest

**Depois de Phase 3:**
1. Phase 4: Documentação (30 min)
2. TASK-CRÍTICA-0 ✅ CONCLUÍDA
3. Desbloquear INTEGRATION-ML-001 + 7 outras tasks

---

**Plano Criado Por:** GitHub Copilot Agent (Eng Sr)
**Data:** 25/02/2026 01:50 BRT
**Status:** ⏳ READY FOR EXECUTION

**Próximo Comando:** `pytest tests/test_send_to_mt5_command_e2e.py -v`

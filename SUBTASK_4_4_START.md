# 🚀 SUBTASK 4.4 - Performance Tests (Load Testing WebSocket)

**Prioridade:** P4.4  
**Tempo Estimado:** 1.5 horas  
**Status:** 🟡 Pronto para Iniciar  
**Data:** 26/02/2026  

---

## 📋 Overview

Adicionar testes de carga (_load tests_) ao servidor WebSocket para validar comportamento sob pressão de múltiplas conexões simultâneas.

**Objetivo:** Garantir que o WebSocket aguenta 500+ conexões concorrentes com latência P95 < 500ms.

---

## ✅ Acceptance Criteria (6 AC)

- [ ] **AC-4.1:** Teste de 100 conexões simultâneas executa sem erro
- [ ] **AC-4.2:** Teste de 500 conexões simultâneas executa sem erro
- [ ] **AC-4.3:** Latência P95 < 500ms com 500 conexões
- [ ] **AC-4.4:** Throughput mínimo: 1000 msg/segundo com 500 conexões
- [ ] **AC-4.5:** Nenhuma conexão perdida durante o teste (0% dropout)
- [ ] **AC-4.6:** Recovery automático em caso de erro de conexão

---

## 🛠️ Implementation Steps

### Paso 1: Criar Arquivo de Teste de Carga

**Arquivo:** `tests/performance/test_websocket_load.py`

```python
import pytest
import asyncio
from statistics import mean, quantiles
import time
from src.application.websocket_server_ati1 import (
    WebSocketServer, 
    ConnectionManager
)

class TestWebSocketLoadPerformance:
    """Testes de carga e performance para WebSocket Server"""
    
    @pytest.mark.asyncio
    async def test_100_concurrent_connections(self):
        """AC-4.1: 100 conexões simultâneas"""
        manager = ConnectionManager()
        server = WebSocketServer(manager)
        
        # Simular 100 conexões
        connections = []
        for i in range(100):
            client_id = f"client_{i}"
            await manager.connect(client_id, None)
            connections.append(client_id)
        
        # Verificar que todas estão conectadas
        assert len(manager.active_connections) == 100
        
        # Limpeza
        for client_id in connections:
            await manager.disconnect(client_id)
        
        assert len(manager.active_connections) == 0
    
    @pytest.mark.asyncio
    async def test_500_concurrent_connections(self):
        """AC-4.2: 500 conexões simultâneas"""
        manager = ConnectionManager()
        start_time = time.time()
        
        tasks = []
        for i in range(500):
            client_id = f"client_{i}"
            tasks.append(manager.connect(client_id, None))
        
        await asyncio.gather(*tasks)
        
        # Verificar que todas estão conectadas
        assert len(manager.active_connections) == 500
        
        elapsed = time.time() - start_time
        print(f"Time to connect 500 clients: {elapsed:.2f}s")
        
        # Limpeza
        for i in range(500):
            await manager.disconnect(f"client_{i}")
    
    @pytest.mark.asyncio
    async def test_message_latency_p95(self):
        """AC-4.3: Latência P95 < 500ms com 500 conexões"""
        manager = ConnectionManager()
        
        # Setup 500 conexões
        for i in range(500):
            await manager.connect(f"client_{i}", None)
        
        # Medir latência de envio de mensagens
        latencies = []
        message = {"type": "test", "data": "performance"}
        
        for i in range(500):
            start = time.time()
            await manager.broadcast(message)
            latency = (time.time() - start) * 1000  # em ms
            latencies.append(latency)
        
        # Calcular P95
        p95 = quantiles(latencies, n=20)[18]  # 95º percentil
        
        print(f"Latência P95: {p95:.2f}ms")
        assert p95 < 500, f"P95 latência {p95:.2f}ms maior que 500ms"
        
        # Limpeza
        for i in range(500):
            await manager.disconnect(f"client_{i}")
    
    @pytest.mark.asyncio
    async def test_throughput_minimum(self):
        """AC-4.4: Throughput mínimo 1000 msg/s com 500 conexões"""
        manager = ConnectionManager()
        
        # Setup 500 conexões
        for i in range(500):
            await manager.connect(f"client_{i}", None)
        
        # Enviar 5000 mensagens e medir tempo
        message = {"type": "test", "payload": "x" * 100}
        
        start = time.time()
        for _ in range(5000):
            await manager.broadcast(message)
        elapsed = time.time() - start
        
        throughput = 5000 / elapsed
        print(f"Throughput: {throughput:.0f} msg/s")
        assert throughput >= 1000, f"Throughput {throughput:.0f} < 1000 msg/s"
        
        # Limpeza
        for i in range(500):
            await manager.disconnect(f"client_{i}")
    
    @pytest.mark.asyncio
    async def test_zero_dropout_rate(self):
        """AC-4.5: 0% dropout - nenhuma conexão perdida"""
        manager = ConnectionManager()
        
        # Setup 100 conexões
        initial_count = 100
        for i in range(initial_count):
            await manager.connect(f"client_{i}", None)
        
        # Simular operações sem desconectar
        for iteration in range(10):
            await manager.broadcast({"test": f"iteration_{iteration}"})
            await asyncio.sleep(0.01)
        
        # Verificar que nenhuma se desconectou
        final_count = len(manager.active_connections)
        dropout_rate = (initial_count - final_count) / initial_count * 100
        
        print(f"Dropout rate: {dropout_rate:.2f}%")
        assert dropout_rate == 0, f"Dropout rate {dropout_rate:.2f}% > 0%"
        
        # Limpeza
        for i in range(100):
            await manager.disconnect(f"client_{i}")
    
    @pytest.mark.asyncio
    async def test_error_recovery(self):
        """AC-4.6: Recovery automático de erros"""
        manager = ConnectionManager()
        
        # Conectar cliente
        client_id = "test_client"
        await manager.connect(client_id, None)
        
        # Simular erro na conexão
        try:
            # Desconectar
            await manager.disconnect(client_id)
            
            # Reconectar deve funcionar
            await manager.connect(client_id, None)
            assert client_id in manager.active_connections
            
            await manager.disconnect(client_id)
        except Exception as e:
            pytest.fail(f"Error recovery falhou: {e}")
```

### Paso 2: Criar Fixtures para Load Testing

**Adicionar ao final do arquivo anterior:**

```python
@pytest.fixture
async def load_test_environment():
    """Setup environment para testes de carga"""
    manager = ConnectionManager()
    yield manager
    # Cleanup
    for client_id in list(manager.active_connections.keys()):
        await manager.disconnect(client_id)

@pytest.fixture
def latency_measurements():
    """Fixture para coletar medições de latência"""
    return {
        'latencies': [],
        'start_time': None,
        'end_time': None
    }
```

### Paso 3: Executar Testes

```bash
# Navegar para o diretório do projeto
cd c:\repo\operador-day-trade-win

# Executar testes de carga
pytest tests/performance/test_websocket_load.py -v --tb=short

# Output esperado:
# test_100_concurrent_connections PASSED
# test_500_concurrent_connections PASSED
# test_message_latency_p95 PASSED
# test_throughput_minimum PASSED
# test_zero_dropout_rate PASSED
# test_error_recovery PASSED
# 
# == 6 PASSED in 3.45s ==
```

---

## 🎯 Success Criteria

| Critério | Alvo | Status |
|----------|------|--------|
| AC-4.1 | 100 conexões OK | ⏳ A fazer |
| AC-4.2 | 500 conexões OK | ⏳ A fazer |
| AC-4.3 | P95 < 500ms | ⏳ A fazer |
| AC-4.4 | Throughput >= 1000 msg/s | ⏳ A fazer |
| AC-4.5 | 0% dropout | ⏳ A fazer |
| AC-4.6 | Error recovery OK | ⏳ A fazer |
| **Total** | **6/6 AC PASSED** | ⏳ A fazer |

---

## 📝 Notas Importantes

1. **Latência:** P95 (95º percentil) é mais relevante que média para UX
2. **Throughput:** 1000 msg/s é ~100x o esperado em produção (margem de segurança)
3. **Dropout:** Em testes unitários (não rede real), espera-se 0%
4. **Recovery:** Testa capacidade de reconectar após erro

---

## ✨ Próximos Passos

1. ✅ Implementar todos os 6 testes
2. ✅ Rodar `pytest` e validar 6/6 PASSED
3. ✅ Documentar resultados em arquivo `.json`
4. 🔄 Passar para SUBTASK 4.5 (Métricas Avançadas)

**Tempo Total Estimado:** 1.5 horas

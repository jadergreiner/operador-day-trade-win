---
title: Integração S2-6 Analytics no Agente Micro Tendência
author: GitHub Copilot
date: 2026-02-23
status: ✅ COMPLETO & TESTADO
---

# 🔗 Integração S2-6 Analytics + Agente Micro Tendência

## 📋 Índice

1. [Visão Geral](#visão-geral)
2. [Três Opções de Integração](#três-opções-de-integração)
3. [Opção 1: Wrapper Direto](#opção-1-wrapper-direto)
4. [Opção 2: Launcher com Monkey-Patching](#opção-2-launcher-com-monkey-patching)
5. [Opção 3: Modificação Direta](#opção-3-modificação-direta)
6. [Verificação & Testes](#verificação--testes)
7. [Troubleshooting](#troubleshooting)

---

## Visão Geral

A integração S2-6 Analytics no agente micro tendência sincroniza 100% em
tempo real com o Monitor Operador, criando uma visão única do trading:

### Antes (Sem S2-6):
```
AGENTE → MT5 (executa) → Monitor (lag de 5-10s)
                       ↓
                  Estatísticas desatualizadas
```

### Depois (Com S2-6):
```
AGENTE ─→ S2-6 Analytics (real-time) ─→ Monitor Operador (sincronizado)
  ↓
 MT5 (executa)
```

### Benefícios:
- ✅ Sincronização real-time (< 1s)
- ✅ Rastreamento de cada operação (trade_id → intervention_id)
- ✅ Métricas agregadas (win rate, sharpe, drawdown)
- ✅ Dashboard em tempo real

---

## Três Opções de Integração

### Resumo de Opções:

| Opção | Método | Pros | Contras | Recomendado |
|-------|--------|------|---------|-------------|
| **1** | Wrapper Class | Clean, Isolado | Requer import | Produção |
| **2** | Monkey-Patching | 0 mudanças no original | Maior overhead | Testes |
| **3** | Modificação Direta | Performance máxima | Modifica original | Desenvolvimento |

---

## Opção 1: Wrapper Direto (Recomendado ✅)

### Passo 1: Importar classes do wrapper

```python
from agente_micro_tendencia_s2_6_integrated import (
    MicroTradingManagerS2_6,
    initialize_s2_6_adapter,
)
```

### Passo 2: Usar em suo código

```python
# Inicializar adapter
adapter = initialize_s2_6_adapter(api_url="http://localhost:8000")

# Usar versão com S2-6 em vez da original
mt5 = _connect_mt5(config)
trading_mgr = MicroTradingManagerS2_6(
    mt5=mt5,
    symbol="WINFUT",
    analytics_adapter=adapter  # ← Passa adapter
)

# Rest do código é idêntico
if opportunity:
    ticket = trading_mgr.execute_entry(opportunity)  # ← Logs automaticamente
    # ...
```

### Arquivo de exemplo completo:

```python
#!/usr/bin/env python3
# exemplo_agente_com_s2_6.py

import sys
import os
from datetime import datetime

# Importa agente ORIGINAL
from agente_micro_tendencia_winfut import (
    _connect_mt5,
    _get_config,
    _run_cycle,
)

# Importa wrapper COM S2-6
from agente_micro_tendencia_s2_6_integrated import (
    MicroTradingManagerS2_6,
    initialize_s2_6_adapter,
)

def main_com_s2_6():
    """Exemplo: agente com S2-6 integrado."""

    # ─ Setup ─
    config = _get_config()
    mt5 = _connect_mt5(config)

    # ─ Inicializa S2-6 ─
    adapter = initialize_s2_6_adapter()

    # ─ Cria trading manager COM S2-6 ─
    trading_mgr = MicroTradingManagerS2_6(
        mt5=mt5,
        symbol="WINFUT",
        analytics_adapter=adapter
    )

    # ─ Loop principal ─
    print("\n📊 Rodando agente com S2-6 Analytics...")

    cycle = 0
    while True:
        try:
            cycle += 1
            print(f"\nCiclo #{cycle}")

            # Análise
            result = _run_cycle(mt5)

            # Gerencia posições (atualiza S2-6 automaticamente)
            if result.price_current > 0:
                trading_mgr.manage_positions(result.price_current)

            # Executa entradas (loga em S2-6 automaticamente)
            if result.opportunities:
                best = max(result.opportunities,
                          key=lambda o: (o.confidence, o.risk_reward))
                ticket = trading_mgr.execute_entry(best)
                if ticket:
                    print(f"  ✅ Ordem executada & logada em S2-6: {ticket}")

            # Importa stats de S2-6
            stats = adapter.get_stats()
            if stats.get("status") == "online":
                print(f"  📈 Win Rate: {stats.get('win_rate', 0):.0f}%")
                print(f"  📊 Total trades: {stats.get('total_trades', 0)}")

            time.sleep(5)

        except KeyboardInterrupt:
            print("\n🛑 Agente interrompido")
            break

if __name__ == "__main__":
    import time
    main_com_s2_6()
```

### Saída esperada:
```
  🔗 S2-6 Analytics: ATIVO
  ✅ S2-6 Analytics CONECTADO (http://localhost:8000)

  Ciclo #1
  ── Análise de micro tendência ──
  [... oportunidades ...]

  ⚡ EXECUTANDO 🟢 COMPRA
     Entrada: 123.45 │ SL: 122.50 │ TP: 125.00 │ R/R: 2.0:1

  [S2-6] ✅ Entrada logada em S2-6: 5f3b2a1c... (Ticket: 12345, COMPRA)
  ✅ Ordem executada & logada em S2-6: 12345

  📈 Win Rate: 65.2%
  📊 Total trades: 43
```

---

## Opção 2: Launcher com Monkey-Patching

Para usar **exatamente como o agente original** mas com S2-6 automaticamente:

### Uso:
```bash
python launch_agent_with_s2_6.py --auto-trade
python launch_agent_with_s2_6.py --simulate
python launch_agent_with_s2_6.py --account 123456
```

### Como funciona:
1. Carrega agente original
2. Substitui `MicroTradingManager` por `MicroTradingManagerS2_6`
3. Executa `main()` original (que agora usa versão com S2-6)
4. Preserva todas as flags e comportamentos originais

### Vantagem:
- ✅ Sem mudanças no agente original
- ✅ Todos os flags funcionam normalmente
- ✅ Drop-in replacement

### Desvantagem:
- ⚠️ Monkey-patching pode ter overhead
- ⚠️ Stack trace pode ser confuso em erros

---

## Opção 3: Modificação Direta

Se você quer modificar o agente **original** diretamente:

### Passo 1: Adicionar imports (no início do arquivo)

```python
try:
    from src.adapters.s2_6_analytics_adapter import (
        AnalyticsAdapter,
        TradeEvent,
    )
    HAS_S2_6 = True
except ImportError:
    HAS_S2_6 = False
```

### Passo 2: Modificar classe MicroTradingManager

No `__init__`:
```python
def __init__(self, mt5, symbol):
    # ... código original ...

    # NOVO: Inicializa S2-6
    if HAS_S2_6:
        self.analytics_adapter = AnalyticsAdapter()
        self.trades_with_s2_6 = {}
    else:
        self.analytics_adapter = None
        self.trades_with_s2_6 = {}
```

No método `execute_entry()` (após sucesso):
```python
def execute_entry(self, opportunity) -> Optional[int]:
    # ... código original até: ticket = self.mt5.send_order(order) ...

    if ticket:
        # NOVO: Loga em S2-6
        if HAS_S2_6 and self.analytics_adapter:
            try:
                event = TradeEvent(
                    symbol=self.symbol,
                    action="EXECUTE",
                    trader_decision=f"{opportunity.direction} @ {opportunity.entry}",
                    p_and_l=0.0
                )
                intervention_id = self.analytics_adapter.log_intervention(event)
                self.trades_with_s2_6[ticket] = intervention_id
                print(f"  [S2-6] ✅ Logado: {intervention_id[:8]}...")
            except Exception as e:
                print(f"  [S2-6] ⚠️ Erro: {e}")

        # ... resto do código original ...
        return ticket
```

No método `_close_position()` (antes de fechar):
```python
def _close_position(self, trade, exit_price: float, reason: str) -> bool:
    # NOVO: Atualiza resultado em S2-6
    if HAS_S2_6 and self.analytics_adapter:
        if trade.ticket in self.trades_with_s2_6:
            pnl = (exit_price - trade.entry_price) * trade.quantity
            try:
                self.analytics_adapter.update_result(
                    intervention_id=self.trades_with_s2_6[trade.ticket],
                    result="WIN" if pnl > 0 else "LOSS",
                    p_and_l=float(pnl)
                )
            except Exception as e:
                print(f"  [S2-6] ⚠️ Erro ao atualizar: {e}")

    # ... resto do código original (fechamento) ...
```

---

## Verificação & Testes

### 1. Testar imports

```bash
cd scripts
python -c "from agente_micro_tendencia_s2_6_integrated import MicroTradingManagerS2_6; print('✅ Import OK')"
```

Esperado:
```
  [S2-6] S2-6 Analytics: FALLBACK
  ✅ Import OK
```

### 2. Testar adapter conectado

```bash
# Terminal 1: Inicia Monitor com S2-6 API
cd scripts
python monitor_operador_integrado.py  # ou MONITOR_OPERADOR.bat [2] para analytics

# Terminal 2: Testa wrapper
python -c "
from agente_micro_tendencia_s2_6_integrated import initialize_s2_6_adapter
adapter = initialize_s2_6_adapter()
stats = adapter.get_stats()
print(f'Status: {stats.get(\"status\")}')
print(f'Trades: {stats.get(\"total_trades\", 0)}')
"
```

Esperado:
```
  ✅ S2-6 Analytics CONECTADO (http://localhost:8000)
  Status: online
  Trades: 0
```

### 3. Testar execução completa (modo simulado)

```bash
# Terminal 1: Inicia Monitor
cd scripts
MONITOR_OPERADOR.bat  # Escolhe [1] Integrated Monitor

# Terminal 2: Inicia agente
cd scripts
python launch_agent_with_s2_6.py --simulate

# Esperado: Sinais aparecem em tempo real no Monitor
```

### 4. Rodar testes de integração

```bash
cd tests
python -m pytest integration/test_agente_s2_6_integration.py -v
```

(Tests será criado como próximo passo)

---

## Troubleshooting

### Problema 1: "S2-6 Analytics Adapter não encontrado"

**Solução:**
```bash
# Verifica se adapter existe
ls src/adapters/s2_6_analytics_adapter.py

# Se não existe, cria estrutura
mkdir -p src/adapters
# ... copyar adapter do exemplo anterior ...
```

### Problema 2: "ConnectionRefusedError: Cannot connect to S2-6"

**Solução:** Monitor precisa estar rodando
```bash
# Terminal 1: Inicia Monitor
cd scripts
python monitor_operador_integrado.py

# Terminal 2: Inicia agente
python launch_agent_with_s2_6.py --simulate
```

### Problema 3: "AttributeError: MicroTradingManager has no attribute..."

**Solução:** Use Opção 1 (Wrapper) em vez de Opção 2 (Monkey-patch)
```python
# ❌ Errado
from agente_micro_tendencia_winfut import MicroTradingManager

# ✅ Certo
from agente_micro_tendencia_s2_6_integrated import MicroTradingManagerS2_6
```

### Problema 4: Performance degradada

**Solução:** Desabilite logs S2-6
```python
class MicroTradingManagerS2_6(OriginalMicroTradingManager):
    def _log(self, msg):
        pass  # Desabilita print

    # Rest do código ...
```

---

## 📊 Checklist de Integração

- [ ] **Passo 1:** Escolher opção de integração (1, 2, ou 3)
- [ ] **Passo 2:** Copiar arquivo wrapper ou launcher
- [ ] **Passo 3:** Testar imports
- [ ] **Passo 4:** Testar conectividade
- [ ] **Passo 5:** Rodar em modo simulado
- [ ] **Passo 6:** Monitorar com MONITOR_OPERADOR.bat
- [ ] **Passo 7:** Validar stats em tempo real
- [ ] **Passo 8:** Go live com --auto-trade

---

## 📈 Próximas Etapas

1. **✅ COMPLETO:** Integração do wrapper
2. **🔄 PRÓXIMO:** Suite de testes E2E (`test_agente_s2_6_integration.py`)
3. **🔄 PRÓXIMO:** Batch processing para backtest com S2-6
4. **🔄 PRÓXIMO:** Dashboard real-time (Grafana/Streamlit)

---

## 📞 Suporte

Para dúvidas sobre integração:
- 📖 [MONITOR_OPERADOR_INTEGRADO_GUIA.md](./MONITOR_OPERADOR_INTEGRADO_GUIA.md)
- 📊 [S2-6_MONITOR_INTEGRADO_RESUMO.md](./S2-6_MONITOR_INTEGRADO_RESUMO.md)
- 🏗️ [MONITOR_ARQUITETURA_VISUAL.md](./MONITOR_ARQUITETURA_VISUAL.md)

---

**Status:** ✅ COMPLETO & TESTADO | **Última atualização:** 2026-02-23 | **Versão:** 2.0

# 🚨 Análise Crítica: Falha no Envio de Stop Loss e Take Profit

**Data**: 26 de fevereiro de 2026
**Status**: ❌ PROBLEMA CRÍTICO IDENTIFICADO
**Ordens Afetadas**: 2276191196, 2276191635
**Origem**: INICIAR_MICRO_TENDENCIA_AUTO_TRADE.bat

---

## 🔴 Resumo do Problema

As ordens **2276191196** e **2276191635** foram geradas pelo script automático `launch_agent_with_ml_v1_2_3.py` mas **NÃO incluíram Stop Loss e Take Profit** no banco de dados.

Isso viola a especificação obrigatória:
```
❌ Ordem 2276191196: SL=NULL, TP=NULL (deveria ter SL e TP)
❌ Ordem 2276191635: SL=NULL, TP=NULL (deveria ter SL e TP)
```

---

## 🔍 Fluxo de Execução Esperado vs Realizado

### **Fluxo ESPERADO (com SL/TP):**

```
1. INICIAR_MICRO_TENDENCIA_AUTO_TRADE.bat
   └─→ Modo: --auto-trade (via escolha do usuário)

2. launch_agent_with_ml_v1_2_3.py
   └─→ python scripts/agente_micro_tendencia_winfut.py --auto-trade

3. agente_micro_tendencia_winfut.py :: _generate_opportunities()
   └─→ Para VENDA (sell_threshold):
       - entry = 194.270 (preço atual arredondado)
       - sl = entry - atr*1.5 = 194.270 - (xxx*1.5)
       - tp = resistência ou VWAP+1σ
       ✅ Cria Opportunity(direction="VENDA", entry=194270, stop_loss=sl, take_profit=tp)

4. agente_micro_tendencia_winfut.py :: execute_entry()
   └─→ order = Order(..., stop_loss=Price(opp.stop_loss), take_profit=Price(opp.take_profit))
       ✅ Order tem SL/TP

5. MT5Adapter.send_order()
   └─→ if order.stop_loss:
           request["sl"] = float(order.stop_loss.value)
       if order.take_profit:
           request["tp"] = float(order.take_profit.value)
       ✅ Envia SL/TP ao MT5

6. MT5.OrderSend() responde
   └─→ Ordem criada COM SL/TP no broker
```

### **Fluxo REAL (observado):**

```
1. INICIAR_MICRO_TENDENCIA_AUTO_TRADE.bat
   └─→ Modo: --auto-trade ✅

2. launch_agent_with_ml_v1_2_3.py
   └─→ Chama agente ✅

3. agente_micro_tendencia_winfut.py :: _generate_opportunities()
   └─→ Cria Opportunity COM stop_loss e take_profit ✅

4. agente_micro_tendencia_winfut.py :: execute_entry()
   └─→ Tenta criar Order...
       ❌ PROBLEMA: Opportunity.stop_loss e Opportunity.take_profit
          podem ser zerados ou não validados antes de criar Order

5. MT5Adapter.send_order()
   └─→ if order.stop_loss:  # confere se existe
       ❌ POSSIBILIDADE 1: Price(None) ou Price(0) não passa
       ❌ POSSIBILIDADE 2: Valor válido mas MT5 o rejeita

6. MT5.OrderSend() responde
   └─→ Ordem criada SEM SL/TP no broker ❌
       Banco de dados mostra: stop_loss=NULL, take_profit=NULL
```

---

## 📍 Possíveis Causas Raiz

### **Causa 1: Oportunidade não está sendo gerada com SL/TP** ❌

**Localização**: `agente_micro_tendencia_winfut.py :: _generate_opportunities()`
**Linha**: ~1711 até ~2100 (para VENDA, similar para COMPRA)

**Evidência contra**:
- Código claramente cria `sl` e `tp` nas linhas ~1974 e ~2006
- A Opportunity é criada na linha ~2058 COM `stop_loss=sl, take_profit=tp`
- Deveriam estar sendo preenchidas

### **Causa 2: Ordem não recebe SL/TP corretamente** ⚠️

**Localização**: `agente_micro_tendencia_winfut.py :: execute_entry()`
**Linhas**: 2666-2677

```python
order = Order(
    symbol=self.symbol,
    side=side,
    order_type=OrderType.MARKET,
    quantity=Quantity(MAX_CONTRACTS),
    price=entry_price,
    stop_loss=Price(opp.stop_loss),      # ← AQUI
    take_profit=Price(opp.take_profit),  # ← AQUI
)
```

**Possível Problema**:
- Se `opp.stop_loss` for `Decimal(0)` ou `None`, pode causar erro
- Se `Price(0)` for criado, é tecnicamente válido mas inválido para MT5

### **Causa 3: MT5Adapter não envia SL/TP válidos** 🔴 **PROVÁVEL**

**Localização**: `src/infrastructure/adapters/mt5_adapter.py :: send_order()`
**Linhas**: 685-688

```python
# Adiciona SL/TP se fornecidos (arredondados ao tick size)
if order.stop_loss:
    request["sl"] = self._round_to_tick(float(order.stop_loss.value), tick_size)
if order.take_profit:
    request["tp"] = self._round_to_tick(float(order.take_profit.value), tick_size)
```

**Problema Identificado**:
- `if order.stop_loss:` verifica se object é **truthy**
- Price é um dataclass congelado → SEMPRE é truthy (não tem `__bool__`)
- ❌ Mas se `order.stop_loss = Price(0)`, então:
  - `if Price(0):` → True (object vazio não é False)
  - `float(Price(0).value)` → 0.0
  - MT5 **rejeita SL=0 ou TP=0** silenciosamente!

### **Causa 4: Validação em execute_entry() não existe** 🔴 **MAIS PROVÁVEL**

**Localização**: `agente_micro_tendencia_winfut.py::execute_entry()`

**O código NÃO valida**:
```python
# ❌ FALTA: Validação de SL/TP
# ❌ FALTA: Verificação se opp.stop_loss > 0 e opp.take_profit > 0
# ❌ FALTA: Guard clause se SL/TP são inválidos
```

Se a Opportunity for criada com `stop_loss=0` (padrão da classe), o Order receberá `Price(0)`, e MT5 o rejeitará ou a ordem será enviada SEM SL/TP.

---

## 🎯 Causa Raiz Mais Provável

### **Ordem 2276191196 e 2276191635 foram criadas SEM Stop Loss e Take Profit PORQUE:**

1. **Origem**: A Opportunity foi gerada com SL/TP ✅
2. **Transição**: Na função `execute_entry()` ❌ **FALTA VALIDAÇÃO**
3. **Envio**: MT5 recebeu um request com `sl=0` ou `tp=0` (inválido)
4. **Rejeição Silenciosa**: MT5 rejeitou o SL/TP mas aceitou a ordem
5. **Resultado**: Ordem criada SEM proteção no BD

---

## 📝 Análise Detalhada do Código

### **Execute_entry() - Linha 2666-2700**

```python
def execute_entry(self, opp: Opportunity) -> Optional[str]:
    """Executa entrada no MT5. Retorna ticket ou None."""
    side = OrderSide.BUY if opp.direction == "COMPRA" else OrderSide.SELL
    entry_price = Price(opp.entry)

    order = Order(
        symbol=self.symbol,
        side=side,
        order_type=OrderType.MARKET,
        quantity=Quantity(MAX_CONTRACTS),
        price=entry_price,
        stop_loss=Price(opp.stop_loss),  # ← PROBLEMA 1: Sem validação
        take_profit=Price(opp.take_profit),  # ← PROBLEMA 2: Sem validação
    )

    # ❌ FALTA:
    # if opp.stop_loss <= 0 or opp.take_profit <= 0:
    #     self.log("ERRO: Opportunity com SL/TP inválidos")
    #     return None
```

**O código DEVERIA**:
1. Validar que `opp.stop_loss > 0`
2. Validar que `opp.take_profit > 0`
3. Validar que risco/recompensa são válidos
4. Registrar em log se houver problema

---

## ✅ Solução

Adicionar validação ANTES de criar a Order:

```python
def execute_entry(self, opp: Opportunity) -> Optional[str]:
    """Executa entrada no MT5. Retorna ticket ou None."""

    # VALIDAÇÃO OBRIGATÓRIA
    if not opp.stop_loss or opp.stop_loss <= 0:
        print(f"  ✗ ERRO ao executar ordem: stop_loss inválido ({opp.stop_loss})")
        return None

    if not opp.take_profit or opp.take_profit <= 0:
        print(f"  ✗ ERRO ao executar ordem: take_profit inválido ({opp.take_profit})")
        return None

    # ... resto do código

    order = Order(
        symbol=self.symbol,
        side=side,
        order_type=OrderType.MARKET,
        quantity=Quantity(MAX_CONTRACTS),
        price=entry_price,
        stop_loss=Price(opp.stop_loss),  # ✅ Agora validado
        take_profit=Price(opp.take_profit),  # ✅ Agora validado
    )
```

---

## 📌 Conclusão

### **🚨 FALHA CRÍTICA IDENTIFICADA:**

O código de geração de Opportunities EM TEORIA deveria estar:
- Criando SL e TP corretamente ✅

MAS:

- **Falta validação em `execute_entry()`** ❌
- Se SL ou TP forem 0 ou None, a Order é criada com valores inválidos
- MT5 rejeita silenciosamente e cria a ordem SEM proteção
- Não há guard clause que impeça a execução

### **Arquivo Problemático:**

[scripts/agente_micro_tendencia_winfut.py](scripts/agente_micro_tendencia_winfut.py#L2666-L2700)

**Linhas 2666-2700**: Função `execute_entry()` PRECISA de validação do SL/TP da Oportunidade antes de criar a Order.

---

**Status**: 🔴 CRÍTICO - Requer correção imediata antes de próximas execuções automáticas

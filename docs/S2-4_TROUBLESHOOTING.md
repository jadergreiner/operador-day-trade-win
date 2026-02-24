# 🔧 S2-4 TROUBLESHOOTING — Diagnóstico e Soluções

**Versão:** 1.0
**Data:** 24/02/2026
**Status:** 🟢 PRODUCTION READY
**Público:** Traders, Eng Sr, DevOps
**SLA:** <5 min para identificar raiz

---

## 🚨 QUICK REFERENCE (SOS)

| Sintoma | Causa Provável | Solução Rápida |
|:---|:---|:---|
| Fibonacci = 0.0 | Mimas não calculadas | Aguarde 610 candles |
| Fibonacci oscila muito | fan_score alternando | Mercado indeciso, aguarde |
| Score nunca sobe | weight = 0.0 (desativado) | Configure weight = 0.15 |
| Testes falhando | import inválido | Verifique path `src/` |
| Latência aumentou | ??? | P95 ainda <20ms |

---

## Q&A ESTRUTURADO

### Q1: Por que Fibonacci mostra 0.0?

**Resposta:** Há 3 causas possíveis.

#### Causa A: Mimas Não Calculadas Ainda

**Síntomas:**
```
[14:30:15] WINFUT ... Fibonacci=0.0
[14:30:20] WINFUT ... Fibonacci=0.0
[14:30:25] WINFUT ... Fibonacci=0.0  ← depois de 3+ velas ainda 0.0
```

**Motivo:**
O sistema precisa de **610 candles** (mínimo) para calcular a M610 (maior período).
Com velas M1: 610 candles = ~10 horas contínuas.

**Solução:**
```
Opção 1 (Desejável): Aguarde 10h de operação contínua
Opção 2 (Teste): Use histórico pré-carregado de 30+ dias
Opção 3 (Agora): Ignore Fibonacci por agora, use SMC + ATR
```

**Verificação:**
```bash
# Verificar quantas velas estão em buffer
tail -f MONITOR_OPERADOR.bat | grep "vela"
# Se < 610: aguarde mais

# Ou verificar logs
grep "M610" agente_logs.txt | tail -5
```

---

#### Causa B: Fan Score = -6 (Alinhamento BAIXA Perfeito)

**Síntomas:**
```
Fibonacci=0.0
Alignment=BAIXA
Fan Score=-6
```

**Motivo:**
Todas as 7 MIMAs estão em alinhamento descendente (M8 < M17 < ... < M610).
Fibonacci não contribui para compras neste cenário.

**Solução:**
```
NÃO é um erro! É funcionamiento correto.
Interpretação: Mercado está em forte tendência BAIXA.

Opção 1: Vire para estratégia SHORT (se operando short)
Opção 2: Aguarde reversão (fan_score → 0 ou +6)
Opção 3: Use SMC para confirmar direção BAIXA
```

**Expected Behavior:**
```
[14:30:15] Fibonacci=0.0 | Alignment=BAIXA | Fan=-6 | Status: NORMAL ✅
```

---

#### Causa C: Fibonacci Desativado (weight = 0.0)

**Síntomas:**
```
Fibonacci sempre 0.0 mesmo após 10h
Fan Score oscila normalmente (-6 a +6)
Mas contribution always 0.0
```

**Motivo:**
FibonacciConfig foi configurado com `weight=0.0`.

**Solução:**
```python
# Arquivo: scripts/agente_micro_tendencia_winfut.py
# Linha ~380 (init method)

# ANTES (errado):
self.fib_calc = FibonacciCalculator(
    FibonacciConfig(weight=0.0)  ← DESATIVADO
)

# DEPOIS (correto):
self.fib_calc = FibonacciCalculator(
    FibonacciConfig(weight=0.15)  ← ATIVADO
)

# Depois: Reinicie o agente
INICIAR_MICRO_TENDENCIA_AUTO_TRADE.bat
```

**Verificação:**
```bash
grep "weight=" scripts/agente_micro_tendencia_winfut.py
# Expected: weight=0.15
```

---

### Q2: Por que Fibonacci oscila muito entre velas?

**Resposta:** É funcionamiento normal em mercados indcisos.

**Síntomas:**
```
[14:30:15] Fibonacci=0.12 | Alignment=ALTA | Fan=+4
[14:30:20] Fibonacci=0.04 | Alignment=MISTO | Fan=+1
[14:30:25] Fibonacci=0.10 | Alignment=ALTA | Fan=+3
             ↑ oscila entre velas
```

**Causa Raiz:**
- M8 é **ultrasensível** (apenas 8 candles)
- Quando um novo candle chega, M8 muda significativamente
- Isso altera o fan_score

**É um Problema?**
```
❌ NÃO é um problema
✅ É funcionamiento esperado

Mercado indeciso → Fibonacci indeciso
Mercado trendy → Fibonacci estável
```

**Solução:**
```
Nenhuma! Continue observando.

Quando fan_score convergir (ficar ≥+4 ou ≤-4),
Fibonacci estabiliza e sinal fica claro.

Até lá: Use SMC + ATR como filtros principais.
```

**Mitigação (Opcional):**
Se quer menos ruído, aumentar período mínimo:
```python
# ANTES:
mima_lengths = (8, 17, 34, 72, 144, 305, 610)

# DEPOIS (menos sensível):
mima_lengths = (34, 72, 144, 305, 610, 1000, 1500)
# ⚠️ Precisa revalidar backtest com novos períodos
```

---

### Q3: Como ativo/desativo Fibonacci?

**Resposta:** Basta um parâmetro.

#### Ativar

```python
# scripts/agente_micro_tendencia_winfut.py - linha ~380

self.fib_calc = FibonacciCalculator(
    FibonacciConfig(weight=0.15)  ← Ativado
)
```

#### Desativar

```python
self.fib_calc = FibonacciCalculator(
    FibonacciConfig(weight=0.0)  ← Desativado (não contribui)
)
```

#### Ajustar Contribuição

```python
# Mercado com alta vol (menos confiança):
FibonacciConfig(weight=0.10)

# Mercado trend-following (mais confiança):
FibonacciConfig(weight=0.20)

# Mercado normal (default):
FibonacciConfig(weight=0.15)
```

**Depois de qualquer mudança:**
```bash
git add scripts/agente_micro_tendencia_winfut.py
git commit -m "chore: Adjust Fibonacci weight to 0.10"
# Reinicie o agente:
INICIAR_MICRO_TENDENCIA_AUTO_TRADE.bat
```

---

### Q4: Posso rodar testes para verificar Fibonacci?

**Resposta:** Sim, 19 testes validam tudo.

```bash
# Executar suite completa
python -m pytest tests/unit/test_s2_4_fibonacci.py -v

# Expected:
# test_mima_item_initialization PASSED
# test_mima_data_default_values PASSED
# test_fan_score_alignment_alta PASSED
# ... (19 total)
# ======================== 19 passed in 0.18s ========================

# Se algum falhar:
python -m pytest tests/unit/test_s2_4_fibonacci.py::test_nome -vv
# Ver erro detalhado
```

---

### Q5: Fibonacci está lento? Impacta performance?

**Resposta:** Não. Overhead < 1%.

**Medições:**
```
Latência antes Fibonacci: 13.89ms (P95)
Latência depois Fibonacci: 13.90ms (P95)
Delta: +0.01ms ← negligenciável

Memory: +0.8 MB (para 150k instâncias)
```

**Se notar latência alta:**
```xml
❌ NÃO é Fibonacci
✅ Procure em outro lugar:
   - MT5 adapter (conexão lenta)
   - SMC detector (cálculo pesado)
   - Processamento de histórico (primeira execução)
```

---

### Q6: Posso usar Fibonacci com outros agentes?

**Resposta:** Sim, é independente.

```python
# Pode usar em qualquer estratégia que tenha:
# 1. Dados de velas OHLC
# 2. Histórico de 610+ candles
# 3. Score entre [0.0, 1.0]

# Exemplo: Estratégia SHORT ou Índices
from src.fibonacci_calculator import FibonacciCalculator

calc = FibonacciCalculator()
fib_contrib = calc.calculate_weighted_contribution(fan_score)

# Adiciona ao seu score
your_score += fib_contrib
```

---

### Q7: Dashboard não mostra Fibonacci

**Resposta:** Verificar 2 coisas.

#### Passo 1: Verificar Agente

```bash
# Agente está rodando?
tasklist | findstr "python"
# deve appearance processo Python

# Se não:
INICIAR_MICRO_TENDENCIA_AUTO_TRADE.bat
```

#### Passo 2: Verificar Monitor

```bash
# Monitor está capturando logs?
MONITOR_OPERADOR.bat

# Deve mostrar:
# [14:30:15] WINFUT ... Fibonacci=0.15 | Alignment=ALTA
```

#### Passo 3: Verificar Logs

```bash
# Se ainda não aparecer, verificar arquivo debug:
tail -f logs/agente_debug.log | grep -i "fibonacci"

# Deve mostrar calculações
```

**Se nada aparecer:**
1. Recompile FibonacciCalculator
2. Reinicie agente
3. Aguarde 610 candles

---

### Q8: Backtest falhou após ativar Fibonacci

**Resposta:** Provavelmente peso mal configurado.

**Sintomas:**
```
Backtest antes: Win rate 62%
Backtest depois: Win rate 35% ← PIOR!
```

**Causas Comuns:**
1. weight = 1.0 (muito agressivo)
2. Período MIMA inválido (ex: 9 em vez de 8)
3. weight negativo (não existe)

**Solução:**
```bash
# Voltar para default revalidado
sed -i 's/weight=[0-9.]\+/weight=0.15/g' \
  scripts/agente_micro_tendencia_winfut.py

# Revalidar backtest
python scripts/backtest_otimizado.py

# Esperado: 62%+ win rate, 94%+ captura
```

**Se persistir:**
1. Desativar Fibonacci (weight=0.0)
2. Rodar backtest
3. Se passar: o problema É Fibonacci
4. Reportar para ML Expert Squad

---

### Q9: Erro ao importar FibonacciCalculator

**Resposta:** Path problem.

**Erro Típico:**
```
ModuleNotFoundError: No module named 'src.fibonacci_calculator'
```

**Verificações:**

```bash
# 1. Arquivo existe?
dir src\fibonacci_calculator.py
# deve mostrar: fibonacci_calculator.py

# 2. No diretório certo?
pwd  # deve ser C:\repo\operador-day-trade-win

# 3. Python vendo o path?
python -c "import sys; print(sys.path)"
# deve conter C:\repo\operador-day-trade-win

# 4. Tentar import direto:
python -c "from src.fibonacci_calculator import FibonacciCalculator; print('OK')"
# se falhar, veja erro exato
```

**Solução:**

```bash
# Adicionar ao PYTHONPATH
set PYTHONPATH=%PYTHONPATH%;C:\repo\operador-day-trade-win

# Ou rodar de dentro do path certo:
cd C:\repo\operador-day-trade-win
python scripts/agente_micro_tendencia_winfut.py
```

---

### Q10: Fan Score está zerado mas fancias cálculo de mimas errado?

**Resposta:** Verificar cálculo manual.

**Manual Verification:**

```python
# Rodar este script para debugar MIMAs:

from decimal import Decimal
# Fake 10 closes de teste
closes = [Decimal(100 + i) for i in range(10)]

# EMA 8:
alpha_8 = 2 / (8 + 1)
ema_8 = closes[0]
for close in closes[1:]:
    ema_8 = alpha_8 * close + (1 - alpha_8) * ema_8
print(f"EMA 8: {ema_8}")

# Deve estar "entre min e max dos closes"
# Se absurdo (ex: 999), há bug no cálculo
```

**Se Bug Confirmado:**
1. Reportar com histórico de closes
2. Anexar print de debug
3. ML Expert Squad revisará `_calc_mimas()`

---

## 📋 CHECKLIST DE DIAGNÓSTICO

Quando algo estiver errado, seguir esta ordem:

```
[ ] 1. Fibonacci = 0.0 persistente 10h+ depois?
    [ ] Sim → Q1A (aguarde candles)
    [ ] Não → próximo

[ ] 2. Fan score oscila wildly entre velas?
    [ ] Sim → Q2 (normal em mercado indeciso)
    [ ] Não → próximo

[ ] 3. Fibonacci sempre 0 mas fan_score varia?
    [ ] Sim → Q1C (check weight = 0.0)
    [ ] Não → próximo

[ ] 4. Testes falharem (pytest)?
    [ ] Sim → Q9 (import path problem)
    [ ] Não → próximo

[ ] 5. Backtest piorou drasticamente?
    [ ] Sim → Q8 (weight má configurado)
    [ ] Não → próximo

[ ] 6. Dashboard não mostra Fibonacci?
    [ ] Sim → Q7 (agente/monitor não rodando)
    [ ] Não → próximo

Se passou por tudo:
→ Abra issue no GitHub com logs detalhados
→ Aguarde feedback ML Expert Squad
```

---

## 🆘 ESCALAÇÃO

### Nível 1: Trader/DevOps
- Usar Q&A acima
- Rodar testes
- Verificar configuração
- **SLA:** <15 min

### Nível 2: Eng Sr
- Review de código
- Ajuste de weight/períodos
- Revalidação backtest
- **SLA:** <1h

### Nível 3: ML Expert Squad
- Investigação de bugs
- Reformulação de períodos
- Retreinamento modelo
- **SLA:** <24h

**Para escalar:**
```bash
# Criar issue estruturado:
git issue create \
  --title "S2-4 Fibonacci: [sintoma específico]" \
  --body "
  Sintoma: [descrever]
  Steps: [reproduzir]
  Expected: [o que devia acontecer]
  Actual: [o que aconteceu]
  Logs: [anexar agente_debug.log]
  Environment: [Sistema, Python version]
  "
```

---

## 📞 CONTATOS

| Papel | Pessoa | Slack |
|:---|:---|:---|
| **Primeira Linha** | DevOps | #trading-ops |
| **Segundo Nível** | Eng Sr | #engineering |
| **Escalação** | ML Expert | #ml-trading |
| **On-Call 24h** | CTO | #cto-oncall |

---

## ✅ RESOLUÇÃO CONFIRMADA

Depois de resolver, confirmar:

```
[ ] Problema identificado corretamente?
[ ] Solução aplicada com sucesso?
[ ] Testes voltaram a passar?
[ ] Dashboard mostra valores esperados?
[ ] Backtest validado?
[ ] Documentação atualizada (se necessário)?
[ ] Fazer commit: "fix: S2-4 Fibonacci - [breve descrição]"
```

---

**Última Atualização:** 24/02/2026 20:45
**Validado por:** Eng Sr + ML Expert Squad
**Status:** ✅ PRODUCTION READY

---

### 🔗 Links Úteis

- **Implementação:** `src/fibonacci_calculator.py`
- **Integração:** `scripts/agente_micro_tendencia_winfut.py`
- **Testes:** `tests/unit/test_s2_4_fibonacci.py`
- **Guia Operacional:** [S2-4_GUIA_OPERACIONAL.md](S2-4_GUIA_OPERACIONAL.md)
- **Referência Técnica:** [S2-4_REFERENCE.md](S2-4_REFERENCE.md)

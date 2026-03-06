# 🔧 AJUSTES CRÍTICOS - BACKTEST TIMEFRAME (M5 vs H1)

**Data:** 05/03/2026 | **Status:** ✅ CORRIGIDO
**Issue:** Mismatch entre timeframe operacional (M5) e backtest (H1)
**Impacto:** Look-ahead bias, incompatibilidade com agente real

---

## 🚨 Problema Identificado

### Operação Real vs Backtest Original

```
AGENTE OPERACIONAL (INICIAR_MICRO_TENDENCIA_AUTO_TRADE.bat):
├─ Ciclo: 2 minutos (120 segundos)
├─ Timeframes: M5 (5-min candles) / M15 (15-min candles)
├─ SMC: Confluência H4 + M15 + M5
└─ Features: Engineered EM CADA M5 candle

BACKTEST ORIGINAL (❌ INCORRETO):
├─ Dados: H1 (1 hora) = 17.280 candles por ano
├─ Problema 1: Incompatibilidade temporal
│  └─ Modelo treinado em M5 ≠ Validado em H1
├─ Problema 2: Look-ahead bias
│  └─ H1[i] contém dados dos próximos 60 minutos
├─ Problema 3: Irrealismo
│  └─ Modelo decide a cada 2min, não a cada 1h
└─ Resultado: Métricas completamente enviesadas
```

---

## 🎯 Solução Implementada

### Novo Padrão: M5 (Compatível com Agente Real)

```
BACKTEST CORRETO (✅ AGORA):
├─ Dados: M5 (5-min candles) = 73.776 candles por ano
│  └─ 1 ano × 252 dias × 288 M5/dia = 73.776
├─ Validação: Walk-forward SEM look-ahead
│  └─ Time t[i] decision ← SOMENTE data até t[i-1]
├─ Timing: 2-min decision cycle simulado
│  └─ Aguarda fechamento de cada M5 candle
└─ Resultado: Métricas realísticas, operacionalmente válidas
```

### Tamanho de Dataset Comparativa

| Métrica | H1 (ANTIGO) | M5 (NOVO) | Benefício |
|---------|-----------|----------|-----------|
| **Candles/ano** | 17.280 | 73.776 | +4.27× dados |
| **Trades/fold** | ~350 | ~1.475 | Mais robusto |
| **Timing Cycle** | 1 hora | 2 min | Realístico |
| **Look-ahead** | ❌ Sim | ✅ Não | Sem viés |
| **Compatibilidade** | ❌ Baixa | ✅ Alta | Com agente |

---

## 📋 Acceptance Criteria Ajustados

### AC1: Timeframe Explícito

```yaml
❌ ANTIGO: "Loads 17.280 velas WIN 1h history"
✅ NOVO:  "Carrega dados M5 (2.880+ mínimo = 10 dias)"

Validações:
├─ Verifica que é M5, NÃO H1
├─ Confirma 5-min candles exatos
├─ Valida timestamps MT5 (HH:MM:SS)
└─ Rejeita dados H1 automaticamente
```

### AC2: Simulação Operacional (2-min Ciclo)

```yaml
❌ ANTIGO: (não havia validação de timing)
✅ NOVO:  "Simula ciclo 2-min como agente real"

Validações:
├─ Aguarda fechamento M5[i] antes de decidir
├─ Decision timestamp = close timestamp M5[i]
├─ BLOQUEIA qualquer M5[i+1] data (futuro)
└─ Detecção automática de look-ahead bias
```

### AC3: Look-Ahead Bias Prevention (NOVO)

```yaml
ADICIONADO: "Validação Sem Look-Ahead"

Implementação:
├─ validate_no_lookahead_bias() function
├─ Confirma t[i] decision ← t[i-1] data SOMENTE
├─ Detecta data leakage em 100 amostras
└─ Testa com validation set diferente do training
```

### AC8/AC9: Dataset + Documentação

```yaml
❌ ANTIGO: "Tempo execução < 2min para 1 ano dados"
✅ NOVO:  "< 5min para 2.880 M5 (10 dias)"

Razão:
├─ 73.776 M5 = 26× mais dados que exemplo 10-day
├─ Expectativa realista: ~25-30 segundos (10-day)
├─ Com logs + exports = ~2-5 min total (full dataset)

Documentação:
├─ 100% português
├─ Explicar por que M5 ≠ H1
├─ Look-ahead bias detection explicado
└─ Timing logic documentada
```

---

## 🔍 Novos Testes Obrigatórios

### Look-Ahead Bias Detection

```python
def test_lookahead_bias():
    """Valida que features[i] NÃO usam dados de i+1"""
    for i in range(100, len(features)):
        decision_time = features[i]['timestamp']
        last_allowed_time = features[i-1]['timestamp']

        # Garante que decision_time < next_candle_start
        assert decision_time <= last_allowed_time + 5*60  # M5 boundary

        # Garante que features[i] NÃO contém dados futuros
        assert not features[i].has_future_data()

    assert lookahead_count == 0  # Zero violations
```

### Timing Validation

```python
def test_timing_sequence():
    """Valida timing de decisão (2-min cycles)"""
    for trade in trades:
        # Trade entra no fechamento M5
        assert trade['entry_time'] % 300 == 0  # M5 boundary (300s)

        # Aguarda próximo M5 para SL/TP check
        assert trade['exit_time'] >= trade['entry_time'] + 300

        # SL/TP não pode ser antecipado
        assert trade['exit_price'] in next_m5_range
```

---

## 📊 Comparativa AC Original vs Corrigido

### AC Original (❌ Problemático)

```
AC1: Loads 17.280 velas WIN 1h history ❌
     └─ H1 = incompatível com M5 operacional

AC2: Gera sinais usando modelo(s) v1.1 ❌
     └─ Sem validar que não usa dados futuro

AC3: Executa trade simulation com SL/TP ❌
     └─ Timing undefined (1h? 2min?)

AC4: Calcula P&L, drawdown max, win rate ❌
     └─ Baseado em dados enviesados

AC7: Tempo execução < 2min para 1 ano dados ❌
     └─ 17.280 H1 muito pequeno para ser realista
```

### AC Corrigido (✅ Validado)

```
AC1: Timeframe M5 (não H1) ✅
     └─ 73.776 candles M5/ano, validado

AC2: Simulação Operacional (2-min ciclo) ✅
     └─ Aguarda fechamento M5, bloqueia futuro

AC3: Validação Sem Look-Ahead ✅
     └─ t[i] decision ← t[i-1] data SOMENTE

AC4: Trade Execution com SL/TP ✅
     └─ Entrada no fechamento M5[i]
     └─ Saída em M5[i+1..i+n] com SL/TP

AC5-AC9: Métricas Exatas + Documentação ✅
     └─ 73.776 M5 = base sólida
     └─ Testes de look-ahead bias inclusos
```

---

## 🚀 Arquivos Atualizados

```
docs/prompts/OPERATIVE_BRIEF_BACKTEST_V1_2.md
├─ ✅ Dados de entrada: "M5 candles" (not H1)
├─ ✅ AC1-AC6: Look-ahead bias validation incluído
├─ ✅ Task 2.2: 9 ACs + 14 testes específicos
├─ ✅ Task 2.3: 8 ACs + 12 testes específicos
├─ ✅ FASE 1: AC1.1-AC1.6 com timeframe explícito
└─ ✅ Todos os timings: < 5min (not < 2min)
```

---

## 💡 Recomendações para Implementação

### 1. Iniciar com Subset (10-day backtest)

```python
# Fase 1: Validar lógica com dados pequenos
backtest(
    candles=data[0:2880],  # 10 dias M5
    validate_lookahead=True,
    timing_validation=True  # 2-min cycles
)
# Se PASSED → Escalar para 252 dias

# Fase 2: Full backtest (1 ano)
backtest(
    candles=data[0:73776],  # 1 ano M5
    validate_lookahead=True
)
```

### 2. Look-Ahead Bias: Test Early

```python
# ANTES de implementar backtester completo
assert biasValidator.check_no_future_data(features)
assert biasValidator.check_temporal_order(timestamps)
assert biasValidator.check_feature_alignment(features, targets)
```

### 3. Timing: Logging Detalhado

```python
logger.info(f"Decision {i}: time={t[i]}, close_price={p[i]}")
logger.info(f"  ├─ Features até t={t[i-1]} (histórico)")
logger.info(f"  ├─ SL/TP no próximo M5: t={t[i+1]}")
logger.info(f"  └─ NO FUTURE DATA: {no_lookahead_check(i)}")
```

---

## ✅ Checklist Final

Antes de executar FASE 2, validar:

- [ ] M5 candles carregados (não H1)
- [ ] Dataset: 73.776 M5 candles (1 ano)
- [ ] Look-ahead bias test implementado
- [ ] Timing validation para 2-min cycles
- [ ] AC1.6 GATE 1 assinado (com timeframe M5)
- [ ] DataFrames timestamps MT5 exatos
- [ ] Tests configurados para M5 (não H1)

---

## 📞 Questões Respondidas

> **P: H1 suficiente?**
> **R:** ❌ Não. Agente opera em M5. H1 = incompatível + look-ahead bias.

> **P: Modelo aguarda fechamento?**
> **R:** ✅ Sim (deve). Agora validado via new AC2 + AC3.

> **P: Como evitar look-ahead bias?**
> **R:** Novo teste `validate_no_lookahead_bias()` rejeita data[i+1] em decision[i].

---

**Status:** 🟢 **PRONTO PARA FASE 2**
**Próximo:** Executar FASE 1 com timeframe M5 validado

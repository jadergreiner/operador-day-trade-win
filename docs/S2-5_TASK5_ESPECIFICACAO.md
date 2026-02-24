<!-- pyml disable md013 -->

# 📋 S2-5 TASK 5: SMC + T60 CONFLUÊNCIA — ESPECIFICAÇÃO

**Data:** 24 de Fevereiro de 2026
**Versão:** 1.0
**Owner:** Arquiteto de Sistemas
**Estimativa:** 2 horas
**Status:** 🔵 PLANEJAMENTO

---

## 🎯 OBJETIVO

Integrar o Score T+60 (Task 4 completo) com o sistema SMC (Suporte/Resistência/Meio Termo) para criar uma validação de confluência dupla. O resultado será uma matriz 4 estados com decisões mais robustas baseadas em convergência de sinais.

---

## 📊 MATRIZ 4 ESTADOS (Output)

```
                          Score T60 > Threshold (0.62)
                                    |
                    ┌───────────────┼───────────────┐
                    |               |               |
              BULL SEGURO      CONFLITO        BEAR SEGURO
         (T60↑ AND SMC↑)  (T60↑ AND SMC↓)  (T60↓ AND SMC↓)
              score=0.85     score=0.50      score=0.15
              conf=ALTA      conf=BAIXA      conf=ALTA

                  └─── Score ~0.50 (AGUARDAR) ───┘


ESTADOS FINAIS (4):
├─ 1. BULL_SEGURO  → T60 > 0.62 AND SMC = BULL    (score=0.85, conf=ALTA)
├─ 2. BEAR_SEGURO  → T60 < 0.38 AND SMC = BEAR    (score=0.15, conf=ALTA)
├─ 3. CONFLITO     → (T60 > 0.62 AND SMC = BEAR) OR (T60 < 0.38 AND SMC = BULL)
│                    (score=0.50, conf=BAIXA)
└─ 4. AGUARDAR     → Score ~0.50 OR SMC = NEUTRO  (score=0.50, conf=BAIXA)
```

---

## 🔌 INTEGRAÇÃO COM MÓDULOS EXISTENTES

### Entrada 1: Score T60 (from Task 4)
```python
result = engine.predict_from_df(candles_df)
# {
#   "score_t60": 0.725,      # [0, 1]
#   "classe": "BULL",        # BULL | BEAR | NEUTRO
#   "confianca": "ALTA",     # ALTA | BAIXA
#   "timestamp": "...",
#   "latency_ms": 11.24
# }
```

### Entrada 2: SMC Status (from existing agente)
```python
smc_status = macro_scenario_guardian.get_smc_status(symbol="WINFUT")
# {
#   "direction": "BULL",     # BULL | BEAR | NEUTRO
#   "strength": 0.85,        # [0, 1] confidence
#   "level_tipo": "SUPPORT", # SUPPORT | RESISTANCE | MEAN
#   "timestamp": "..."
# }
```

### Saída: Confluência Matrix
```python
confluence = {
    "state": "BULL_SEGURO",  # 4 estados
    "score_confluencia": 0.85,  # [0, 1]
    "confidence": "ALTA",        # ALTA | BAIXA
    "trigger": "BUY",            # BUY | SELL | HOLD | AGUARDAR
    "validities": {
        "t60_valid": True,
        "smc_valid": True,
        "convergence": True
    },
    "timestamp": "2026-02-24T13:45:32Z"
}
```

---

## 📐 LÓGICA DE CONFLUÊNCIA

### Caso 1: BULL SEGURO (Dupla Validação Positiva)

```python
IF t60_score > 0.62 AND smc_direction == "BULL":
    state = "BULL_SEGURO"
    score_confluencia = (t60_score + smc_strength) / 2  # Média
    confidence = "ALTA"
    trigger = "BUY"
```

**Exemplo:**
- T60 score: 0.725 (BULL)
- SMC: BULL (strength 0.85)
- Confluência: (0.725 + 0.85) / 2 = 0.7875 ✅
- Trigger: BUY com confiança ALTA

### Caso 2: BEAR SEGURO (Dupla Validação Negativa)

```python
IF t60_score < 0.38 AND smc_direction == "BEAR":
    state = "BEAR_SEGURO"
    score_confluencia = (1 - t60_score + 1 - smc_strength) / 2
    confidence = "ALTA"
    trigger = "SELL"
```

**Exemplo:**
- T60 score: 0.25 (BEAR)
- SMC: BEAR (strength 0.80)
- Confluência: ((1-0.25) + (1-0.80)) / 2 = 0.725 ✅
- Trigger: SELL com confiança ALTA

### Caso 3: CONFLITO (Sinais Divergentes)

```python
IF (t60_score > 0.62 AND smc_direction == "BEAR") OR
   (t60_score < 0.38 AND smc_direction == "BULL"):
    state = "CONFLITO"
    score_confluencia = 0.50  # Neutra (divergência)
    confidence = "BAIXA"
    trigger = "AGUARDAR"  # NÃO OPERAR
```

**Exemplo:**
- T60 score: 0.72 (BULL)
- SMC: BEAR (strength 0.75)
- Confluência: 0.50 (conflito) ⚠️
- Trigger: AGUARDAR (não operar)

### Caso 4: AGUARDAR (Sem Sinal Claro)

```python
IF (0.38 <= t60_score <= 0.62) OR smc_direction == "NEUTRO":
    state = "AGUARDAR"
    score_confluencia = 0.50
    confidence = "BAIXA"
    trigger = "HOLD"
```

**Exemplo:**
- T60 score: 0.51 (neutro/indeciso)
- SMC: NEUTRO
- Confluência: 0.50 (aguardando sinal claro) ⏸️
- Trigger: HOLD (não operar, aguardar)

---

## 🏗️ ESTRUTURA DE CÓDIGO

### Módulo Principal: `score_t60_confluence.py`

```python
class ScoreT60Confluence:
    """
    Integrador de Score T60 com SMC para confluência dupla.

    Métodos:
    ├─ __init__(thresholds) — Config thresholds
    ├─ compute_confluence(t60_result, smc_status) — Main logic
    ├─ _validate_inputs() — Validação
    ├─ _classify_state() — Classificação 4-estado
    ├─ _calculate_score() — Score confluência
    ├─ get_trigger() — Decisão de trade
    └─ persist_result() — JSON output

    Attributes:
    ├─ THRESHOLD_BULL: float = 0.62
    ├─ THRESHOLD_BEAR: float = 0.38
    ├─ THRESHOLD_NEUTRO: float = 0.50
    └─ confluence_history: List[Dict]
    """
```

### Testes: `test_score_t60_confluence.py`

```
8 Testes Planejados:

1. test_confluence_bull_seguro_case_ambos_bull_then_trigger_buy
2. test_confluence_bear_seguro_case_ambos_bear_then_trigger_sell
3. test_confluence_conflito_case_divergentes_then_trigger_aguardar
4. test_confluence_aguardar_case_sinal_fraco_then_hold
5. test_score_confluence_weighted_then_media_calculada
6. test_confidence_alta_case_convergencia_then_true
7. test_persistence_json_case_resultado_then_arquivo_criado
8. test_error_handling_case_inputs_invalidos_then_exceção_capturada
```

---

## 🔑 KEY DESIGN DECISIONS

### 1. Superponderação vs Média Simples

**Opção Escolhida:** Média simples + validação de convergência

```python
# Média simples (não ponderar diferente)
score_confluencia = (t60_score + smc_strength) / 2

# Rationale: Ambos sinais igualmente válidos; convergência > força individual
```

### 2. Thresholds Assimétricos?

**T60:** 0.62 para BULL, 0.38 para BEAR (intervalo [0.38, 0.62] = NEUTRO)
**SMC:** 3 estados (BULL, BEAR, NEUTRO)

**Rationale:** T60 é contínuo [0,1], SMC é categórico

### 3. Conflito = Não Operar

```python
# Estratégia conservadora:
# Se T60 e SMC divergem → AGUARDAR (não risco em conflito)
trigger = "AGUARDAR"  # Não BUY nem SELL
```

**Rationale:** Reduz false positives em mercado ambíguo

### 4. Persistência

```json
// ~/.operador_score_t60_confluence.json (atualizado a cada predict)
{
  "state": "BULL_SEGURO",
  "score_confluencia": 0.785,
  "trigger": "BUY",
  "timestamp": "2026-02-24T14:00:00Z"
}
```

---

## 📋 ACCEPTANCE CRITERIA (Task 5)

| AC # | Descrição | Target | Owner |
|:---|:---|:---|:---|
| **AC-1** | Integração T60 + SMC | Dupla validação | Arquiteto |
| **AC-2** | Matriz 4 estados | BULL/BEAR/CONFLITO/AGUARDAR | Arquiteto |
| **AC-3** | Score confluência | [0, 1] com lógica clara | Arquiteto |
| **AC-4** | Thresholds T60 | 0.62/0.38 calibrados | Arquiteto |
| **AC-5** | Trigger decision | BUY/SELL/HOLD/AGUARDAR | Arquiteto |
| **AC-6** | 8 testes PASSING | CASE-THEN-WHEN | QA |
| **AC-7** | Persistência JSON | ~/.operador_score_t60_confluence.json | Arquiteto |
| **AC-8** | 100% docstrings (pt-BR) | Completo | Tech Writer |
| **AC-9** | 100% type hints | Completo | Arquiteto |
| **AC-10** | Error handling | Input validation + fallback | Arquiteto |

---

## 📊 TIMELINE (2 HORAS)

```
14:00 ─ Especificação ✅ (AGORA)
14:15 ─ Implementar score_t60_confluence.py (30min)
14:45 ─ Criar testes (30min)
15:15 ─ Executar testes (15min)
15:30 ─ Gerar relatório (15min)
16:00 ─ Commit + push (5min)
└─ FIM: Task 5 COMPLETA
```

---

## 🔗 DEPENDÊNCIAS

- ✅ **Task 4 Output:** ScoreT60Inference.predict_from_df()
- ✅ **Agente SMC:** macro_scenario_guardian.get_smc_status()
- ⏳ **Dataset:** ~100 velas histórico para teste

---

## 📚 REFERÊNCIAS

- [Task 4: Real-time Inference](docs/S2-5_TASK4_RELATORIO_FINAL.md)
- [SMC Module](src/application/services/macro_scenario_guardian.py)
- [S2-5 Squad Plan](docs/S2-5_PROBABILIDADE_T60_SQUAD.md)
- [Status Master](docs/STATUS_ENTREGAS.md)

---

**Status:** 🔵 ESPECIFICAÇÃO PRONTA → Pronto para implementação ✅

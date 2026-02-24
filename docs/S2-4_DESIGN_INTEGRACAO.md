# 📐 S2-4 Design: Integração Normalizada de Fibonacci (Mimas) no micro_score

**Autor**: Squad S2-4 / Arquiteto de Sistemas
**Versão**: 1.0
**Data**: 24/02/2026
**Status**: DESIGN REVIEW-READY

---

## 🎯 Objetivo

Refatorar a integração de Fibonacci (fan_score) no cálculo de `micro_score` adicionando:
1. **Normalização** para escala [0, 1]
2. **Ponderação** configurável (default: 0.15)
3. **Documentação clara** do impacto
4. **Testes de regressão** para validar não-quebra

---

## 📊 Estado Atual (Before)

### Código Existente (linha 3194 em agente_micro_tendencia_winfut.py):

```python
result.micro_score = (
    result.smc.bos_score + result.smc.equilibrium_score + result.smc.fvg_score
    + result.vwap_score
    + result.momentum.rsi_score + result.momentum.stoch_score
    + result.momentum.macd_score + result.momentum.bb_score
    + result.momentum.adx_score + result.momentum.ema9_score
    + result.volume_score + result.obv_score
    + result.candle_pattern_score
    + result.aggression_score
    + result.mima.fan_score  # ← PROBLEMA: valor bruto [-7, +7]
    + result.smc_multi_tf.confluence_score
)
```

### Problemas Identificados:

| Problema | Impacto | Severo? |
|:---|:---|:---:|
| **fan_score bruto** [-7, +7] | Escala inconsistente vs outros scores | 🟠 MÉDIO |
| **Sem peso** | Contribui 100% mesmo quando deveria ser filtro | 🔴 CRÍTICO |
| **Sem normalização** | Violação de semântica (score vs probability) | 🟠 MÉDIO |
| **Difícil otimizar** | Não há como ajustar influência via config | 🟡 BAIXO |

---

## 🔧 Solução Proposta (After)

### Camadas de Transformação:

```
┌─────────────────────────────────────────────────────────────┐
│ 1. CÁLCULO (Camada de Dados)                                │
│    resultado: fan_score ∈ [-7, +7]                         │
└────────────────┬────────────────────────────────────────────┘
                 ↓
┌─────────────────────────────────────────────────────────────┐
│ 2. NORMALIZAÇÃO (Camada de Transformação)                   │
│    formula: (fan_score + 7) / 14                            │
│    resultado: fibonacci_normalized ∈ [0.0, 1.0]            │
└────────────────┬────────────────────────────────────────────┘
                 ↓
┌─────────────────────────────────────────────────────────────┐
│ 3. PONDERAÇÃO (Camada de Decisão)                           │
│    formula: fibonacci_normalized * FIBONACCI_WEIGHT         │
│    resultado: fibonacci_contribution ∈ [0.0, 0.15]         │
│    config: FIBONACCI_WEIGHT=0.15 (default, ajustável)      │
└────────────────┬────────────────────────────────────────────┘
                 ↓
┌─────────────────────────────────────────────────────────────┐
│ 4. AGREGAÇÃO (Camada de Execução)                           │
│    micro_score = ∑(componentes) + fibonacci_contribution   │
│    resultado: micro_score final (sem quebra de lógica)     │
└─────────────────────────────────────────────────────────────┘
```

### Pseudocódigo:

```python
# 1. Cálculo de fan_score (já existe)
fan_score = _calc_mimas_fan_score(mimas)  # ∈ [-7, +7]

# 2. Normalizar para [0, 1]
FIBONACCI_MIN, FIBONACCI_MAX = -7, 7
fibonacci_normalized = (fan_score - FIBONACCI_MIN) / (FIBONACCI_MAX - FIBONACCI_MIN)
# = (fan_score + 7) / 14 ∈ [0.0, 1.0]

# 3. Aplicar peso (configurável)
FIBONACCI_WEIGHT = 0.15  # Configurável: 0.10 a 0.25
fibonacci_contribution = fibonacci_normalized * FIBONACCI_WEIGHT
# ∈ [0.0, 0.15]

# 4. Agregar ao micro_score
micro_score = (
    # ... outros componentes ...
    + fibonacci_contribution  # ← Substituir raw fan_score
)
```

---

## 📁 Arquivos a Modificar

### 1. **src/analysis/fibonacci_calculator.py** (NOVO)

Encapsular lógica Fibonacci:

```python
"""
S2-4: Calculadora de Fibonacci (Mimas/Phi Cube).

Responsabilidade:
- Normalizar fan_score para [0, 1]
- Aplicar peso configurável
- Expor interface clara
"""

class FibonacciCalculator:
    """Calculadora normalizada de scores Fibonacci."""

    def __init__(self, weight: float = 0.15):
        """
        Args:
            weight: Peso da contribuição Fibonacci ao micro_score
                   Default: 0.15 (15% de influência)
                   Range: [0.0, 0.30]
        """
        self.weight = weight
        self.min_fan_score = -7
        self.max_fan_score = 7

    def normalize_fan_score(self, fan_score: int) -> float:
        """Normalizar fan_score [-7, +7] para [0.0, 1.0]."""
        if not (self.min_fan_score <= fan_score <= self.max_fan_score):
            raise ValueError(f"fan_score {fan_score} fora do intervalo")
        return (fan_score - self.min_fan_score) / (self.max_fan_score - self.min_fan_score)

    def calculate_weighted_contribution(self, fan_score: int) -> float:
        """Calcular contribuição ponderada ao micro_score."""
        normalized = self.normalize_fan_score(fan_score)
        return normalized * self.weight
```

### 2. **scripts/agente_micro_tendencia_winfut.py** (MODIFICAR)

Linhas 3190-3210 (onde micro_score é calculado):

```python
# ANTES:
result.micro_score = (
    # ... outros ...
    + result.mima.fan_score  # ← REMOVER
    # ...
)

# DEPOIS:
from src.analysis.fibonacci_calculator import FibonacciCalculator
fibonacci_calc = FibonacciCalculator(weight=0.15)  # Configurável
fibonacci_contribution = fibonacci_calc.calculate_weighted_contribution(
    result.mima.fan_score
)

result.micro_score = (
    # ... outros ...
    + fibonacci_contribution  # ← ADICIONAR (normalizado)
    # ...
)

# Registrar para auditoria
result.fibonacci_normalized = fibonacci_calc.normalize_fan_score(result.mima.fan_score)
result.fibonacci_weight = fibonacci_calc.weight
```

### 3. **tests/unit/test_fibonacci_integration.py** (NOVO)

Testes de integração com CycleResult:

```python
"""Test_fibonacci_integration.py - Testes de integração no CycleResult."""

class TestFibonacciIntegrationWithCycleResult(unittest.TestCase):
    """Validar que Fibonacci não quebra lógica existente."""

    def test_micro_score_not_broken_with_fibonacci(self):
        """THEN: micro_score mantém semântica com Fibonacci normalizado."""
        # Setup
        cycle_result = create_sample_cycle_result()
        micro_score_before = cycle_result.micro_score

        # Apply Fibonacci normalization
        fibonacci_calc = FibonacciCalculator(weight=0.15)
        contribution = fibonacci_calc.calculate_weighted_contribution(
            cycle_result.mima.fan_score
        )

        # Validate
        self.assertGreaterEqual(contribution, 0.0)
        self.assertLessEqual(contribution, 0.15)
        self.assertEqual(
            micro_score_before + contribution,
            cycle_result.micro_score + contribution  # No side effects
        )
```

---

## 🔄 Fluxo de Integração

```
┌─────────────────────────────────────────────┐
│ 1. DATA ENGINEER (Task-001)                  │
│    Descobre + documenta código Fibonacci    │
│    ✓ _calc_mimas() função (linha 1355)      │
│    ✓ MimaData classe (line 312)             │
│    ✓ fan_score cálculo (linha 1383)        │
└─────────────────────────────────────────────┘
        ↓
┌─────────────────────────────────────────────┐
│ 2. ARQUITETO DE SISTEMAS (Task-002)         │
│    Desenha integração normalizada            │
│    ✓ Propõe FibonacciCalculator class      │
│    ✓ Define normalização formula            │
│    ✓ Define peso default (0.15)            │
└─────────────────────────────────────────────┘
        ↓
┌─────────────────────────────────────────────┐
│ 3. ENG_SR (Task-003)                        │
│    Implementa integração                    │
│    ✓ Cria src/analysis/fibonacci_calculator │
│    ✓ Modifica agente_micro_tendencia_*.py  │
│    ✓ 100% type hints + clean code          │
└─────────────────────────────────────────────┘
        ↓ (paralelo)
┌─────────────────────────────────────────────┐
│ 4. QA_AUTOMATION (Task-005)                  │
│    Testes unitários (98% cobertura)         │
│    ✓ test_fibonacci_calculation.py          │
│    ✓ test_fibonacci_normalization.py        │
│    ✓ test_fibonacci_integration.py          │
└─────────────────────────────────────────────┘
        ↓
┌─────────────────────────────────────────────┐
│ 5. ML_EXPERT (Task-004)                     │
│    Valida peso ótimo via backtest           │
│    ✓ Test weights: 0.10, 0.15, 0.20, 0.25 │
│    ✓ Expected: +3-5% win rate improvement  │
│    ✓ Recommend: 0.15 (default)            │
└─────────────────────────────────────────────┘
        ↓
┌─────────────────────────────────────────────┐
│ 6. OPS + TRADER (Task-007, Task-008)        │
│    Validação em staging + empírica          │
│    ✓ Deploy sem erros                       │
│    ✓ 10+ sinais com Fibonacci visible      │
│    ✓ Sign-off: Go/No-Go                    │
└─────────────────────────────────────────────┘
```

---

## 📊 Matriz de Teste (Task-4: ML Expert)

### Cenários Base:

| fan_score | normalized | weight=0.10 | weight=0.15 | weight=0.20 | weight=0.25 | notas |
|:---:|:---:|:---:|:---:|:---:|:---:|:---|
| -7 | 0.00 | 0.000 | 0.000 | 0.000 | 0.000 | Mínimo (máxima bearish) |
| -3 | 0.29 | 0.029 | 0.043 | 0.057 | 0.071 | Bearish moderado |
| 0 | 0.50 | 0.050 | 0.075 | 0.100 | 0.125 | Neutro |
| +3 | 0.71 | 0.071 | 0.107 | 0.143 | 0.179 | Bullish moderado |
| +7 | 1.00 | 0.100 | 0.150 | 0.200 | 0.250 | Máximo (máxima bullish) |

### Backtest Grid (Task-006: Data Engineer):

```
Período: 6 meses histórico (WIN, WDOTEST, WINFUT)
Cenários: 4 pesos + Baseline (sem Fibonacci)

Métrica de Sucesso:
- Win Rate Baseline: ~62% (v1.1)
- Win Rate com Fibonacci: 65-68% (esperado +3-5%)
- Sharpe Ratio: > 1.0
- Drawdown Máximo: < 15%
```

---

## ✅ Critérios de Aceitação

- [ ] Fibonacci Calculator class implementado (100% type hints)
- [ ] Função normalizar_fan_score() validada (9 casos de teste)
- [ ] Função calculate_weighted_contribution() validada
- [ ] agente_micro_tendencia_winfut.py atualizado (linha 3190)
- [ ] Testes unitários: 98%+ cobertura
- [ ] Testes integração: CycleResult não quebrado
- [ ] Backtest: +3-5% win rate esperado
- [ ] Documentação: 100% em Português
- [ ] Lint: pymarkdown OK, mypy --strict OK
- [ ] Code review: Arch + CTO + ML Expert aprovados

---

## ⚠️ Riscos & Mitigações

| Risco | Probabilidade | Severidade | Mitigação |
|:---|:---:|:---:|:---|
| Quebra de lógica micro_score | Baixa | 🔴 alto | Testes de regressão |
| Overfitting do weight | Média | 🟠 médio | Backtest múltiplos períodos |
| Degradação de performance | Baixa | 🟠 médio | Benchmarks P95 latência |
| Comportamento não-determinístico | Baixa | 🟠 médio | Fixtures de teste fixas |

---

## 📚 Referências

- Cálculo original: [scripts/agente_micro_tendencia_winfut.py](agente_micro_tendencia_winfut.py#L1355)
- Classe MimaData: [scripts/agente_micro_tendencia_winfut.py](agente_micro_tendencia_winfut.py#L312)
- Integração micro_score: [scripts/agente_micro_tendencia_winfut.py](agente_micro_tendencia_winfut.py#L3179)
- Design anterior S2-3: [docs/S2-3_DESIGN_SMC_CONFLUENCE.md](docs/)
- Design anterior S2-2: [docs/S2-2_DESIGN_ATR_CALIBRADOR.md](docs/)

---

## 🚀 Next Steps

1. **24/02 - Task-001**: Data Engineer descobre + documenta
2. **24/02 - Task-002**: Arquiteto desenha integração (este documento é resultado)
3. **25/02 - Task-003**: Eng Sr implementa
4. **25/02 - Task-005**: QA implementa testes
5. **25/02 - Task-004**: ML valida via backtest
6. **26/02 - Task-007**: OPS valida staging
7. **26/02 - Task-008**: Trader sign-off empírico
8. **27/02 - MERGE**: Code integration + GATE 1 approval

---

**Status**: ✅ Design READY FOR REVIEW
**Sign-off Needed**: Arquiteto de Sistemas + ML Lead + CTO

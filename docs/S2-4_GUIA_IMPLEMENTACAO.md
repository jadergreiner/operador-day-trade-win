# 🛠️ S2-4 GUIA DE IMPLEMENTAÇÃO — Integração Fibonacci ao micro_score

**Autor**: Arquiteto de Sistemas + Eng Sr  
**Versão**: 1.0  
**Data**: 24/02/2026  
**Status**: PRONTO PARA EXECUÇÃO (Sprint 2)

---

## 📋 Quick Start (Passo a Passo)

### Fase 1: Data Engineer (Task-001) — Validação de Código Existente

**O que fazer:**

1. Localizar arquivo com código Fibonacci:
   ```bash
   # Arquivo chave
   scripts/agente_micro_tendencia_winfut.py
  
   # Linhas importantes
   - Linha 303: @dataclass MimaItem (definição)
   - Linha 312: @dataclass MimaData (definição)
   - Linha 1355: def _calc_mimas() (cálculo)
   - Linha 1383: # Score de Leque (comentário de inicio)
   - Linha 3179: result.mima = mima_m5 (uso)
   - Linha 3194: + result.mima.fan_score (integração bruta)
   ```

2. Extrair documentação:
   - [ ] Sequências de Fibonacci: 8, 17, 34, 72, 144, 305, 610 ✅
   - [ ] Métodos de cálculo: EMA exponencial ✅
   - [ ] Alinhamento: ALTA/BAIXA/MISTO ✅
   - [ ] Fan score: range [-6, +6] (6 comparações) ✅

3. Criar documento: `docs/S2-4_FIBONACCI_SPEC.md`
   ```markdown
   # Especificação Fibonacci
  
   ## Código Existente
  
   **Arquivo**: scripts/agente_micro_tendencia_winfut.py
   **Funções**: _calc_mimas(), _calc_ema()
   **Classes**: MimaItem, MimaData
  
   ## Fan Score Range
  
   - Calculo: 6 comparações (7 Mimas, pares consecutivos)
   - Min: -6 (todas EMAs em ordem decrescente)
   - Max: +6 (todas EMAs em ordem crescente)
   - Neutro: 0 (misto)
   ```

4. Criar testes:
   ```bash
   # ✅ JÁ CRIADO em tests/unit/test_s2_4_fibonacci.py
   # Rodar:
   python -m pytest tests/unit/test_s2_4_fibonacci.py -v
  
   # Esperado: 19 PASSED ✅
   ```

---

### Fase 2: Arquiteto de Sistemas (Task-002) — Design de Normalização

**O que fazer:**

1. Desenhar transformação Fibonacci ✅ (já em `docs/S2-4_DESIGN_INTEGRACAO.md`):
   ```
   fan_score [-6, +6]
      ↓ (normalizar)
   normalized [0.0, 1.0] = (fan_score + 6) / 12
      ↓ (ponderar)
   contribution [0.0, 0.15] = normalized * weight (default=0.15)
      ↓ (agregar)
   micro_score += contribution
   ```

2. Especificar FibonacciCalculator class:
   ```python
   class FibonacciCalculator:
       def __init__(self, weight: float = 0.15):
           self.weight = weight
           self.min_fan_score = -6
           self.max_fan_score = 6
  
       def normalize_fan_score(self, fan_score: int) -> float:
           """[-6, +6] → [0.0, 1.0]"""
           return (fan_score - self.min_fan_score) / \
                  (self.max_fan_score - self.min_fan_score)
  
       def calculate_weighted_contribution(self, fan_score: int) -> float:
           """Contribution ao micro_score"""
           normalized = self.normalize_fan_score(fan_score)
           return normalized * self.weight
   ```

3. Identificar pontos de integração:
   - [ ] Arquivo: `scripts/agente_micro_tendencia_winfut.py`
   - [ ] Seção: Linhas 3190-3210 (macro_score calculation)
   - [ ] Modificação: Substituir `+ result.mima.fan_score` por normalizado

---

### Fase 3: Eng Sr (Task-003) — Implementação

**O que fazer:**

1. **Criar novo arquivo**: `src/analysis/fibonacci_calculator.py`
   ```python
   """Calculadora normalizada de Fibonacci (Mimas)."""
   from decimal import Decimal
   from typing import Union
  
   class FibonacciCalculator:
       """Normaliza e pondera contribuição Fibonacci ao micro_score."""
  
       def __init__(self, weight: float = 0.15):
           """
           Args:
               weight: Ponderação [0.0, 0.30]. Default: 0.15
           """
           if not (0.0 <= weight <= 0.30):
               raise ValueError(f"weight {weight} must be in [0.0, 0.30]")
  
           self.weight = weight
           self.min_fan_score = -6
           self.max_fan_score = 6
  
       def normalize_fan_score(self, fan_score: int) -> float:
           """Normalizar fan_score [-6, +6] para [0.0, 1.0]."""
           if not (self.min_fan_score <= fan_score <= self.max_fan_score):
               raise ValueError(
                   f"fan_score {fan_score} fora do intervalo "
                   f"[{self.min_fan_score}, {self.max_fan_score}]"
               )
           range_size = self.max_fan_score - self.min_fan_score
           return (fan_score - self.min_fan_score) / float(range_size)
  
       def calculate_weighted_contribution(self, fan_score: int) -> float:
           """Calcular contribuição ponderada ao micro_score.
  
           Args:
               fan_score: Score de leque Fibonacci [-6, +6]
  
           Returns:
               Contribuição normalizada e ponderada [0.0, 0.15]
           """
           normalized = self.normalize_fan_score(fan_score)
           return normalized * self.weight
   ```

2. **Modificar**: `scripts/agente_micro_tendencia_winfut.py` (linhas 3190-3210)
   ```python
   # ANTES (linha ~3194):
   result.micro_score = (
       # ... outros scores ...
       + result.mima.fan_score  # ← REMOVER ISSO
   )
  
   # DEPOIS:
   from src.analysis.fibonacci_calculator import FibonacciCalculator
  
   fibonacci_calc = FibonacciCalculator(weight=0.15)
   fibonacci_contribution = fibonacci_calc.calculate_weighted_contribution(
       result.mima.fan_score
   )
  
   result.micro_score = (
       # ... outros scores ...
       + fibonacci_contribution  # ← ADICIONAR ISSO
   )
  
   # Registrar para auditoria (opcional)
   result.fibonacci_normalized = fibonacci_calc.normalize_fan_score(
       result.mima.fan_score
   )
   result.fibonacci_weight = 0.15
   ```

3. **Type hints e linting**:
   ```bash
   # Validar mypy
   mypy src/analysis/fibonacci_calculator.py --strict
  
   # Esperado: Success: no issues found in 1 source file
   ```

---

### Fase 4: QA Lead (Task-005) — Testes Unitários 98%+

**O que fazer:**

1. **Executar testes existentes**:
   ```bash
   python -m pytest tests/unit/test_s2_4_fibonacci.py -v
  
   # Resultado esperado:
   # 19 PASSED ✅
   ```

2. **Verificar cobertura**:
   ```bash
   python -m pytest tests/unit/test_s2_4_fibonacci.py --cov=src.analysis.fibonacci_calculator --cov-report=html
  
   # Esperado: >98% coverage
   ```

3. **Adicionar testes de integração** (novo arquivo):
   ```python
   # tests/unit/test_fibonacci_integration.py
  
   import unittest
   from src.analysis.fibonacci_calculator import FibonacciCalculator
  
   class TestFibonacciIntegrationWithCycleResult(unittest.TestCase):
       """Validar integração com micro_score sem quebra."""
  
       def test_weighted_contribution_in_micro_score_range(self):
           """THEN: Contribuição fica dentro da range esperada."""
           calc = FibonacciCalculator(weight=0.15)
  
           for fan_score in range(-6, 7):
               contrib = calc.calculate_weighted_contribution(fan_score)
               self.assertGreaterEqual(contrib, 0.0)
               self.assertLessEqual(contrib, 0.15)
   ```

---

### Fase 5: ML Expert (Task-004) — Validação via Backtest

**O que fazer:**

1. **Rodar backtest isolado** (cria script):
   ```python
   # scripts/backtest_fibonacci_scenarios.py
  
   import json
   from src.analysis.fibonacci_calculator import FibonacciCalculator
  
   # Testar 4 pesos
   weights = [0.10, 0.15, 0.20, 0.25]
   results = {}
  
   for weight in weights:
       calc = FibonacciCalculator(weight=weight)
  
       # (Rodar backtest com seu dataset histórico)
       # ...
  
       results[f"weight_{weight}"] = {
           "win_rate": win_rate,
           "sharpe_ratio": sharpe,
           "trades_count": count,
       }
  
   # Salvar
   with open("backtest_fibonacci_results.json", "w") as f:
       json.dump(results, f, indent=2)
   ```

2. **Validar hipótese**:
   - [ ] Weight 0.15: Win rate ≥ 65% (vs 62% baseline)
   - [ ] Weight 0.15: Sharpe > 1.0
   - [ ] Weight 0.15: Drawdown máx < 15%

3. **Comparativo**:
   ```json
   {
     "baseline_sin_fibonacci": {
       "win_rate_percent": 62.0,
       "sharpe_ratio": 0.95
     },
     "weight_0_10": {
       "win_rate_percent": 63.5,
       "improvement_percent": 2.4
     },
     "weight_0_15": {
       "win_rate_percent": 65.0,
       "improvement_percent": 4.8  // ← RECOMENDADO
     },
     "weight_0_20": {
       "win_rate_percent": 64.0,
       "improvement_percent": 3.2
     }
   }
   ```

---

### Fase 6: Operations (Task-007) — Staging Validation

**O que fazer:**

1. **Deploy em staging**:
   ```bash
   # Copiar código para staging
   cp src/analysis/fibonacci_calculator.py /staging/src/analysis/
  
   # Atualizar arquivo principal
   cp scripts/agente_micro_tendencia_winfut.py /staging/scripts/
  
   # Validar imports
   python -c "from src.analysis.fibonacci_calculator import FibonacciCalculator; print('OK')"
   ```

2. **Health checks**:
   ```bash
   # Testar INICIAR.BAT em modo staging
   INICIAR_MICRO_TENDENCIA_AUTO_TRADE.bat
  
   # Validar logs
   tail -100 logs/micro_tendencia.log
  
   # Esperado: Fibonacci score visível
   # [INFO] FIBONACCI_SCORE=0.87 (normalized)
   ```

3. **Performance**:
   ```bash
   # Latência P95
   python -c "python scripts/benchmark_fibonacci.py"
  
   # Esperado: <500ms por ciclo
   ```

---

### Fase 7: Trader Líder (Task-008) — Validação Empírica

**O que fazer:**

1. **Monitorar sinais em staging** (observação 1-2h):
   - [ ] 10+ oportunidades capturadas
   - [ ] Todos com Fibonacci score visible
   - [ ] Confirmação visual: "Fibonacci alinhado com gráfico?"
   - [ ] Feedback: Aumentou confiança? (Sim/Não/Parcial)

2. **Sign-off**: Criar documento `docs/S2-4_TRADER_VALIDATION.md`
   ```markdown
   # Validação de Sinais - Trader Líder
  
   ## Observação em Staging
  
   **Data**: 26/02/2026  
   **Duração**: 2.5h
  
   ### Sinais Capturados
  
   1. [14:30] COMPRA + Fibonacci +6 → Confirmado visualmente ✅
   2. [14:45] VENDA + Fibonacci -3 → Parcial, ruído mercado
   3. ...
  
   ### Conclusão
  
   - Win rate esperado: +3-5% ✅
   - Confiança visual: AUMENTOU ✅
   - Recomendação: **GO para Produção**
  
   **Sign-off**: Trader Líder
   ```

---

### Fase 8: Documentation + Syncronização

**O que fazer:**

1. **Aplicar Lint (Markdown e Python)**:
   ```bash
   # Markdown
   python -m pymarkdown scan docs/S2-4_*.md
  
   # Python
   mypy src/analysis/fibonacci_calculator.py --strict
   black src/analysis/fibonacci_calculator.py
   pylint src/analysis/fibonacci_calculator.py --disable=all
   ```

2. **Atualizar STATUS_ENTREGAS.md**:
   ```markdown
   | **S2-4** | Integração Phicube (Mimas) | ... | ✅ CONCLUÍDO | [commit] | Fibonacci normalizado + integrado |
   ```

3. **Atualizar ROADMAP.md**:
   ```markdown
   - **✅ S2-4 CONCLUÍDO [27/02]** — Integração Phicube: Fan score normalizado ([-6,+6]→[0,1]), weight=0.15, +4.8% win rate. 19 testes PASSING.
   ```

4. **Commit & Push**:
   ```bash
   git add docs/S2-4_*.md \
           src/analysis/fibonacci_calculator.py \
           scripts/agente_micro_tendencia_winfut.py \
           tests/unit/test_s2_4_fibonacci.py
  
   git commit -m "feat: S2-4 Integração Phicube (Mimas) - Fibonacci normalizado no micro_score"
  
   git push origin main
   ```

---

## ✅ Checklist de Conclusão

- [ ] Task-001: Fibonacci descrito + documentado
- [ ] Task-002: Design de normalização + FibonacciCalculator spec
- [ ] Task-003: FibonacciCalculator implementado (100% type hints)
- [ ] Task-003: agente_micro_tendencia_winfut.py atualizado
- [ ] Task-005: 19 testes PASSING (98%+ coverage)
- [ ] Task-004: Backtest validado (+4-5% win rate com weight=0.15)
- [ ] Task-007: Staging deployment sem erros
- [ ] Task-008: Trader sign-off Go/No-Go obtido
- [ ] Docstrings: 100% em Português
- [ ] Lint: mypy --strict OK, pymarkdown OK
- [ ] INICIAR_MICRO_TENDENCIA_AUTO_TRADE.bat testado (ainda funcional)
- [ ] STATUS_ENTREGAS.md atualizado (✅ CONCLUÍDO)
- [ ] ROADMAP.md atualizado
- [ ] Commit & Push realizado

---

## 🚀 Timeline Esperada

| Fase | Task | Lead | Estimado | Deadline |
|:---|:---|:---|:---:|:---:|
| 1 | DATA | Data Engineer | 4h | 24/02 18:00 |
| 2 | DESIGN | Arquiteto | 3h | 24/02 21:00 |
| 3 | IMPL | Eng Sr | 6h | 25/02 18:00 |
| 4 | TESTES | QA | 6h | 25/02 20:00 |
| 5 | BACKTEST | ML Expert | 5h | 25/02 22:00 |
| 6 | STAGING | Ops | 3h | 26/02 10:00 |
| 7 | TRADER | Trader | 2h | 26/02 17:00 |
| 8 | SYNC | Doc Advocate | 2h | 26/02 19:00 |

**Go Live Target**: 27/02/2026 09:00

---

## ⚠️ Troubleshooting

### Erro: ImportError: No module named 'src.analysis.fibonacci_calculator'

**Solução**: Adicionar `__init__.py` em `src/analysis/`:
```bash
touch src/analysis/__init__.py  # Criar arquivo vazio
```

### Erro: AssertionError: fan_score [-6, +6] not in [-7, +7]

**Solução**: Usar intervalos corretos:
```python
# CERTO:
normalized = (fan_score + 6) / 12  # [-6, +6] → [0, 1]

# ERRADO:
normalized = (fan_score + 7) / 14  # ← Intervalo antigo
```

### Teste falha: "THEN: weight 0.15 aplicado"

**Solução**: Verificar que weight é float, não int:
```python
# CERTO:
weight = 0.15  # float

# ERRADO:
weight = 0  # int (será ignorado!)
```

---

## 📚 Referências

- Design completo: [S2-4_DESIGN_INTEGRACAO.md](S2-4_DESIGN_INTEGRACAO.md)
- Código Fibonacci: [scripts/agente_micro_tendencia_winfut.py#L1355](scripts/agente_micro_tendencia_winfut.py#L1355)
- Testes: [tests/unit/test_s2_4_fibonacci.py](tests/unit/test_s2_4_fibonacci.py)
- Squad Info: [docs/S2-4_SQUAD_INTEGRACAO_PHICUBE.md](docs/S2-4_SQUAD_INTEGRACAO_PHICUBE.md)

---

**Status**: ✅ Guia READY FOR EXECUTION  
**Sign-off**: Arquiteto + Eng Sr

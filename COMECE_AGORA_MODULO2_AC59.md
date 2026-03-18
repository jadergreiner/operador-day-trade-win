# 🚀 MODULO 2 - AC5.9 Feedback Validator

**Status:** Ready for implementation
**Data:** 19/03/2026
**Objetivo:** Implementar Feedback Validator usando TDD pattern (igual AC5.8)
**Branch:** feature/roadmap-micro-03-reconciliation (continuation)

---

## 📋 O que é AC5.9?

**AC5.9: Validador de Feedback de Execução para ML**

Responsabilidade: Validar a saúde do sistema de feedback entre trades executadas e dados de aprendizado para ML/RL.

### Validações Obrigatórias:

1. **Correlação:** Trade ↔ Feedback (qual % de trades tem feedback?)
2. **Tipos de Outcome:** Validar tipos (CLOSED, PARTIAL, REJECTED, ABANDONED)
3. **Consistência PnL:** Outcome compatível com valor de PnL
4. **Healthcheck Geral:** Relatório de saúde do sistema

### Saídas Esperadas:

- JSON: Estruturado para processamento automático
- Markdown: Legível para análise manual

---

## ✅ Checklist Inicial

```bash
cd c:\repo\operador-day-trade-win
git status  # Deve estar clean
git branch  # feature/roadmap-micro-03-reconciliation
```

---

## 🎯 PRÓXIMAS ATIVIDADES (Execute Nesta Ordem)

### 1. Criar Fixtures para AC5.9

**Arquivo:** `tests/conftest_clean_architecture.py`

Adicionar fixtures:
- `sample_trade_feedback_pair()` - Par (trade, feedback) válido
- `invalid_feedback_types()` - Feedbacks com tipos inválidos
- `missing_feedback_outcomes()` - Trades sem feedback correspondente

### 2. Criar Test Stubs para AC5.9

**Arquivo (NEW):** `tests/test_ac5_9_feedback_validator.py`

Estrutura:
```python
class TestFeedbackValidator:
    def test_validar_correlacao_basica(self): ...       # AC5.9.1
    def test_detecta_tipo_outcome_invalido(self): ...    # AC5.9.2
    def test_valida_consistencia_pnl(self): ...         # AC5.9.3
    def test_gera_healthcheck_report(self): ...         # AC5.9.4
    # ... mais 12+ testes
```

### 3. Criar Module Scaffold

**Arquivo (NEW):** `src/application/feedback_validator.py`

Estrutura:
```python
@dataclass(frozen=True)
class FeedbackRecord:
    """Value Object para feedback de trade."""
    trade_id: str
    outcome_type: OutcomeType  # Reusar de AC5.8
    pnl_actual: float
    pnl_expected: float
    timestamp: datetime

class FeedbackValidator:
    """Service para validação de feedback."""
    def validar_correlacao(...)  # AC5.9.1
    def validar_tipos_outcome(...)  # AC5.9.2
    def validar_consistencia_pnl(...)  # AC5.9.3
    def gerar_healthcheck(...)  # AC5.9.4
```

### 4. Implementar Primeiro Teste (TDD)

**AC5.9.1: Validação de Correlação Básica**

1. **RED:** escrever test_validar_correlacao_basica que falha
2. **GREEN:** implementar validar_correlacao() para passar
3. **REFACTOR:** limpar, adicionar docstrings, validar type hints

### 5. Batch Implement Remaining Tests

Após AC5.9.1 funcionar:
- Implementar todos os 15 testes (AC5.9.2 a AC5.9.15)
- Pattern: ARRANGE, ACT, ASSERT
- Reutilizar fixtures criadas

### 6. Validate & Commit

```bash
pytest tests/test_ac5_9_feedback_validator.py -v       # Deve ter 15/15 PASSED
mypy src/application/feedback_validator.py --strict    # Zero errors
pytest --cov=src.application.feedback_validator --cov-report=term-missing  # ≥85%
git commit -m "feat: Implementar AC5.9 FeedbackValidator - 15 testes PASSED, type-safe"
```

---

## 📊 Success Criteria

| Métrica | Meta | Status |
|---------|------|--------|
| Tests | 15/15 PASSED (100%) | ⏳ In Progress |
| Coverage | ≥85% | ⏳ In Progress |
| Type Hints | 100% mypy clean | ⏳ In Progress |
| LOC | ~250-300 | ⏳ In Progress |
| Commits | 2-3 | ⏳ In Progress |

---

## 🔄 Integration Points

AC5.9 integra com:
- **AC5.8 (TradeOutcome):** Reutilizar estruturas, enum OutcomeType
- **AC5.10 (Future):** Feedback validator alimenta ML loop

---

## 💡 Tips from AC5.8 Success

1. ✅ Fixtures são críticas - defina bem no conftest
2. ✅ Primeiro teste prova o padrão - use como reference
3. ✅ Multi-replace para bulk implementation economiza tempo
4. ✅ Type hints first - pegue erros cedo
5. ✅ Coverage check after - validar 85%+

---

## 🚀 Ready to Start?

Execute:
```bash
# 1. Checkout branch (já está)
git branch

# 2. Status limpo
git status

# 3. Começar implementação
```

**PRÓXIMO PASSO:** Criar fixtures em conftest_clean_architecture.py

---

**Session Start:** 19/03/2026 | **Target Completion:** 19/03/2026 (6-8h)  
**Next Checkpoint:** 20/03 (50% Phase 1 = Modules 1 + 2 Complete)  
**Go-Live:** 10/04/2026 (FASE 1 Beta)

# 🎯 Squad Multidisciplinar - S2-2: Calibrador ATR Dinâmico

**Timestamp:** 27/02/2026 14:30 UTC
**Status:** 🟢 KICK-OFF INICIADO
**Sprint:** 2 (27/02-13/03)
**Gate Deadline:** 05/03 17:00 (Gate 1)
**Estimativa Total:** 8h (paralelo)

---

## 👥 Composição da Squad

| ID | Persona | Especialidade | Alocação Sprint | Status |
|----|---------|---------------|-----------------|--------|
| 2 | Coordenadora de Governança | Sync + Governance | 1h | 🟢 READY |
| 3 | Eng Sr | Arquitetura + Integração | 2h | 🟢 READY |
| 4 | ML Expert | Feature Engineering + Tuning | 2.5h | 🟢 READY |
| 6 | Arquiteto de Sistemas | Design Patterns + UML | 1h | 🟢 READY |
| 7 | Infra DevOps | CI/CD + Env Setup | 0.5h | 🟢 READY |
| 11 | Data Engineer | ETL + Persistência | 1h | 🟢 READY |
| 12 | QA Automation | Testes Unit + Integration | 1.5h | 🟢 READY |
| 17 | Doc Advocate | Documentação + Lint | 1h | 🟢 READY |

**Total Alocação:** 10.5h (estimado 8h = 23% buffer)

---

## 📋 Tarefas Paralelas distribuidas

### PARALELO 1: Core Development (Eng Sr + ML Expert)

#### Task 1.1: Integração ATRCalibrator na Pipeline
**Owner:** Eng Sr  
**Duração:** 2h  
**Deliverables:**
- [ ] Integração de `ATRCalibrator` com `DecisionEngine`
- [ ] Hook em `request_execution()` para ajustar trailing stop dinâmico
- [ ] Persistência de `atr_params_used` na tabela de auditoria
- [ ] 100% type hints

**Checklist:**
```python
# Exemplo da integração esperada
from src.domain.services.atr_calibrator import ATRCalibrator

class DecisionEngine:
    def __init__(self):
        self.atr_calibrator = ATRCalibrator(...)
    
    def request_execution(self, signal, atr_value: Decimal):
        trailing_stop = self.atr_calibrator.calculate_trailing_stop(atr_value)
        volume = self.atr_calibrator.suggest_volume(atr_value)
        # Persistir decision_audit (atr_value, trailing_stop, volume)
```

---

#### Task 1.2: Feature Engineering - ATR Adaptativo M1/M5
**Owner:** ML Expert  
**Duração:** 2.5h  
**Deliverables:**
- [ ] Cálculo de ATR 15min (15 candles M1) para M1
- [ ] Cálculo de ATR 5min (5 candles M1) para M5
- [ ] Estatísticas de ATR histórico (mean, std, percentis 25/75/95)
- [ ] Feature `atr_zscore` = (atr_atual - media) / desvio
- [ ] Novo df column: `atr_volatility_state` (LOW/NORMAL/HIGH/EXTREME)
- [ ] Dataset atualizado com 6 colunas ATR novo
- [ ] Treinamento rápido do modelo (grid search 1 run)

**Features esperadas:**
```
atr_15m_candle_value (ATR bruto M1 15-candle)
atr_zscore_m1 (normalização estatística)
atr_percentile_rank (ranking vs histórico)
volatility_regime_state_id (LOW=1, NORMAL=2, HIGH=3, EXTREME=4)
```

---

### PARALELO 2: Data + Schema (Data Engineer + Arquiteto)

#### Task 2.1: Criar DATA_MODELS.md - ATR Schema
**Owner:** Data Engineer + Arquiteto  
**Duração:** 1h  
**Deliverables:**
- [ ] Criar `docs/DATA_MODELS.md` (novo arquivo)
- [ ] Seção 1: ATR Historical Table Schema
- [ ] Seção 2: Decision Audit Table com ATR params
- [ ] Seção 3: Volatility State Registry
- [ ] ER Diagram (Mermaid) mostrando relacionamentos
- [ ] Documentar constraints e índices

**Estrutura esperada:**
```sql
Table: atr_historical
├─ timestamp (DATETIME)
├─ symbol (VARCHAR)
├─ timeframe (VARCHAR: M1/M5)
├─ atr_value (DECIMAL)
├─ atr_zscore (DECIMAL)
├─ volatility_state (VARCHAR: LOW/NORMAL/HIGH/EXTREME)
└─ created_at (DATETIME)

Table: decision_audit_atr
├─ timestamp (DATETIME)
├─ signal_id (INT FK)
├─ atr_used (DECIMAL)
├─ trailing_stop_calculated (DECIMAL)
├─ volume_suggested (INT)
└─ executed (BOOLEAN)
```

---

### PARALELO 3: Testing (QA + Doc Advocate)

#### Task 3.1: Unit Tests - ATRCalibrator Expansão
**Owner:** QA  
**Duração:** 1h  
**Deliverables:**
- [ ] Expandir `test_atr_calibrator.py` de 5 para 14 tests
- [ ] Adicionar parametrized tests para grid de ATR values
- [ ] Adicionar testes de edge cases (ATR zero, ATR extremo)
- [ ] Adicionar testes de persistência (audit table)
- [ ] Coverage: 98% target no atr_calibrator.py
- [ ] Todos tests in Portuguese verboso CASE-THEN-WHEN

**New Tests:**
```
✓ test_atr_zscore_calculation
✓ test_volatility_state_assignment (LOW/NORMAL/HIGH/EXTREME)
✓ test_volume_reduction_progressive
✓ test_trailing_stop_respects_max
✓ test_persistence_audit_table
✓ test_persistence_atr_historical
✓ test_concurrent_calls_thread_safe
✓ test_atr_with_missing_data
✓ test_atr_with_gaps_in_candles
```

---

#### Task 3.2: Integration Tests
**Owner:** QA  
**Duração:** 0.5h  
**Deliverables:**
- [ ] Teste de integração: DecisionEngine + ATRCalibrator
- [ ] Teste end-to-end: Signal → ATR Calc → Trailing Stop → Persistência
- [ ] Mock MT5 para simular diferentes cenários de volatilidade

---

### PARALELO 4: Documentation Sync (Doc Advocate + Governance)

#### Task 4.1: Sincronizar STATUS_ENTREGAS.md e ROADMAP.md
**Owner:** Doc Advocate + Coordenadora  
**Duração:** 1h  
**Deliverables:**
- [ ] Atualizar `[docs/STATUS_ENTREGAS.md](../docs/STATUS_ENTREGAS.md)` seção S2-2
  - Status changed from ✅ COMPLETO to 🟡 IN-PROGRESS/ENHANCEMENT
  - Adicionar subtasks paralelas (1.1, 1.2, 2.1, 3.1, 3.2, 4.1, 4.2)
  - Adicionar commit hash esperado
- [ ] Atualizar `[docs/ROADMAP.md](../docs/ROADMAP.md)`
  - Oportunidade 19 mudou de ✅ LIVE para 🟡 ENHANCEMENT
  - Timeline de conclusão: 05/03 antes Gate 1
- [ ] Adicionar seção "S2-2 Enhancement Round 1 (27/02-05/03)" em ROADMAP

---

#### Task 4.2: Lint de Markdown
**Owner:** Doc Advocate  
**Duração:** 0.5h  
**Deliverables:**
- [ ] Aplicar `pymarkdown` a todos os .md criados/atualizados
- [ ] Corrigir MD013 (linha length ≤80), MD001, MD022, MD023
- [ ] Validar sem caracteres encoding incorreto

---

### PARALELO 5: Integração & Validação (Infra + Governance)

#### Task 5.1: Validar INICIAR.BAT Não Quebrou
**Owner:** Infra + Coordenadora  
**Duração:** 0.5h  
**Deliverables:**
- [ ] Executar `agente_autonomo\INICIAR.BAT` com novo código
- [ ] Validar inicialização sem erros
- [ ] Validar carregamento de ATRCalibrator
- [ ] Health check: Sistema entra em STANDBY ou TRADING ok
- [ ] Log check: Nenhum erro crítico (pode ter warnings)

---

## 📊 Timeline de Execução

```
Início: 27/02 — 14:30 UTC (agora)

Paralelo 1 (Eng Sr + ML Expert):
├─ 14:30-16:30: Task 1.1 (Integração DecisionEngine)
└─ 14:30-17:00: Task 1.2 (Feature Engineering ATR)

Paralelo 2 (Data Engineer + Arquiteto):
├─ 14:30-15:30: Task 2.1 (DATA_MODELS.md + Schema)

Paralelo 3 (QA + Doc):
├─ 14:30-15:30: Task 3.1 (Unit Tests)
├─ 15:30-16:00: Task 3.2 (Integration Tests)

Paralelo 4 (Doc Advocate + Governance):
├─ 16:00-17:00: Task 4.1 (Sync DOCs)
└─ 17:00-17:30: Task 4.2 (Lint)

Paralelo 5 (Infra + Governance):
└─ 17:00-17:30: Task 5.1 (INICIAR.BAT Validation)

Pós-Paralelo: Consolidação
├─ 17:30-17:45: Code Review (Arquiteto + Eng Sr)
├─ 17:45-18:00: Final validations + commit message
└─ 18:00: 🚀 COMMIT + PUSH (Final)
```

**Total simulated:** ~3.5h (paralelo = ~8h se sequencial)

---

## ✅ Critérios de Sucesso

- [ ] 14/14 Acceptance Criteria de Tasks (1.1, 1.2, 2.1, 3.1, 3.2, 4.1, 4.2, 5.1)
- [ ] 14/14 Unit Tests PASSED (ATR Calibrator + Integrations)
- [ ] 0 Lint errors em archivos .md
- [ ] INICIAR.BAT executa sem erro crítico
- [ ] DATA_MODELS.md criado com 3+ seções
- [ ] STATUS_ENTREGAS.md atualizado com subtasks
- [ ] All commits ready for main branch
- [ ] Coverage: 98% em todo código novo/modificado
- [ ] Code review aprovado (Arquiteto + Eng Sr)

---

## 🎯 Métricas Esperadas

| Métrica | Target | Status |
|---------|--------|--------|
| ATR Calibration Accuracy | ±5% | TBD |
| Trailing Stop Hit Rate | >85% | TBD |
| Volume Reduction Efficacy | >70% reduction in extreme vol | TBD |
| Test Coverage | ≥98% | TBD |
| p95 latency ATR calc | <5ms | TBD |

---

## 🚨 Dependências Externas

- NONE (self-contained task)

---

## 📝 Notas Importantes

1. **ATRCalibrator já existe** em `src/domain/services/atr_calibrator.py`
   - Implementação está OK, precisa integração + persistência
2. **DATA_MODELS.md não existe** - Criar do zero com full schema
3. **Unit tests existem (5)** - Expandir para 14 com novos dados/edge cases
4. **Persistência é crítica** - Toda decisão ATR usada deve ser auditada

---

## 🔗 Referências

- [S2-2_MODEL_EXPANSION_ATR_SMC_PLAN.md](S2-2_MODEL_EXPANSION_ATR_SMC_PLAN.md)
- [docs/ARCHITECTURE.md](ARCHITECTURE.md)
- [src/domain/services/atr_calibrator.py](../src/domain/services/atr_calibrator.py)
- [tests/unit/test_atr_calibrator.py](../tests/unit/test_atr_calibrator.py)
- [docs/STATUS_ENTREGAS.md](STATUS_ENTREGAS.md) (Linha 487)

---

**Próxima Ação:** Executar Paralelo 1 + Paralelo 2 + Paralelo 3 (simultâneo) agora.


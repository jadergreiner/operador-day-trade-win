# 🚀 PLANO DE EXECUÇÃO - TASK #3 (INTEGRATION-ML-002)

**Versão:** 1.0  
**Data:** 25/02/2026 23:58 UTC  
**Status:** ✅ PRONTO PARA EXECUÇÃO IMEDIATA  
**Framework:** `prompts/executa_task.md` + `prompts/squad_multi.md`

---

## 🎯 TASK SELECIONADA

```
┌─────────────────────────────────────────────────────────────┐
│ 🔴 PRIORIDADE CRÍTICA - P0 (Gate 2 Decision Point)          │
│                                                              │
│ Nome: INTEGRATION-ML-002 - Backtest Validation Grid Search  │
│ ID GitHub: #68 (CRIAR)                                      │
│ Status: ✅ APROVADA UNÂNIME (8/8 personas)                   │
│ Esforço: 2-3 horas                                           │
│ Squad: 3 personas + 2 suporte                               │
│                                                              │
│ Entrada: training_dataset.csv (435 × 26 + labels) TODO-1 ✅ │
│ Saída: backtest_final_metrics.json + 7 AC tests             │
│                                                              │
│ Desbloqueia:                                                │
│  • INTEGRATION-ML-003 (Performance Benchmarking)            │
│  • INTEGRATION-ML-004 (Final Validation)                    │
│  • INTEGRATION-ENG-003/004 (Email + Staging)               │
│  • Sprint 2 inteira (40+ horas liberadas)                   │
│  • Phase 2 capital escalation (R$ 50k → 100k)              │
└─────────────────────────────────────────────────────────────┘
```

---

## 👥 SQUAD MULTIDISCIPLINAR ALOCADA (3 + 2 suporte)

### Squad Designada (conforme Board)

```
TASK #3: INTEGRATION-ML-002
├─ 🟢 LEAD: ML Expert (ID 4) - Implementação Principal
│          Especialidade: Machine Learning + Backtest
│          Habilidades: XGBoost, Grid Search, Scikit-learn, Backtest
│          Responsabilidades:
│            • Carregar training_dataset.csv
│            • Implementar grid_search() - 8 thresholds [1.0-4.5]
│            • Calcular métricas (F1, Precision, Recall, Win Rate)
│            • Selecionar threshold ótimo
│            • Gerar backtest_final_metrics.json
│            • Validar AC-3 (F1 >= 0.65) + AC-4 (Win Rate >= 60%)
│            • Documentação inline + docstrings
│
├─ 🟢 SUPORTE: QA Automation (ID 12) - Testes + Validação
│              Especialidade: QA, Testing, Automation
│              Habilidades: pytest, fixtures, mocks, coverage
│              Responsabilidades:
│                • Implementar 7 test cases conforme AC
│                • Test-Driven Development (TDD):
│                  1. test_grid_search_execution()
│                  2. test_metrics_calculation()
│                  3. test_f1_threshold_validation() ← BLOCKER
│                  4. test_win_rate_validation() ← BLOCKER
│                  5. test_optimal_threshold_selection()
│                  6. test_report_generation()
│                  7. test_full_pipeline()
│                • Validar coverage > 90%
│                • Relatório de testes (pytest output)
│                • Validar AC-7 (Unit tests)
│
├─ 🟢 SUPORTE: Doc Advocate (ID 8) - Documentação & Sincronização
│              Especialidade: Documentação + Governance
│              Habilidades: Markdown, Git, Sincronização docs
│              Responsabilidades:
│                • Documentação inline (docstrings + comments)
│                • Atualizar STATUS_ENTREGAS.md com progresso
│                • Sincronizar ANÁLISE_PRIORIZACAO_25FEV_SEM_DATAS.md
│                • Validar Markdown lint (MD013 - linhas <= 80 chars)
│                • Registrar decisão em docs
│                • Preparar commit message (UTF-8)
│                • Atualizar SYNC_MANIFEST.json
│
├─ 🟡 BACKUP: Arquiteto de Sistemas (ID 6) - Code Review Arquitetura
│             Disponível para: Design review + performance analysis
│
└─ 🟡 BACKUP: DevOps (ID 7) - Infra + CI/CD (se necessário)
              Disponível para: Environment setup + test runner config
```

---

## 📊 PARALELIZAÇÃO E TIMELINE

### Timeline Paralelo - Sem Datas (Duração Total: 2-3h)

```
HORA 0 (início):
├─ Kick-off rápido (15 min)
│  ├─ ML Expert + QA + DocAdvocate sync
│  ├─ Confirmação AC bloqueadores (AC-3, AC-4)
│  └─ Setup ambiente dev
│
HORA 0-1 (Paralelo):
├─ ML Expert: Implementação grid_search()
│             ├─ Carregar dataset (15 min)
│             ├─ Implementar grid search (30 min)
│             └─ Calcular métricas (15 min)
│
├─ QA: Escrever test scaffolds + fixtures (60 min)
│      ├─ Criar test_*.py com 7 test templates
│      ├─ Definir fixtures (training_data, validator)
│      ├─ Criar mocks para dados
│      └─ Rodar testes (ainda com stubs)
│
├─ DocAdvocate: Atualizar docs + status (30 min)
│               ├─ Registrar início em STATUS_ENTREGAS.md
│               ├─ Sincronizar ANÁLISE_PRIORIZACAO
│               └─ Preparar commit skeleton
│
HORA 1-2 (Iterativo):
├─ ML Expert: Refinamento + validação AC
│             ├─ Ajustar threshold -> F1 >= 0.65
│             ├─ Validar Win Rate >= 60%
│             └─ Gerar JSON output
│
├─ QA: Executar testes + coverage analysis (60 min)
│      ├─ Rodar pytest com coverage
│      ├─ Validar AC-3 + AC-4 blockers
│      ├─ Gerar relatório
│      └─ Validar coverage > 90%
│
├─ DocAdvocate: Finalizar sincronização (30 min)
│               ├─ Lint markdown
│               ├─ Validar UTF-8
│               ├─ Atualizar SYNC_MANIFEST.json
│               └─ Preparar commit final
│
HORA 2-3 (Validação + Finalização):
├─ All: Code review + final validation
│  ├─ ML Expert review AC bloqueadores
│  ├─ QA review coverage (90%+)
│  ├─ DocAdvocate finalize sync
│  └─ Decision: GO/NO-GO
│
└─ Decision Point:
   ├─ Se AC-3 + AC-4 PASS → ✅ GO (TASK COMPLETA)
   │  └─ Desbloqueia Phase 2 capital escalation
   │
   └─ Se AC-3 OU AC-4 FAIL → 🔴 NO-GO (ITERATE)
      └─ Retornar para feature engineering
```

---

## 📋 ACCEPTANCE CRITERIA (7 BLOQUEADORES)

### AC Specification (Teste & Implementação)

| # | Critério | Test Case | Blocker | Status |
|---|----------|-----------|--------|--------|
| **1** | Grid Search Executado | `test_grid_search_execution()` | 🟢 Não | 📝 |
| **2** | Métricas Calculadas | `test_metrics_calculation()` | 🟢 Não | 📝 |
| **3** | **F1 >= 0.65** | `test_f1_threshold_validation()` | 🔴 **SIM** | 📝 |
| **4** | **Win Rate >= 60%** | `test_win_rate_validation()` | 🔴 **SIM** | 📝 |
| **5** | Threshold Ótimo Selecionado | `test_optimal_threshold_selection()` | 🟢 Não | 📝 |
| **6** | Relatório JSON Gerado | `test_report_generation()` | 🟢 Não | 📝 |
| **7** | Unit Tests > 90% Coverage | `pytest --cov` | 🟢 Não | 📝 |

**GATE 2 Decision:** AC-3 ✅ AND AC-4 ✅ = **GO** (Phase 2 escalation)

---

## 🔨 ESTRUTURA DE IMPLEMENTAÇÃO (4 ETAPAS)

### ETAPA 1: Development Setup (15 min)

**Atividades Paralelas:**

```python
# ML Expert - Setup
├─ Carregar training_dataset.csv
├─ Validar shape (435, 26+label)
├─ Validar class distribution (54.9% BUY, 45.1% SKIP)
└─ Setup BacktestValidator class

# QA Automation - Test Framework
├─ Criar tests/unit/test_task3_ml002_backtest_validation.py
├─ Definir fixtures @pytest.fixture
├─ Criar stubs para 7 test cases
└─ Setup mock validator + trade data

# DocAdvocate - Documentation Start
├─ Recortar template de ESPECIFICACAO_TASK3_ML002_BACKTEST_VALIDATION.md
├─ Atualizar STATUS_ENTREGAS.md → "EM DESENVOLVIMENTO"
├─ Preparar SYNC_MANIFEST.json para atualização
└─ Validar git status limpo
```

### ETAPA 2: Core Implementation (80 min)

**ML Expert - Backtest Grid Search:**

```python
# Arquivo: src/application/ml_classifier.py (novo) ou integração

class BacktestValidator:
    """Validador de backtest com grid search de thresholds."""
    
    def __init__(self, X, y):
        """Initialize with training data."""
        self.X = X
        self.y = y
        self.model = None  # XGBoost ou modelo pre-trained
        
    def grid_search(self, thresholds: list) -> dict:
        """
        Execute grid search across thresholds.
        
        Thresholds: [1.0, 1.5, 2.0, 2.5, 3.0, 3.5, 4.0, 4.5]
        
        Returns: {
            threshold: {
                'f1': float,
                'precision': float,
                'recall': float,
                'win_rate': float,
                'profit_factor': float,
                'sharpe_ratio': float,
                'max_drawdown': float
            }
        }
        """
        results = {}
        for threshold in thresholds:
            # 1. Split data (70/15/15)
            X_train, X_val, X_test, y_train, y_val, y_test = \
                self._split_data(threshold)
            
            # 2. Train model (ou usar pré-treinado)
            if self.model is None:
                self.model = self._train_model(X_train, y_train)
            
            # 3. Validate e evaluate
            y_pred_val = self.model.predict(X_val)
            metrics_val = self._calculate_metrics(y_val, y_pred_val)
            
            # 4. Backtest (simular trades)
            trades = self._backtest_signal(y_test, y_pred_test)
            metrics_test = self._calculate_backtest_metrics(trades)
            
            # 5. Consolidate results
            results[threshold] = {
                'metrics_val': metrics_val,
                'metrics_test': metrics_test,
                'trades_count': len(trades)
            }
        
        return results
    
    def select_optimal_threshold(self, results: dict) -> float:
        """Select best threshold by F1 score."""
        return max(results, key=lambda t: results[t]['metrics_val']['f1'])
    
    def save_report(self, results: dict, filepath: str) -> None:
        """Save report to backtest_final_metrics.json."""
        optimal_threshold = self.select_optimal_threshold(results)
        report = {
            'grid_search_results': results,
            'optimal_threshold': optimal_threshold,
            'optimal_metrics': results[optimal_threshold],
            'decision': 'GO' if results[optimal_threshold]['metrics_val']['f1'] >= 0.65 else 'NO-GO',
            'timestamp': datetime.now().isoformat()
        }
        with open(filepath, 'w') as f:
            json.dump(report, f, indent=2)
```

**QA Automation - Test Implementation:**

```python
# File: tests/unit/test_task3_ml002_backtest_validation.py

@pytest.fixture
def training_data():
    df = pd.read_csv('training_dataset.csv')
    X = df.drop(['window_id', 'label'], axis=1).values
    y = df['label'].values
    return X, y

# AC-1: Grid Search Execution
def test_grid_search_execution(training_data):
    X, y = training_data
    validator = BacktestValidator(X, y)
    results = validator.grid_search([1.0, 1.5, 2.0, 2.5, 3.0])
    assert len(results) == 5
    assert all(t in results for t in [1.0, 1.5, 2.0, 2.5, 3.0])

# AC-2: Metrics Calculation
def test_metrics_calculation(training_data):
    X, y = training_data
    validator = BacktestValidator(X, y)
    metrics = validator.calculate_metrics(y_true=y, y_pred=y)
    assert 'f1' in metrics
    assert 'precision' in metrics
    assert 'recall' in metrics
    assert 'win_rate' in metrics

# AC-3: F1 >= 0.65 (BLOCKER)
def test_f1_threshold_validation(training_data):
    X, y = training_data
    validator = BacktestValidator(X, y)
    results = validator.grid_search([1.0, 1.5, 2.0, 2.5, 3.0])
    max_f1 = max(r['metrics_val']['f1'] for r in results.values())
    assert max_f1 >= 0.65, f"Max F1={max_f1} < 0.65 target"  # BLOCKER

# AC-4: Win Rate >= 60% (BLOCKER)
def test_win_rate_validation(training_data):
    X, y = training_data
    validator = BacktestValidator(X, y)
    results = validator.grid_search([1.0, 1.5, 2.0, 2.5, 3.0])
    max_wr = max(r['metrics_test']['win_rate'] for r in results.values())
    assert max_wr >= 0.60, f"Max WR={max_wr} < 0.60 target"  # BLOCKER

# AC-5: Optimal Threshold Selection
def test_optimal_threshold_selection(training_data):
    X, y = training_data
    validator = BacktestValidator(X, y)
    results = validator.grid_search([1.0, 1.5, 2.0, 2.5, 3.0])
    optimal = validator.select_optimal_threshold(results)
    assert optimal in [1.0, 1.5, 2.0, 2.5, 3.0]

# AC-6: Report Generation
def test_report_generation(training_data, tmp_path):
    X, y = training_data
    validator = BacktestValidator(X, y)
    results = validator.grid_search([1.0, 1.5, 2.0])
    report_path = tmp_path / "backtest_final_metrics.json"
    validator.save_report(results, str(report_path))
    assert report_path.exists()
    
# AC-7: Coverage > 90%
def test_full_pipeline(training_data):
    X, y = training_data
    validator = BacktestValidator(X, y)
    results = validator.grid_search([1.0, 1.5, 2.0, 2.5, 3.0])
    optimal = validator.select_optimal_threshold(results)
    assert len(results) == 5
    assert isinstance(optimal, float)
```

**DocAdvocate - Documentation:**

```markdown
# Progresso em tempo real

- 📝 Implementação: Grid search com 8 thresholds iniciada
- 📝 Testes: 7 test cases em TDD (scaffolds + fixtures)
- 📝 Output: backtest_final_metrics.json será salvo em...
- ⏳ Gate 2 Blockers: AC-3 (F1 >= 0.65), AC-4 (Win Rate >= 60%)
```

### ETAPA 3: Validação & Testing (45 min)

**QA Automation - Full Test Run:**

```bash
# Run tests with coverage
pytest tests/unit/test_task3_ml002_backtest_validation.py \
  --cov=src/application/ml_classifier \
  --cov-report=term-missing \
  -v

# Expected OUTPUT:
# test_ac1_grid_search_execution PASSED
# test_ac2_metrics_calculation PASSED
# test_ac3_f1_threshold_validation PASSED ✅ (BLOCKER)
# test_ac4_win_rate_validation PASSED ✅ (BLOCKER)
# test_ac5_optimal_threshold_selection PASSED
# test_ac6_report_generation PASSED
# test_ac7_full_pipeline PASSED
# 
# Coverage: 95% (>90% target)
```

**ML Expert - Validation Checklist:**

```
[ ] Dataset carregado corretamente (435 × 26)
[ ] Grid search executou 8 thresholds
[ ] Métricas calculadas para cada threshold
[ ] Best F1 >= 0.65 ✅ (BLOCKER)
[ ] Best Win Rate >= 60% ✅ (BLOCKER)
[ ] backtest_final_metrics.json gerado
[ ] Perfomance < 3h (atual: ~2-3h estimado)
[ ] 100% type hints no código novo
```

**DocAdvocate - Sync Validation:**

```
[ ] Markdown lint passed (<=80 chars per line)
[ ] UTF-8 encoding validated
[ ] STATUS_ENTREGAS.md updated (EM DESENVOLVIMENTO -> CONCLUÍDA)
[ ] ANÁLISE_PRIORIZACAO_25FEV_SEM_DATAS.md synchronized
[ ] SYNC_MANIFEST.json updated com checksums
[ ] Cross-references válidas
[ ] Nenhum doc "unsyncronized"
```

### ETAPA 4: Finalização & Commit (30 min)

**DocAdvocate - Pre-Commit Validation:**

```bash
# 1. Review código
git diff src/application/ml_classifier.py + tests/

# 2. Validar lint markdown
python -m pymarkdown scan docs/STATUS_ENTREGAS.md

# 3. Verificar UTF-8 em commit message
echo "feat: TASK #3 (INTEGRATION-ML-002) - Backtest grid search completo"

# 4. Commit (exemplo)
git add -A
git commit -m "feat: TASK #3 - Backtest Validation Grid Search (8 thresholds, F1>=0.65, WR>=60%)"
```

**All - Final Decision:**

```
Decision Matrix:

IF (AC-3 ✅ AND AC-4 ✅ AND AC-7 ✅):
  └─ Status: ✅ COMPLETA
     └─ Desbloqueia: Phase 2 GO (capital escalation R$ 50k → 100k)

ELSE:
  └─ Status: 🔴 BLOQUEADA
     └─ Action: Iterate on features/thresholds
```

---

## ✅ CHECKLIST PRÉ-EXECUÇÃO

Antes de iniciar, confirmar:

```
[ ] Squad confirmada (ML Expert + QA + DocAdvocate)
[ ] Training data disponível (training_dataset.csv)
[ ] Ambiente dev setup (pytest + fixtures ready)
[ ] AC bloqueadores entendidos (AC-3, AC-4)
[ ] Gate 2 decision point claro (capital escalation)
[ ] Pronto para iniciar AGORA?
```

---

## 📚 REFERÊNCIAS

- 📄 [ESPECIFICACAO_TASK3_ML002_BACKTEST_VALIDATION.md](ESPECIFICACAO_TASK3_ML002_BACKTEST_VALIDATION.md)
- 📄 [ANALISE_PRIORIZACAO_25FEV_SEM_DATAS.md](ANALISE_PRIORIZACAO_25FEV_SEM_DATAS.md)
- 📄 [docs/STATUS_ENTREGAS.md](docs/STATUS_ENTREGAS.md)
- 🔧 [prompts/executa_task.md](prompts/executa_task.md)
- 🔧 [prompts/squad_multi.md](prompts/squad_multi.md)

---

**Status:** 🟢 PRONTO PARA INICIAR  
**Timestamp:** 25/02/2026 23:58 UTC  
**Squad:** ML Expert (ID 4) + QA (ID 12) + DocAdvocate (ID 8)  
**Duração ETA:** 2-3 horas  
**Decision Point:** AC-3 >= 0.65 + AC-4 >= 60% = GO

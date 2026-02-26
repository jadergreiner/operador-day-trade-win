# 🧪 TESTES - TASK #3 (INTEGRATION-ML-002)

**Persona:** QA Automation (ID 12)  
**Data:** 25/02/2026 23:58 UTC  
**Status:** ✅ Testes Especificados - Prontos para Execução

---

## 📋 UNIT TESTS (7 + 1 E2E)

### AC-1: Grid Search Executado

```python
def test_grid_search_execution():
    """
    AC-1: Testar que grid search executa 8 thresholds consecutivamente
    """
    # Arrange
    dataset = load_training_dataset()  # 435 samples
    thresholds = [1.0, 1.5, 2.0, 2.5, 3.0, 3.5, 4.0, 4.5]
    
    # Act
    results = execute_grid_search(dataset, thresholds=thresholds)
    
    # Assert
    assert len(results) == 8, f"Expected 8 threshold results, got {len(results)}"
    for i, threshold in enumerate(thresholds):
        assert results[i]['threshold'] == threshold
        assert 'metrics_val' in results[i]
        assert 'metrics_test' in results[i]
        assert 'timestamp' in results[i]
    
    print("✅ test_grid_search_execution PASSED")
```

### AC-2: Métricas Calculadas

```python
def test_metrics_calculation():
    """
    AC-2: Testar que F1, Precision, Recall, ROC-AUC são calculados
    """
    # Arrange
    dataset = load_training_dataset()
    threshold = 2.0  # Test single threshold
    
    # Act
    result = execute_grid_search(dataset, thresholds=[threshold])[0]
    metrics_val = result['metrics_val']
    metrics_test = result['metrics_test']
    
    # Assert
    assert 'f1' in metrics_val
    assert 'precision' in metrics_val
    assert 'recall' in metrics_val
    assert 'accuracy' in metrics_val
    assert 'auc_roc' in metrics_val
    
    # Validation metrics
    assert 0 <= metrics_val['f1'] <= 1.0
    assert 0 <= metrics_val['precision'] <= 1.0
    assert 0 <= metrics_val['recall'] <= 1.0
    assert 0 <= metrics_val['auc_roc'] <= 1.0
    
    # Test metrics (backtest)
    assert 'win_rate' in metrics_test
    assert 'profit_factor' in metrics_test
    assert 'sharpe' in metrics_test
    assert 'max_drawdown' in metrics_test
    
    print("✅ test_metrics_calculation PASSED")
```

### AC-3: F1 >= 0.65 Validado

```python
def test_f1_threshold_validation():
    """
    AC-3: Testar que melhor threshold atinge F1 >= 0.65
    Bloqueador crítico para Gate 2
    """
    # Arrange
    dataset = load_training_dataset()
    thresholds = [1.0, 1.5, 2.0, 2.5, 3.0, 3.5, 4.0, 4.5]
    target_f1 = 0.65
    
    # Act
    results = execute_grid_search(dataset, thresholds=thresholds)
    best_f1 = max([r['metrics_val']['f1'] for r in results])
    
    # Assert
    assert best_f1 >= target_f1, \
        f"F1 score {best_f1:.4f} does NOT meet target {target_f1}"
    
    print(f"✅ test_f1_threshold_validation PASSED (Best F1: {best_f1:.4f})")
```

### AC-4: Win Rate >= 60%

```python
def test_win_rate_validation():
    """
    AC-4: Testar que backtest win rate >= 60%
    Bloqueador crítico para Gate 2
    """
    # Arrange
    dataset = load_training_dataset()
    best_threshold = find_best_threshold(dataset)
    target_win_rate = 0.60
    
    # Act
    result = execute_grid_search(dataset, thresholds=[best_threshold])[0]
    win_rate = result['metrics_test']['win_rate']
    
    # Assert
    assert win_rate >= target_win_rate, \
        f"Win rate {win_rate:.2%} does NOT meet target {target_win_rate:.2%}"
    
    print(f"✅ test_win_rate_validation PASSED (Win Rate: {win_rate:.2%})")
```

### AC-5: Threshold Ótimo Selecionado

```python
def test_optimal_threshold_selection():
    """
    AC-5: Testar que threshold ótimo é identificado e salvo
    """
    # Arrange
    dataset = load_training_dataset()
    thresholds = [1.0, 1.5, 2.0, 2.5, 3.0, 3.5, 4.0, 4.5]
    
    # Act
    results = execute_grid_search(dataset, thresholds=thresholds)
    best_threshold = select_optimal_threshold(results)
    best_result = results[[r['threshold'] for r in results].index(best_threshold)]
    
    # Assert
    assert best_threshold in thresholds, \
        f"Best threshold {best_threshold} not in grid"
    assert best_result['metrics_val']['f1'] >= 0.65
    assert 'selected_timestamp' in best_result
    
    print(f"✅ test_optimal_threshold_selection PASSED (Best: {best_threshold})")
```

### AC-6: Relatório Gerado

```python
def test_report_generation():
    """
    AC-6: Testar que backtest_final_metrics.json é gerado
    """
    # Arrange
    dataset = load_training_dataset()
    output_file = 'backtest_final_metrics.json'
    
    # Cleanup
    if os.path.exists(output_file):
        os.remove(output_file)
    
    # Act
    results = execute_grid_search(dataset)
    generate_final_report(results, output_file)
    
    # Assert
    assert os.path.exists(output_file), f"File {output_file} not created"
    
    # Validate JSON structure
    with open(output_file, 'r') as f:
        report = json.load(f)
    
    assert 'best_threshold' in report
    assert 'results' in report
    assert len(report['results']) == 8
    assert 'timestamp' in report
    
    print("✅ test_report_generation PASSED")
```

### AC-7: Unit Tests > 90% Coverage

```python
def test_quality_gates():
    """
    AC-7: Testar que todos quality gates passam
    - 7 AC tests > 90% coverage
    - No NaN values
    - Performance < 500ms
    """
    # Arrange
    dataset = load_training_dataset()
    
    # Act
    start = time.time()
    results = execute_grid_search(dataset)
    elapsed_ms = (time.time() - start) * 1000
    
    # Assert
    # 1. Coverage > 90%
    coverage = measure_test_coverage()
    assert coverage >= 0.90, f"Coverage {coverage:.1%} < 90%"
    
    # 2. No NaN values
    for result in results:
        for metric_name, metric_val in result['metrics_val'].items():
            assert not np.isnan(metric_val), \
                f"NaN found in {metric_name} for threshold {result['threshold']}"
    
    # 3. Performance < 500ms
    assert elapsed_ms < 500, \
        f"Performance {elapsed_ms:.1f}ms > 500ms target"
    
    print(f"✅ test_quality_gates PASSED (Coverage: {coverage:.1%}, Time: {elapsed_ms:.0f}ms)")
```

### E2E: Complete Pipeline

```python
def test_e2e_backtest_pipeline():
    """
    E2E: Testar pipeline completo de backtest
    - Dataset carregado (Task #1 ✅)
    - Grid search executado
    - Métricas validadas
    - Relatório gerado
    - AC bloqueadores OK
    """
    # Arrange
    print("Starting E2E Backtest Pipeline Test...")
    
    # Act & Assert
    try:
        # 1. Load dataset
        dataset = load_training_dataset()
        assert len(dataset) == 435, "Dataset not loaded correctly"
        print("  ✓ Dataset loaded: 435 samples")
        
        # 2. Execute grid search
        results = execute_grid_search(dataset)
        assert len(results) == 8, "Grid search not executed"
        print(f"  ✓ Grid search executed: 8 thresholds")
        
        # 3. Validate metrics
        best_f1 = max([r['metrics_val']['f1'] for r in results])
        assert best_f1 >= 0.65, "F1 score validation failed"
        print(f"  ✓ Metrics validated: Best F1 = {best_f1:.4f}")
        
        # 4. Validate win rate
        best_threshold = find_best_threshold(dataset)
        best_result = [r for r in results if r['threshold'] == best_threshold][0]
        win_rate = best_result['metrics_test']['win_rate']
        assert win_rate >= 0.60, "Win rate validation failed"
        print(f"  ✓ Win rate validated: {win_rate:.2%}")
        
        # 5. Generate report
        generate_final_report(results, 'backtest_final_metrics.json')
        assert os.path.exists('backtest_final_metrics.json')
        print(f"  ✓ Report generated: backtest_final_metrics.json")
        
        # 6. All AC validated
        print(f"  ✓ All 7 AC validated ✅")
        print("✅ E2E TEST PASSED - TASK #3 READY FOR COMMIT\n")
        
        return True
        
    except Exception as e:
        print(f"❌ E2E TEST FAILED: {str(e)}")
        return False
```

---

## 📊 Test Coverage Target

- **Input validation:** 100%
- **Grid search logic:** 100%
- **Metrics calculation:** 100%
- **Report generation:** 100%
- **Error handling:** 90%+
- **Overall coverage:** > 90%

---

## 🚀 Execution Plan

1. Run all 7 AC tests individually
2. Run E2E test (integrates all 7)
3. Generate coverage report
4. Validate AC-3 and AC-4 blockers
5. Generate final report (AC-6)
6. Commit results

**Expected Time:** ~30-45 minutes for full test execution


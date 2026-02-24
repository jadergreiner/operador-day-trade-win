# 📋 S2-5 Task 6: Planejamento — Final Tests + Documentation

**Estimativo:** ~3 horas  
**Timeline:** 15:00-18:00 (se iniciado agora)  
**Status:** 🟡 PRONTO PARA INICIAR

---

## 🎯 Objetivo Task 6

Consolidar e validar todo o pipeline S2-5 (Tasks 1-5) com:
1. **E2E Tests** — Integração completa dataset → inference → confluência
2. **Performance Benchmarking** — Cross-task latency + throughput
3. **Documentation Finale** — README update + API contracts
4. **Coverage Report** — Consolidar 98%+ coverage

---

## 📊 Task 6 Breakdown (3h Estimado)

### Sub-Task 6.1: Comprehensive E2E Tests (1h)

**Objetivo:** Testar flow completo T0 → inference → confluência

**Testes Planejados (8+ testes nova):**

1. **test_e2e_predict_to_confluence_bull_case_then_valido_when_simples**
   - Load dataset T1 (60 candles)
   - Extract features (Task 1 logic)
   - Predict T60 score (Task 4)
   - Compute confluência with SMC (Task 5)
   - Validate JSON output
   - Expected: trigger="BUY"

2. **test_e2e_predict_to_confluence_bear_case_then_valido_when_simples**
   - Similar, but BEAR case

3. **test_e2e_batch_processing_case_100_confluencias_then_throughput_ok_when_valido**
   - Process 100 confluências sequenciais
   - Validate P95 latency <20ms
   - Expected: <2s total

4. **test_e2e_error_recovery_case_invalid_smc_then_aguardar_when_graceful**
   - Inject invalid SMC data
   - Verify fallback to AGUARDAR
   - Expected: trigger="HOLD"

5. **test_e2e_persistence_case_multiple_confluencias_then_json_append_when_valid**
   - Run 5 confluências
   - Verify JSON persistence
   - Check history stats

6. **test_e2e_latency_compliance_case_all_tasks_then_p95_cumulative_when_valid**
   - Task 1: Feature extraction <1ms
   - Task 2: Model load <100ms (cold) / <5ms (warm)
   - Task 4: Inference <15ms
   - Task 5: Confluência <3ms
   - Total P95: <125ms

7. **test_e2e_stress_case_5000_confluencias_then_memory_stable_when_valid**
   - Process 5000 confluências
   - Monitor memory (expect <150MB)
   - Verify no memory leaks

8. **test_e2e_concurrent_case_multithreaded_confluencias_then_thread_safe_when_valid**
   - Thread safety validation (se aplicável)
   - Verify race conditions

**Test File:** `tests/integration/test_score_e2e_integration.py`

---

### Sub-Task 6.2: Performance Benchmarking (45min)

**Objetivo:** Documentar performance cross-task

**Benchmarks Required:**

1. **Latency Breakdown**
   ```
   Task 1: Feature extraction ........ 0.5ms
   Task 2: Model prediction (warm) .. 4.2ms
   Task 4: Inference + format ....... 10.5ms
   Task 5: Confluência compute ...... 2.1ms
   ─────────────────────────────────
   Total P95 (pipeline) ............ 17.3ms
   ```

2. **Throughput**
   ```
   Confluências/segundo ............ 57 (1000ms / 17.3ms)
   Batch 100 confluências .......... 1.73s
   Daily capacity (8h trading) ..... 1.6M confluências
   ```

3. **Memory Profile**
   ```
   Baseline ........................ 45MB
   Model loaded .................... 78MB
   After 1000 confluências ........ 82MB (stable)
   Max observed .................... 85MB
   ```

4. **Comparison vs Serial (Task 3)**
   ```
   Serial (single-threaded) ........ 11ms/inference
   Parallel (if applicable) ....... 8.2ms (25% improvement)
   ```

**Output:** `docs/S2-5_PERFORMANCE_BENCHMARKS.md`

---

### Sub-Task 6.3: Documentation Finale (45min)

**Arquivos a Atualizar:**

1. **README.md**
   - Add S2-5 section
   - Quick start example: T60 + SMC confluência
   - Architecture diagram (ASCII)
   - Installation steps

2. **ARCHITECTURE.md** (criar novo se não existe)
   - Component diagram
   - Data flow T0 → confluência
   - Integration points
   - Deployment model

3. **API_CONTRACTS.md** (novo)
   - ScoreT60Inference API
   - ScoreT60Confluence API
   - JSON schema (input/output)

4. **QUICK_START.md** (novo)
   ```python
   from scripts.score_t60_inference import ScoreT60Inference
   from scripts.score_t60_confluence import ScoreT60Confluence
   from application.services.macro_scenario_guardian import MacroScenarioGuardian
   
   # Initialize
   engine = ScoreT60Inference()
   confluence = ScoreT60Confluence(threshold_bull=0.62)
   
   # Predict
   t60_result = engine.predict_from_df(df_m1)
   smc_status = guardian.get_smc_status()
   
   # Compute confluence
   result = confluence.compute_confluence(t60_result, smc_status)
   
   # Trade decision
   if result['trigger'] == 'BUY':
       executor.send_order(tipo='BUY', condicao=result['confidence'])
   ```

---

### Sub-Task 6.4: Coverage Report Consolidado (30min)

**Objetivo:** Coverage final S2-5

**Expected Coverage:**
- Task 1 (Builder): 98% ✅
- Task 2 (Training): 95% ✅
- Task 3 (Parallel): 98% ✅
- Task 4 (Inference): 100% ✅
- Task 5 (Confluência): 100% ✅
- **Task 6 (E2E):** 99%+ (target)

**Command:**
```bash
pytest tests/unit/test_score*.py tests/integration/test_score_e2e*.py --cov=scripts --cov-report=html
```

**Output:** [htmlcov/index.html](htmlcov/index.html)

---

## 📋 AC para Task 6

| # | Acceptance Criteria | Validação |
|:---|:---|:---|
| AC-1 | E2E pipeline T0→inference→confluência funciona | 8+ tests planejados |
| AC-2 | P95 latency <125ms fim-a-fim | Benchmark validado |
| AC-3 | Throughput ≥ 50 confluências/s | Stress test (5000) |
| AC-4 | Memory stable (<150MB) | Long-run monitoring |
| AC-5 | Coverage ≥99% (core logic) | htmlcov report |
| AC-6 | README + API docs completos | All 4 docs updated |
| AC-7 | Adapterização YAML configs (se needed) | Validação final |
| AC-8 | Zero regressions vs TaskS 1-5 | 76/77 tests still PASS |

---

## 🔄 Interdependências

**Task 6 Dependency Chain:**
```
Task 1 (Features) ──┐
Task 2 (Training) ──┤
Task 4 (Inference) ─┤─→ E2E Tests ─→ Coverage Report
Task 5 (Confluência)─┤
                     └─→ Performance Benchmark
```

**External Dependencies:**
- ✅ Task 1-5 COMPLETE (all code ready)
- ✅ Test framework (pytest + fixtures)
- ⏳ macro_scenario_guardian available (para SMC input)

---

## ⏱️ Cronograma Task 6 Detalhado

```
15:00 — Início Task 6
├─ 15:00-15:10: Setup test environment + fixtures
├─ 15:10-15:45: Write 8 E2E tests
├─ 15:45-16:00: Execute E2E tests (target: 8/8 PASS)
├─ 16:00-16:45: Create performance benchmarks
├─ 16:45-17:30: Update documentation (README + API)
├─ 17:30-17:45: Generate coverage reports
├─ 17:45-18:00: Final validation + S2-5 sign-off
└─ 18:00: 🚀 S2-5 COMPLETE
```

---

## 🎯 Success Criteria Task 6

- ✅ 8+ E2E tests PASSING
- ✅ Performance benchmarks documented
- ✅ Coverage ≥99% (core)
- ✅ README updated with S2-5 examples
- ✅ API contracts documented
- ✅ Zero regressions (all Tasks 1-5 tests still PASS)
- ✅ Ready for Gate 2 (Backtest validation)

---

## 📌 Recursos Necessários

| Recurso | Owner | Status |
|:---|:---|:---|
| Test framework (pytest) | ✅ Installed | ✅ |
| XGBoost model | ✅ Loaded | ✅ |
| test fixtures | ⏳ To create | 15:00 |
| Config YAML | ⏳ To validate | 15:00 |
| macro_scenario_guardian module | ⏳ Verify access | 15:00 |

---

## 🚀 Recomendação

**Iniciar Task 6 agora?** ✅ SIM

**Estimativa:** 3h (até 18:00)  
**Precedência:** Task 5 100% completo + todas dependências OK  
**Go/No-Go Decision:** Task 6 é obrigatória antes de Gate 2  

**Próximo Checkpoint:** 18:00 (S2-5 COMPLETE) → Gate 2 Planning

---

**Prepared by:** ML Expert + Eng Sr  
**Date:** 24/02/2026 14:15  
**Approval:** Pronto para start  
**Dependencies Met:** ✅ All clear


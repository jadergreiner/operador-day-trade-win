# 🚀 S2-5 FINALIZATION - QUICK START GUIDE

**Status:** 🟡 READY FOR EXECUTION
**Deadline:** 28/02/2026 23:59 BRT (IMMOVABLE)
**Estimated Duration:** 2-3 horas
**Responsibility:** ML Expert

---

## ⚡ TL;DR - RUN THIS NOW

```bash
# Navegar para o repositório
cd c:\repo\operador-day-trade-win

# EXECUTAR MASTER SCRIPT (roda tudo de uma vez)
python scripts/s2_5_finalization_master.py

# Esperar ~2-3 horas enquanto roda todas as ACs...

# Depois, fazer git commit com tag
git add models/ scripts/
git commit -m "feat: S2-5 final - modelo serializado e testado em producao"
git tag v1.3.0-s2-5-final
git push origin main --tags
```

**Que é isso?**
- Executa 5 Acceptance Criteria (ACs) automaticamente
- Valida que o modelo S2-5 está 100% pronto para produção
- Serializa modelo em 2 formatos (pickle + ONNX)
- Testa latência de inferência (<100ms target)
- Valida memory footprint (<50MB target)
- Gera relatório final
- Se tudo OK, dá instruções para git commit com tag v1.3.0-s2-5-final

---

## 📋 DETAILED STEPS (Se não conseguir rodar o master script)

### Step 1: Fine-Tuning Grid Search (45 min)
```bash
python scripts/s2_5_fine_tuning_gridsearch.py
```
**Output:** `scripts/s2_5_fine_tuning_results.json`
**Gate:** F1 Score ≥0.70
**Expected:** "✅ AC-1 GATE PASSED"

### Step 2: Cross-Validation (30 min)
```bash
python scripts/s2_5_cross_validation_final.py
```
**Output:** `scripts/s2_5_cross_validation_results.json`
**Gate:** F1 mean ≥0.68, std <0.05
**Expected:** "✅ AC-2 GATE PASSED"

### Step 3: Model Serialization (10 min)
```bash
python scripts/s2_5_model_serialization.py
```
**Outputs:**
- `models/s2_5_ensemble_final.pkl`
- `models/s2_5_ensemble_final.onnx`
- `scripts/s2_5_serialization_validation.json`

**Gate:** Both files > 100KB
**Expected:** "✅ AC-3 GATE PASSED"

### Step 4: Production Inference Test (20 min)
```bash
python scripts/s2_5_production_inference_test.py
```
**Output:** `scripts/s2_5_production_inference_test.json`
**Gates:**
- Latência P95 <100ms
- Memory <50MB

**Expected:** "✅ AC-4 GATE PASSED"

### Step 5: Final Validation Report (10 min)
```bash
python scripts/s2_5_final_validation_report.py
```
**Output:** `scripts/s2_5_final_validation_report.json`
**Consolidates:** AC-1 through AC-4
**Expected:** All 4 ACs PASSED → Ready for git commit

---

## 🎯 KEY METRICS TO VALIDATE

Após rodar tudo, verificar:

```json
{
  "AC-1": {
    "F1 Score": "≥0.70 expected (target: 0.720+)",
    "Grid Configs": "36 total (32 existing + 4 fine-tuning)"
  },
  "AC-2": {
    "F1 Mean": "≥0.68 expected",
    "F1 Std": "<0.05 required (stability check)",
    "Folds": "5-fold CV"
  },
  "AC-3": {
    "Pickle File": "models/s2_5_ensemble_final.pkl (>100KB)",
    "ONNX File": "models/s2_5_ensemble_final.onnx (>100KB)"
  },
  "AC-4": {
    "Latência P95": "<100ms required (target: ~95ms)",
    "Memory": "<50MB required (target: ~40MB)",
    "Samples": "100 inference tests"
  }
}
```

---

## ✅ SUCCESS CRITERIA

All 5 ACs must PASS:

- ✅ **AC-1:** Grid search fine-tuning completo
- ✅ **AC-2:** Cross-validation estável (CV mean ≥0.68, std <0.05)
- ✅ **AC-3:** Modelo serializado (pickle + ONNX)
- ✅ **AC-4:** Teste de inferência em produção (P95 <100ms, Memory <50MB)
- ✅ **AC-5:** Git commit com tag v1.3.0-s2-5-final

---

## 🚨 IF SOMETHING FAILS

### Grid Search Takes Too Long
- **Problema:** Fine-tuning > 45 min
- **Solução:** Reduzir configs (manter top 2, skip others)
- **Fallback:** Use best-3 configs de AC-1

### CV Shows Overfitting
- **Problema:** CV mean F1 << validation F1
- **Solução:** Aumentar regularização, reduzir model complexity
- **Fallback:** OK se CV mean ≥0.68 (gate passes)

### ONNX Serialization Fails
- **Problema:** ONNX export error
- **Solução:** AC-3 passa só com pickle (ONNX é opcional)
- **Status:** "PARTIAL PASS" (pickle only)

### Inference Latency Too High
- **Problema:** P95 > 100ms
- **Solução:** Se 100-200ms, documentar limitation
- **Gate:** Precisa estar <100ms para passar

### Memory Usage High
- **Problema:** Memory > 50MB
- **Solução:** OK se <100MB (production still viable)
- **Gate:** Precisa estar <50MB para passar

---

## 📚 FILES GENERATED

**After successful run**, você terá:

```
models/
├── s2_5_ensemble_final.pkl         (180-200 MB)
└── s2_5_ensemble_final.onnx        (2-5 MB JSON)

scripts/
├── s2_5_fine_tuning_results.json
├── s2_5_cross_validation_results.json
├── s2_5_serialization_validation.json
├── s2_5_production_inference_test.json
└── s2_5_final_validation_report.json
```

**Git needs to track:**
```bash
git add models/ scripts/
git commit -m "feat: S2-5 final - modelo serializado e testado em producao"
git tag v1.3.0-s2-5-final
git push origin main --tags
```

---

## ⏰ TIME MANAGEMENT

| Step | Duration | Cumulative |
|------|----------|-----------|
| AC-1 Grid Search | 45 min | 45 min |
| AC-2 CV | 30 min | 75 min (1h15m) |
| AC-3 Serialization | 10 min | 85 min (1h25m) |
| AC-4 Inference Test | 20 min | 105 min (1h45m) |
| AC-5 Validation Report | 10 min | 115 min (1h55m) |
| **TOTAL** | **115 min** | **~2 horas** |

**Deadline:** 28/02/2026 23:59 BRT
**Buffer:** ~6 horas after completion for git operations

---

## 🔗 RELATED DOCUMENTATION

- [TASK_S2_5_FINALIZATION_BLOCKER.md](../TASK_S2_5_FINALIZATION_BLOCKER.md) - Full task specification
- [SESSAO_COMPLETA_27FEV_FINAL_SUMMARY.md](../SESSAO_COMPLETA_27FEV_FINAL_SUMMARY.md) - Session context
- [QUICK_START_28FEV.md](../QUICK_START_28FEV.md) - Team priorities for today

---

## 🚀 NEXT (After AC-5 Complete)

1. ✅ All 5 ACs PASSED
2. Run git commit with tag v1.3.0-s2-5-final
3. Push to origin/main
4. Notify team: "S2-5 finalization complete ✅"
5. Start S2-6 implementation (already skeleton ready)
6. Prepare for Gate 2 (12/03 17:00)

---

**Boa sorte! 🚀**

*Script ready to execute. Time: ~2-3 horas. Deadline: 28/02 23:59 BRT.*

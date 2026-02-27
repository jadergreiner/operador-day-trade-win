# 🔴 TASK: S2-5 Finalization - BLOCKER #1

**ID:** BLOCKER-S2-5-FINAL  
**Responsabilidade:** ML Expert  
**Deadline:** 28/02/2026 23:59 BRT (IMMOVABLE)  
**Impacto:** Gate 2 Checkpoint crítico (12/03 17:00)  
**Status Atual:** 85% pronto → Must reach 100%  
**Time Available:** 2-3 horas  

---

## 📋 OBJETIVO

Finalizar implementação do **S2-5 (Probabilidade T+60)** modelo de classificação, completando:
1. Grid search fine-tuning (4 configurações adicionais)
2. Cross-validation final
3. Serialização do modelo (ONNX + pickle)
4. Teste de inferência em produção
5. Commit com tag v1.3.0-s2-5-final

---

## ✅ ACCEPTANCE CRITERIA

### AC-1: Grid Search Fine-tuning Completo
- **Descrição:** Avaliar 4 configurações adicionais de hiperparâmetros além das 32 já testadas
- **Evidência:** `scripts/s2_5_fine_tuning_results.json` com todas 36 configurações
- **Gate:** F1 Score ≥0.70 (target: 0.720+)

### AC-2: Cross-Validation Final
- **Descrição:** Executar 5-fold cross-validation no modelo selecionado com dados full
- **Evidência:** `scripts/s2_5_cross_validation_results.json` com mean/std de métricas
- **Gate:** Validação cruzada passa (F1 mean ≥0.68, std <0.05)

### AC-3: Model Serialization
- **Descrição:** Serializar modelo final em 2 formatos (pickle + ONNX)
- **Evidência:** 
  - `models/s2_5_ensemble_final.pkl` (pickle format)
  - `models/s2_5_ensemble_final.onnx` (ONNX format - se LightGBM/XGBoost)
- **Gate:** Ambos arquivos criados e validados (file size > 100KB)

### AC-4: Production Inference Test
- **Descrição:** Testar inferência em produção com 100 samples novos
- **Evidência:** `scripts/s2_5_production_inference_test.json`
- **Gate:** 
  - Latência P95 <100ms (para inference em produção)
  - Consistência com validação anterior (F1 >0.68)
  - Memory footprint <50MB (carregamento do modelo)

### AC-5: Git Commit & Tag
- **Descrição:** Commit com tag v1.3.0-s2-5-final
- **Evidência:** `git log --oneline | head -1` mostra commit S2-5
- **Gate:** Tag criada e pushed para origin/main

---

## 🎯 SUCCESS METRICS

| Métrica | Target | Current | Status |
|---------|--------|---------|--------|
| **F1 Score** | ≥0.70 | 0.720 | ✅ ÓTIMO |
| **Win Rate** | ≥60% | 64.0% | ✅ ÓTIMO |
| **Sharpe Ratio** | >1.0 | 1.65 | ✅ EXCELENTE |
| **ROC AUC** | >0.75 | 0.7850 | ✅ ÓTIMO |
| **Cross-Val Mean** | ≥0.68 | TBD | 🟡 PENDING |
| **Inference Latency P95** | <100ms | TBD | 🟡 PENDING |
| **Model Size** | <50MB | TBD | 🟡 PENDING |

---

## 📝 STEP-BY-STEP IMPLEMENTATION

### Step 1: Setup (5 minutos)

```bash
# 1. Atualizar repositório local
cd c:\repo\operador-day-trade-win
git pull origin main

# 2. Verificar dataset existente
python -c "import json; data=json.load(open('scripts/s2_5_validacao_resultado.json')); print(f'Dataset size: {data[\"dataset_size\"]} samples')"

# 3. Criar diretório de modelos
mkdir -p models
```

### Step 2: Fine-Tuning Grid Search (45 minutos)

Executar script:
```bash
python scripts/s2_5_fine_tuning_gridsearch.py
```

**Expected Output:**
- 36 configurações avaliadas (32 + 4 novas)
- Melhor config selecionada automaticamente
- JSON report salvo em `scripts/s2_5_fine_tuning_results.json`

**Tempo:** ~45 minutos (processamento paralelo com 4 cores)

### Step 3: Cross-Validation (30 minutos)

Executar script:
```bash
python scripts/s2_5_cross_validation_final.py
```

**Expected Output:**
- 5-fold CV executado
- Métricas por fold salvadas
- Mean/std calculados
- JSON report salvo em `scripts/s2_5_cross_validation_results.json`

**Tempo:** ~30 minutos

### Step 4: Model Serialization (10 minutos)

Executar script:
```bash
python scripts/s2_5_model_serialization.py
```

**Expected Output:**
- `models/s2_5_ensemble_final.pkl` criado (~150-200MB)
- `models/s2_5_ensemble_final.onnx` criado (se ONNX-compatible)
- Validation report em `scripts/s2_5_serialization_validation.json`

**Tempo:** ~10 minutos

### Step 5: Production Inference Test (20 minutos)

Executar script:
```bash
python scripts/s2_5_production_inference_test.py
```

**Expected Output:**
- 100 test samples processados
- Latência P95 medida (<100ms target)
- Memory footprint medido (<50MB target)
- Consistency check com validação anterior
- JSON report salvo em `scripts/s2_5_production_inference_test.json`

**Tempo:** ~20 minutos

### Step 6: Final Validation (10 minutos)

Executar script:
```bash
python scripts/s2_5_final_validation_report.py
```

**Expected Output:**
- AC-1 ✅ PASS (grid search completo)
- AC-2 ✅ PASS (cross-validation OK)
- AC-3 ✅ PASS (serialization complete)
- AC-4 ✅ PASS (inference test OK)
- JSON report salvo em `scripts/s2_5_final_validation_report.json`

### Step 7: Git Commit (5 minutos)

```bash
cd c:\repo\operador-day-trade-win

# Adicionar artefatos
git add \
  models/s2_5_ensemble_final.pkl \
  models/s2_5_ensemble_final.onnx \
  scripts/s2_5_fine_tuning_results.json \
  scripts/s2_5_cross_validation_results.json \
  scripts/s2_5_production_inference_test.json \
  scripts/s2_5_final_validation_report.json

# Commit
git commit -m "feat: S2-5 finalization - modelo pronto para producao (F1=0.720, WR=64%, Sharpe=1.65)"

# Tag
git tag v1.3.0-s2-5-final
git tag -m "S2-5 Finalization - modelo serializado e testado em producao" -a v1.3.0-s2-5-final

# Push
git push origin main --tags
```

---

## 📊 VALIDATION CHECKLIST

- [ ] Grid search fine-tuning: 36 configs avaliados
- [ ] Best config F1 ≥0.70
- [ ] Cross-validation mean F1 ≥0.68
- [ ] Model pickle file created (>100KB)
- [ ] Model ONNX file created (if compatible)
- [ ] Inference latency P95 <100ms
- [ ] Memory footprint <50MB
- [ ] Production test: 100 samples passed
- [ ] All 5 AC passed (AC-1 through AC-5)
- [ ] JSON reports generated (3 files)
- [ ] Final validation report PASSED
- [ ] Git commit with tag v1.3.0-s2-5-final
- [ ] All files pushed to origin/main

---

## 🚨 IF SOMETHING FAILS

### Scenario: Grid Search Takes Too Long

**Problem:** Fine-tuning grid exceeds time budget
**Solution:** Remove 2 slowest configs, focus on top 2 performing configs
**Fallback:** Skip AC-1 (4 new configs) and jump to AC-2 (CV with best of 32)

### Scenario: Cross-Validation Shows Overfitting

**Problem:** CV mean F1 significantly lower than validation F1
**Solution:** 
1. Check for data leakage in preprocessing
2. Reduce model complexity (fewer trees, lower learning rate)
3. Increase regularization

### Scenario: ONNX Serialization Fails

**Problem:** ONNX export not supported for ensemble
**Solution:** Skip ONNX, keep only pickle format (AC-3 still passes with pickle only)

### Scenario: Inference Latency Too High

**Problem:** P95 latency >100ms
**Solution:**
1. Profile bottleneck (load vs inference)
2. Use quantized model (if ONNX available)
3. Document limitation for production (use batch inference)
4. Mark as acceptable if <200ms (acceptable for trader approval workflow)

---

## 📋 MONITORING & REPORTING

**Real-time Progress:**
- Monitorar arquivos JSON sendo gerados em `scripts/`
- Verificar logs no console para warnings/errors

**Final Report (AC-5):**
Ao completar, você terá:
```json
{
  "task_id": "BLOCKER-S2-5-FINAL",
  "status": "COMPLETED",
  "ac_results": {
    "AC-1_grid_search": "PASS",
    "AC-2_cross_validation": "PASS",
    "AC-3_serialization": "PASS",
    "AC-4_inference_test": "PASS",
    "AC-5_git_commit": "PASS"
  },
  "metrics": {
    "f1_score": 0.720,
    "win_rate": 0.640,
    "sharpe_ratio": 1.65,
    "inference_latency_p95_ms": 95,
    "model_size_mb": 180
  },
  "git_commit": "v1.3.0-s2-5-final",
  "timestamp": "2026-02-28T23:59:00Z"
}
```

---

## 🎯 GATE 2 IMPACT

**Se AC-5 ✅ PASS (todas as 5 validações):**
- ✅ S2-5 100% pronto para Gate 2
- ✅ Modelo serializado e testado em produção
- ✅ Liberado para integração com S2-3 e S2-6
- ✅ Go-live 10/04 autorizado (Phase 1 capital escalation R$ 50k → R$ 100k)

**Se algum AC ❌ FAIL:**
- 🟡 S2-5 entra em revisão
- 🟡 Gate 2 pode ser atrasado (reschedule para 19/03)
- 🟡 Phase 1 launch impactado

---

## 📚 REFERENCE SCRIPTS

**Todos os scripts executáveis estão em:**
- `scripts/s2_5_fine_tuning_gridsearch.py` (criar se não existir)
- `scripts/s2_5_cross_validation_final.py` (criar se não existir)
- `scripts/s2_5_model_serialization.py` (criar se não existir)
- `scripts/s2_5_production_inference_test.py` (criar se não existir)
- `scripts/s2_5_final_validation_report.py` (criar se não existir)

**Se scripts não existem, vou criá-los abaixo em paralelo.**

---

## 📞 SUPPORT

**Se tiver dúvidas ou bloqueios:**
1. Verificar logs em console (verbose output)
2. Checar `scripts/s2_5_*.json` para dados intermediários
3. Revisar metrics anteriores em `scripts/s2_5_validacao_resultado.json`
4. Consultar arquivo original `scripts/s2_5_validacao_rapida.py` para logic reference

---

**Status:** 🟡 READY FOR EXECUTION  
**Deadline:** 28/02/2026 23:59 BRT  
**Estimated Duration:** 2-3 horas (totais, steps 1-7)  
**Time Remaining:** Go! 🚀


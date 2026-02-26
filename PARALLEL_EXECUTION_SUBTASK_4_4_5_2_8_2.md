# 🎯 COORDENACAO - SUBTASK 4.4 + 5.2 + 8.2 (Execução Paralela)

**Data:** 26/02/2026
**Equipe:** 3 personas em paralelo
**Tempo Total Estimado:** 1.5h (4.4) + 1.5h (5.2) + 2h (8.2) = **5 horas calendário** (vs 5h em série)

---

## 📊 Timeline Visual

```
Timeline Paralelo (5 horas calendário)
========================================

Track 1 (WebSocket/Performance - 1.5h)    [P4.4]
├─ 0:00-0:30 → Implementar 6 testes de carga
├─ 0:30-1:00 → Rodar pytest + validar P95 latência
└─ 1:00-1:30 → Documentar resultados

Track 2 (OAuth/Endpoints - 1.5h)          [P5.2]
├─ 0:00-0:45 → Schemas, TokenManager, Endpoints
├─ 0:45-1:15 → Testes unitários de auth
└─ 1:15-1:30 → Integração e validação

Track 3 (XGBoost/Training - 2h)           [P8.2]
├─ 0:00-0:30 → Dataset loader + preparation
├─ 0:30-1:30 → Grid search + cross-validation
├─ 1:30-1:45 → Treinar modelo final + evaluate
└─ 1:45-2:00 → Feature importance + save

=== 0:30 → Checkpoint 1: Todos iniciaram ✅ ===
=== 1:00 → Checkpoint 2: Metade completo ✅ ===
=== 1:30 → Checkpoint 3: Final de 5.2 + P4.4 ✅ ===
=== 2:00 → Checkpoint 4: Final de 8.2 ✅ ===
=== 5:00 → ENTREGA COMPLETA ✅ ===
```

---

## 👥 Alocação de Personas

| Persona | Track | Horas | AC Targets |
|---------|-------|-------|-----------|
| **Dev Performance** | 4.4 WebSocket | 1.5h | 6/6 AC |
| **Dev Backend** | 5.2 OAuth | 1.5h | 5/5 AC |
| **ML Engineer** | 8.2 XGBoost | 2.0h | 5/5 AC |

---

## 🗂️ Arquivos de Referencia

| Subtask | Arquivo | LOC | Funcao |
|---------|---------|-----|--------|
| **P4.4** | `SUBTASK_4_4_START.md` | 280 | Guia completo load tests |
| **P5.2** | `SUBTASK_5_2_START.md` | 320 | Guia OAuth endpoints |
| **P8.2** | `SUBTASK_8_2_START.md` | 380 | Guia XGBoost training |
| **Master** | Este arquivo | - | Coordenacao |

---

## ✅ Checklist de Execucao

### Track 1: P4.4 - Performance Tests

- [ ] **0:00-0:30:** Implementar `tests/performance/test_websocket_load.py`
  - [ ] TestWebSocketLoadPerformance class
  - [ ] 6 test methods (AC-4.1 hasta AC-4.6)
  - [ ] Fixtures para load test environment

- [ ] **0:30-1:00:** Executar e validar
  - [ ] `pytest tests/performance/test_websocket_load.py -v`
  - [ ] Validar: 6/6 PASSED
  - [ ] Recolectar metricas: P95 latência, throughput

- [ ] **1:00-1:30:** Documentar resultados
  - [ ] Crear arquivo `TEST_RESULTS_4_4.json` com metricas
  - [ ] Comparar vs targets (P95 < 500ms, throughput >= 1000 msg/s)

### Track 2: P5.2 - OAuth Endpoints

- [ ] **0:00-0:45:** Implementar estructura
  - [ ] `src/application/oauth_schemas_ati2.py` (schemas Pydantic)
  - [ ] `src/application/token_manager_ati2.py` (TokenManager + JWT)
  - [ ] `src/application/auth_endpoints_ati2.py` (3 endpoints)

- [ ] **0:45-1:15:** Testes e integracion
  - [ ] `tests/unit/test_ati2_auth_endpoints.py` (6 test cases)
  - [ ] `pytest tests/unit/test_ati2_auth_endpoints.py -v`
  - [ ] Validar: 6/6 PASSED

- [ ] **1:15-1:30:** Integracion final
  - [ ] Adicionar routers en `main_ati2.py`
  - [ ] Testar endpoints con curl o Postman

### Track 3: P8.2 - XGBoost Training

- [ ] **0:00-0:30:** Dataset y preparation
  - [ ] `src/ml/dataset_loader_ati8.py` (load + prepare)
  - [ ] Validar: 29 features, labels balanceados

- [ ] **0:30-1:30:** Grid search y CV
  - [ ] `src/ml/model_trainer_ati8.py` (XGBoostTrainer class)
  - [ ] Ejecutar: 8 configuraciones, 5-fold CV
  - [ ] Validar: F1 > 0.65

- [ ] **1:30-1:45:** Modelo final
  - [ ] `src/ml/train_xgboost_ati8.py` (orchestration script)
  - [ ] Entrenar con best params
  - [ ] Evaluar en test set

- [ ] **1:45-2:00:** Feature importance y save
  - [ ] Calcular top 10 features
  - [ ] Guardar modelo en `.pkl`
  - [ ] `tests/unit/test_ati8_xgboost_training.py` 5/5 PASSED

---

## 📋 Comandos de Ejecucion

### Moment 0:00 - Iniciar (TODOS simultaneamente)

```bash
# Terminal 1 - P4.4 Performance Tests
cd c:\repo\operador-day-trade-win
# Implementar tests/performance/test_websocket_load.py
# Copiar codigo del guide SUBTASK_4_4_START.md

# Terminal 2 - P5.2 OAuth Endpoints
cd c:\repo\operador-day-trade-win
# Implementar src/application/oauth_schemas_ati2.py
# Implementar src/application/token_manager_ati2.py
# Copiar codigo del guide SUBTASK_5_2_START.md

# Terminal 3 - P8.2 XGBoost Training
cd c:\repo\operador-day-trade-win
# Implementar src/ml/dataset_loader_ati8.py
# Implementar src/ml/model_trainer_ati8.py
# Copiar codigo del guide SUBTASK_8_2_START.md
```

### Moment 0:30 - Checkpoint 1 (VALIDAR INICIO)

```bash
# Terminal 1 - P4.4
pytest tests/performance/test_websocket_load.py::TestWebSocketLoadPerformance::test_100_concurrent_connections -v

# Terminal 2 - P5.2
pytest tests/unit/test_ati2_auth_endpoints.py::TestAuthEndpoints::test_login_success -v

# Terminal 3 - P8.2
python src/ml/train_xgboost_ati8.py  # Primera ejecucion
```

### Moment 1:00 - Checkpoint 2 (MITAD COMPLETO)

```bash
# Terminal 1 - P4.4 FULL TEST
pytest tests/performance/test_websocket_load.py -v

# Terminal 2 - P5.2 FULL TEST
pytest tests/unit/test_ati2_auth_endpoints.py -v

# Terminal 3 - P8.2 MONITORING
# Grid search debe estar en progreso
# Ver outputs de F1 scores
```

### Moment 1:30 - Checkpoint 3 (P4.4 y P5.2 TERMINADOS)

```bash
# P4.4 + P5.2 completos en este punto
# P8.2 debe estar en "Modelo final" phase

# Recolectar resultados
ls -la TEST_RESULTS_4_4.json
pytest tests/unit/test_ati2_auth_endpoints.py -v --tb=short
```

### Moment 2:00 - Checkpoint 4 (P8.2 TERMINADO)

```bash
# Terminal 3 - Validar modelo
python -c "import pickle; m = pickle.load(open('models/xgboost_model_ati8.pkl', 'rb')); print('✅ Modelo cargado:', type(m))"

# Tests finales
pytest tests/unit/test_ati8_xgboost_training.py -v
```

### Moment 5:00 - ENTREGA FINAL

```bash
# Consolidar todos los cambios
git add -A
git commit -m "feat: PRIORITY 4.4+5.2+8.2 parallel execution COMPLETE (6/6 + 5/5 + 5/5 AC)"

# Summary
echo "=== PARALLEL EXECUTION SUMMARY ==="
echo "P4.4 (WebSocket Load): 6/6 AC ✅"
echo "P5.2 (OAuth Endpoints): 5/5 AC ✅"
echo "P8.2 (XGBoost Training): 5/5 AC ✅"
echo "==============================="
echo "TOTAL: 16/16 AC PASSED ✅"
```

---

## 🎯 Success Definition

✅ **EXITO PARANELA** =
- [x] P4.4: 6/6 AC PASSED (test_websocket_load.py)
- [x] P5.2: 5/5 AC PASSED (test_ati2_auth_endpoints.py)
- [x] P8.2: 5/5 AC PASSED (test_ati8_xgboost_training.py)
- [x] Total: 16/16 AC ✅
- [x] Tiempo: ~5h (paralelizado)
- [x] Commits: 3 independientes + 1 consolidacion final

---

## 🚨 Troubleshooting

### P4.4 - WebSocket Tests Fallan
```
Causa: ConnectionManager imports incorrectos
Fix: from src.application.websocket_server_ati1 import ConnectionManager
```

### P5.2 - JWT Token Errors
```
Causa: JWT_SECRET no definido
Fix: export JWT_SECRET="dev-secret-key" o usar default
```

### P8.2 - Grid Search Demora
```
Causa: 5-fold CV con 8 params puede ser lento
Fix: Reducir a 3-fold CV para testing, 5-fold en produccion
```

---

## 📈 Metricas de Exito

| Metrica | Target | P4.4 | P5.2 | P8.2 |
|---------|--------|------|------|------|
| **AC Passed** | 100% | 6/6 | 5/5 | 5/5 |
| **Tests Passed** | 100% | 6/6 | 6/6 | 5/5 |
| **Code Quality** | 100% | - | - | - |
| **Tiempo** | <5h | 1.5h | 1.5h | 2h |
| **Commits** | 4 | 1 | 1 | 1 |

---

## 🔄 Proximo Paso

Como de 4.3+5.1+8.1, despues de este ciclo paralelo estar:

1. **Merge** de todas las branches/commits
2. **Integration Testing** de los 3 componentes juntos
3. **Performance Benchmarking** end-to-end
4. Iniciar **SUBTASK 4.5, 5.3, 8.3**

---

## 📚 Referencia Rapida

- **P4.4:** `SUBTASK_4_4_START.md`
- **P5.2:** `SUBTASK_5_2_START.md`
- **P8.2:** `SUBTASK_8_2_START.md`
- **Master:** Este archivo
- **Git:** Commits T1 + T2 + T3 + FINAL

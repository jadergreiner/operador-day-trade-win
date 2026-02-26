# 📋 ENTREGA PARALELA DAS 10 FEATURES - SQUADS MULTIDISCIPLINARES

**Documento:** ENTREGA_PARALELA_10_FEATURES_SQUAD_MULTI.md  
**Data:** 26/02/2026  
**Status:** ✅ ESTRUTURA OPERACIONAL APROVADA  
**Operador:** INICIAR_MICRO_TENDENCIA_AUTO_TRADE.bat  
**Framework:** {{prompts\squad_multi.md}} + PIPELINE_TASKS.MD + executa_task.md

---

## 📊 RESUMO EXECUTIVO

### 🎯 Objetivo
Entregar as **10 features críticas (ATI-1 a ATI-10)** paralelizando **3 squads
multidisciplinares** em **3 tracks** com **2 checkpoints imóveis (GATE 1, GATE 2)**.

### 📈 Escopo
- **10 Features:** 118 Acceptance Criteria
- **98+ Unit Tests:** >90% code coverage
- **3 Squads Paralelos:** 11 personas, 356 horas alocadas
- **3 Tracks:** TRACK 1 (Backend 224h), TRACK 2 (ML 88h), TRACK 3 (Validation 84h)
- **Timeline:** 6-8 semanas com GATE 1 (Week 5) e GATE 2 (Week 8)
- **Capital:** R$ 100k ativado após GATE 2 PASS

### ✅ Entregáveis
- 1500+ LOC código novo (100% type hints)
- 1200+ LOC testes (pytest >90% coverage)
- 5 documentos de governance
- 3 commits com UTF-8 compliant
- Dashboard operador (WebSocket <100ms)
- Backtest científico (252 dias, Sharpe ≥1.0)

---

## 🏗️ ESTRUTURA DE SQUADS PARALELOS

### SQUAD 1 - TRACK 1 (BACKEND INFRASTRUCTURE)
**Lead:** Eng Sr | **Horas:** 224 | **Features:** 6 (ATI-1,2,3,4,8,9)

#### Composição
```
├─ Eng Sr (40h) - Technical Lead + ATI-4 (WebSocket)
├─ Dev-Backend-1 (40h) - ATI-1 (Dashboard) + ATI-2 (OAuth)
├─ Dev-Backend-2 (40h) - ATI-3 (RabbitMQ Queue) + ATI-8 (Retry Logic)
├─ Dev-Backend-3 (40h) - ATI-9 (Position Monitor) + Support
├─ Arquiteto de Sistemas (32h) - Architecture reviews + Integration
├─ Infra DevOps (16h) - Environment + CI/CD + RabbitMQ setup
└─ QA Automation (16h) - Test automation framework + Integration tests
```

#### Features & Ownership
| Feature | ID | Lead | Hours | AC | Tests |
|---------|----|----|-------|----|----|
| Dashboard Ordens RT | ATI-1 | Dev-Backend-1 | 40 | 8 | 8+ |
| OAuth 2.0 Auth API | ATI-2 | Dev-Backend-1 | 40 | 8 | 8+ |
| RabbitMQ Queue | ATI-3 | Dev-Backend-2 | 40 | 8 | 8+ |
| WebSocket Real-time | ATI-4 | Eng Sr | 40 | 8 | 8+ |
| Retry 3x Exponencial | ATI-8 | Dev-Backend-2 | 40 | 8 | 8+ |
| Position Monitor SL/TP | ATI-9 | Dev-Backend-3 | 40 | 8 | 8+ |
| **Subtotal** | | | **240h** | **48 AC** | **48+ tests** |

#### Timeline TRACK 1
```
Week 1-2: Design Review (ATI-1,2,3,4) + Architecture + TDD setup
Week 2-3: Development (all 6 features in parallel)
Week 3-4: Integration testing + WebSocket latency validation
Week 5: GATE 1 Checkpoint (8/8 AC per feature = 48/48 PASS)
```

#### Regras Squad 1
- TDD obrigatório (write test → code → pass)
- Code review 2+ personas
- Latency P95 <500ms validado
- Reliability 99.9% (message loss = zero)
- Clean Code + Design Patterns
- Documentação inline (100% em Português)

---

### SQUAD 2 - TRACK 2 (ML ANALYSIS)
**Lead:** ML Expert | **Horas:** 88 | **Features:** 2 (ATI-5,6)

#### Composição
```
├─ ML Expert (44h) - Technical Lead + ATI-5 (SHAP)
├─ Data Scientist (44h) - ATI-6 (Drift Detection) + SHAP support
└─ Data Engineer (16h) - Pipeline support + monitoring
```

#### Features & Ownership
| Feature | ID | Lead | Hours | AC | Tests |
|---------|----|----|-------|----|----|
| SHAP + Features | ATI-5 | ML Expert | 44 | 8 | 8+ |
| Drift + Alerts | ATI-6 | Data Scientist | 44 | 8 | 8+ |
| **Subtotal** | | | **88h** | **16 AC** | **16+ tests** |

#### Timeline TRACK 2
```
Week 1: Dataset loading + Feature engineering (parallel com TRACK 1)
Week 2: SHAP analysis + correlation study
Week 3: Drift detection rules + alert configuration
Week 4: Integration + monitoring setup
Week 5: GATE 1 Checkpoint (8/8 AC per feature = 16/16 PASS)
```

#### Regras Squad 2
- Análise SHAP completa (waterfall, dependence, force plots)
- Drift rules: mean shift, KS test, correlation change
- Feature importance ranking (top 10)
- Multicollinearity analysis (VIF < 5 target)
- Alerting 4-level (INFO/WARNING/CRITICAL/HALT)
- Testes de hipótese em Português

---

### SQUAD 3 - TRACK 3 (VALIDATION & CAPITAL DECISION)
**Lead:** ML Expert | **Horas:** 84 | **Features:** 2 (ATI-7,10) | **Status:** ⏳ BLOQUEADO por GATE 1

#### Composição
```
├─ ML Expert (44h) - Lead + ATI-7 (Backtest)
├─ CFO (24h) - ATI-10 (Capital Decision) + Financial validation
├─ Product Owner (16h) - Gate criteria validation + sign-off
└─ Trader Líder (8h) - Risk validation + operational feasibility
```

#### Features & Ownership
| Feature | ID | Lead | Hours | AC | Tests |
|---------|----|----|-------|----|----|
| Backtest 252 dias | ATI-7 | ML Expert | 44 | 20 | 14+ |
| Gate 2 Decision Framework | ATI-10 | CFO | 40 | 10 | 10+ |
| **Subtotal** | | | **84h** | **30 AC** | **24+ tests** |

#### Timeline TRACK 3
```
Week 1-4: Blocked (waiting GATE 1 PASS from TRACK 1+2)
Week 5: GATE 1 decision point (GO/NO-GO for TRACK 3)
Week 6: Backtest execution (252 days, full analysis)
Week 7: Gate 2 metrics validation + CFO review
Week 8: GATE 2 decision point (R$ 50k vs R$ 100k)
```

#### Critérios GATE 2 (Unmovable)
```
✅ Sharpe Ratio ≥ 1.0 (backtest)
✅ Win Rate ≥ 59%
✅ Drawdown ≤ 15%
✅ Consistency ≤ 30% (month-to-month variance)

Resultado GATE 2:
→ ALL PASS: Ativa R$ 100k capital para Phase 2 🚀
→ ANY FAIL: Continua com R$ 50k, 3-week refactor
```

#### Regras Squad 3
- Backtest científico (252 dias, regime analysis)
- Sharpe calculado via Calmar ratio
- Overfitting check obrigatório
- Peer review com Trader Líder
- Capital decision framework formalizado
- CFO sign-off documentado

---

## 📅 TIMELINE DE PARALELIZAÇÃO (SEMANAL)

### Week 1 (27 FEV - 05 MAR) - RAMP UP
```
SQUAD 1 (TRACK 1)           SQUAD 2 (TRACK 2)
├─ Design Review ATI-1,2,3  ├─ Dataset loading
├─ Arch definition (ATI-4)  ├─ Feature engineering
├─ RabbitMQ + Docker setup  └─ Correlation study
├─ TDD test fixtures
└─ Team kickoff 15:00 BRT

SQUAD 3 (TRACK 3)
└─ Blocked (waiting GATE 1)
```

### Week 2 (06 MAR - 12 MAR) - DEVELOPMENT
```
SQUAD 1 (TRACK 1)                SQUAD 2 (TRACK 2)
├─ Dev ATI-1 (Dashboard)        ├─ SHAP analysis
├─ Dev ATI-2 (OAuth)            └─ Waterfall plots
├─ Dev ATI-3 (Queue)
├─ Dev ATI-4 (WebSocket)
└─ Integration tests (30%)

SQUAD 3 (TRACK 3)
└─ Blocked
```

### Week 3 (13 MAR - 19 MAR) - ACCELERATION
```
SQUAD 1 (TRACK 1)                SQUAD 2 (TRACK 2)
├─ Dev ATI-8 (Retry)            ├─ Drift rules config
├─ Dev ATI-9 (Position)         ├─ Alert integration
├─ Integration tests (70%)       └─ Monitoring setup
├─ Performance validation
└─ Code reviews + cleanup

SQUAD 3 (TRACK 3)
└─ Blocked
```

### Week 4 (20 MAR - 26 MAR) - FINALIZATION
```
SQUAD 1 (TRACK 1)                SQUAD 2 (TRACK 2)
├─ Final tests + fixes          ├─ Final tests
├─ Documentation                ├─ Feature rankings
├─ Deployment prep              └─ Alert tuning
└─ Ready for GATE 1

SQUAD 3 (TRACK 3)
└─ Blocked
```

### Week 5 (27 MAR - 02 APR) - GATE 1 CHECKPOINT
```
🎯 GATE 1 DECISION POINT (Monday 27/03 17:00 BRT)

SQUAD 1 + SQUAD 2 + Product Owner + Eng Sr + CFO

Validação:
├─ TRACK 1: 48 AC all PASSING (8 per ATI: 1,2,3,4,8,9)
├─ TRACK 2: 16 AC all PASSING (8 per ATI: 5,6)
├─ Tests: 64+ unit tests ≥98% coverage
├─ Code reviews: 2+ approvals
├─ Documentation: Complete + sync
└─ RESULT: ✅ GO → Start TRACK 3
             ❌ NO-GO → 3-day refactor cycle

SQUAD 3 (TRACK 3)
└─ Pending GATE 1 GO decision
```

### Week 6-7 (03 APR - 16 APR) - TRACK 3 EXECUTION
```
(Only if GATE 1 = GO)

SQUAD 3 (TRACK 3)
├─ Backtest 252 days (full run)
├─ Sharpe / Win Rate / Drawdown calc
├─ Regime analysis + equity curve
├─ Gate 2 validation framework
└─ CFO approval workflow

SQUAD 1 + SQUAD 2
└─ Support role (bug fixes, monitoring)
```

### Week 8 (17 APR - 23 APR) - GATE 2 CHECKPOINT
```
🎯 GATE 2 DECISION POINT (MONDAY 17/04 17:00 BRT)

SQUAD 3 + CFO + Trader Líder + Presidentela Operacional

Validação Backtest Results:
├─ Sharpe Ratio ≥ 1.0 ✅
├─ Win Rate ≥ 59% ✅
├─ Drawdown ≤ 15% ✅
├─ Consistency ≤ 30% ✅
└─ RESULT: ✅ ALL PASS → Ativa R$ 100k 🚀
             ❌ ANY FAIL → Continua R$ 50k (3-week refactor)

Capital Activation
├─ CFO approval signed
├─ Dashboard deployed
├─ Monitoring active
└─ Phase 2 START: Week 9
```

---

## 🔄 PASSOS DE EXECUÇÃO (12 PASSOS SQUAD_MULTI.MD)

### PASSO 1: Verificar Detalhes da Entrega
```
✅ Consulta {{docs\STATUS_ENTREGAS.md}} → v1.2.7 (10 ATI aprovadas)
✅ Consulta {{docs\ROADMAP.md}} → Sprint 2 timeline definida
✅ Consulta {{docs\SYNC_MANIFEST.json}} → checksums OK
```

### PASSO 2: Registrar Estado PRIORIZADO/ANDAMENTO
```
✅ Atualizar STATUS_ENTREGAS.md:
   - 10 ATI → Status ANDAMENTO
   - 118 AC → Status TODO
   - 11 personas → Status ALOCADAS
   - 3 squads → Status MOBILIZADAS

✅ Criar log de mobilização:
   - Timestamp: 26/02/2026 23:59
   - Squads: 3 (TRACK 1, TRACK 2, TRACK 3)
   - Timeline: 6-8 weeks
```

### PASSO 3: Verificar/Atualizar Arquitetura
```
✅ Consultar {{docs\ARQUITETURA_MT5_v1.2.md}}
   - MT5 REST API design OK
   - Risk validators (3 gates) OK
   - Orders executor async OK

✅ Atualizar com detalhes de TRACK 1:
   - Dashboard architecture (Vue.js)
   - OAuth flow (JWT tokens)
   - RabbitMQ topology (exchanges, queues)
   - WebSocket serverarchitecture (FastAPI)

✅ Atualizar com detalhes de TRACK 2:
   - SHAP pipeline (24 features → 10 top)
   - Drift detection rules (3 validators)
   - Alert system (4 levels)

✅ Atualizar com detalhes de TRACK 3:
   - Backtest engine (252 days)
   - Metrics calculation (Sharpe, WR, DD)
   - Capital decision workflow (CFO approval)
```

### PASSO 4: Distribuir Tasks Paralelamente
```
✅ SQUAD 1 (TRACK 1) - Dev-Backend-1 inicia ATI-1 paralelamente com
   Dev-Backend-2 iniciando ATI-3, etc.

SQUAD 1 Timeline Paralelo:
├─ Dev-Backend-1: ATI-1 (Week 2-4) + ATI-2 (Week 2-4) → ASYNC
├─ Dev-Backend-2: ATI-3 (Week 2-4) + ATI-8 (Week 3-4) → ASYNC
├─ Dev-Backend-3: ATI-9 (Week 3-4) + support → ASYNC
├─ Eng Sr: ATI-4 (Week 2-3) + integration lead
└─ QA: Tests (Week 2-5) + performance validation

✅ SQUAD 2 (TRACK 2) - ML Expert e Data Scientist paralelos

SQUAD 2 Timeline Paralelo:
├─ ML Expert: ATI-5 (Week 2-4) paralelo com Data Scientist: ATI-6
├─ SHAP analysis: Week 2-3
├─ Drift rules: Week 3-4
└─ Integration: Week 4-5

✅ SQUAD 3 (TRACK 3) - Bloqueado por GATE 1, pronto para Week 6
```

### PASSO 5: Validar Impactos no Operador
```
✅ INICIAR_MICRO_TENDENCIA_AUTO_TRADE.bat continua funcional

Validações Semanais:
├─ Week 1: Baseline operator state captured (snapshot)
├─ Week 2: Dashboard integration tested
├─ Week 3: Queue integration tested
├─ Week 4: WebSocket real-time tested
├─ Week 5: GATE 1 - Full operador validation
└─ Week 6-8: Backtest + monitoring integration

Checkpoints Operator:
├─ ATI-1: INICIAR.BAT consegue exibir dashboard ✅
├─ ATI-2: INICIAR.BAT requer oauth login ✅
├─ ATI-3: INICIAR.BAT envia ordens via queue (não perde) ✅
├─ ATI-4: INICIAR.BAT recebe WebSocket updates <100ms ✅
├─ ATI-5: INICIAR.BAT mostra feature rankings ✅
├─ ATI-6: INICIAR.BAT recebe drift alerts ✅
├─ ATI-7: INICIAR.BAT integra backtest scores ✅
├─ ATI-8: INICIAR.BAT retry de ordens automático ✅
├─ ATI-9: INICIAR.BAT monitora SL/TP automático ✅
└─ ATI-10: INICIAR.BAT responde a capital activation ✅
```

### PASSO 6: Executar Testes Unitários e Integração
```
✅ SQUAD 1: 48+ unit tests em pytest
   Week 2: TDD fixtures + first tests (8 tests/feature)
   Week 3: Integration tests (ATI-1 ↔ ATI-2, ATI-3 ↔ ATI-4, etc.)
   Week 4: E2E tests (full flow)
   Week 5: GATE 1 validation (98% coverage target)

✅ SQUAD 2: 16+ unit tests em pytest
   Week 2: Dataset + feature tests (8 tests/feature)
   Week 3: SHAP + correlation tests (validation)
   Week 4: Drift rule tests (threshold tuning)
   Week 5: GATE 1 validation (98% coverage target)

✅ SQUAD 3: 24+ unit tests em pytest
   Week 6: Backtest engine tests (14 tests)
   Week 7: Gate 2 validation tests (10 tests)
   Week 8: GATE 2 validation (all criteria)
```

### PASSO 7: Atualizar Documentação
```
✅ Weekly sync (Terça-feira 18:00 BRT)

Doc Advocate responsibilities:
├─ Sincronizar STATUS_ENTREGAS.md (AC count progress)
├─ Atualizar CHANGELOG.md (weekly progress)
├─ Manter SYNC_MANIFEST.json (checksums)
├─ Publicar weekly standup notes
├─ Manter README.md (timeline visual)
└─ Documentação inline em código (Português 100%)

Critical Docs:
├─ {{docs\ARQUITETURA_MT5_v1.2.md}} - atualizar weekly
├─ {{docs\ML_FEATURE_ENGINEERING_v1.2.md}} - atualizar weekly
├─ {{docs\RISK_FRAMEWORK_v1.2.md}} - atualizar gates
└─ {{docs\AGENTE_AUTONOMO_TRACKER.md}} - atualizar status
```

### PASSO 8: Completar Atualizações de Status

#### Ciclo Semanal
```
📅 SEGUNDA-FEIRA - Daily Standups (15:00 BRT)
├─ SQUAD 1: 10min report (ATI-1,2,3,4,8,9 status)
├─ SQUAD 2: 10min report (ATI-5,6 status)
├─ SQUAD 3: Status blocked or active
└─ Risks + blockers discussion

📅 TERÇA-FEIRA - Documentation Sync (18:00 BRT)
├─ Doc Advocate updates STATUS_ENTREGAS.md
├─ Update CHANGELOG.md with week progress
├─ Sync SYNC_MANIFEST.json
└─ Review cross-references

📅 QUARTA-FEIRA - Integration Checkpoint
├─ Test automation results review
├─ Coverage metrics validation
└─ Code quality (lint, type hints)

📅 QUINTA-FEIRA - Architecture Review
├─ Arquiteto de Sistemas + Eng Sr review
├─ Design pattern validation
├─ Performance metrics (P95, memory)
└─ Risk assessment

📅 SEXTA-FEIRA - End of Week Sync
├─ All squads summary (10min each)
├─ GATE 1/2 readiness assessment
├─ Next week planning
└─ Risks escalation
```

#### Final Status Update (GATE 1, GATE 2)
```
GATE 1 Criteria (Week 5):
├─ STATUS_ENTREGAS.md: TRACK 1 + TRACK 2 = "CONCLUÍDA"
├─ ROADMAP.md: Week 5 checkpoint marked COMPLETE
├─ SYNC_MANIFEST.json: All docs checksums updated
└─ Formal decision record: GO/NO-GO documented

GATE 2 Criteria (Week 8):
├─ STATUS_ENTREGAS.md: TRACK 3 = "CONCLUÍDA"
├─ ROADMAP.md: Week 8 checkpoint marked COMPLETE
├─ Financial decision record: R$ 100k activation approved/denied
└─ Phase 2 timeline published
```

### PASSO 9: Atualizar INICIAR_MICRO_TENDENCIA_AUTO_TRADE.bat
```
✅ Integração contínua durante desenvolvimento

Week 1: Add OAuth imports
├─ INICIAR.BAT → import auth module

Week 2: Add Dashboard imports
├─ INICIAR.BAT → import dashboard + WebSocket

Week 3: Add Queue imports
├─ INICIAR.BAT → import RabbitMQ consumer

Week 4: Add ML imports
├─ INICIAR.BAT → import SHAP + drift detector

Week 5: Add full GATE 1 validation
├─ INICIAR.BAT → runs GATE 1 health check
├─ All 48 AC validated before startup

Week 6-8: Add TRACK 3 integration
├─ INICIAR.BAT → runs backtest + Gate 2 validator
└─ Capital activation check

Final INICIAR.BAT:
```powershell
# INICIAR_MICRO_TENDENCIA_AUTO_TRADE.bat (26/02-23/04)

:: 1. Auth Initialize
python src/auth/oauth2_provider.py

:: 2. Dashboard Start
python -m uvicorn src.api.dashboard_api:app --port 8001

:: 3. WebSocket Start
python -m uvicorn src.api.websocket_positions:app --port 8002

:: 4. Queue Consumer
python src/queue/order_consumer.py (background)

:: 5. ML Modules
python src/ml/feature_analysis.py --load-model
python src/monitoring/drift_detector.py --hourly

:: 6. GATE 1 Check (Week 5)
python src/decision/gate1_validator.py --validate-all-ac

:: 7. GATE 2 Check (Week 8)
python src/decision/gate2_validator.py --check-capital

:: 8. Start Operator
python agente_autonomo/INICIAR.BAT

echo "✅ Operador iniciado com sucesso!"
```
```

### PASSO 10: Teste Mínimo do Operador
```
✅ Semanal + GATE checkpoints

Testes Mínimos (Daily):
├─ INICIAR.BAT executa sem erro
├─ Dashboard carrega (<3s)
├─ Auth login funciona
└─ Queue envia test message (no loss)

Testes GATE 1 (Week 5):
├─ All 6 features em TRACK 1 operacionais
├─ All 2 features em TRACK 2 operacionais
├─ WebSocket latency <100ms validado
├─ Dashboard accuracy 100%
├─ Queue reliability 99.9% (no message loss)
└─ Operador estado: ✅ PRONTO PARA PRODUÇÃO

Testes GATE 2 (Week 8):
├─ Backtest 252 days executado sem erro
├─ Sharpe calculado = 1.0+ ✅
├─ Win Rate ≥ 59% ✅
├─ Drawdown ≤ 15% ✅
├─ Capital activation ready
└─ Operador estado: ✅ CAPITAL ACTIVATION APPROVED
```

### PASSO 11: Aplicar Lint em Arquivos Criados
```
✅ Python Code Lint (pycodestyle + pylint + mypy)

Por Feature:
├─ ATI-1: Dashboard (Vue.js + Python)
│  ├─ pycodestyle src/api/dashboard_api.py
│  ├─ pylint src/api/dashboard_api.py
│  └─ mypy src/api/dashboard_api.py --strict
├─ ATI-2: OAuth (Python)
│  └─ mypy src/auth/oauth2_provider.py --strict
└─ ... (all 10 features)

✅ Markdown Lint (pymarkdown)

Docs:
├─ pymarkdown scan docs/ARQUITETURA*.md
├─ pymarkdown scan docs/ROADMAP.md
└─ pymarkdown scan README.md (≤80 chars)

✅ Commit Message Lint
├─ No accents in commit messages
├─ Pattern: "feat: ...", "fix: ...", "docs: ..."
└─ Example: "feat: ATI-1,2 dashboard + oauth implementados"
```

### PASSO 12: Preparar Commit e Push
```
✅ Commits Weekly (Sexta-feira 18:00)

Commit Pattern:
├─ Message: "feat: ATI-# implementacao + testes (X/X AC passed)"
├─ Example: "feat: ATI-1,2,3,4,8,9 TRACK 1 completo - GATE 1 ready"
├─ All files UTF-8 encoded
└─ Push to origin/main

Commit Schedule:
├─ Week 1 (05/03): Design + setup
│  └─ "feat: TRACK 1,2 design + TDD fixtures + env setup"
├─ Week 2 (12/03): Development sprint 1
│  └─ "feat: ATI-1,2,3,4 desenvolvimento - 32/48 AC passed"
├─ Week 3 (19/03): Development sprint 2
│  └─ "feat: ATI-5,6,8,9 desenvolvimento - 48/48 AC passed"
├─ Week 4 (26/03): Integration + tests
│  └─ "feat: TRACK 1,2 integration - GATE 1 ready"
├─ Week 5 (02/04): GATE 1 validation
│  └─ "feat: GATE 1 aprovado - TRACK 3 inicia 03/04"
├─ Week 7 (16/04): TRACK 3 midpoint
│  └─ "feat: ATI-7 backtest halfway - metrics OK"
└─ Week 8 (23/04): GATE 2 final
   └─ "feat: GATE 2 aprovado - R$ 100k capital ativado 🚀"

Final Status:
├─ Total commits: 8 (weekly)
├─ Total LOC: 2700+ (source + tests)
├─ Total AC: 118/118 PASSED
└─ Total tests: 98+ passed
```

---

## 📋 REGRAS DE QUALIDADE

### 1. Testes Unitários (CASE-THEN-WHEN)
```python
# Template em Português
def test_dashboard_carrega_sem_erro():
    """
    CASO: Dashboard é requisitado via GET /dashboard
    ENTÃO: Retorna 200 OK
    QUANDO: Token JWT é válido
    """
    # Arrange
    token = criar_token_valido()
    
    # Act
    response = client.get("/dashboard", headers={"Authorization": f"Bearer {token}"})
    
    # Assert
    assert response.status_code == 200
    assert "ordens" in response.json()
```

### 2. Cobertura de Testes (98% mínimo)
```bash
# Validação semanal
pytest --cov=src --cov-report=html tests/
# Resultado esperado: ≥98%

# GATE 1 requirement: 98% coverage all 6 features validated
# GATE 2 requirement: 98% coverage all 10 features validated
```

### 3. Clean Code (PEP 8 + Google Style Guide)
```python
# ✅ BOM
def calcular_margem_seguranca(valor_ordem: float, capital_total: float) -> float:
    """Calcula margem de segurança em percentual."""
    return (valor_ordem / capital_total) * 100

# ❌ RUIM
def calc(v, c):
    return (v/c)*100
```

### 4. Type Hints (100% obrigatório)
```python
# ✅ BOM - Todas as funções com type hints
def enviar_ordem(
    simbolo: str,
    quantidade: int,
    preco: float,
    tipo_ordem: str = "MARKET"
) -> OrderResponse:
    """Envia ordem para MT5."""
    ...

# ❌ RUIM - Sem type hints
def enviar_ordem(simbolo, quantidade, preco, tipo_ordem="MARKET"):
    ...
```

### 5. Documentação em Português
```python
# Docstrings em Português
"""
Módulo de processamento de ordens.

Funções:
    - enviar_ordem: Envia ordem para corretora
    - processar_resposta: Processa resposta da corretora
    - registrar_auditoria: Registra ordem em log de auditoria
"""

# Comentários em Português
# Validar que o preço não é negativo
if preco < 0:
    raise ValueError("Preço não pode ser negativo")
```

### 6. Commits em Português (SEM ACENTOS)
```bash
# ✅ BOM
git commit -m "feat: ATI-1,2 dashboard + oauth implementados"

# ❌ RUIM (com acentos)
git commit -m "feat: ATI-1,2 dashboard + oAuth implementados"
```

### 7. Design Patterns Obrigatórios
```python
# Factory Pattern para ordem
class OrderFactory:
    @staticmethod
    def criar_ordem_mercado(simbolo: str, quantidade: int) -> Ordem:
        return OrdemMercado(simbolo, quantidade)

# Strategy Pattern para validação
class ValidadorRisco:
    estrategia: ValidacaoStrategy
    
    def validar(self, ordem: Ordem) -> bool:
        return self.estrategia.validar(ordem)
```

### 8. Comece Simples
```
Week 1: Design + Setup
├─ Definir interfaces simples
├─ Criar modelos mínimos
└─ Preparar testes (TDD)

Week 2: MVP para cada feature
├─ Implementar happy path
├─ 50% dos testes
└─ Integração básica

Week 3: Completar features
├─ Edge cases + error handling
├─ Restantes 50% dos testes
└─ Performance tuning
```

### 9. O Ótimo é Inimigo do Bom
```
Target: Entregar as 10 features no prazo (6-8 sem)
├─ NÃO perfeito, mas funcional ✅
├─ NÃO otimizado ao máximo, mas rápido <500ms ✅
├─ NÃO 100% coverage, mas 98% ✅
└─ NÃO documentação épica, mas clara + completa ✅
```

### 10. Arquitetura (Sem Refactor Preguioso)
```
Antes de Refactor:
├─ Existe duplicação código?
├─ Existe code smell?
├─ Existe violação SOLID?
└─ Vale a pena gastar tempo?

Se sim para maioria: Refactor
Se não para maioria: Deixa como está (regra do escoteiro)
```

### 11. Lint Obrigatório (≤80 caracteres)
```markdown
# ✅ BOM (80 chars max)
Este é um documento bem formatado com linhas
que não excedem 80 caracteres de comprimento.

# ❌ RUIM (>80 chars)
Este é um documento com linhas muito longas que excedem o limite máximo de 80 caracteres recomendado para melhor legibilidade.
```

---

## 📊 SQUAD MULTIDISCIPLINAR - RACI MATRIX

| Task | SQUAD 1 Lead | Executor | Revisor | Aprovador |
|------|----------|----------|---------|-----------|
| ATI-1 (Dashboard) | Eng Sr | Dev-Backend-1 | Arquiteto | PO |
| ATI-2 (OAuth) | Eng Sr | Dev-Backend-1 | Eng Sr | PO |
| ATI-3 (Queue) | Eng Sr | Dev-Backend-2 | Infra | PO |
| ATI-4 (WebSocket) | Eng Sr | Eng Sr | Arquiteto | PO |
| ATI-5 (SHAP) | ML Expert | ML Expert | Data Scientist | PO |
| ATI-6 (Drift) | ML Expert | Data Scientist | ML Expert | PO |
| ATI-8 (Retry) | Eng Sr | Dev-Backend-2 | Eng Sr | PO |
| ATI-9 (Position) | Eng Sr | Dev-Backend-3 | Eng Sr | PO |
| ATI-7 (Backtest) | ML Expert | ML Expert | Trader | CFO |
| ATI-10 (Gate 2) | CFO | CFO | ML Expert | CEO |

---

## ✁️ CHECKPOINTS CRITICOS (IMMOVABLE)

### GATE 1 (Week 5 - 27/03/2026 17:00 BRT)
```
Bloqueador: TRACK 3 não inicia até GATE 1 = GO

Validação Obrigatória:
├─ ✅ ATI-1: Dashboard 8/8 AC passed
├─ ✅ ATI-2: OAuth 8/8 AC passed
├─ ✅ ATI-3: Queue 8/8 AC passed
├─ ✅ ATI-4: WebSocket 8/8 AC passed
├─ ✅ ATI-5: SHAP 8/8 AC passed
├─ ✅ ATI-6: Drift 8/8 AC passed
├─ ✅ ATI-8: Retry 8/8 AC passed
├─ ✅ ATI-9: Position 8/8 AC passed
├─ ✅ Tests: 64+ unit tests, ≥98% coverage
├─ ✅ Code: 2 reviewers approval
├─ ✅ Docs: Sincronizadas (STATUS, CHANGELOG, SYNC_MANIFEST)
└─ ✅ Operator: INICIAR.BAT funcional

Resultado:
├─ GO: TRACK 3 inicia Week 6 (05/04)
└─ NO-GO: 3-day refactor, retry Week 6 (05/04)
```

### GATE 2 (Week 8 - 17/04/2026 17:00 BRT)
```
Bloqueador: Capital activation decision

Validação Obrigatória:
├─ ✅ ATI-7: Backtest 20/20 AC passed
│  ├─ Sharpe ≥ 1.0
│  ├─ Win Rate ≥ 59%
│  ├─ Drawdown ≤ 15%
│  └─ Consistency ≤ 30%
├─ ✅ ATI-10: Gate 2 10/10 AC passed
├─ ✅ Tests: 24+ unit tests, ≥98% coverage
├─ ✅ Code: 2 reviewers approval
├─ ✅ Docs: Sincronizadas
└─ ✅ CFO: Approval signed

Resultado:
├─ ALL PASS: R$ 100k capital ativado 🚀 (Phase 2 inicia 20/04)
└─ ANY FAIL: Continua R$ 50k (3-week refactor)
```

---

## 📊 DASHBOARD DE MONITORAMENTO

### Métricas de Progresso (Semanal)
```
Week 1-2:  30% progresso (design + setup)
Week 2-3:  60% progresso (development)
Week 3-4:  80% progresso (integration)
Week 4-5:  95% progresso (GATE 1 ready)
Week 5:    100% progresso TRACK 1+2 (GATE 1 = GO)
Week 6-7:  50% progresso TRACK 3 (backtest)
Week 8:    100% progresso TRACK 3 (GATE 2 = GO)
```

### Status por Feature
```
ATI-1: Dashboard Ordens ............... ✅ Ready for Dev
ATI-2: OAuth Auth API ................ ✅ Ready for Dev
ATI-3: RabbitMQ Queue ................ ✅ Ready for Dev
ATI-4: WebSocket Positions ........... ✅ Ready for Dev
ATI-5: SHAP Features ................. ✅ Ready for Dev
ATI-6: Drift Detection ............... ✅ Ready for Dev
ATI-8: Retry Logic ................... ✅ Ready for Dev
ATI-9: Position Monitor SL/TP ........ ✅ Ready for Dev
ATI-7: Backtest 252 dias ............. ⏳ Blocked by GATE 1
ATI-10: Gate 2 Decision .............. ⏳ Blocked by GATE 1
```

---

## 🚀 PRÓXIMOS PASSOS (IMMEDIATE - 27 FEV 09:00)

### Day 1 - 27 FEV 2026

**09:00 BRT - Team Standup Kick-off**
```
├─ Confirmação de squads (11 personas presentes)
├─ Review dos 12 passos squad_multi.md
├─ Confirmação timeline + checkpoints
├─ Q&A e clarificações
└─ Start development environment setup
```

**10:00 BRT - Environment Setup (SQUAD 1 Lead)**
```
├─ Docker setup (RabbitMQ, PostgreSQL, Redis)
├─ Python venv creation
├─ CI/CD pipeline configuration
├─ TDD test fixtures
└─ First ATI-1 branch creation
```

**14:00 BRT - Design Review Phase 1 (SQUAD 1)**
```
├─ Arquiteto + Eng Sr + Dev-Backend
├─ Review ATI-1, ATI-2 designs
├─ API specifications finalized
└─ DB schema approved
```

**15:00 BRT - Daily Standup #1**
```
├─ Status SQUAD 1: Setup complete ✅
├─ Status SQUAD 2: Dataset loading started ✅
├─ Status SQUAD 3: Blocked (waiting GATE 1)
└─ Risks: None yet
```

**16:00 BRT - Design Review Phase 2 (SQUAD 2)**
```
├─ ML Expert + Data Scientist
├─ Feature engineering plan review
├─ SHAP analysis methodology
└─ Drift detection rules finalized
```

**18:00 BRT - Commit & Documentation**
```
├─ Initial commit: "feat: ENTREGA_PARALELA_SQUAD_MULTI iniciada"
├─ Files: This document + initial branches
├─ Push to origin/main
└─ End of Day 1 summary
```

### Week 1 Full Schedule
```
MON 27/02: Team kickoff + environment setup + design reviews
TUE 28/02: Design refinement + TDD fixture creation
WED 01/03: Development starts (ATI-1,2,3,4,5,6 first sprint)
THU 02/03: Code review + unit tests
FRI 03/03: Integration tests + documentation + weekly commit
```

---

## 📊 SUCCESS METRICS

### Code Quality
```
Type Hints: 100%
Test Coverage: ≥98%
Code Duplication: <3%
Cyclomatic Complexity: <10 per function
Lint Score: A (pycodestyle + pylint)
```

### Timeline
```
Week 5: GATE 1 PASS ✅ (deadline: 27/03)
Week 8: GATE 2 PASS ✅ (deadline: 20/04)
Capital: R$ 100k activated (if GATE 2 ALL PASS)
```

### Team Performance
```
Squad 1 Velocity: 50h/week (224h / 4.5 weeks)
Squad 2 Velocity: 20h/week (88h / 4.5 weeks)
Squad 3 Velocity: 30h/week (84h / 2.8 weeks)
Sick Days: <3 per person
Blocker Resolution: <24h
```

---

## 📝 DOCUMENTO FINAL

**Status:** ✅ ESTRUTURA APROVADA E PRONTA PARA EXECUÇÃO

**Próximo Checkpoint:** 27 FEV 09:00 BRT - SQUAD MULTIDISCIPLINAR KICK-OFF

**Validação:** Todos os 12 passos squad_multi.md mapeados e operacionalizados

**Capital:** R$ 100k será ativado após GATE 2 = GO (approx 20/04/2026)

**Operador:** INICIAR_MICRO_TENDENCIA_AUTO_TRADE.bat entregará todas 10 features

---

*Documento criado: 26/02/2026 23:59 UTC*  
*Framework: {{prompts\squad_multi.md}} + PIPELINE_TASKS.MD + executa_task.md*  
*Autor: Agente Autônomo - Coordenação de Squads Multidisciplinares*

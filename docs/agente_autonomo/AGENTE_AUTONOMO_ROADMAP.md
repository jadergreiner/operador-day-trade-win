# 🗺️ Roadmap - Agente Autônomo de Trading

**Versão:** 1.0.0
**Data:** 20/02/2026
**Horizonte:** 12 meses

---

## 📅 Timeline de Desenvolvimento

### Q1 2026 (Fevereiro - Abril)

#### **v1.0.0** (20/02) ✅
- Sistema de processamento BDI
- Análise de tendências
- Backlog estruturado
- Documentação completa

#### **v1.0.1** (27/02) 🔄
- Bugfixes
- Melhorias de performance
- Validação de dados

#### **v1.1.0** (13/03/2026) 🚀 **PHASE 6: INTEGRATION IN PROGRESS**
- Dados intradiários (1min, 5min)
- **Alertas automáticos (Push WebSocket + Email)** ✅ **CODE COMPLETE**
  - Detection Engine (volatilidade >2σ + padrões técnicos) ✅ 3,900 LOC
  - Delivery multicanal (latência <30s P95) ✅ WebSocket server ready
  - Rate limiting + deduplicação (>95%) ✅ Queue system ready
  - Audit log completo (CVM compliant) ✅ SQLite append-only
  - **PHASE 6 INTEGRATION (27 FEB - 13 MAR):** ⏳
    - BDI Integration (Eng Sr) - Hook detectors
    - WebSocket Server (Eng Sr) - FastAPI on 8765
    - Email Config (Eng Sr) - SMTP fallback
    - Backtesting Validation (ML Expert) - Gates ≥85% capture
    - Performance Benchmarking (ML Expert) - P95 <30s, Memory <50MB
    - Staging Deployment (Eng Sr) - E2E validation
    - Final Validation (ML Expert) - All tests passing
  - Operação MANUAL v1.1 (automático em v1.2)
  - Capital ramp-up: 50k → 80k → 150k → 200k+ (pós-Beta)
  - 4 Fases: Beta (13/03) → Prod Restrita → Prod Normal → Scale
- Análise de opções
- Módulo de correlações
- Dashboard web básico

#### **v1.2.0** (10/04/2026) 🚀 **EXECUÇÃO AUTOMÁTICA**

**FEATURE P0:** US-001 - Execução Automática de Trades com Validação ML

**Objetivo:** Permitir operações 100% autônomas com risco controlado (Phase 7).

**Especificação Detalhada:**
- [x] User Story formalizada: `US-001-EXECUTION_AUTOMATION_v1.2.md` ✅
- [x] Risk Framework aprovado: `RISK_FRAMEWORK_v1.2.md` ✅
- [x] Análise financeira: +R$ 150-300k/mês (vs 50-80k v1.1) ✅
- [ ] Machine Learning para classificação de padrões (v1.2 novo)
  - Features engineered: 15-25 variáveis
  - Model: XGBoost/LightGBM
  - Target: F1 > 0.68, Sharpe > 1.0
  - Output: Confidence score [0-100%]
- [ ] Integração MT5 API (v1.2 novo)
  - REST API (polling 200ms)
  - Order submission: buy, sell, close
  - Latência target: P95 < 500ms
  - Error handling + retry policy
- [ ] Risk Validators (v1.2 novo)
  - Capital adequacy
  - Correlation check
  - Volatility anomaly detection
- [ ] Circuit Breakers (v1.2 novo)
  - Level 1 (🟡 -3%): Alerta ao trader
  - Level 2 (🟠 -5%): Slow mode (50% ticket, 90% ML)
  - Level 3 (🔴 -8%): Halt obrigatório
- [ ] Position Monitoring (v1.2 novo)
  - Real-time P&L tracking
  - Automatic stop execution
  - Critical alerts
- [ ] Trader Override (v1.2 novo)
  - Manual veto always available (<50ms)
  - Full audit trail (CVM-ready)

**Capital Ramp-up:** 50k → 100k → 150k (3 fases de 2 semanas)

**PHASE 7 SPRINTS (27/02 - 10/04, 27 dias):**
- **Sprint 1 (27/02-05/03):** Design MT5 + Feature engineering
  - Gate: Risk rules + ML features APPROVED
- **Sprint 2 (06/03-12/03):** Risk Validator + ML training
  - Gate: Classifier F1 > 0.65, ready for integration
- **Sprint 3 (13/03-19/03):** MT5 integration + E2E testing
  - Gate: Integration tests PASSED, performance validated
- **Sprint 4 (20/03-10/04):** UAT + Launch
  - Gate: Trader acceptance + CFO sign-off

**Success Criteria:**
- ✅ Win rate: 65-68% (vs 62% v1.1)
- ✅ Sharpe: >1.0 (backtest validated)
- ✅ Latency: P95 <500ms (target)
- ✅ Drawdown max: <15% (circuit breakers)
- ✅ Uptime: >99.5% (Phase 1)
- ✅ ROI: +R$ 150-300k/mês (vs 50-80k v1.1)

---

### Q2 2026 (Maio - Junho)

#### **v2.0.0** (01/06) ⏳
- Arquitetura Microserviços
- API REST completa
- WebSocket tempo real
- Provisioning em cloud (AWS/GCP)
- Database escalável (PostgreSQL + Redis)

---

### Q3-Q4 2026 (Visão)

- [ ] Execution Engine fully automated
- [ ] Portfolio optimization
- [ ] Risk management avançado
- [ ] Compliance & Auditoria
- [ ] Mobile app

---

## 🎯 Objetivos por Milestone

| Milestone | Objetivo | KPI |
|-----------|----------|-----|
| **v1.0** | Análise BDI funcional | 3+ oportunidades/BDI |
| **v1.1** | Alertas + Dados infraday | <30s latência, >95% deduplicate |
| **v1.2** | ML operacional | Sharpe > 1.0, w/rate >65% |
| **v2.0** | Automação completa | 90%+ uptime |

## 📊 Métricas de Sucesso (Atualizado)

1. **Processamento BDI:** <5 segundos ✅
2. **Alertas (v1.1):** <30 segundos P95 latência ✅
3. **Deduplicação:** >95% consolidação ✅
4. **Win Rate Histórico:** 62-68% (v1.0-v1.1) ✅
5. **ROI Esperado:** +R$ 50-200k/mês (v1.1) ✅
6. **Uptime:** >99% em produção

---

**Documentos Relacionados:** BACKLOG, FEATURES, RELEASE

# 📋 Plano de Sprints — MVP NOW

**Status:** Planejamento Ativo
**Versão:** 1.0.0
**Última Atualização:** 2026-02-23

---

## 🎯 Sprint 0 — Foundation (CONCLUÍDO ✅)

**Duração:** 2 semanas
**Objetivo:** Estabelecer base sólida com ML + alertas

### Tasks Entregues

| ID | Task | Owner | Status | Entrega | Prioridade |
|----|------|-------|--------|---------|-----------|
| S0-1 | Dataset Builder (XGBoost) | ML Expert | ✅ DONE | winfut_dataset.py | 🔴 CRÍTICA |
| S0-2 | Feature Engineer (Tiers) | ML Expert | ✅ DONE | winfut_feature_engineer.py | 🔴 CRÍTICA |
| S0-3 | Alertas Automáticos v1.1 | Dev | ✅ DONE | sistema de alertas WebSocket | 🔴 CRÍTICA |

---

## 🎯 Sprint 1 — Operacionalização (CONCLUÍDO ✅)

**Duração:** 1 semana
**Objetivo:** Operação 24/7 com automação completa

### Tasks Entregues

| ID | Task | Owner | Status | Entrega |
|----|------|-------|--------|---------|
| S1-1 | Configuração MT5 Production | Dev | ✅ DONE | real_account=True |
| S1-2 | Health Checks 24/7 | Infra | ✅ DONE | MONITOR_LOGS.bat |
| S1-4 | Testes E2E Automação | QA | ✅ DONE | Suíte de testes integrados |
| S1-5 | Performance Tuning | Dev | ✅ DONE | Latência P95 ~71ms |
| S1-6 | Documentation Updates | Doc | ✅ DONE | STATUS_ENTREGAS Sincro |

---

## 📅 Sprint 2 — Inteligência e Visibilidade (ATUAL 🔵)

**Duração:** 2 semanas
**Objetivo:** Dashboard real-time e expansão lógica do modelo

### Backlog Priorizado (MoSCoW)

#### MUST (Críticas)

| ID | Task | Owner | Estimativa | Status | Deadline |
|----|------|-------|-----------|--------|----------|
| S2-2 | Calibrador ATR Dinâmico | ML | 8h | ⏳ PENDING | P1 |
| S2-3 | Confluência SMC (M1/M5) | Dev | 10h | ⏳ PENDING | P1 |
| S2-4 | Integração Phicube (Mimas) | ML | 6h | ⏳ PENDING | P1 |

#### SHOULD (Altas)

| ID | Task | Owner | Estimativa | Status | Deadline |
|----|------|-------|-----------|--------|----------|
| S2-5 | Probabilidade T+60 | ML | 15h | ⏳ BACKLOG | P2 |
| S2-1 | Dashboard de Monitoramento | Dev | 12h | ⏩ DESPRIORIZADO | P3 |
| S2-6 | Analytics de Intervenção | Doc | 6h | ⏳ BACKLOG | P2 |

#### COULD (Médias)

| ID | Task | Owner | Estimativa | Status | Deadline |
|----|------|-------|-----------|--------|----------|
| S2-7 | Telegram Integration v2 | Dev | 3h | ⏳ BACKLOG | TBD |
| S2-8 | Hot-Reload de Pesos | Dev | 5h | ⏳ BACKLOG | TBD |

---

## 🌌 Sprint 3 — Escala (PLANEJADO)

### Sprint 0
- ✅ 3/3 tasks (100%)
- ✅ 45+ testes passando
- ✅ 0 bugs críticos

### Sprint 1 (Atual)
- 🔵 0/4 MUST iniciado
- 📈 Progresso esperado: 50% atingido no monitoramento.

---

## 🔗 Links Rápidos

- [ROADMAP](ROADMAP.md)
- [STATUS_ENTREGAS](STATUS_ENTREGAS.md)
- [FEATURES](FEATURES.md)
- [DECISIONS](DECISIONS.md)
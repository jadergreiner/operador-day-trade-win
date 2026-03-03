# 📊 Diagrama de Dependências - BACKLOG v4.0

## Visualização de Bloqueadores & Próximos Passos

```
┏━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓
┃                   HOJE: Escolha um caminho                       ┃
┗━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┛

                         ┌─────────────────┐
                         │   COMEÇAR HO    │
                         │     (HOJE!)     │
                         └────────┬────────┘
                                  │
                   ┌──────────────┼──────────────┐
                   │              │              │
              P0-1 REST        P1-1 ML        Outro?
              (160h)         (Features)
               ENG SR         ML EXPERT
               │                │
               │                │
          (Paralelo: NÃO precisa esperar um pelo outro)
```

---

## 🎯 Ciclo 1: Bloqueadores P0 (CRÍTICOS)

```
┌───────────────────────────────────────────────────────────────┐
│                      FASE 1: P0 GATE 1                         │
│                    (ENG SR 160h + ML 40h)                      │
└───────────────────────────────────────────────────────────────┘

                           ┌──────────┐
                           │  P0-1    │
                           │ API REST │
                           │  MT5     │
                           │ 160h/3d  │
                           │  ENG SR  │
                           └────┬─────┘
                                │
                    ┌───────────┴───────────┐
                    │                       │
                    ✓ 14 endpoints OK       ✓ 8/8 AC PASS
                    ✓ Retry 3× OK          ✓ Load test 500u
                    ✓ Error handling OK     ✓ P95 <500ms
                    │                       │
          ┌─────────┴──────────────────────┴────────┐
          │                                          │
          ▼                                          ▼
  ┌─────────────────┐                    ┌──────────────────┐
  │ GATE 1: GO? ✓   │                    │ P1-1: Features   │
  │ CTO + PO        │                    │ SHAP Analysis    │
  │ Decisão Min 5d  │                    │ Drift Detect     │
  └────────┬────────┘                    │ 40h / ML Expert  │
           │                             └──────┬───────────┘
         PASSA?                                  │
           │                                   PASSA?
           │                                     │
         SIM→ Desbloqueia tudo                SIM→ Alimenta P0-2
           │  (P0-2, P1-2-6, P4)                 │
           │                                     │
           └──────────────┬──────────────────────┘
                          │
                        ✓ GATE 1 PASS
```

---

## 🎯 Ciclo 2: Validação ML (GATE 2 = Capital Scale Decision)

```
┌───────────────────────────────────────────────────────────────┐
│          FASE 2: P0-2 + P1-2 to P1-6 (Paralelo)               │
│                   ML-004 Backtest (88h)                        │
└───────────────────────────────────────────────────────────────┘

Pré-Requisito: P0-1 ✅ (endpoints disponíveis)

P0-2 (Bloqueador P4):                  P1-2 a P1-6 (Paralelo):
━━━━━━━━━━━━━━━━━━━━━━                 ━━━━━━━━━━━━━━━━━━━━━
│                                       │
│ Backtest 252 dias                     ├─ P1-2: Dashboard
│ 88h / ML Expert + Data                ├─ P1-3: OAuth
│ ✓ Sharpe ≥ 1.0                        ├─ P1-4: RabbitMQ
│ ✓ Win Rate ≥ 59%                      ├─ P1-5: WebSocket
│ ✓ Max DD < 15%                        ├─ P1-6: Position Monitor
│ ✓ σ mensal < 30%                      │
│                                       Cada uma: 40-50h
│ Relatório PDF (20p)                   Interdependências baixas
│ Visualizações                         Podem rodar paralelo 100%
│                                       │
└──────┬───────────────────────────────┴─┘
       │
       ▼ Após P1-x + P0-2 ✅
  ┌────────────────────┐
  │ GATE 2: GO Fase 2? │
  │ CFO + Board        │
  │ ★ CRÍTICA ★        │
  └────────┬───────────┘
           │
    Sharpe≥1.0?
    Win≥59%?
           │
    ┌──SIM─┴──NÃO──┐
    │         │
    ▼         ▼
  GO      NO-GO
  │       (replan ML)
  │
✓ Ativa
  R$ 100k
  Fase 2
```

---

## 🎯 Ciclo 3: Produção (P4 = Sequencial)

```
┌───────────────────────────────────────────────────────────────┐
│         FASE 3: P4 (GO-LIVE) - SEQUENCIALMENTE                │
│  Pré-Requisito: GATE 2 PASS (P0-2 ✅ + Sharpe+Win OK)         │
└───────────────────────────────────────────────────────────────┘

    ┌──────────────────┐
    │     P4-1:        │
    │   STAGING        │
    │ 20-30h / Eng Sr  │
    │                  │
    │  ✓ 8 Azure OK    │
    │  ✓ 25+ tests     │
    │  ✓ Load 500u     │
    │  ✓ 0 critical    │
    │                  │
    │  Trader testa    │
    │  signals offline │
    └────────┬─────────┘
             │
           ✓ AC 8/8
             │
           GATE 4.1? ✓
           (CTO + QA)
             │
             ▼
    ┌──────────────────┐
    │     P4-2:        │
    │   UAT APPROVAL   │
    │  10-15h / Team   │
    │                  │
    │  ✓ Trader APROVA │
    │  ✓ CIO security  │
    │  ✓ CFO capital R$ │
    │  ✓ 0 blockers    │
    │                  │
    │  3 sign-offs     │
    │  obrigatórios    │
    └────────┬─────────┘
             │
           ✓ AC 8/8
             │
           GATE 4.2? ✓
         (3 pessoas)
             │
             ▼
    ┌──────────────────┐
    │     P4-3:        │
    │   GO-LIVE PROD   │
    │   5-10h / DevOps │
    │                  │
    │  ✓ Deploy prod   │
    │  ✓ Capital active│
    │  ✓ Trades reais  │
    │  ✓ P&L track OK  │
    │                  │
    │  ★ ATIVA ★       │
    │  R$ 50k live     │
    └────────┬─────────┘
             │
           ✓ AC 8/8
             │
           ✓✓✓ LIVE ✓✓✓
```

---

## 📊 Matriz de Dependências (Texto)

```
Tarefa      │ Pré-Requisito   │ Desbloqueia          │ Esforço │ Status
────────────┼─────────────────┼──────────────────────┼─────────┼────────
P0-1 API    │ Nenhum          │ P0-2,P1-2-6,P4-1    │ 160h    │ 🟡 Ready
P0-2 BT     │ P0-1 ✅         │ P4-1                │  88h    │ 🟡 Ready
P1-1 ML     │ Nenhum (paralelo)│ P0-2 (dados)       │  40h    │ 🟡 Ready
P1-2 Dash   │ P0-1 ✅         │ Nenhum              │  40h    │ 🟡 Ready
P1-3 OAuth  │ P0-1 ✅         │ Nenhum              │  40h    │ 🟡 Ready
P1-4 RMQ    │ P0-1 ✅         │ Nenhum              │  50h    │ 🟡 Ready
P1-5 WS     │ P0-1 ✅         │ Nenhum              │  45h    │ 🟡 Ready
P1-6 Posmon │ P0-1 ✅         │ Nenhum              │  40h    │ 🟡 Ready
P4-1 Staging│ P0-2 GATE 2 ✅  │ P4-2                │  25h    │ 🔴 Blocked
P4-2 UAT    │ P4-1 ✅         │ P4-3                │  15h    │ 🔴 Blocked
P4-3 Live   │ P4-2 ✅         │ Capital ativo       │  10h    │ 🔴 Blocked
P2-1 Detect │ GATE 2 PASS ✅  │ Nenhum              │  60h    │ 🔴 Blocked
P3-1 Prodcfg│ GATE 2 PASS ✅  │ Nenhum              │  30h    │ 🔴 Blocked
```

---

## 🚀 Quick Start: Qual é meu próximo passo?

### Se você é: **PRODUCT OWNER**
```
Seu caminho:
  1. Alloc 3 devs para P0-1 (ENG SR tech lead)
  2. Schedule GATE 1 check (5 dias)
  3. Prepare GATE 2 board (CFO + você + CTO)
  4. Clarify priorização P1-x paralelo
```

### Se você é: **ENG SR**
```
Seu caminho:
  1. Leia P0-1 COMPLETAMENTE (14 endpoints)
  2. Comece architecture FastAPI (2 horas design)
  3. Setup skeleton de 3 endpoints (1 hour)
  4. Coordene com ML Expert (dados para features)
```

### Se você é: **ML EXPERT**
```
Seu caminho:
  1. Comece P1-1 HO JE (não espera P0-1)
  2. Extrai 24 features (2-3 horas)
  3. SHAP analysis (1-2 horas)
  4. Drift detection setup (1-2 horas)
  5. Prepara dados para P0-2 backtest
```

### Se você é: **CFO / HEAD FINANÇAS**
```
Seu caminho:
  1. Leia P0-2 GATE 2 (backtest criteria)
  2. Prepare aprovação capital (R$ 50k)
  3. Coordene board para GATE 2 (após P0-2)
  4. Defina circuit breakers limite (-5%, -8%)
```

---

## 📈 Timeline Realista (SEM datas fixas)

```
Semana 1 (P0-1):
  Mon-Weds: Design + skeleton P0-1
  Thu: Código endpoints (8/14)
  Fri: Testes + revisão
  ▶ GATE 1 CHECK (fim semana 1 ou 2)

Semana 2 (P0-2 + P1-x):
  Após P0-1: P0-2 backtest (88h = 2-3 semanas)
  Paralelo: P1-1 a P1-6 desenvolvimento
  ▶ GATE 2 DECISION (fim semana 3-4)

Semana 3-4 (P4 Sequencial):
  Após GATE 2: P4-1 staging (25h = 3 dias)
  Depois P4-1: P4-2 UAT (15h = 2 dias)
  Depois P4-2: P4-3 Go-Live (10h = 1 dia)
  ▶ ✓✓✓ LIVE ✓✓✓
```

**IMPORTANTE:** Isso é estimativa. Sem datas fixas = sem pânico se atrasar.
Foco em AC (acceptance criteria), não em data.

---

## ⚡ Regla de Ouro (Muito Importante!)

```
NÃO COMEÇAR P(N+1) antes de P(N) ter:
  ✅ Todos os AC testáveis completos
  ✅ Todos os critérios de qualidade OK
  ✅ Revisão código/produto aprovada
  ✅ GATE passado (se houver)

Exceções (Paralelo OK):
  ✓ P0-1 + P1-1 (zero dependência)
  ✓ P1-2 a P1-6 entre si (todos dependem P0-1 só)
  ✓ P2-x (após GATE 2)
  ✓ P3-x (após Phase 2 estável)

Sequencial OBRIGATÓRIO:
  P4-1 → P4-2 → P4-3 (produção rígida)
  P0-1 → P0-2 (data validation)
```

---

**Arquivo:** BACKLOG Dependency Map  
**Versão:** 4.0  
**Data:** 03/03/2026  
**Status:** ✅ Atual


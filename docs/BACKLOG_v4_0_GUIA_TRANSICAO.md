# 📌 GUIA DE TRANSIÇÃO - BACKLOG v4.0

## O Que Mudou?

### ❌ ANTES (v3.0 - Timeline-Driven)
```
## SPRINT 1 (27/02 - 05/03)
    P0-1: ENG-003 API REST
    P0-2: ML-004 Backtest
    ...
    Timeline: 27/02 → 10/04
    Datas FIXAS em 100+ seções
```

**Problema:** Calendário rígido criava fake urgência. Tarefas aparecem bloqueadas por DATA, não por funcionalidade.

---

### ✅ AGORA (v4.0 - Task-Independent)
```
## P0 - CRÍTICAS (Bloqueadores Lógicos, não temporais)
    P0-1: ENG-003 API REST
      └─ Bloqueador para: [P0-2, P1-2 a P1-6, P4-1]
    
    P0-2: ML-004 Backtest Validation
      └─ GATE 2 Decisão (lógica, não data)

## EXECUÇÃO
    Paralelo: P0-1 + P1-1 começam AGORA (não "27/02")
    Sequencial: P4-1 → P4-2 → P4-3 (pré-requisitos, não datas)
```

**Vantagem:** Foco em **dependências reais** (código, AC, gates) não em calendário.

---

## 📋 Como Usar (3 Passos)

### 1️⃣ ESCOLHA SEU PAPEL

```
PO/Eng Sr:  
  → Leia seção P0 (críticas)
  → Decida: começamos P0-1 HO convaje?
  → Sim? Aloque 3 devs
  → Não? Identifique bloqueador

CFO/Head Finanças:
  → Leia P0-2 (GATE 2)
  → Veja: Sharpe ≥ 1.0, Win Rate ≥ 59%, Drawdown < 15%
  → SE PASS → ativa R$ 100k
  → SE FAIL → replanha ML

ML Expert:
  → Acesse P1-1 paralelo (começa AGORA, não espera P0-1)
  → Análise Features + Drift Detection
  → Feedings into P0-2
```

---

### 2️⃣ LEIA O MODELO DE EXECUÇÃO

**Seção "MODELO DE EXECUÇÃO (SEM DATAS)" no BACKLOG**

```
Diagrama ASCII mostra:
  - O que roda em PARALELO (P0-1 + P1-1 simultâneos)
  - O que PRECISA DE dependência (P1-2 aguarda P0-1)
  - O que é SEQUENCIAL (P4: staging → UAT → live)
```

---

### 3️⃣ EXECUTE CONFORME PRIORIDADE

| Prioridade | Começa | Pré-Requi sitos | Status |
|-----------|--------|-----------------|--------|
| **P0-1** | HO JE | Nenhum | 🟡 Pronto |
| **P1-1** | HO JE | Nenhum (paralelo P0-1) | 🟡 Pronto |
| **P0-2** | Após P0-1 ✅ | P0-1 completo | 🟡 Aguardando |
| **P1-2 a P1-6** | Após P0-1 ✅ | P0-1 completo | 🟡 Aguardando |
| **P4-1** | Após GATE 2 ✅ | P0-2 passando em GATE | 🟡 Aguardando |
| **P4-2** | Após P4-1 ✅ | P4-1 AC 8/8 completo | 🟡 Aguardando |
| **P4-3** | Após P4-2 ✅ | P4-2 3 sign-offs | 🟡 Aguardando |

---

## 🔴 GATES (Decisões Lógicas, não Calendário)

Cada GATE é uma **decisão binária** (GO/NO-GO):

### GATE 1: P0-1 Pronto?
- Critério: 8/8 AC PASS + latência P95 <500ms
- Quem: CTO + PO
- Ação: GO → desbloqueia P0-2 + P1-2a P1-6

### GATE 2: Backtest OK? ★ CRÍTICA ★
- Critério: Sharpe ≥1.0 + Win Rate ≥59% + Drawdown <15%
- Quem: CFO + Board
- Ação: GO → ativa R$ 100k | NO→ replan ML

### GATE 4.1: Staging Pronto?
- Critério: 8/8 AC + tests 25+ + load 500 users OK
- Quem: CTO + QA
- Ação: GO → desbloqueia P4-2 UAT

### GATE 4.2: Trader Aprova?
- Critério: 3 sign-offs (Trader accuracy + CIO security + CFO capital)
- Quem: Trader + CIO + CFO
- Ação: GO → desbloqueia P4-3 live

---

## 🚀 PRÓXIMOS PASSOS (COMECE HOJE)

### Se você é Eng Sr:
```
1. Leia P0-1 completamente (14 endpoints, 8 AC)
2. Valide timeline realista (160h com 3 devs = 2-3 semanas)
3. Comece design arquitetura FastAPI
4. Paralelize P1-1 com ML Expert (análise features)
```

### Se você é ML Expert:
```
1. Comece P1-1 HO convaje (não espera P0-1)
2. Extrair features + SHAP analysis + drift detection
3. Prepare dados para P0-2 backtest
4. Coordene com P0-2 bloqueador (seu código → validação)
```

### Se você é CFO:
```
1. Leia P0-2 GATE 2 critérios
2. Prepare aprovação capital (R$ 50k assinado)
3. Coordene board pré-backtest (agendar sessão GATE 2)
4. Defina limite risco (max drawdown?)
```

---

## 📞 Q&A (Dúvidas Frequentes)

**P: Vi "P2" e "P3". Quando começam?**
A: NÃO COMEÇAM ATÉ GATE 2 PASS (P0-2 ✅). Primeiro finalize P0 + P1 + P4 produção.

**P: Preciso sair 10/04. Como sabe se vai dar tempo?**
A: Sem datas fixas agora. Depende de: P0-1 quanto tempo leva? P0-2 backtest passar? Não prometa timbau 10/04. Diga: "P0-1 + P0-2 + P4 em X semanas" (realista).

**P: E se P0-1 atrasa?**
A: Tudo atrasa. P1-2a P1-6 esperam. P0-2 espera. P4 espera. SEM datas = sem surpresa, só realidade.

**P: P0-1 e P1-1 rodam paralelo?**
A: SIM. Não dependem uma da outra. Mas P1-2 a P1-6 dependem de P0-1.

**P: Quando é GATE 2?**
A: Quando P0-2 ✅. Se demorar, GATE 2 atrasa. Mas QUAL a data? Não sabe. Depende de P0-1 primeiro.

---

## 🔄 ALTERAÇÃO DO FLUXO GIT

**Branch Development:**
```bash
# ANTES: branch nomeado por data/sprint
git checkout -b sprint-1-27fev  ❌

# AGORA: branch nomeado por tarefa
git checkout -b feature/P0-1-api-rest-mt5  ✅
git checkout -b feature/P1-1-ml-features-analysis  ✅
git checkout -b feature/P1-2-dashboard-realtime  ✅
```

---

## ✅ Checklist: Você Entendeu?

- [ ] Li seção P0 completamente (P0-1 + P0-2)
- [ ] Entendi: P0-1 bloqueador central para tudo
- [ ] Entendi: GATE 2 decide capital (Sharpe+Win+Drawdown)
- [ ] Entendi: P4-1, 4-2, 4-3 sequencial (staging → UAT → live)
- [ ] Entendi: P1-1 começa paralelo (não espera P0-1)
- [ ] Entendi: SEM DATAS, apenas pré-requisitos lógicos
- [ ] Escolhi meu papel (PO/Eng/ML/CFO)
- [ ] Identifiquei minha tarefa P(x) para começar

---

## 📚 Links Documentação Rel acionada

1. **[ARCHITECTURE.md](ARCHITECTURE.md)** - Arquitetura 7 camadas (leitura obrigatória)
2. **[CODING_STANDARDS.md](CODING_STANDARDS.md)** - Padrões Python (SOLID + DDD)
3. **[REGRAS_NEGOCIO.md](REGRAS_NEGOCIO.md)** - 6 regras críticas P0
4. **[README.md](README.md)** - Visão geral projeto

---

## 🤝 Contato

- **Dúvida de Primiorização?** → PO
- **Dúvida Técnica P0-1?** → Eng Sr
- **Dúvida ML/Backtest?** → ML Expert  
- **Dúvida Financeira/Capital?** → CFO
- **Bloqueado?** → Escalate imediatamente (não deixa "para depois")

---

**Versão:** 1.0  
**Data:** 03/03/2026  
**Status:** ✅ Válido


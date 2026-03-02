# 🚀 Guia Rápido — Backlog Unificado

**Versão:** 2.0
**Data:** 02/03/2026
**Público:** PO, Squad, Agentes Autônomos

---

## ⚡ Acesso Rápido

| Papel | Ação | Link |
|------|------|------|
| **Product Owner** | Ver todo o backlog | [BACKLOG_UNIFICADO.md](BACKLOG_UNIFICADO.md) |
| **Team Lead** | Ver próxima tarefa | [P0-1 ou P1-1](#próxima-tarefa) |
| **Dev** | Ver critérios aceite | [P0-1 CA](#p0-1-api-rest-mt5) |
| **QA** | Ver testes esperados | [Seção Testes](#testes-necessários) |
| **Executivo** | Ver resumo executivo | [RESUMO_EXECUTIVO_BACKLOG.md](RESUMO_EXECUTIVO_BACKLOG.md) |

---

## 🎯 Próxima Tarefa

### Sprint Atual (Sprint 2):

```
┌─────────────────────────────────────────┐
│  🔴 ATIVA AGORA: P0-1 + P1-1            │
│  (Paralelas - sem dependências)         │
└─────────────────────────────────────────┘

P0-1: ENG-003 - API REST MT5
  Lead: Eng Sr
  Squad: 3 Devs Backend
  Horas: 160h
  CA: 8/8 (especificados)
  Status: 🟢 Pronto pra começar

P1-1: ML-003 - Feature Analysis
  Lead: ML Expert
  Squad: 2 Data Scientists
  Horas: 88h
  CA: 18/18 (especificados)
  Status: 🟢 Pronto pra começar
```

---

## 📋 Estrutura de Prioridades

### P0 — CRÍTICAS (Bloqueadores)
Tarefas que **bloqueiam** outras. Devem ser feitas primeiro.

```
P0-1: ENG-003 API REST MT5 [160h]
  ↓ Desbloqueia
P0-2: ML-004 Backtest 252d [88h]
```

### P1 — IMPORTANTES (Não-Bloqueadores)
Podem rodar **em paralelo** com P0-1. Começam quando P0-1 atinge
30%.

```
P1-1: ML-003 Features [88h] ← Paralelo com P0-1
P1-2: Dashboard [40h] ← Começa quando P0-1 ✅
P1-3: OAuth [40h] ← Começa quando P0-1 ✅
P1-4: RabbitMQ [40h] ← Começa quando P0-1 ✅
P1-5: WebSocket [40h] ← Começa quando P0-1 ✅
P1-6: Positions [32h] ← Começa quando P0-1 ✅
```

### P2 — FUTURO (Sprint 2+)
Começam **após GATE 2** aprovado.

```
P2-1: Retry Logic [32h]
P2-2: Capital Framework [40h]
P2-3: Performance [40h]
P2-4: Staging [32h]
```

### P3 — BACKLOG (Sprint 3+)
**Não começar agora.** Futuro.

```
P3-1: Fontes Externas
P3-2: Analytics
P3-3: Mobile App
```

---

## 🏃 Como Solicitar Próxima Tarefa

### Ao GPT (Agente Autônomo):

```
Pergunta:
"Qual é a próxima tarefa prioritária?"

Resposta:
- Verifica BACKLOG_UNIFICADO.md
- Retorna tarefa P0/P1 não-iniciada
- Mostra dependências
- Indica responsável
```

### Ao PO (Manual):

1. Abrir `docs/BACKLOG_UNIFICADO.md`
2. Procurar seção `## ✅ P0 - CRÍTICAS`
3. Encontrar tarefa com `Status: 🟢 Pronto ...`
4. Atribuir ao responsável

---

## 📊 Esforço por Prioridade

| Prioridade | Tarefas | Horas | % Esforço |
|-----------|---------|-------|----------|
| P0 | 2 | 248h | 37% |
| P1 | 6 | 272h | 41% |
| P2 | 4 | 144h | 22% |
| P3 | 3 | TBD | — |
| **TOTAL** | **15** | **664h+** | **100%** |

---

## 🎯 Quando Cada Tarefa Começa

```
DAY 1 (Sprint 2 Kickoff)
  P0-1: ENG-003 ──────┐
  P1-1: ML-003 ──────┘ (Paralelos, sem dependências)

WHEN P0-1 is ~30% done
  P1-2: Dashboard ─┐
  P1-3: OAuth ─────┤
  P1-4: RabbitMQ ──┤ (Paralelos, aguardam P0-1)
  P1-5: WebSocket ─┤
  P1-6: Positions ─┘

WHEN P0-1 is DONE
  P0-2: ML-004 ──────┐ (Sequential, aguarda P0-1)
       (GATE 1 check)

WHEN P0-2 is DONE
  P2-1 through P2-4 ─ (Sequencial após GATE 2)
       (GATE 2 check)

NEVER (Sprint 3+)
  P3-1 through P3-3 ─ (Futuro - não comece)
```

---

## 📈 Progresso esperado

### Semana 1 (Sprint 2 Start)
- P0-1: 0 → 30% (ENG-003)
- P1-1: 0 → 100% (ML-003 independent)

### Semana 2
- P0-1: 30 → 70% (ENG-003)
- P1-2 through P1-6: 0 → 50%

### Semana 3
- P0-1: 70 → 100% ✅ (GATE 1)
- P0-2: 0 → 50% (ML-004)
- P1-2 through P1-6: 50 → 100%

### Semana 4+
- P0-2: 50 → 100% ✅ (GATE 2)
- P2-1 through P2-4: 0 → 100% (if GO)

---

## 🔑 Critérios-Chave

### Para P0-1 Completo:
- ✅ 8/8 Critérios Aceite passando
- ✅ 35+ testes passando
- ✅ Latência P95 < 500ms
- ✅ Código revisado (2+ reviewers)

### Para P0-2 Completo:
- ✅ 20/20 CA passando
- ✅ Sharpe ≥ 1.0
- ✅ Win rate ≥ 59%
- ✅ Drawdown < 15%
- ✅ Consistência < 30% std

### Para P1-x Completo:
- ✅ CA especificado passando
- ✅ Testes passando
- ✅ Código revisado
- ✅ Documentação OK

---

## ⚠️ Bloqueadores Críticos

| Se Bloqueado | Impacto | Escalate Para |
|-------------|---------|---------------|
| P0-1 | Tudo parado | CTO |
| ML metrics (P0-2) | Gate 2 fail | Head Data |
| Gate criteria | Capital decision | CFO + Board |
| Capital decision | Fase 2 não ativa | Board |

---

## 📚 Documentação Completa

### Arquivo Principal:
- **[docs/BACKLOG_UNIFICADO.md](BACKLOG_UNIFICADO.md)** ← Fonte de Verdade

### Documentos de Suporte:
- [docs/RESUMO_EXECUTIVO_BACKLOG.md](RESUMO_EXECUTIVO_BACKLOG.md) — PO overview
- [docs/VERIFICACAO_CONSOLIDACAO_BACKLOG.md](VERIFICACAO_CONSOLIDACAO_BACKLOG.md) — Validação
- [docs/BACKLOG.md](BACKLOG.md) — Índice

### Documentos Originais (Ainda Válidos):
- `SPRINT2_TAREFAS_PRIORIZADAS.md` — Details
- `SPRINT2_ACTIVIDADES_PRIORIDADE.md` — Details
- `PLANO_DE_SPRINTS_MVP_NOW.md` — Planning

---

## 🚀 Checklist Daily

### Para Squad Lead:
- [ ] Leu BACKLOG_UNIFICADO.md secão "Próxima Tarefa"?
- [ ] Squad confirmado vs alocação esperada?
- [ ] Dependências claras?
- [ ] Bloqueadores identificados?

### Para PO:
- [ ] P0 progresso on-track?
- [ ] P1 paralelos started?
- [ ] Testes resultados?
- [ ] Escalação necessária?

### Para Agente Autônomo:
- [ ] Consultou BACKLOG_UNIFICADO.md?
- [ ] Próxima tarefa P0/P1 identificada?
- [ ] Dependências validadas?
- [ ] Pronto para executar?

---

## 📞 Contatos

| Questão | Owner | Escalate |
|---------|-------|----------|
| Próxima tarefa? | Leia BACKLOG_UNIFICADO.md | PO |
| Bloqueador P0-1? | Eng Sr | CTO |
| Bloqueador ML? | ML Expert | Head Data |
| Gate criteria? | PO | CFO/Board |
| Documentação? | Tech Writer | PO |

---

## ✨ Diferenciais do Novo Sistema

```
Antes:
  - 7 arquivos diferentes
  - Priorização inconsistente
  - Difícil navegar
  - Duplicação
  - Confusão

Depois:
  ✅ 1 arquivo centralizado
  ✅ Priorização clara (P0-P3)
  ✅ Navegação fácil
  ✅ Sem duplicação
  ✅ Consistente
  ✅ 82 CA testáveis
  ✅ 100+ testes definidos
  ✅ Squad alocado
  ✅ Gates definidos
```

---

## 🎊 Status Geral

```
✅ Backlog: Consolidado
✅ Priorizado: Claro (P0-P3)
✅ Documentado: 3.500+ linhas
✅ Squad: Alocado (11 personas)
✅ Gates: Definidos (2)
✅ Testes: 100+ especificados
✅ Escalação: Mapeada

🟢 PRONTO PARA EXECUÇÃO
```

---

**Versão:** 2.0
**Data:** 02/03/2026
**Proprietário:** Product Owner (GitHub Copilot)
**Última Revisão:** VERIFICACAO_CONSOLIDACAO_BACKLOG.md

# Backlog — Operador Day Trade WIN
⭐ **CORE DO PRODUTO**: Todas as tarefas neste backlog convergem para entregar dois operadores principais:
- [INICIAR_DIARIOS.bat](../INICIAR_DIARIOS.bat) - Inicializa sistemas
- [INICIAR_MICRO_TENDENCIA_AUTO_TRADE.bat](../INICIAR_MICRO_TENDENCIA_AUTO_TRADE.bat) - Engine de trading automático
> ⚠️ **ARQUIVO CONSOLIDADO:**
>
> Este arquivo foi consolidado em:
>
> **→ [docs/BACKLOG_UNIFICADO.md](BACKLOG_UNIFICADO.md) ←**
>
> **Esta é a única fonte de verdade para todo o backlog do
> projeto.**

---

## 📚 Padrão de Scripts

**Todos os scripts Python devem estar em `scripts/`**

Ver [CODING_STANDARDS.md - Padrão de Localização](CODING_STANDARDS.md#11-scripts---padrão-de-localização-obrigatório-) para diretrizes completas.

---

## 🎯 Como Usar

Para solicitar a próxima atividade prioritária, consulte:

**[📋 BACKLOG UNIFICADO](BACKLOG_UNIFICADO.md)**

---

## ✅ O que mudou?

O backlog foi unificado de múltiplos arquivos espalhados em um
único documento:

**Arquivos Consolidados:**
- ✅ SPRINT2_TAREFAS_PRIORIZADAS.md
- ✅ SPRINT2_ACTIVIDADES_PRIORIDADE.md
- ✅ 10_ATIVIDADES_CRITICAS_SPRINT2.md
- ✅ SPRINT2_PRIORITY_ACTIVITIES.md
- ✅ PLANO_DE_SPRINTS_MVP_NOW.md
- ✅ PROXIMAS_ACOES_24FEV.md
- ✅ DESENVOLVIMENTO_SPRINT1_TASKS_PRIORIZADAS.md

---

## 📊 Estrutura do Backlog Unificado

```
P0 - CRÍTICAS (Bloqueadores)
├─ P0-1: ENG-003 API REST MT5 [Bloqueador Central]
└─ P0-2: ML-004 Backtest 252 dias [Aguarda P0-1]

P1 - IMPORTANTES (Não-Bloqueadores)
├─ P1-1: ML-003 Feature Analysis
├─ P1-2: Dashboard Ordens Real-Time
├─ P1-3: OAuth 2.0 Auth
├─ P1-4: RabbitMQ Queue
├─ P1-5: WebSocket Positions
└─ P1-6: Position Monitoring

P2 - FUTURO (Sprint 2+)
├─ P2-1: Retry Logic
├─ P2-2: Capital Framework
├─ P2-3: Performance Benchmarking
└─ P2-4: Staging Deployment

P3 - BACKLOG (Sprint 3+)
├─ P3-1: Fontes Externas
├─ P3-2: Analytics Avançadas
└─ P3-3: Mobile App
```

---

## 🚀 Como Usar

**Para solicitar a próxima atividade:**

```
"Qual é a próxima tarefa prioritária?"
```

O agente consultará `docs/BACKLOG_UNIFICADO.md` e retornará a
próxima atividade não-iniciada mais importante.

---

**Última Atualização:** 02/03/2026
**Proprietário:** Product Owner (GitHub Copilot)
**Versão:** 2.0

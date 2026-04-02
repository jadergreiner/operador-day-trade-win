# Documentação - Índice Geral

**Projeto:** Operador Day Trade WIN
**Organização:** Estrutura hierárquica por tipo/feature

> Documento histórico/read-only. O estado atual do projeto está em
> `docs/PLANO_MULTI_AGENTES.md`, `docs/BACKLOG.md` e `docs/STATUS_ENTREGAS.md`.

⚠️ **CORE DO PRODUTO:** Veja `INICIAR_DIARIOS.bat` e
`INICIAR_MICRO_TENDENCIA_AUTO_TRADE.bat` na **raiz do projeto**.
Esses são os dois entry points principais ao redor dos quais o sistema foi
construído.

✅ **STATUS CRÍTICO (05/03/2026 20:00 - IMMEDIATE ACTIONS 48H EM PROGRESSO):**

- ✅ P50 (Pessimism Detection): **ATIVO** - sistema em estado seguro
- ✅ **P1-CORE (Order Execution):** etapas 1-4 completas + go-live aprovado
  - Etapa 1 (05/03): OrderQueue + async enqueueing ✅
  - Etapa 2 (06/03): MT5Executor + real execution ✅
  - Etapa 3 (07/03): Position Monitor + WebSocket broadcast ✅
    [ver ADR-012](ADRs.md#adr-012-real-time-position-monitoring-com-websocket-p1-core-etapa-3)
  - Etapa 4 (08/03): Load testing (100+ ord/min) + cleanup scheduler ✅
    [ver P52](BACKLOG_UNIFICADO.md#p52-etapa-4-load-testing-100ordensmin--cleanup-scheduler)
- ✅ **GATE 2:** backtest validation aprovada
  (captura 94,48%, FP 7,43%, win 62%)
- ✅ **TASK 3:** model deployment testing completo (16/16 testes)
- 🚀 **GO-LIVE DECISION:** Phase 1 Beta Launch em 10/03 15:00
  (R$ 50k de capital)
- 📍 Próxima ação: Task 4 - Operational Readiness → Task 5 Daily Closure

---

## 📚 Estrutura de Documentação

```text
docs/
├── README.md (este arquivo)
├── ARCHITECTURE.md
├── BACKLOG_UNIFICADO.md
├── CODING_STANDARDS.md
├── CONTRIBUTING.md
├── DATA_MODELS.md
├── STATUS_ENTREGAS.md
│
└── features/
    └── intraday-learner/
        ├── README.md (START HERE)
        ├── APRENDIZADO_TRANSPARENTE_GUIA.md
        ├── IMPLEMENTACAO_INTRADAY_LEARNER.md
        ├── PROTECAO_MT5_CLEAR_GUIA.md
        └── STATUS_INTRADAY_LEARNER_FINAL.md
```

---

## 🎯 Documentação por Público

### Para Operador 👨‍💼

**Comece aqui:**
[docs/features/intraday-learner/README.md](features/intraday-learner/README.md)

⚠️ **IMPORTANTE - TERMINAL ISOLATION (NOVO):**
Antes de executar qualquer trade, leia
[QUICK_START.md#-configuração-de-isolamento](QUICK_START.md#-configuração-de-isolamento-de-terminal-importante).

- Configure `MT5_TERMINAL_PATH` para proteger contra brokers errados
- O sistema bloqueará automaticamente conexões a FBS/XP/Zero/IC/Ativa/Rica
- Sem isolamento correto, o go-live é impossível ❌

Então leia:

1. [Aprendizado Transparente](features/intraday-learner/APRENDIZADO_TRANSPARENTE_GUIA.md)
2. [Proteção MT5 CLEAR](features/intraday-learner/PROTECAO_MT5_CLEAR_GUIA.md)

### Para Developer 👨‍💻

**Comece aqui:** [ARCHITECTURE.md](ARCHITECTURE.md)

Então leia feature docs:

1. [Implementação IntraDayLearner](features/intraday-learner/IMPLEMENTACAO_INTRADAY_LEARNER.md)
2. [Status e Roadmap](features/intraday-learner/STATUS_INTRADAY_LEARNER_FINAL.md)

### Para PM/Stakeholder 📊

**Comece aqui:** [STATUS_ENTREGAS.md](STATUS_ENTREGAS.md)

Então consulte:

1. [BACKLOG_UNIFICADO.md](BACKLOG_UNIFICADO.md) - Tarefas
2. [features/intraday-learner/](features/intraday-learner/) - Status da feature

---

## 📋 Features Documentadas

### AC1: Signal Generation (M5 Pattern Detection)

**Status:** ✅ **PRODUCTION READY** (06/03/2026)
**Linguagem:** Python 3.11 (Clean Architecture)
**Cobertura:** 100% (6 integration tests PASSED - pipeline AC1→AC6)
**Commit:** 29a9353

Geração de sinais de trading em timeframe M5 usando padrões SMC:

- 🟢 **Detectores:** BOS, CHoCH, FVG e IMPULSE
- 🟢 **Scoring:** score SMC `[-3, +3]` consolidado
- 🟢 **Validação:** confluence multi-indicator
  (`RSI 20-80`, `ATR > 0.1`, `Volatility < 200%`)
- 🟢 **Implementação real:** 449 LOC, type hints 100%, `mypy --strict` OK
- 🟢 **Testado:** 6/6 integration tests no pipeline completo
- 📊 **Referência:**
  [`src/domain/signal_generator.py`](../src/domain/signal_generator.py) e
  [`CODING_STANDARDS.md`](CODING_STANDARDS.md)

### AC2: Signal Persistence (Market Context JSON)

**Status:** ✅ **PRODUCTION READY** (05/03/2026)
**Linguagem:** Python 3.11 (SQLite Backend)
**Cobertura:** 100% (8 testes PASSED)
**Integração:** pipeline AC1→AC2→AC3 validado (06/03/2026)

Persistência de sinais AC1 com contexto de mercado serializado em JSON:

- 🟢 **Serialização:** 8 campos de contexto de mercado
  (`RSI`, `ATR`, `BB`, `Volume`, `Spread`, `Trend`, `LastClose`)
- 🟢 **Storage:** SQLite com índices otimizados, `UNIQUE constraints` e `FK`
- 🟢 **Testado:** 8/8 testes de integração
- 📊 **Referência:**
  [`src/application/signal_persistence.py`](../src/application/signal_persistence.py)

### IntraDayLearner

**Localização:** `docs/features/intraday-learner/`
**Status:** ✅ Implementado
**Data:** 03/03/2026

Desenvolvimento de aprendizado em tempo real (intraday) para análise de
padrões HOLD.

- 🟢 **IMPLEMENTAÇÃO:** 3 camadas de proteção MT5 CLEAR
- 🟡 **P33-P36:** próximas fases de integração e dashboard
- 📊 **Impacto esperado:** +1-2% de win rate em 3 semanas

👉 [Ir para IntraDayLearner docs](features/intraday-learner/README.md)

---

## 🔧 Padrão de Documentação

### Regras para Criar Novo Feature Doc

1. Criar pasta em: `docs/features/{feature-name}/`
2. Criar `README.md` como índice
3. Colocar guias específicos:
   - `GUIA_OPERADOR.md` (se aplicável)
   - `IMPLEMENTACAO_TECNICA.md` (se aplicável)
   - `STATUS_ROADMAP.md` (se aplicável)
4. Não deixar .md na raiz de `docs/`

### Exemplo: Feature X

```text
docs/features/feature-x/
├── README.md
├── GUIA_OPERADOR.md
├── IMPLEMENTACAO_TECNICA.md
└── STATUS_ROADMAP.md
```

---

## 📖 Documentação Global

- [AC1_SIGNAL_GENERATION_IMPLEMENTATION.md](AC1_SIGNAL_GENERATION_IMPLEMENTATION.md)
  - Implementação AC1: geração de sinais M5 com padrões SMC
- [AC2_SIGNAL_PERSISTENCE_IMPLEMENTATION.md](AC2_SIGNAL_PERSISTENCE_IMPLEMENTATION.md)
  - Implementação AC2: persistência de sinais em SQLite com `market_context_json`
- [ARCHITECTURE.md](ARCHITECTURE.md)
  - Visão arquitetural geral do sistema
- [CODING_STANDARDS.md](CODING_STANDARDS.md)
  - Padrões de código e estilo
- [CONTRIBUTING.md](CONTRIBUTING.md)
  - Como contribuir
- [DATA_MODELS.md](DATA_MODELS.md)
  - Modelos de dados e schemas
- [BACKLOG_UNIFICADO.md](BACKLOG_UNIFICADO.md)
  - Todas as tarefas e sprints
- [STATUS_ENTREGAS.md](STATUS_ENTREGAS.md)
  - Status de entregas e milestones

---

## 🏗️ Documentação Arquitetural

### Diagramas e Modelagem

- [DIAGRAMA_CLASSES.md](DIAGRAMA_CLASSES.md)
  - Arquitetura orientada a objetos: 10 classes principais e padrões de design
  - Público: 👨‍💻 Developer, Tech Lead
- [REGRAS_NEGOCIO.md](REGRAS_NEGOCIO.md)
  - Formalização das 13 regras de negócio com criticidade e mapeamento
  - Público: 👨‍💼 Operador, 👨‍💻 Developer
- [DIAGRAMA_DADOS.md](DIAGRAMA_DADOS.md)
  - Modelo visual de dados (ER) com entidades e relacionamentos
  - Público: 👨‍💻 Developer, 🏗️ Tech Lead
- [MODELAGEM_DADOS.md](MODELAGEM_DADOS.md)
  - Schema implementado com DDL, índices, triggers, views e constraints
  - Público: 👨‍💻 Developer, 🔧 DevOps
- [ADRs.md](ADRs.md)
  - Architecture Decision Records com contexto, consequências e trade-offs
  - Público: 🏗️ Tech Lead, 👨‍💻 Senior Developer

**Recomendação:** leia nesta ordem:

1. [ARCHITECTURE.md](ARCHITECTURE.md) - visão geral
2. [DIAGRAMA_CLASSES.md](DIAGRAMA_CLASSES.md) - classes e padrões
3. [REGRAS_NEGOCIO.md](REGRAS_NEGOCIO.md) - regras críticas
4. [DIAGRAMA_DADOS.md](DIAGRAMA_DADOS.md) - fluxo de dados
5. [MODELAGEM_DADOS.md](MODELAGEM_DADOS.md) - schema SQL
6. [ADRs.md](ADRs.md) - decisões e trade-offs

---

## 🔗 Links Rápidos

### By Role

- 👨‍💼 [Operador: Comece aqui](features/intraday-learner/APRENDIZADO_TRANSPARENTE_GUIA.md)
- 👨‍💻 [Developer: Arquitetura](ARCHITECTURE.md)
- 📊 [PM: Status Entregas](STATUS_ENTREGAS.md)
- 🏗️ [Tech Lead: Roadmap](features/intraday-learner/STATUS_INTRADAY_LEARNER_FINAL.md)

### By Feature

- ⚡ [IntraDayLearner](features/intraday-learner/README.md)

---

## ✅ Última Atualização

- **Data:** 03/03/2026
- **Reorganização:** IntraDayLearner docs em `docs/features/intraday-learner/`
- **Status:** Estrutura pronta, documentação completa
- **Próxima:** Adicionar novos features em mesmo padrão

---

**Nota:** Sempre cheque o `README.md` de cada feature para navegação interna.

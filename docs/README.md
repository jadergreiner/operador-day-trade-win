# Documentação - Índice Geral

**Projeto:** Operador Day Trade WIN
**Organização:** Estrutura hierárquica por tipo/feature

⚠️ **CORE DO PRODUTO:** Veja [INICIAR_DIARIOS.bat](../INICIAR_DIARIOS.bat) e [INICIAR_MICRO_TENDENCIA_AUTO_TRADE.bat](../INICIAR_MICRO_TENDENCIA_AUTO_TRADE.bat) na **raiz do projeto** - estes são os dois entry points principais que o sistema foi construído ao redor.

🚨 **STATUS CRÍTICO (05/03/2026):**
- ✅ P50 (Pessimism Detection): **ATIVO** - Sistema em estado seguro
- 🔴 GATE 2 (Backtest Validation): **FAIL** (DD 92.8%, σ=238.8%) - Capital HOLD
- 📍 Próxima ação: P0-2 melhorias (Risk Management + Dataset real)

---

## 📚 Estrutura de Documentação

```
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
**Comece aqui:** [docs/features/intraday-learner/README.md](features/intraday-learner/README.md)

⚠️ **IMPORTANTE - TERMINAL ISOLATION (NOVO):**
Antes de executar qualquer trade, leia [QUICK_START.md#-configuração-de-isolamento](QUICK_START.md#-configuração-de-isolamento-de-terminal-importante)
- Configura `MT5_TERMINAL_PATH` para proteger contra brokers errados
- Sistema bloqueará automaticamente qualquer conexão a FBS/XP/Zero/IC/Ativa/Rica
- Sem isolamento correto, go-live é impossível ❌

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
2. [features/intraday-learner/](features/intraday-learner/) - Status feature

---

## 📋 Features Documentadas

### IntraDayLearner
**Localização:** `docs/features/intraday-learner/`
**Status:** ✅ Implementado
**Data:** 03/03/2026

Desenvolvimento de aprendizado em tempo real (intraday) para análise de padrões HOLD.

- 🟢 **IMPLEMENTAÇÃO:** 3 camadas de proteção MT5 CLEAR
- 🟡 **P33-P36:** Próximas fases de integração e dashboard
- 📊 **Impacto esperado:** +1-2% win rate em 3 semanas

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
```
docs/features/feature-x/
├── README.md
├── GUIA_OPERADOR.md
├── IMPLEMENTACAO_TECNICA.md
└── STATUS_ROADMAP.md
```

---

## 📖 Documentação Global

| Documento | Propósito |
|-----------|-----------|
| [ARCHITECTURE.md](ARCHITECTURE.md) | Visão arquitetural geral do sistema |
| [CODING_STANDARDS.md](CODING_STANDARDS.md) | Padrões de código e estilo |
| [CONTRIBUTING.md](CONTRIBUTING.md) | Como contribuir |
| [DATA_MODELS.md](DATA_MODELS.md) | Modelos de dados e schemas |
| [BACKLOG_UNIFICADO.md](BACKLOG_UNIFICADO.md) | Todas as tarefas e sprints |
| [STATUS_ENTREGAS.md](STATUS_ENTREGAS.md) | Status de entregas e milestones |

---

## � Documentação Arquitetural (Complementar a ARCHITECTURE.md)

### Diagramas e Modelagem

| Documento | Propósito | Público |
|-----------|-----------|---------|
| [DIAGRAMA_CLASSES.md](DIAGRAMA_CLASSES.md) | Arquitetura orientada a objetos: 10 classes principais com relacionamentos, responsabilidades e padrões de design | 👨‍💻 Developer, Tech Lead |
| [REGRAS_NEGOCIO.md](REGRAS_NEGOCIO.md) | Formalização de 13 regras de negócio: 6 críticas (P0), 4 de risco (P1) e 3 de otimização (P2) com criticidade e mapeamento a código | 👨‍💼 Operador, 👨‍💻 Developer |
| [DIAGRAMA_DADOS.md](DIAGRAMA_DADOS.md) | Modelo de dados visual (ER): 10 entidades, 11 relacionamentos, integridade referencial e fluxo de dados | 👨‍💻 Developer, 🏗️ Tech Lead |
| [MODELAGEM_DADOS.md](MODELAGEM_DADOS.md) | Schema implementado: DDL completo com 10 tabelas, indices, triggers, views e constrains (CVM/B3 audit-ready) | 👨‍💻 Developer, 🔧 DevOps |
| [ADRs.md](ADRs.md) | Architecture Decision Records: 7 decisões arquiteturais com contexto, consequências, estatuto e próximas ações | 🏗️ Tech Lead, 👨‍💻 Senior Developer |

**Recomendação:** Leia nesta ordem:
1. Comece com [ARCHITECTURE.md](ARCHITECTURE.md) (visão geral)
2. [DIAGRAMA_CLASSES.md](DIAGRAMA_CLASSES.md) (como funciona: classes & padrões)
3. [REGRAS_NEGOCIO.md](REGRAS_NEGOCIO.md) (o que não pode falhar: regras críticas)
4. [DIAGRAMA_DADOS.md](DIAGRAMA_DADOS.md) (fluxo de dados: entidades e relacionamentos)
5. [MODELAGEM_DADOS.md](MODELAGEM_DADOS.md) (implementação: schema SQL)
6. [ADRs.md](ADRs.md) (por quê: decisões e trade-offs)

---

## �🔗 Links Rápidos

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

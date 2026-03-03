# Documentação - Índice Geral

**Projeto:** Operador Day Trade WIN  
**Organização:** Estrutura hierárquica por tipo/feature

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

# 🎯 Prompt de Priorização - Operador Day Trade WIN

Foco na entrega do operador `INICIAR_MICRO_TENDENCIA_AUTO_TRADE.bat`

## Instruções para Análise de Priorização

Leia os seguintes documentos de governança para extrair status, dependências e riscos:

### Documentos Obrigatórios (Fonte da Verdade)

1. **[docs/ROADMAP.md](../docs/ROADMAP.md)** - Visão estratégica e roadmap (Now → Next → Later)
2. **[docs/PLANO_DE_SPRINTS_MVP_NOW.md](../docs/PLANO_DE_SPRINTS_MVP_NOW.md)** - Backlog detalhado do Sprint ativo e timeline
3. **[ANALISE_PRIORIZACAO_23FEV.md](../ANALISE_PRIORIZACAO_23FEV.md)** - Status atual, dependências, riscos e TODOs (substitui STATUS_ENTREGAS)
4. **[TAREFAS_INTEGRACAO_PHASE6.md](../TAREFAS_INTEGRACAO_PHASE6.md)** - Parallelogram de tasks para Eng Sr + ML Expert
5. **[docs/FEATURES.md](../docs/FEATURES.md)** - Mapa de features com prioridade e status
6. **[docs/BOARD_STRUCTURE.md](../docs/BOARD_STRUCTURE.md)** - Responsabilidades por persona (RACI matrix)
7. **[docs/CRITERIOS_DE_ACEITE_MVP.md](../docs/CRITERIOS_DE_ACEITE_MVP.md)** - Matriz de critérios de aceite padrão
8. **[docs/agente_autonomo/](../docs/agente_autonomo/)** - Decisões aprovadas, arquitetura e versionamento

### Documentos Complementares (Contexto)

- [docs/ARCHITECTURE.md](../docs/ARCHITECTURE.md) - Arquitetura em camadas (Data → Analysis → Decision → Execution)
- [docs/CONTRIBUTING.md](../docs/CONTRIBUTING.md) - Padrões de código e contribuição
- [GITHUB_ISSUES_TEMPLATES_23FEV.md](../GITHUB_ISSUES_TEMPLATES_23FEV.md) - Templates prontos para criar issues
- [ANALISE_FINANCEIRA_US004.md](../ANALISE_FINANCEIRA_US004.md) - Análise de impacto financeiro

---

## Análise Requerida

### SEÇÃO 1: Status Atual

**Extrair de: [ANALISE_PRIORIZACAO_23FEV.md](../ANALISE_PRIORIZACAO_23FEV.md) e [PLANO_DE_SPRINTS_MVP_NOW.md](../docs/PLANO_DE_SPRINTS_MVP_NOW.md)**

- Qual é o Sprint ativo? (dia de kickoff, duração, personas)
- % de conclusão das tarefas? (contar DONE vs PENDING/BLOCKED)
- Quais estão bloqueadas e por quê? (listar bloqueadores específicos)
- Timeline até Gate 1 / Beta / Go-Live

### SEÇÃO 2: Dependências Críticas

**Extrair de: [ANALISE_PRIORIZACAO_23FEV.md](../ANALISE_PRIORIZACAO_23FEV.md) → "Mapa de Dependências"**

- Liste todas as tarefas com dependências não-satisfeitas
- Ordene por "capacidade de desbloquear" (impacto cascata) → tarefas cujo sucesso libera múltiplas outras
- Identifique caminho crítico (critical path): que sequência não pode atrasar?
- Mapeie personas críticas esperando input (CTO, ML Lead, Head Finanças)

### SEÇÃO 3: Risco Operacional

**Extrair de: [ANALISE_PRIORIZACAO_23FEV.md](../ANALISE_PRIORIZACAO_23FEV.md) → "Risco Operacional"**

- Tarefas atrasadas? Quanto tempo perdido vs plano original?
- SLAs em risco? (Gate 1 → 05/03 | Beta → 13/03 | Go-Live → 10/04)
- Personas críticas esperando input? (com deadlines)
- Fatores de risco alto/médio/baixo e mitigações

### SEÇÃO 4: TODOs Não Rastreados

**Procure em: `src/` e `scripts/` por `TODO:` (obrigatório), `FIXME:` e `XXX:` (opcional)**

Para cada encontrado:

- Identifique se existe Issue correspondente (procure em GITHUB_ISSUES_TEMPLATES_23FEV.md)
- Se não existe, prepare Issue com:
  - Título descritivo
  - Link para [docs/CRITERIOS_DE_ACEITE_MVP.md](../docs/CRITERIOS_DE_ACEITE_MVP.md)
  - Persona responsável (consulte [docs/BOARD_STRUCTURE.md](../docs/BOARD_STRUCTURE.md))
  - Prioridade (Alta/Média/Baixa) baseada em impacto
  - Esforço estimado (em horas)
  - Bloqueador? (bloqueia outras tasks?)

---

## Saída Esperada

### 1. PRÓXIMA TASK PRIORITÁRIA

```
Nome: [Nome da task]
Sprint: [Sprint 0/1/2]
Status: [Bloqueada/Em Andamento/Pronta/Não-Iniciada]
Razão: [Por dependência crítica, risco SLA, ou impacto cascata]
Persona: [Quem executa - Eng Sr / ML Expert / QA / Infra]
Issue #: [Link GitHub ou [CRIAR NOVA] com template ref]
Bloqueadores: [Se algum - listar]
Desbloqueia: [Quais tasks/sprints? Impacto cascata]
ETA: [Duração estimada em horas ou dias]
```

### 2. TOP 3 PRÓXIMAS (após prioritária)

```
Task [2]: [Nome]
  - Razão: [Sucinta - dependência ou risco]
  - Status: [Status atual]
  - Persona: [Owner]

Task [3]: [Nome]
  - Razão: [...]
  - Status: [...]
  - Persona: [...]

Task [4]: [Nome]
  - Razão: [...]
  - Status: [...]
  - Persona: [...]
```

### 3. ISSUES PARA CRIAR (TODOs não-rastreados)

```
Issue: [Título do GitHub]
  - Arquivo: [src/... ou scripts/...]
  - Tipo: [Feature / Bug / Chore / Refactor]
  - Critérios de Aceite:
    1. [Descrição verificável]
    2. [Descrição verificável]
    3. [Descrição verificável]
    4. [Descrição verificável - opcional]
    5. [Descrição verificável - opcional]
  - Persona Responsável: [Eng Sr / ML Expert / QA]
  - Prioridade: [🔴 CRÍTICA / 🟠 ALTA / 🟡 MÉDIA / 🟢 BAIXA]
  - Esforço Estimado: [Xh ou X dias]
  - Bloqueador? [Sim/Não - bloqueia quais tasks?]
  - Template GitHub: [Link para GITHUB_ISSUES_TEMPLATES_23FEV.md se existir]
```

### 4. RECOMENDAÇÕES (1-3 ajustes estratégicos)

```
Recomendação 1: [O quê fazer, por quê, impacto]
  - Ação: [Executar]
  - Persona: [Quem]
  - Deadline: [Quando - ASAP/antes de X data]

Recomendação 2: [...]
  - Ação: [...]
  - Persona: [...]
  - Deadline: [...]

Recomendação 3: [...]
  - Ação: [...]
  - Persona: [...]
  - Deadline: [...]
```

---

## Notas de Implementação

### Personas Definidas (consulte BOARD_STRUCTURE.md)

- **Eng Sr (Senior Software Engineer)**: Arquitetura, MT5 API, Risk Validators, Orders Executor, WebSocket
- **ML Expert (Machine Learning Specialist)**: Dataset, Feature Engineering, XGBoost, Grid Search, Backtest
- **QA / Infra**: Health Checks, Performance Benchmarking, Staging Deployment, E2E Tests
- **Product Owner / Head Finanças**: Aprovações, SLAs, Gate decisions, Go-Live

### Prioridades Padrão

- 🔴 **CRÍTICA**: Bloqueia Sprint ou Go-Live (Gate 1/2/3 dependency)
- 🟠 **ALTA**: Impacto alto no roadmap ou SLA em risco
- 🟡 **MÉDIA**: Impacto médio, pode ser deferred com justificativa
- 🟢 **BAIXA**: Nice-to-have, pode ser post-launch

### Gates Críticos (não atrasar)

| Gate | Data | Checkpoints |
|------|------|------------|
| **Gate 1** | 05/03 17:00 | F1 > 0.65, Risk framework validado, sprint 1 100% |
| **Gate 2** | 12/03 | Integration OK, performance benchmarks passed |
| **Gate 3** | 19/03 | E2E tests, staging validated, UAT ready |
| **Beta** | 13/03 | v1.1 live com alertas |
| **Go-Live v1.2** | 10/04 | Execução automática live com capital pequeno |

### Padrão de Commits

Todos os commits devem refletir a sincronização de documentação:

```bash
git commit -m "Atualizado priorização + sincronizado docs após task X"
git commit -m "feat: Implementar TODO-Y, atualizar ANALISE_PRIORIZACAO_23FEV.md"
```

---

## Pontos de Verificação

Antes de executar análise:

- [ ] Todos os 8 documentos obrigatórios acessíveis?
- [ ] ANALISE_PRIORIZACAO_23FEV.md é a fonte de verdade (substitui STATUS_ENTREGAS)?
- [ ] TAREFAS_INTEGRACAO_PHASE6.md reflete o parallelogram Eng Sr + ML Expert?
- [ ] PLANO_DE_SPRINTS_MVP_NOW.md está sincronizado com datas reais?
- [ ] GITHUB_ISSUES_TEMPLATES_23FEV.md tem templates para principais TODOs?
- [ ] docs/agente_autonomo/ tem decisões financeiras aprovadas?

---

## Referências Rápidas

### Links para Documentos

- [Cronograma Corrente (ANALISE_PRIORIZACAO_23FEV.md)](../ANALISE_PRIORIZACAO_23FEV.md#L59-L110)
- [Dependências (ANALISE_PRIORIZACAO_23FEV.md)](../ANALISE_PRIORIZACAO_23FEV.md#L56-L105)
- [Riscos (ANALISE_PRIORIZACAO_23FEV.md)](../ANALISE_PRIORIZACAO_23FEV.md#L130-L173)
- [TODOs (ANALISE_PRIORIZACAO_23FEV.md)](../ANALISE_PRIORIZACAO_23FEV.md#L182-L250)
- [Templates de Issues](../GITHUB_ISSUES_TEMPLATES_23FEV.md)
- [Decisões Aprovadas](../docs/agente_autonomo/)

### Comandos Úteis

```bash
# Procurar TODOs no código
grep -r "TODO:" src/ scripts/ --include="*.py"

# Procurar no backlog do Sprint
grep -A 2 "MUST\|SHOULD\|COULD" docs/PLANO_DE_SPRINTS_MVP_NOW.md

# Extrair tarefas bloqueadas
grep -i "BLOCKED\|bloqueado" ANALISE_PRIORIZACAO_23FEV.md
```

---

**Última Atualização:** 23/02/2026
**Responsável por Manutenção:** GitHub Copilot / Agentes Autônomos
**Status:** ✅ Pronto para usar

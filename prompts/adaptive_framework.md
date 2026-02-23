# 🎯 Prompt de Priorização - VERSÃO ADAPTATIVA 2.0

## 🔄 SISTEMA DE AUTO-DESCOBERTA DINÂMICA

Este prompt se adapta **automaticamente** conforme o projeto evolui através de:

1. **Detecção de Documentos** - Busca arquivos em `docs/` e raiz
2. **Leitura de Configuração** - Carrega personas de `prompts/board_*.json`
3. **Análise de Sprint Status** - Detecta Sprint ativo dinamicamente
4. **Validação de Links** - Verifica se docs referenciados existem
5. **Versionamento** - Adapta-se a versões do projeto

---

## 🤖 ALGORITMO DE AUTO-ADAPTAÇÃO

### Fase 1: DESCOBERTA DE CONTEXTO

```python
# Pseudo-código para auto-descoberta
1. DETECTAR_DOCUMENTOS_DISPONIVEIS()
   ├─ Procurar: docs/ROADMAP*.md
   ├─ Procurar: docs/*STATUS*.md ou ANÁLISE*.md (fonte verdade)
   ├─ Procurar: docs/*SPRINT*.md (backlog ativo)
   ├─ Procurar: docs/*FEATURES*.md (feature matrix)
   ├─ Procurar: docs/agente_autonomo/* (decisões)
   └─ RETORNAR: lista de docs encontrados

2. DETECTAR_SPRINT_ATIVO()
   ├─ Ler docs encontrados
   ├─ Procurar padrão "Sprint N (XX/YY - ZZ/AA)"
   ├─ Extrair: número do Sprint, datas, personas
   └─ RETORNAR: Sprint { id, dates, personas, status }

3. DETECTAR_PERSONAS_DISPONIVEIS()
   ├─ Ler: prompts/board_*.json ou docs/*/PERSONAS.json
   ├─ Mapear: { id → nome → especialidade }
   └─ RETORNAR: { personas_pool, especialidades_map }

4. DETECTAR_TAREFAS_PRIORITARIAS()
   ├─ Ler: docs/*ANÁLISE*.md ou docs/*STATUS*.md
   ├─ Procurar padrão "PRÓXIMA TASK" ou "TODO:"
   ├─ Extrair: número, título, bloqueadores, esforço
   └─ RETORNAR: [ Task { id, title, blockers, effort } ]

5. VALIDAR_SINCRONIZACAO()
   ├─ Verificar: docs/agente_autonomo/SYNC_MANIFEST.json existe?
   ├─ Ler checksums e timestamps
   ├─ Comparar com docs reais
   └─ RETORNAR: { sync_status, out_of_sync_docs, warnings }

6. RETORNAR: CONTEXT = { docs, sprint, personas, tasks, sync_status }
```

### Fase 2: CUSTOMIZAÇÃO DINÂMICA

```python
1. GERAR_PROMPT_CUSTOMIZADO(CONTEXT)
   ├─ Para cada doc em CONTEXT.docs
   │  ├─ Gerar seção dinâmica
   │  ├─ Usar paths reais (não hardcoded)
   │  └─ Validar links
   │
   ├─ Para cada persona em CONTEXT.personas
   │  ├─ Alocar conforme especialidade
   │  ├─ Validar disponibilidade
   │  └─ Gerar assignment dinamicamente
   │
   ├─ Para Sprint em CONTEXT.sprint
   │  ├─ Calcular timeline real
   │  ├─ Identificar Gates críticos
   │  └─ Gerar milestones dinâmicos
   │
   └─ RETORNAR: Prompt customizado + validações

2. EXECUTAR_PRE_FLIGHT_CHECKS()
   ├─ [ ] Todos docs referenciados existem?
   ├─ [ ] Todas personas alocadas estão disponíveis?
   ├─ [ ] Sprint dates fazem sentido?
   ├─ [ ] Links (GitHub issues) são válidos?
   ├─ [ ] SYNC_MANIFEST está atualizado?
   └─ RETORNAR: [ warnings [], errors [] ]
```

---

## 📝 VERSÃO ADAPTATIVA - IMPLEMENTAÇÃO

### Passo 1: Incluir DETECÇÃO AUTOMÁTICA no prompt

```markdown
# 🎯 Prompt de Priorização - AUTO-ADAPTATIVO

## 🔍 FASE 1: AUTO-DESCOBERTA (Executar automáticamente)

Antes de tudo, execute estas buscas para DESCOBRIR o contexto real:

### 1.1 Descobrir Documentos-Fonte de Verdade

**Objetivo:** Encontrar qual documento é a fonte de verdade ATUAL

**Busque por (em ordem de prioridade):**

1. **Documentos de Status/Análise:**
   ```bash
   find docs/ -name "*STATUS*.md" -o -name "*ANÁLISE*.md" -o -name "*ANALYSE*.md"
   # Se encontrado → USE ESTE como fonte de verdade
   # Espera: Contém "Sprint ativo:", "Progresso", "%"
   ```

2. **Se não encontrado, busque Status em raiz:**
   ```bash
   ls -la | grep -i "status\|análise\|analysis"
   # Se encontrado no root → USE ESTE
   ```

3. **Fallback: Usar PLANO_DE_SPRINTS_MVP_NOW.md**
   ```bash
   find docs/ -name "*PLANO*SPRINT*.md" -o -name "*BACKLOG*.md"
   # Se encontrado → USE COMO backlog reference
   ```

**Resultado Esperado:**
```
Fonte de Verdade: [CAMINHO REAL ENCONTRADO]
Last update: [TIMESTAMP REAL]
Format: [JSON | Markdown | Tabela]
```

---

### 1.2 Descobrir Sprint ATIVO

**Objetivo:** Extrair Sprint ID, datas, personas da fonte de verdade

**Algoritmo:**

```bash
# Buscar padrão: "Sprint N (" ou "SPRINT_N"
grep -i "sprint.*(" [ARQUIVO_ENCONTRADO] | head -1

# Extrair datas no formato XX/YY - ZZ/AA
grep -E "[0-9]{1,2}/[0-9]{1,2}\s*-\s*[0-9]{1,2}/[0-9]{1,2}" [ARQUIVO]

# Extrair personas mencionadas
grep -i "persona\|pessoa\|owner\|assigne" [ARQUIVO] | head -5
```

**Resultado Esperado:**
```
Sprint ID: [N]
Period: [XX/YY - ZZ/AA]
Personas: [Lista de nomes/IDs]
Status: [% completo | BLOCKED | ON-TRACK]
Gate deadline: [Data do próximo gate]
```

---

### 1.3 Descobrir Personas Disponíveis

**Objetivo:** Mapear lista REAL de personas do projeto

**Busque em (em ordem):**

1. **Arquivo Estruturado (JSON/YAML):**
   ```bash
   find prompts/ -name "board_*.json" -o -name "*personas*.json" -o -name "*team*.json"
   cat [ARQUIVO_ENCONTRADO] | jq '.members[] | {id, nome, especialidade}'
   ```

2. **Se não encontrado, buscar em Markdown:**
   ```bash
   find docs/ -name "*estrutura*" -o -name "*personas*" -o -name "*team*" -o -name "*board*"
   grep -A 3 "persona\|membro\|engineer" [ARQUIVO] | head -20
   ```

3. **Fallback: Usar Nomes mencionados em assigns existentes**
   ```bash
   # Procurar em issues/PRs mencionados
   grep -i "@[a-z-]*" docs/*ANÁLISE* | cut -d'@' -f2 | sort -u
   ```

**Resultado Esperado:**
```
Personas Pool: [
  { id: 1, nome: "Eng Sr", especialidade: "Backend/Architecture", disponível: true },
  { id: 2, nome: "The Brain", especialidade: "ML/IA", disponível: true },
  ...
]
```

---

### 1.4 Descobrir TAREFAS PRIORITÁRIAS

**Objetivo:** Extrair TODO/TASK list REAL do projeto

**Busque por:**

```bash
# 1. No arquivo de análise/status
grep -i "próxima.*task\|todo\|task.*prioritária" [STATUS_FILE] -A 10

# 2. No código (TODOs)
grep -r "TODO:" src/ scripts/ --include="*.py" | head -20

# 3. Em template de issues
ls docs/*ISSUE* || ls docs/*GITHUB* && cat [ARQUIVO]

# 4. Em backlog/sprint plan
grep -E "S1-[0-9]|Task-[0-9]|TODO-[0-9]" [SPRINT_FILE]
```

**Resultado Esperado:**
```
Tasks Encontradas: [
  { id: "TODO-1", titulo: "...", esforço: "2-3h", bloqueadores: "nenhum" },
  { id: "TODO-2", titulo: "...", esforço: "3-4h", bloqueadores: ["TODO-1"] },
  ...
]
```

---

### 1.5 Validar SINCRONIZAÇÃO

**Objetivo:** Detectar se documentação está sincronizada

**Verificações:**

```bash
# 1. Existe SYNC_MANIFEST.json?
test -f docs/agente_autonomo/SYNC_MANIFEST.json && echo "✅ SYNC found" || echo "❌ SYNC missing"

# 2. Se existe, é válido?
cat docs/agente_autonomo/SYNC_MANIFEST.json | jq '.documents | length'

# 3. Qual é o status de sync?
cat docs/agente_autonomo/SYNC_MANIFEST.json | jq '.sync_status'

# 4. Quando foi última atualização?
cat docs/agente_autonomo/SYNC_MANIFEST.json | jq '.last_update'

# 5. Docs desincronizados?
cat docs/agente_autonomo/SYNC_MANIFEST.json | jq '.out_of_sync_documents'
```

**Resultado Esperado:**
```
Sync Status: [SYNCHRONIZED | OUT_OF_SYNC]
Last Update: [TIMESTAMP]
Out of Sync: [lista de docs desincronizados ou empty]
Validation: [✅ PASS | ⚠️ WARNING | ❌ CRITICAL]
```

---

## 🎯 FASE 2: GERAÇÃO DINÂMICA DE CONTEXTO

Com base nos resultados da Fase 1, GERAR dinamicamente:

### 2.1 Próxima Task (Baseado em dados REAIS)

```markdown
# PRÓXIMA TASK PRIORITÁRIA

[Preencher DINAMICAMENTE com valores encontrados em Fase 1]

Nome: [Extraído de TODO-list real]
Sprint: [Extraído de sprint atual detectado]
Status: [Extraído de status real no documento]
Razão: [Extraído de bloqueadores reais]
Persona: [Extraído de assignment real]
Issue #: [Detectado em GitHub ou docs]
ETA: [Extraído de estimativa real]
```

### 2.2 Top 3 Próximas (Ordenadas por impacto REAL)

```markdown
Task [2]: [Segundo maior bloqueador detectado]
  - Status: [REAL]
  - Persona: [REAL]
  - Bloqueadores: [REAIS]

Task [3]: [Terceiro maior bloqueador detectado]
  - Status: [REAL]
  - Persona: [REAL]
  - Bloqueadores: [REAIS]

Task [4]: [Quarto maior bloqueador detectado]
  - Status: [REAL]
  - Persona: [REAL]
  - Bloqueadores: [REAIS]
```

### 2.3 Issues Para Criar (Baseado em TODOs encontrados)

```markdown
[Para cada TODO encontrado no código que NÃO tem issue:]

Issue: [Auto-numerar como próximo após obtidos]
  Arquivo: [Path REAL encontrado]
  Type: [Detectado do contexto]
  Critérios: [Extraído de CRITERIOS_DE_ACEITE_MVP.md se existir]
  Persona: [Detectado de especialidade matches]
  Prioridade: [Calculada dinamicamente por impacto]
  Esforço: [Extraído do TODO comment ou estimado]
```

---

## ⚙️ PRE-FLIGHT CHECKS (Validação Antes de Usar)

Antes de executar qualquer prompt, VALIDAR:

```bash
# 1. Arquivo de contexto existe?
[ ] Encontrado: [ARQUIVO]

# 2. Todas as pessoas no prompt existem no pool real?
[ ] Persona 1 existe? [ ] Persona 2? [ ] ... [ ] Persona N?

# 3. Sprint dates fazem sentido?
[ ] Data início > hoje? [ ] Data fim > data início?

# 4. Todos os links/paths são válidos?
[ ] Link 1 existente? [ ] Link 2? ... [ ] Link N?

# 5. SYNC_MANIFEST updated no último dia?
[ ] Last update < 24h atrás?

# 6. Não há docs criados após SYNC_MANIFEST?
[ ] ls -la docs/ | grep -v SYNC_MANIFEST && check dates
```

---

## 📊 ADAPTAÇÃO AUTOMÁTICA CONFORME PROJETO EVOLUI

### Quando Project Muda → Prompt Auto-Adapta

**Cenário 1: Novo Sprint iniciado**
```
Antes: Sprint 1 ativo
Após: git commit "feat: Iniciar Sprint 2"
Auto-detecção: Próxima execução detecta Sprint 2 automaticamente
✅ Prompt usa Sprint 2 dates, personas, tasks
```

**Cenário 2: Nova Persona adicionada**
```
Antes: 8 personas no board_16_members_data.json
Após: Atualizar board_16_members_data.json com { id: 18, ... }
Auto-detecção: Próxima execução inclui Persona 18
✅ Prompt pode alocar Persona 18 se compatível
```

**Cenário 3: Documentação sincronizada**
```
Antes: SYNC_MANIFEST.json desincronizado
Após: git commit "docs: Sync Sprint 1 progress"
Auto-detecção: SYNC_MANIFEST atualizado
✅ Prompt detecta sincronização e prossegue
```

**Cenário 4: Nova Sprint Plan criada**
```
Antes: docs/PLANO_DE_SPRINTS_MVP_NOW.md
Após: Criar docs/PLANO_DE_SPRINTS_SPRINT2.md
Auto-detecção: Detecta novo arquivo de sprint
✅ Prompt usa arquivo mais recente automatically
```

**Cenário 5: Issues criadas no GitHub**
```
Antes: Issues #66-#69 mencionadas no prompt
Após: GitHub API mostra Issues +#70, +#71
Auto-detecção: Próxima execução lê GitHub API
✅ Prompt linklist referencia issue números REAIS
```

---

## 🔗 CAMPOS DINÂMICOS (ADAPTATIVOS)

Estes campos são CALCULADOS automaticamente, não hardcoded:

| Campo | Fonte | Como Adapta |
|-------|-------|-----------|
| Sprint ID | Docs de status/análise | Detecta padrão "Sprint N" |
| Sprint Dates | Arquivo de sprint plan | Lê período real |
| Persona Pool | board_*.json | Carrega JSON dinâmico |
| Tasks Prioritárias | Docs + código TODOs | Busca em tempo real |
| Issue Numbers | GitHub API ou local | Query issues reais |
| Gates Críticos | Docs de roadmap | Extrai datas de documentos |
| Sync Status | SYNC_MANIFEST.json | Valida em tempo real |
| Documentation Status | ls docs/agente_autonomo/ | Detecta docs presentes |

---

## 🎬 COMO USAR A VERSÃO ADAPTATIVA

### Opção 1: Manual (Preencher Fase 1)

```bash
# 1. Executar descoberta manualmente
cat docs/ANALISE_PRIORIZACAO_23FEV.md | grep "Sprint Ativo"
cat prompts/board_16_members_data.json | jq '.teamBoard.members'
# ... etc

# 2. Usar valores descobertos para customizar

# 3. Executar prompt com contexto real
```

### Opção 2: Automático (Script Python)

```python
# scripts/auto_discover_context.py (criar novo)

import json
import os
import re
from pathlib import Path
from datetime import datetime

def discover_context():
    """Auto-descobrir contexto do projeto"""

    context = {
        'docs_found': {},
        'sprint_active': None,
        'personas_pool': [],
        'tasks': [],
        'sync_status': None,
        'validation': []
    }

    # 1. Discover docs
    for doc in Path('docs').glob('*.md'):
        if 'STATUS' in doc.name or 'ANÁLISE' in doc.name:
            context['docs_found']['source_of_truth'] = str(doc)

    # 2. Detect sprint
    with open(context['docs_found'].get('source_of_truth')) as f:
        content = f.read()
        match = re.search(r'Sprint\s+(\d+)\s+\((.*?)\)', content)
        if match:
            context['sprint_active'] = {
                'id': int(match.group(1)),
                'period': match.group(2)
            }

    # 3. Load personas
    with open('prompts/board_16_members_data.json') as f:
        board = json.load(f)
        context['personas_pool'] = board.get('teamBoard', {}).get('members', [])

    # 4. Sync validation
    sync_file = Path('docs/agente_autonomo/SYNC_MANIFEST.json')
    if sync_file.exists():
        with open(sync_file) as f:
            sync = json.load(f)
            context['sync_status'] = sync.get('sync_status', 'UNKNOWN')

    return context

# Usage:
# context = discover_context()
# print(json.dumps(context, indent=2))
```

### Opção 3: Integrado com Git Hooks

```bash
# .git/hooks/pre-commit (criar novo)

#!/bin/bash

# Antes de cada commit:
# 1. Executar auto-descoberta
python scripts/auto_discover_context.py > /tmp/context.json

# 2. Validar SYNC_MANIFEST
python scripts/validate_sync_manifest.py

# 3. Se sincronizado:
#    - Atualizar prompts com novo contexto
#    - Permitir commit
# 4. Se desincronizado:
#    - Avisar e bloquear commit até sync
exit 0
```

---

## ✅ CHECKLIST: Prompts Verdadeiramente Adaptativos

- [ ] Fase 1: Auto-descoberta implementada (scripts ou manual)
- [ ] Fase 2: Geração dinâmica baseada em Fase 1
- [ ] Campos dinâmicos identificados e mapeados
- [ ] Pre-flight checks implementados
- [ ] Script de auto-descoberta criado (opcional)
- [ ] Git hooks configured (opcional)
- [ ] Documentação de adaptação atualizada
- [ ] Validação de evolução de projeto testada

---

## 📖 RESUMO: Generic vs. Specific vs. Adaptive

```
PROMPTS v1.0 (Atuais - solicita_task.md + executa_task.md)
├─ Específicos: Para Day Trade WIN
├─ Semi-estáticos: Contêm hardcoded paths/personas
├─ Problema: Quebram se contexto mudar
└─ Solução: Implementar auto-descoberta (v2.0)

PROMPTS v2.0 (Proposto - solicita_task_adaptive.md)
├─ Específicos: Para Day Trade WIN
├─ Adaptativos: Auto-descobrem contexto
├─ Dinâmicos: Geram output baseado em dados REAIS
├─ Evolutivos: Evoluem conforme projeto muda
└─ Resilientes: Não quebram se documentação mudar
```

---

**Próximo Passo:** Criar `prompts/solicita_task_adaptive.md` com implementação completa da auto-descoberta?

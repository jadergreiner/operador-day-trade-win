# Instrucoes do Copilot

A comunicacao entre Agente e Humano deve ser sempre em Portugues.

## 📋 Boas Práticas Obrigatórias

Todas as ações devem seguir estas diretrizes sem exceção:

### 1. 🇧🇷 Idioma Português em 100%
- **Requisito:** Manter TODO diálogo, documentação e código em Português do Brasil
- **Escopo:** Comentários, docstrings, variáveis, nomes de funções, commit messages, docs
- **Exemplo:** `def calcular_margem()` ✅ | `def calculate_margin()` ❌
- **Commit:** `git commit -m "feat: adicionar calculadora de margem de segurança"` ✅
- **Documentação:** Todos os .md, .rst, docstrings devem estar em português

### 2. 📝 Integridade de Commits (Sem Quebra de Texto)
- **Requisito:** Mensagens de commit devem ser legíveis e sem caracteres corrompidos
- **Problema Comum:** `docs: Sum├írio de atualiza├º├úo` (encoding incorreto) ❌
- **Solução:** Usar UTF-8 explicitamente em todas as mensagens
- **Verificação:** Antes de fazer commit, validar que não há caracteres `├` ou `┌` nos logs
- **Formato Correto:**

  ```bash
  git commit -m "docs: Sumário de atualização de arquitetura"
  git commit -m "feat: Novo sistema de trading automatizado"
git commit -m "fix: Correção de bug no cálculo de volatilidade"
  ```

- **Exemplo Errado:** `docs: Sum├írio de atualiza├º├úo` ❌ → Refazer com UTF-8

### 3. 🔍 Lint de Markdown (MD013 e Outras Regras)
- **Requisito:** Aplicar lint a TODA documentação criada ou editada
- **Ferramenta:** `pymarkdown` com regras padrão do projeto
- **Regra Principal - MD013 (Comprimento de Linha):**
  - Linhas máximo: 80 caracteres
  - Exceção: URLs, mesas de dados, blocos de código podem ultrapassar
  - Erro Comum: `MD013/line-length: Line length [Expected: 80; Actual: 94]`
- **Outras Regras Críticas:**
  - MD001: Cabeçalhos devem estar em ordem sequencial
  - MD002: Primeiro cabeçalho deve ser nível 1
  - MD022: Cabeçalhos devem ter espaço em branco acima
  - MD023: Cabeçalhos devem começar no início da linha
- **Aplicar Lint:**

  ```bash
  # Verificar um arquivo
python -m pymarkdown scan docs/arquivo.md

  # Verificar toda documentação
  python -m pymarkdown scan docs/

  # Corrigir automaticamente (quando possível)
  python -m pymarkdown fix docs/arquivo.md
  ```

- **Obrigação:** Antes de criar/editar qualquer arquivo .md, rodar lint e corrigir
- **Checklist de Lint:**
  - ✓ Linhas ≤ 80 caracteres?
  - ✓ Cabeçalhos em sequência?
  - ✓ Espaço branco correto?
  - ✓ Sem caracteres de encoding incorreto?

## 🤖 Agente Autônomo - Governança e Sincronização

A partir de 20/02/2026, o projeto implementa um **sistema obrigatório de sincronização de documentação** para manter a integridade do Agente Autônomo.

### ⚠️ Regras Obrigatórias de Sincronização:

1. **Validação Pre-Commit:**
   - ✓ Todos os documentos agente_autonomo presentes?
   - ✓ SYNC_MANIFEST.json atualizado com checksums corretos?
   - ✓ Todas as cross-references são válidas?
   - ✓ Timestamps e versões sincronizadas?
   - ✓ VERSIONING.json reflete mudanças?
   - ✓ Nenhum documento está marcado como "unsyncronized"?

2. **Documentos Críticos (Sincronização Obrigatória):**
   - `docs/agente_autonomo/AGENTE_AUTONOMO_ARQUITETURA.md` - Sync com FEATURES + ROADMAP
   - `docs/agente_autonomo/AGENTE_AUTONOMO_FEATURES.md` - Sync com README.md + ROADMAP
   - `docs/agente_autonomo/AGENTE_AUTONOMO_BACKLOG.md` - Atualizar a cada 24h
   - `docs/agente_autonomo/AUTOTRADER_MATRIX.md` - Sync com FEATURES + ROADMAP
   - `docs/agente_autonomo/SYNC_MANIFEST.json` - SEMPRE desatualizar com novas mudanças
   - `docs/agente_autonomo/VERSIONING.json` - Atualizar com nova versão após mudanças

3. **Integração Obrigatória:**
   - Mudanças em `docs/agente_autonomo/` DEVEM refletir em `README.md`
   - Mudanças em FEATURES DEVEM atualizar ROADMAP com timelines
   - Mudanças em ARQUITETURA DEVEM validar todas dependent docs

4. **Health Check Automático:**
   - Sistema valida a cada 6-8 horas
   - Timestamp da última validação em `SYNC_MANIFEST.json`
   - Se desincronizado, bloqueia novos commits com mensagem clara

### 📋 Manifest de Sincronização:

Consulte `docs/agente_autonomo/SYNC_MANIFEST.json` para:
- Lista completa de documentos rastreados
- Checksums de cada arquivo
- Relacionamentos entre documentos (mandatory_sync_with)
- Status de sincronização em tempo real
- Regras de enforce (bloqueantes vs avisos)
- Próxima horário de health check

### 📦 Versionamento de Componentes:

Consulte `docs/agente_autonomo/VERSIONING.json` para:
- Versão atual de cada componente (BDI_Processor, Documentation_System, etc)
- Release calendar com ETAs
- Feature matrix por versão
- Status de deployment (PRODUCTION, STAGING, PLANNING)

### 🚀 Procedimento de Atualização:

Ao modificar qualquer documento do Agente Autônomo:

```bash
# 1. Fazer mudança no documento específico
vim docs/agente_autonomo/AGENTE_AUTONOMO_*.md

# 2. Identificar documentos relacionados (ver SYNC_MANIFEST)
# 3. Atualizar documentos relacionados com sincronização

# 4. Validar antes de commit
python scripts/validate_sync_manifest.py  # (se implementado)

# 5. Commit com mensagem clara sobre sincronização:
git commit -m "Update AGENTE_AUTONOMO_*: sync with ARQUITETURA + FEATURES + ROADMAP"
```

### 📚 Documentação Completa:

- [🤖 Arquitetura Detalhada](docs/agente_autonomo/AGENTE_AUTONOMO_ARQUITETURA.md)
- [📊 Sistema de Sincronização](docs/agente_autonomo/SYNC_MANIFEST.json)
- [📈 Rastreamento de Versionamento](docs/agente_autonomo/VERSIONING.json)
- [📊 Dashboard de Progresso](docs/agente_autonomo/AGENTE_AUTONOMO_TRACKER.md)

**IMPORTANTE:** A integridade do Agente Autônomo depende da sincronia perfeita da documentação.
Sempre validar antes de commit seguindo as regras acima.
---

## 🚀 PHASE 6 INTEGRATION STATUS (20/02/2026 - Kickoff)

### 📋 Agentes Autônomos Ativos

**Two Autonomous Agents Starting MON 27/02:**

1. **👨‍💻 Senior Software Engineer (Eng Sr)**
   - Task INTEGRATION-ENG-001: BDI Integration (3-4h)
   - Task INTEGRATION-ENG-002: WebSocket Server (2-3h, código ✅)
   - Task INTEGRATION-ENG-003: Email Configuration (1-2h)
   - Task INTEGRATION-ENG-004: Staging Deployment (2-3h)

2. **🧠 Machine Learning Expert (ML Expert)**
   - Task INTEGRATION-ML-001: Backtest Setup (2-3h)
   - Task INTEGRATION-ML-002: Backtest Validation (2-3h, script ✅)
   - Task INTEGRATION-ML-003: Performance Benchmarking (2-3h)
   - Task INTEGRATION-ML-004: Final Validation (1-2h)

### 📊 Phase 6 Timeline
- **Week 1 (27 FEB - 01 MAR):** BDI + WebSocket + Backtest setup
- **Week 2 (03 MAR - 07 MAR):** Email + Performance + Staging deploy
- **Week 3 (10 MAR - 13 MAR):** UAT + Final validation + BETA Launch

### 🎯 Success Criteria
- [ ] All 8 parallel tasks completed on time
- [ ] All 18+ tests passing (100%)
- [ ] Backtest gates PASS (Capture ≥85%, FP ≤10%, Win ≥60%)
- [ ] Performance targets MET (P95 <30s, Memory <50MB)
- [ ] CFO + PO sign-off
- [ ] 🚀 **BETA LAUNCH: Thursday 13/03/2026**

### 📚 Phase 6 Documentation (Referência Obrigatória)

- [📋 Tarefas de Integração](TAREFAS_INTEGRACAO_PHASE6.md)
- [🏗️ Arquitetura](ARQUITETURA_INTEGRACAO_PHASE6.md)
- [✅ Checklist](CHECKLIST_INTEGRACAO_PHASE6.md)
- [📊 Resumo Executivo](RESUMO_PHASE6_KICKOFF.md)
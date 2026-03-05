# 📝 Atualização de Documentação — Guia Executável

## 🎯 Objetivo

Manter sincronização e integridade referencial entre 11 documentos críticos
do projeto operador-day-trade-win.

---

## 📚 Documentos e Responsabilidades

| Doc | Propósito | Atualizar Quando |
|-----|-----------|-----------------|
| **ARCHITECTURE.md** | Arquitetura do sistema | Mudança componentes |
| **ADRs.md** | Decisões arquiteturais | Nova decisão design |
| **BACKLOG_UNIFICADO.md** | Status progresso | Conclusão tarefas |
| **CODING_STANDARDS.md** | Padrões código | Nova regra qualidade |
| **CONTRIBUTING.md** | Guia contribuição | Mudança workflow |
| **DATA_MODELS.md** | Modelo dados | Novo campo/schema |
| **DIAGRAMA_CLASSES.md** | Diagrama UML | Nova classe |
| **DIAGRAMA_DADOS.md** | Diagrama ER | Mudança modelagem |
| **MODELAGEM_DADOS.md** | Docs técnica | Evolução DATA_MODELS |
| **README.md** | Visão geral projeto | Mudança features |
| **REGRAS_NEGOCIO.md** | Regras não-técnicas | Nova regra lógica |
| **STATUS_ENTREGAS.md** | Cronograma status | Mudança prazos |

---

## 🔗 Mapa de Dependências

### ARCHITECTURE.md (🔴 CORE)

- ADRs.md, DIAGRAMA_CLASSES.md, CODING_STANDARDS.md, README.md

### DATA_MODELS.md (🔴 CORE)

- DIAGRAMA_DADOS.md, MODELAGEM_DADOS.md, README.md, REGRAS_NEGOCIO.md

### BACKLOG_UNIFICADO.md (🔴 CORE)

- STATUS_ENTREGAS.md, README.md

### REGRAS_NEGOCIO.md

- CODING_STANDARDS.md, DATA_MODELS.md

### CONTRIBUTING.md

- CODING_STANDARDS.md

---

## ✅ Lint Obrigatório

**Regra MD013 (Comprimento de Linha):**

- Máximo 80 caracteres por linha
- Exceção: URLs, tabelas, blocos código
- Ferramenta: `python -m pymarkdown scan docs/`

**Padrões Obrigatórios:**

- MD001: Headers em sequência
- MD002: Primeiro header deve ser (#) nível 1
- MD022: Espaço em branco acima headers
- MD023: Headers devem começar no início da linha
- Sem caracteres de encoding incorreto
- Mensagens commit SEM acentos

**Validação Pré-Commit:**

```bash
python -m pymarkdown scan docs/*.md
python -m pymarkdown fix docs/arquivo.md
```

---

## 🚀 Fluxo de Execução (5 Passos)

### 1️⃣ EDITAR + IDENTIFICAR IMPACTOS

EDITAR documento X → CLASSIFICAR tipo → MAPEAR impactados

**Impactos Rápidos:**

- ARCHITECTURE → ADRs, DIAGRAM_CLASSES, README
- DATA_MODELS → DIAGRAM_DADOS, MODELAGEM, README
- BACKLOG → STATUS_ENTREGAS, README

### 2️⃣ ATUALIZAR DEPENDENTES

REVISAR seção → ATUALIZAR mudanças → VALIDAR cross-references

### 3️⃣ LINT VALIDATION (OBRIGATÓRIO)

```bash
python -m pymarkdown scan docs/
# Esperado: 0 violations
python -m pymarkdown fix docs/arquivo.md
```

### 4️⃣ REGISTRAR NO BACKLOG

Adicionar entrada em `BACKLOG_UNIFICADO.md`:

```markdown
- [DD/MM] atualiza_docs: {Docs sincronizados}
  Motivo: {descrição breve}
  Docs Afetados: {lista}
  Lint: ✅ VALIDADO
```

### 5️⃣ COMMIT + PUSH

```bash
python -m pymarkdown scan docs/
git commit -m "docs: Sincronizacao {Docs} - {desc}"
git push origin main
```

---

## 📊 Checklist Rápido

**Antes:**

- Qual documento foi editado?
- Qual tipo: CORE ou DEPENDENTE?
- Quais documentos dependem dele?

**Durante:**

- Atualizei todas as seções impactadas?
- Nenhum link quebrado?
- Nenhuma contradição?

**Depois:**

- Lint passou? (`python -m pymarkdown scan docs/`)
- Registrei em BACKLOG_UNIFICADO.md?
- Commit message clara e SEM acentos?

---

## 🎯 Exemplo Prático (Completo)

**Cenário:** Alterar `ARCHITECTURE.md` (add seção 4.8)

**Execução:**

1. **EDITAR** docs/ARCHITECTURE.md - Nova seção

2. **MAPEAR IMPACTOS:**
   - ADRs.md ← Registrar decisão
   - README.md ← Atualizar visão geral
   - STATUS_ENTREGAS.md ← Reflect completion

3. **ATUALIZAR:**

   ```markdown
   # ADRs.md
   + ADR-XXX com decisão arquitetural

   # README.md
   + Seção "Arquitetura" com link

   # STATUS_ENTREGAS.md
   + Seção Próximas Fases
   ```

### 4️⃣ LINT

   ```bash
   python -m pymarkdown scan docs/ARCHITECTURE.md \
     docs/ADRs.md docs/README.md docs/STATUS_ENTREGAS.md
   # ✅ 0 violations
   ```

### 5️⃣ REGISTRAR

   ```markdown
   - [07/03] atualiza_docs: ARCHITECTURE + ADRs + README
     + STATUS_ENTREGAS sincronizados
     Motivo: Nova seção 4.8 (P1-CORE Etapa 3)
     Docs Afetados: 4 (ARCHITECTURE → 3 dependentes)
     Lint: ✅ VALIDADO (0 violations)
   ```

### 6️⃣ COMMIT

   ```bash
   git commit -m \
     "docs: Sincronizacao ARCHITECTURE - P1-CORE Etapa 3"
   git push
   ```

---

## ⚡ Instruções para Claude Haiku

**Quando receber "Execute {{prompts/atualiza_docs_refatorado.md}}":**

1. **PARSE:** Qual documento foi alterado?
   - Procure: ARCHITECTURE, DATA_MODELS, BACKLOG
   - Identifique: CORE ou DEPENDENTE?

2. **MAP:** Encontre impactados
   - Use seção "Mapa de Dependências"
   - Execute: `grep -r "referência" docs/`

3. **PROCESS:** Atualize impactados
   - Altere APENAS seções relacionadas
   - Use replace_string_in_file (não reescreva tudo)

4. **LINT:** Valide todos os docs
   - Execute: `python -m pymarkdown scan docs/`
   - SE ERROS: `python -m pymarkdown fix docs/arquivo.md`
   - Revalidar até 0 violations

5. **REGISTER:** Adicione entrada BACKLOG
   - Template: `- [DATA] atualiza_docs: {...}`
   - Inclua "Lint: ✅ VALIDADO"

6. **COMMIT:** Mensagem clara, SEM acentos
   - Template: `docs: Sincronizacao {Docs} - {desc}`

**Critical:** Lint obrigatório antes de qualquer commit!

---

## 📌 Reminders

- ⏱️ Tempo típico: 15-30 min por update (incluindo lint)
- 🎯 Foco: Atualizar seções impactadas, não reescrever
- 🔗 Links: Validar cross-references após update
- ✅ Lint: SEMPRE executar antes de commit
- 📝 Registro: SEMPRE adicionar entrada em BACKLOG
- 💬 Commit: Mensagens claras, SEM acentos

---

## 📈 Métricas de Sucesso

| Critério | Target | Validação |
|----------|--------|-----------|
| Docs sincronizadas | 100% | Sem contradição |
| Lint violations | 0 | `pymarkdown scan` |
| Links válidos | 100% | Grep cross-refs |
| Registro BACKLOG | 100% | Check BACKLOG |
| Commits claros | 100% | Review commit |

---

**Versão:** 2.0 (Refatorado 07/03/2026)

**Lint:** ✅ MD013, MD001, MD002, MD022, MD023

**Encoding:** ✅ UTF-8, sem caracteres danificados

**Executable:** ✅ Pronto para Claude Haiku

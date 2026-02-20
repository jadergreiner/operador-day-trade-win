# ✅ SYNC_VALIDATION_CHECKLIST - Mecanismo de Validação Automática

**Última Sincronização:** 20/02/2026 18:00 BRT  
**Próxima Validação:** 21/02/2026 09:00 BRT  
**Status:** ✅ SINCRONIZADO

---

## 📋 Como Usar Este Checklist

Este checklist deve ser completado **ANTES de fazer commit** de qualquer mudança
em documentação crítica.

### Um-Minuto Quick Check:
```bash
# Antes de fazer commit, execute:
echo "Validando sincronização..."

# 1. Verifique Markdown syntax
python -m pymarkdown scan docs/agente_autonomo/*.md

# 2. Verifique VERSIONS (opcional)
python -c "import json; json.load(open('docs/agente_autonomo/VERSIONING.json'))"

# 3. Se tudo OK:
git commit -m "docs: Sincronizacao v1.2 - <descrição>"
```

---

## ✅ CHECKLIST COMPLETO - Antes de Commit

### SEÇÃO 1: Documentação Markdown (Sintaxe)

**MD001 - Cabeçalhos em sequência:**
- [ ] Nenhum # salta para ### (ex: # → ### é inválido)
- [ ] Cabeçalhos começam em # (não em ##)
- [ ] Comando: `python -m pymarkdown scan docs/`

**MD013 - Comprimento de linha:**
- [ ] Linhas ≤ 80 caracteres (exceto URLs e tabelas)
- [ ] Descrição: `Maximum line length is 80`
- [ ] Exceções aceitas: `|`, URLs, blocos de código

**MD022 - Espaço branco acima de cabeçalho:**
- [ ] Linha em branco ANTES de cada `#` (exceto primeiro)
- [ ] Padrão: `\n\n# Title` ✅ | `text\n# Title` ❌

**MD023 - Cabeçalho no início de linha:**
- [ ] Cabeçalhos NÃO indentados
- [ ] Padrão: `# Title` ✅ | `  # Title` ❌

**Verificação Final:**
- [ ] Nenhum caractere corrompido (`├`, `┌`, `│`, etc)
- [ ] Encoding UTF-8 (não ANSI ou Latin-1)
- [ ] Quotes corretos (não smart quotes `"` `"`)

---

### SEÇÃO 2: Conteúdo & Cross-References

**Verificação de Versões:**
- [ ] README.md menciona v1.2.0?
- [ ] copilot-instructions.md menciona v1.2.0?
- [ ] SYNC_MANIFEST_v1.2.md mencionaarcivos?
- [ ] Todas as versões são iguais: v1.2.0

**Verificação de Datas:**
- [ ] Todas as datas são 20/02/2026 ou depois?
- [ ] Nenhuma data no futuro (> hoje)?
- [ ] Formato consistente: DD/MM/YYYY

**Verificação de Links Internos:**
```bash
# Verifique se todos os links existem:
ls docs/agente_autonomo/US-001-EXECUTION_AUTOMATION_v1.2.md
ls docs/agente_autonomo/RISK_FRAMEWORK_v1.2.md
ls docs/agente_autonomo/ARQUITETURA_MT5_v1.2.md
ls docs/agente_autonomo/ML_FEATURE_ENGINEERING_v1.2.md
ls docs/agente_autonomo/SPRINT1_MASTERPLAN.md
```

- [ ] Nenhum link para arquivo inexistente
- [ ] Nenhum link (markdown broken) `](path` sem `[text`)

**Verificação de Feature List Sincronizado:**
- [ ] US-001 AC match SPRINT1_MASTERPLAN items?
- [ ] ML features em FEATURES.md match ML_FEATURE_ENGINEERING.md?
- [ ] Risk gates em RISK_FRAMEWORK match ARQUITETURA_MT5?

**Verificação de Timeline Sincronizado:**
- [ ] Sprint 1: 27/02-05/03 (consistent em todos docs)?
- [ ] Sprint 2: 06/03-12/03?
- [ ] Sprint 3: 13/03-19/03?
- [ ] Sprint 4: 20/03-10/04?
- [ ] Go-live: 10/04/2026?

---

### SEÇÃO 3: Integridade Semântica

**Verificação de Dependências:**
- [ ] Se modifica README → revisa copilot-instructions?
- [ ] Se modifica US-001 → revisa SPRINT1_MASTERPLAN?
- [ ] Se modifica Risk rules → revisa ARQUITETURA_MT5?
- [ ] Se modifica ML features → revisa SPRINT1_MASTERPLAN?

**Verificação de Números Críticos:**
- [ ] Win rate target: 65-68% (não 60%, não 70%)?
- [ ] Sharpe target: >1.0 (não >0.8, não >1.5)?
- [ ] Max drawdown: <15% (não <10%, não <20%)?
- [ ] Latência P95: <500ms (não <1s, não <100ms)?
- [ ] Circuit breakers: -3% / -5% / -8% (não -2% / -4% / -6%)?
- [ ] Capital ramp: 50k → 100k → 150k?

**Verificação de Personas:**
- [ ] Product Owner é mencionado (PO)?
- [ ] Head de Finanças é mencionado (CFO)?
- [ ] CTO/Eng Sr é mencionado (CTO)?
- [ ] ML Expert é mencionado (ML_LEAD)?
- [ ] Todos têm sign-off? ✅

---

### SEÇÃO 4: Git Workflow

**Branch Naming:**
- [ ] Branch name segue padrão: `sync/v1.2-<date>`
- [ ] Exemplo válido: `sync/v1.2-20feb`
- [ ] Exemplo inválido: `master`, `main`, `feature/docs`

**Commit Message:**
- [ ] Formato: `docs: Sincronizacao v1.2 - <descrição>`
- [ ] Exemplo: `docs: Sincronizacao v1.2 - US-001 + RISK_FRAMEWORK`
- [ ] UTF-8 válido (sem caracteres `├`, `┌`)
- [ ] Comprimento: ≤ 72 caracteres (primeira linha)

**Commit Content:**
- [ ] Nenhum arquivo .bak, .tmp, .swp incluído?
- [ ] Nenhum arquivo gerado automaticamente?
- [ ] Apenas .md e .json em `docs/agente_autonomo/`?

**Verificação Final Git:**
```bash
# Antes de push, verifique:
git log -1 --oneline
git status  # Deve estar vazio
git diff --cached --name-only  # Só arquivos esperados
```

---

## 📊 Histórico de Validações

| Data | Executor | Docs | Status | Nota |
|------|----------|------|--------|------|
| 20/02 18:00 | ML Expert | 11 docs | ✅ | Sincronização inicial |
| 20/02 17:00 | CTO/Eng Sr | copilot-instructions | ✅ | Gate details |
| 21/02 (planejado) | PO + Team | Todos | ⏳ | Refinement post-session |

---

## 🚨 Alertas & Ações Corretivas

### Alerta: Lint Failed

**Problema:** `pymarkdown` encontrou erros

**Ação Corretiva:**
```bash
# 1. Identifique o erro
python -m pymarkdown scan docs/agente_autonomo/

# 2. Se MD013 (linha comprida):
# Quebre linhas longas em múltiplas linhas

# 3. Se MD022 (espaço acima cabeçalho):
# Adicione linha em branco antes do #

# 4. Se encoding (caracteres corrompidos):
# Abra arquivo, delete caracteres inválidos, salve com UTF-8

# 5. Teste novamente
python -m pymarkdown scan docs/agente_autonomo/
```

### Alerta: Version Mismatch

**Problema:** Alguns docs têm v1.2.0, outros v1.1.9

**Ação Corretiva:**
```bash
# 1. Procure por todas as versões
grep -r "v1\.[0-9]\.[0-9]" docs/agente_autonomo/

# 2. Padronize para v1.2.0
# Abra cada arquivo, faça Find & Replace
# v1.1 → v1.2.0

# 3. Verify
grep -r "v1\.[0-9]\.[0-9]" docs/agente_autonomo/ | sort | uniq
```

### Alerta: Broken Link

**Problema:** Link `[texto](arquivo.md)` aponta para arquivo inexistente

**Ação Corretiva:**
```bash
# 1. Identifique arquivo inexistente
ls docs/agente_autonomo/ARQUIVO_NAO_EXISTE.md  # Erro!

# 2. Opção A: Criar arquivo
touch docs/agente_autonomo/ARQUIVO_NAO_EXISTE.md

# Opção B: Corrigir link
# Editar arquivo, mudar [texto](arquivo_errado) para [texto](arquivo_certo)

# 3. Verify
git status  # Nenhum arquivo "deleted"
```

---

## 🔐 Assinatura de Validação

```
✅ SYNC_VALIDATION_CHECKLIST: ATIVO
   Validator: ML Expert
   Data: 20/02/2026 18:00
   Status: READY FOR USE

✅ Próxima Validação: 21/02/2026 09:00 (antes de Sprint 1)
   Executor: Product Owner + Team
   Escopo: Sincronização pós-refinement session
```

---

## 📚 Recursos Úteis

**Documentação Markdown Lint:**
- [pymarkdown docs](https://github.com/jackdewinter/pymarkdown)
- [Markdown style guide](https://google.github.io/styleguide/docguide/style.html)

**UTF-8 Encoding:**
- VS Code: Click "UTF-8" in bottom-right (deve já estar configurado)
- Git: `git config --global core.safecrlf true`

**Git Workflow:**
- Branch: `git checkout -b sync/v1.2-20feb`
- Commit: `git commit -m "docs: Sincronizacao v1.2 - descrição"`
- Push: `git push origin sync/v1.2-20feb`
- PR: GitHub interface (requer review)


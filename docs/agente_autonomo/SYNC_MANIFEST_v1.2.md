# 🔄 SYNC_MANIFEST v1.2 - Sistema de Sincronização Obrigatória

**Última Sincronização:** 20/02/2026 18:00 BRT
**Status:** ✅ SINCRONIZADO
**Próxima Validação:** 21/02/2026 09:00 BRT

---

## 📌 Visão Geral do Sistema de Sincronização

Este manifest rastreia a sincronização entre **14 documentos críticos** que
compõem a governança do Agente Autônomo. Qualquer mudança em um documento
**OBRIGA** a revisão dos demais para manter integridade.

### Documentos Rastreados

| # | Documento | Versão | Última Atu. | Status | Criticidade |
|---|-----------|--------|-----------|--------|------------|
| 01 | README.md | v1.2.0 | 20/02 18:00 | ✅ | CRÍTICA |
| 02 | copilot-instructions.md | v1.2.0 | 20/02 17:00 | ✅ | CRÍTICA |
| 03 | AGENTE_AUTONOMO_ARQUITETURA.md | v1.2.0 | 20/02 16:00 | ✅ | CRÍTICA |
| 04 | AGENTE_AUTONOMO_FEATURES.md | v1.2.0 | 20/02 16:00 | ✅ | CRÍTICA |
| 05 | AGENTE_AUTONOMO_ROADMAP.md | v1.2.0 | 20/02 16:00 | ✅ | CRÍTICA |
| 06 | US-001-EXECUTION_AUTOMATION_v1.2.md | v1.2.0 | 20/02 16:00 | ✅ | CRÍTICA |
| 07 | RISK_FRAMEWORK_v1.2.md | v1.2.0 | 20/02 16:00 | ✅ | CRÍTICA |
| 08 | SPRINT1_MASTERPLAN.md | v1.2.0 | 20/02 16:00 | ✅ | CRÍTICA |
| 09 | ARQUITETURA_MT5_v1.2.md | v1.2.0 | 20/02 16:00 | ✅ | CRÍTICA |
| 10 | ML_FEATURE_ENGINEERING_v1.2.md | v1.2.0 | 20/02 16:00 | ✅ | CRÍTICA |
| 11 | AGENTE_AUTONOMO_TRACKER.md | v1.2.0 | 20/02 14:00 | ✅ | MEDIA |
| 12 | AGENTE_AUTONOMO_BACKLOG.md | v1.2.0 | 20/02 14:00 | ✅ | MEDIA |
| 13 | AGENTE_AUTONOMO_CHANGELOG.md | v1.2.0 | 20/02 18:00 | ✅ | MEDIA |
| 14 | VERSIONING.json | v1.2.0 | 20/02 16:00 | ✅ | CRÍTICA |

---

## 🔗 Mapa de Dependências (Sincronização Obrigatória)

### CORE (Modificar qualquer um desses → TODOS os outro precisam revisar)

```
README.md  ←→  copilot-instructions.md
   ↓ ↑            ↓ ↑
   └─→ US-001-EXECUTION_AUTOMATION_v1.2.md ←─┘
       ↓ ↑
       ├─→ ARQUITETURA_MT5_v1.2.md (referenced)
       ├─→ RISK_FRAMEWORK_v1.2.md (referenced)
       ├─→ ML_FEATURE_ENGINEERING_v1.2.md (referenced)
       └─→ SPRINT1_MASTERPLAN.md (timeline sync)
```

### Dependências Específicas

**Se modifica → Sincronize também:**

| Modificou | Depois sincronize | Razão |
|-----------|------------------|-------|
| README.md | copilot-instructions.md | Cross-references |
| README.md | AGENTE_AUTONOMO_FEATURES.md | Feature list must match |
| US-001-EXECUTION_AUTOMATION_v1.2.md | SPRINT1_MASTERPLAN.md | AC must map to sprints |
| ARQUITETURA_MT5_v1.2.md | RISK_FRAMEWORK_v1.2.md | Risk gates defined in arch |
| ML_FEATURE_ENGINEERING_v1.2.md | SPRINT1_MASTERPLAN.md | ML timeline impact |
| AGENTE_AUTONOMO_ROADMAP.md | README.md | Visible roadmap |
| VERSIONING.json | copilot-instructions.md | Version numbers must match |

---

## ✅ Checklist de Validação Automática

Toda mudança deve passar por este checklist ANTES de commit:

### Sintaxe & Estrutura (Automático)

- [ ] YAML válido (se aplicável)
- [ ] Markdown lint clean (MD001-MD048)
- [ ] Linhas ≤ 80 caracteres (MD013 - exceção: URLs/tabelas)
- [ ] Sem caracteres de encoding corrompido (UTF-8 válido)
- [ ] Headings em sequência (MD001)
- [ ] Espaço branco correto (MD022-MD023)

### Conteúdo & Sincronização (Manual)

- [ ] Números de versão consistentes (v1.2.x)
- [ ] Datas de atualização consistentes
- [ ] Cross-references corretas (todos os links internos válidos)
- [ ] Estatísticas atualizadas (LOC, timeline, métricas)
- [ ] Feature list sincronizado entre docs
- [ ] Timeline sincronizado entre docs
- [ ] Nenhum documento desatualizado foi referenciado

### Integridade Semântica

- [ ] US-001 AC sempre refletem SPRINT1_MASTERPLAN
- [ ] RISK_FRAMEWORK sempre reflete ARQUITETURA_MT5
- [ ] ML features sempre refletem ML_FEATURE_ENGINEERING
- [ ] Roadmap sempre reflete current sprints
- [ ] Copilot instructions sempre refletem latest decisions

### Git Workflow

- [ ] Branch name: `sync/v1.2-<date>` (ex: `sync/v1.2-20feb`)
- [ ] Commit message: `docs: Sincronizacao v1.2 - <summary>`
- [ ] Commit é UTF-8 (sem caracteres `├`, `┌`, etc)
- [ ] Commits relacionados agrupados logicamente
- [ ] Nenhum arquivo .bak, .tmp, ou temporário incluído

---

## 📊 Histórico de Sincronização (Audit Trail)

| Data | Executor | Operação | Docs | Status | Nota |
|------|----------|----------|------|--------|------|
| 20/02 18:00 | ML Expert | Create | SYNC_MANIFEST_v1.2.md | ✅ | Creation |
| 20/02 17:00 | CTO/Eng Sr | Update | copilot-instructions.md | ✅ | Gate details |
| 20/02 16:00 | PO | Create | US-001-EXECUTION_AUTOMATION_v1.2.md | ✅ | AC defined |
| 20/02 16:00 | CTO/Eng Sr | Create | ARQUITETURA_MT5_v1.2.md | ✅ | Design |
| 20/02 16:00 | Head Finanças | Create | RISK_FRAMEWORK_v1.2.md | ✅ | Risk gates |
| 20/02 16:00 | ML Expert | Create | ML_FEATURE_ENGINEERING_v1.2.md | ✅ | ML design |
| 20/02 16:00 | Scrum Master | Create | SPRINT1_MASTERPLAN.md | ✅ | Timeline |

---

## 🚨 Alertas de Sincronização

**Nenhum alerta ativo.** Sistema está sincronizado.

### Próximas Ações Obrigatórias (21/02):

- [ ] 09:00: PO + Head Finanças + CTO + ML Expert - Refinement Session
- [ ] 14:00: Confirmação final de Go/No-Go para Sprint 1 (27/02)
- [ ] 18:00: Atualizar SYNC_MANIFEST com resultados de refinement

---

## 🔐 Assinaturas de Sincronização

```
✅ Product Owner: VALIDADO (Feature scope v1.2)
   Assinatura: PO
   Data: 20/02/2026 18:00

✅ Head de Finanças: VALIDADO (Financial case + risk)
   Assinatura: CFO
   Data: 20/02/2026 18:00

✅ CTO/Eng Sr: VALIDADO (Technical feasibility)
   Assinatura: CTO
   Data: 20/02/2026 18:00

✅ ML Expert: VALIDADO (ML strategy + gates)
   Assinatura: ML_LEAD
   Data: 20/02/2026 18:00
```

---

## 📚 Como Usar Este Manifest

### Para Agentes Autônomos:

1. **Ao fazer qualquer mudança em um doc:**
   ```bash
   # Identifique documentos dependentes na seção "Mapa de Dependências"
   # Revise TODOS os documentos dependentes
   # Passe pelo checklist completo
   # Update "Histórico de Sincronização" com sua ação
   # Commit com mensagem clara: "docs: Sincronizacao <docs> - <reason>"
   ```

2. **Antes de fazer commit:**
   ```bash
   # Complete TODAS as sessões do checklist
   # Se algum item não passar → NÃO faça commit
   # Corrija o documento antes de tentar novamente
   ```

3. **Se sincronização quebrar:**
   ```bash
   # Edite este arquivo adicionando ao "Alertas de Sincronização"
   # Mensagem clara: qual doc está desatualizado e por quê
   # Bloqueie novos commits até resolver
   ```

---

## 🔄 Próxima Sincronização Planejada

**Data:** 21/02/2026 14:00 BRT (após Refinement Session)
**Tipo:** UPDATE (não breaking change esperado)
**Executores:** PO + Head Finanças + CTO + ML Expert
**Documentos Impactados:** copilot-instructions.md, SPRINT1_MASTERPLAN.md (possível)


# Atualização de Documentação — Prompt Refatorado

## 🎯 Objetivo
Manter sincronização e integridade referencial entre 11 documentos críticos do projeto.

---

## 📋 Documentos e Responsabilidades

| Doc | Propósito | Atualizar Quando |
|-----|-----------|-----------------|
| **ADRs.md** | Decisões arquiteturais registradas | Nova decisão de design importante |
| **ARCHITECTURE.md** | Arquitetura do sistema (evolução) | Mudança em componentes/módulos |
| **BACKLOG_UNIFICADO.md** | Status e progresso de atividades | Conclusão/início de tarefas |
| **CODING_STANDARDS.md** | Padrões de código e boas práticas | Nova regra de qualidade/style |
| **CONTRIBUTING.md** | Guia de contribuição (referencia CODING_STANDARDS) | Mudança em workflow/processo |
| **DATA_MODELS.md** | Modelo de dados (tabelas, campos, tipos) | Novo campo/tabela ou alteração de schema |
| **DIAGRAMA_CLASSES.md** | Diagrama de classes (UML/visual) | Nova classe ou refatoração estrutural |
| **DIAGRAMA_DADOS.md** | Diagrama ER (entidade-relacionamento) | Mudança na modelagem de dados |
| **MODELAGEM_DADOS.md** | Documentação técnica da modelagem | Evolução do DATA_MODELS.md |
| **README.md** | Visão geral do projeto (top-level) | Mudança em features, setup ou status |
| **REGRAS_NEGOCIO.md** | Regras em linguagem não-técnica | Nova regra ou mudança de lógica |
| **STATUS_ENTREGAS.md** | Cronograma e status de entregas | Mudança em prazos ou conclusão |

---

## 🔗 Mapa de Dependências (Impactos)

```
ARCHITECTURE.md (core)
  ├─→ ADRs.md (registra decisões)
  ├─→ DIAGRAMA_CLASSES.md (visual)
  └─→ CODING_STANDARDS.md (implementação)

DATA_MODELS.md (core)
  ├─→ DIAGRAMA_DADOS.md (visual)
  ├─→ MODELAGEM_DADOS.md (documentação tática)
  └─→ README.md (overview)

BACKLOG_UNIFICADO.md
  ├─→ STATUS_ENTREGAS.md (resumo status)
  └─→ README.md (seção "Status")

REGRAS_NEGOCIO.md
  ├─→ CODING_STANDARDS.md (implementar padrões)
  └─→ DATA_MODELS.md (validar estrutura)

CONTRIBUTING.md (implementação)
  └─→ CODING_STANDARDS.md (referencia)

README.md (agregador)
  ├─ Resumo de ARCHITECTURE.md
  ├─ Resumo de DATA_MODELS.md
  ├─ Link para CONTRIBUTING.md
  └─ Status de STATUS_ENTREGAS.md
```

---

## ✅ Checklist de Sincronização (EXECUTÁVEL)

Após **QUALQUER** mudança em documentação:

### Passo 1: Identificar Núcleo Alterado
- [ ] Qual documento foi editado?
- [ ] É um documento **CORE** (ARCHITECTURE, DATA_MODELS, BACKLOG)?
- [ ] É um documento **DEPENDENTE**?

### Passo 2: Mapear Impactos
Baseado no mapa acima, verificar documentos dependentes.

**Se ARCHITECTURE alterada:**
  - [ ] ADRs.md registra decisão?
  - [ ] DIAGRAMA_CLASSES.md reflete mudança?
  - [ ] CODING_STANDARDS.md precisa atualização?
  - [ ] README.md seção "Arquitetura" está sincronizado?

**Se DATA_MODELS alterada:**
  - [ ] DIAGRAMA_DADOS.md reflete nova schema?
  - [ ] MODELAGEM_DADOS.md documentação técnica atualizada?
  - [ ] README.md dados estrutura atualizada?

**Se BACKLOG_UNIFICADO alterada:**
  - [ ] STATUS_ENTREGAS.md reflete novo status?
  - [ ] README.md seção "Status" sincronizado?

**Se REGRAS_NEGOCIO alterada:**
  - [ ] CODING_STANDARDS.md implementação está confirmada?
  - [ ] DATA_MODELS.md validação está consistente?

**Se CONTRIBUTING alterada:**
  - [ ] README.md "Como Contribuir" aponta para novo localização?
  - [ ] CODING_STANDARDS.md linkado corretamente?

### Passo 3: Atualizar Documentos Impactados
- [ ] Para cada documento impactado, revisar conteúdo relevante
- [ ] Fazer updates incrementais (não reescrever tudo)
- [ ] Manter timestamps/versões quando aplicável

### Passo 4: Validação
- [ ] Cross-references entre docs estão válidas?
- [ ] Não há contradições nos conteúdos?
- [ ] Exemplos de código estão sincronizados?
- [ ] Links internos funcionam?

### Passo 5: Registrar Mudança
Adicionar entrada em BACKLOG_UNIFICADO.md:
```
- [DD/MM] atualiza_docs: {Doc1} + {Doc2} + {Doc3} sincronizados
  Motivo: {descrição breve}
  Impacto: {quais documentos foram atualizados}
```

---

## 🔄 Fluxo de Execução

```
1. EDITAR documento X
   ↓
2. IDENTIFICAR documentos dependentes (usar mapa acima)
   ↓
3. PARA CADA documento impactado:
   a. REVISAR seção relevante
   b. ATUALIZAR com mudanças
   c. VALIDAR cross-references
   ↓
4. REGISTRAR em BACKLOG_UNIFICADO.md
   ↓
5. VALIDAÇÃO FINAL:
   - Nenhuma contradição?
   - Links válidos?
   - Timestamps sincronizados?
   ↓
6. COMMIT: git commit -m "docs: Sincronizacao {Docs atualizados}"
```

---

## 📊 Critérios de Sucesso

✅ **Validação Automática (Checklist)**
- Todos os 11 documentos passam validação de sintaxe
- Nenhum link quebrado entre documentos
- Nenhuma contradição entre sections relacionadas

✅ **Completude**
- Documento núcleo atualizado
- Todos os documentos dependentes identificados
- Todos os documentos dependentes sincronizados

✅ **Consistência**
- Schema de dados reflete em todos os 3 diagramas
- Regras de negócio implementadas em CODING_STANDARDS
- Status em STATUS_ENTREGAS reflete BACKLOG_UNIFICADO
- README.md sempre reflete status atual

✅ **Documentação**
- Mudança registrada em BACKLOG_UNIFICADO.md
- Commit message clara e descritiva
- Nenhuma documentação órfã (não referenciada)

---

## 🚀 Exemplo Prático

**Cenário:** Nova field adicionada à tabela `orders` no banco.

**Execução:**

1. **EDITAR:** DATA_MODELS.md
   - Adicionar nova field à seção `orders`
   - Documentar tipo e propósito

2. **IMPACTOS IDENTIFICADOS:**
   - DIAGRAMA_DADOS.md (visual)
   - MODELAGEM_DADOS.md (documentação tática)
   - REGRAS_NEGOCIO.md (se field tem validação)
   - README.md (se mudança é relevante ao user)

3. **ATUALIZAR IMPACTADOS:**
   ```
   DIAGRAMA_DADOS.md: Adicionar field ao diagrama ER
   MODELAGEM_DADOS.md: Documentar nova field + constraints
   REGRAS_NEGOCIO.md: Validação se aplicável
   README.md: Atualizar schema summary se necessário
   ```

4. **VALIDAR:**
   - Toda referência à tabela `orders` está consistente?
   - Nenhuma contradição entre docs?

5. **REGISTRAR:**
   ```
   BACKLOG_UNIFICADO.md:
   - [05/03] atualiza_docs: DATA_MODELS + DIAGRAMA_DADOS + 
     MODELAGEM_DADOS sincronizados
     Motivo: Nova field 'execution_timestamp' em orders
     Impacto: Schema evolução + validações atualizadas
   ```

6. **COMMIT:**
   ```bash
   git commit -m "docs: Sincronizacao DATA_MODELS - nova field orders.execution_timestamp"
   ```

---

## ⚡ Instruções para Claude Haiku

**Quando receber task "atualiza_docs":**

1. **Parse:** Qual documento foi alterado? (identifique CORE ou DEPENDENTE)
2. **Map:** Use mapa de dependências para encontrar impactados
3. **Process:** Atualize cada impactado seguindo Passo 3
4. **Validate:** Use Validação (Passo 4)
5. **Register:** Registre em BACKLOG_UNIFICADO.md seguindo template
6. **Commit:** Mensagem clara indicando docs sincronizados

**Crítico:** Não reescreva documentos inteiros. Atualize apenas seções impactadas.

---

## 📌 Notas Importantes

- **Não é bloqueante:** Use checklist como guia, não impedimento
- **Incremental:** Atualizações pequenas e focadas
- **Transparência:** Sempre registrar mudanças em BACKLOG_UNIFICADO.md
- **Link Validation:** Antes de commit, validar que links internos funcionam
- **Version Control:** Usar timestamps/versões apenas em docs que evoluem frequentemente

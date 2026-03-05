# 📋 ROADMAP DE EXECUÇÃO - P0 + P1 READY

**Status Atual:** P0-URGENT-1 implementado e committed  
**Pronto para:** Próximo pregão (validação de produção)

---

## ⚡ SEQUÊNCIA DE ATIVIDADES IMEDIATAS

### 1. Revisar P0-URGENT-1 com Stakeholders
- [ ] ML Expert: Validar lógica de penalidade
- [ ] Head Finanças: Confirmar R$ 280/dia base
- [ ] CTO: Confirmar integração sem side effects
- [ ] Operador: Testar no ambiente staging
- **Tempo:** 45 min
- **Sucesso:** Aprovação de 3/4 personas

### 2. Deploy P0-URGENT-1 para Staging
- [ ] Backup versão anterior (data/db/trading.db.backup_05mar)
- [ ] Executar agent com P0-URGENT-1 ativo
- [ ] Validar logs (sem erros, penalidades sendo aplicadas)
- [ ] Monitorar primeiro ciclo
- **Tempo:** 30 min
- **Sucesso:** Agent rodando sem crashes

### 3. Notificar Equipe sobre P1-LEARNING
- [ ] Email para ML Expert: "P1-LEARNING planejado"
- [ ] Incluir: ROADMAP_P1_LEARNING.md
- [ ] Incluir: Reunião Eng Sr + ML para setup DB
- [ ] Confirmar disponibilidade equipe
- **Tempo:** 20 min
- **Sucesso:** Respostas de confirmação

---

## � Monitoramento Contínuo (Validação de Produção)

### Daily Standup (09:00 BRT):

```
✅ MÉTRICA CRÍTICA: Trades/dia
   Target: 0 → 2-3
   Validar: Logs com ENTER signals
   
✅ MÉTRICA CRÍTICA: Confidence Trend
   Target: Para de cair, começa subir
   Validar: Gráfico trend (não mais caindo)
   
✅ MÉTRICA CRÍTICA: Penalty Aplicada
   Target: Ativa em >120min sem trade
   Validar: Logs "INACTIVITY_PENALTY" presentes
   
✅ MÉTRICA CRÍTICA: Erros
   Target: Zero
   Validar: Nenhum exception ou crash
```

### Logs Esperados:

```
[09:15] IntraDayLearner initialized
[10:30] evaluate_opportunity: confidence=0.52
[10:50] INACTIVITY_PENALTY(LEVE): 127min inativo → penalidade -0.0310
[11:05] evaluate_opportunity: confidence=0.49 (adjusted -3.1%)
[11:45] → ENTER sinal (confidence 0.55 > threshold 0.50)
[11:46] ✓ Ordem executada! Ticket: 12345
[11:46] record_entry() → inactivity_penalty reset 0.0

[14:00] evaluate_opportunity: confidence=0.51
[14:55] INACTIVITY_PENALTY(LEVE): 130min inativo → penalidade -0.0315
[15:10] → HOLD (confidence insuficiente)
```

### Se Métricas OK:
- ✅ Continuar P0-URGENT-1 em produção
- ✅ Prosseguir para P1-LEARNING setup

### Se Problemas (trades ainda 0):
- [ ] Revisar lógica penalidade (expected behavior)
- [ ] Verificar threshold não está muito alto
- [ ] Considerar P0-URGENT-2: Forced Activation
- [ ] Call: ML Expert + CTO

---

## 🏗️ Preparação P1-LEARNING (Framework Causal)

### 1. Setup Infraestrutura DB

- [ ] Criar tabela: `causal_learning_episodes`
  - Campos: signal_detection, decision, monitoring, closure, analysis_L1, analysis_L2, causal_rules
  - Referência: ROADMAP_P1_LEARNING.md
- [ ] Criar índices (episode_id, timestamp, outcome)
- [ ] Validar conectividade SQLite
- **Owner:** Data Engineer
- **Tempo:** 2h

### 2. Setup Classes Python

- [ ] Criar `src/application/services/causal_learning_engine.py`
  - Stub das 7 funções (record_signal, record_decision, etc)
  - Tipo hints Pydantic
  - Docstrings com exemplos
- [ ] Criar `scripts/test_causal_learning.py`
  - 5 testes básicos (create, read, update)
  - Fixtures para dados de teste
- **Owner:** ML Expert
- **Tempo:** 3h

### 3. Revisar Documentação

- [ ] ROADMAP_P1_LEARNING.md (review final)
- [ ] ADR-010-CAUSAL_FEEDBACK_LOOP.md (validação)
- [ ] Criar 1-pager "Quick Reference" (visual)
- **Owner:** Tech Lead
- **Tempo:** 1h

---

## 🚀 P1-LEARNING Kick-off (Quando P0-URGENT-1 validado)

### Agenda (60 min):

```
00:00-10:00: Contexto + Objetivos
  ├─ Problema: Modelo aprende correlações, não causação
  ├─ Solução: 7-step causal loop
  └─ Benefício: Win rate +12% (60% → 72%)

10:00-25:00: Architecture Deep-dive
  ├─ 7 etapas + dados capturados
  ├─ Database schema
  └─ Integração com agente principal

25:00-45:00: Sprint Planning
  ├─ Etapas 1-5: Foundation
  ├─ Etapas 6-7: Causal Analysis + Rule Extraction
  ├─ Roles: ML Expert (Lead), Data Eng, QA
  └─ Checkpoints: Daily standup 15:00

45:00-60:00: Q&A + Start Coding
  ├─ Perguntas de design
  ├─ Setup environment
  └─ Primeiro commit de skeleton
```

### Deliverables Iniciais:
- [ ] CausalLearningEngine class (80-100 LOC)
- [ ] database schema + migrations
- [ ] 5+ unit tests (all passing)
- [ ] Integração hook no agente (record_signal_detection)
- [ ] Documentation update

### Gate Checkpoint:
```
Critério Validação:
  ✓ Etapas 1-5 capturando dados corretamente
  ✓ 5+ episódios de teste processados
  ✓ Testes de unit 5/5 passing
  ✓ Code review approved

Se NOT OK: Replan com ajustes
Se OK: Prosseguir Etapas 6-7
```

---

## 📊 Tracking & Sincronização

### Daily Updates:
```
Arquivo: outputs/RELATORIO_FECHAMENTO.md

Seção 1: Status P0-URGENT-1
  - Trades realizados
  - Confidence trend
  - Penalties applied
  - Issues/blockers

Seção 2: Status P1-LEARNING Prep
  - DB setup progress
  - Classes created
  - Tests ready
  - Blockers

Seção 3: Métricas
  - Model win rate vs benchmark
  - Operational costs
  - Sharpe ratio
```

### Sync Points:
- Daily 09:00: Team standup (métricas)
- Daily 15:00: Engineering sync
- Weekly: Executive review (blockers)

---

## ✅ Checklists de Validação

### Antes de Ativar P0-URGENT-1 em Produção:
- [ ] Backup completo de trading.db
- [ ] Verificação de syntax (py_compile OK)
- [ ] 10 testes passando (test_inactivity_penalty.py)
- [ ] Logs configurados para auditoria
- [ ] Threshold de confidence validado
- [ ] Operador testou em staging
- [ ] Rollback plan documentado
- [ ] Stakeholders aprovaram (3/4 personas)

### Após P0-URGENT-1 em Produção (Validação Contínua):
- [ ] Trades começam aparecer (0 → 2-3)
- [ ] Confidence para de cair
- [ ] Penalidades sendo aplicadas corretamente
- [ ] Nenhum erro ou crash nos logs
- [ ] Op costs começam reduzir

### Antes de P1-LEARNING Kick-off:
- [ ] DB infraestrutura pronta
- [ ] CausalLearningEngine stub criado
- [ ] 5 testes básicos passando
- [ ] Quick reference 1-pager ready
- [ ] ML Expert + Data Eng agenda confirmada
- [ ] Calendário bloqueado

---

## 🆘 Escalação & Contingência

### Se Problemas com P0-URGENT-1:
**Trades ainda 0 (após validação contínua):**
- [ ] Call: ML Expert (viés no modelo?)
- [ ] Call: CTO (penalidade funcionando?)
- [ ] Option: Trigger P0-URGENT-2 (Forced Activation)

**Agent crashed ou erros críticos:**
- [ ] Rollback para backup (trading.db.backup_05mar)
- [ ] Investigar logs de erro
- [ ] Reunião emergencial tech team

### Se P1-LEARNING Atrasado:
- [ ] Reduzir escopo (focar etapas 1-4)
- [ ] Extend timeline se necessário
- [ ] Ajustar recursos (contratar support)

---

## 🎯 Critérios de Sucesso

### P0-URGENT-1 (Validação Contínua):
- ✅ Trades/dia: 0 → 2-3
- ✅ Confidence: para de cair progressivamente
- ✅ Op costs: começam reduzir
- ✅ Modelo: quebra loop de inatividade
- ✅ Zero crashes ou erros críticos

### P1-LEARNING (Execução Completa):
- ✅ 7 etapas capturando dados estruturados
- ✅ 20+ episódios processados
- ✅ 5+ regras causais extraídas
- ✅ Backtest: +12% win rate vs correlacional
- ✅ Gate approval (todos os critérios)

---

**Próxima Review:** Daily standup 09:00  
**Owner:** GitHub Copilot + ML Expert + Data Analyzer  
**Status:** 🟢 READY FOR EXECUTION (Próximo pregão)

# 🚀 INICIAR AGORA - INSTRUÇÕES POR PASSO

**Leia este arquivo primeiro** - 5 minutos para entender o flow

---

## 📋 RESUMO DOS 7 PASSOS

```
PASSO 1 (45 min):  Revisar com stakeholders
├─ O quê?  Apresentar P0-URGENT-1, obter aprovação
├─ Quem?   ML Expert, Head Finanças, CTO
├─ Saída?  ✅ Aprovação de 3/4 personas

PASSO 2 (30 min):  Deploy para staging
├─ O quê?  Backup + validação + rodarlo agent em staging
├─ Quem?   Operador técnico
├─ Saída?  ✅ Agent rodando no staging

PASSO 3 (20 min):  Notificar equipe P1
├─ O quê?  Enviar email, agendar reunião
├─ Quem?   Tech lead
├─ Saída?  ✅ Confirmações recebidas

PASSO 4 (3-5 dias): Monitorar P0-URGENT-1
├─ O quê?  Daily standup, métricas (trades, confidence, penalties)
├─ Quem?   Operador + ML Expert
├─ Saída?  ✅ P0 validado, métricas OK

PASSO 5 (5-6h):  Preparar P1-LEARNING (paralelo)
├─ O quê?  DB schema + classes skeleton + testes
├─ Quem?   Data Engineer + ML Expert + QA
├─ Saída?  ✅ Infrastructure pronta

PASSO 6 (60 min): P1-LEARNING Kick-off
├─ O quê?  Reunião de planejamento, start coding
├─ Quem?   ML Expert + Data Engineer + QA
├─ Saída?  ✅ Etapas 1-5 começadas

PASSO 7 (5-8h):  Extrair regras causais
├─ O quê?  Implementar etapas 6-7, gerar + validar regras
├─ Quem?   ML Expert + Data Engineer
├─ Saída?  ✅ 5+ regras causais prontas
```

---

## 🎯 COMO COMEÇAR AGORA

### PASSO 1: Revisar P0-URGENT-1 HOJE (Próximas 2-3h)

**Prepare a apresentação:**
```
1. Abra: docs/features/inactivity-penalty/IMPLEMENTACAO_P0_URGENT_1.md
2. Leia: Problema + Solução + Evidência
3. Rode: python scripts/test_inactivity_penalty.py
4. Evidence: Screenshots dos testes passando
5. Prepare slides com: Problema (2min) + Solução (3min) + Evidência (5min) + Timeline (5min) + Risks (10min)
```

**Agende reunião:**
```
- Tempo: 45 min
- Participantes: ML Expert, Head Finanças, CTO, Operador
- Local: Video call ou presencial
- Objetivo: Aprovação para proceder com deploy
```

**Checklist pré-reunião:**
- [ ] Ler documentação
- [ ] Rodar testes
- [ ] Preparar slides
- [ ] Ter rollback plan escrito
- [ ] Contactar stakeholders 2h antes

---

### PASSO 2: Deploy Staging HOJE (30 min após aprovação P0)

**Copie-Cole nos Terminal (PowerShell):**

```powershell
# Passo 2.1: Backup
cd c:\repo\operador-day-trade-win
copy data\db\trading.db data\db\trading.db.backup_06mar
echo "✅ Backup criado"

# Passo 2.2: Validar syntax
python -m py_compile scripts/agente_micro_tendencia_winfut.py
python -m py_compile scripts/test_inactivity_penalty.py
echo "✅ Syntax OK"

# Passo 2.3: Rodar testes
python scripts/test_inactivity_penalty.py
echo "✅ Testes completados"

# Passo 2.4: Iniciar agent em staging (com simulator mode)
# IMPORTANTE: Edite config/settings.py → MT5_SIMULATOR_MODE = True
python scripts/agente_micro_tendencia_winfut.py

# Monitorar por 5-10 min (esperar INACTIVITY_PENALTY nos logs)
```

**Saída esperada:**
```
[09:15] IntraDayLearner initialized
[10:30] evaluate_opportunity: confidence=0.52
[10:50] INACTIVITY_PENALTY(LEVE): 127min inativo
✅ Se vir isso = está funcionando
```

---

### PASSO 3: Notificar Equipe HOJE (20 min)

**Use template de email:**

Abra: `outputs/7_PASSOS_PLANO_EXECUCAO.md` → Procure "PASSO 3: Email Padrão"

```
Copie texto → Cole no Outlook/Gmail → Envie para:
  - ML Expert
  - Data Engineer
  - QA Lead
```

**Saída esperada:**
```
Confirmação de recebimento + calendário bloqueado
```

---

### PASSO 4: Monitorar P0-URGENT-1 (PRÓXIMOS 3-5 DIAS)

**Cada dia 09:00 BRT:**

```powershell
# 1. Verificar que agent está rodando
Get-Process python | Select-Object -First 5

# 2. Ver logs (últimas 20 linhas)
Get-Content outputs/trading_*.log -Tail 20

# 3. Procurar por INACTIVITY_PENALTY
Select-String "INACTIVITY_PENALTY|ENTER|confidence" outputs/trading_*.log | Select-Object -Last 10

# 4. Contar trades hoje
(Select-String "Ordem executada" outputs/trading_*.log).Count
```

**Daily standup (template):**
```
Arquivo: outputs/DAILY_STANDUP_P0_URGENT1_[data].md

Métrica 1 - Trades/dia: [?] (target 2-3)
Métrica 2 - Confidence: [0.XX] (target: para de cair)
Métrica 3 - Penalties: [SIM/NÃO nos logs]
Métrica 4 - Erros: [0 ou lista]

Análise: ...
Próximas ações: ...
```

**Sucesso:** Após 3-5 dias com métricas OK → Prosseguir para PASSO 6

---

### PASSO 5: Preparar P1-LEARNING (PARALELO a PASSO 4)

**Time P1 começa hoje:**

```bash
# Data Engineer (2h):
1. Abra: outputs/7_PASSOS_PLANO_EXECUCAO.md → PASSO 5 - Infrastructure
2. Execute o SQL para criar tabela
3. Teste conexão: sqlite3 data/db/trading.db ".schema causal_learning_episodes"

# ML Expert (3h):
1. Crie arquivo: src/application/services/causal_learning_engine.py
2. Use skeleton do PASSO 5 como template (copy-paste + complete)
3. Commit quando pronto

# QA (3h):
1. Crie arquivo: scripts/test_causal_learning.py
2. Use skeleton do PASSO 5 (5 testes básicos)
3. Rode testes: pytest scripts/test_causal_learning.py
```

**Saída:**
```
Git commit: "feat: P1-LEARNING infrastructure skeleton"
```

---

### PASSO 6: P1-LEARNING Kick-off (QUANDO P0 VALIDADO)

**Assim que P0-URGENT-1 tiver 3-5 dias de sucesso:**

```
1. Agende reunião (60 min)
2. Use agenda do PASSO 6 (copy-paste slides)
3. Rode reunião com: ML Expert, Data Engineer, QA
4. Ao final: Primeiro commit de etapas 1-5
```

**Saída:**
```
Reunião realizada, sprint iniciado
```

---

### PASSO 7: Extrair Regras Causais (SEMANA 2 de P1)

**Após 5-8 dias de P1-LEARNING:**

```python
# ML Expert implementa etapas 6-7:
1. Etapa 6: analyze_causation() - compara contexto START vs END
2. Etapa 7: generate_causal_rule() - extrai regra estruturada
3. extract_causal_rules() - agrega 5+ regras válidas

Use código skeleton do PASSO 7 como template
Rode testes: pytest scripts/test_causal_learning.py
```

**Saída:**
```
✅ 5+ regras causais extraídas
✅ Backtest: +12% win rate
```

---

## 📌 ARQUIVO DETALHADO

Para detalhes de cada passo (instruções step-by-step, código, testes):

👉 **`outputs/7_PASSOS_PLANO_EXECUCAO.md`**

Cada passo tem:
- Descrição detalhada
- Código/SQL/exemplos prontos para copy-paste
- Checklist de conclusão
- Saída esperada

---

## 🚨 NEXT ACTION

**Imediatamente (próximas 2 horas):**

1. ✅ Leia este arquivo (você está aqui)
2. ⏳ Prepare apresentação para PASSO 1
3. ⏳ Agende reunião stakeholders
4. ⏳ Execute PASSO 1 (apresentação)
5. ⏳ Execute PASSO 2 (deploy staging)
6. ⏳ Execute PASSO 3 (notificar equipe)

**Próximas 3-5 dias:**
- Execute PASSO 4 (monitorar P0)
- Execute PASSO 5 em paralelo (preparar P1)

**Quando P0 validado:**
- Execute PASSO 6 (P1 kick-off)
- Execute PASSO 7 (regras causais)

---

## 📊 PROGRESSO VISUAL

```
[████████░░░░░░░░███] 50% COMPLETO
  ✅ P0-URGENT-1 implementado
  ✅ Documentação de 7 passos
  ⏳ Execução começar AGORA

PRÓXIMAS 24h: Passos 1-3
PRÓXIMAS 5 dias: Passos 4-5
PRÓXIMAS 2 semanas: Passos 6-7
```

---

**Tempo estimado para LER + ENTENDER:**
- Este arquivo: 5 min
- Arquivo detalhado (7_PASSOS): 20 min
- Total: 25 min

**Tempo p/EXECUTAR tudo (7 passos):**
- Passo 1: 45 min
- Passo 2: 30 min
- Passo 3: 20 min
- Passos 4-5 (paralelo): 3-5 dias
- Passo 6: 60 min
- Passo 7: 5-8 horas
- **Total: ~2 semanas** (com time paralelo)

---

## ✅ Você está pronto!

Próximo passo: **Prepare material para PASSO 1 (reunião com stakeholders)**

Dúvidas? Revise o arquivo `7_PASSOS_PLANO_EXECUCAO.md` (muito detalhado)

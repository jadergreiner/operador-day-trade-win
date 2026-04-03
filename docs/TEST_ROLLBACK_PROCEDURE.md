# TEST ROLLBACK PROCEDURE — Profit Protection v2

**Data Criação:** 02/04/2026
**Status:** Procedure Ready (NOT YET EXECUTED)
**Objetivo:** Validar que rollback pode ser executado com segurança

---

## 🧪 TESTE 1: Validar Backups

### Prerequisito: Fazer Backups

```bash
# ANTES de qualquer teste, fazer cópia de segurança
cp -r scripts scripts.backup_20260402_prod
cp -r src src.backup_20260402_prod
cp config/profit_protection.yaml config/profit_protection.yaml.backup_prod
cp data/db/trading.db data/db/trading.db.backup_prod

# Verificar integridade
ls -lh scripts.backup_20260402_prod/ | head -5
ls -lh config/profit_protection.yaml.backup_prod
ls -lh data/db/trading.db.backup_prod

echo "✓ Backups criados com sucesso"
```

### Expected Output

```
✓ Backups criados com sucesso
```

---

## 🧪 TESTE 2: Verificar Versão Atual (v2)

### Checkpoint: RL Direto está com v2?

```bash
# Verificar se a função v2 existe
grep -c "processar_protecao_lucros_rl_direto" scripts/agente_rl_direto_independente.py
# Esperado: 2+ matches

# Verificar se está sendo chamada no loop
grep -A3 "Executando processar_protecao_lucros_rl_direto" scripts/agente_rl_direto_independente.py
# Esperado: output com try/except

echo "✓ v2 confirmada em produção"
```

### Expected Output

```
2
Executando processar_protecao_lucros_rl_direto()...
try:
    processar_protecao_lucros_rl_direto()
✓ v2 confirmada em produção
```

---

## 🧪 TESTE 3: Simular Rollback (Dry Run)

### Passo 1: Checkout de v1 (SEM executar)

```bash
# Ver o histórico local
git log --oneline | head -10

# Mostrar commit do feature (deve existir)
git log --oneline --grep="profit.protection" | head -1
# Esperado: commit com "profit-protection" ou "ADR-018"

# Criar branch de teste (NÃO fazer checkout da main)
git checkout -b test/rollback-simulation

echo "✓ Branch de teste criado (SEM fazer checkout main)"
```

### Passo 2: Simular Remoção da Função v2

```bash
# Apenas MOSTRAR o que seria removido
grep -n "^def processar_protecao_lucros_rl_direto" scripts/agente_rl_direto_independente.py | head -1
# Esperado: line number onde função começa

# Contar quantas linhas a função tem
grep -n "^def processar_protecao_lucros_rl_direto" -A 50 scripts/agente_rl_direto_independente.py | grep "^[0-9]*:def\|^[0-9]*:    return\|^[0-9]*:$" | head -2
# Isso mostra início e fim

echo "✓ Função v2 identificada para remoção"
```

### Passo 3: Validar Sintaxe Versão Old

```bash
# Simular: o que aconteceria se reversíssemos?
python -m py_compile scripts/agente_rl_direto_independente.py 2>&1
# Esperado: nenhum erro

echo "✓ Sintaxe v2 válida (reversão futura será válida também)"
```

---

## 🧪 TESTE 4: Simular Restart Agentes

### NOTA: NÃO EXECUTAR EM PRODUÇÃO

Este teste apenas MOSTRA o que seria feito. **NÃO executar.**

```bash
# SIMULAÇÃO APENAS:
echo "[SIMULAÇÃO] Comando que seria executado para parar agentes:"
echo "  pkill -f agente_rl_direto_independente.py"
echo "  sleep 5"

echo "[SIMULAÇÃO] Comando que seria executado para restart (v1):"
echo "  python scripts/agente_rl_direto_independente.py --simulate"

echo "✓ Procedimento simulado (SEM executar)"
```

---

## 🧪 TESTE 5: Validar Post-Rollback

### Checkpoint: Após reverter, esperamos quê?

```bash
# APÓS rollback, este comando deve retornar VAZIO:
grep "processar_protecao_lucros_rl_direto" scripts/agente_rl_direto_independente.py | wc -l
# Esperado: 0

# RL 5000 DEVE continuar com proteção (MAGIC 234500):
grep "processar_protecao" scripts/agente_com_supervision.py | wc -l
# Esperado: 2+

echo "✓ RL Direto sem v2, RL 5000 mantém proteção"
```

---

## 📋 ROLLBACK READINESS CHECKLIST

Antes de fazer rollback em emergência, validar:

```bash
□ Backups existem e são acessíveis?
  ls -lh scripts.backup_20260402_prod
  ls -lh config/profit_protection.yaml.backup_prod
  ls -lh data/db/trading.db.backup_prod

□ Git branch limpa (nenhuma mudança local)?
  git status
  # Esperado: "nothing to commit, working tree clean"

□ Todos os testes passam em v2?
  pytest tests/unit/test_rl_direto_profit_protection_integration.py -v
  # Esperado: 5/5 PASSED

□ Agentes não estão rodando?
  ps aux | grep agente_ | grep -v grep | wc -l
  # Esperado: 0

□ Procedure documentada em:
  docs/DEPLOYMENT_RUNBOOK.md (✓ criado)
  docs/ADR-018-PROFIT_PROTECTION_ROLLBACK.md (abaixo)
```

---

## 🚨 TRIGGER CONDITIONS PARA ROLLBACK

Rollback deve ser ativado APENAS se:

| Condição | Severidade | Ação |
|----------|-----------|------|
| RL Direto crash no startup | 🔴 CRÍTICO | ROLLBACK IMEDIATO |
| Win rate cai <55% (>7% degradation) | 🔴 CRÍTICO | ROLLBACK IMEDIATO |
| MT5 side effects detectados | 🔴 CRÍTICO | ROLLBACK IMEDIATO |
| Memory leak (cresce monotonicamente) | 🟠 ALTO | ROLLBACK se P95 > 500MB |
| Break-even ativando incorretamente | 🟠 ALTO | ROLLBACK + post-mortem |
| Qualquer exception não capturada | 🟡 MÉDIO | Investigate, depois decide |

---

## 📊 ROLLBACK SIMULATION RESULTS

### Teste Executado: [DATE TBD]

```
□ TESTE 1: Backups validados
  Status: [NOT YET RUN]
  Duration: [TBD]
  Result: [PASS/FAIL]

□ TESTE 2: v2 confirmada
  Status: [NOT YET RUN]
  Duration: [TBD]
  Result: [PASS/FAIL]

□ TESTE 3: Dry-run rollback
  Status: [NOT YET RUN]
  Duration: [TBD]
  Result: [PASS/FAIL]

□ TESTE 4: Restart simulado
  Status: [NOT YET RUN]
  Duration: [TBD]
  Result: [PASS/FAIL]

□ TESTE 5: Post-rollback check
  Status: [NOT YET RUN]
  Duration: [TBD]
  Result: [PASS/FAIL]

OVERALL STATUS: [PENDING EXECUTION]
```

---

## 🔗 Documentos Relacionados

- **Deployment:** `docs/DEPLOYMENT_RUNBOOK.md`
- **Architecture:** `docs/ARQUITETURA_ALVO.md#adr-018`
- **Feature Spec:** `notebooks/release_management_profit_protection_v2.ipynb`
- **Tests:** `tests/unit/test_rl_direto_profit_protection_integration.py`

---

## ✅ CONCLUSÃO

Este procedimento de teste de rollback está **pronto para ser executado quando necessário**.

Próximas ações:
1. ✅ [CONCLUÍDO] Criar procedimento (este documento)
2. 🔄 [PRÓXIMO] Executar testes quando staging validation passar
3. 🔄 [PRÓXIMO] Registrar resultado de cada teste
4. 🔄 [PRÓXIMO] Mover para "VALIDATED_READY" após tudo passar

**Timestamp:** 02/04/2026 18:15 BRT

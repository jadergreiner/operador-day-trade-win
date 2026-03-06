# 📋 PASSO 4 - MONITORAR P0-URGENT-1 (3-5 dias)

**Status:** 🟢 Pronto para iniciar
**Duração:** 3-5 dias (07/03 - 11/03)
**Daily Time:** 5 minutos por dia

---

## 🚀 COMO USAR

### Diariamente (5 min):
```bash
python scripts/monitorar_p0_diario.py
```

Isso vai:
- ✅ Checar logs do dia
- ✅ Contar penalties aplicadas
- ✅ Contar trades executados
- ✅ Contar erros
- ✅ Salvar histórico em JSON
- ✅ Mostrar trend (📈 / → / 📉)

---

## 📊 MÉTRICAS A RASTREAR

### Métrica 1: INACTIVITY PENALTIES
```
Target: > 0 (deve estar sendo aplicada)
Status: ✅ OK se > 0, ⚠️ AVISO se = 0

O que procurar nos logs:
  INACTIVITY_PENALTY(LEVE|MÉDIA|CRÍTICA)
  PENALTY: -3.1%
  PENALTY: -5.0%
```

### Métrica 2: TRADES
```
Target: 2-3 por semana (começando 0)
Status: 📈 SUBINDO se > 0, → ESTÁVEL se = 0

O que procurar:
  TRADE executado
  ORDEM enviada
  Position opened
```

### Métrica 3: CONFIDENCE
```
Target: Parou de cair (0.46 → ?)
Status: 📈 SUBINDO, → ESTÁVEL, 📉 CAINDO

O que verificar:
  confidence: 0.46
  confidence: 0.47
  confidence: 0.48
```

### Métrica 4: ERROS
```
Target: 0 (zero)
Status: ✅ OK se = 0, ❌ CRÍTICO se > 0

O que procurar:
  ERROR
  ERRO
  Exception
  Traceback
```

---

## 📅 DAILY STANDUP TEMPLATE (Copy-Paste)

**Use esse template cada dia:**

```
📊 DAILY STANDUP - P0-URGENT-1
Data: [DD/MM/YYYY]
Hora: [HH:MM]

Penalties:        [SIM/NÃO] - [quantidade]
Trades:           [quantidade]
Confidence:       [0.XX] - [📈/→/📉]
Erros:            [quantidade]

Status: [🟢 OK / 🟡 AVISO / 🔴 CRÍTICO]

Observações:
  [Descrever comportamento anormal se houver]

Próximas ações:
  [ ] Rodar script novamente amanhã
  [ ] [Qualquer ação manual necessária]
```

---

## 🔍 COMO VER OS LOGS

### Opção 1: Via script (RECOMENDADO)
```bash
python scripts/monitorar_p0_diario.py
```

### Opção 2: Via PowerShell (detalhado)
```powershell
# Ver logs em tempo real
Get-Content outputs/agent_execution.log -Wait

# Procurar por penalties
Select-String "PENALTY|INACTIVITY" outputs/agent_execution.log | Select-Object -Last 10

# Procurar por trades
Select-String "TRADE|ORDEM" outputs/agent_execution.log | Select-Object -Last 10

# Procurar por erros
Select-String "ERROR|ERRO|Exception" outputs/agent_execution.log | Select-Object -Last 5
```

### Opção 3: Via Python (interativo)
```python
import json
from pathlib import Path

# Ver histórico
with open('outputs/PASSO_4_ACOMPANHAMENTO_DIARIO.json') as f:
    history = json.load(f)

# Mostrar últimos 3 dias
for date in sorted(history.keys())[-3:]:
    print(f"{date}: {history[date]}")
```

---

## 📋 CHECKLIST (3-5 dias)

### Dia 1 (07/03 - Quinta):
- [ ] 09:00 - Rodar script monitorar_p0_diario.py
- [ ] Confirmar penalties sendo aplicadas
- [ ] Checar se erros = 0
- [ ] Salvar resultado em PASSO_4_ACOMPANHAMENTO_DIARIO.json

### Dia 2 (08/03 - Sexta):
- [ ] 09:00 - Rodar script novamente
- [ ] Comparar com dia 1
- [ ] Confidence está subindo?
- [ ] Trades começaram?

### Dia 3 (09/03 - Sábado):
- [ ] 09:00 - Rodar script
- [ ] Trend (📈 / → / 📉)?
- [ ] Erros persistentes?
- [ ] Qualidade dos trades?

### Dia 4 (10/03 - Domingo):
- [ ] 09:00 - Rodar script
- [ ] Consolidar dados de 4 dias
- [ ] Preparar análise para gate

### Dia 5 (11/03 - Segunda):
- [ ] 09:00 - Rodar script (última coleta)
- [ ] Gate decision meeting
- [ ] GO → P1-LEARNING
- [ ] NO-GO → Root cause + fix

---

## 🎯 GATE DECISION (11/03)

**Critérios GO (proceed com P1-LEARNING):**
- ✅ Penalties sendo aplicadas consistentemente
- ✅ Confidence parou de cair (0.46+)
- ✅ Trades começaram (1-3+ durante os 5 dias)
- ✅ Zero erros críticos
- ✅ Agent rodando estável (sem crashes)

**Critérios NO-GO (retry/fix):**
- ❌ Penalties não aparecendo nos logs
- ❌ Confidence continua caindo (0.44 ou menos)
- ❌ Trades zerados
- ❌ Erros críticos frequentes
- ❌ Agent crashing

---

## 📊 HISTÓRICO AUTOMÁTICO

Script salva histórico em:
```
outputs/PASSO_4_ACOMPANHAMENTO_DIARIO.json
```

Formato:
```json
{
  "07/03/2026": {
    "timestamp": "2026-03-07T09:00:00",
    "penalties": 5,
    "trades": 1,
    "errors": 0,
    "status": "OK"
  },
  "08/03/2026": {
    ...
  }
}
```

---

## 🚨 SE ALGO DER ERRADO

### Penalties não aparecendo:
- Verificar: Agent rodando? `Get-Process python`
- Verificar: Log sendo gerado? `ls outputs/agent_*.log`
- Ação: Relançar agent via `INICIAR_MICRO_TENDENCIA_AUTO_TRADE.bat`

### Erros no agent:
- Verificar: Qual é o erro? `Select-String "ERROR" outputs/agent_execution.log`
- Ação: Read logs → debug → fix → relançar

### Confidence caindo mais:
- Isso significa P0 não funcionou como esperado
- Ação: Revisar lógica de penalidade
- Fallback: Rollback via `trading.db.backup_06mar.bkp`

### Trades zerados:
- Pode ser normal no início
- Esperar até dia 3-5
- Se persistir: Revisar threshold de confiança

---

## ✅ CHECKLIST FINAL (Dia 5)

```
Depois de 5 dias, preencha:

[ ] Penalties funcionando?        (SIM/NÃO)
[ ] Confidence subiu?             (SIM/NÃO)
[ ] Trades aumentaram?            (SIM/NÃO)
[ ] Erros críticos?               (SIM/NÃO)
[ ] Agent estável?                (SIM/NÃO)

Resultado:
  [ ] GO → Launch P1-LEARNING
  [ ] NO-GO → Root cause analysis
  [ ] RETRY → Ajustar + repeat
```

---

## 📞 RESUMO

**PASSO 4 é SIMPLES:**
1. Rodar `python scripts/monitorar_p0_diario.py` cada dia (5 min)
2. Anotar métricas (penalties, trades, confidence, errors)
3. Após 5 dias: Decidir GO/NO-GO

**Se tudo ok:** Proceed P1-LEARNING
**Se problem:** Debug + fix + retry

---

**Timestamp:** 06/03/2026 21:00 BRT
**Status:** 🟢 PASSO 4 TEMPLATE PRONTO
**Próximo:** Executar diariamente por 3-5 dias (07-11/03)

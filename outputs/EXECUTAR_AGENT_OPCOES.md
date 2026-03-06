# 🚀 EXECUTAR AGENT - OPÇÕES DE INICIALIZAÇÃO

**Atualizado:** 06/03/2026
**Status:** ✅ P0-URGENT-1 Inactivity Penalty integrado

---

## 📋 3 FORMAS DE INICIAR O AGENT

### **Opção 1: Via BAT File OFICIAL da Raiz (RECOMENDADO)**

```batch
cd c:\repo\operador-day-trade-win
INICIAR_MICRO_TENDENCIA_AUTO_TRADE.bat
```

**Localização Oficial:** `c:\repo\operador-day-trade-win\INICIAR_MICRO_TENDENCIA_AUTO_TRADE.bat`
**Versão:** v1.2.3 (26/02/2026) - Full integration avec BDI + SMC + ML + P0-URGENT-1

**O que faz:**
- ✅ Inicia em background automaticamente
- ✅ Carrega ML models (LightGBM F1: 0.5664, IntraDayLearner)
- ✅ Aplica P0-URGENT-1 (Inactivity Penalty System)
- ✅ Valida health checks pré-voo (P50-A: pessimismo, P50-B: retraining, P50-C: feedback logger)
- ✅ Ativa BDI Detection (v1.2.0)
- ✅ Ativa SMC Confluence validation (M1/M5)
- ✅ Salva logs em `outputs/agent_auto_trade_YYYYMMDD_HHMM.log`
- ✅ REST API disponível (porta 8000, auto-startup)
- ✅ Não bloqueia o terminal
- ✅ Pronto para monitoramento

**Saída esperada:**
```
[*] Sessao ID: 51/52 iniciada
[-] IntraDayLearner: Ativo
[*] LightGBM: Carregado (F1: 0.5664, Accuracy: 59.55%)
[!] P0-URGENT-1: Inactivity Penalties ATIVA
[*] BDI Detection: Ativo
[i] Terminal CLEAR: Pronto para negocios (isolado)
Agent iniciado (PID: 29724 | 31872)
Logs: outputs/agent_auto_trade_20260306_2010.log

Para monitorar:
  Get-Content outputs/agent_auto_trade_20260306_2010.log -Wait
```

---

### **Opção 2: Via PowerShell (Terminal Window - Para Debug)**

```powershell
cd c:\repo\operador-day-trade-win
python scripts/agente_micro_tendencia_winfut.py
```

**O que faz:**
- ✅ Executa no terminal onde você vê os logs em tempo real
- ✅ Útil para debug e desenvolvimento
- ✅ Bloqueia o terminal enquanto roda
- ⚠️ Mais lento (overhead de terminal)

**Saída esperada:**
```
[*] Sessao ID: 51 iniciada
[-] IntraDayLearner: Ativo
✅ LightGBM Integrator: Ativo (F1: 0.5664)
```

---

### **Opção 3: Via PowerShell Script (Background com Logging)**

```powershell
cd c:\repo\operador-day-trade-win
$process = Start-Process python `
  -ArgumentList "scripts/agente_micro_tendencia_winfut.py" `
  -RedirectStandardOutput "outputs/agent_staging.log" `
  -PassThru -NoNewWindow

Write-Host "Agent iniciado (PID: $($process.Id))"
Write-Host "Logs: outputs/agent_staging.log"
```

**O que faz:**
- ✅ Inicia em background (não bloqueia terminal)
- ✅ Logs salvos em arquivo
- ✅ Máximo controle
- ⚠️ Requer conhecimento de PowerShell

---

## 🎯 QUAL ESCOLHER?

| Situação | Recomendado |
|----------|-------------|
| **Iniciar e esquecer** | Opção 1 (BAT file) |
| **Debug/Desenvolvimento** | Opção 2 (Terminal) |
| **Automação avançada** | Opção 3 (PowerShell) |

---

## 📊 ARQUIVOS BAT DISPONÍVEIS

### Oficial (Raiz do Projeto):
```
INICIAR_MICRO_TENDENCIA_AUTO_TRADE.bat    ← OFICIAL (v1.2.3, 26/02/2026)
   └─ Localização: c:\repo\operador-day-trade-win\INICIAR_MICRO_TENDENCIA_AUTO_TRADE.bat
   └─ Integrações: BDI + SMC + ML + P0-URGENT-1 + P50-A/B/C
   └─ Status: 🟢 PRODUCTION-READY (use este arquivo)
```

### Extras em Subdirectório (BAT/):
```
BAT/INICIAR_MICRO_TENDENCIA_AUTO_TRADE.bat
   └─ ⚠️ Versão criada por agente (duplica função do oficial)
   └─ Status: ❌ DEPRECATED (usar arquivo da raiz em vez disso)

INICIAR_AGENTE_MICRO_TENDENCIA.bat
   └─ Versão original (terminal window)

INICIAR_TRADING_AUTOMATICO.bat
   └─ Modo auto-trade completo

INICIAR_AGENTE_WDO_WINFUT.bat
   └─ Sem loop automático

INICIAR_AGENTE_WDO_WINFUT_LOOP.bat
   └─ Com loop automático
```

**⚡ RECOMENDAÇÃO:** Use sempre o arquivo raiz `INICIAR_MICRO_TENDENCIA_AUTO_TRADE.bat`

---

## 🔍 MONITORAR AGENT RODANDO

Depois de iniciar via qualquer opção:

### Ver logs em tempo real:
```powershell
Get-Content outputs/agent_auto_trade_*.log -Wait
```

### Procurar por P0-URGENT-1 (Inactivity Penalty):
```powershell
Select-String "INACTIVITY" outputs/agent_*.log
```

### Ver status do processo:
```powershell
Get-Process python | Select-Object Id, ProcessName, CPU, @{Name="Memory";Expression={"{0:N0} MB" -f ($_.WorkingSet/1MB)}}
```

### Parar agent:
```powershell
Get-Process python | Stop-Process -Force
```

---

## 📋 CHECKLIST PRÉ-EXECUÇÃO

Antes de executar:

- [ ] `.env` configurado com MT5_LOGIN, MT5_PASSWORD, MT5_SERVER
- [ ] `MT5_TERMINAL_PATH` aponta para CLEAR (não FBS/XP)
- [ ] Python 3.11 instalado em `C:\Users\Usuario\AppData\Local\Programs\Python\Python311\`
- [ ] Database `data/db/trading.db` existe (ou será criado automaticamente)
- [ ] Pasta `outputs/` existe (será criada se não existir)

---

## 🎯 FLUXO DE EXECUÇÃO

### Via INICIAR_MICRO_TENDENCIA_AUTO_TRADE.bat:

```
1. User duplo-clica no BAT
   ↓
2. BAT detecta Python path
   ↓
3. PowerShell inicia agent em background
   ↓
4. Log file criado (outputs/agent_auto_trade_YYYYMMDD_HHMM.log)
   ↓
5. Agent roda com P0-URGENT-1 integrado
   ↓
6. Terminal fecha (execução em background)
   ↓
7. User monitora via Get-Content logs
```

---

## 📊 LOG EXEMPLO

```
Database created at: data/db/trading.db
[*] Sessao ID: 51 iniciada
[-] IntraDayLearner: Ativo (latencia ~10min)
✅ LGBM: Modelo carregado [lgbm_classification_latest.pkl]
[*] LightGBM Integrator: Ativo (F1: 0.5664, Acc: 59.55%)
[PRE-FLIGHT] Auditando terminal MT5...
✅ Terminal CLEAR pronto
══════════════════════════════════════════════════════════════════════
  AGENTE MICRO TENDENCIA WINFUT — Day Trade B3
  Ciclo: 2min │ Horário: 09:00-17:55 │ Símbolo: WIN$N
══════════════════════════════════════════════════════════════════════
⏸ Fora do horário de pregão. Aguardando...
```

---

## ✅ VALIDAÇÕES

**P0-URGENT-1 está sendo executado quando você vê:**
```
INACTIVITY_PENALTY(LEVE): XXXmin inativo → penalidade -0.0XX
```

**LightGBM está ativo quando você vê:**
```
LightGBM Integrator: Ativo (F1: 0.5664, Acc: 59.55%)
```

**Terminal MT5 está conectado quando você vê:**
```
✅ Terminal CLEAR pronto. Path: C:\Program Files\Clear...
```

---

## 🔥 PRÓXIMOS PASSOS

### Imediato:
1. Escolha uma das 3 opções acima
2. Inicie o agent
3. Monitore por 10-15 min

### Depois:
1. Proceder para **PASSO 3: Notificar Equipe**
2. Atualizar CHECKLIST
3. Começar PASSO 4 (monitoramento contínuo)

---

## 📝 NOTAS DE VERSÃO

**06/03/2026 - P0-URGENT-1 Release:**
- ✅ Novo BAT file: `INICIAR_MICRO_TENDENCIA_AUTO_TRADE.bat`
- ✅ Execução em background com PowerShell nativo
- ✅ Logging automático com timestamp
- ✅ P0-URGENT-1 (Inactivity Penalty) integrado
- ✅ Encoding UTF-8 para suportar caracteres especiais
- ✅ Monitoramento fácil via PowerShell Get-Content

---

**Recomendação:** Use `INICIAR_MICRO_TENDENCIA_AUTO_TRADE.bat` para all novo deployments.

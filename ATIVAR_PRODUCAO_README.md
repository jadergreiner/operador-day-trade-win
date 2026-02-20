# 🚀 ATIVAR AGENTE EM PRODUÇÃO

Scripts para ativar o agente Phase 7 (Execução Automática) em produção **AGORA** com 1 contrato WIN$N.

---

## 📋 Opções de Execução

### **Opção 1: PowerShell (RECOMENDADO) ⭐**

**Mais robusto, melhor feedback, funciona perfeitamente.**

```powershell
# Abrir PowerShell como Administrador
# Navegue até:
cd c:\repo\operador-day-trade-win

# Executar (modo teste - apenas validação):
powershell -ExecutionPolicy Bypass -File .\Ativar-Producao.ps1 -TestOnly

# Executar (modo ativação normal - com menu):
powershell -ExecutionPolicy Bypass -File .\Ativar-Producao.ps1

# Executar (modo força - ativa direto sem confirmação):
powershell -ExecutionPolicy Bypass -File .\Ativar-Producao.ps1 -Force
```

**O que faz:**
```
[01/10] Verifica Python + Git
[02/10] Valida estrutura do projeto
[03/10] Instala dependências
[04/10] Roda testes (MT5, Risk, Orders)
[05/10] Cria config de produção
[06/10] Prepara logs
[07/10] Menu interativo

Depois você escolhe:
  [1] INICIAR AGORA (Abre 5 terminais)
  [2] Rodar testes antes
  [3] Mostrar status
  [4] Cancelar
```

---

### **Opção 2: CMD Batch (ALTERNATIVA)**

**Se PowerShell tiver problemas, use:**

```cmd
cmd.exe
cd c:\repo\operador-day-trade-win
ATIVAR_PRODUCAO_AGORA.bat
```

---

## 🎯 Modo Recomendado (Primeira Ativação)

1. **Abrir PowerShell como Admin**
   ```
   Windows + X → PowerShell (Admin)
   ```

2. **Navegar ao projeto**
   ```powershell
   cd c:\repo\operador-day-trade-win
   ```

3. **Executar em modo teste (validar tudo funciona)**
   ```powershell
   powershell -ExecutionPolicy Bypass -File .\Ativar-Producao.ps1 -TestOnly
   ```

   Output esperado:
   ```
   [OK] Python
   [OK] Git
   [OK] estrutura do projeto
   [OK] Dependencias instaladas
   [OK] MT5Adapter validado
   [OK] RiskValidator validado
   [OK] OrdersExecutor validado
   [OK] Config de producao criada
   [OK] Pasta logs criada
   [OK] Sistema pronto para producao
   [OK] Modo teste ativado - saindo sem iniciar
   ```

4. **Se tudo OK, executar modo normal**
   ```powershell
   powershell -ExecutionPolicy Bypass -File .\Ativar-Producao.ps1
   ```

   Menu aparecerá:
   ```
   OPCOES DE ATIVACAO:

      [1] INICIAR AGORA (Producao - 1 contrato ao vivo)
      [2] Rodar testes antes
      [3] Apenas mostrar status
      [4] Cancelar
   ```

5. **Escolher [1] para iniciar**

---

## 📊 O que Acontece ao Iniciar [1]

**Aviso de confirmação:**
```
AVISO CRITICO:
   - Capital REAL: R$ 5.000
   - Max perda: R$ 100 (-2 por cento = HALT automatico)
   - Trader DEVE monitorar 24h
   - Kill switch: Ctrl+C em qualquer terminal

Confirmar ativacao? (S/N):
```

**Se confirmar (S), abre 5 terminais:**
```
[Terminal 1] Iniciando MT5Adapter       (Orders)
[Terminal 2] Iniciando RiskValidator    (Validacao)
[Terminal 3] Iniciando OrdersExecutor   (State machine)
[Terminal 4] Iniciando Detector BDI     (Oportunidades)
[Terminal 5] Iniciando Dashboard        (Monitoramento)
```

**Depois abre browser em:**
```
http://localhost:8765/dashboard
```

---

## ⚙️ Configuração Gerada

**Arquivo:** `config\producao_20feb_v1.yaml`

```yaml
capital:
  inicial: 5000
  max_contracts: 1
  max_loss_daily: -100        # -2% = R$ 100
  circuit_breaker: -150       # -3% = halt

asset:
  symbol: WIN$N
  timeframe: 5m

ml_classifier:
  confidence_threshold: 0.90  # 90% = máximo conservador

execution:
  auto_trade: true
  order_timeout: 60

monitoring:
  trader_required: true       # OBRIGATORIO MONITORAR
```

---

## 🔴 Kill Switch (Emergência)

**Para parar TUDO imediatamente:**

**Opção 1 (Em qualquer terminal):**
```
Ctrl + C
```

**Opção 2 (PowerShell):**
```powershell
Get-Process python | Stop-Process -Force
```

**Opção 3 (CMD):**
```cmd
taskkill /F /IM python.exe
```

---

## 📋 Logs e Monitoramento

**Pasta de logs:**
```
logs\producao\
```

**Arquivos gerados:**
- `audit_*.jsonl` - Audit trail de cada ordem (CVM compliant)
- `mt5_adapter.log` - Log do MT5
- `risk_validator.log` - Log do validador de risco
- `detector.log` - Log do detector de oportunidades

**Dashboard:**
```
http://localhost:8765/dashboard
```

---

## ⏱️ Próximas Ações

```
21/02 08:00:  Trader começa monitoramento 24h
27/02 14:00:  SPRINT 1 kickoff (integração + ML treino em paralelo)
05/03 18:00:  GATE 1 review (validação com dados reais)
12/03:        GATE 2 (ML Sharpe > 1.0)
10/04:        GO LIVE com 50k capital
```

---

## ❓ Troubleshooting

### **Erro: "Python não found"**
```
Solução: Instale Python 3.9+ de https://www.python.org
```

### **Erro: "MT5 Gateway não está rodando"**
```
Solução: Verifique se MT5 REST Gateway está inicializado
         Porta esperada: http://localhost:8000/api/v1/health
```

### **Erro: "Permissão negada no PowerShell"**
```powershell
# Abra PowerShell como Administrador antes de executar
```

### **Script lento na primeira execução**
```
Normal! pytest está descobrindo e instalando dependências
Próxima execução será rápida
```

---

## ✅ Checklist Antes de Ativar

- [ ] MT5 Gateway está rodando?
- [ ] Trader vai monitorar 24h?
- [ ] Capital R$ 5k disponível?
- [ ] CFO aprovou?
- [ ] Você aceita perda até R$ 100 (-2%)?
- [ ] PowerShell tem permissão de Admin?

**Se TODOS forem SIM → Execute o script**

---

**Status:** ✅ PRONTO PARA ATIVAR

Dúvidas? Verifique documentation:
- [SPRINT1_DAY1_KICKOFF.md](docs/agente_autonomo/SPRINT1_DAY1_KICKOFF.md)
- [ARQUITETURA PHASE 7](docs/agente_autonomo/AGENTE_AUTONOMO_ARQUITETURA.md)

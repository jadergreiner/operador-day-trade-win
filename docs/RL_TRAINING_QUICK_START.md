# ⚡ RL Training Scheduler - Quick Start

## 📦 Instalação (30 segundos)

### Windows - CMD/PowerShell

```bash
# Setup rápido (instala dependências)
SETUP_RL_QUICK.bat

# Ou manual
pip install apscheduler
```

### Linux/Mac

```bash
pip install apscheduler
mkdir -p logs data/db
```

## 🚀 Iniciar

### Opção 1: Menu Interativo (Recomendado)

**Windows (PowerShell):**
```powershell
.\INICIAR_RL_SCHEDULER.ps1
```

**Windows (CMD):**
```cmd
INICIAR_RL_SCHEDULER.bat
```

Menu oferece:
- ▶️ Iniciar scheduler (background)
- 🧪 Teste rápido
- 📊 Verificar saúde
- 📋 Ver jobs
- ⛔ Sair

### Opção 2: Linha de Comando

Teste rápido (executa uma vez):
```bash
python scripts/rl_training_loop_v3.py
```

Iniciar scheduler (background):
```bash
python scripts/rl_training_integration.py --mode watch
```

Scheduler com hora fixa (22:00):
```bash
python scripts/rl_training_integration.py --mode scheduler --scheduler-time 22:00
```

Modo híbrido (scheduler + market watch):
```bash
python scripts/rl_training_integration.py --mode hybrid
```

### Opção 3: Background (Windows)

```powershell
$job = Start-Job -ScriptBlock {
    cd C:\repo\operador-day-trade-win
    python scripts/rl_training_scheduler.py
}
# Ver status
Get-Job -Id $job.Id
# Parar
Stop-Job -Id $job.Id
```

## 📊 Checklist Inicial

- [ ] Python 3.11+ instalado (`python --version`)
- [ ] APScheduler instalado (`pip list | grep apscheduler`)
- [ ] Diretório `logs/` criado
- [ ] Diretório `data/db/` existe
- [ ] Arquivo `data/db/trading.db` existe
- [ ] Teste passou (`python scripts/rl_training_loop_v3.py`)

## 🎯 Primeiro Teste

```bash
# 1. Verificar saúde do modelo atual
python scripts/rl_health_monitor.py

# 2. Executar um treinamento (leva ~2-5 min)
python scripts/rl_training_loop_v3.py

# 3. Verificar resultado
python scripts/rl_health_monitor.py
```

Esperado:
```
📊 RL MODEL HEALTH REPORT
✅ MODELO ATUAL:
   F1 Score: 0.850+
   Episodes: 1082 train / 271 validation
   Status: ✅ Modelo estável
```

## ⚙️ Configuração Padrão

**Arquivo:** `rl_config.json` (criar se necessário)

```json
{
  "daily_training": {
    "enabled": true,
    "time": "22:00",
    "days": "mon-fri"
  },
  "weekly_deep_training": {
    "enabled": true,
    "day": "friday",
    "time": "20:00"
  },
  "market_watch": {
    "enabled": true,
    "market_close": "17:00",
    "training_delay": 120
  },
  "model": {
    "n_estimators": 100,
    "max_depth": 8,
    "degradation_threshold": 0.10
  }
}
```

## 📈 Monitorar Execução

### Logs em Tempo Real

```bash
# Windows PowerShell
Get-Content logs/rl_scheduler.log -Tail 20 -Wait

# Linux/Mac
tail -f logs/rl_scheduler.log
```

### Ver Jobs Rodando

```powershell
# Windows
Get-Job
Get-Content logs/rl_scheduler.log -Tail 50

# Linux/Mac
ps aux | grep rl_training
```

### Alertas de Degradação

```bash
# Ver alertas
cat logs/degradation_alerts.jsonl

# Ou no PowerShell
Get-Content logs/degradation_alerts.jsonl
```

## 🆘 Troubleshooting

| Problema | Solução |
|----------|---------|
| `ModuleNotFoundError: apscheduler` | `pip install apscheduler` |
| `database is locked` | Aguarde 10s, scheduler tenta novamente |
| Scheduler não inicia | Verifique: Python, pasta logs/, DB permissions |
| Modelo degradando | Coletar mais dados, revisar features |
| Logs vazios | Verifique pasta `logs/` existe |

## 💡 Dicas

1. **Para máxima automação:** Use `--mode watch`
   - Treina automaticamente após fechamento do mercado (17:00)
   - Melhor para produção

2. **Para testes:** Use `--mode scheduler`
   - Treina em hora fixa (ex: 22:00)
   - Testável durante o dia

3. **Para híbrido:** Use `--mode hybrid`
   - Scheduler + Market watch
   - Mais robusto

4. **Horário recomendado:** 22:00 (depois do fechamento 17:00, antes da próxima manhã)

## 📚 Documentação Completa

Veja: [RL_TRAINING_SCHEDULER_README.md](RL_TRAINING_SCHEDULER_README.md)

## ✅ Next Steps

Depois que scheduler está rodando:

1. Deixar rodando por 7 dias
2. Coletar mais dados (meta: 5000+ episódios)
3. Otimizar features
4. Integrar com sinais de trading
5. Deploy em produção

---

**Status:** ✅ Pronto para produção
**Última atualização:** 2026-02-23


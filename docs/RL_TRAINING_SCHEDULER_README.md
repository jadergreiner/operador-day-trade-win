# 🤖 RL Training Scheduler - Documentação Completa

## 📋 Visão Geral

O **RL Training Scheduler** é um sistema automático que:

1. ✅ **Executa treinamentos regularmente** (diariamente após fechamento do mercado)
2. ✅ **Monitora degradação do modelo** (detecta queda de performance)
3. ✅ **Deep training semanal** (retreinamento com mais dados)
4. ✅ **Mantém histórico de métricas** (rastreamento de progresso)
5. ✅ **Gera alertas** (quando modelo degrada)

## 🚀 Iniciar o Scheduler

### Opção 1: PowerShell (Recomendado - Modern)

```bash
.\INICIAR_RL_SCHEDULER.ps1
```

Abrirá menu interativo com opções:
- 1️⃣ Iniciar scheduler (background)
- 2️⃣ Executar uma vez (teste)
- 3️⃣ Verificar saúde do modelo
- 4️⃣ Ver jobs agendados
- 5️⃣ Sair

### Opção 2: Batch (CMD)

```bash
INICIAR_RL_SCHEDULER.bat
```

Mesmo menu que PowerShell (compatibilidade com Windows antigos).

### Opção 3: Python Direto

```bash
python scripts/rl_training_scheduler.py
```

Inicia scheduler em foreground (mantém console aberto).

## ⚙️ Configuração

### Schedule Padrão

```python
# Daily training
- Hora: 22:00 (10 PM) - Após fechamento do mercado
- Dias: Segunda-Sexta (dias úteis)
- Duração: ~2-5 minutos

# Weekly deep training
- Dia: Sexta-feira
- Hora: 20:00 (8 PM)
- Duração: ~10-15 minutos
```

### Customizar Schedule

Edite `scripts/rl_training_scheduler.py` na função `main()`:

```python
def main():
    scheduler = RLTrainingScheduler()
    
    # DIÁRIO (customizar hora)
    scheduler.schedule_training(
        time_of_day='22:00',      # Mudar para '18:00', '20:00', etc
        days_of_week='mon-fri'    # 'tue-sat', 'mon-fri', etc
    )
    
    # SEMANAL (customizar dia)
    scheduler.schedule_weekly_deep_training(
        day_of_week=4,            # 0=segunda, 4=sexta, 6=domingo
        time_of_day='20:00'       # Mudar hora
    )
    
    scheduler.start()
```

## 📊 Monitorar Status

### Via PowerShell

```powershell
# Ver jobs rodando
Get-Job

# Ver logs em tempo real
Get-Content logs/rl_scheduler.log -Tail 20 -Wait

# Parar um job
Stop-Job -Id <id>

# Ver alertas de degradação
Get-Content logs/degradation_alerts.jsonl
```

### Via Menu

Digite **3** no menu launcher para "Verificar saúde do modelo":

```
📊 RL MODEL HEALTH REPORT
=======================================================
✅ MODELO ATUAL:
   Version: 4.0.0
   Algorithm: RandomForest
   F1 Score: 0.850
   Episodes: 1082 train / 271 validation = 1353 total
   Trained: 2026-02-23 15:45:23

📈 HISTÓRICO (últimos 7 dias):
   Total de treinos: 7
   F1 Min: 0.820
   F1 Max: 0.885
   F1 Média: 0.850

🔍 STATUS:
   ✅ Modelo estável
```

## 🔍 Detecção de Degradação

O scheduler monitora automaticamente:

### 1. Degradação Severa (>10%)
```
⚠️ DEGRADAÇÃO DETECTADA: F1 caiu 12.3%
```

Ações recomendadas:
- Revisar dados recentes
- Aumentar janela de treinamento
- Reajustar feature engineering

### 2. Advertência (5-10%)
```
📊 Leve redução de 7.5% - monitorando
```

Monitorar nas próximas execuções.

### 3. Modelo Saudável (<5%)
```
✅ Modelo estável (F1 drop: 2.1%)
```

Tudo normal!

## 📁 Estrutura de Logs

```
logs/
├── rl_scheduler.log          # Log principal (detalhado)
├── degradation_alerts.jsonl  # Alertas de degradação (JSON)
└── training_metrics.db       # Histórico de métricas (SQLite)
```

### Exemplo Log

```
2026-02-23 15:30:15 - [INFO] 🔄 INICIANDO NOVO CICLO DE TREINAMENTO...
2026-02-23 15:30:15 - [INFO]    Episódios carregados: 1353
2026-02-23 15:30:15 - [INFO]    Rewards: 6761 (Win: 1776, 26.3%)
2026-02-23 15:30:15 - [INFO]    Features: 1353 episódios
2026-02-23 15:30:16 - [INFO]    F1: 0.850
2026-02-23 15:30:16 - [INFO]    ROC-AUC: 0.875
2026-02-23 15:30:16 - [INFO]    Win Rate: 0.192
2026-02-23 15:30:16 - [INFO]    ✅ Métricas salvas! ID: 30dcb894-a3e8-43af
2026-02-23 15:30:16 - [INFO]    ✅ Modelo estável (F1 drop: 2.1%)
```

## 🧠 Como o Scheduler Funciona

### Ciclo Diário (22:00)

```
1. Conectar ao banco (trading.db)
   ↓
2. Carregar últimos 2000 episódios
   ↓
3. Agregar rewards por episódio
   ↓
4. Calcular features:
   - n_rewards (número de recompensas)
   - win_rate (% de wins)
   - avg_reward (recompensa média)
   - reward_range (máx - mín)
   ↓
5. Treinar RandomForest com 100 estimadores
   ↓
6. Avaliar: F1, ROC-AUC, Precision, Recall
   ↓
7. Salvar métricas em RL_TRAINING_METRICS
   ↓
8. Comparar com última métrica
   - Detectar degradação (drop > 10%)
   - Log de alertas se necessário
   ↓
9. Fim (próxima execução: amanhã 22:00)
```

### Deep Training Semanal (Sexta 20:00)

```
Mesmo processo acima, mas:
- Usa 100% dos dados (não limita a 2000 episódios)
- RandomForest com 200 estimadores (vs 100 diário)
- max_depth=10 (vs 8 diário)
- Maior rigor na validação
```

## 📈 Interpretar Métricas

| Métrica | Ideal | Aceitável | Ruim |
|---------|-------|-----------|------|
| **F1 Score** | 0.80-0.95 | 0.70-0.79 | <0.70 |
| **ROC-AUC** | 0.85-0.95 | 0.75-0.84 | <0.75 |
| **Precision** | 0.80-0.90 | 0.70-0.79 | <0.70 |
| **Recall** | 0.70-0.85 | 0.60-0.70 | <0.60 |

**Exemplo Real v3.0.0:**
- F1: 1.000 ⚠️ (possível overfitting)
- ROC-AUC: 1.000 ⚠️ (possível overfitting)
- Precision: 1.000 ✅
- Recall: 1.000 ✅
- Win Rate: 19.2% ⚠️ (precisa dados mais recentes)

## 🔧 Troubleshooting

### Erro: ModuleNotFoundError: No module named 'apscheduler'

```bash
pip install apscheduler
```

### Scheduler não está rodando

```bash
# Verificar jobs
Get-Job

# Ver erro
Get-Job -Id <id> | Receive-Job

# Reiniciar
Stop-Job -Id <id>
Start-Job -ScriptBlock { cd C:\repo\...; python scripts/rl_training_scheduler.py }
```

### Database locked

Se receber erro "database is locked":
1. Aguarde alguns segundos
2. O scheduler tentará novamente automaticamente
3. Se persistir, reinicie o scheduler

### Modelo degradando frequentemente

Possíveis causas:
1. **Janela de dados muito pequena**: Aumentar `LIMIT 2000` para `LIMIT 5000`
2. **Features inadequadas**: Revisar feature engineering
3. **Reward function incorreta**: Ajustar lógica de wins

## 🎯 Próximos Passos

1. **Coletar mais dados**
   - Target: 5000+ episódios
   - Continuar trading automático

2. **Otimizar features**
   - Adicionar indicadores técnicos
   - Correlation analysis

3. **Tunar hiperparâmetros**
   - Grid search nos hiperparâmetros do RandomForest
   - Cross-validation mais rigorosa

4. **Integrar com trading**
   - Usar modelo para gerar sinais
   - Validar em paper trading

5. **Deploy em produção**
   - Rodar scheduler 24/7
   - Monitorar métricas em tempo real
   - Alertas automáticos para degradação

## 📞 Suporte

Para erros ou dúvidas:
1. Verifique `logs/rl_scheduler.log`
2. Verifique `logs/degradation_alerts.jsonl`
3. Execute teste: `python scripts/rl_training_loop_v3.py`

---

**Status:** ✅ Pronto para uso
**Última atualização:** 2026-02-23
**Versão:** 1.0.0

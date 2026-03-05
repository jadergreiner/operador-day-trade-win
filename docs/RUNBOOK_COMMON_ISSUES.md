# Runbook - Operação Phase 1 Beta

**Objetivo:** Respostas rápidas para os 15+ cenários mais prováveis durante o Beta
**Data:** 08/03/2026
**Audiência:** Operador, CTO, ML Expert, Finance

---

## Cenários de Resposta Rápida

### 🟡 ALERTA: Nenhuma ordem sendo gerada

**Sintomas:**
- Mercado aberto, nenhuma alerta gerada em 30 min
- Dashboard mostra "0 alertas gerados"
- Logs não contêm signal generation

**Causas Possíveis:**
1. Modelo não está carregando (100% prob)
2. Threshold muito alto (sigma=2.0+)
3. Dados não chegando (datafeed offline)
4. Filtro de volatilidade bloqueando (20+ volatilidade)

**Diagnóstico (5 min):**
```bash
# 1. Verificar modelo carregado
python -c "from src.ml.backtest_server_xgboost import load_model; m=load_model('data/models/xgboost_v1.0.pkl'); print('✅ Modelo OK')"

# 2. Verificar dados chegando
sqlite3 data/db/trading.db "SELECT COUNT(*) FROM price_history WHERE symbol='WIN' AND date='2026-03-10';"

# 3. Verificar threshold
grep -r "threshold" config/ | grep -i sigma

# 4. Verificar logs de erro
tail -50 data/logs/errors.log
```

**Ações Corretivas:**
- ❌ **NÃO ativar modo de risco** - sistema está funcionando corretamente, apenas sem oportunidades
- ✅ **Aguarde próxima oportunidade** - backtest mostrou 1-3 alertas/hora, é normal
- ✅ **Monitore volatilidade** - se VIX > 25, sistema está correto em não gerar sinais
- ❌ **NÃO ajuste threshold** - procedimento só com aprovação CTO + ML Expert

**Escalação se persistir >2h:** Contactar ML Expert (verificar calibração modelo)

**Tempo SLA:** 30 min diagnóstico, decision tree até resolução

---

### 🔴 CRÍTICO: Circuit breaker ativado (-3%)

**Sintomas:**
- Sistema mostra aviso: "CIRCUIT BREAKER LEVEL 1 ATIVADO"
- Mensagem: "Drawdown -3% - Modo ALERTA ativado"
- Dashboard: amarelo/laranja

**O que acontece:**
- ✅ Sistema continua gerando sinais (NÃO PAUSA)
- ✅ Trader pode vetá-los manualmente (override funciona)
- ✅ Alertas continuam em NORMAL (sem slow-down)

**Causas Típicas:**
1. Slippage maior do que esperado (gap de 30+ pips)
2. Reversão de mercado (perda 3-4 trades cumulativo)
3. Entrada errada de trader (ordem fora do timing)
4. Correlação maior do que threshold permite

**Ações Operacionais (0 min - IMEDIATO):**
1. ✅ **Notifique Trader:** "Alerta -3% ativado, continue monitorando"
2. ✅ **Notifique CTO:** Envie log para análise de root cause
3. ✅ **Monitore P&L:** Se próximos sinais revertem loss, OK. Se continua caindo → escalação
4. ✅ **Mantenha transparência:** Comunique status para CFO

**Análise de Root Cause (15 min):**
```bash
# Ver últimas 10 ordens
sqlite3 data/db/trading.db "SELECT timestamp, type, price, sl, tp, exit_price, pnl FROM orders ORDER BY timestamp DESC LIMIT 10;"

# Verificar volatilidade no period
python -c "
import pandas as pd
prices = pd.read_csv('data/backtest/prices.csv')
volatility = prices['close'].pct_change().std() * 100
print(f'Current volatility: {volatility:.2f}%')
print(f'Threshold check: {\"OK\" if volatility < 5.0 else \"ELEVATED\"}')
"

# Ver ML scores nos últimos sinais
tail -30 data/logs/model.log | grep "score="
```

**Decisão em Level 1:**
- **Se P&L reverter em próximos 2h:** Sem ação necessária ✅
- **Se P&L continua caindo:** Goto LEVEL 2 (-5%)
- **Se múltiplas perdas consecutivas:** Contactar CTO

**Não fazer:**
- ❌ NÃO ativar HALT automático - Trader decide
- ❌ NÃO mudar parâmetros - Freeze de config até análise

**SLA:** Status update a cada 30 min até resolução

---

### 🔴 CRÍTICO: Circuit breaker LEVEL 2 (-5%)

**Sintomas:**
- "CIRCUIT BREAKER LEVEL 2 ATIVADO"
- Sistema em SLOW MODE (50% dos sinais gerados)
- Mensagem: "Drawdown -5% - Sistema em modo conservador"

**O que muda:**
- ✅ Sistema agora gera 50% dos sinais
- ✅ ML confidence > 90% obrigatório (vs 80% antes)
- ✅ Trader pode AINDA vetá-los manualmente
- ❌ Sem pause completo (ainda existe risco)

**Ações Emergenciais (0 min):**
1. **IMEDIATAMENTE notificar CFO:** "Drawdown -5%, sistema em modo conservador"
2. **Trader em standby:** Revisar cada sinal manualmente ANTES de executar
3. **CTO em investigação:** Root cause analysis iniciado
4. **ML Expert consultado:** Avaliar se modelo está degraded

**Checkpoint (15 min):**
```bash
# Quantificar impacto exato
echo "Recent trades:"
sqlite3 data/db/trading.db "SELECT COUNT(*), AVG(pnl) FROM orders WHERE date='2026-03-10' AND timestamp > datetime('now', '-30 minutes');"

# Verificar se loss é reverting
python -c "
import sqlite3
conn = sqlite3.connect('data/db/trading.db')
cursor = conn.execute('SELECT SUM(pnl) FROM orders WHERE date=date(\"now\")')
cumulative_pnl = cursor.fetchone()[0] or 0
print(f'Cumulative P&L today: R$ {cumulative_pnl:,.2f}')
print(f'Status: {\"🟡 Loss\" if cumulative_pnl < -2500 else \"🟢 Profit/Breakeven\"}')
"
```

**Decisão em Level 2:**
- **Se reverter em próximos 30 min:** Mantenha SLOW MODE, monitore
- **Se continua caindo:** Goto LEVEL 3 (-8% HALT)
- **Se estabiliza:** Permaneça em SLOW MODE até reset manual

---

### 🔴 🚨 CRÍTICO MÁXIMO: Circuit breaker LEVEL 3 (-8% HALT)

**Sintomas:**
- Sistema mostra: "CIRCUIT BREAKER LEVEL 3 - SISTEMA PAUSADO"
- Dashboard totalmente vermelho
- Nenhum novo sinal gerado

**O que acontece:**
- ✅ **TODOS os sinais pausados** - trading engine parado
- ✅ **Posições abertas mantidas** (não fecham automaticamente)
- ✅ **Trader tem estranho:** Pode fechar manualmente
- ✅ **Recuperação requer aprovação CTO + CFO**

**Ações (PRIMERTOS 2 MINUTOS):**
1. **PARAR TUDO:** Sistema já parou, trader não faz nada
2. **ALERTAS EMERGENCIAIS:**
   - Slack: "#trading-emergency" com screenshot
   - Teams: Tag CTO + CFO
   - Email: Exec on-call
3. **POSIÇÕES VIVAS:**
   - Trader avalia cada posição aberta
   - Fecha perdedoras se necessário (decisão manual)
   - Mantém vencedoras para continuar

**Análise de Root Cause (IMEDIATO - 10 min):**
```bash
# Ver EXATAMENTE o que aconteceu
echo "=== ORDER LOG (últimas 20 transações) ==="
sqlite3 data/db/trading.db "SELECT timestamp, type, symbol, price, exit_price, pnl FROM orders ORDER BY timestamp DESC LIMIT 20;"

echo "=== CUMULATIVE P&L (intraday) ==="
sqlite3 data/db/trading.db "SELECT SUM(pnl) as total_loss FROM orders WHERE date='2026-03-10';"

echo "=== VOLATILITY CHECK ==="
python -c "
import pandas as pd
df = pd.read_csv('data/backtest/prices.csv')
vol = df['close'].pct_change().std()
print(f'Volatility: {vol*100:.2f}%')
"

echo "=== MODEL DIAGNOSTICS ==="
tail -50 data/logs/model.log | grep -E "score=|error|exception"
```

**Decisão de Recuperação:**
Requer aprovação de AMBOS:
- ✅ **CTO:** "Código operacional, recuperação segura"
- ✅ **CFO:** "Aceita risco, capital protegido"

**Recuperação (CTO autoriza):**
```bash
# Resetar circuit breaker
python -c "
from src.domain.models.risk_system import CircuitBreaker
cb = CircuitBreaker()
cb.reset_level_3()
print('Circuit breaker resetado - autorização CTO + CFO obrigatória')
"

# Reiniciar motor de trading
python -m src.application.services.trading_orchestrator --resume --capital-check
```

**Não fazer:**
- ❌ NÃO reiniciar automaticamente - requer autorização manual
- ❌ NÃO fechar todas as posições - decisão do Trader
- ❌ NÃO culpar o sistema - investigar root cause PRIMEIRO

**SLA:** Análise em 10 min, decisão em 30 min, recuperação em <2h

---

### 🟡 AVISO: Taxa de falsos positivos acima do normal

**Sintomas:**
- Gerador de sinais funciona, mas muitos resultam em loss
- FP rate >15% (target: <10%)
- Algumas ordens com pnl = -R$ 100-500

**Causas Prováveis:**
1. Mercado em range/consolidação (sem tendência)
2. Slippage maior que esperado
3. Entrada no modelo em threshold baixo
4. Market regime change (modelo desatualizado)

**Diagnóstico (10 min):**
```bash
# Calcular FP rate atual
sqlite3 data/db/trading.db "
SELECT
  CAST(SUM(CASE WHEN pnl < 0 THEN 1 ELSE 0 END) AS FLOAT) / COUNT(*) * 100 as fp_rate,
  AVG(ABS(pnl)) as avg_trade_size,
  MIN(pnl) as worst_trade
FROM orders
WHERE date = '2026-03-10' AND timestamp > datetime('now', '-2 hours');
"

# Ver distribuição de P&L
python -c "
import sqlite3, statistics
conn = sqlite3.connect('data/db/trading.db')
cursor = conn.execute('SELECT pnl FROM orders WHERE date=date(\"now\")')
pnls = [row[0] for row in cursor.fetchall()]
print(f'Total trades: {len(pnls)}')
print(f'Winning trades: {len([x for x in pnls if x > 0])}')
print(f'Mean P&L: R$ {statistics.mean(pnls):.2f}')
print(f'StdDev: R$ {statistics.stdev(pnls) if len(pnls) > 1 else 0:.2f}')
"
```

**Ações Corretivas:**
1. ✅ **Monitore por 30 min** - pode ser variação normal
2. ✅ **Se FP >20%:** Notifique ML Expert para análise modelo
3. ✅ **Se volatilidade baixa (<2%):** Sistema correto, mercado sem tendência
4. ✅ **Trader pode elevar threshold manualmente** (CTO approval)

**ML Expert análise (se continua):**
```bash
# Fazer backtest com dados atualizados
python scripts/backtest_optimizado.py --recent 50 --resample

# Resultado esperado: Confirmar que sistema performance está alinhado com backtest
# Se divergência > 10%: Retraining necessário
```

---

### 🟡 AVISO: Latência P95 acima de 500ms

**Sintomas:**
- Logs mostram: "P95 latency: 650ms"
- Ordens executadas, mas com delay visível
- Sistema ainda responde, mas lento

**Causas Típicas:**
1. Network latency (MT5 server overloaded)
2. CPU spike (múltiplos processos rodando)
3. Database contention (backup em andamento)
4. Memory pressure (swap ativado)

**Diagnóstico Rápido (3 min):**
```bash
# Ver CPU/Memory real-time
tasklist /v | find "python"

# Verificar network
ping -c 10 localhost | grep "Average"

# Database check
sqlite3 data/db/trading.db "PRAGMA page_count;"
```

**Ações:**
1. ✅ **Se CPU > 80%:** Interrompa outros processos (backups, análises)
2. ✅ **Se Network > 200ms:** Contactar Infra team
3. ✅ **Se Database > 100MB:** Rodar vacuum
4. ✅ **Se Memory > 500MB:** Reiniciar serviço

**Não é crítico:** Sistema ainda funciona, métricas acima de target são avisos apenas.

---

## Matriz de Escalação

| Nível | Condição | Escalação | Tempo Resposta |
|-------|----------|-----------|----------------|
| 🟢 Normal | Sistema operacional | Monitoramento passivo | - |
| 🟡 Level 1 | -3% drawdown | Notificar CTO | 15 min |
| 🟠 Level 2 | -5% drawdown | Slow mode, notify CFO | 15 min |
| 🔴 Level 3 | -8% drawdown | HALT, requer aprovação | 30 min |
| 🔴🔴 Crítico | Falha sistema | Contactar exec on-call | 5 min |

---

## Contatos de Escalação

```
TIER 1 (5-15 min response):
- CTO/Eng Sr: <TELEFONE> | Teams: @cto_name
- ML Expert: <TELEFONE> | Teams: @ml_name
- Trader: <TELEFONE> | Slack: @trader_name

TIER 2 (15-30 min response):
- Head Finance/CFO: <TELEFONE> | Email: cfo@company.com
- Data Eng: <TELEFONE> | Teams: @data_eng

TIER 3 (Executive Escalation):
- CIO: <TELEFONE> | Email: cio@company.com
- CEO: <TELEFONE> | Email: ceo@company.com

24/5 On-Call Schedule:
Mon-Fri: 09:00-18:00 BRT (primary)
Fri 15:00-Mon 09:00: Standby mode
```

---

Document: RUNBOOK_COMMON_ISSUES.md
Created: 08/03/2026 16:20 BRT
Status: ✅ READY FOR OPERATIONS

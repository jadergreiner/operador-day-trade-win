# 🔧 Quick Reference - Comandos SQL para Diagnóstico

**Uso Rápido:** Copiar/colar direto em `sqlite3 data/db/trading.db` ou DBeaver

```bash
# Abrir BD
sqlite3 data/db/trading.db
```

---

## Q1: OS 3 TRADES ESTÃO EM trading.db?

### 1a) Checar estrutura

```sql
.schema trades
```

### 1b) Buscar pelos 3 IDs específicos

```sql
SELECT id, order_id, symbol, direction, entry_price, exit_price,
       entry_time, exit_time, status
FROM trades
WHERE order_id IN (2276170194, 2276191196, 2276191635)
ORDER BY entry_time;
```

### 1c) Todos trades de 26/02

```sql
SELECT id, order_id, symbol, direction, entry_price, exit_price,
       entry_time, exit_time
FROM trades
WHERE date(entry_time) = '2026-02-26'
ORDER BY entry_time;
```

### 1d) Contagem total de trades

```sql
SELECT COUNT(*) as total_trades FROM trades;
SELECT COUNT(*) as trades_26fev FROM trades WHERE date(entry_time) = '2026-02-26';
```

### 1e) Últimos 10 trades (para ver data mais recente)

```sql
SELECT MAX(entry_time) as ultimo_trade FROM trades;
SELECT id, order_id, entry_time, exit_time FROM trades ORDER BY entry_time DESC LIMIT 10;
```

---

## Q2: POR QUE TRADE #1 SEM SL/TP?

### 2a) Inspecionar colunas SL/TP

```sql
PRAGMA table_info(trades);
```

### 2b) Trade específico com todos detalhes

```sql
SELECT * FROM trades WHERE order_id = 2276170194;
```

### 2c) Buscar padrão SL/TP (múltiplos nomes possíveis)

```sql
-- Se houver colunas 'stop_loss' e 'take_profit'
SELECT order_id, entry_price, stop_loss, take_profit
FROM trades
WHERE order_id = 2276170194;

-- Ou se 'sl' e 'tp'
SELECT order_id, entry_price, sl, tp
FROM trades
WHERE order_id = 2276170194;
```

### 2d) Quantos trades em 26/02 têm SL/TP vazios?

```sql
-- Assumindo colunas stop_loss / take_profit
SELECT COUNT(*) as trades_sem_sl_tp
FROM trades
WHERE date(entry_time) = '2026-02-26'
AND (stop_loss IS NULL OR take_profit IS NULL);
```

### 2e) Verificar tabela manual_activities (se existir)

```sql
SELECT * FROM manual_activities
WHERE date(timestamp) = '2026-02-26'
ORDER BY timestamp;
```

---

## Q3: QUAL É O DELAY ENTRE MT5 E PERSISTÊNCIA?

### 3a) Timings de 26/02

```sql
SELECT order_id, entry_time, exit_time,
       CAST((julianday(exit_time) - julianday(entry_time)) * 86400 AS INTEGER) as duration_seconds
FROM trades
WHERE date(entry_time) = '2026-02-26'
ORDER BY entry_time;
```

### 3b) Tabelas de log (se houver)

```sql
-- Listar O que tem "log" ou "sync"
SELECT DISTINCT name FROM sqlite_master
WHERE type='table'
AND (name LIKE '%log%' OR name LIKE '%sync%');
```

### 3c) Verificar se há coluna de created_at/updated_at

```sql
PRAGMA table_info(trades);
-- Procurar por "created_at", "updated_at", "persisted_at", etc.
```

### 3d) Estimar delay (se houver created_at)

```sql
-- Calcular diferença entre entry_time (MT5) e created_at (BD)
SELECT order_id, entry_time, created_at,
       CAST((julianday(created_at) - julianday(entry_time)) * 86400 AS INTEGER) as delay_seconds
FROM trades
WHERE date(entry_time) = '2026-02-26'
ORDER BY order_id;
```

---

## Q4: FORAM GERADOS RLs DAS 3 TRADES?

### 4a) Listar tabelas RL

```sql
SELECT name FROM sqlite_master
WHERE type='table'
AND name LIKE '%rl%'
ORDER BY name;
```

### 4b) Contagem de RL episodes

```sql
SELECT COUNT(*) as total_episodes FROM rl_episodes;
SELECT COUNT(*) as episodes_26fev FROM rl_episodes
WHERE date(created_at) = '2026-02-26';
```

### 4c) Últimos episodes (para verificar timestamp)

```sql
SELECT * FROM rl_episodes
ORDER BY created_at DESC LIMIT 5;
```

### 4d) Episodes linkados ao 26/02

```sql
SELECT ep.id, ep.trade_id, ep.created_at, tr.order_id
FROM rl_episodes ep
LEFT JOIN trades tr ON tr.id = ep.trade_id
WHERE date(ep.created_at) = '2026-02-26'
ORDER BY ep.created_at;
```

### 4e) Verificar linkage 1:1 (cada trade tem episode?)

```sql
SELECT tr.order_id, COUNT(ep.id) as episode_count
FROM trades tr
LEFT JOIN rl_episodes ep ON tr.id = ep.trade_id
WHERE date(tr.entry_time) = '2026-02-26'
GROUP BY tr.id;
```

### 4f) Rewards associados

```sql
SELECT r.id, r.episode_id, r.reward, r.created_at
FROM rl_rewards r
WHERE date(r.created_at) = '2026-02-26'
LIMIT 10;
```

### 4g) Status table rl_training_history

```sql
SELECT * FROM rl_training_history
ORDER BY training_date DESC LIMIT 5;
```

---

## BÔNUS: Auditorias Rápidas

### Verificar se analytics.db tem os trades

```bash
sqlite3 data/analytics.db
```

```sql
-- Dentro de analytics.db
SELECT COUNT(*) FROM trades WHERE date(entry_time) = '2026-02-26';
SELECT id, order_id, entry_time FROM trades
WHERE order_id IN (2276170194, 2276191196, 2276191635);
```

### Procurar por "manual_activities" (trader override?)

```sql
SELECT * FROM manual_activities
WHERE date(timestamp) = '2026-02-26'
AND (order_id = 2276170194 OR trade_id IN (
    SELECT id FROM trades WHERE order_id = 2276170194
));
```

### Listar TODAS as colunas de trades (para referência)

```sql
SELECT sql FROM sqlite_master
WHERE type='table' AND name='trades';
```

---

## 🚀 ATALHO (Rodá-lo tudo de uma vez)

Crie um arquivo `diagnostico.sql`:

```sql
-- Q1
SELECT 'Q1: 3 Trades de 26/02' as Questao;
SELECT order_id, entry_time FROM trades
WHERE order_id IN (2276170194, 2276191196, 2276191635);

-- Q2
SELECT 'Q2: SL/TP Trade #1' as Questao;
SELECT order_id, entry_price, stop_loss, take_profit FROM trades
WHERE order_id = 2276170194;

-- Q3
SELECT 'Q3: Timings 26/02' as Questao;
SELECT order_id, entry_time, exit_time FROM trades
WHERE date(entry_time) = '2026-02-26';

-- Q4
SELECT 'Q4: RLs 26/02' as Questao;
SELECT COUNT(*) as episode_count FROM rl_episodes
WHERE date(created_at) = '2026-02-26';
```

Depois:
```bash
sqlite3 data/db/trading.db < diagnostico.sql
```

---

**Observações:**
- Substituir nomes de colunas se estrutura for diferente
- Colar output do script Python no TEMPLATE_RESPOSTA_DATA_ENGINEER_S1-4.md
- Entregar resposta até 15:30 BRT

# ✅ S2-6 INICIAÇÃO DE EXECUÇÃO — Analytics de Intervenção Manual

**Status:** 🟢 AUTORIZADO (Gate 2 GO - 24/02 17:45)
**Owner:** Doc Advocate + Infra
**Timeline:** 24/02 19:00 → 28/02 14:00
**Objetivo:** Analytics completo de intervenções manuais para produção

---

## 🎯 Quick Checklist (Execução Paralela com S2-4)

### [X] Pré-requisitos Validados
- ✅ Framework pronto (`gate2_backtest_validator.py`)
- ✅ Database schema definido
- ✅ API endpoints especificados

### [ ] Passo 1: Setup Analytics Database (19:00-20:30 — 90 min)

**O que fazer:**

```bash
# Terminal 3: Setup da base de intervenções
cd c:/repo/operador-day-trade-win

# 1. Criar tabela de intervenções
python scripts/setup_analytics.py --mode interventions

# 2. Criar índices para performance
python scripts/setup_analytics.py --mode optimize

# 3. Validar estrutura
python scripts/setup_analytics.py --mode validate
```

**Schema Esperado:**

```sql
CREATE TABLE trader_interventions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp DATETIME NOT NULL,
    symbol TEXT NOT NULL,
    action TEXT NOT NULL,  -- 'OVERRIDE', 'PAUSE', 'CANCEL', 'EXECUTE'
    reason TEXT,
    ml_signal FLOAT,
    trader_decision TEXT,
    result TEXT,  -- 'WIN', 'LOSS', 'PARTIAL'
    p_and_l FLOAT,
    created_at DATETIME,
    INDEX idx_timestamp (timestamp),
    INDEX idx_symbol (symbol)
);
```

**Checklist:**
- [ ] Tabela traders created
- [ ] Índices criados
- [ ] Validação PASSED
- [ ] Backup de dados anteriores

---

### [ ] Passo 2: Implementar Collectors (20:30-23:00 — 150 min)

**Ação:** Criar `src/analytics_collector.py`

```python
# Arquivo: src/analytics_collector.py

import sqlite3
from datetime import datetime
from dataclasses import dataclass
from typing import Optional, Dict

@dataclass
class AnalyticsCollector:
    """Coletor de eventos de intervenção manual"""

    def __init__(self, db_path: str):
        self.db_path = db_path
        self.conn = None

    def connect(self):
        """Conecta á base de dados"""
        self.conn = sqlite3.connect(self.db_path)
        self.conn.row_factory = sqlite3.Row

    def log_intervention(
        self,
        symbol: str,
        action: str,  # OVERRIDE, PAUSE, CANCEL, EXECUTE
        reason: str,
        ml_signal: float,
        trader_decision: str
    ) -> int:
        """
        Registra uma intervenção manual.

        Returns:
            intervention_id para posterior update
        """
        cursor = self.conn.cursor()
        cursor.execute("""
            INSERT INTO trader_interventions (
                timestamp, symbol, action, reason,
                ml_signal, trader_decision, created_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (
            datetime.now(),
            symbol,
            action,
            reason,
            ml_signal,
            trader_decision,
            datetime.now()
        ))
        self.conn.commit()
        return cursor.lastrowid

    def update_intervention_result(
        self,
        intervention_id: int,
        result: str,  # WIN, LOSS, PARTIAL
        p_and_l: float
    ):
        """Atualiza resultado da intervenção"""
        cursor = self.conn.cursor()
        cursor.execute("""
            UPDATE trader_interventions
            SET result = ?, p_and_l = ?
            WHERE id = ?
        """, (result, p_and_l, intervention_id))
        self.conn.commit()

    def get_intervention_stats(self, symbol: Optional[str] = None):
        """Retorna estatísticas de intervenções"""
        cursor = self.conn.cursor()

        if symbol:
            cursor.execute("""
                SELECT
                    COUNT(*) as total_interventions,
                    SUM(CASE WHEN result = 'WIN' THEN 1 ELSE 0 END) as wins,
                    SUM(CASE WHEN result = 'LOSS' THEN 1 ELSE 0 END) as losses,
                    AVG(p_and_l) as avg_pnl,
                    SUM(p_and_l) as total_pnl
                FROM trader_interventions
                WHERE symbol = ?
            """, (symbol,))
        else:
            cursor.execute("""
                SELECT
                    COUNT(*) as total_interventions,
                    SUM(CASE WHEN result = 'WIN' THEN 1 ELSE 0 END) as wins,
                    SUM(CASE WHEN result = 'LOSS' THEN 1 ELSE 0 END) as losses,
                    AVG(p_and_l) as avg_pnl,
                    SUM(p_and_l) as total_pnl
                FROM trader_interventions
            """)

        return dict(cursor.fetchone())

    def close(self):
        if self.conn:
            self.conn.close()
```

**Checklist:**
- [ ] Arquivo `src/analytics_collector.py` criado
- [ ] Todas as funções testadas
- [ ] 100% type hints
- [ ] Docstrings completas

---

### [ ] Passo 3: API Endpoints (23:00-01:30 — 150 min)

**Ação:** Estender FastAPI em `src/websocket_server.py`

```python
# Em src/websocket_server.py - adicionar rotas

from analytics_collector import AnalyticsCollector

analytics = AnalyticsCollector("data/analytics.db")

@app.post("/api/intervention/log")
async def log_intervention(data: dict):
    """
    Log uma intervenção manual

    Body:
    {
        "symbol": "WINFUT",
        "action": "OVERRIDE",  # OVERRIDE, PAUSE, CANCEL, EXECUTE
        "reason": "Política de risco",
        "ml_signal": 0.45,
        "trader_decision": "Validado pelo trader"
    }
    """
    intervention_id = analytics.log_intervention(
        symbol=data["symbol"],
        action=data["action"],
        reason=data.get("reason", ""),
        ml_signal=data.get("ml_signal", 0.0),
        trader_decision=data["trader_decision"]
    )
    return {"intervention_id": intervention_id, "status": "logged"}

@app.post("/api/intervention/{intervention_id}/result")
async def update_intervention_result(intervention_id: int, data: dict):
    """
    Atualiza resultado de uma intervenção

    Body:
    {
        "result": "WIN",  # WIN, LOSS, PARTIAL
        "p_and_l": 125.50
    }
    """
    analytics.update_intervention_result(
        intervention_id,
        result=data["result"],
        p_and_l=data.get("p_and_l", 0.0)
    )
    return {"status": "updated"}

@app.get("/api/analytics/stats")
async def get_stats(symbol: str = None):
    """Retorna estatísticas de intervenções"""
    stats = analytics.get_intervention_stats(symbol)
    return stats

@app.get("/api/analytics/dashboard")
async def get_dashboard():
    """Dashboard completo de analytics"""
    all_stats = analytics.get_intervention_stats()
    return {
        "total_interventions": all_stats["total_interventions"],
        "win_rate": (all_stats["wins"] / max(1, all_stats["total_interventions"])) * 100,
        "avg_pnl": all_stats["avg_pnl"],
        "total_pnl": all_stats["total_pnl"]
    }
```

**Checklist:**
- [ ] Endpoints implementados
- [ ] Testes de API PASSING
- [ ] Error handling completo
- [ ] Documentação Swagger OK

---

### [ ] Passo 4: Integration Tests (01:30-04:00 — 150 min)

**Comando:**
```bash
# Terminal: Rodar testes de S2-6
python -m pytest tests/integration/test_analytics_api.py -v

# Esperado:
# test_log_intervention PASSED
# test_update_result PASSED
# test_get_stats PASSED
# test_dashboard PASSED
```

**Checklist:**
- [ ] Todos os 4 testes PASSING
- [ ] Coverage ≥ 90%
- [ ] Performance <200ms por request

---

### [ ] Passo 5: Documentação + Deploy Plan (04:00-06:00 — 120 min)

**Criar documento:** `docs/S2-6_DEPLOYMENT_PLAN.md`

```markdown
# 📋 S2-6 Deployment Plan

## Timeline de Deploy

| Fase | Data | Status |
|------|------|--------|
| Staging setup | 28/02 | 🟢 READY |
| Trader UAT | 01/03-02/03 | 🔄 SCHEDULED |
| Production | 03/03 | ⏳ PENDING |

## Rollback Strategy

- Se win rate < 60%: Revert em 2h
- Se API error rate > 5%: Revert imediato
- Checkpoint a cada 4h no primeiro dia

## Success Criteria

- Analytics capturing 100% de intervenções
- API latency P95 < 200ms
- Trader satisfaction > 4/5
```

**Checklist:**
- [ ] Deployment plan criado
- [ ] Rollback strategy detalhada
- [ ] Success criteria quantificado

---

## 📊 Timeline Esperada

| Fase | Duração | Deadline | Owner |
|------|---------|----------|-------|
| 1. Database | 90 min | 20:30 | Infra |
| 2. Collector | 150 min | 23:00 | Eng Sr |
| 3. API | 150 min | 01:30 | Eng Sr |
| 4. Tests | 150 min | 04:00 | QA |
| 5. Deploy Plan | 120 min | 06:00 | Doc Advocate |

**Total:** 12 horas (pode paralelizar)
**Início:** 24/02 19:00
**Conclusão:** 25/02 07:00

---

## ✅ Próximas Ações

1. Confirmar infraestrutura DB (19:00 24/02)
2. Iniciar Passo 1 (Database setup)
3. Paralelizar com S2-4 (ambas começam ~19h)
4. Reportar progresso a cada 2h

**Status:** 🟢 PRONTO PARA EXECUÇÃO

---

> Documento criado em 24/02 17:45 como parte de Gate 2 GO Approval

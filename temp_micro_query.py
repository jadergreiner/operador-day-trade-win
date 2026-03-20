"""Consulta especifica de micro_trend_decisions de hoje - versao corrigida."""
import sqlite3
from datetime import datetime

data_hoje = "2026-03-19"

conn = sqlite3.connect("data/db/trading.db")
conn.row_factory = sqlite3.Row
cursor = conn.cursor()

print("=" * 80)
print("MICRO TREND DECISIONS - 19/03/2026")
print("=" * 80)

# Verificar estrutura
cursor.execute("PRAGMA table_info(micro_trend_decisions)")
cols_info = cursor.fetchall()
cols = [c[1] for c in cols_info]
print(f"Colunas: {cols}\n")

# Buscar decisoes de hoje
cursor.execute("""
    SELECT * FROM micro_trend_decisions
    WHERE timestamp >= ?
    ORDER BY timestamp DESC
""", (f"{data_hoje} 00:00:00",))
rows = cursor.fetchall()
print(f"Total de decisoes de hoje: {len(rows)}")

# Analise por macro_signal
cursor.execute("""
    SELECT macro_signal, COUNT(*) as count
    FROM micro_trend_decisions
    WHERE timestamp >= ?
    GROUP BY macro_signal
""", (f"{data_hoje} 00:00:00",))
print("\n=== RESUMO POR MACRO_SIGNAL ===")
for row in cursor.fetchall():
    print(f"  {dict(row)}")

# Analise por micro_trend
cursor.execute("""
    SELECT micro_trend, COUNT(*) as count
    FROM micro_trend_decisions
    WHERE timestamp >= ?
    GROUP BY micro_trend
""", (f"{data_hoje} 00:00:00",))
print("\n=== RESUMO POR MICRO_TREND ===")
for row in cursor.fetchall():
    print(f"  {dict(row)}")

# Analise por SMC direction
cursor.execute("""
    SELECT smc_direction, COUNT(*) as count
    FROM micro_trend_decisions
    WHERE timestamp >= ?
    GROUP BY smc_direction
""", (f"{data_hoje} 00:00:00",))
print("\n=== RESUMO POR SMC_DIRECTION ===")
for row in cursor.fetchall():
    print(f"  {dict(row)}")

# Estatisticas de macro_score
cursor.execute("""
    SELECT
        MIN(macro_score) as min_score,
        MAX(macro_score) as max_score,
        AVG(macro_score) as avg_score,
        MIN(micro_score) as min_micro,
        MAX(micro_score) as max_micro,
        AVG(micro_score) as avg_micro
    FROM micro_trend_decisions
    WHERE timestamp >= ?
""", (f"{data_hoje} 00:00:00",))
print("\n=== ESTATISTICAS ===")
stats = dict(cursor.fetchone())
print(f"  Macro Score: min={stats['min_score']}, max={stats['max_score']}, avg={stats['avg_score']:.2f}")
print(f"  Micro Score: min={stats['min_micro']}, max={stats['max_micro']}, avg={stats['avg_micro']:.2f}")

# Mostrar algumas decisoes
print("\n=== PRIMEIRAS DECISOES DO DIA ===")
cursor.execute("""
    SELECT * FROM micro_trend_decisions
    WHERE timestamp >= ?
    ORDER BY timestamp ASC LIMIT 5
""", (f"{data_hoje} 00:00:00",))
for i, row in enumerate(cursor.fetchall(), 1):
    d = dict(row)
    print(f"\n{i}. {d.get('timestamp')}")
    print(f"   MacroScore: {d.get('macro_score')} | MacroSignal: {d.get('macro_signal')} | Confidence: {d.get('macro_confidence')}")
    print(f"   MicroScore: {d.get('micro_score')} | MicroTrend: {d.get('micro_trend')}")
    print(f"   Price: {d.get('price_current')} | VWAP: {d.get('vwap')} | SMC: {d.get('smc_direction')}")
    print(f"   Opportunities: {d.get('num_opportunities')}")

print("\n=== ULTIMAS DECISOES DO DIA ===")
cursor.execute("""
    SELECT * FROM micro_trend_decisions
    WHERE timestamp >= ?
    ORDER BY timestamp DESC LIMIT 5
""", (f"{data_hoje} 00:00:00",))
for i, row in enumerate(cursor.fetchall(), 1):
    d = dict(row)
    print(f"\n{i}. {d.get('timestamp')}")
    print(f"   MacroScore: {d.get('macro_score')} | MacroSignal: {d.get('macro_signal')} | Confidence: {d.get('macro_confidence')}")
    print(f"   MicroScore: {d.get('micro_score')} | MicroTrend: {d.get('micro_trend')}")
    print(f"   Price: {d.get('price_current')} | VWAP: {d.get('vwap')} | SMC: {d.get('smc_direction')}")
    print(f"   Opportunities: {d.get('num_opportunities')}")

# Verificar micro_trend_opportunities de hoje
print("\n" + "=" * 80)
print("MICRO TREND OPPORTUNITIES - 19/03/2026")
print("=" * 80)
cursor.execute("PRAGMA table_info(micro_trend_opportunities)")
cols = [c[1] for c in cursor.fetchall()]
print(f"Colunas: {cols}")

cursor.execute("""
    SELECT * FROM micro_trend_opportunities
    WHERE timestamp >= ?
    ORDER BY timestamp DESC
""", (f"{data_hoje} 00:00:00",))
opps = cursor.fetchall()
print(f"\nTotal de oportunidades de hoje: {len(opps)}")

# Resumo por direcao
cursor.execute("""
    SELECT direction, COUNT(*) as count, AVG(confidence) as avg_conf
    FROM micro_trend_opportunities
    WHERE timestamp >= ?
    GROUP BY direction
""", (f"{data_hoje} 00:00:00",))
print("\n=== RESUMO POR DIRECAO ===")
for row in cursor.fetchall():
    print(f"  {dict(row)}")

# Mostrar oportunidades
print("\n=== PRIMEIRAS OPORTUNIDADES DO DIA ===")
cursor.execute("""
    SELECT * FROM micro_trend_opportunities
    WHERE timestamp >= ?
    ORDER BY timestamp ASC LIMIT 5
""", (f"{data_hoje} 00:00:00",))
for i, row in enumerate(cursor.fetchall(), 1):
    d = dict(row)
    print(f"\n{i}. {d}")

print("\n=== ULTIMAS OPORTUNIDADES DO DIA ===")
cursor.execute("""
    SELECT * FROM micro_trend_opportunities
    WHERE timestamp >= ?
    ORDER BY timestamp DESC LIMIT 5
""", (f"{data_hoje} 00:00:00",))
for i, row in enumerate(cursor.fetchall(), 1):
    d = dict(row)
    print(f"\n{i}. {d}")

# Verificar trades de hoje
print("\n" + "=" * 80)
print("RESUMO DE TRADES - 19/03/2026")
print("=" * 80)
cursor.execute("""
    SELECT
        COUNT(*) as total,
        SUM(CASE WHEN status = 'CLOSED' THEN 1 ELSE 0 END) as fechados,
        SUM(CASE WHEN status = 'OPEN' THEN 1 ELSE 0 END) as abertos,
        SUM(CASE WHEN profit_loss > 0 THEN 1 ELSE 0 END) as gains,
        SUM(CASE WHEN profit_loss < 0 THEN 1 ELSE 0 END) as losses,
        SUM(profit_loss) as total_pnl,
        AVG(profit_loss) as avg_pnl
    FROM trades
    WHERE entry_time >= ?
""", (f"{data_hoje} 00:00:00",))
summary = dict(cursor.fetchone())
print(f"  Total de trades: {summary['total']}")
print(f"  Fechados: {summary['fechados']} | Abertos: {summary['abertos']}")
print(f"  Gains: {summary['gains']} | Losses: {summary['losses']}")
print(f"  P&L Total: R$ {summary['total_pnl']:.2f} | Media: R$ {summary['avg_pnl']:.2f}")

# Lista detalhada de trades
print("\n=== DETALHES DOS TRADES DE HOJE ===")
cursor.execute("""
    SELECT * FROM trades
    WHERE entry_time >= ?
    ORDER BY entry_time ASC
""", (f"{data_hoje} 00:00:00",))
for i, row in enumerate(cursor.fetchall(), 1):
    d = dict(row)
    status_icon = "+" if d['status'] == 'CLOSED' and d.get('profit_loss', 0) > 0 else "-" if d['status'] == 'CLOSED' and d.get('profit_loss', 0) < 0 else "O"
    print(f"\n{i}. [{status_icon}] {d['side']} @ {d['entry_time']}")
    print(f"   Entry: {d['entry_price']} | Exit: {d['exit_price']} | Status: {d['status']}")
    print(f"   P&L: R$ {d.get('profit_loss', 'N/A')} ({d.get('return_percentage', 0):.2f}%)")
    print(f"   Magic: {d.get('magic_number')} | Broker ID: {d['broker_trade_id']}")

conn.close()
print("\n" + "=" * 80)

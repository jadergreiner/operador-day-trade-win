#!/usr/bin/env python3
"""
DIAGNÓSTICO RÁPIDO - Trades 26/02/2026 & RLs
Executar imediatamente para responder questões críticas S1-4-LOGGING

Uso: python scripts/DIAGNOSTICO_26FEV_TRADES.py
"""

import sqlite3
import json
from datetime import datetime, timedelta
from pathlib import Path

# ============================================================================
# CONFIG
# ============================================================================

DB_PATH = "data/db/trading.db"
TRADE_IDS = [2276170194, 2276191196, 2276191635]
TARGET_DATE = "2026-02-26"

# ============================================================================
# CONEXÃO
# ============================================================================

def connect_db():
    """Conectar ao trading.db"""
    if not Path(DB_PATH).exists():
        print(f"❌ ERRO: {DB_PATH} não encontrado!")
        return None

    try:
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        return conn
    except Exception as e:
        print(f"❌ Erro ao conectar: {e}")
        return None

# ============================================================================
# QUESTÃO 1: Os 3 trades estão em trading.db?
# ============================================================================

def diagnostico_trades_26fev(conn):
    """Q1: Verificar se 3 trades de 26/02 estão em BD"""
    print("\n" + "="*80)
    print("Q1: OS 3 TRADES DE 26/02 ESTÃO EM trading.db?")
    print("="*80)

    cursor = conn.cursor()

    # Listar estrutura de trades
    try:
        cursor.execute("PRAGMA table_info(trades)")
        columns = cursor.fetchall()
        print(f"\n📋 Colunas da tabela 'trades':")
        for col in columns:
            print(f"   - {col['name']} ({col['type']})")
    except Exception as e:
        print(f"   ⚠️ Erro ao inspecionar colunas: {e}")

    # Q1a: Buscar por order_id
    print(f"\n🔍 Buscando pelos 3 order IDs específicos...")
    for order_id in TRADE_IDS:
        try:
            cursor.execute(
                "SELECT id, order_id, symbol, direction, entry_price, exit_price, entry_time, exit_time, status FROM trades WHERE order_id = ?",
                (order_id,)
            )
            row = cursor.fetchone()
            if row:
                print(f"\n   ✅ Order {order_id} ENCONTRADO:")
                print(f"      ID: {row['id']}")
                print(f"      Symbol: {row['symbol']}")
                print(f"      Direction: {row['direction']}")
                print(f"      Entry: {row['entry_price']} @ {row['entry_time']}")
                print(f"      Exit: {row['exit_price']} @ {row['exit_time']}")
                print(f"      Status: {row['status']}")
            else:
                print(f"\n   ❌ Order {order_id} NÃO ENCONTRADO em trades!")
        except Exception as e:
            print(f"\n   ⚠️ Erro ao buscar {order_id}: {e}")

    # Q1b: Buscar todos trades de 26/02
    print(f"\n🔍 Todos os trades de {TARGET_DATE}...")
    try:
        cursor.execute(
            """
            SELECT id, order_id, symbol, direction, entry_price, exit_price, entry_time, exit_time
            FROM trades
            WHERE date(entry_time) = ?
            ORDER BY entry_time
            """,
            (TARGET_DATE,)
        )
        rows = cursor.fetchall()

        if rows:
            print(f"\n   ✅ {len(rows)} trade(s) encontrado(s) em {TARGET_DATE}:")
            for i, row in enumerate(rows, 1):
                print(f"\n   Trade #{i}:")
                print(f"      Order ID: {row['order_id']}")
                print(f"      Symbol: {row['symbol']}")
                print(f"      Direction: {row['direction']}")
                print(f"      Entry: {row['entry_price']} @ {row['entry_time']}")
                print(f"      Exit: {row['exit_price']} @ {row['exit_time']}")
        else:
            print(f"\n   ⚠️ NENHUM trade encontrado para {TARGET_DATE}!")

            # Mostrar últimos 10 trades como referência
            cursor.execute(
                "SELECT entry_time FROM trades ORDER BY entry_time DESC LIMIT 10"
            )
            last_trades = cursor.fetchall()
            print(f"\n   📌 Últimos 10 trades registrados:")
            for trade in last_trades:
                print(f"      - {trade['entry_time']}")
    except Exception as e:
        print(f"\n   ⚠️ Erro ao buscar trades de {TARGET_DATE}: {e}")

# ============================================================================
# QUESTÃO 2: Por que Trade #1 sem SL/TP?
# ============================================================================

def diagnostico_sl_tp(conn):
    """Q2: Verificar SL/TP do Trade #1"""
    print("\n" + "="*80)
    print("Q2: POR QUE TRADE #1 (2276170194) SEM SL/TP?")
    print("="*80)

    cursor = conn.cursor()

    try:
        # Buscar colunas SL/TP
        cursor.execute("PRAGMA table_info(trades)")
        columns = [col['name'] for col in cursor.fetchall()]

        sl_col = 'stop_loss' if 'stop_loss' in columns else 'sl' if 'sl' in columns else None
        tp_col = 'take_profit' if 'take_profit' in columns else 'tp' if 'tp' in columns else None

        if not sl_col or not tp_col:
            print(f"\n⚠️ Colunas SL/TP não encontradas!")
            print(f"   Colunas disponíveis: {columns}")
            return

        # Buscar trade específico
        cursor.execute(
            f"""
            SELECT order_id, symbol, direction, entry_price, {sl_col}, {tp_col}, entry_time, status
            FROM trades
            WHERE order_id = 2276170194
            """
        )

        row = cursor.fetchone()

        if row:
            print(f"\n   ✅ Trade #2276170194 encontrado:")
            print(f"      Symbol: {row['symbol']}")
            print(f"      Direction: {row['direction']}")
            print(f"      Entry Price: {row['entry_price']}")
            print(f"      Stop Loss: {row[sl_col]} {'❌ NULL/VAZIO!' if row[sl_col] is None else '✅ SET'}")
            print(f"      Take Profit: {row[tp_col]} {'❌ NULL/VAZIO!' if row[tp_col] is None else '✅ SET'}")
            print(f"      Entry Time: {row['entry_time']}")
            print(f"      Status: {row['status']}")

            # Investigação: era esperado SL/TP?
            if row[sl_col] is None and row[tp_col] is None:
                print(f"\n   🔴 ACHADO: Trade executado SEM SL/TP!")
                print(f"   Possíveis causas:")
                print(f"   1. Override manual do trader (sem proteção)")
                print(f"   2. Erro no sistema de execução")
                print(f"   3. Configuração de gates incompleta")
        else:
            print(f"\n   ⚠️ Trade #2276170194 não encontrado!")
    except Exception as e:
        print(f"\n   ⚠️ Erro ao inspecionar SL/TP: {e}")

# ============================================================================
# QUESTÃO 3: Qual é o DELAY persistência?
# ============================================================================

def diagnostico_delay_persistencia(conn):
    """Q3: Medir delay entre execução MT5 e persistência BD"""
    print("\n" + "="*80)
    print("Q3: QUAL É O DELAY ENTRE MT5 E PERSISTÊNCIA?")
    print("="*80)

    cursor = conn.cursor()

    try:
        # Verificar se há tabela de logs
        cursor.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name LIKE '%log%'"
        )
        log_tables = [row[0] for row in cursor.fetchall()]

        if log_tables:
            print(f"\n   📋 Tabelas de log encontradas: {log_tables}")
        else:
            print(f"\n   ⚠️ Nenhuma tabela de log de persistência encontrada")

        # Verificar trades de 26/02 com timing
        cursor.execute(
            """
            SELECT order_id, entry_time, exit_time,
                   CASE WHEN exit_time IS NOT NULL
                        THEN (julianday(exit_time) - julianday(entry_time)) * 86400
                        ELSE NULL
                   END as duration_seconds
            FROM trades
            WHERE date(entry_time) = ?
            ORDER BY entry_time
            """,
            (TARGET_DATE,)
        )

        rows = cursor.fetchall()

        if rows:
            print(f"\n   ✅ Timings de trades {TARGET_DATE}:")
            for row in rows:
                print(f"\n      Order ID: {row['order_id']}")
                print(f"      Entry @ {row['entry_time']}")
                print(f"      Exit @ {row['exit_time']}")
                if row['duration_seconds']:
                    print(f"      Duration: {row['duration_seconds']:.2f}s")
        else:
            print(f"\n   ⚠️ Nenhum timing de trades para {TARGET_DATE}")

        # Consultar sync_mt5_trades_to_db se houver registro
        print(f"\n   🔍 Procurando registros de sincronização...")
        cursor.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name LIKE '%sync%'"
        )
        sync_tables = [row[0] for row in cursor.fetchall()]

        if sync_tables:
            print(f"      Tabelas de sync: {sync_tables}")
        else:
            print(f"      ℹ️ Scripts de sync usam arquivos .log (fora BD)")

    except Exception as e:
        print(f"\n   ⚠️ Erro ao medir delay: {e}")

# ============================================================================
# QUESTÃO 4: RLs foram gerados das 3 trades?
# ============================================================================

def diagnostico_rls_26fev(conn):
    """Q4: Verificar se RLs foram gerados de 3 trades"""
    print("\n" + "="*80)
    print("Q4: FORAM GERADOS RLs DAS 3 TRADES?")
    print("="*80)

    cursor = conn.cursor()

    # Q4a: Verificar tabelas RL
    try:
        cursor.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name LIKE '%rl%'"
        )
        rl_tables = [row[0] for row in cursor.fetchall()]

        print(f"\n   📋 Tabelas RL encontradas:")
        for table in rl_tables:
            print(f"      - {table}")

            # Contar registros
            cursor.execute(f"SELECT COUNT(*) FROM {table}")
            count = cursor.fetchone()[0]
            print(f"        Total registros: {count}")

            # Mostrar últimos registros
            cursor.execute(f"SELECT * FROM {table} ORDER BY -rowid LIMIT 3")
            cols = [description[0] for description in cursor.description]
            latest = cursor.fetchall()

            if latest:
                print(f"        Últimos 3 registros:")
                for record in latest:
                    print(f"          {dict(zip(cols, record))}")
    except Exception as e:
        print(f"\n   ⚠️ Erro ao investigar RLs: {e}")

    # Q4b: Verificar linkage entre trades e episodes
    try:
        cursor.execute(
            """
            SELECT rl_episodes.id, rl_episodes.trade_id, rl_episodes.created_at,
                   trades.order_id
            FROM rl_episodes
            LEFT JOIN trades ON trades.id = rl_episodes.trade_id
            WHERE date(rl_episodes.created_at) = ?
            LIMIT 10
            """,
            (TARGET_DATE,)
        )

        rows = cursor.fetchall()

        if rows:
            print(f"\n   ✅ Episodes linkados para {TARGET_DATE}:")
            for row in rows:
                print(f"      Episode ID: {row[0]}, Trade ID: {row[1]}, Order: {row[3]}, Created: {row[2]}")
        else:
            print(f"\n   ⚠️ Nenhum episode linkado para {TARGET_DATE}")
    except Exception as e:
        print(f"   ℹ️ Erro em linkage (pode ser estrutura diferente): {e}")

# ============================================================================
# MAIN
# ============================================================================

def main():
    """Executar diagnóstico completo"""
    print("\n" + "█"*80)
    print("DIAGNÓSTICO TRADES 26/02/2026 & RLs")
    print("Data Engineer Kit - S1-4-LOGGING Fase 1")
    print("█"*80)
    print(f"\nBP: {DB_PATH}")
    print(f"Data: {TARGET_DATE}")
    print(f"Trade IDs: {TRADE_IDS}")

    conn = connect_db()
    if not conn:
        print("\n❌ Falha ao conectar ao banco. Abortar.")
        return

    try:
        # Executar 4 questionários
        diagnostico_trades_26fev(conn)
        diagnostico_sl_tp(conn)
        diagnostico_delay_persistencia(conn)
        diagnostico_rls_26fev(conn)

        # Resumo
        print("\n" + "="*80)
        print("PRÓXIMOS PASSOS")
        print("="*80)
        print("""
1. ✅ Salve a saída deste script
2. ✅ Preencha TEMPLATE_RESPOSTA_DATA_ENGINEER.md com achados
3. ✅ Responda as 4 questões críticas
4. ✅ Entregue docs/DIAGNOSTICO_DELAY_PERSISTENCIA_26FEV.md
5. ✅ Apresente ao Executor Técnico para validação
        """)

    finally:
        conn.close()
        print("\n✅ Diagnóstico completo!")

if __name__ == "__main__":
    main()

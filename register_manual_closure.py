#!/usr/bin/env python3
"""Registra encerramento de operações manuais WIN no banco de dados."""

import sqlite3
from datetime import datetime
import json

DATABASE_PATH = "data/db/trading.db"

def register_manual_closure():
    """Registra o encerramento das operações manuais."""

    try:
        conn = sqlite3.connect(DATABASE_PATH)
        cursor = conn.cursor()

        timestamp = datetime.now().isoformat()

        # 1. Adiciona entrada de atividade manual (se tabela existir)
        try:
            cursor.execute("""
                INSERT INTO manual_activities (
                    timestamp,
                    activity_type,
                    description,
                    status
                ) VALUES (?, ?, ?, ?)
            """, (
                timestamp,
                'MANUAL_WIN_OPERATION_CLOSURE',
                'Encerramento das operações manuais WIN por horário programado',
                'COMPLETED'
            ))
            print("✅ Atividade registrada na tabela manual_activities")
        except sqlite3.OperationalError as e:
            print(f"ℹ️ Tabela manual_activities não existe: {e}")

        # 2. Registra na tabela de trades com status especial
        try:
            trade_id = f"MANUAL_WIN_CLOSE_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            cursor.execute("""
                INSERT INTO trades (
                    trade_id,
                    symbol,
                    side,
                    quantity,
                    entry_price,
                    entry_time,
                    status,
                    execution_method,
                    notes,
                    created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                trade_id,
                'WINFUT',
                'CLOSE',
                0,
                0.0,
                timestamp,
                'MANUAL_CLOSURE',
                'manual',
                'Encerramento manual de operações WIN ao término do horário',
                timestamp
            ))
            print("✅ Encerramento registrado na tabela trades")
        except sqlite3.IntegrityError as e:
            print(f"⚠️ Erro ao inserir trade: {e}")

        # 3. Cria log estruturado em JSON
        log_entry = {
            "timestamp": timestamp,
            "event_type": "MANUAL_WIN_CLOSURE",
            "reason": "Horário programado de finalização de operações",
            "asset": "WINFUT",
            "status": "COMPLETED",
            "recorded_by": "system"
        }

        try:
            cursor.execute("""
                INSERT INTO trading_journal_logs (
                    entry_id,
                    timestamp,
                    symbol,
                    headline,
                    market_feeling,
                    detailed_narrative,
                    decision,
                    confidence,
                    macro_bias,
                    fundamental_bias,
                    sentiment_bias,
                    technical_bias,
                    alignment_score,
                    market_regime,
                    tags,
                    created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                trade_id,
                timestamp,
                'WINFUT',
                'Encerramento de Operações Manuais WIN',
                'NEUTRAL',
                json.dumps(log_entry, indent=2),
                'CLOSE',
                1.0,
                'NEUTRAL',
                'NEUTRAL',
                'NEUTRAL',
                'NEUTRAL',
                1.0,
                'REGULAR',
                json.dumps(['manual_closure', 'end_of_day'], ensure_ascii=False),
                timestamp
            ))
            print("✅ Log estruturado registrado na tabela trading_journal_logs")
        except sqlite3.OperationalError as e:
            print(f"ℹ️ Erro ao registrar journal log: {e}")

        # Commit de todas as transações
        conn.commit()

        print("\n" + "="*60)
        print("✅ ENCERRAMENTO REGISTRADO COM SUCESSO")
        print("="*60)
        print(f"Timestamp: {timestamp}")
        print(f"Ativo: WINFUT")
        print(f"Motivo: Finalização programada de operações manuais")
        print(f"Database: {DATABASE_PATH}")
        print("="*60 + "\n")

        return True

    except Exception as e:
        print(f"❌ Erro ao registrar: {e}")
        return False

    finally:
        if conn:
            conn.close()


def verify_registration():
    """Verifica se o registro foi salvo corretamente."""

    try:
        conn = sqlite3.connect(DATABASE_PATH)
        cursor = conn.cursor()

        # Verifica último registro na tabela trades
        cursor.execute("""
            SELECT trade_id, symbol, status, created_at
            FROM trades
            WHERE status = 'MANUAL_CLOSURE'
            ORDER BY created_at DESC
            LIMIT 1
        """)

        result = cursor.fetchone()
        if result:
            print("\n📋 ÚLTIMO REGISTRO VERIFIED:")
            print(f"  Trade ID: {result[0]}")
            print(f"  Symbol: {result[1]}")
            print(f"  Status: {result[2]}")
            print(f"  Created: {result[3]}\n")
            return True
        else:
            print("⚠️ Nenhum registro MANUAL_CLOSURE encontrado")
            return False

    except Exception as e:
        print(f"❌ Erro ao verificar: {e}")
        return False

    finally:
        if conn:
            conn.close()


if __name__ == "__main__":
    print("\n🔄 Registrando encerramento de operações manuais WIN...\n")

    if register_manual_closure():
        verify_registration()
    else:
        print("❌ Falha ao registrar encerramento")

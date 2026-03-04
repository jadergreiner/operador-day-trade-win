#!/usr/bin/env python3
"""Inicia FastAPI server em background."""

import sys
import os
from pathlib import Path
import sqlite3

# Setup path
root_dir = Path(__file__).parent.parent
if str(root_dir) not in sys.path:
    sys.path.insert(0, str(root_dir))

import uvicorn
from src.application.orders_executor import OrdersExecutor
from src.interfaces.api.fastapi_server import create_app


def create_database_tables():
    """Cria tabelas SQLite para P0-1 se não existirem."""
    db_path = root_dir / "data" / "db" / "trading.db"
    
    try:
        conn = sqlite3.connect(str(db_path))
        cursor = conn.cursor()
        
        # Tabela api_orders
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS api_orders (
                order_id TEXT PRIMARY KEY,
                symbol TEXT NOT NULL,
                order_type TEXT NOT NULL,
                volume REAL NOT NULL,
                entry_price REAL NOT NULL,
                stop_loss REAL NOT NULL,
                take_profit REAL NOT NULL,
                ml_score REAL,
                detector_spike REAL,
                trader_approval BOOLEAN DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Tabela api_audit_log
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS api_audit_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                order_id TEXT NOT NULL,
                state TEXT NOT NULL,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                message TEXT,
                metadata TEXT,
                FOREIGN KEY (order_id) REFERENCES api_orders(order_id)
            )
        """)
        
        # Criar índices
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_api_orders_symbol ON api_orders(symbol)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_api_audit_order ON api_audit_log(order_id)")
        
        conn.commit()
        conn.close()
        print("[DB] Tabelas SQLite criadas/validadas com sucesso")
    except Exception as e:
        print(f"[WARN] Erro criando tabelas: {e}")


# Criar executor singleton
executor = OrdersExecutor()

# Criar app
app = create_app(executor)

if __name__ == "__main__":
    # Criar tabelas SQLite
    create_database_tables()
    
    print("\n" + "="*60)
    print("🚀 INICIANDO API REST MT5 (P0-1)")
    print("="*60)
    print(f"  Servidor: http://localhost:8888")
    print(f"  Docs: http://localhost:8888/docs")
    print(f"  Health: http://localhost:8888/health")
    print("="*60 + "\n")
    
    # Rodar Uvicorn
    uvicorn.run(
        app,
        host="127.0.0.1",
        port=8888,
        log_level="info"
    )

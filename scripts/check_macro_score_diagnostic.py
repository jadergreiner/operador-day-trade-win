import sys
import os
import logging
from decimal import Decimal

# Configurar logging basico para ver o que esta acontecendo
logging.basicConfig(level=logging.INFO)

ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

from src.infrastructure.adapters.mt5_adapter import MT5Adapter
from src.application.services.macro_score.engine import MacroScoreEngine
from config import get_config

def diagnostic():
    config = get_config()
    mt5 = MT5Adapter(
        login=config.mt5_login,
        password=config.mt5_password,
        server=config.mt5_server,
    )

    if not mt5.connect():
        print("FAIL: MT5 connection failed.")
        return

    try:
        engine = MacroScoreEngine(mt5)
        print("\n--- Diagnosticando Macro Score ---")
        result = engine.analyze()

        print(f"\nSinal: {result.signal}")
        print(f"Score Final: {result.score_final}")
        print(f"Disponiveis: {result.items_available} / {result.total_items}")

        print("\n--- Detalhes dos Itens (Nao Disponiveis) ---")
        unavailable = [i for i in result.items if not i.available]
        for item in unavailable[:10]:
            print(f"  [X] {item.symbol}: {item.detail}")
        if len(unavailable) > 10:
            print(f"  ... (+ {len(unavailable)-10} outros)")

        print("\n--- Detalhes dos Itens (Disponiveis com Score 0) ---")
        zeros = [i for i in result.items if i.available and i.final_score == 0]
        for item in zeros[:10]:
            print(f"  [0] {item.symbol}: {item.detail}")
        if len(zeros) > 10:
            print(f"  ... (+ {len(zeros)-10} outros)")

        print("\n--- Detalhes dos Itens (Com Score Ativo) ---")
        active = [i for i in result.items if i.available and i.final_score != 0]
        for item in active:
            print(f"  [{item.final_score:+d}] {item.symbol}: {item.detail}")

    finally:
        mt5.disconnect()

if __name__ == "__main__":
    diagnostic()

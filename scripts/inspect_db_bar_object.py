"""Inspeciona o objeto da primeira barra M15 salvo no DB para um símbolo.

Uso: python scripts/inspect_db_bar_object.py SYMBOL DD/MM/YYYY
Ex: python scripts/inspect_db_bar_object.py IBOV 06/02/2026
"""
import sys
from pathlib import Path
from datetime import datetime

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from config import get_config
from src.infrastructure.adapters.mt5_adapter import MT5Adapter
from src.application.services.backtest.historical_data_provider import HistoricalDataProvider
from src.application.services.macro_score.item_registry import get_item_registry


def main():
    if len(sys.argv) < 3:
        print('Uso: python scripts/inspect_db_bar_object.py SYMBOL DD/MM/YYYY')
        return
    symbol = sys.argv[1]
    date = datetime.strptime(sys.argv[2], '%d/%m/%Y')

    config = get_config()
    adapter = MT5Adapter(login=config.mt5_login, password=config.mt5_password, server=config.mt5_server)
    adapter.connect()

    provider = HistoricalDataProvider(mt5_adapter=adapter, date=date)
    provider.load_all(get_item_registry())

    day_start = date.replace(hour=0, minute=0, second=0, microsecond=0)
    bars = provider._load_m15_from_db(symbol, day_start)
    print('bars type:', type(bars))
    if not bars:
        print('Nenhuma barra encontrada no DB para', symbol)
    else:
        first = bars[0]
        print('first type:', type(first))
        try:
            print('dir(first) sample:', [a for a in dir(first) if not a.startswith('_')][:80])
        except Exception as e:
            print('dir failed:', e)
        try:
            print('as dict (first.__dict__):')
            print(first.__dict__)
        except Exception:
            print('first has no __dict__')
        # try common attribute names
        for attr in ('timestamp', 'time', 'open', 'close'):
            print(attr, getattr(first, attr, None))

    adapter.disconnect()


if __name__ == '__main__':
    main()

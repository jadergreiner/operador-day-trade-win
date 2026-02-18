"""Debug: lista disponibilidade de dados por simbolo para a barra indexada (0-based).

Uso: python scripts/debug_bar_availability.py DD/MM/YYYY BAR_INDEX
Ex: python scripts/debug_bar_availability.py 05/02/2026 0
"""
import sys
from pathlib import Path
from datetime import datetime

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from config import get_config
from src.infrastructure.adapters.mt5_adapter import MT5Adapter
from src.application.services.macro_score.item_registry import get_item_registry
from src.application.services.backtest.historical_data_provider import HistoricalDataProvider


def main():
    if len(sys.argv) < 3:
        print('Uso: python scripts/debug_bar_availability.py DD/MM/YYYY BAR_INDEX')
        return
    date = datetime.strptime(sys.argv[1], '%d/%m/%Y')
    bar_index = int(sys.argv[2])

    config = get_config()
    adapter = MT5Adapter(login=config.mt5_login, password=config.mt5_password, server=config.mt5_server)
    adapter.connect()

    registry = get_item_registry()
    provider = HistoricalDataProvider(mt5_adapter=adapter, date=date)
    provider.load_all(registry)

    total_items = len([
        i for i in registry
        if i.scoring_type.name != 'TECHNICAL_INDICATOR' and not provider.is_registry_symbol_blacklisted(i.symbol)
    ])

    available = []
    missing = []
    for item in registry:
        if item.scoring_type.name == 'TECHNICAL_INDICATOR':
            continue
        if provider.is_registry_symbol_blacklisted(item.symbol):
            continue
        resolved = provider.get_resolved_symbol(item.symbol)
        price = None
        if resolved:
            price = provider.get_price_at_bar(resolved, bar_index)
        if price is not None:
            available.append((item.symbol, resolved, float(price)))
        else:
            missing.append((item.symbol, resolved))

    print(f'Total items considered: {total_items}')
    print(f'Available at bar {bar_index}: {len(available)}')
    for s in available[:30]:
        print(' +', s)
    print(f'Missing at bar {bar_index}: {len(missing)}')
    for s in missing[:50]:
        print(' -', s)

    adapter.disconnect()


if __name__ == '__main__':
    main()

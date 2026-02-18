"""Carrega dados historicos via HistoricalDataProvider e verifica por que simbolos falharam.

Usage:
    python scripts/check_failed_symbols.py DD/MM/YYYY

Exemplo:
    python scripts/check_failed_symbols.py 05/02/2026
"""
import sys
from datetime import datetime, timedelta
from pathlib import Path

# ensure project root on path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from config import get_config
from src.infrastructure.adapters.mt5_adapter import MT5Adapter
from src.application.services.macro_score.item_registry import get_item_registry
from src.application.services.backtest.historical_data_provider import HistoricalDataProvider


def main():
    if len(sys.argv) < 2:
        print('Uso: python scripts/check_failed_symbols.py DD/MM/YYYY')
        return
    try:
        date = datetime.strptime(sys.argv[1], '%d/%m/%Y')
    except Exception:
        print('Formato de data invalido. Use DD/MM/YYYY')
        return

    config = get_config()
    adapter = MT5Adapter(login=config.mt5_login, password=config.mt5_password, server=config.mt5_server)
    print('Conectando MT5...')
    adapter.connect()

    registry = get_item_registry()
    provider = HistoricalDataProvider(mt5_adapter=adapter, date=date)
    provider.load_all(registry)

    print('\nLoad errors:')
    for err in provider.load_errors:
        print(' -', err)

    print('\nChecking MT5 directly for failed/resolved symbols:')
    day_start = date.replace(hour=9, minute=0, second=0)
    day_end = date.replace(hour=23, minute=59, second=59)

    for registry_item in registry:
        # skip technical indicators
        if registry_item.scoring_type.name == 'TECHNICAL_INDICATOR':
            continue
        key = registry_item.symbol
        resolved = provider.get_resolved_symbol(key)
        if resolved is None:
            print(f'{key}: not resolved by provider')
            continue
        # query MT5 directly using adapter
        try:
            # use adapter's mt5 instance
            mt5 = adapter._mt5
            # ensure symbol selected
            mt5.symbol_select(resolved, True)
            rates = mt5.copy_rates_range(resolved, mt5.TIMEFRAME_M15, day_start, day_end)
            n = len(rates) if rates is not None else 0
            print(f'{key} -> {resolved}: MT5 M15 bars = {n}')
        except Exception as e:
            print(f'{key} -> {resolved}: error querying MT5: {e}')

    adapter.disconnect()


if __name__ == '__main__':
    main()

"""Encontra o horário da primeira barra M15 disponível por símbolo para uma data.

Uso: python scripts/find_first_bar_times.py DD/MM/YYYY
Ex: python scripts/find_first_bar_times.py 06/02/2026
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


def extract_time_from_bars(bars):
    if not bars:
        return None
    first = bars[0]
    # sqlalchemy model
    if hasattr(first, 'timestamp'):
        return first.timestamp
    if hasattr(first, 'time'):
        return first.time
    # dict-like
    try:
        if isinstance(first, dict):
            return first.get('timestamp') or first.get('time') or first.get('datetime')
    except Exception:
        pass
    # numpy/tuple record
    try:
        if hasattr(first, 'tolist'):
            # attempt common fields
            for k in ('time', 'timestamp'):
                if k in first.dtype.names:
                    return first[k]
    except Exception:
        pass
    return None


def main():
    if len(sys.argv) < 2:
        print('Uso: python scripts/find_first_bar_times.py DD/MM/YYYY')
        return
    date = datetime.strptime(sys.argv[1], '%d/%m/%Y')

    config = get_config()
    adapter = MT5Adapter(login=config.mt5_login, password=config.mt5_password, server=config.mt5_server)
    adapter.connect()

    registry = get_item_registry()
    provider = HistoricalDataProvider(mt5_adapter=adapter, date=date)
    provider.load_all(registry)

    results = []
    missing = []
    day_start = date.replace(hour=0, minute=0, second=0, microsecond=0)
    for item in registry:
        if item.scoring_type.name == 'TECHNICAL_INDICATOR':
            continue
        if provider.is_registry_symbol_blacklisted(item.symbol):
            continue
        resolved = provider.get_resolved_symbol(item.symbol)
        if not resolved:
            missing.append((item.symbol, None))
            continue
        bars = None
        try:
            bars = provider._load_m15_from_db(resolved, day_start)
        except Exception:
            bars = None
        first_time = extract_time_from_bars(bars)
        if first_time is None:
            missing.append((item.symbol, resolved))
        else:
            results.append((item.symbol, resolved, first_time))

    # sort by time
    results.sort(key=lambda x: x[2])

    print(f'Encontrados {len(results)} símbolos com M15 (primeiro horário) e {len(missing)} sem M15')
    for sym, res, t in results:
        print(f'+ {sym} -> {res} @ {t}')
    if missing:
        print('\nSem M15 (ou sem registro resolvido):')
        for sym, res in missing:
            print(f'- {sym} -> {res}')

    adapter.disconnect()


if __name__ == '__main__':
    main()

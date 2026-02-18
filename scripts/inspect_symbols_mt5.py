"""Inspeciona símbolos no MetaTrader5: busca correspondências e verifica barras M15 na data.

Uso: python scripts/inspect_symbols_mt5.py

Alvo de data fixo: 2026-02-05 (pode ser alterado no código)
"""
from datetime import datetime, timedelta
import MetaTrader5 as mt5
import os

TARGET_DATE = datetime(2026, 2, 5)
SYMBOLS = [
    'CNYG26', 'ZARG26', 'TRYG26', 'CLPH26', 'HSIG26'
]


def load_env_mt5():
    login = os.environ.get('MT5_LOGIN')
    pwd = os.environ.get('MT5_PASSWORD')
    server = os.environ.get('MT5_SERVER')
    if login and pwd and server:
        return int(login), pwd, server
    # try .env
    try:
        with open('.env', 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if line.startswith('MT5_LOGIN='):
                    login = line.split('=',1)[1].strip()
                if line.startswith('MT5_PASSWORD='):
                    pwd = line.split('=',1)[1].strip()
                if line.startswith('MT5_SERVER='):
                    server = line.split('=',1)[1].strip()
        if login and pwd and server:
            return int(login), pwd, server
    except Exception:
        pass
    return None, None, None


def find_matches(name):
    # try exact, startswith, contains
    syms = mt5.symbols_get()
    if not syms:
        return []
    names = [s.name for s in syms]
    matches = [n for n in names if n == name]
    if matches:
        return matches
    matches = [n for n in names if n.startswith(name)]
    if matches:
        return matches
    matches = [n for n in names if name in n]
    return matches


def check_symbol(sym, day):
    # ensure selected
    sel = mt5.symbol_select(sym, True)
    sel_ok = bool(sel)
    start = day.replace(hour=0, minute=0, second=0)
    end = day.replace(hour=23, minute=59, second=59)
    rates = None
    try:
        rates = mt5.copy_rates_range(sym, mt5.TIMEFRAME_M15, start, end)
    except Exception as e:
        rates = None
    n = len(rates) if rates is not None else 0
    sample = None
    if n > 0:
        r = rates[0]
        sample = (datetime.fromtimestamp(int(r['time'])).strftime('%Y-%m-%d %H:%M:%S'), float(r['open']), float(r['high']), float(r['low']), float(r['close']))
    return sel_ok, n, sample


def main():
    if not mt5.initialize():
        print('mt5.initialize failed', mt5.last_error())
        return
    # try login if possible
    login, pwd, server = load_env_mt5()
    if login:
        ok = mt5.login(login=login, password=pwd, server=server)
        if not ok:
            print('mt5.login falhou:', mt5.last_error())

    print('Inspecting symbols on MT5 for date', TARGET_DATE.date())
    syms_all = mt5.symbols_get() or []
    print('Total symbols in MarketWatch:', len(syms_all))

    for name in SYMBOLS:
        print('\n--', name)
        matches = find_matches(name)
        if not matches:
            print(' No matches found in MT5 symbols list')
            continue
        print(' Matches:', matches)
        for m in matches:
            sel_ok, n, sample = check_symbol(m, TARGET_DATE)
            print(f'  {m}: symbol_select={sel_ok}, M15 bars on date={n}')
            if sample:
                print('   sample:', sample)

    mt5.shutdown()


if __name__ == '__main__':
    main()

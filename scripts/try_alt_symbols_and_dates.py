"""Tenta variações de vencimento e testa várias datas para símbolos problemáticos.

Uso: python scripts/try_alt_symbols_and_dates.py

Resultados: imprime combos encontrados e quantidade de barras M15 por dia.
"""
from datetime import datetime
import MetaTrader5 as mt5
import os

BASE_SYMBOLS = [
    'CNYG26', 'ZARG26', 'TRYG26', 'CLPH26', 'HSIG26'
]

# candidate suffixes to try (common futures expiries / month codes)
SUFFIXES = ['', 'G26', 'H26', 'J26', 'K26', 'M26', 'N26', 'Q26', 'V26', 'Z26', '27', '26']

DATES = [
    datetime(2026, 2, 4),
    datetime(2026, 2, 5),
    datetime(2026, 2, 6),
]


def load_env_mt5():
    login = os.environ.get('MT5_LOGIN')
    pwd = os.environ.get('MT5_PASSWORD')
    server = os.environ.get('MT5_SERVER')
    if login and pwd and server:
        return int(login), pwd, server
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


def symbol_candidates(base):
    # if base already contains a month/year suffix, also try without
    yield base
    # try stripping trailing year digits and month letter combos
    if len(base) > 3:
        core = base.rstrip('0123456789')
        if core != base:
            yield core
    for s in SUFFIXES:
        if s and s != base:
            # if base already contains letter/num suffix, replace it
            # attempt simple replacement of last 3 chars
            candidate = base[: -3] + s if len(base) > 3 else base + s
            yield candidate


def check_candidate(sym, day):
    try:
        mt5.symbol_select(sym, True)
    except Exception:
        pass
    start = day.replace(hour=0, minute=0, second=0)
    end = day.replace(hour=23, minute=59, second=59)
    try:
        rates = mt5.copy_rates_range(sym, mt5.TIMEFRAME_M15, start, end)
    except Exception:
        rates = None
    n = len(rates) if rates is not None else 0
    return n


def main():
    if not mt5.initialize():
        print('mt5.initialize failed', mt5.last_error())
        return
    login, pwd, server = load_env_mt5()
    if login:
        mt5.login(login=login, password=pwd, server=server)

    # build list of all available symbol names for faster membership test
    all_syms = [s.name for s in (mt5.symbols_get() or [])]

    for base in BASE_SYMBOLS:
        print('\n====', base)
        tried = set()
        for cand in symbol_candidates(base):
            if cand in tried:
                continue
            tried.add(cand)
            # check if present in MT5 symbol list
            present = cand in all_syms
            print('\n candidate:', cand, 'present_in_marketwatch=', present)
            for d in DATES:
                n = check_candidate(cand, d) if present else 0
                print(f'  {d.date()}: M15 bars = {n}')

    mt5.shutdown()


if __name__ == '__main__':
    main()

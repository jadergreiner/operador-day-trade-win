"""Verifica disponibilidade de barras em diferentes timeframes para símbolos problemáticos.

Uso: python scripts/check_timeframes_mt5.py
"""
from datetime import datetime
import MetaTrader5 as mt5
import os

SYMBOLS_FILE = os.path.join('data', 'bad_symbols.txt')
DATES = [datetime(2026,2,4), datetime(2026,2,5), datetime(2026,2,6)]
TIMEFRAMES = [
    ('M1', mt5.TIMEFRAME_M1),
    ('M5', mt5.TIMEFRAME_M5),
    ('M15', mt5.TIMEFRAME_M15),
    ('M30', mt5.TIMEFRAME_M30),
    ('H1', mt5.TIMEFRAME_H1),
    ('H4', mt5.TIMEFRAME_H4),
    ('D1', mt5.TIMEFRAME_D1),
]


def load_symbols():
    if not os.path.exists(SYMBOLS_FILE):
        return []
    with open(SYMBOLS_FILE, 'r', encoding='utf-8') as f:
        return [line.strip() for line in f if line.strip() and not line.strip().startswith('#')]


def main():
    if not mt5.initialize():
        print('mt5.initialize failed', mt5.last_error())
        return
    # try login from .env if present
    try:
        with open('.env','r',encoding='utf-8') as f:
            env = f.read()
            if 'MT5_LOGIN' in env:
                # best-effort login
                import re
                m_login = re.search(r'MT5_LOGIN=(\d+)', env)
                m_pwd = re.search(r'MT5_PASSWORD=(.+)', env)
                m_srv = re.search(r'MT5_SERVER=(.+)', env)
                if m_login and m_pwd and m_srv:
                    try:
                        mt5.login(login=int(m_login.group(1)), password=m_pwd.group(1).strip(), server=m_srv.group(1).strip())
                    except Exception:
                        pass
    except FileNotFoundError:
        pass

    symbols = load_symbols()
    print('Testing timeframes for symbols:', symbols)

    for sym in symbols:
        print('\n==', sym)
        # ensure symbol selected
        try:
            mt5.symbol_select(sym, True)
        except Exception:
            pass
        for tf_name, tf_const in TIMEFRAMES:
            for d in DATES:
                start = d.replace(hour=0, minute=0, second=0)
                end = d.replace(hour=23, minute=59, second=59)
                try:
                    rates = mt5.copy_rates_range(sym, tf_const, start, end)
                except Exception:
                    rates = None
                n = len(rates) if rates is not None else 0
                print(f' {tf_name} {d.date()}: {n}')

    mt5.shutdown()


if __name__ == '__main__':
    main()

"""Consulta o MetaTrader5 diretamente para barras M15 de um simbolo/data/hora.

Uso:
    python scripts/check_mt5_marketdata.py SYMBOL YYYY-MM-DD [HH:MM|HH:MM-HH:MM]
Ex: python scripts/check_mt5_marketdata.py "WIN$N" 2026-02-05 09:00
"""
import sys
from datetime import datetime, timedelta

try:
    import MetaTrader5 as mt5
except Exception as e:
    print('MetaTrader5 package not available:', e)
    sys.exit(1)

def load_env_mt5():
    # try environment variables first
    import os

    login = os.environ.get('MT5_LOGIN')
    pwd = os.environ.get('MT5_PASSWORD')
    server = os.environ.get('MT5_SERVER')
    if login and pwd and server:
        return int(login), pwd, server

    # fallback: parse .env file in repo root
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
    except FileNotFoundError:
        pass

    return None, None, None

def parse_time_arg(day, time_arg):
    if not time_arg:
        start = datetime.fromisoformat(f"{day}T00:00:00")
        end = datetime.fromisoformat(f"{day}T23:59:59")
        return start, end
    if '-' in time_arg:
        t0, t1 = time_arg.split('-', 1)
        start = datetime.fromisoformat(f"{day}T{t0}")
        end = datetime.fromisoformat(f"{day}T{t1}")
        return start, end
    # single time -> M15 window
    start = datetime.fromisoformat(f"{day}T{time_arg}")
    end = start + timedelta(minutes=14, seconds=59)
    return start, end

def main():
    if len(sys.argv) < 3:
        print('Uso: scripts/check_mt5_marketdata.py SYMBOL YYYY-MM-DD [HH:MM|HH:MM-HH:MM]')
        return
    symbol = sys.argv[1]
    day = sys.argv[2]
    time_arg = sys.argv[3] if len(sys.argv) >= 4 else None

    start_dt, end_dt = parse_time_arg(day, time_arg)

    if not mt5.initialize():
        print('mt5.initialize() falhou:', mt5.last_error())
        sys.exit(1)

    # try login if credentials available
    login, pwd, server = load_env_mt5()
    if login and pwd and server:
        ok = mt5.login(login=login, password=pwd, server=server)
        if not ok:
            print('mt5.login falhou:', mt5.last_error())
            # continue anyway; sometimes historical data is available without explicit login

    try:
        # ensure symbol is selected in Market Watch
        selected = mt5.symbol_select(symbol, True)
        if not selected:
            print(f'Warning: symbol_select returned {selected} for {symbol}')
        tf = mt5.TIMEFRAME_M15
        print(f'Buscando {symbol} M15 entre {start_dt} e {end_dt} via MT5...')
        rates = mt5.copy_rates_range(symbol, tf, start_dt, end_dt)
        if rates is None:
            print('Nenhuma resposta do MT5 (None). Erro:', mt5.last_error())
            return
        n = len(rates)
        print(f'Found {n} M15 bars for {symbol} between {start_dt} and {end_dt}')
        names = rates.dtype.names if hasattr(rates, 'dtype') else []
        for i, r in enumerate(rates[:20]):
            # structured array fields: time, open, high, low, close, tick_volume
            t = datetime.fromtimestamp(int(r['time']))
            vol = 0
            if 'tick_volume' in names:
                vol = int(r['tick_volume'])
            elif 'real_volume' in names:
                vol = int(r['real_volume'])
            print(i+1, t.strftime('%Y-%m-%d %H:%M:%S'), float(r['open']), float(r['high']), float(r['low']), float(r['close']), vol)
    finally:
        mt5.shutdown()

if __name__ == '__main__':
    main()

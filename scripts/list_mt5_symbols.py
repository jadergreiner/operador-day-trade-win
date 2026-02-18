"""Lista simbolos disponiveis no MT5 filtrando por prefixo (ex: WIN)."""
import MetaTrader5 as mt5

def main():
    if not mt5.initialize():
        print('mt5.initialize failed', mt5.last_error())
        return
    try:
        syms = mt5.symbols_get('WIN*')
        if syms is None:
            print('symbols_get returned None')
            return
        print('Found', len(syms), 'symbols matching WIN*')
        for s in syms:
            print(s.name)
    finally:
        mt5.shutdown()

if __name__ == '__main__':
    main()

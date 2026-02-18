"""Diagnostic: test futures resolver flow."""
import MetaTrader5 as mt5

mt5.initialize()

# Test $N continuous contracts
print("=== CONTRATOS CONTINUOS ($N) ===")
continuous = ['WDO$N', 'DOL$N', 'DI1$N', 'CCM$N', 'WSP$N', 'BGI$N', 'BIT$N', 'T10$N', 'ICF$N']
for sym in continuous:
    sel = mt5.symbol_select(sym, True)
    print(f'{sym}: select={sel} (type={type(sel).__name__})', end='')
    if sel:
        tick = mt5.symbol_info_tick(sym)
        has_tick = tick is not None
        print(f', tick={has_tick}', end='')
        if has_tick:
            print(f', last={tick.last}', end='')
    print()

# Test dated contracts
print("\n=== CONTRATOS DATADOS ===")
dated = ['DI1F27', 'WDOF27', 'GLDG26', 'SJCH26', 'ETHG26', 'HSIG26', 'DDIF27', 'ETRG26', 'SOLG26']
for sym in dated:
    sel = mt5.symbol_select(sym, True)
    print(f'{sym}: select={sel} (type={type(sel).__name__})', end='')
    if sel:
        tick = mt5.symbol_info_tick(sym)
        has_tick = tick is not None
        print(f', tick={has_tick}', end='')
        if has_tick:
            print(f', last={tick.last}', end='')
    print()

# Test select_symbol via adapter
print("\n=== TESTE VIA MT5Adapter._symbol_exists ===")
import sys
sys.path.insert(0, '.')
from src.infrastructure.adapters.mt5_adapter import MT5Adapter

adapter = MT5Adapter()
adapter.connect()

# Test _symbol_exists equivalent
for sym in ['WDO$N', 'DOL$N', 'DI1$N', 'DI1F27']:
    selected = adapter.select_symbol(sym)
    print(f'{sym}: adapter.select_symbol={selected} (type={type(selected).__name__})', end='')
    if selected:
        tick = adapter.get_symbol_info_tick(sym)
        print(f', tick={tick is not None}', end='')
        if tick:
            print(f', last={tick.last}', end='')
    print()

# Test the full resolver
print("\n=== TESTE FuturesContractResolver ===")
from src.application.services.macro_score.futures_resolver import FuturesContractResolver
resolver = FuturesContractResolver(adapter)
test_symbols = ['WDO', 'DOL', 'DI', 'DI1F', 'DI1N', 'DI1J', 'CCM', 'ICF', 'SJC', 'BGI', 'DAP',
                'GLDG', 'BIT', 'ETH', 'SOL', 'ETR', 'WSP', 'HSI', 'DDI', 'T10', 'DI1F27', 'DI1F29']
for sym in test_symbols:
    result = resolver.resolve(sym)
    print(f'{sym} -> {result}')

adapter.disconnect()

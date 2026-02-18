"""Diagnostic: why symbol_select returns False for futures."""
import MetaTrader5 as mt5

mt5.initialize()
print(f"Account: {mt5.account_info().login}")
print(f"Server: {mt5.account_info().server}")

# Check symbol_info details (not tick, the full info)
symbols_to_check = ['WDO$N', 'DOL$N', 'WIN$N', 'DI1$N', 'DI1F27', 'CCM$N', 'PETR4', 'VALE3', 'IBOV']

for sym in symbols_to_check:
    info = mt5.symbol_info(sym)
    if info:
        print(f"\n{sym}:")
        print(f"  visible={info.visible}, select={info.select}")
        print(f"  trade_mode={info.trade_mode}, path={info.path}")
        print(f"  session_deals={info.session_deals}")
        # Try to select
        result = mt5.symbol_select(sym, True)
        err = mt5.last_error()
        print(f"  symbol_select={result}, last_error={err}")
        # Check info after select
        info2 = mt5.symbol_info(sym)
        if info2:
            print(f"  after_select: visible={info2.visible}")
    else:
        err = mt5.last_error()
        print(f"\n{sym}: NOT FOUND, error={err}")

# Also test what symbols are visible (in Market Watch)
print("\n=== SYMBOLS VISIBLE IN MARKET WATCH ===")
visible = mt5.symbols_get()
visible_names = [s.name for s in visible] if visible else []
futures_visible = [s for s in visible_names if any(s.startswith(p) for p in ['WDO', 'DOL', 'WIN', 'DI1', 'CCM'])]
print(f"Visible futures: {futures_visible[:20]}")
print(f"Total visible: {len(visible_names)}")

# Check if any futures from symbols_get can be selected
print("\n=== SYMBOLS_GET vs VISIBLE ===")
all_wdo = mt5.symbols_get("WDO*")
if all_wdo:
    for s in all_wdo[:5]:
        print(f"  {s.name}: visible={s.visible}, trade_mode={s.trade_mode}, select={s.select}")

mt5.shutdown()

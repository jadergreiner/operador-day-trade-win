
import sys
from pathlib import Path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.infrastructure.adapters.mt5_adapter import MT5Adapter
from src.domain.value_objects import Symbol
from config import get_config

def get_all_prices():
    config = get_config()
    mt5 = MT5Adapter(login=config.mt5_login, password=config.mt5_password, server=config.mt5_server)
    if mt5.connect():
        import MetaTrader5 as mt5_lib
        symbols = {
            "WIN": "WIN$N",
            "WDO": "WDO$N",
            "WSP": "WSP$N",
            "PETR4": "PETR4",
            "VALE3": "VALE3"
        }
        print("COTACOES ATUAIS:")
        for name, s in symbols.items():
            try:
                # Ensure symbol is selected
                mt5_lib.symbol_select(s, True)
                tick = mt5_lib.symbol_info_tick(s)
                if tick:
                    price = tick.last if tick.last > 0 else (tick.bid + tick.ask) / 2
                    print(f"{name} ({s}): R$ {price:,.2f} [Last: {tick.last}, Bid: {tick.bid}, Ask: {tick.ask}]")
                else:
                    print(f"{name}: tick not found")
            except Exception as e:
                print(f"{name}: ERRO - {e}")
        mt5.disconnect()

if __name__ == '__main__':
    get_all_prices()

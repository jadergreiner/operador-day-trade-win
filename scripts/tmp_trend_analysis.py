
import sys
from pathlib import Path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.infrastructure.adapters.mt5_adapter import MT5Adapter, TimeFrame
from src.domain.value_objects import Symbol
from config import get_config
from datetime import datetime

def analyze_recent_trends():
    config = get_config()
    mt5 = MT5Adapter(login=config.mt5_login, password=config.mt5_password, server=config.mt5_server)
    if not mt5.connect():
        print("Erro ao conectar ao MT5")
        return

    symbols = {
        "WIN": "WIN$N",
        "WDO": "WDO$N",
        "WSP": "WSP$N",
        "PETR4": "PETR4",
        "VALE3": "VALE3"
    }

    print(f"ANÁLISE DE TENDÊNCIA RECENTE - {datetime.now().strftime('%H:%M:%S')}")
    print("-" * 50)

    for name, code in symbols.items():
        candles = mt5.get_candles(Symbol(code=code), TimeFrame.M5, count=12) # last hour
        if candles:
            last = candles[-1].close.value
            first = candles[0].open.value
            change = ((last - first) / first) * 100

            # Check acceleration (last 3 candles vs average)
            last_3_avg = sum(abs(c.close.value - c.open.value) for c in candles[-3:]) / 3
            total_avg = sum(abs(c.close.value - c.open.value) for c in candles) / 12
            strength = "ACELERANDO" if last_3_avg > total_avg else "PERDENDO FORÇA"

            trend = "ALTA" if last > first else "BAIXA"
            print(f"{name:5}: R$ {last:10.2f} | Tend. (1h): {trend} ({change:+.2f}%) | {strength}")

            if name == "WIN":
                h_day = max(c.high.value for c in candles)
                l_day = min(c.low.value for c in candles)
                print(f"       Range (1h): {h_day:.2f} - {l_day:.2f}")

    mt5.disconnect()

if __name__ == '__main__':
    analyze_recent_trends()

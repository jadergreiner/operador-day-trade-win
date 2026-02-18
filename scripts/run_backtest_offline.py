"""
Offline backtest runner using CSV exports as a fake MT5 adapter.

Usage:
    python scripts/run_backtest_offline.py [DD/MM/YYYY]

If no date is provided, defaults to 06/02/2026 (matches sample data).
"""
from datetime import datetime
from pathlib import Path
import sys

# Ensure project root is on sys.path (same approach as scripts/run_backtest.py)
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))
import csv
from decimal import Decimal
from typing import List, Optional

from src.application.services.backtest.historical_data_provider import HistoricalDataProvider
from src.application.services.backtest.display import BacktestDisplay
from src.application.services.macro_score.item_registry import get_item_registry
from src.application.services.backtest.backtest_engine import BacktestMacroScoreEngine
from src.application.services.macro_score.technical_scorer import TechnicalIndicatorScorer
from src.application.services.macro_score.forex_handler import ForexScoreHandler
from src.domain.enums.trading_enums import TimeFrame
from src.infrastructure.adapters.mt5_adapter import TickData, Candle, MT5Adapter
from src.domain.value_objects import Symbol, Price
from datetime import datetime as dt, timedelta


class FakeMT5Adapter(MT5Adapter):
    """A minimal fake MT5 adapter that reads CSV files from data/export.

    It implements the subset used by the backtest: connect/disconnect/is_connected,
    get_candles, get_daily_candle, get_available_symbols, select_symbol,
    get_symbol_info_tick.
    """

    def __init__(self, export_dir: Optional[str] = None):
        # no super init needed
        self.export_dir = Path(export_dir or Path(__file__).parents[1] / "data" / "export")
        self._connected = True
        # cache loaded data: symbol -> list of dict rows
        self._data = {}

    def connect(self) -> bool:
        self._connected = True
        return True

    def disconnect(self) -> None:
        self._connected = False

    def is_connected(self) -> bool:
        return self._connected

    def _load_csv(self, symbol_code: str) -> List[dict]:
        if symbol_code in self._data:
            return self._data[symbol_code]

        # Find file starting with symbol_code
        pattern = f"{symbol_code}_"
        found = None
        for f in self.export_dir.iterdir():
            if f.name.upper().startswith(symbol_code.upper() + "_"):
                found = f
                break

        if not found:
            # try exact match with code (some files may be like IBOV_B_0_5min.csv)
            for f in self.export_dir.iterdir():
                if f.name.upper().startswith(symbol_code.upper()):
                    found = f
                    break

        rows = []
        if found:
            with found.open("r", encoding="utf-8", errors="ignore") as fh:
                reader = csv.DictReader(fh, delimiter=';')
                for r in reader:
                    # Normalize columns and parse date/time
                    try:
                        date_raw = r.get('Data') or r.get('Date')
                        time_raw = r.get('Hora') or r.get('Time')
                        if not date_raw or not time_raw:
                            continue
                        # Date format in files: DD/MM/YY
                        # Convert to YYYY
                        day, month, year = date_raw.split('/')
                        year = '20' + year if len(year) == 2 else year
                        timestamp = dt.strptime(f"{day}/{month}/{year} {time_raw}", "%d/%m/%Y %H:%M:%S")
                        # Convert numbers with comma decimal
                        def parse_num(s: str) -> Decimal:
                            s = s.replace('.', '').replace(',', '.')
                            return Decimal(s)

                        open_p = parse_num(r.get('Abertura') or r.get('Open') or '0')
                        high_p = parse_num(r.get('M�ximo') or r.get('Max') or '0')
                        low_p = parse_num(r.get('M�nimo') or r.get('Min') or '0')
                        close_p = parse_num(r.get('Fechamento') or r.get('Close') or '0')
                        volume_raw = r.get('Volume') or r.get('Vol') or '0'
                        volume = int(float(volume_raw.replace('.', '').replace(',', '.')))

                        rows.append({
                            'timestamp': timestamp,
                            'open': open_p,
                            'high': high_p,
                            'low': low_p,
                            'close': close_p,
                            'volume': volume,
                        })
                    except Exception:
                        continue

        # sort by timestamp ascending
        rows.sort(key=lambda x: x['timestamp'])
        self._data[symbol_code] = rows
        return rows

    def get_candles(self, symbol: Symbol, timeframe: TimeFrame, count: int = 100, start_time: Optional[datetime] = None):
        rows = self._load_csv(symbol.code)
        if not rows:
            return []

        # Filter by start_time
        if start_time:
            rows = [r for r in rows if r['timestamp'] >= start_time]

        # Convert timeframe
        if timeframe == TimeFrame.M5:
            step = 5
        elif timeframe == TimeFrame.M15:
            step = 15
        elif timeframe == TimeFrame.M1:
            step = 1
        elif timeframe == TimeFrame.D1:
            # return first daily candle for the date
            # group by date and return first
            grouped = {}
            for r in rows:
                d = r['timestamp'].date()
                grouped.setdefault(d, []).append(r)
            # pick day from start_time if provided
            if start_time:
                day = start_time.date()
            else:
                day = rows[0]['timestamp'].date()
            day_rows = grouped.get(day, [])
            if not day_rows:
                return []
            r = day_rows[0]
            return [Candle(symbol=symbol, timeframe=TimeFrame.D1,
                           open=Price(r['open']), high=Price(r['high']), low=Price(r['low']), close=Price(r['close']), volume=r['volume'], timestamp=r['timestamp'])]

        else:
            step = 5

        # Aggregate rows into timeframe buckets
        candles = []
        i = 0
        while i < len(rows) and len(candles) < count:
            base = rows[i]
            minute = base['timestamp'].minute
            # for M15, align groups where minute % 15 == 0
            if step == 15 and (minute % 15) != 0:
                i += 1
                continue

            # collect entries in the next 'step' minutes window
            window_end = base['timestamp'] + timedelta(minutes=step)
            group = []
            j = i
            while j < len(rows) and rows[j]['timestamp'] < window_end:
                group.append(rows[j])
                j += 1

            if not group:
                i += 1
                continue

            open_p = group[0]['open']
            close_p = group[-1]['close']
            high_p = max(r['high'] for r in group)
            low_p = min(r['low'] for r in group)
            vol = sum(r['volume'] for r in group)

            candles.append(Candle(symbol=symbol, timeframe=timeframe,
                                  open=Price(open_p), high=Price(high_p), low=Price(low_p), close=Price(close_p), volume=vol, timestamp=group[0]['timestamp']))

            i = j

        # return last 'count' candles
        return candles[-count:]

    def get_daily_candle(self, symbol_code: str):
        rows = self._load_csv(symbol_code)
        if not rows:
            return None
        # pick first row of the day
        r = rows[0]
        return Candle(symbol=Symbol(symbol_code), timeframe=TimeFrame.D1,
                      open=Price(r['open']), high=Price(r['high']), low=Price(r['low']), close=Price(r['close']), volume=r['volume'], timestamp=r['timestamp'])

    def get_available_symbols(self, prefix: str = "") -> list[str]:
        names = []
        for f in self.export_dir.iterdir():
            # filename like PETR4_B_0_5min.csv -> symbol = part before _
            symbol = f.name.split('_')[0]
            if prefix:
                if symbol.startswith(prefix):
                    names.append(symbol)
            else:
                names.append(symbol)
        return list(sorted(set(names)))

    def select_symbol(self, symbol_code: str) -> bool:
        rows = self._load_csv(symbol_code)
        return bool(rows)

    def get_symbol_info_tick(self, symbol_code: str):
        rows = self._load_csv(symbol_code)
        if not rows:
            return None
        last = rows[-1]
        return TickData(symbol=Symbol(symbol_code), bid=Price(last['close']), ask=Price(last['close']), last=Price(last['close']), volume=last['volume'], timestamp=last['timestamp'])


def main():
    import sys
    arg = sys.argv[1] if len(sys.argv) > 1 else "06/02/2026"
    try:
        date = datetime.strptime(arg, "%d/%m/%Y")
    except Exception:
        print("Invalid date. Use DD/MM/YYYY")
        return

    adapter = FakeMT5Adapter()

    from src.application.services.macro_score.item_registry import get_item_registry

    registry = get_item_registry()
    provider = HistoricalDataProvider(mt5_adapter=adapter, date=date)

    print(f"Loading historical data for {date.date()}")
    provider.load_all(registry)

    win_bars = provider.get_win_bars()
    if not win_bars:
        print("No WIN M15 bars found in local export for the date.")
        return

    display = BacktestDisplay()
    total_bars = len(win_bars)
    total_items = len([i for i in registry if i.scoring_type.name != 'TECHNICAL_INDICATOR'])

    display.show_header(date=date, total_bars=total_bars, symbols_loaded=provider.symbols_loaded, symbols_failed=provider.symbols_failed, total_items=total_items)

    engine = BacktestMacroScoreEngine(data_provider=provider, registry=registry, technical_scorer=TechnicalIndicatorScorer(adapter), forex_handler=ForexScoreHandler(adapter))

    all_results = []
    for i in range(min(5, total_bars)):
        result = engine.score_at_bar(i)
        all_results.append(result)
        display.show_bar(bar_number=i+1, total_bars=total_bars, candle=win_bars[i], result=result, daily_open=provider.get_daily_open(provider.get_resolved_symbol('IBOV') or 'WIN$N'))

    display.show_summary(all_results)


if __name__ == '__main__':
    main()


import sys
import pandas as pd
import numpy as np
from pathlib import Path
from datetime import datetime, timedelta
import pytz

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.infrastructure.adapters.mt5_adapter import MT5Adapter
from src.domain.enums.trading_enums import TimeFrame
from src.domain.value_objects import Symbol
from config import get_config

def calculate_legs(df, threshold=150):
    if df.empty: return []
    legs = []
    current_leg_start = df.iloc[0]['low']
    current_leg_end = df.iloc[0]['high']
    direction = 0

    for i in range(1, len(df)):
        row = df.iloc[i]
        if direction == 0:
            if row['high'] > current_leg_end + threshold:
                direction = 1
                current_leg_end = row['high']
            elif row['low'] < current_leg_start - threshold:
                direction = -1
                current_leg_end = row['low']
            continue

        if direction == 1:
            if row['high'] > current_leg_end:
                current_leg_end = row['high']
            elif row['low'] < current_leg_end - threshold:
                legs.append({'range': current_leg_end - current_leg_start, 'direction': 'UP'})
                direction = -1
                current_leg_start = current_leg_end
                current_leg_end = row['low']
        else:
            if row['low'] < current_leg_end:
                current_leg_end = row['low']
            elif row['high'] > current_leg_end + threshold:
                legs.append({'range': current_leg_start - current_leg_end, 'direction': 'DOWN'})
                direction = 1
                current_leg_start = current_leg_end
                current_leg_end = row['high']
    return legs

def detect_boxes(df, window=4, max_range=250):
    boxes = []
    i = 0
    while i <= len(df) - window:
        subset = df.iloc[i:i+window]
        h, l = subset['high'].max(), subset['low'].min()
        if h - l <= max_range:
            j = i + window
            while j < len(df):
                nh, nl = max(h, df.iloc[j]['high']), min(l, df.iloc[j]['low'])
                if nh - nl <= max_range:
                    h, l, j = nh, nl, j + 1
                else: break
            boxes.append({'start': df.iloc[i]['timestamp'], 'end': df.iloc[j-1]['timestamp'], 'range': h-l, 'duration': j-i})
            i = j
        else: i += 1
    return boxes

def analyze_market_frequency():
    config = get_config()
    mt5 = MT5Adapter(login=config.mt5_login, password=config.mt5_password, server=config.mt5_server)
    if not mt5.connect():
        print("Erro ao conectar ao MT5")
        return

    symbols_to_try = ["WIN$N", config.trading_symbol, "WING26"]
    for sym_code in symbols_to_try:
        if not sym_code: continue
        print(f"\n--- SÍMBOLO: {sym_code} ---")
        for tf in [TimeFrame.M5, TimeFrame.M15]:
            try:
                candles = mt5.get_candles(Symbol(code=sym_code), tf, count=400)
                if not candles: continue
                last_date = candles[-1].timestamp.date()
                df = pd.DataFrame([{
                    'timestamp': c.timestamp, 'open': float(c.open.value),
                    'high': float(c.high.value), 'low': float(c.low.value),
                    'close': float(c.close.value), 'volume': c.volume
                } for c in candles])
                df = df[df['timestamp'].dt.date == last_date]
                if df.empty: continue

                avg_range = (df['high'] - df['low']).mean()
                legs = calculate_legs(df)
                boxes = detect_boxes(df)
                avg_leg = np.mean([l['range'] for l in legs]) if legs else 0

                print(f"[{tf.name}] Data: {last_date} | Velas: {len(df)}")
                print(f"  Range Médio Vela: {avg_range:.1f} pts")
                print(f"  Pernas: {len(legs)} | Range Médio Pernas: {avg_leg:.1f} pts")
                print(f"  Caixotes: {len(boxes)}")
                print(f"  Freq: ~300pts: {sum(1 for l in legs if 250<=l['range']<=350)}, ~500pts: {sum(1 for l in legs if 450<=l['range']<=550)}")

                diag = "ESCADA/BLOCOS" if len(boxes) > 1 or (avg_range < 130 and len(legs) > 2) else "DIRECIONAL FLUIDO"
                print(f"  DIAGNÓSTICO: {diag}")
            except Exception as e: print(f"Erro {sym_code} {tf.name}: {e}")
    mt5.disconnect()

if __name__ == '__main__':
    analyze_market_frequency()

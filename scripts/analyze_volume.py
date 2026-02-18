"""
Volume Analysis - Analisa volume financeiro vs dias anteriores.
"""

import sys
from pathlib import Path

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from decimal import Decimal
from datetime import datetime, timedelta
from config import get_config
from src.domain.value_objects import Symbol
from src.infrastructure.adapters.mt5_adapter import MT5Adapter, TimeFrame


def analyze_volume():
    """Analyze volume patterns."""

    print("=" * 80)
    print("ANALISE DE VOLUME FINANCEIRO")
    print("=" * 80)
    print(f"Horario: {datetime.now().strftime('%H:%M:%S')}")
    print()

    # Configuration
    config = get_config()
    symbol = Symbol(config.trading_symbol)

    # Connect
    mt5 = MT5Adapter(
        login=config.mt5_login,
        password=config.mt5_password,
        server=config.mt5_server,
    )

    if not mt5.connect():
        print("[ERRO] Falha ao conectar")
        return

    print("Obtendo dados de volume...")

    # Get several days of data
    # Using M5 (5-minute) candles for better resolution
    candles_today = mt5.get_candles(symbol, TimeFrame.M5, count=300)  # ~1 day

    if not candles_today:
        print("[ERRO] Sem dados")
        mt5.disconnect()
        return

    print(f"[OK] {len(candles_today)} candles obtidos")
    print()

    # Calculate today's volume metrics
    current_time = datetime.now()
    current_hour = current_time.hour
    current_minute = current_time.minute

    # Volume até agora (desde 09:00)
    volume_today = sum(c.volume for c in candles_today)
    volume_current_hour = sum(
        c.volume for c in candles_today[-12:]  # Last hour (12 x 5min candles)
    )

    # Average volume per candle
    avg_volume_per_candle = volume_today / len(candles_today) if candles_today else 0

    # Calculate volume for same period in previous days (approximate)
    # Split data into daily segments
    candles_per_day = 84  # Approximately 7 hours * 12 candles/hour

    if len(candles_today) >= candles_per_day * 3:
        # Previous 3 days
        day1_candles = candles_today[-candles_per_day*4:-candles_per_day*3]
        day2_candles = candles_today[-candles_per_day*3:-candles_per_day*2]
        day3_candles = candles_today[-candles_per_day*2:-candles_per_day]
        today_candles = candles_today[-candles_per_day:]

        volume_day1 = sum(c.volume for c in day1_candles)
        volume_day2 = sum(c.volume for c in day2_candles)
        volume_day3 = sum(c.volume for c in day3_candles)
        volume_today_segment = sum(c.volume for c in today_candles)

        avg_volume_3days = (volume_day1 + volume_day2 + volume_day3) / 3

        volume_vs_avg = ((volume_today_segment - avg_volume_3days) / avg_volume_3days * 100) if avg_volume_3days > 0 else 0

        has_historical = True
    else:
        has_historical = False
        avg_volume_3days = 0
        volume_vs_avg = 0

    # Current price info
    current_candle = candles_today[-1]
    opening_candle = candles_today[0]
    current_price = current_candle.close.value
    opening_price = opening_candle.open.value
    price_change = ((current_price - opening_price) / opening_price) * 100

    print("=" * 80)
    print("VOLUME HOJE")
    print("=" * 80)
    print(f"Volume Total (ate agora):     {volume_today:,.0f} contratos")
    print(f"Volume Ultima Hora:           {volume_current_hour:,.0f} contratos")
    print(f"Volume Medio por Candle (5m): {avg_volume_per_candle:,.0f} contratos")
    print()

    if has_historical:
        print("=" * 80)
        print("COMPARACAO COM DIAS ANTERIORES")
        print("=" * 80)
        print(f"Volume Dia -3:                {volume_day1:,.0f} contratos")
        print(f"Volume Dia -2:                {volume_day2:,.0f} contratos")
        print(f"Volume Dia -1:                {volume_day3:,.0f} contratos")
        print(f"Media 3 Dias:                 {avg_volume_3days:,.0f} contratos")
        print()
        print(f"Volume Hoje (mesmo periodo):  {volume_today_segment:,.0f} contratos")
        print(f"Variacao vs Media:            {volume_vs_avg:+.1f}%")
        print()

        # Analysis
        print("-" * 80)
        print("ANALISE DO VOLUME")
        print("-" * 80)

        if volume_vs_avg > 20:
            print("Status: VOLUME MUITO ACIMA DA MEDIA")
            print(f"  -> Volume {volume_vs_avg:+.1f}% maior que media")
            print("  -> Indica ALTA participacao do mercado")
            print("  -> Movimentos tem FORTE conviccao")
            print()
            print("Interpretacao:")
            if price_change < -0.5:
                print("  -> Queda com volume ALTO = Pressao vendedora REAL")
                print("  -> Vendedores com CONVICCAO")
                print("  -> Movimento bearish tem FORCA")
            elif price_change > 0.5:
                print("  -> Alta com volume ALTO = Pressao compradora REAL")
                print("  -> Compradores com CONVICCAO")
                print("  -> Movimento bullish tem FORCA")
            else:
                print("  -> Lateral com volume ALTO = Indecisao com participacao")
                print("  -> Mercado aguardando definicao")

        elif volume_vs_avg < -20:
            print("Status: VOLUME MUITO ABAIXO DA MEDIA")
            print(f"  -> Volume {volume_vs_avg:+.1f}% menor que media")
            print("  -> Indica BAIXA participacao do mercado")
            print("  -> Movimentos tem FRACA conviccao")
            print()
            print("Interpretacao:")
            if abs(price_change) > 0.5:
                print("  -> Movimento de preco SEM volume = SUSPEITO")
                print("  -> Pode ser falso rompimento")
                print("  -> Probabilidade de reversao ALTA")
            else:
                print("  -> Lateral com volume BAIXO = Mercado DESINTERESSADO")
                print("  -> Aguardando catalisador")

        else:
            print("Status: VOLUME NORMAL")
            print(f"  -> Volume {volume_vs_avg:+.1f}% vs media (dentro da normalidade)")
            print("  -> Participacao do mercado REGULAR")
            print("  -> Movimentos tem conviccao MODERADA")
            print()
            print("Interpretacao:")
            print("  -> Comportamento tipico do ativo")
            print("  -> Sem anomalias detectadas")

    print()

    # Volume profile analysis
    print("=" * 80)
    print("DISTRIBUICAO DE VOLUME INTRADAY")
    print("=" * 80)
    print()

    # Group by hour
    volume_by_hour = {}
    for candle in candles_today[-84:]:  # Last trading day
        hour = candle.timestamp.hour
        if 9 <= hour <= 17:
            if hour not in volume_by_hour:
                volume_by_hour[hour] = 0
            volume_by_hour[hour] += candle.volume

    if volume_by_hour:
        max_volume_hour = max(volume_by_hour.values())

        print("Volume por Hora (aprox):")
        for hour in sorted(volume_by_hour.keys()):
            vol = volume_by_hour[hour]
            bar_length = int((vol / max_volume_hour) * 40) if max_volume_hour > 0 else 0
            bar = "#" * bar_length
            print(f"  {hour:02d}:00-{hour:02d}:59  {vol:8,.0f}  {bar}")
        print()

        # Identify peak hours
        sorted_hours = sorted(volume_by_hour.items(), key=lambda x: x[1], reverse=True)
        if sorted_hours:
            peak_hour, peak_vol = sorted_hours[0]
            print(f"Horario de Maior Volume: {peak_hour:02d}:00-{peak_hour:02d}:59")
            print(f"Volume no Pico: {peak_vol:,.0f} contratos")
            print()

    # Price vs Volume correlation
    print("=" * 80)
    print("PRECO vs VOLUME")
    print("=" * 80)
    print(f"Variacao Preco Hoje:  {price_change:+.2f}%")
    print(f"Preco Atual:          R$ {current_price:,.2f}")
    print()

    if has_historical:
        if abs(price_change) > 1.0 and volume_vs_avg > 20:
            print("COMBINACAO: Movimento FORTE + Volume ALTO")
            print("  -> Movimento TEM CONVICCAO")
            print("  -> Tendencia provavelmente CONTINUA")
            print("  -> Alta probabilidade de follow-through")

        elif abs(price_change) > 1.0 and volume_vs_avg < -20:
            print("COMBINACAO: Movimento FORTE + Volume BAIXO")
            print("  -> Movimento SEM CONVICCAO")
            print("  -> ALERTA: Possivel reversao")
            print("  -> Cuidado com armadilhas")

        elif abs(price_change) < 0.5 and volume_vs_avg > 20:
            print("COMBINACAO: Preco LATERAL + Volume ALTO")
            print("  -> Acumulacao ou Distribuicao em curso")
            print("  -> Preparando proximo movimento")
            print("  -> Aguardar rompimento com volume")

        else:
            print("COMBINACAO: Comportamento NORMAL")
            print("  -> Preco e volume em range normal")
            print("  -> Sem sinais anomalos")

    print()
    print("=" * 80)
    print("CONCLUSAO")
    print("=" * 80)
    print()

    if has_historical:
        if volume_vs_avg > 20:
            print("Volume esta ACIMA da media dos ultimos dias.")
            print("Movimentos de hoje tem MAIOR significancia.")
            if abs(price_change) > 1.0:
                print("A variacao de preco TEM FUNDAMENTO no volume.")

        elif volume_vs_avg < -20:
            print("Volume esta ABAIXO da media dos ultimos dias.")
            print("Movimentos de hoje tem MENOR significancia.")
            if abs(price_change) > 1.0:
                print("A variacao de preco PODE SER falsa (baixo volume).")

        else:
            print("Volume esta NORMAL comparado aos ultimos dias.")
            print("Comportamento tipico do mercado para este ativo.")
    else:
        print("Dados historicos insuficientes para comparacao multi-dia.")
        print(f"Volume total ate agora: {volume_today:,.0f} contratos")

    print()
    print("=" * 80)

    mt5.disconnect()


if __name__ == "__main__":
    analyze_volume()

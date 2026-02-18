"""
Pre-Market Analysis - Morning briefing for the trading day.
"""

import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from decimal import Decimal
from src.application.services.premarket_briefing import PreMarketBriefingService


def display_premarket_briefing():
    """Display complete pre-market briefing."""
    print("=" * 80)
    print("PRE-MERCADO - BRIEFING DO HEAD FINANCEIRO")
    print("=" * 80)
    print()

    # Generate briefing
    service = PreMarketBriefingService()

    # Simulate realistic data for today (2026-02-06)
    briefing = service.generate_briefing(
        sp500_change=Decimal("0.45"),  # S&P fechou positivo
        nasdaq_change=Decimal("0.62"),  # Tech forte
        asia_sentiment="MIXED",  # Asia mista
        us_futures=Decimal("0.25"),  # Futuros positivos
        dollar_index=Decimal("104.3"),  # Dollar estável
        vix=Decimal("16.5"),  # Volatilidade baixa
    )

    # Display briefing
    print(f"Data: {briefing.date}")
    print(f"Horario: {briefing.timestamp.strftime('%H:%M:%S')}")
    print()

    print("-" * 80)
    print("MANCHETE")
    print("-" * 80)
    print(f"{briefing.headline}")
    print()

    print("-" * 80)
    print("RESUMO EXECUTIVO")
    print("-" * 80)
    print(briefing.summary)
    print()

    print("-" * 80)
    print("MERCADOS GLOBAIS - MADRUGADA")
    print("-" * 80)
    print()
    print("ESTADOS UNIDOS (ontem):")
    print(f"  S&P 500:  {briefing.global_markets.sp500_change:+.2f}%")
    print(f"  Nasdaq:   {briefing.global_markets.nasdaq_change:+.2f}%")
    print(f"  Dow:      {briefing.global_markets.dow_change:+.2f}%")
    print()
    print("ASIA (madrugada):")
    print(f"  Nikkei:     {briefing.global_markets.nikkei_change:+.2f}%")
    print(f"  Hang Seng:  {briefing.global_markets.hang_seng_change:+.2f}%")
    print(f"  Shanghai:   {briefing.global_markets.shanghai_change:+.2f}%")
    print()
    print("EUROPA (abertura):")
    print(f"  DAX:   {briefing.global_markets.dax_change:+.2f}%")
    print(f"  FTSE:  {briefing.global_markets.ftse_change:+.2f}%")
    print()
    print("FUTUROS EUA (agora):")
    print(f"  S&P 500:  {briefing.global_markets.sp500_futures:+.2f}%")
    print(f"  Nasdaq:   {briefing.global_markets.nasdaq_futures:+.2f}%")
    print()
    print("COMMODITIES:")
    print(
        f"  Petroleo WTI: ${briefing.global_markets.oil_wti_price} ({briefing.global_markets.oil_change:+.2f}%)"
    )
    print(f"  Ouro:         ${briefing.global_markets.gold_price}")
    print()
    print("FOREX:")
    print(
        f"  DXY Dollar:   {briefing.global_markets.dxy_dollar}"
    )
    print(
        f"  USD/BRL:      {briefing.global_markets.usd_brl} ({briefing.global_markets.usd_brl_change:+.2f}%)"
    )
    print()
    print("VOLATILIDADE:")
    print(f"  VIX:  {briefing.global_markets.vix_level}")
    print()
    print("TREASURIES:")
    print(
        f"  US 10Y Yield: {briefing.global_markets.us_10y_yield}%"
    )
    print()

    print("-" * 80)
    print("DRIVERS DO DIA")
    print("-" * 80)
    print(f"Principal: {briefing.market_drivers.primary_driver}")
    print()
    print("Secundarios:")
    for driver in briefing.market_drivers.secondary_drivers:
        print(f"  - {driver}")
    print()
    if briefing.market_drivers.risk_events:
        print("Eventos de Risco:")
        for event in briefing.market_drivers.risk_events:
            print(f"  [!] {event}")
        print()
    if briefing.market_drivers.economic_data:
        print("Dados Economicos:")
        for data in briefing.market_drivers.economic_data:
            print(f"  - {data}")
        print()

    print("-" * 80)
    print("IMPACTO PARA O BRASIL / WIN")
    print("-" * 80)
    print(
        f"Sentimento Geral:     {briefing.brazil_impact.overall_sentiment}"
    )
    print(
        f"Fluxo de Capital:     {briefing.brazil_impact.capital_flow_expectation}"
    )
    print(f"Ibovespa:             {briefing.brazil_impact.ibovespa_bias}")
    print(f"WIN (Mini Indice):    {briefing.brazil_impact.win_bias}")
    print()
    print("Fatores Chave:")
    for factor in briefing.brazil_impact.key_factors:
        print(f"  - {factor}")
    print()

    print("-" * 80)
    print("ANALISE DIRECIONAL")
    print("-" * 80)
    print(f"Vies de Trading:  {briefing.trading_bias}")
    print(f"Confianca:        {briefing.confidence:.0%}")
    print(f"Nivel de Risco:   {briefing.risk_level}")
    print()

    print("FATORES BULLISH:")
    for factor in briefing.bullish_factors:
        print(f"  [+] {factor}")
    print()

    print("FATORES BEARISH:")
    for factor in briefing.bearish_factors:
        print(f"  [-] {factor}")
    print()

    print("PONTOS DE ATENCAO:")
    for point in briefing.watch_points:
        print(f"  [!] {point}")
    print()

    print("-" * 80)
    print("RECOMENDACAO DE ESTRATEGIA")
    print("-" * 80)
    print(briefing.strategy_recommendation)
    print()

    print("=" * 80)
    print("[OK] BRIEFING CONCLUIDO")
    print("=" * 80)
    print()
    print("Proximos passos:")
    print("  1. Aguardar abertura do mercado brasileiro (10:00)")
    print("  2. Observar primeiros minutos para confirmar direcao")
    print("  3. Buscar setups alinhados com o vies identificado")
    print()


if __name__ == "__main__":
    display_premarket_briefing()

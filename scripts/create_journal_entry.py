"""
Trading Journal CLI - View and create journal entries with storytelling.
"""

import sys
from pathlib import Path

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from decimal import Decimal
from datetime import datetime
from config import get_config
from src.application.services.trading_journal import TradingJournalService
from src.application.services.quantum_operator import QuantumOperatorEngine
from src.application.services.volume_analysis import VolumeAnalysisService
from src.domain.value_objects import Symbol
from src.infrastructure.adapters.mt5_adapter import MT5Adapter, TimeFrame


def create_journal_entry():
    """Create a storytelling journal entry for current market conditions."""

    print("=" * 80)
    print("DIARIO DE TRADING - STORYTELLING")
    print("=" * 80)
    print()

    now = datetime.now()
    print(f"Data: {now.strftime('%d/%m/%Y')}")
    print(f"Horario: {now.strftime('%H:%M:%S')}")
    print()

    # Connect to MT5
    config = get_config()
    mt5 = MT5Adapter(
        login=config.mt5_login,
        password=config.mt5_password,
        server=config.mt5_server,
    )

    if not mt5.connect():
        print("[ERRO] Falha ao conectar ao MT5")
        return

    print("[OK] Conectado ao MT5\n")

    # Get symbol and data
    symbol = Symbol(config.trading_symbol)

    # Get candles
    candles_15m = mt5.get_candles(symbol, TimeFrame.M15, count=100)

    if not candles_15m:
        print("[ERRO] Falha ao obter dados")
        mt5.disconnect()
        return

    opening_candle = candles_15m[0]
    current_candle = candles_15m[-1]

    opening_price = opening_candle.open.value
    current_price = current_candle.close.value
    high = max(c.high.value for c in candles_15m)
    low = min(c.low.value for c in candles_15m)

    print(f"Simbolo: {symbol}")
    print(f"Preco Atual: R$ {current_price:,.2f}")
    print(f"Abertura: R$ {opening_price:,.2f}")
    print(f"Maxima: R$ {high:,.2f}")
    print(f"Minima: R$ {low:,.2f}")
    print()

    # Calculate volume metrics
    print("Analisando volume...")
    volume_service = VolumeAnalysisService()
    volume_today, volume_avg_3days, volume_variance_pct = volume_service.calculate_volume_metrics(candles_15m)

    if volume_variance_pct is not None:
        print(f"[OK] {volume_service.get_volume_interpretation(volume_variance_pct)}")
    print()

    # Get decision from Quantum Operator
    print("Analisando mercado...")
    operator = QuantumOperatorEngine()

    decision = operator.analyze_and_decide(
        symbol=symbol,
        candles=candles_15m,
        dollar_index=Decimal("104.3"),
        vix=Decimal("16.5"),
        selic=Decimal("10.75"),
        ipca=Decimal("4.5"),
        usd_brl=Decimal("5.85"),
        embi_spread=250,
    )

    print("[OK] Analise concluida\n")

    # Create journal service
    journal = TradingJournalService()

    # Prepare decision data
    decision_data = {
        "action": decision.action,
        "confidence": decision.confidence,
        "primary_reason": decision.primary_reason,
        "macro_bias": decision.macro_bias,
        "fundamental_bias": decision.fundamental_bias,
        "sentiment_bias": decision.sentiment_bias,
        "technical_bias": decision.technical_bias,
        "alignment_score": decision.alignment_score,
        "supporting_factors": decision.supporting_factors,
        "market_regime": decision.market_regime,
    }

    # Create narrative
    narrative = journal.create_narrative(
        symbol=symbol,
        current_price=current_price,
        opening_price=opening_price,
        high=high,
        low=low,
        decision_data=decision_data,
        volume_today=volume_today,
        volume_avg_3days=volume_avg_3days,
        volume_variance_pct=volume_variance_pct,
    )

    # Save entry
    entry = journal.save_entry(narrative, decision_data)

    # Display storytelling
    print("=" * 80)
    print("NARRATIVA DO MERCADO")
    print("=" * 80)
    print()

    print(f"MANCHETE:")
    print(f"  {narrative.headline}")
    print()

    print(f"SENTIMENTO DO MERCADO: {narrative.market_feeling}")
    print()

    print("-" * 80)
    print("O QUE ESTOU VENDO:")
    print("-" * 80)
    print()
    print(narrative.detailed_narrative)
    print()

    print("-" * 80)
    print("CONTEXTO MULTIDIMENSIONAL")
    print("-" * 80)
    print(f"  Macro:        {entry.macro_bias}")
    print(f"  Fundamentos:  {entry.fundamental_bias}")
    print(f"  Sentimento:   {entry.sentiment_bias}")
    print(f"  Tecnica:      {entry.technical_bias}")
    print(f"  Alinhamento:  {entry.alignment_score:.0%}")
    print()

    print("-" * 80)
    print("DECISAO")
    print("-" * 80)
    print(f"  Acao:       {narrative.decision.value}")
    print(f"  Confianca:  {narrative.confidence:.0%}")
    print(f"  Reasoning:  {narrative.reasoning}")
    print()

    print("-" * 80)
    print("TAGS PARA APRENDIZAGEM")
    print("-" * 80)
    print(f"  {', '.join(narrative.tags)}")
    print()

    print("-" * 80)
    print("DADOS TECNICOS")
    print("-" * 80)
    print(f"  Entry ID:      {entry.entry_id}")
    print(f"  Fase Sessao:   {entry.sessionthoven_phase}")
    print(f"  Regime:        {entry.market_regime}")
    print()

    # Disconnect
    mt5.disconnect()

    print("=" * 80)
    print("[OK] ENTRADA NO DIARIO SALVA")
    print("=" * 80)
    print()
    print("Esta narrativa sera usada para aprendizagem por reforco.")
    print("Ao fim do dia, analisaremos se as decisoes foram corretas.")
    print()

    return entry


if __name__ == "__main__":
    create_journal_entry()

"""
Continuous Trading Journal - Automatic entries every 15 minutes.
"""

import sys
from pathlib import Path

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

import time
from decimal import Decimal
from datetime import datetime
from config import get_config
from src.application.services.trading_journal import TradingJournalService
from src.application.services.quantum_operator import QuantumOperatorEngine
from src.application.services.volume_analysis import VolumeAnalysisService
from src.domain.value_objects import Symbol
from src.infrastructure.adapters.mt5_adapter import MT5Adapter, TimeFrame


def create_journal_entry(mt5: MT5Adapter, operator: QuantumOperatorEngine, journal: TradingJournalService, symbol: Symbol):
    """Create a single journal entry."""

    now = datetime.now()
    print("\n" + "=" * 80)
    print(f"NOVA ENTRADA - {now.strftime('%H:%M:%S')}")
    print("=" * 80)

    # Get candles
    candles_15m = mt5.get_candles(symbol, TimeFrame.M15, count=100)

    if not candles_15m:
        print("[ERRO] Falha ao obter dados")
        return None

    opening_candle = candles_15m[0]
    current_candle = candles_15m[-1]

    opening_price = opening_candle.open.value
    current_price = current_candle.close.value
    high = max(c.high.value for c in candles_15m)
    low = min(c.low.value for c in candles_15m)

    print(f"Preco Atual: R$ {current_price:,.2f}")
    print(f"Variacao:    {((current_price - opening_price) / opening_price * 100):+.2f}%")

    # Calculate volume metrics
    volume_service = VolumeAnalysisService()
    volume_today, volume_avg_3days, volume_variance_pct = volume_service.calculate_volume_metrics(candles_15m)

    if volume_variance_pct is not None:
        print(f"Volume:      {volume_service.get_volume_interpretation(volume_variance_pct)}")

    # Get decision
    print("Analisando...")
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

    # Create journal entry
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

    entry = journal.save_entry(narrative, decision_data)

    # Display FULL narrative
    print()
    print("=" * 80)
    print("NARRATIVA DO MERCADO")
    print("=" * 80)
    print()
    print("MANCHETE:")
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
    print(f"  Macro:        {decision_data['macro_bias']}")
    print(f"  Fundamentos:  {decision_data['fundamental_bias']}")
    print(f"  Sentimento:   {decision_data['sentiment_bias']}")
    print(f"  Tecnica:      {decision_data['technical_bias']}")
    print(f"  Alinhamento:  {entry.alignment_score:.0%}")
    print()
    print("-" * 80)
    print("DECISAO")
    print("-" * 80)
    print(f"  Acao:       {narrative.decision.value}")
    print(f"  Confianca:  {narrative.confidence:.0%}")
    print(f"  Reasoning:  {decision_data['primary_reason']}")
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
    print(f"  Fase Sessao:   {entry.session_phase}")
    print(f"  Regime:        {entry.market_regime}")
    print()
    print("=" * 80)
    print(f"[OK] ENTRADA NO DIARIO SALVA - #{entry.entry_id}")
    print("=" * 80)

    return entry


def run_continuous_journal():
    """Run journal entries continuously every 15 minutes."""

    print("=" * 80)
    print("DIARIO CONTINUO - ENTRADAS A CADA 15 MINUTOS")
    print("=" * 80)
    print()
    print("Pressione Ctrl+C para parar")
    print()

    # Setup
    config = get_config()
    symbol = Symbol(config.trading_symbol)

    # Connect to MT5
    print("Conectando ao MT5...")
    mt5 = MT5Adapter(
        login=config.mt5_login,
        password=config.mt5_password,
        server=config.mt5_server,
    )

    if not mt5.connect():
        print("[ERRO] Falha ao conectar ao MT5")
        return

    print("[OK] Conectado!")
    print()

    # Initialize services
    operator = QuantumOperatorEngine()
    journal = TradingJournalService()

    entry_count = 0

    try:
        while True:
            entry_count += 1

            # Create entry
            entry = create_journal_entry(mt5, operator, journal, symbol)

            if entry:
                print(f"\n[OK] Entrada #{entry_count} salva com sucesso")

            # Wait 15 minutes
            print(f"\nProxima analise em 15 minutos...")
            print(f"Aguardando ate {datetime.now().replace(second=0, microsecond=0).strftime('%H:%M')}")

            # Sleep for 15 minutes (900 seconds)
            time.sleep(900)

    except KeyboardInterrupt:
        print("\n\n" + "=" * 80)
        print("DIARIO INTERROMPIDO PELO USUARIO")
        print("=" * 80)
        print(f"\nTotal de entradas criadas: {entry_count}")
        print(f"Entradas de hoje: {len(journal.get_today_entries())}")
        print()

    finally:
        # Disconnect
        mt5.disconnect()
        print("[OK] Desconectado do MT5")
        print()

        # Show today's summary
        today_entries = journal.get_today_entries()
        if today_entries:
            print("-" * 80)
            print("RESUMO DO DIA")
            print("-" * 80)
            for e in today_entries:
                print(f"  [{e.time}] {e.narrative.decision.value:4s} - {e.narrative.market_feeling:10s} - {e.narrative.headline[:50]}...")
            print()


if __name__ == "__main__":
    run_continuous_journal()

"""
Monitor Trading System - Monitora execucao do trading automatizado.
"""

import sys
from pathlib import Path

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

import time
from decimal import Decimal
from datetime import datetime
from config import get_config
from src.application.services.quantum_operator import QuantumOperatorEngine
from src.domain.value_objects import Symbol
from src.infrastructure.adapters.mt5_adapter import MT5Adapter, TimeFrame


def main():
    """Test system configuration and first analysis."""

    print("=" * 80)
    print("TESTE DO SISTEMA DE TRADING AUTOMATIZADO")
    print("=" * 80)
    print()

    # Configuration
    config = get_config()
    symbol = Symbol(config.trading_symbol)

    print("CONFIGURACAO:")
    print(f"  Simbolo: {symbol}")
    print(f"  Max Posicoes: 5")
    print(f"  Contratos por Trade: 1")
    print()

    # Connect
    print("Conectando ao MT5...")
    mt5 = MT5Adapter(
        login=config.mt5_login,
        password=config.mt5_password,
        server=config.mt5_server,
    )

    if not mt5.connect():
        print("[ERRO] Falha ao conectar")
        return

    print("[OK] Conectado!")
    print()

    # Get balance
    try:
        balance = mt5.get_account_balance()
        print(f"Saldo: R$ {balance:,.2f}")
        print()
    except Exception as e:
        print(f"[AVISO] Erro ao obter saldo: {e}")
        print()

    # Get market data
    print("Obtendo dados do mercado...")
    candles = mt5.get_candles(symbol, TimeFrame.M5, count=100)

    if not candles:
        print("[ERRO] Falha ao obter candles")
        mt5.disconnect()
        return

    current_candle = candles[-1]
    print(f"[OK] {len(candles)} candles obtidos")
    print(f"Preco Atual: R$ {current_candle.close.value:,.2f}")
    print()

    # Run analysis
    print("Executando analise completa...")
    operator = QuantumOperatorEngine()

    decision = operator.analyze_and_decide(
        symbol=symbol,
        candles=candles,
        dollar_index=Decimal("104.3"),
        vix=Decimal("16.5"),
        selic=Decimal("10.75"),
        ipca=Decimal("4.5"),
        usd_brl=Decimal("5.85"),
        embi_spread=250,
    )

    print("[OK] Analise concluida")
    print()

    # Display decision
    print("=" * 80)
    print("DECISAO DO OPERADOR QUANTICO")
    print("=" * 80)
    print()
    print(f"Sinal:       {decision.action.value}")
    print(f"Confianca:   {decision.confidence:.0%}")
    print(f"Alinhamento: {decision.alignment_score:.0%}")
    print()
    print(f"Razao: {decision.primary_reason}")
    print()

    print("-" * 80)
    print("CONTEXTO MULTIDIMENSIONAL")
    print("-" * 80)
    print(f"  Macro:        {decision.macro_bias}")
    print(f"  Fundamentos:  {decision.fundamental_bias}")
    print(f"  Sentimento:   {decision.sentiment_bias}")
    print(f"  Tecnica:      {decision.technical_bias}")
    print()

    # Check if would enter
    would_enter = (
        decision.action.value in ["BUY", "SELL"]
        and decision.confidence >= Decimal("0.75")
        and decision.alignment_score >= Decimal("0.75")
    )

    print("-" * 80)
    print("DECISAO DE ENTRADA")
    print("-" * 80)
    if would_enter:
        print("[OK] ENTRARIA NO TRADE")
        print(f"  Confianca: {decision.confidence:.0%} >= 75%")
        print(f"  Alinhamento: {decision.alignment_score:.0%} >= 75%")

        if decision.recommended_entry:
            entry = decision.recommended_entry
            print()
            print(f"  Entrada:      R$ {entry.entry_price.value:,.2f}")
            print(f"  Stop Loss:    R$ {entry.stop_loss.value:,.2f}")
            print(f"  Take Profit:  R$ {entry.take_profit.value:,.2f}")
            print(f"  R/R Ratio:    {entry.risk_reward_ratio:.2f}")
    else:
        print("[AGUARDAR] NAO ENTRARIA NO TRADE")
        if decision.confidence < Decimal("0.75"):
            print(f"  Confianca baixa: {decision.confidence:.0%} < 75%")
        if decision.alignment_score < Decimal("0.75"):
            print(f"  Alinhamento baixo: {decision.alignment_score:.0%} < 75%")
        if decision.action.value == "HOLD":
            print(f"  Sinal: HOLD (aguardar)")

    print()
    print("=" * 80)
    print("TESTE CONCLUIDO")
    print("=" * 80)
    print()
    print("O sistema esta funcionando corretamente!")
    print("Para iniciar trading automatizado: INICIAR_TRADING_AUTOMATICO.bat")
    print()

    mt5.disconnect()


if __name__ == "__main__":
    main()

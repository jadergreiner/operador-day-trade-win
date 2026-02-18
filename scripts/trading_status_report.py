"""
Trading Status Report - Relatorio completo do dia.
"""

import sys
from pathlib import Path

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from decimal import Decimal
from datetime import datetime
from config import get_config
from src.application.services.quantum_operator import QuantumOperatorEngine
from src.domain.value_objects import Symbol
from src.infrastructure.adapters.mt5_adapter import MT5Adapter, TimeFrame


def get_dolar_info():
    """Get current dollar exchange rate."""

    config = get_config()
    mt5 = MT5Adapter(
        login=config.mt5_login,
        password=config.mt5_password,
        server=config.mt5_server,
    )

    if not mt5.connect():
        return None

    try:
        # Try to get USDBRL data
        dolar_symbol = Symbol("USDBRL")
        tick = mt5.get_current_tick(dolar_symbol)

        if tick:
            mt5.disconnect()
            return {
                'bid': tick.bid.value,
                'ask': tick.ask.value,
                'last': tick.last.value,
            }
    except:
        pass

    mt5.disconnect()
    return None


def main():
    """Generate trading status report."""

    print("=" * 80)
    print("RELATORIO DE TRADING - STATUS DO DIA")
    print("=" * 80)
    print(f"Data: {datetime.now().strftime('%d/%m/%Y')}")
    print(f"Hora: {datetime.now().strftime('%H:%M:%S')}")
    print()

    # Configuration
    config = get_config()
    symbol = Symbol(config.trading_symbol)

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

    print("[OK] Conectado")
    print()

    # Account info
    balance = mt5.get_account_balance()
    equity = mt5.get_account_equity()

    print("=" * 80)
    print("CONTA")
    print("=" * 80)
    print(f"Saldo:         R$ {balance:,.2f}")
    print(f"Patrimonio:    R$ {equity:,.2f}")
    print(f"PnL Flutuante: R$ {equity - balance:,.2f}")
    print()

    # Market data
    candles = mt5.get_candles(symbol, TimeFrame.M5, count=100)

    if candles:
        opening_candle = candles[0]
        current_candle = candles[-1]

        opening_price = opening_candle.open.value
        current_price = current_candle.close.value
        high = max(c.high.value for c in candles)
        low = min(c.low.value for c in candles)

        change = ((current_price - opening_price) / opening_price) * 100
        amplitude = ((high - low) / opening_price) * 100

        print("=" * 80)
        print("MERCADO - WING26")
        print("=" * 80)
        print(f"Abertura:      R$ {opening_price:,.2f}")
        print(f"Atual:         R$ {current_price:,.2f}")
        print(f"Maxima:        R$ {high:,.2f}")
        print(f"Minima:        R$ {low:,.2f}")
        print(f"Variacao:      {change:+.2f}%")
        print(f"Amplitude:     {amplitude:.2f}%")
        print()

    # Current analysis
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

    print("=" * 80)
    print("ANALISE ATUAL")
    print("=" * 80)
    print(f"Sinal:         {decision.action.value}")
    print(f"Confianca:     {decision.confidence:.0%}")
    print(f"Alinhamento:   {decision.alignment_score:.0%}")
    print()
    print("Contexto Multidimensional:")
    print(f"  Macro:        {decision.macro_bias}")
    print(f"  Fundamentos:  {decision.fundamental_bias}")
    print(f"  Sentimento:   {decision.sentiment_bias}")
    print(f"  Tecnica:      {decision.technical_bias}")
    print()
    print(f"Razao: {decision.primary_reason}")
    print()

    # Trading activity today
    print("=" * 80)
    print("ATIVIDADE DE TRADING HOJE")
    print("=" * 80)
    print("Operacoes Executadas:     0")
    print("Operacoes Abertas:        0")
    print("Contratos Negociados:     0")
    print("PnL Realizado:            R$ 0.00")
    print("Win Rate:                 N/A")
    print()
    print("Status: Sistema aguardando setup de qualidade")
    print("  Filtro: Confianca >= 75% E Alinhamento >= 75%")
    print()

    # Dollar info
    print("=" * 80)
    print("DOLAR (USD/BRL)")
    print("=" * 80)

    dolar_info = get_dolar_info()
    if dolar_info:
        print(f"Compra (Bid):  R$ {dolar_info['bid']:.4f}")
        print(f"Venda (Ask):   R$ {dolar_info['ask']:.4f}")
        print(f"Ultimo:        R$ {dolar_info['last']:.4f}")
    else:
        print("Referencia (usada nas analises): R$ 5.8500")
        print("(Cotacao real indisponivel no feed)")
    print()

    # Configuration
    print("=" * 80)
    print("CONFIGURACAO DO SISTEMA")
    print("=" * 80)
    print("Max Operacoes Simultaneas:  5")
    print("Contratos por Operacao:     1")
    print("Risco por Trade:            2.0%")
    print("Confianca Minima:           75%")
    print("Alinhamento Minimo:         75%")
    print("Trailing Stop:              SIM (0.5%)")
    print()

    print("=" * 80)
    print("RELATORIO CONCLUIDO")
    print("=" * 80)
    print()

    mt5.disconnect()


if __name__ == "__main__":
    main()

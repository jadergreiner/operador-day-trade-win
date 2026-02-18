"""
Test MT5 Connection - Verificar conectividade com MetaTrader 5
"""

import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from config import get_config
from src.infrastructure.adapters.mt5_adapter import MT5Adapter, TimeFrame
from src.domain.value_objects import Symbol


def test_mt5_connection():
    """Test connection to MetaTrader 5."""
    print("=" * 80)
    print("TESTE DE CONEXAO - MetaTrader 5")
    print("=" * 80)
    print()

    # Get config
    config = get_config()

    print("Configuracao carregada:")
    print(f"   Login:  {config.mt5_login}")
    print(f"   Server: {config.mt5_server}")
    print(f"   Symbol: {config.trading_symbol}")
    print()

    # Create adapter
    print("Criando adapter MT5...")
    adapter = MT5Adapter(
        login=config.mt5_login,
        password=config.mt5_password,
        server=config.mt5_server,
    )

    # Connect
    print("Conectando ao MT5...")
    try:
        if adapter.connect():
            print("[OK] CONECTADO COM SUCESSO!\n")

            # Get account info
            print("Informacoes da Conta:")
            balance = adapter.get_account_balance()
            equity = adapter.get_account_equity()
            print(f"   Saldo:  R$ {balance:,.2f}")
            print(f"   Equity: R$ {equity:,.2f}")
            print()

            # Get current tick
            symbol = Symbol(config.trading_symbol)
            print(f"Dados de Mercado - {symbol}:")

            try:
                tick = adapter.get_current_tick(symbol)
                print(f"   Bid:    R$ {tick.bid.value:,.2f}")
                print(f"   Ask:    R$ {tick.ask.value:,.2f}")
                print(f"   Last:   R$ {tick.last.value:,.2f}")
                print(f"   Volume: {tick.volume:,}")
                print(f"   Time:   {tick.timestamp}")
                print()
            except Exception as e:
                print(f"   [AVISO] Erro ao obter tick: {e}")
                print()

            # Get some candles
            print(f"Candles de 5 minutos:")
            try:
                candles = adapter.get_candles(
                    symbol=symbol,
                    timeframe=TimeFrame.M5,
                    count=10,
                )

                if candles:
                    print(f"   Total: {len(candles)} candles")
                    latest = candles[-1]
                    print(f"   Ultimo candle:")
                    print(f"      Open:   R$ {latest.open.value:,.2f}")
                    print(f"      High:   R$ {latest.high.value:,.2f}")
                    print(f"      Low:    R$ {latest.low.value:,.2f}")
                    print(f"      Close:  R$ {latest.close.value:,.2f}")
                    print(f"      Volume: {latest.volume:,}")
                    print(f"      Time:   {latest.timestamp}")
                else:
                    print("   [AVISO] Nenhum candle retornado")
                print()
            except Exception as e:
                print(f"   [AVISO] Erro ao obter candles: {e}")
                print()

            # Disconnect
            print("Desconectando...")
            adapter.disconnect()
            print("[OK] Desconectado\n")

            print("=" * 80)
            print("[OK] TESTE CONCLUIDO COM SUCESSO!")
            print("=" * 80)
            return True

        else:
            print("[ERRO] FALHA NA CONEXAO")
            print()
            print("Verifique:")
            print("  - MetaTrader 5 esta aberto?")
            print("  - Credenciais estao corretas?")
            print("  - Servidor esta correto?")
            print()
            return False

    except Exception as e:
        print(f"[ERRO] {e}\n")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    test_mt5_connection()

"""
Enviar Ordem Real usando MT5 Python Library
Conecta diretamente ao MT5 aberto localmente
"""

import logging
import time

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)


async def enviar_ordem_mt5_local():
    """Envia ordem usando conexão direta ao MT5."""

    print("\n" + "="*80)
    print("🚀 ENVIAR ORDEM VIA MT5 PYTHON LIBRARY")
    print("="*80 + "\n")

    try:
        import MetaTrader5 as mt5

        print("[1/5] Conectando ao MT5 local...\n")

        # Conectar
        if not mt5.initialize():
            print(f"      ❌ Não consegui conectar ao MT5")
            print(f"      Erro: {mt5.last_error()}\n")
            print("      Verifique se MT5 está aberto com a conta 1000346516\n")
            return False

        print(f"      ✅ Conectado ao MT5\n")

        print("[2/5] Verificando conta...\n")

        # Obter info da conta
        account_info = mt5.account_info()
        if account_info is None:
            print(f"      ❌ Erro ao obter info da conta: {mt5.last_error()}\n")
            return False

        print(f"      Conta: {account_info.login}")
        print(f"      Corretora: {account_info.company}")
        print(f"      Saldo: R$ {account_info.balance}")
        print(f"      Margem disponível: R$ {account_info.margin_free}\n")

        # Verificar se é conta 1000346516
        if account_info.login != 1000346516:
            print(f"      ⚠️  AVISO: Conta logada é {account_info.login}")
            print(f"      Expected: 1000346516\n")

        print("[3/5] Preparando ordem BUY WIN$N...\n")

        # Obter símbolo info
        symbol = "WIN$N"
        if not mt5.symbol_select(symbol):
            print(f"      ❌ Símbolo {symbol} não encontrado: {mt5.last_error()}\n")
            print(f"      Símbolos disponíveis:")
            symbols = mt5.symbols_get()
            for s in symbols[:10]:
                print(f"         - {s.name}")
            print("")
            mt5.shutdown()
            return False

        symbol_info = mt5.symbol_info(symbol)
        print(f"      Símbolo: {symbol}")
        print(f"      Preço Bid: {symbol_info.bid}")
        print(f"      Preço Ask: {symbol_info.ask}")
        print(f"      Ponto (tick): {symbol_info.point}\n")

        print("[4/5] Enviando ordem ao servidor...\n")

        # Preparar pedido de trade
        request = {
            "action": mt5.TRADE_ACTION_DEAL,
            "symbol": symbol,
            "volume": 1,
            "type": mt5.ORDER_TYPE_BUY_LIMIT,
            "price": symbol_info.ask,
            "sl": symbol_info.bid - (100 * symbol_info.point),  # Stop Loss -100 pontos
            "tp": symbol_info.bid + (300 * symbol_info.point),  # Take Profit +300 pontos
            "deviation": 10,
            "magic": 20260220,
            "comment": "Ordem real CLEAR - enviar_ordem_mt5.py",
            "type_time": mt5.ORDER_TIME_GTC,
            "type_filling": mt5.ORDER_FILLING_FOK,
        }

        print(f"      Detalhes da ordem:")
        print(f"         Ação: BUY (Compra)")
        print(f"         Símbolo: {request['symbol']}")
        print(f"         Volume: {request['volume']}")
        print(f"         Preço: {request['price']}")
        print(f"         SL: {request['sl']}")
        print(f"         TP: {request['tp']}\n")

        # Enviar ordem
        result = mt5.order_send(request)

        if result is None:
            print(f"      ❌ Erro ao enviar: {mt5.last_error()}\n")
            mt5.shutdown()
            return False

        if result.retcode == mt5.TRADE_RETCODE_DONE or result.retcode == mt5.TRADE_RETCODE_PLACED:
            print(f"      ✅ ORDEM ENVIADA COM SUCESSO!\n")
            print(f"      Resultado:")
            print(f"         Retcode: {result.retcode}")
            print(f"         Ticket: {result.order}")
            print(f"         Volume: {result.volume}")
            print(f"         Preço: {result.price}")
            print(f"         Comment: {result.comment}\n")

            print("[5/5] Confirmando posição...\n")

            time.sleep(0.5)

            # Verificar posição aberta
            positions = mt5.positions_get(symbol=symbol)
            if positions:
                pos = positions[0]
                print(f"      ✅ Posição aberta no servidor:\n")
                print(f"      Ticket: {pos.ticket}")
                print(f"      Símbolo: {pos.symbol}")
                print(f"      Tipo: {'BUY' if pos.type == 0 else 'SELL'}")
                print(f"      Volume: {pos.volume}")
                print(f"      Entrada: {pos.price_open}")
                print(f"      SL: {pos.sl}")
                print(f"      TP: {pos.tp}")
                print(f"      P&L: {pos.profit}\n")
            else:
                print(f"      ⚠️  Posição não encontrada ainda (aguarde alguns segundos)\n")

            mt5.shutdown()
            return True
        else:
            print(f"      ❌ Erro ao processar ordem")
            print(f"      Retcode: {result.retcode}")
            print(f"      Motivo: {mt5.last_error()}\n")
            mt5.shutdown()
            return False

    except ImportError:
        print("❌ Biblioteca MetaTrader5 não instalada\n")
        print("   Instalando... pip install MetaTrader5\n")

        import subprocess
        subprocess.check_call(["pip", "install", "MetaTrader5", "-q"])

        print("   ✅ Instalado. Tente novamente.\n")
        return False

    except Exception as e:
        print(f"❌ Erro: {e}\n")
        import traceback
        traceback.print_exc()
        return False


async def main():
    """Main entry point."""

    resultado = await enviar_ordem_mt5_local()

    if resultado:
        print("="*80)
        print("✅ ORDEM ENVIADA COM SUCESSO AO SERVIDOR CLEAR")
        print("="*80 + "\n")
        print("Próximos passos:")
        print("1. Verifique a ordem no MT5 CLEAR")
        print("2. Dashboard: http://localhost:8765/dashboard")
        print("3. Monitore em tempo real\n")
    else:
        print("="*80)
        print("⚠️  FALHA AO ENVIAR ORDEM")
        print("="*80 + "\n")
        print("Possíveis causas:")
        print("1. MT5 não está aberto")
        print("2. MT5 não tem a conta 1000346516 logada")
        print("3. Símbolo WIN$N não está disponível")
        print("4. Sem permissão para enviar ordens\n")


if __name__ == "__main__":
    import asyncio
    asyncio.run(main())

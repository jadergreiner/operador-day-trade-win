
import sys
from pathlib import Path
from decimal import Decimal
from datetime import datetime

project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from src.infrastructure.adapters.mt5_adapter import MT5Adapter
from src.domain.value_objects import Symbol, Price, Quantity
from src.domain.entities.trade import Order
from src.domain.enums.trading_enums import OrderSide, OrderType, TimeFrame
from src.application.services.ai_reflection_journal import AIReflectionJournalService
from config import get_config

def main():
    config = get_config()
    mt5 = MT5Adapter(
        login=config.mt5_login,
        password=config.mt5_password,
        server=config.mt5_server,
    )

    if not mt5.connect():
        print("Erro ao conectar ao MetaTrader 5")
        return

    symbol_code = "WING26"  # Using the actual contract from the analysis
    symbol = Symbol(code=symbol_code)

    try:
        # Get current Tick
        tick = mt5.get_current_tick(symbol)
        current_price = tick.ask

        # Get Opening Price (first candle of the day)
        candles = mt5.get_candles(symbol, TimeFrame.M5, count=100)
        day_opening = None
        if candles:
            today = datetime.now().date()
            today_candles = [c for c in candles if c.timestamp.date() == today]
            if today_candles:
                day_opening = today_candles[0].open

        if not day_opening:
            print("Não foi possível determinar o preço de abertura de hoje.")
            day_opening = current_price

        print(f"Preço de Abertura: {day_opening.value}")
        print(f"Preço Atual (Ask): {current_price.value}")

        tp_price = Price(current_price.value + Decimal("500"))
        sl_price = Price(current_price.value - Decimal("250"))

        print(f"Configurando Take Profit: {tp_price.value} (+500 pts)")
        print(f"Configurando Stop Loss: {sl_price.value} (-250 pts)")

        # Manually construct request if send_order is failing due to result=None
        # This helps debugging
        import MetaTrader5 as mt5_lib

        request = {
            "action": mt5_lib.TRADE_ACTION_DEAL,
            "symbol": symbol.code,
            "volume": 1.0,
            "type": mt5_lib.ORDER_TYPE_BUY,
            "price": float(current_price.value),
            "sl": float(sl_price.value),
            "tp": float(tp_price.value),
            "deviation": 10,
            "magic": 234000,
            "comment": "Head Financeiro Master Order",
            "type_time": mt5_lib.ORDER_TIME_GTC,
            "type_filling": mt5_lib.ORDER_FILLING_RETURN, # Probable fix for B3
        }

        result = mt5_lib.order_send(request)
        if result is None:
            print(f"Erro Crítico: mt5.order_send retornou None. Last error: {mt5_lib.last_error()}")
        elif result.retcode != mt5_lib.TRADE_RETCODE_DONE:
            print(f"Erro na Ordem: {result.comment} (code: {result.retcode})")
        else:
            print(f"ORDEM EXECUTADA COM SUCESSO!")
            print(f"Ticket ID: {result.order}")
            print(f"Preço de Entrada: {result.price}")
            print(f"SL: {sl_price.value}")
            print(f"TP: {tp_price.value}")

            # Registra no AI Reflection Journal
            try:
                journal = AIReflectionJournalService()
                journal.record_head_financeiro_strategic_operation(
                    price=Decimal(str(result.price)),
                    operation=f"COMPRA (Master Order #{result.order})",
                    justification="Intervencao manual estrategica do Head Financeiro via terminal externo.",
                    alignment_thesis="Execucao direta em B3 para maior precisao de ticket.",
                    system_status="MANUAL_EXECUTION",
                    confidence=Decimal("0.95")
                )
                print("[OK] Operacao registrada no AI Reflection Journal")
            except Exception as e:
                print(f"[AVISO] Nao foi possivel registrar no Diario: {e}")


    except Exception as e:
        print(f"Erro durante a execução: {e}")
    finally:
        mt5.disconnect()

if __name__ == "__main__":
    main()

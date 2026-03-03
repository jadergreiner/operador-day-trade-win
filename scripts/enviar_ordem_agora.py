"""
Enviar Ordem Real usando WINJ26 (contrato ativo)
"""

import MetaTrader5 as mt5
import time

print("\n" + "="*80)
print("🚀 ENVIAR ORDEM REAL - WINJ26")
print("="*80 + "\n")

if not mt5.initialize():
    print(f"❌ Erro ao conectar MT5\n")
    exit(1)

print("✅ Conectado ao MT5\n")

print("[1/5] Verificando conta...\n")

account = mt5.account_info()
print(f"      Conta: {account.login}")
print(f"      Corretora: {account.company}")
print(f"      Saldo: R$ {account.balance:.2f}")
print(f"      Margem disponível: R$ {account.margin_free:.2f}\n")

print("[2/5] Selecionando contrato WINJ26...\n")

symbol = "WINJ26"
if not mt5.symbol_select(symbol, True):
    print(f"      ❌ Erro ao selecionar {symbol}\n")
    mt5.shutdown()
    exit(1)

info = mt5.symbol_info(symbol)
print(f"      ✅ Símbolo: {symbol}")
print(f"      Bid: {info.bid}")
print(f"      Ask: {info.ask}")
print(f"      Ponto (tick): {info.point}\n")

print("[3/5] Preparando ordem BUY...\n")

# Usar preço Ask para entrada
entry_price = info.ask
sl_price = entry_price - 100  # -100 pontos
tp_price = entry_price + 300  # +300 pontos

print(f"      Entrada (Ask): {entry_price}")
print(f"      Stop Loss: {sl_price} (-100 pontos)")
print(f"      Take Profit: {tp_price} (+300 pontos)\n")

print("[4/5] ENVIANDO ORDEM...\n")

request = {
    "action": mt5.TRADE_ACTION_DEAL,
    "symbol": symbol,
    "volume": 1.0,  # 1 contrato
    "type": mt5.ORDER_TYPE_BUY,
    "price": entry_price,
    "sl": sl_price,
    "tp": tp_price,
    "deviation": 20,
    "magic": 20260220,
    "comment": "WINJ26",
    "type_time": mt5.ORDER_TIME_GTC,
    "type_filling": mt5.ORDER_FILLING_IOC,
}

print(f"      📊 Enviando para servidor CLEAR...\n")

result = mt5.order_send(request)

if result is None:
    print(f"      ❌ Erro: {mt5.last_error()}\n")
    mt5.shutdown()
    exit(1)

print(f"      Resultado do servidor:")
print(f"         Retcode: {result.retcode}")
print(f"         Ordem: {result.order}")
print(f"         Ticket: {result.order}")
print(f"         Volume: {result.volume}")
print(f"         Preço: {result.price}\n")

if result.retcode == mt5.TRADE_RETCODE_DONE or result.retcode == mt5.TRADE_RETCODE_PLACED:
    print(f"      ✅ ORDEM ENVIADA COM SUCESSO!\n")

    print("[5/5] Confirmando posição aberta...\n")

    time.sleep(1)

    positions = mt5.positions_get(symbol=symbol)

    if positions:
        pos = positions[-1]  # Última posição aberta
        print(f"      ✅ POSIÇÃO ABERTA NA CORRETORA:\n")
        print(f"         Ticket: {pos.ticket}")
        print(f"         Símbolo: {pos.symbol}")
        print(f"         Tipo: {'BUY' if pos.type == 0 else 'SELL'}")
        print(f"         Volume: {pos.volume}")
        print(f"         Entrada: {pos.price_open}")
        print(f"         SL: {pos.sl}")
        print(f"         TP: {pos.tp}")
        print(f"         P&L: R$ {pos.profit:.2f}\n")

        print("="*80)
        print("✅ ORDEM NA CORRETORA - OPERAÇÃO COM SUCESSO")
        print("="*80 + "\n")

        print("Detalhes da operação:")
        print(f"  Contrato: {pos.symbol}")
        print(f"  Ticket: {pos.ticket}")
        print(f"  Entrada: {pos.price_open}")
        print(f"  Volume: {pos.volume} contrato(s)")
        print(f"  Status: ABERTA\n")

        print("Próximos passos:")
        print(f"  1. Monitor dashboard: http://localhost:8765/dashboard")
        print(f"  2. Acompanhe em tempo real no MT5")
        print(f"  3. SL será executado em: {pos.sl}")
        print(f"  4. TP será executado em: {pos.tp}\n")
    else:
        print(f"      ⚠️  Posição não localizada ainda (aguarde alguns segundos)\n")

else:
    print(f"      ❌ Erro ao executar ordem")
    print(f"      Retcode: {result.retcode}")
    print(f"      Razão: {mt5.last_error()}\n")

mt5.shutdown()

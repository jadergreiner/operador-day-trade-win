"""
Verificar status de posições e ordens no MT5
"""

import MetaTrader5 as mt5
from datetime import datetime, timedelta

print("\n" + "="*80)
print("🔍 VERIFICAR STATUS DE POSIÇÕES E ORDENS")
print("="*80 + "\n")

if not mt5.initialize():
    print(f"❌ Erro ao conectar MT5\n")
    exit(1)

print("✅ Conectado ao MT5\n")

# Conta
account = mt5.account_info()
print(f"Conta: {account.login}")
print(f"Corretora: {account.company}")
print(f"Saldo: R$ {account.balance:.2f}")
print(f"Margem disponível: R$ {account.margin_free:.2f}\n")

# ===== POSIÇÕES ABERTAS =====
print("="*80)
print("📊 POSIÇÕES ABERTAS AGORA")
print("="*80 + "\n")

positions = mt5.positions_get()

if positions:
    print(f"Total de posições abertas: {len(positions)}\n")
    for pos in positions:
        print(f"Ticket: {pos.ticket}")
        print(f"  Símbolo: {pos.symbol}")
        print(f"  Tipo: {'BUY' if pos.type == 0 else 'SELL'}")
        print(f"  Volume: {pos.volume}")
        print(f"  Entrada: {pos.price_open}")
        print(f"  SL: {pos.sl}")
        print(f"  TP: {pos.tp}")
        print(f"  Preço atual: {pos.price_current}")
        print(f"  P&L: R$ {pos.profit:.2f}")
        print(f"  Aberta em: {datetime.fromtimestamp(pos.time)}\n")
else:
    print("❌ NENHUMA POSIÇÃO ABERTA NO MOMENTO\n")

# ===== ORDENS PENDENTES =====
print("="*80)
print("📋 ORDENS PENDENTES")
print("="*80 + "\n")

orders = mt5.orders_get()

if orders:
    print(f"Total de ordens pendentes: {len(orders)}\n")
    for order in orders:
        print(f"Ticket: {order.ticket}")
        print(f"  Símbolo: {order.symbol}")
        print(f"  Tipo: {order.type}")
        print(f"  Volume: {order.volume_initial}")
        print(f"  Preço: {order.price_open}\n")
else:
    print("✅ Nenhuma ordem pendente\n")

# ===== HISTÓRICO RECENTE =====
print("="*80)
print("📜 HISTÓRICO DE OPERAÇÕES (Últimas 24 horas)")
print("="*80 + "\n")

# Buscar ordens executadas nas últimas 24 horas
from_date = datetime.now() - timedelta(days=1)
deals = mt5.history_deals_get(from_date, datetime.now())

if deals:
    print(f"Total de operações: {len(deals)}\n")

    # Ordenar por tempo (mais recentes primeiro)
    deals_sorted = sorted(deals, key=lambda x: x.time, reverse=True)

    for deal in deals_sorted[:10]:  # Mostrar últimas 10
        deal_type = "BUY" if deal.type == mt5.DEAL_TYPE_BUY else "SELL"
        print(f"Ticket: {deal.ticket}")
        print(f"  Símbolo: {deal.symbol}")
        print(f"  Tipo: {deal_type}")
        print(f"  Volume: {deal.volume}")
        print(f"  Preço: {deal.price}")
        print(f"  Profit: R$ {deal.profit:.2f}")
        print(f"  Executado em: {datetime.fromtimestamp(deal.time)}")
        print(f"  Comentário: {deal.comment}\n")
else:
    print("❌ Nenhuma operação encontrada\n")

# ===== RESUMO WINJ26 =====
print("="*80)
print("🎯 RESUMO - WINJ26 (Ticket 2275949935)")
print("="*80 + "\n")

# Procurar a posição específica
target_positions = [p for p in mt5.positions_get() if p.ticket == 2275949935]

if target_positions:
    pos = target_positions[0]
    print(f"✅ POSIÇÃO AINDA ABERTA!")
    print(f"  Entrada: {pos.price_open}")
    print(f"  Preço atual: {pos.price_current}")
    print(f"  P&L: R$ {pos.profit:.2f}")
    print(f"  SL: {pos.sl}")
    print(f"  TP: {pos.tp}\n")
else:
    # Procurar no histórico
    winj_deals = [d for d in deals if d.symbol == "WINJ26" and 2275949935 in str(d.ticket)]

    if winj_deals:
        print(f"❌ POSIÇÃO FOI FECHADA")
        deal = winj_deals[0]
        print(f"  Símbolo: {deal.symbol}")
        print(f"  Ticket: {deal.ticket}")
        print(f"  Tipo: {'BUY' if deal.type == mt5.DEAL_TYPE_BUY else 'SELL'}")
        print(f"  Preço de entrada: {deal.price}")
        print(f"  Profit final: R$ {deal.profit:.2f}")
        print(f"  Fechado em: {datetime.fromtimestamp(deal.time)}\n")
    else:
        print(f"❌ NÃO ENCONTRADA POSIÇÃO OU ORDEM COM TICKET 2275949935\n")
        print(f"Possíveis causas:")
        print(f"  1. Posição foi fechada (TP/SL/Cancelada)")
        print(f"  2. Ordem foi rejeitada pelo servidor")
        print(f"  3. MT5 foi reiniciado e perdeu dados\n")

mt5.shutdown()
print("="*80)
print("✅ Verificação concluída\n")

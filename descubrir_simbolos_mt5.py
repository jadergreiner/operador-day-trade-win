"""
Descobrir símbolos disponíveis no MT5 e seus preços
"""

import MetaTrader5 as mt5
import time

print("\n" + "="*80)
print("🔍 DESCOBRIR SÍMBOLOS DISPONÍVEIS NO MT5")
print("="*80 + "\n")

if not mt5.initialize():
    print(f"❌ Não consegui conectar ao MT5\n")
    exit(1)

print("✅ Conectado ao MT5\n")

# Obter conta
account = mt5.account_info()
print(f"Conta: {account.login}")
print(f"Corretora: {account.company}\n")

print("Símbolos contendo 'WIN':\n")

# Procurar por símbolos WIN
symbols = mt5.symbols_get()
win_symbols = [s for s in symbols if 'WIN' in s.name.upper()]

if win_symbols:
    print(f"Encontrados {len(win_symbols)} símbolos:\n")
    
    for i, symbol in enumerate(win_symbols[:20], 1):
        # Selecionar simbolo
        mt5.symbol_select(symbol.name)
        time.sleep(0.1)
        
        # Obter info
        info = mt5.symbol_info(symbol.name)
        if info:
            print(f"{i}. {symbol.name}")
            print(f"   Bid: {info.bid}")
            print(f"   Ask: {info.ask}")
            print(f"   Ponto: {info.point}")
            print(f"   Volume min: {info.volume_min}")
            print(f"   Volume max: {info.volume_max}")
            print(f"   Volume step: {info.volume_step}\n")
else:
    print("❌ Nenhum símbolo WIN encontrado\n")
    print("Procurando símbolos iniciais com 'W':\n")
    
    w_symbols = [s for s in symbols if s.name.upper().startswith('W')][:10]
    for i, symbol in enumerate(w_symbols, 1):
        print(f"{i}. {symbol.name}")

print("\nTodos os símbolos (primeiros 30):\n")
for i, symbol in enumerate(symbols[:30], 1):
    print(f"{i}. {symbol.name}")

mt5.shutdown()
print("\n✅ Busca concluída\n")

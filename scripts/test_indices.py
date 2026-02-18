"""Teste de resolucao de futuros e simbolos no MT5."""
import MetaTrader5 as mt5
from dotenv import load_dotenv
import os
import datetime

load_dotenv()
login = int(os.getenv("MT5_LOGIN"))
password = os.getenv("MT5_PASSWORD")
server = os.getenv("MT5_SERVER")

mt5.initialize()
mt5.login(login, password=password, server=server)

# Testar busca de futuros por prefixo
futures_prefixes = [
    "WDO", "DOL", "WIN", "DI1", "CCM", "ICF", "SJC", "BGI",
    "DAP", "GLDG", "WSP", "HSI", "BIT", "ETH", "SOL", "ETR",
    "T10", "DDI", "FRC",
]

print("=== BUSCA DE FUTUROS POR PREFIXO ===\n")
for prefix in futures_prefixes:
    syms = mt5.symbols_get(prefix + "*")
    if syms:
        names = [s.name for s in syms[:8]]
        extra = f" (+{len(syms)-8} mais)" if len(syms) > 8 else ""
        print(f"  {prefix:8s} -> {names}{extra}")
    else:
        print(f"  {prefix:8s} -> NENHUM SIMBOLO")

# Testar $N continuous
print("\n=== CONTRATOS CONTINUOS ($N) ===\n")
cont_syms = [
    "WIN$N", "WDO$N", "DOL$N", "DI1$N", "CCM$N", "ICF$N",
    "WSP$N", "BGI$N", "SJC$N", "DAP$N", "GLDG$N",
    "BIT$N", "ETH$N", "SOL$N", "ETR$N",
]
for s in cont_syms:
    mt5.symbol_select(s, True)
    tick = mt5.symbol_info_tick(s)
    if tick:
        print(f"  {s:10s} -> OK  last={tick.last:.2f}")
    else:
        print(f"  {s:10s} -> NAO DISPONIVEL")

# Testar acoes/ETFs que falharam
print("\n=== ACOES E ETFS ===\n")
stock_syms = [
    "PETR4", "VALE3", "ITUB3", "ABEV3", "B3SA3", "BBDC3",
    "SMAL11", "CXSE3", "EGIE3", "EQPA3", "MRVE3", "BBAS3",
    "SANB3", "SAPR4", "VIVT3", "WEGE3", "PETR3", "PRIO3",
    "CSNA3", "USIM5", "NASD11", "IVVB11", "HASH11", "TSLC",
    "VXBR", "B5P211", "IRFM11", "EWZ", "EEM", "FXI", "ILF",
    "XTIUSD", "XBRUSD", "XNGUSD",
]
for s in stock_syms:
    mt5.symbol_select(s, True)
    tick = mt5.symbol_info_tick(s)
    if tick and tick.last > 0:
        print(f"  {s:10s} -> OK  last={tick.last:.2f}")
    elif tick:
        print(f"  {s:10s} -> TICK mas last=0")
    else:
        print(f"  {s:10s} -> NAO DISPONIVEL")

mt5.shutdown()

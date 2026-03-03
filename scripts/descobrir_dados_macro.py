"""
Análise Macro Avançada - Buscando símbolos alternativos
Tenta múltiplas variações para Dólar e Taxa de Juros
"""

import MetaTrader5 as mt5
import numpy as np
import pandas as pd
from datetime import datetime


def descobrir_simbolos_disponiveis():
    """Descobre símbolos disponíveis no MT5."""

    if not mt5.initialize():
        print("❌ Erro ao conectar ao MT5\n")
        return

    print("\n" + "="*80)
    print("🔍 DESCOBRINDO SÍMBOLOS DISPONÍVEIS")
    print("="*80 + "\n")

    print("Procurando símbolos contendo 'USD':\n")
    symbols = mt5.symbols_get()

    # Buscar USD
    usd_symbols = [s.name for s in symbols if 'USD' in s.name.upper()]
    if usd_symbols:
        for sym in usd_symbols[:10]:
            print(f"  • {sym}")
        if len(usd_symbols) > 10:
            print(f"  ... e mais {len(usd_symbols)-10}")
    else:
        print("  ❌ Nenhum símbolo USD encontrado")

    print("\nProcurando símbolos contendo 'DI' ou 'Taxa':\n")

    # Buscar DI/taxa
    di_symbols = [s.name for s in symbols if 'DI' in s.name.upper() or 'FUT' in s.name.upper()]
    if di_symbols:
        for sym in di_symbols[:10]:
            print(f"  • {sym}")
        if len(di_symbols) > 10:
            print(f"  ... e mais {len(di_symbols)-10}")
    else:
        print("  ❌ Nenhum símbolo DI/Futuro encontrado")

    print("\nProcurando símbolos contendo 'IPCA' ou 'FV':\n")

    # Buscar IPCA/FV
    ipca_symbols = [s.name for s in symbols if 'IPCA' in s.name.upper() or 'FV' in s.name.upper()]
    if ipca_symbols:
        for sym in ipca_symbols[:10]:
            print(f"  • {sym}")
        if len(ipca_symbols) > 10:
            print(f"  ... e mais {len(ipca_symbols)-10}")
    else:
        print("  ❌ Nenhum símbolo IPCA/FV encontrado")

    print("\nTodos os símbolos WIN (Mini Índice) disponíveis:\n")

    # Buscar WIN
    win_symbols = [s.name for s in symbols if 'WIN' in s.name.upper()]
    if win_symbols:
        for sym in win_symbols[:10]:
            print(f"  • {sym}")
        if len(win_symbols) > 10:
            print(f"  ... e mais {len(win_symbols)-10}")

    print("\nTop 30 símbolos futures disponíveis:\n")

    # Buscar todos os futuros
    fut_symbols = [s.name for s in symbols if 'F' in s.name[-1] or 'H' in s.name[-1] or 'M' in s.name[-1] or 'U' in s.name[-1] or 'Z' in s.name[-1]]
    if fut_symbols:
        for sym in fut_symbols[:30]:
            print(f"  • {sym}")

    mt5.shutdown()


def buscar_dados_macro():
    """Busca dados macro com símbolos encontrados."""

    if not mt5.initialize():
        print("❌ Erro ao conectar MT5\n")
        return

    print("\n" + "="*80)
    print("📊 BUSCANDO DADOS MACRO DISPONÍVEIS")
    print("="*80 + "\n")

    # Tentar obter dados do Mini Índice
    simbolo_mini = "WINJ26"

    print(f"1️⃣  Mini Índice ({simbolo_mini}):")

    if mt5.symbol_select(simbolo_mini):
        barras = mt5.copy_rates_from_pos(simbolo_mini, mt5.TIMEFRAME_D1, 0, 20)
        if barras is not None:
            df = pd.DataFrame(barras)
            df['time'] = pd.to_datetime(df['time'], unit='s')

            print(f"   ✅ Dados disponíveis")
            print(f"   Últimas cotações:")
            for i in range(-3, 0):
                print(f"      {df.iloc[i]['time'].strftime('%Y-%m-%d')}: {df.iloc[i]['close']:.2f}")

            # Calcular tendência
            media_10 = df['close'].tail(10).mean()
            close_atual = df.iloc[-1]['close']
            tendencia = ((close_atual - media_10) / media_10) * 100

            print(f"   Tendência: {tendencia:+.2f}%")
        else:
            print(f"   ❌ Sem dados disponíveis")
    else:
        print(f"   ❌ Símbolo não encontrado")

    print()

    # Tentar diferentes símbolos de dólar
    print(f"2️⃣  Dólar (tentando símbolos):")

    dolar_symbols = ["USDBRL", "USD", "USDBRL$", "DOLAR"]
    dolar_encontrado = False

    for sym_dolar in dolar_symbols:
        if mt5.symbol_select(sym_dolar):
            barras = mt5.copy_rates_from_pos(sym_dolar, mt5.TIMEFRAME_D1, 0, 20)
            if barras is not None and len(barras) > 0:
                df = pd.DataFrame(barras)
                df['time'] = pd.to_datetime(df['time'], unit='s')

                print(f"   ✅ {sym_dolar} - Dados encontrados")
                print(f"   Últimas cotações:")
                for i in range(-3, 0):
                    print(f"      {df.iloc[i]['time'].strftime('%Y-%m-%d')}: {df.iloc[i]['close']:.4f}")

                media_10 = df['close'].tail(10).mean()
                close_atual = df.iloc[-1]['close']
                tendencia = ((close_atual - media_10) / media_10) * 100

                print(f"   Tendência: {tendencia:+.2f}%")
                dolar_encontrado = True
                break

    if not dolar_encontrado:
        print(f"   ⚠️  Nenhum símbolo de dólar encontrado")
        print(f"   Tentados: {', '.join(dolar_symbols)}")

    print()

    # Tentar taxa de juros
    print(f"3️⃣  Taxa de Juros / DI (tentando símbolos):")

    taxa_symbols = ["DI1G26", "DI1H26", "DI1U26", "SELIC", "DI1F26", "DI1"]
    taxa_encontrada = False

    for sym_taxa in taxa_symbols:
        if mt5.symbol_select(sym_taxa):
            barras = mt5.copy_rates_from_pos(sym_taxa, mt5.TIMEFRAME_D1, 0, 20)
            if barras is not None and len(barras) > 0:
                df = pd.DataFrame(barras)
                df['time'] = pd.to_datetime(df['time'], unit='s')

                print(f"   ✅ {sym_taxa} - Dados encontrados")
                print(f"   Últimas cotações:")
                for i in range(-3, 0):
                    print(f"      {df.iloc[i]['time'].strftime('%Y-%m-%d')}: {df.iloc[i]['close']:.2f}")

                media_10 = df['close'].tail(10).mean()
                close_atual = df.iloc[-1]['close']
                tendencia = ((close_atual - media_10) / media_10) * 100

                print(f"   Tendência: {tendencia:+.2f}%")
                taxa_encontrada = True
                break

    if not taxa_encontrada:
        print(f"   ⚠️  Nenhum símbolo de taxa encontrado")
        print(f"   Tentados: {', '.join(taxa_symbols)}")

    print()

    # Tentar IBOVESPA se disponível
    print(f"4️⃣  Índice Bovespa (referência macro):")

    ibov_symbols = ["IBOV", "IBOVESPA", "IBOVJ26", "$BVSP"]
    ibov_encontrado = False

    for sym_ibov in ibov_symbols:
        if mt5.symbol_select(sym_ibov):
            barras = mt5.copy_rates_from_pos(sym_ibov, mt5.TIMEFRAME_D1, 0, 20)
            if barras is not None and len(barras) > 0:
                df = pd.DataFrame(barras)
                df['time'] = pd.to_datetime(df['time'], unit='s')

                print(f"   ✅ {sym_ibov} - Dados encontrados")
                print(f"   Últimas cotações:")
                for i in range(-3, 0):
                    print(f"      {df.iloc[i]['time'].strftime('%Y-%m-%d')}: {df.iloc[i]['close']:.2f}")

                media_10 = df['close'].tail(10).mean()
                close_atual = df.iloc[-1]['close']
                tendencia = ((close_atual - media_10) / media_10) * 100

                print(f"   Tendência: {tendencia:+.2f}%")
                ibov_encontrado = True
                break

    if not ibov_encontrado:
        print(f"   ⚠️  Índice Bovespa não disponível")

    mt5.shutdown()


if __name__ == "__main__":
    print("\nEste script vai descobrir quais símbolos estão disponíveis no MT5")
    print("e depois buscar dados para análise macro.\n")

    opcao = input("Deseja:\n1 - Descobrir símbolos disponíveis\n2 - Buscar dados macro\n3 - Ambos\n\nOpção (1-3): ").strip()

    if opcao in ['1', '3']:
        descobrir_simbolos_disponiveis()

    if opcao in ['2', '3']:
        buscar_dados_macro()

    print("\n✅ Análise concluída.")

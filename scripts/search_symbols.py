"""
Pesquisa simbolos corretos no MT5 para itens indisponiveis do macro score.

Para cada item com simbolo possivelmente incorreto, pesquisa no MT5
usando diversos prefixos e padroes alternativos.
"""

import sys
from pathlib import Path

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from config import get_config
from src.infrastructure.adapters.mt5_adapter import MT5Adapter


def search_symbols():
    """Pesquisa simbolos alternativos no MT5."""
    config = get_config()
    adapter = MT5Adapter(
        login=config.mt5_login,
        password=config.mt5_password,
        server=config.mt5_server,
    )

    print("Conectando ao MT5...")
    adapter.connect()
    print("[OK] Conectado!\n")

    # Itens a investigar: {numero: (simbolo_atual, nome, prefixos_busca)}
    items_to_search = {
        32: ("RIIA3", "Acao a confirmar", ["RIIA", "RII", "RI"]),
        39: ("DXY", "Indice Dolar Global", ["DXY", "DX", "DOLAR", "DOLLAR"]),
        59: ("BGI", "Boi Gordo Indice", ["BGI", "BOI"]),
        60: ("DAP", "Fosfato Fertilizante", ["DAP", "FOSF", "FERT"]),
        61: ("WTI", "Petroleo WTI", ["WTI", "OIL", "PETRO", "CRUDE", "CL"]),
        62: ("BRENT", "Petroleo Brent", ["BRENT", "BRT", "BRN"]),
        63: ("IRON", "Minerio de Ferro", ["IRON", "FERRO", "MINERIO", "FE"]),
        64: ("COPPER", "Cobre", ["COPPER", "COBRE", "COP", "CPR", "HG"]),
        66: ("T10", "US Treasury 10Y", ["T10", "TREAS", "US10", "TNX", "ZN"]),
        68: ("BIT", "Bitcoin", ["BIT", "BTC", "BITCOIN", "BITC"]),
        69: ("ETH", "Ethereum", ["ETH", "ETHER"]),
        70: ("SOL", "Solana", ["SOL", "SOLANA"]),
        71: ("ETR", "Ethereum variante", ["ETR", "ETHR"]),
        73: ("NQ", "Nasdaq US100", ["NQ", "NAS", "NASDAQ", "NDX", "QQQ"]),
        74: ("DAX", "Alemanha", ["DAX", "GER", "DE30", "DE40"]),
        75: ("HSI", "Hang Seng China", ["HSI", "HANG", "HK50", "HONG"]),
        77: ("VIX", "VIX US", ["VIX", "CBOE"]),
    }

    print("=" * 90)
    print("  PESQUISA DE SIMBOLOS NO MT5 - ClearInvestimentos")
    print("=" * 90)

    for num, (symbol, name, prefixes) in sorted(items_to_search.items()):
        print(f"\n--- #{num:>2} {symbol:<10} ({name}) ---")

        all_found = set()
        for prefix in prefixes:
            found = adapter.get_available_symbols(prefix)
            if found:
                for s in found:
                    all_found.add(s)

        if all_found:
            sorted_syms = sorted(all_found)
            print(f"  Encontrados {len(sorted_syms)} simbolos:")
            for s in sorted_syms[:20]:
                tick = adapter.get_symbol_info_tick(s)
                if tick:
                    status = f"bid={tick.bid.value:.4f} ask={tick.ask.value:.4f} last={tick.last.value:.4f}"
                else:
                    adapter.select_symbol(s)
                    tick = adapter.get_symbol_info_tick(s)
                    if tick:
                        status = f"bid={tick.bid.value:.4f} ask={tick.ask.value:.4f} last={tick.last.value:.4f} (apos select)"
                    else:
                        status = "sem tick"
                print(f"    {s:<25} {status}")
            if len(sorted_syms) > 20:
                print(f"    ... e mais {len(sorted_syms) - 20} simbolos")
        else:
            print("  NENHUM simbolo encontrado com esses prefixos")

    # Busca complementar por categorias
    print("\n\n" + "=" * 90)
    print("  BUSCA COMPLEMENTAR")
    print("=" * 90)

    all_syms = adapter.get_available_symbols("")

    print(f"\nTotal de simbolos disponiveis no MT5: {len(all_syms) if all_syms else 0}")

    if all_syms:
        # Dolar/Cambio
        print("\n--- Simbolos com DOL/USD ---")
        dol_syms = [s for s in all_syms if "DOL" in s.upper() or "USD" in s.upper()]
        for s in sorted(dol_syms)[:30]:
            print(f"    {s}")

        # Boi/Agro
        print("\n--- Simbolos com BOI/BGI ---")
        boi_syms = [s for s in all_syms if "BOI" in s.upper() or "BGI" in s.upper()]
        for s in sorted(boi_syms)[:20]:
            print(f"    {s}")

        # Cripto
        print("\n--- Simbolos com BTC/BIT/ETH/SOL ---")
        crypto_syms = [s for s in all_syms if any(
            k in s.upper() for k in ["BTC", "BIT", "ETH", "SOL", "CRIPTO", "CRYPTO"]
        )]
        for s in sorted(crypto_syms)[:20]:
            print(f"    {s}")

        # Commodities internacionais
        print("\n--- Simbolos com OIL/PETRO/IRON/COPPER/GOLD ---")
        comm_syms = [s for s in all_syms if any(
            k in s.upper() for k in ["OIL", "PETRO", "IRON", "COPPER", "GOLD", "CRUDE", "BRENT"]
        )]
        for s in sorted(comm_syms)[:20]:
            print(f"    {s}")

        # Indices globais
        print("\n--- Simbolos com SP500/NASDAQ/DAX/HSI/VIX ---")
        global_syms = [s for s in all_syms if any(
            k in s.upper() for k in ["SP500", "NASDAQ", "DAX", "HSI", "VIX", "S&P"]
        )]
        for s in sorted(global_syms)[:20]:
            print(f"    {s}")

        # Treasury/Juros
        print("\n--- Simbolos com TREAS/T10/BOND ---")
        fixed_syms = [s for s in all_syms if any(
            k in s.upper() for k in ["TREAS", "T10", "BOND", "TNOTE"]
        )]
        for s in sorted(fixed_syms)[:20]:
            print(f"    {s}")

    adapter.disconnect()
    print("\n[OK] Desconectado do MT5")


if __name__ == "__main__":
    search_symbols()

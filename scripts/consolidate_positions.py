"""
Consolidate Positions - Consolida posicoes abertas por corretora.
"""

import sys
from pathlib import Path

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from decimal import Decimal
from datetime import datetime
from config import get_config
from src.domain.value_objects import Symbol
from src.infrastructure.adapters.mt5_adapter import MT5Adapter, TimeFrame


def get_open_positions(mt5: MT5Adapter):
    """Get all open positions from MT5."""

    try:
        import MetaTrader5 as mt5_lib

        positions = mt5_lib.positions_get()

        if positions is None:
            return []

        position_list = []
        for pos in positions:
            position_list.append({
                'ticket': pos.ticket,
                'symbol': pos.symbol,
                'type': 'BUY' if pos.type == 0 else 'SELL',
                'volume': pos.volume,
                'price_open': pos.price_open,
                'price_current': pos.price_current,
                'profit': pos.profit,
                'sl': pos.sl,
                'tp': pos.tp,
                'time': datetime.fromtimestamp(pos.time),
            })

        return position_list

    except Exception as e:
        print(f"[ERRO] Falha ao obter posicoes: {e}")
        return []


def main():
    """Generate consolidated positions report."""

    print("=" * 80)
    print("CONSOLIDACAO DE POSICOES POR CORRETORA")
    print("=" * 80)
    print(f"Data: {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}")
    print()

    # Configuration
    config = get_config()

    # Connect to broker
    print("Conectando a corretora...")
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

    # Get account info
    balance = mt5.get_account_balance()
    equity = mt5.get_account_equity()

    # Get open positions
    positions = get_open_positions(mt5)

    print("=" * 80)
    print(f"CORRETORA: {config.mt5_server}")
    print("=" * 80)
    print(f"Login:           {config.mt5_login}")
    print(f"Saldo:           R$ {balance:,.2f}")
    print(f"Patrimonio:      R$ {equity:,.2f}")
    print(f"PnL Flutuante:   R$ {equity - balance:,.2f}")
    print()

    if not positions:
        print("POSICOES ABERTAS: 0")
        print()
        print("Nenhuma posicao aberta no momento.")
        print()
    else:
        print(f"POSICOES ABERTAS: {len(positions)}")
        print()

        # Group by symbol
        by_symbol = {}
        total_profit = Decimal("0")

        for pos in positions:
            symbol = pos['symbol']
            if symbol not in by_symbol:
                by_symbol[symbol] = {
                    'buy_volume': 0,
                    'sell_volume': 0,
                    'positions': [],
                    'total_profit': Decimal("0"),
                }

            if pos['type'] == 'BUY':
                by_symbol[symbol]['buy_volume'] += pos['volume']
            else:
                by_symbol[symbol]['sell_volume'] += pos['volume']

            by_symbol[symbol]['positions'].append(pos)
            by_symbol[symbol]['total_profit'] += Decimal(str(pos['profit']))
            total_profit += Decimal(str(pos['profit']))

        # Display by symbol
        for symbol, data in by_symbol.items():
            print("-" * 80)
            print(f"SIMBOLO: {symbol}")
            print("-" * 80)

            net_volume = data['buy_volume'] - data['sell_volume']
            direction = "COMPRADO" if net_volume > 0 else "VENDIDO" if net_volume < 0 else "NEUTRO"

            print(f"Posicoes:        {len(data['positions'])}")
            print(f"Contratos LONG:  {data['buy_volume']:.0f}")
            print(f"Contratos SHORT: {data['sell_volume']:.0f}")
            print(f"Posicao Liquida: {abs(net_volume):.0f} contratos {direction}")
            print(f"PnL:             R$ {data['total_profit']:,.2f}")
            print()

            # Detail each position
            for i, pos in enumerate(data['positions'], 1):
                print(f"  Pos #{i}:")
                print(f"    Ticket:     {pos['ticket']}")
                print(f"    Tipo:       {pos['type']}")
                print(f"    Contratos:  {pos['volume']:.0f}")
                print(f"    Entrada:    R$ {pos['price_open']:,.2f}")
                print(f"    Atual:      R$ {pos['price_current']:,.2f}")
                print(f"    Stop Loss:  R$ {pos['sl']:,.2f}" if pos['sl'] > 0 else "    Stop Loss:  Nao definido")
                print(f"    Take Profit: R$ {pos['tp']:,.2f}" if pos['tp'] > 0 else "    Take Profit: Nao definido")
                print(f"    PnL:        R$ {pos['profit']:,.2f}")
                print(f"    Aberta em:  {pos['time'].strftime('%d/%m/%Y %H:%M:%S')}")
                print()

        print("=" * 80)
        print("RESUMO CONSOLIDADO")
        print("=" * 80)
        print(f"Total de Posicoes:       {len(positions)}")
        print(f"Total PnL Flutuante:     R$ {total_profit:,.2f}")
        print()

    # Exposure analysis
    print("=" * 80)
    print("ANALISE DE EXPOSICAO")
    print("=" * 80)

    if positions:
        total_contracts = sum(pos['volume'] for pos in positions)
        print(f"Total de Contratos:      {total_contracts:.0f}")
        print(f"Exposicao por Contrato:  ~R$ 180.000")  # Approx contract value
        print(f"Exposicao Total Estimada: R$ {total_contracts * 180000:,.0f}")
        print()
        print(f"Utilizacao de Margem:    {(total_contracts / 5 * 100):.1f}% (max 5 posicoes)")
    else:
        print("Capacidade Disponivel:   5 operacoes simultaneas")
        print("Contratos por Operacao:  1 contrato")
        print("Exposicao Maxima:        5 contratos")
        print("Status:                  Aguardando setups de qualidade")

    print()

    print("=" * 80)
    print("SISTEMA OPERANDO AUTOMATICAMENTE")
    print("=" * 80)
    print("Configuracao:")
    print("  - Max 5 posicoes simultaneas")
    print("  - 1 contrato por operacao")
    print("  - Entra apenas com Confianca >= 75% E Alinhamento >= 75%")
    print("  - Stop Loss e Take Profit automaticos")
    print("  - Trailing Stop ativo (0.5%)")
    print()

    mt5.disconnect()

    print("=" * 80)
    print()


if __name__ == "__main__":
    main()

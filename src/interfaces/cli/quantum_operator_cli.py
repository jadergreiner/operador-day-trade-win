"""
Quantum Operator CLI - Interface for interacting with the Head Financeiro.

This is the main entry point for users to interact with the Quantum Operator.
"""

import sys
from decimal import Decimal
from typing import Any, Optional

from config import get_config
from src.application.services.quantum_operator import QuantumOperatorEngine
from src.domain.value_objects import Symbol
from src.infrastructure.adapters.mt5_adapter import MT5Adapter
from src.domain.enums.trading_enums import TimeFrame


class QuantumOperatorCLI:
    """Command-line interface for the Quantum Operator."""

    def __init__(self) -> None:
        """Initialize CLI."""
        self.config = get_config()
        self.operator = QuantumOperatorEngine()
        self.mt5_adapter: Optional[MT5Adapter] = None

    def connect_to_mt5(self) -> bool:
        """Connect to MetaTrader 5."""
        try:
            print("🔌 Conectando ao MetaTrader 5...")
            self.mt5_adapter = MT5Adapter(
                login=self.config.mt5_login,
                password=self.config.mt5_password,
                server=self.config.mt5_server,
            )

            if self.mt5_adapter.connect():
                print("✅ Conectado ao MT5 com sucesso!\n")
                return True
            else:
                print("❌ Falha ao conectar ao MT5\n")
                return False

        except Exception as e:
            print(f"❌ Erro ao conectar: {e}\n")
            return False

    def analyze_market(self, symbol: str) -> None:
        """
        Analyze market and get trading decision.

        This is the main command that triggers the complete analysis chain.
        """
        if not self.mt5_adapter or not self.mt5_adapter.is_connected():
            print("❌ MT5 não está conectado. Execute connect_mt5() primeiro.\n")
            return

        print("═" * 80)
        print(f"🎯 OPERADOR QUÂNTICO - ANÁLISE DE MERCADO: {symbol}")
        print("=" * 80)
        print()

        try:
            symbol_obj = Symbol(symbol)

            # Get market data
            print("📊 Capturando dados de mercado do MT5...")
            candles_5min = self.mt5_adapter.get_candles(
                symbol=symbol_obj,
                timeframe=TimeFrame.M5,
                count=100,
            )
            candles_15min = self.mt5_adapter.get_candles(
                symbol=symbol_obj,
                timeframe=TimeFrame.M15,
                count=100,
            )

            if not candles_5min or not candles_15min:
                print("❌ Erro ao obter dados de mercado\n")
                return

            print(f"✅ {len(candles_5min)} candles de 5min capturados")
            print(f"✅ {len(candles_15min)} candles de 15min capturados\n")

            # Get current market metrics (in production, would fetch live)
            print("🌍 Analisando cenário macroeconômico...")
            print("🇧🇷 Analisando fundamentos do Brasil...")
            print("📈 Analisando sentimento de mercado...")
            print("📊 Executando análise técnica...")
            print()

            # Run complete analysis
            decision = self.operator.analyze_and_decide(
                symbol=symbol_obj,
                candles=candles_15min,  # Use 15min for analysis
                # In production, these would be fetched from APIs
                dollar_index=Decimal("104.5"),  # Example
                vix=Decimal("16.8"),  # Example
                selic=Decimal("10.75"),  # Example
                ipca=Decimal("4.5"),  # Example
                usd_brl=Decimal("5.85"),  # Example
                embi_spread=250,  # Example
            )

            # Display results
            self._display_decision(decision)

        except Exception as e:
            print(f"❌ Erro durante análise: {e}\n")
            import traceback

            traceback.print_exc()

    def _display_decision(self, decision: Any) -> None:
        """Display trading decision in a beautiful format."""
        print(decision.executive_summary)
        print()

        print("📊 ANÁLISE MULTIDIMENSIONAL:")
        print(f"   🌍 Macro:        {decision.macro_bias}")
        print(f"   🇧🇷 Fundamentos:  {decision.fundamental_bias}")
        print(f"   📈 Sentimento:   {decision.sentiment_bias}")
        print(f"   📊 Técnica:      {decision.technical_bias}")
        print()

        print("✅ FATORES DE SUPORTE:")
        for factor in decision.supporting_factors:
            print(f"   {factor}")
        print()

        if decision.warning_factors:
            print("⚠️  FATORES DE ATENÇÃO:")
            for warning in decision.warning_factors:
                print(f"   {warning}")
            print()

        if decision.recommended_entry:
            entry = decision.recommended_entry
            print("🎯 SETUP RECOMENDADO:")
            print(f"   Tipo:         {entry.setup_type}")
            print(f"   Sinal:        {entry.signal.value}")
            print(f"   Entrada:      R$ {entry.entry_price.value:,.2f}")
            print(f"   Stop Loss:    R$ {entry.stop_loss.value:,.2f}")
            print(f"   Take Profit:  R$ {entry.take_profit.value:,.2f}")
            print(
                f"   R/R Ratio:    {entry.risk_reward_ratio:.2f}"
            )
            print(f"   Qualidade:    {entry.setup_quality.value}")
            print(f"   Confiança:    {entry.confidence:.0%}")
            print(f"   Razão:        {entry.reason}")
            print()

        print("=" * 80)

    def display_menu(self) -> None:
        """Display main menu."""
        print("\n" + "=" * 80)
        print("🤖 OPERADOR QUÂNTICO - Head Financeiro")
        print("=" * 80)
        print()
        print("Comandos disponíveis:")
        print("  1. analyze <SYMBOL>  - Analisar mercado e obter decisão")
        print("  2. status            - Status da conexão")
        print("  3. help              - Mostrar ajuda")
        print("  4. exit              - Sair")
        print()

    def run_interactive(self) -> None:
        """Run interactive mode."""
        print("\n🚀 Iniciando Operador Quântico...\n")

        # Try to connect automatically
        connected = self.connect_to_mt5()

        if not connected:
            print(
                "⚠️  Continuando sem conexão MT5 (modo demonstração)\n"
            )

        self.display_menu()

        while True:
            try:
                command = input("📌 Comando: ").strip().lower()

                if not command:
                    continue

                if command == "exit" or command == "quit":
                    print("\n👋 Encerrando Operador Quântico...")
                    if self.mt5_adapter:
                        self.mt5_adapter.disconnect()
                    print("✅ Desconectado. Até logo!\n")
                    break

                elif command == "status":
                    if self.mt5_adapter and self.mt5_adapter.is_connected():
                        print("✅ MT5 conectado")
                        balance = self.mt5_adapter.get_account_balance()
                        equity = self.mt5_adapter.get_account_equity()
                        print(f"   Saldo:  R$ {balance:,.2f}")
                        print(f"   Equity: R$ {equity:,.2f}")
                    else:
                        print("❌ MT5 não conectado")
                    print()

                elif command == "help":
                    self.display_menu()

                elif command.startswith("analyze"):
                    parts = command.split()
                    if len(parts) < 2:
                        symbol = self.config.trading_symbol
                    else:
                        symbol = parts[1].upper()

                    self.analyze_market(symbol)

                else:
                    print("❌ Comando não reconhecido. Digite 'help' para ajuda.\n")

            except KeyboardInterrupt:
                print("\n\n👋 Interrompido pelo usuário. Saindo...\n")
                if self.mt5_adapter:
                    self.mt5_adapter.disconnect()
                break

            except Exception as e:
                print(f"❌ Erro: {e}\n")


def main() -> None:
    """Main entry point."""
    cli = QuantumOperatorCLI()
    cli.run_interactive()


if __name__ == "__main__":
    main()

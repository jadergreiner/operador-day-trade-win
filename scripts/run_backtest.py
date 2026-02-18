"""
Backtest Interativo do MacroScore - barra a barra M15.

Uso:
    python scripts/run_backtest.py

Fluxo:
1. Conecta ao MT5
2. Solicita data ao usuario
3. Carrega dados historicos de todos os simbolos
4. Para cada barra M15 do WIN:
   - Calcula MacroScore usando dados historicos
   - Exibe score, sinal e detalhamento por categoria
   - Aguarda Enter para avancar
5. Ao final, mostra resumo da sessao
"""

import signal
import sys
from datetime import datetime
from pathlib import Path
import argparse

# Adiciona raiz do projeto ao path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from config import get_config
from src.application.services.backtest.backtest_engine import (
    BacktestMacroScoreEngine,
)
from src.application.services.backtest.display import BacktestDisplay
from src.application.services.backtest.historical_data_provider import (
    HistoricalDataProvider,
)
from src.application.services.macro_score.engine import MacroScoreResult
from src.application.services.macro_score.forex_handler import ForexScoreHandler
from src.application.services.macro_score.item_registry import get_item_registry
from src.application.services.macro_score.technical_scorer import (
    TechnicalIndicatorScorer,
)
from src.domain.enums.macro_score_enums import ScoringType
from src.infrastructure.adapters.mt5_adapter import MT5Adapter


def _setup_signal_handlers() -> None:
    """Configura handlers para Ctrl+C funcionar durante chamadas MT5."""
    def handler(signum, frame):
        print("\n\n  Operacao cancelada pelo usuario (Ctrl+C).")
        sys.exit(0)
    signal.signal(signal.SIGINT, handler)


def ask_date() -> datetime:
    """Solicita uma data ao usuario."""
    while True:
        raw = input("  Data para backtest (DD/MM/AAAA): ").strip()
        if not raw:
            print("  Data nao pode ser vazia.")
            continue
        try:
            dt = datetime.strptime(raw, "%d/%m/%Y")
            if dt.date() >= datetime.now().date():
                print("  A data deve ser anterior a hoje.")
                continue
            if dt.weekday() >= 5:
                print("  A data informada e fim de semana. Escolha um dia util.")
                continue
            return dt
        except ValueError:
            print("  Formato invalido. Use DD/MM/AAAA (ex: 15/01/2025)")


def connect_mt5() -> MT5Adapter:
    """Conecta ao MetaTrader 5."""
    config = get_config()
    print(f"  Login:  {config.mt5_login}")
    print(f"  Server: {config.mt5_server}")
    print()

    adapter = MT5Adapter(
        login=config.mt5_login,
        password=config.mt5_password,
        server=config.mt5_server,
    )

    print("  Conectando ao MT5...")
    adapter.connect()
    print("  [OK] Conectado!")
    print()
    return adapter


def run_backtest(adapter: MT5Adapter, date: datetime, auto: bool = False, max_bars: int | None = None) -> None:
    """Executa o backtest interativo para a data informada."""
    display = BacktestDisplay()
    registry = get_item_registry()

    # Carregar dados historicos
    print("  Carregando dados historicos...")
    print("  (pode levar alguns segundos)")
    print()

    provider = HistoricalDataProvider(mt5_adapter=adapter, date=date)
    provider.load_all(registry)

    win_bars = provider.get_win_bars()
    total_bars = len(win_bars)

    if total_bars == 0:
        print("  [ERRO] Nenhuma barra M15 do WIN encontrada para esta data.")
        print("  Verifique se o MT5 possui historico para a data informada.")
        return

    # Contabilizar itens totais (sem indicadores tecnicos que nao tem simbolo)
    # e excluindo simbolos presentes na blacklist (evita incluir na pontuação)
    total_items = len([
        i for i in registry
        if i.scoring_type != ScoringType.TECHNICAL_INDICATOR
        and not provider.is_registry_symbol_blacklisted(i.symbol)
    ])

    # Mostrar cabecalho
    display.show_header(
        date=date,
        total_bars=total_bars,
        symbols_loaded=provider.symbols_loaded,
        symbols_failed=provider.symbols_failed,
        total_items=total_items,
    )

    # Mostrar erros de carregamento se houver
    if provider.load_errors:
        print(f"  Erros de carregamento ({len(provider.load_errors)}):")
        for err in provider.load_errors[:10]:
            print(f"    - {err}")
        if len(provider.load_errors) > 10:
            print(f"    ... e mais {len(provider.load_errors) - 10}")
        print()

    # Criar engine de backtest
    engine = BacktestMacroScoreEngine(
        data_provider=provider,
        registry=registry,
        technical_scorer=TechnicalIndicatorScorer(adapter),
        forex_handler=ForexScoreHandler(adapter),
    )

    # Obter abertura diaria do WIN para calcular variacao
    win_daily_open = provider.get_daily_open(
        provider.get_resolved_symbol("IBOV") or "WIN$N"
    )
    # Tentar pegar abertura do proprio WIN
    win_open_direct = provider.get_daily_open("WIN$N")
    if win_open_direct:
        win_daily_open = win_open_direct
    elif win_bars:
        # Fallback: usar open da primeira barra M15
        win_daily_open = win_bars[0].open.value

    # Loop interativo barra-a-barra
    all_results: list[MacroScoreResult] = []

    for i, candle in enumerate(win_bars):
        bar_number = i + 1

        # Calcular score
        result = engine.score_at_bar(i)
        all_results.append(result)

        # Exibir resultado da barra
        display.show_bar(
            bar_number=bar_number,
            total_bars=total_bars,
            candle=candle,
            result=result,
            daily_open=win_daily_open,
        )

        # Aguardar input do usuario (exceto ultima barra) -- ou auto-advance
        if i < total_bars - 1:
            if auto:
                # auto advance: optionally stop early if max_bars is set
                if max_bars is not None and bar_number >= max_bars:
                    print("\n  Backtest encerrado (max bars atingido).")
                    break
                continue
            try:
                user_input = input(
                    "\n  [Enter] Proxima barra | [Q] Encerrar: "
                ).strip().upper()
                if user_input == "Q":
                    print("\n  Backtest encerrado pelo usuario.")
                    break
            except (KeyboardInterrupt, EOFError):
                print("\n\n  Backtest interrompido.")
                break
        else:
            print("\n  Ultima barra do dia atingida.")

    # Resumo final
    display.show_summary(all_results)


def main() -> None:
    """Ponto de entrada principal do backtest."""
    _setup_signal_handlers()

    print()
    print("=" * 90)
    print("  BACKTEST MACRO SCORE - MetaTrader 5")
    print("=" * 90)
    print()

    parser = argparse.ArgumentParser()
    parser.add_argument("--auto", action="store_true", help="Executar sem interação (auto-advance)")
    parser.add_argument("--date", type=str, help="Data para backtest DD/MM/YYYY")
    parser.add_argument("--max-bars", type=int, help="Máximo de barras a processar (usar com --auto)")
    args = parser.parse_args()

    adapter: MT5Adapter | None = None
    try:
        adapter = connect_mt5()

        if args.date:
            try:
                date = datetime.strptime(args.date, "%d/%m/%Y")
            except Exception:
                print("  Formato de data invalido. Use DD/MM/YYYY.")
                return
        else:
            date = ask_date()

        print()
        run_backtest(adapter, date, auto=args.auto, max_bars=args.max_bars)
    except KeyboardInterrupt:
        print("\n\n  Operacao cancelada pelo usuario.")
    except Exception as e:
        print(f"\n  [ERRO] {e}")
        import traceback
        traceback.print_exc()
    finally:
        if adapter:
            adapter.disconnect()
            print("\n  [OK] Desconectado do MT5.")
        print()


if __name__ == "__main__":
    main()

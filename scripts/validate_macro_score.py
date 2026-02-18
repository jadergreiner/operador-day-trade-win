"""
Validacao do Macro Score com MT5 - Verifica disponibilidade dos 85 itens.

Executa:
1. Conecta ao MT5
2. Testa cada um dos 85 simbolos do registry
3. Para simbolos disponiveis, busca preco de abertura e atual
4. Calcula score de demonstracao
5. Gera relatorio completo
"""

import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from decimal import Decimal
from config import get_config
from src.infrastructure.adapters.mt5_adapter import MT5Adapter
from src.application.services.macro_score.item_registry import get_item_registry
from src.application.services.macro_score.futures_resolver import FuturesContractResolver
from src.application.services.macro_score.forex_handler import ForexScoreHandler
from src.infrastructure.providers.forex_api_provider import ForexAPIProvider
from src.domain.enums.macro_score_enums import AssetCategory, ScoringType


def validate_macro_score():
    """Valida todos os 85 itens do macro score no MT5."""
    print("=" * 90)
    print("  VALIDACAO MACRO SCORE - MetaTrader 5")
    print("=" * 90)
    print()

    # Conectar
    config = get_config()
    print(f"Login:  {config.mt5_login}")
    print(f"Server: {config.mt5_server}")
    print()

    adapter = MT5Adapter(
        login=config.mt5_login,
        password=config.mt5_password,
        server=config.mt5_server,
    )

    print("Conectando ao MT5...")
    try:
        adapter.connect()
        print("[OK] Conectado!\n")
    except Exception as e:
        print(f"[ERRO] Falha na conexao: {e}")
        return

    # Sub-servicos
    futures_resolver = FuturesContractResolver(adapter)
    forex_handler = ForexScoreHandler(adapter)
    forex_api = ForexAPIProvider(cache_ttl_seconds=60)

    # Registry
    registry = get_item_registry()
    print(f"Total de itens no registry: {len(registry)}\n")

    # Resultados
    available = []
    unavailable = []
    with_data = []
    errors = []

    # Categorias
    categories = {}

    print("-" * 90)
    print(f"{'#':>3} | {'Simbolo':<10} | {'Resolvido':<15} | {'Status':<12} | "
          f"{'Abertura':>12} | {'Atual':>12} | {'Score':>5} | {'Detalhe'}")
    print("-" * 90)

    for item in registry:
        cat = str(item.category)
        if cat not in categories:
            categories[cat] = {"total": 0, "available": 0, "unavailable": 0}
        categories[cat]["total"] += 1

        resolved = None
        status = "---"
        opening = None
        current = None
        score = 0
        detail = ""

        try:
            # Indicadores tecnicos: testar se WIN$N esta disponivel
            if item.scoring_type == ScoringType.TECHNICAL_INDICATOR:
                tick = adapter.get_symbol_info_tick("WIN$N")
                if tick:
                    resolved = "WIN$N"
                    status = "DISPONIVEL"
                    detail = f"Indicador: {item.indicator_config.get('type', '?')}"
                    available.append(item)
                    categories[cat]["available"] += 1
                else:
                    status = "INDISPONIVEL"
                    detail = "WIN$N nao disponivel"
                    unavailable.append(item)
                    categories[cat]["unavailable"] += 1

            # Flow/Microestrutura: usa candles do WIN
            elif item.scoring_type == ScoringType.FLOW_INDICATOR:
                tick = adapter.get_symbol_info_tick("WIN$N")
                if tick:
                    resolved = "WIN$N"
                    status = "DISPONIVEL"
                    detail = f"Flow: {item.indicator_config.get('type', '?')}"
                    available.append(item)
                    categories[cat]["available"] += 1
                else:
                    status = "INDISPONIVEL"
                    detail = "WIN$N nao disponivel"
                    unavailable.append(item)
                    categories[cat]["unavailable"] += 1

            # Spread de curva: testar vertices
            elif item.scoring_type == ScoringType.SPREAD_CURVE:
                ic = item.indicator_config or {}
                short_v = ic.get("short_vertex", "DI1H")
                long_v = ic.get("long_vertex", "DI1F29")
                short_r = futures_resolver.resolve(short_v)
                long_r = futures_resolver.resolve(long_v)
                if short_r and long_r:
                    resolved = f"{short_r}/{long_r}"
                    status = "DISPONIVEL"
                    detail = f"Spread: {short_r} vs {long_r}"
                    available.append(item)
                    categories[cat]["available"] += 1
                else:
                    status = "INDISPONIVEL"
                    detail = f"Vertices: {short_v}={short_r} {long_v}={long_r}"
                    unavailable.append(item)
                    categories[cat]["unavailable"] += 1

            # Forex: resolver par (MT5 com fallback API)
            elif item.category == AssetCategory.FOREX:
                resolved = forex_handler.resolve_forex_symbol(item.symbol)
                if resolved:
                    status = "DISPONIVEL"
                    # Tentar obter dados
                    daily = adapter.get_daily_candle(resolved)
                    tick = adapter.get_symbol_info_tick(resolved)
                    if daily and tick:
                        opening = daily.open.value
                        current = tick.last.value
                        if current > opening:
                            score = 1
                        elif current < opening:
                            score = -1
                        # Aplicar convencao forex
                        raw = forex_handler.calculate_raw_score(
                            item.symbol, current, opening
                        )
                        detail = f"Raw={raw:+d} Conv={item.forex_convention}"
                        with_data.append(item)
                    available.append(item)
                    categories[cat]["available"] += 1
                else:
                    # Fallback: tentar via AwesomeAPI
                    quote = forex_api.get_quote(item.symbol)
                    if quote:
                        resolved = f"API:{item.symbol}/USD"
                        status = "DISPONIVEL"
                        opening = quote.opening
                        current = quote.bid
                        raw = forex_handler.calculate_raw_score(
                            item.symbol, current, opening
                        )
                        score = raw
                        detail = f"API | Var: {quote.pct_change:+}%"
                        with_data.append(item)
                        available.append(item)
                        categories[cat]["available"] += 1
                    else:
                        status = "INDISPONIVEL"
                        detail = "Par forex nao encontrado (MT5 e API)"
                        unavailable.append(item)
                        categories[cat]["unavailable"] += 1

            # Futuros: resolver contrato
            elif item.is_futures:
                resolved = futures_resolver.resolve(item.symbol)
                if resolved:
                    status = "DISPONIVEL"
                    daily = adapter.get_daily_candle(resolved)
                    tick = adapter.get_symbol_info_tick(resolved)
                    if daily and tick:
                        opening = daily.open.value
                        current = tick.last.value
                        if current > opening:
                            score = 1
                        elif current < opening:
                            score = -1
                        detail = f"Contrato resolvido"
                        with_data.append(item)
                    available.append(item)
                    categories[cat]["available"] += 1
                else:
                    status = "INDISPONIVEL"
                    detail = "Contrato futuro nao resolvido"
                    unavailable.append(item)
                    categories[cat]["unavailable"] += 1

            # Ativo normal: tentar direto
            else:
                # Habilitar simbolo primeiro (indices teoricos precisam de select)
                adapter.select_symbol(item.symbol)
                tick = adapter.get_symbol_info_tick(item.symbol)
                if tick and tick.last.value > 0:
                    resolved = item.symbol
                    status = "DISPONIVEL"
                    daily = adapter.get_daily_candle(item.symbol)
                    if daily:
                        opening = daily.open.value
                        current = tick.last.value
                        if current > opening:
                            score = 1
                        elif current < opening:
                            score = -1
                        with_data.append(item)
                    available.append(item)
                    categories[cat]["available"] += 1
                elif tick:
                    status = "SEM TICK"
                    detail = "Simbolo existe mas sem tick"
                    unavailable.append(item)
                    categories[cat]["unavailable"] += 1
                else:
                    status = "INDISPONIVEL"
                    detail = "Simbolo nao encontrado"
                    unavailable.append(item)
                    categories[cat]["unavailable"] += 1

        except Exception as e:
            status = "ERRO"
            detail = str(e)[:40]
            errors.append((item, str(e)))
            unavailable.append(item)
            categories[cat]["unavailable"] += 1

        # Formatar linha
        open_str = f"{opening:>12.2f}" if opening else f"{'---':>12}"
        curr_str = f"{current:>12.2f}" if current else f"{'---':>12}"
        score_str = f"{score:+d}" if status == "DISPONIVEL" and opening else "---"
        resolved_str = (resolved or "---")[:15]

        print(f"{item.number:>3} | {item.symbol:<10} | {resolved_str:<15} | "
              f"{status:<12} | {open_str} | {curr_str} | {score_str:>5} | {detail}")

    print("-" * 90)

    # Resumo
    print()
    print("=" * 90)
    print("  RESUMO")
    print("=" * 90)
    print(f"  Total de itens:       {len(registry)}")
    print(f"  Disponiveis:          {len(available)}")
    print(f"  Indisponiveis:        {len(unavailable)}")
    print(f"  Com dados de preco:   {len(with_data)}")
    print(f"  Erros:                {len(errors)}")
    print(f"  Cobertura:            {len(available)/len(registry)*100:.1f}%")
    print()

    # Por categoria
    print("  POR CATEGORIA:")
    print(f"  {'Categoria':<30} | {'Total':>5} | {'OK':>5} | {'Falta':>5} | {'%':>6}")
    print("  " + "-" * 65)
    for cat, stats in sorted(categories.items()):
        pct = (stats["available"] / stats["total"] * 100) if stats["total"] > 0 else 0
        cat_display = cat.replace("AssetCategory.", "")
        print(f"  {cat_display:<30} | {stats['total']:>5} | "
              f"{stats['available']:>5} | {stats['unavailable']:>5} | {pct:>5.1f}%")

    print()

    # Simbolos indisponiveis
    if unavailable:
        print("  SIMBOLOS INDISPONIVEIS (a resolver):")
        for item in unavailable:
            print(f"    #{item.number:>2} {item.symbol:<10} - {item.name}")
    print()

    # Erros
    if errors:
        print("  ERROS:")
        for item, err in errors:
            print(f"    #{item.number:>2} {item.symbol:<10} - {err}")
    print()

    # Teste do engine completo
    print("=" * 90)
    print("  TESTE DO MACRO SCORE ENGINE")
    print("=" * 90)

    try:
        from src.application.services.macro_score.engine import MacroScoreEngine

        engine = MacroScoreEngine(
            mt5_adapter=adapter,
            repository=None,
        )

        print("  Executando analyze()...")
        result = engine.analyze()

        print(f"\n  Score Final:    {result.score_final:+.2f}")
        print(f"  Sinal:          {result.signal}")
        print(f"  Bias:           {result.get_trading_bias()}")
        print(f"  Confianca:      {result.confidence:.0%}")
        print(f"  Disponiveis:    {result.items_available}/{result.total_items}")
        print(f"  Score Alta:     +{result.score_bullish:.1f}")
        print(f"  Score Baixa:    -{result.score_bearish:.1f}")
        print(f"  Neutros:        {result.score_neutral}")

        if result.win_price:
            print(f"  WIN Preco:      {result.win_price:,.2f}")

        print(f"\n  Resumo: {result.summary}")

        # Top contribuidores positivos
        top_bull = sorted(
            [i for i in result.items if i.available and i.final_score > 0],
            key=lambda x: x.weighted_score,
            reverse=True,
        )[:5]

        if top_bull:
            print("\n  TOP 5 CONTRIBUIDORES POSITIVOS (+):")
            for item in top_bull:
                print(f"    {item.symbol:<10} {item.name:<25} Score: {item.final_score:+d} | "
                      f"Peso: {item.weight} | {item.detail[:40]}")

        # Top contribuidores negativos
        top_bear = sorted(
            [i for i in result.items if i.available and i.final_score < 0],
            key=lambda x: x.weighted_score,
        )[:5]

        if top_bear:
            print("\n  TOP 5 CONTRIBUIDORES NEGATIVOS (-):")
            for item in top_bear:
                print(f"    {item.symbol:<10} {item.name:<25} Score: {item.final_score:+d} | "
                      f"Peso: {item.weight} | {item.detail[:40]}")

    except Exception as e:
        print(f"  [ERRO] Falha no engine: {e}")
        import traceback
        traceback.print_exc()

    print()
    print("=" * 90)

    # Desconectar
    adapter.disconnect()
    print("  [OK] Desconectado do MT5")
    print("=" * 90)


if __name__ == "__main__":
    validate_macro_score()

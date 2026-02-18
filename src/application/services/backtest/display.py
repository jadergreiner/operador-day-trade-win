"""Formatacao e exibicao de resultados do backtest MacroScore."""

from datetime import datetime
from decimal import Decimal
from typing import Optional

from src.application.services.macro_score.engine import (
    ItemScoreResult,
    MacroScoreResult,
)
from src.domain.enums.macro_score_enums import AssetCategory, MacroSignal
from src.infrastructure.adapters.mt5_adapter import Candle


# Mapeamento de categorias para nomes curtos na exibicao
CATEGORY_DISPLAY = {
    AssetCategory.INDICES_BRASIL: "Indices Brasil",
    AssetCategory.ACOES_BRASIL: "Acoes Brasil",
    AssetCategory.DOLAR_CAMBIO: "Dolar/Cambio",
    AssetCategory.FOREX: "Forex",
    AssetCategory.COMMODITIES: "Commodities",
    AssetCategory.JUROS_RENDA_FIXA: "Juros/Renda Fixa",
    AssetCategory.CRIPTOMOEDAS: "Criptomoedas",
    AssetCategory.INDICES_GLOBAIS: "Indices Globais",
    AssetCategory.VOLATILIDADE: "Volatilidade",
    AssetCategory.INDICADORES_TECNICOS: "Indicadores Tec",
}


class BacktestDisplay:
    """Formatacao e exibicao de resultados do backtest barra-a-barra."""

    LINE_WIDTH = 90

    def show_header(
        self,
        date: datetime,
        total_bars: int,
        symbols_loaded: int,
        symbols_failed: int,
        total_items: int,
    ) -> None:
        """Mostra cabecalho da sessao de backtest."""
        print()
        print("=" * self.LINE_WIDTH)
        print(f"  BACKTEST INTERATIVO - MACRO SCORE")
        print(f"  Data: {date.strftime('%d/%m/%Y')}")
        print(f"  Barras M15 do WIN: {total_bars}")
        print(
            f"  Simbolos carregados: {symbols_loaded}/{total_items} "
            f"({symbols_failed} falhas)"
        )
        print("=" * self.LINE_WIDTH)
        print()
        print("  Pressione [Enter] para avancar barra a barra.")
        print("  Digite [Q] e Enter para encerrar.")
        print()

    def show_bar(
        self,
        bar_number: int,
        total_bars: int,
        candle: Candle,
        result: MacroScoreResult,
        daily_open: Optional[Decimal] = None,
    ) -> None:
        """Mostra resultado de uma barra M15."""
        # Variacao do WIN em relacao a abertura
        win_change_str = ""
        if daily_open and daily_open > 0 and result.win_price:
            win_change = (
                (result.win_price - daily_open) / daily_open * 100
            )
            win_change_str = f" ({win_change:+.2f}%)"

        # Sinal com indicador visual
        signal_display = {
            MacroSignal.COMPRA: "COMPRA  ^",
            MacroSignal.VENDA: "VENDA   v",
            MacroSignal.NEUTRO: "NEUTRO  -",
        }

        print("=" * self.LINE_WIDTH)
        print(
            f"  Barra {bar_number}/{total_bars} | "
            f"{candle.timestamp.strftime('%H:%M')} | "
            f"WIN: {candle.close.value:,.0f}{win_change_str}"
        )
        print("-" * self.LINE_WIDTH)

        # Score final e sinal
        print(
            f"  SCORE: {result.score_final:+.1f} | "
            f"SINAL: {signal_display[result.signal]} | "
            f"Confianca: {result.confidence:.0%}"
        )
        print(
            f"  Alta: +{result.score_bullish:.1f} | "
            f"Baixa: -{result.score_bearish:.1f} | "
            f"Neutros: {result.score_neutral} | "
            f"Disponiveis: {result.items_available}/{result.total_items}"
        )
        print()

        # Detalhamento por categoria
        self._show_category_breakdown(result.items)

        print("=" * self.LINE_WIDTH)

    def _show_category_breakdown(self, items: list[ItemScoreResult]) -> None:
        """Mostra breakdown por categoria com itens individuais."""
        # Agrupar por categoria
        by_category: dict[AssetCategory, list[ItemScoreResult]] = {}
        for item in items:
            if item.category not in by_category:
                by_category[item.category] = []
            by_category[item.category].append(item)

        # Ordem fixa das categorias
        category_order = [
            AssetCategory.INDICES_BRASIL,
            AssetCategory.ACOES_BRASIL,
            AssetCategory.DOLAR_CAMBIO,
            AssetCategory.FOREX,
            AssetCategory.COMMODITIES,
            AssetCategory.JUROS_RENDA_FIXA,
            AssetCategory.CRIPTOMOEDAS,
            AssetCategory.INDICES_GLOBAIS,
            AssetCategory.VOLATILIDADE,
            AssetCategory.INDICADORES_TECNICOS,
        ]

        for category in category_order:
            cat_items = by_category.get(category, [])
            if not cat_items:
                continue

            cat_name = CATEGORY_DISPLAY.get(category, str(category))
            cat_score = sum(i.weighted_score for i in cat_items)
            available = [i for i in cat_items if i.available]

            # Linha da categoria com score total
            score_sign = "+" if cat_score > 0 else ""
            print(f"  {cat_name:<18} ({score_sign}{cat_score:.0f})  ", end="")

            # Itens individuais (apenas disponiveis, resumo compacto)
            item_parts = []
            for item in available:
                score_char = (
                    "+" if item.final_score > 0
                    else "-" if item.final_score < 0
                    else "0"
                )
                # Usar simbolo curto
                sym = item.symbol[:6]
                item_parts.append(f"{sym}{score_char}")

            # Mostrar itens (limitar para caber na linha)
            items_str = " ".join(item_parts)
            if len(items_str) > 55:
                items_str = items_str[:52] + "..."
            print(items_str)

    def show_summary(self, all_results: list[MacroScoreResult]) -> None:
        """Mostra resumo final da sessao de backtest."""
        if not all_results:
            print("\n  Nenhuma barra processada.\n")
            return

        print()
        print("=" * self.LINE_WIDTH)
        print("  RESUMO DO BACKTEST")
        print("=" * self.LINE_WIDTH)

        total = len(all_results)
        compra = sum(
            1 for r in all_results if r.signal == MacroSignal.COMPRA
        )
        venda = sum(
            1 for r in all_results if r.signal == MacroSignal.VENDA
        )
        neutro = sum(
            1 for r in all_results if r.signal == MacroSignal.NEUTRO
        )

        scores = [float(r.score_final) for r in all_results]
        score_medio = sum(scores) / len(scores) if scores else 0
        score_max = max(scores) if scores else 0
        score_min = min(scores) if scores else 0

        print(f"  Total de barras:     {total}")
        print(f"  Sinais COMPRA:       {compra} ({compra/total*100:.0f}%)")
        print(f"  Sinais VENDA:        {venda} ({venda/total*100:.0f}%)")
        print(f"  Sinais NEUTRO:       {neutro} ({neutro/total*100:.0f}%)")
        print()
        print(f"  Score medio:         {score_medio:+.2f}")
        print(f"  Score maximo:        {score_max:+.1f}")
        print(f"  Score minimo:        {score_min:+.1f}")

        # Evolucao temporal simples
        if total > 1:
            print()
            print("  EVOLUCAO DO SCORE:")
            bar_width = 50
            abs_max = max(abs(score_max), abs(score_min), 1)

            for i, result in enumerate(all_results):
                time_str = result.timestamp.strftime("%H:%M")
                score_val = float(result.score_final)
                # Barra proporcional
                bar_len = int(abs(score_val) / abs_max * (bar_width // 2))
                if score_val > 0:
                    bar = " " * (bar_width // 2) + "#" * bar_len
                elif score_val < 0:
                    pad = (bar_width // 2) - bar_len
                    bar = " " * pad + "#" * bar_len
                else:
                    bar = " " * (bar_width // 2) + "|"

                signal_char = (
                    "C" if result.signal == MacroSignal.COMPRA
                    else "V" if result.signal == MacroSignal.VENDA
                    else "N"
                )
                print(f"  {time_str} [{signal_char}] {result.score_final:+6.1f} |{bar}")

        # Predominancia
        print()
        if compra > venda and compra > neutro:
            print("  PREDOMINANCIA: COMPRA (vies altista no dia)")
        elif venda > compra and venda > neutro:
            print("  PREDOMINANCIA: VENDA (vies baixista no dia)")
        else:
            print("  PREDOMINANCIA: NEUTRO (sem direcao clara)")

        print()
        print("=" * self.LINE_WIDTH)

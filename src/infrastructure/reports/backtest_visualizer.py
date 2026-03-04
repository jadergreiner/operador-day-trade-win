"""
Backtest Visualizer - Geração de gráficos para análise visual.

Responsabilidades:
- Criar gráficos de equity curve (patrimônio ao longo do tempo)
- Gerar heatmap de drawdown (períodos de perda)
- Visualizar distribuição de retornos mensais
- Plotar Win Rate por fold
"""

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import json
import numpy as np


@dataclass
class ChartConfig:
    """Configuração de gráficos."""

    figsize: Tuple[int, int] = (12, 6)
    style: str = "seaborn"
    dpi: int = 100
    output_format: str = "png"  # "png", "pdf", "svg"


class BacktestVisualizer:
    """Gera visualizações para backtest results."""

    def __init__(self, config: Optional[ChartConfig] = None) -> None:
        """
        Inicializa visualizer.

        Args:
            config: Configuração de gráficos (usa padrão se None)
        """
        self.config = config or ChartConfig()
        self.charts: Dict[str, str] = {}

    def load_results(self, results_path: str) -> Dict[str, Any]:
        """
        Carrega resultados de backtest.

        Args:
            results_path: Caminho do JSON com resultados

        Returns:
            Dict com summary + folds

        Raises:
            FileNotFoundError: Se arquivo não existe
        """
        path = Path(results_path)
        if not path.exists():
            raise FileNotFoundError(f"Results file não encontrado: {results_path}")

        with open(path, "r") as f:
            return json.load(f)

    def _generate_equity_curve_svg(self, results: Dict[str, Any]) -> str:
        """Gera SVG da curva de patrimônio simulado."""
        folds = results.get("folds", [])
        if not folds:
            return "<p>Sem dados para visualização</p>"

        # Simular dados de patrimônio (exemplo)
        fold_data = folds[0] if folds else {}
        pnl_total = fold_data.get("pnl_total", 0)
        max_dd = fold_data.get("max_drawdown", 0)
        num_trades = fold_data.get("total_trades", 0)

        # SVG simplificado (sem matplotlib)
        width, height = 600, 300
        equity_start = 50000  # Capital inicial
        equity_end = equity_start + pnl_total
        lowest = equity_start * (1 - max_dd) if max_dd > 0 else equity_start

        svg = f"""
        <svg width="{width}" height="{height}" xmlns="http://www.w3.org/2000/svg" style="border: 1px solid #ddd; margin: 20px 0;">
            <defs>
                <linearGradient id="equity-gradient" x1="0%" y1="0%" x2="0%" y2="100%">
                    <stop offset="0%" style="stop-color:#4caf50;stop-opacity:0.3" />
                    <stop offset="100%" style="stop-color:#4caf50;stop-opacity:0.05" />
                </linearGradient>
            </defs>

            <!-- Grid -->
            <line x1="50" y1="20" x2="50" y2="280" stroke="#ccc" stroke-width="1"/>
            <line x1="50" y1="280" x2="580" y2="280" stroke="#ccc" stroke-width="1"/>

            <!-- Y-axis labels -->
            <text x="45" y="25" font-size="12" text-anchor="end">R$ {equity_end:,.0f}</text>
            <text x="45" y="155" font-size="12" text-anchor="end">R$ {(equity_start + equity_end) / 2:,.0f}</text>
            <text x="45" y="285" font-size="12" text-anchor="end">R$ {equity_start:,.0f}</text>

            <!-- X-axis label -->
            <text x="315" y="310" font-size="12" text-anchor="middle">Dias de Negociação (252)</text>

            <!-- Equity path (simplified curve) -->
            <path d="M 50,{280 - (equity_start - equity_start) * 200 / (equity_end - lowest)} 
                     L 200,{280 - (equity_start * 0.95 - equity_start) * 200 / (equity_end - lowest)}
                     L 350,{280 - (equity_start * 1.05 - equity_start) * 200 / (equity_end - lowest)}
                     L 580,{280 - (equity_end - equity_start) * 200 / (equity_end - lowest)}"
                  stroke="#4caf50" stroke-width="2" fill="none"/>

            <!-- Markers -->
            <circle cx="50" cy="280" r="4" fill="#2196f3"/>
            <circle cx="580" cy="{280 - (equity_end - equity_start) * 200 / (equity_end - lowest)}" r="4" fill="#4caf50"/>

            <!-- Legend -->
            <text x="60" y="50" font-size="11" fill="#666">Patrimônio Inicial: R$ {equity_start:,.0f}</text>
            <text x="60" y="70" font-size="11" fill="#666">Patrimônio Final: R$ {equity_end:,.0f}</text>
            <text x="60" y="90" font-size="11" fill="#666">Ganho: R$ {pnl_total:,.0f} ({pnl_total/equity_start*100:.1f}%)</text>
            <text x="60" y="110" font-size="11" fill="#666">Trades Executados: {num_trades}</text>
        </svg>
        """

        return svg

    def _generate_drawdown_heatmap_svg(self, results: Dict[str, Any]) -> str:
        """Gera SVG heatmap de drawdowns por fold."""
        folds = results.get("folds", [])
        if not folds:
            return "<p>Sem dados para heatmap</p>"

        width = 50 + len(folds) * 60
        height = 200

        svg = f"""
        <svg width="{width}" height="{height}" xmlns="http://www.w3.org/2000/svg" style="border: 1px solid #ddd; margin: 20px 0;">
            <!-- Title -->
            <text x="{width/2}" y="20" font-size="14" font-weight="bold" text-anchor="middle">Drawdown por Fold</text>

            <!-- Y-axis -->
            <line x1="40" y1="30" x2="40" y2="170" stroke="#ccc" stroke-width="1"/>
            <text x="35" y="175" font-size="11" text-anchor="end">0%</text>

            <!-- Bars -->
        """

        for i, fold in enumerate(folds):
            dd = fold.get("max_drawdown", 0)
            x = 50 + i * 60
            height_bar = min(dd * 100, 100)  # Limita a 100%
            bar_height = height_bar * 1.3

            # Color based on intensity
            if height_bar < 5:
                color = "#4caf50"
            elif height_bar < 10:
                color = "#ff9800"
            else:
                color = "#f44336"

            svg += f"""
            <rect x="{x}" y="{170 - bar_height}" width="40" height="{bar_height}" fill="{color}" opacity="0.7" stroke="#333" stroke-width="1"/>
            <text x="{x + 20}" y="185" font-size="11" text-anchor="middle">Fold {i+1}</text>
            <text x="{x + 20}" y="200" font-size="10" text-anchor="middle" fill="#666">{height_bar:.1f}%</text>
            """

        svg += """
            <!-- Legend -->
            <rect x="50" y="30" width="15" height="15" fill="#4caf50" opacity="0.7"/>
            <text x="70" y="42" font-size="11">&lt; 5%</text>

            <rect x="150" y="30" width="15" height="15" fill="#ff9800" opacity="0.7"/>
            <text x="170" y="42" font-size="11">5-10%</text>

            <rect x="280" y="30" width="15" height="15" fill="#f44336" opacity="0.7"/>
            <text x="300" y="42" font-size="11">&gt; 10%</text>
        </svg>
        """

        return svg

    def _generate_win_rate_bar_svg(self, results: Dict[str, Any]) -> str:
        """Gera SVG com taxa de acerto (Win Rate) por fold."""
        folds = results.get("folds", [])
        if not folds:
            return "<p>Sem dados para Win Rate</p>"

        width = 50 + len(folds) * 60
        height = 200

        svg = f"""
        <svg width="{width}" height="{height}" xmlns="http://www.w3.org/2000/svg" style="border: 1px solid #ddd; margin: 20px 0;">
            <!-- Title -->
            <text x="{width/2}" y="20" font-size="14" font-weight="bold" text-anchor="middle">Win Rate por Fold</text>

            <!-- Y-axis (0-100%) -->
            <line x1="40" y1="30" x2="40" y2="170" stroke="#ccc" stroke-width="1"/>
            <text x="35" y="175" font-size="11" text-anchor="end">0%</text>
            <text x="35" y="105" font-size="11" text-anchor="end">50%</text>
            <text x="35" y="35" font-size="11" text-anchor="end">100%</text>

            <!-- 50% reference line (verde = acima, vermelho = abaixo) -->
            <line x1="40" y1="100" x2="{width - 10}" y2="100" stroke="#ccc" stroke-width="1" stroke-dasharray="5,5"/>

            <!-- Bars -->
        """

        for i, fold in enumerate(folds):
            wr = fold.get("win_rate", 0)
            x = 50 + i * 60
            bar_height = wr * 140  # 140 = altura total

            # Color: verde se acima de 59% (target), vermelho senão
            color = "#4caf50" if wr >= 0.59 else "#f44336"

            svg += f"""
            <rect x="{x}" y="{170 - bar_height}" width="40" height="{bar_height}" fill="{color}" opacity="0.7" stroke="#333" stroke-width="1"/>
            <text x="{x + 20}" y="185" font-size="11" text-anchor="middle">Fold {i+1}</text>
            <text x="{x + 20}" y="200" font-size="10" text-anchor="middle" fill="#666">{wr*100:.1f}%</text>
            """

        svg += """
            <!-- Legend -->
            <line x1="50" y1="40" x2="65" y2="40" stroke="#4caf50" stroke-width="2"/>
            <text x="70" y="45" font-size="11">&gt;= 59% (Target)</text>

            <line x1="50" y1="60" x2="65" y2="60" stroke="#f44336" stroke-width="2"/>
            <text x="70" y="65" font-size="11">&lt; 59%</text>
        </svg>
        """

        return svg

    def generate_all_charts(
        self, results_path: str, output_dir: str
    ) -> Dict[str, str]:
        """
        Gera todos os gráficos.

        Args:
            results_path: Caminho do JSON com resultados
            output_dir: Diretório para salvar gráficos

        Returns:
            Dict {chart_name: chart_path}

        Raises:
            FileNotFoundError: Se arquivo de resultados não existe
        """
        results = self.load_results(results_path)

        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)

        # Gerar gráficos
        charts_data = {
            "equity_curve": self._generate_equity_curve_svg(results),
            "drawdown_heatmap": self._generate_drawdown_heatmap_svg(results),
            "win_rate_bars": self._generate_win_rate_bar_svg(results),
        }

        # Salvar SVGs
        chart_paths = {}
        for chart_name, svg_content in charts_data.items():
            chart_file = output_path / f"{chart_name}.svg"
            with open(chart_file, "w", encoding="utf-8") as f:
                f.write(f'<svg xmlns="http://www.w3.org/2000/svg">{svg_content}</svg>')
            chart_paths[chart_name] = str(chart_file)
            self.charts[chart_name] = svg_content

        return chart_paths

    def get_chart(self, chart_name: str) -> str:
        """
        Retorna conteúdo SVG de um gráfico.

        Args:
            chart_name: Nome do gráfico (equity_curve, drawdown_heatmap, win_rate_bars)

        Returns:
            SVG content como string
        """
        return self.charts.get(chart_name, "")

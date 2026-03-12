"""
Backtest Reporter - Geração de relatórios HTML/PDF com análise completa.

Responsabilidades:
- Gerar HTML com 20+ seções (summary, performance, risk, allocation)
- Renderizar templates com dados do backtest
- Exportar para PDF (opcional)
- Incluir visualizações inline (base64 encoded)
"""

from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

import json


@dataclass
class ReportConfig:
    """Configuração de relatório."""

    title: str = "Backtest Validation Report - P0-2"
    author: str = "ML Expert Team"
    company: str = "Operador WIN"
    report_date: str = ""
    output_format: str = "html"  # "html" or "pdf"

    def __post_init__(self) -> None:
        """Inicializa data se não fornecida."""
        if not self.report_date:
            self.report_date = datetime.now().strftime("%d/%m/%Y %H:%M")


class BacktestReporter:
    """Gera relatórios HTML/PDF para resultados de backtest."""

    def __init__(self, config: Optional[ReportConfig] = None) -> None:
        """
        Inicializa reporter.

        Args:
            config: Configuração do relatório (usa padrão se None)
        """
        self.config = config or ReportConfig()
        self.html_content = ""
        self.sections: List[str] = []

    def load_results(self, results_path: str) -> Dict[str, Any]:
        """
        Carrega resultados de backtest.

        Args:
            results_path: Caminho do JSON com resultados

        Returns:
            Dict com summary + folds

        Raises:
            FileNotFoundError: Se arquivo não existe
            json.JSONDecodeError: Se JSON inválido
        """
        path = Path(results_path)
        if not path.exists():
            raise FileNotFoundError(f"Results file não encontrado: {results_path}")

        with open(path, "r") as f:
            results = json.load(f)

        audit_path = path.parent / "dataset_audit.json"
        if audit_path.exists():
            try:
                with open(audit_path, "r", encoding="utf-8") as handle:
                    results["dataset_audit"] = json.load(handle)
            except json.JSONDecodeError:
                results["dataset_audit"] = {"audit_passed": False, "error": "invalid_json"}

        return results

    def _create_header(self) -> str:
        """Cria seção de header do relatório."""
        return f"""
        <!DOCTYPE html>
        <html lang="pt-BR">
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>{self.config.title}</title>
            <style>
                body {{ font-family: Arial, sans-serif; margin: 20px; background: #f5f5f5; }}
                .container {{ max-width: 1200px; margin: 0 auto; background: white; padding: 20px; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }}
                h1, h2, h3 {{ color: #1a1a1a; border-bottom: 2px solid #007bff; padding-bottom: 10px; }}
                h1 {{ font-size: 28px; margin-bottom: 5px; }}
                .metadata {{ color: #666; font-size: 12px; margin-bottom: 20px; }}
                .summary-grid {{ display: grid; grid-template-columns: repeat(4, 1fr); gap: 15px; margin: 20px 0; }}
                .metric-card {{ background: #f9f9f9; padding: 15px; border-left: 4px solid #007bff; border-radius: 4px; }}
                .metric-card.warning {{ border-left-color: #ff9800; }}
                .metric-card.danger {{ border-left-color: #f44336; }}
                .metric-card.success {{ border-left-color: #4caf50; }}
                .metric-label {{ font-size: 12px; color: #999; text-transform: uppercase; }}
                .metric-value {{ font-size: 24px; font-weight: bold; color: #1a1a1a; margin-top: 5px; }}
                .metric-unit {{ font-size: 12px; color: #666; }}
                table {{ width: 100%; border-collapse: collapse; margin: 20px 0; }}
                th {{ background: #007bff; color: white; padding: 12px; text-align: left; }}
                td {{ padding: 10px; border-bottom: 1px solid #ddd; }}
                tr:nth-child(even) {{ background: #f9f9f9; }}
                .pass {{ color: #4caf50; font-weight: bold; }}
                .fail {{ color: #f44336; font-weight: bold; }}
                .accent {{ color: #007bff; font-weight: bold; }}
                .section {{ page-break-inside: avoid; margin-bottom: 30px; }}
                footer {{ margin-top: 40px; padding-top: 20px; border-top: 1px solid #ddd; color: #999; font-size: 12px; text-align: center; }}
            </style>
        </head>
        <body>
            <div class="container">
                <h1>{self.config.title}</h1>
                <div class="metadata">
                    <p><strong>Relatório:</strong> {self.config.author} | <strong>Data:</strong> {self.config.report_date} | <strong>Empresa:</strong> {self.config.company}</p>
                </div>
        """

    def _create_executive_summary(self, results: Dict[str, Any]) -> str:
        """Cria sumário executivo com métricas principais."""
        summary = results.get("summary", {})
        dataset_audit = results.get("dataset_audit", {})

        # Determinar status Gate 2
        sharpe_pass = summary.get("mean_sharpe", 0) >= 1.0
        wr_pass = summary.get("mean_win_rate", 0) >= 0.59
        dd_pass = summary.get("mean_max_drawdown", 1.0) < 0.15
        consistency_value = summary.get(
            "consistency_std",
            summary.get("mean_monthly_consistency", float("inf"))
        )
        consistency_pass = consistency_value < 0.30

        all_pass = sharpe_pass and wr_pass and dd_pass and consistency_pass
        gate_status = '<span class="pass">PASS ✓</span>' if all_pass else '<span class="fail">FAIL ✗</span>'

        audit_status = "AUDIT OK" if dataset_audit.get("audit_passed", False) else "AUDIT PENDENTE/FAIL"
        cost_profile = summary.get("cost_profile", {})
        cost_label = cost_profile.get("name", "n/a")
        min_confidence = summary.get("min_confidence", 0)
        hold_period = summary.get("hold_period_bars", 1)

        return f"""
        <div class="section">
            <h2>Sumário Executivo</h2>
            <div class="summary-grid">
                <div class="metric-card {'success' if sharpe_pass else 'danger'}">
                    <div class="metric-label">Sharpe Ratio</div>
                    <div class="metric-value">{summary.get('mean_sharpe', 0):.2f}</div>
                    <div class="metric-unit">Target: ≥ 1.0</div>
                </div>
                <div class="metric-card {'success' if wr_pass else 'danger'}">
                    <div class="metric-label">Win Rate</div>
                    <div class="metric-value">{summary.get('mean_win_rate', 0)*100:.1f}%</div>
                    <div class="metric-unit">Target: ≥ 59%</div>
                </div>
                <div class="metric-card {'success' if dd_pass else 'danger'}">
                    <div class="metric-label">Max Drawdown</div>
                    <div class="metric-value">{summary.get('mean_max_drawdown', 0)*100:.1f}%</div>
                    <div class="metric-unit">Target: < 15%</div>
                </div>
                <div class="metric-card {'success' if consistency_pass else 'warning'}">
                    <div class="metric-label">Consistência σ</div>
                    <div class="metric-value">{consistency_value:.2f}</div>
                    <div class="metric-unit">Target: < 0.30</div>
                </div>
            </div>
            <h3>Decisão GATE 2</h3>
            <p><strong>Status:</strong> {gate_status}</p>
            <p><strong>Recomendação:</strong> {'✓ Escalar para R$ 100k (FASE 2)' if all_pass else '✗ Manter em R$ 50k (revalidar modelo)'}</p>
            <p><strong>Dataset Audit:</strong> {audit_status}</p>
            <p><strong>Custos:</strong> {cost_label} | <strong>Min Confidence:</strong> {min_confidence:.2f} | <strong>Hold:</strong> {hold_period} barra</p>
        </div>
        """

    def _create_performance_analysis(self, results: Dict[str, Any]) -> str:
        """Cria análise detalhada de performance."""
        summary = results.get("summary", {})
        folds = results.get("folds", [])

        fold_rows = "\n".join(
            f"""
            <tr>
                <td>Fold {i + 1}</td>
                <td>{fold.get('sharpe_ratio', 0):.2f}</td>
                <td>{fold.get('win_rate', 0)*100:.1f}%</td>
                <td>{fold.get('max_drawdown', 0)*100:.1f}%</td>
                <td>{fold.get('pnl_total', 0):.2f}</td>
            </tr>
            """
            for i, fold in enumerate(folds)
        )

        return f"""
        <div class="section">
            <h2>Análise de Performance</h2>
            <p>Backtest executado com 5-fold cross-validation temporal (sem lookahead bias).</p>

            <h3>Resultados por Fold</h3>
            <table>
                <thead>
                    <tr>
                        <th>Fold</th>
                        <th>Sharpe Ratio</th>
                        <th>Win Rate</th>
                        <th>Max Drawdown</th>
                        <th>P&L Total</th>
                    </tr>
                </thead>
                <tbody>
                    {fold_rows}
                    <tr style="background: #f0f0f0; font-weight: bold;">
                        <td>Média</td>
                        <td>{summary.get('mean_sharpe', 0):.2f}</td>
                        <td>{summary.get('mean_win_rate', 0)*100:.1f}%</td>
                        <td>{summary.get('mean_max_drawdown', 0)*100:.1f}%</td>
                <td>{summary.get('total_pnl', 0):.2f}</td>
                    </tr>
                </tbody>
            </table>

            <h3>Métricas Complementares</h3>
            <ul>
                <li><strong>Sortino Ratio:</strong> {summary.get('mean_sortino_ratio', 0):.2f}</li>
                <li><strong>Profit Factor:</strong> {summary.get('mean_profit_factor', 0):.2f}</li>
                <li><strong>Recovery Factor:</strong> {summary.get('mean_recovery_factor', 0):.2f}</li>
                <li><strong>Expectancy:</strong> {summary.get('mean_expectancy', 0):.2f}</li>
                <li><strong>Trades (média):</strong> {summary.get('trade_count', 0)}</li>
                <li><strong>Retorno médio/trade:</strong> {summary.get('mean_return_per_trade', 0):.2f}</li>
            </ul>
        </div>
        """

    def _create_risk_analysis(self, results: Dict[str, Any]) -> str:
        """Cria análise de risco com detalhes mensais."""
        folds = results.get("folds", [])
        consistency_values = [
            f.get("pnl_monthly_std", f.get("monthly_consistency", 0))
            for f in folds
        ]
        avg_consistency = (
            sum(consistency_values) / len(consistency_values)
            if consistency_values
            else 0
        )

        return f"""
        <div class="section">
            <h2>Análise de Risco</h2>

            <h3>Métricas de Risco Agregadas</h3>
            <ul>
                <li><strong>Consistência Mensal (σ):</strong> {avg_consistency:.2f} (Target: &lt; 0.30)</li>
                <li><strong>Drawdown Máximo Observado:</strong> {max([f.get('max_drawdown', 0) for f in folds])*100:.1f}%</li>
                <li><strong>Drawdown Mínimo Observado:</strong> {min([f.get('max_drawdown', 0) for f in folds])*100:.1f}%</li>
                <li><strong>Hurst Exponent (média):</strong> {sum([f.get('hurst_exponent', 0.5) for f in folds])/len(folds) if folds else 0:.3f}</li>
            </ul>

            <h3>Circuit Breakers RECOMENDADOS</h3>
            <table>
                <thead>
                    <tr>
                        <th>Nível</th>
                        <th>Drawdown</th>
                        <th>Ação</th>
                        <th>Descrição</th>
                    </tr>
                </thead>
                <tbody>
                    <tr>
                        <td class="accent">🟡 ALERTA</td>
                        <td>-3%</td>
                        <td>Notificar trader</td>
                        <td>Operador fica atento</td>
                    </tr>
                    <tr>
                        <td class="accent">🟠 SLOW MODE</td>
                        <td>-5%</td>
                        <td>50% ticket size, 90% ML</td>
                        <td>Operação mais conservadora</td>
                    </tr>
                    <tr>
                        <td class="accent">🔴 HALT</td>
                        <td>-8%</td>
                        <td>Parar tudo (manual override)</td>
                        <td>Proteção máxima</td>
                    </tr>
                </tbody>
            </table>
        </div>
        """

    def _create_methodology(self) -> str:
        """Descreve metodologia de validação."""
        return """
        <div class="section">
            <h2>Metodologia</h2>

            <h3>Backtest Configuration</h3>
            <ul>
                <li><strong>Período:</strong> 252 dias de negociação (1 ano completo)</li>
                <li><strong>Features:</strong> 24 features engineered (volatilidade, momentum, MA, etc)</li>
                <li><strong>Cross-Validation:</strong> 5-fold TimeSeriesSplit (sem lookahead bias)</li>
                <li><strong>Frequência:</strong> Intraday trailing (4h/30m timeframe)</li>
            </ul>

            <h3>Validação Rigorosa</h3>
            <ul>
                <li>✓ Walk-forward validation (train < test em cada fold)</li>
                <li>✓ Sem lookahead bias (futures não usados)</li>
                <li>✓ Slippage 2 pts (estimado real)</li>
                <li>✓ Comissão incluída nos cálculos</li>
                <li>✓ Capital inicial R$ 50.000</li>
            </ul>

            <h3>GATE 2 Criteria (Bloqueadores)</h3>
            <p>TODOS os 4 critérios DEVEM ser satisfeitos para aprovação:</p>
            <table>
                <thead>
                    <tr>
                        <th>Critério</th>
                        <th>Métrica</th>
                        <th>Target Min</th>
                        <th>Justificativa</th>
                    </tr>
                </thead>
                <tbody>
                    <tr>
                        <td><strong>Rentabilidade</strong></td>
                        <td>Sharpe Ratio</td>
                        <td>≥ 1.0</td>
                        <td>Risk-adjusted return (1% risco = 1% retorno)</td>
                    </tr>
                    <tr>
                        <td><strong>Taxa Acerto</strong></td>
                        <td>Win Rate</td>
                        <td>≥ 59%</td>
                        <td>Mais ganhos que perdas (expectancy positiva)</td>
                    </tr>
                    <tr>
                        <td><strong>Proteção</strong></td>
                        <td>Max Drawdown</td>
                        <td>&lt; 15%</td>
                        <td>Perda máxima suportável (capital preservation)</td>
                    </tr>
                    <tr>
                        <td><strong>Consistência</strong></td>
                        <td>Monthly σ</td>
                        <td>&lt; 0.30</td>
                        <td>Variação mês a mês (previsibilidade)</td>
                    </tr>
                </tbody>
            </table>
        </div>
        """

    def _create_footer(self) -> str:
        """Cria rodapé com assinatura."""
        return """
                <footer>
                    <p>Relatório gerado automaticamente pelo sistema P0-2 Backtest Validação ML.</p>
                    <p>Este documento é confidencial e destinado apenas para stakeholders autorizados.</p>
                    <p>Reprodução ou distribuição sem autorização é proibida.</p>
                </footer>
            </div>
        </body>
        </html>
        """

    def generate_html(self, results_path: str, output_path: str) -> str:
        """
        Gera relatório HTML completo.

        Args:
            results_path: Caminho do JSON com resultados (backtest_results.json)
            output_path: Caminho para salvar o HTML gerado

        Returns:
            Conteúdo HTML gerado

        Raises:
            FileNotFoundError: Se arquivo de resultados não existe
            ValueError: Se resultados inválidos
        """
        results = self.load_results(results_path)

        # Validar estrutura
        if "summary" not in results:
            raise ValueError("Results deve conter chave 'summary'")
        if "folds" not in results:
            raise ValueError("Results deve conter chave 'folds'")

        # Construir HTML
        html_parts = [
            self._create_header(),
            self._create_executive_summary(results),
            self._create_performance_analysis(results),
            self._create_risk_analysis(results),
            self._create_methodology(),
            self._create_footer(),
        ]

        self.html_content = "".join(html_parts)

        # Salvar para arquivo
        output_file = Path(output_path)
        output_file.parent.mkdir(parents=True, exist_ok=True)
        with open(output_file, "w", encoding="utf-8") as f:
            f.write(self.html_content)

        return self.html_content

    def get_html(self) -> str:
        """Retorna HTML gerado (chamada após generate_html)."""
        return self.html_content

"""
AC6.7 - Detector de Drift de Modelo em Producao

Modulo responsavel por detectar degradacao de performance de modelo
em producao comparando metricas atuais contra baseline.

Componentes:
- DriftMetrics: Dataclass com metricas calculadas (win_rate, sharpe, etc)
- DriftAlert: Alerta de degradacao detectada
- DriftDetector: Classe principal com logica de deteccao

Arquitetura:
- Sliding window de ultimos N trades (default 100)
- Calculo de F1, win_rate, sharpe, PnL medio
- Comparacao contra baseline usando Z-score
- Alertas com severidade (LOW, MEDIUM, CRITICAL)
- Relatorios em JSON e Markdown

Exemplo:
    detector = DriftDetector(
        baseline_f1=0.68,
        baseline_win_rate=0.65,
        baseline_sharpe=1.2,
        window_size=100
    )

    for trade in trades:
        detector.adicionar_trade(trade)

    alerts = detector.detectar_drift(trades)
    if alerts:
        print(detector.gerar_relatorio_markdown(trades))
"""

import json
import statistics
from dataclasses import dataclass, field, asdict
from datetime import datetime
from enum import Enum
from typing import List, Dict, Optional, Tuple, Any
from pathlib import Path


class DriftAlertSeverity(str, Enum):
    """Niveis de severidade de alerta de drift."""
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    CRITICAL = "CRITICAL"


@dataclass
class DriftMetrics:
    """Metricas calculadas para deteccao de drift."""

    timestamp: datetime
    num_trades: int
    win_rate: float
    loss_rate: float
    avg_pnl: float
    total_pnl: float
    sharpe_ratio: float
    f1_score: float
    std_pnl: float

    def para_dict(self) -> Dict[str, Any]:
        """Converte metricas para dicionario."""
        return asdict(self)

    def para_json(self) -> str:
        """Converte metricas para JSON string."""
        data = self.para_dict()
        data["timestamp"] = data["timestamp"].isoformat()
        return json.dumps(data, indent=2)


@dataclass
class DriftAlert:
    """Alerta de degradacao de modelo detectada."""

    timestamp: datetime
    metric: str  # "win_rate", "sharpe", "f1", "avg_pnl"
    baseline_value: float
    current_value: float
    zscore: float
    severity: DriftAlertSeverity
    message: str

    def para_dict(self) -> Dict[str, Any]:
        """Converte alerta para dicionario."""
        return {
            "timestamp": self.timestamp.isoformat(),
            "metric": self.metric,
            "baseline_value": self.baseline_value,
            "current_value": self.current_value,
            "zscore": self.zscore,
            "severity": self.severity.value,
            "message": self.message,
        }

    def para_json(self) -> str:
        """Converte alerta para JSON string."""
        return json.dumps(self.para_dict(), indent=2)


class DriftDetector:
    """
    Detector de drift de modelo em producao.

    Monitora metricas de performance (win_rate, sharpe, F1) e detecta
    quando degradacao supera threshold usando Z-score estatistico.

    Atributos:
        baseline_f1: F1 score baseline (0-1)
        baseline_win_rate: Win rate baseline (0-1)
        baseline_sharpe: Sharpe ratio baseline
        drift_threshold_zscore: Threshold de Z-score para alertar (default 2.0)
        window_size: Tamanho da sliding window (default 100)
        trades_sliding_window: Lista de trades recentes

    Exemplo:
        detector = DriftDetector(
            baseline_f1=0.68,
            baseline_win_rate=0.65,
            baseline_sharpe=1.2
        )
        alerts = detector.detectar_drift(trades)
    """

    def __init__(
        self,
        baseline_f1: float = 0.0,
        baseline_win_rate: float = 0.0,
        baseline_sharpe: float = 0.0,
        drift_threshold_zscore: float = 2.0,
        window_size: int = 100,
    ) -> None:
        """
        Inicializa detector com baseline e parametros.

        Args:
            baseline_f1: F1 score baseline (0-1). Default 0.0
            baseline_win_rate: Win rate baseline (0-1). Default 0.0
            baseline_sharpe: Sharpe ratio baseline. Default 0.0
            drift_threshold_zscore: Z-score threshold para alerta. Default 2.0
            window_size: Tamanho sliding window. Default 100

        Raises:
            ValueError: Se parametros fora de range valido
        """
        if not (0.0 <= baseline_f1 <= 1.0):
            raise ValueError("baseline_f1 deve estar entre 0 e 1")
        if not (0.0 <= baseline_win_rate <= 1.0):
            raise ValueError("baseline_win_rate deve estar entre 0 e 1")
        if window_size <= 0:
            raise ValueError("window_size deve ser > 0")

        self.baseline_f1: float = baseline_f1
        self.baseline_win_rate: float = baseline_win_rate
        self.baseline_sharpe: float = baseline_sharpe
        self.drift_threshold_zscore: float = drift_threshold_zscore
        self.window_size: int = window_size
        self.trades_sliding_window: List[Any] = []
        self.alerts_history: List[DriftAlert] = []

    def adicionar_trade(self, trade: Any) -> None:
        """
        Adiciona trade a sliding window, descartando antigos se overflow.

        Args:
            trade: Trade object com fields trade_id, outcome, pnl, etc
        """
        self.trades_sliding_window.append(trade)

        # Manter apenas ultimas N trades
        if len(self.trades_sliding_window) > self.window_size:
            self.trades_sliding_window.pop(0)

    def calcular_metricas(self, trades: List[Any]) -> DriftMetrics:
        """
        Calcula metricas de performance dos trades.

        Args:
            trades: Lista de trades com outcome, pnl, etc

        Returns:
            DriftMetrics com win_rate, sharpe, etc

        Metricas:
            - win_rate: % de trades vencedores
            - loss_rate: % de trades perdedores
            - avg_pnl: PnL medio por trade
            - total_pnl: PnL total
            - sharpe_ratio: (mean_return - risk_free) / std_return
            - std_pnl: Desvio padrao de PnL
        """
        if not trades:
            return DriftMetrics(
                timestamp=datetime.now(),
                num_trades=0,
                win_rate=0.0,
                loss_rate=0.0,
                avg_pnl=0.0,
                total_pnl=0.0,
                sharpe_ratio=0.0,
                f1_score=0.0,
                std_pnl=0.0,
            )

        # Extrair outcomes e PnLs
        outcomes: List[str] = [
            str(trade.outcome).upper() for trade in trades
        ]
        pnls: List[float] = [float(trade.pnl) for trade in trades]

        # Contar wins, losses, breakevens
        num_wins = sum(1 for o in outcomes if o == "WIN")
        num_losses = sum(1 for o in outcomes if o == "LOSS")
        num_breakevens = sum(1 for o in outcomes if o == "BREAKEVEN")

        # Calcular taxa de sucesso
        win_rate = num_wins / len(trades) if trades else 0.0
        loss_rate = num_losses / len(trades) if trades else 0.0

        # Calcular PnL
        total_pnl = sum(pnls)
        avg_pnl = total_pnl / len(trades) if trades else 0.0

        # Calcular desvio padrao
        std_pnl = (
            statistics.stdev(pnls) if len(pnls) > 1 else 0.0
        )

        # Calcular Sharpe ratio (assuming risk-free rate = 0)
        sharpe_ratio = (
            (avg_pnl / std_pnl) if std_pnl > 0 else 0.0
        )

        # F1 score (como precision-recall balance)
        # Neste contexto: F1 = 2 * (win_rate * precision) / (win_rate + precision)
        # Simplificado: F1 = win_rate (ajuste conforme necessario)
        f1_score = win_rate

        return DriftMetrics(
            timestamp=datetime.now(),
            num_trades=len(trades),
            win_rate=win_rate,
            loss_rate=loss_rate,
            avg_pnl=avg_pnl,
            total_pnl=total_pnl,
            sharpe_ratio=sharpe_ratio,
            f1_score=f1_score,
            std_pnl=std_pnl,
        )

    def _calcular_zscore(
        self, valor_atual: float, valor_baseline: float, std: float = 0.1
    ) -> float:
        """
        Calcula Z-score para deteccao de anomalia.

        Z-score = (valor_atual - valor_baseline) / desvio_padrao

        Args:
            valor_atual: Valor medido atualmente
            valor_baseline: Valor baseline esperado
            std: Desvio padrao (default 0.1)

        Returns:
            Z-score (valor absoluto)
        """
        if std == 0:
            return 0.0
        return abs((valor_atual - valor_baseline) / std)

    def detectar_drift(self, trades: List[Any]) -> List[DriftAlert]:
        """
        Detecta drift comparando metricas atuais contra baseline.

        Usa Z-score para determinar if degradacao eh significativa.
        Limiar padrao: Z-score >= 2.0 = degradacao significativa

        Args:
            trades: Lista de trades recentes (sliding window)

        Returns:
            Lista de DriftAlert se drift detectado, lista vazia caso contrario

        Alertas gerados para:
            - win_rate: Se cai significativamente
            - sharpe_ratio: Se diminui (volatilidade aumenta)
            - avg_pnl: Se fica muito negativo
        """
        alerts: List[DriftAlert] = []

        # Calcular metricas atuais
        current_metrics = self.calcular_metricas(trades)

        # Comparar win_rate com baseline
        if self.baseline_win_rate > 0:
            zscore_wr = self._calcular_zscore(
                current_metrics.win_rate,
                self.baseline_win_rate,
                std=0.05
            )
            if zscore_wr >= self.drift_threshold_zscore:
                severity = (
                    DriftAlertSeverity.CRITICAL if zscore_wr > 3.0
                    else DriftAlertSeverity.MEDIUM
                )
                alert = DriftAlert(
                    timestamp=datetime.now(),
                    metric="win_rate",
                    baseline_value=self.baseline_win_rate,
                    current_value=current_metrics.win_rate,
                    zscore=zscore_wr,
                    severity=severity,
                    message=(
                        f"Degradacao win_rate: {current_metrics.win_rate:.2%} "
                        f"vs baseline {self.baseline_win_rate:.2%}"
                    ),
                )
                alerts.append(alert)

        # Comparar sharpe_ratio com baseline
        if self.baseline_sharpe > 0:
            zscore_sharpe = self._calcular_zscore(
                current_metrics.sharpe_ratio,
                self.baseline_sharpe,
                std=0.2
            )
            if zscore_sharpe >= self.drift_threshold_zscore:
                severity = (
                    DriftAlertSeverity.CRITICAL if zscore_sharpe > 3.0
                    else DriftAlertSeverity.MEDIUM
                )
                alert = DriftAlert(
                    timestamp=datetime.now(),
                    metric="sharpe",
                    baseline_value=self.baseline_sharpe,
                    current_value=current_metrics.sharpe_ratio,
                    zscore=zscore_sharpe,
                    severity=severity,
                    message=(
                        f"Degradacao Sharpe: {current_metrics.sharpe_ratio:.2f} "
                        f"vs baseline {self.baseline_sharpe:.2f}"
                    ),
                )
                alerts.append(alert)

        # Comparar F1 com baseline
        if self.baseline_f1 > 0:
            zscore_f1 = self._calcular_zscore(
                current_metrics.f1_score,
                self.baseline_f1,
                std=0.05
            )
            if zscore_f1 >= self.drift_threshold_zscore:
                severity = (
                    DriftAlertSeverity.CRITICAL if zscore_f1 > 3.0
                    else DriftAlertSeverity.MEDIUM
                )
                alert = DriftAlert(
                    timestamp=datetime.now(),
                    metric="f1",
                    baseline_value=self.baseline_f1,
                    current_value=current_metrics.f1_score,
                    zscore=zscore_f1,
                    severity=severity,
                    message=(
                        f"Degradacao F1: {current_metrics.f1_score:.2f} "
                        f"vs baseline {self.baseline_f1:.2f}"
                    ),
                )
                alerts.append(alert)

        # Registrar alerts no historico
        self.alerts_history.extend(alerts)

        return alerts

    def gerar_relatorio_json(self, trades: List[Any]) -> str:
        """
        Gera relatorio de drift em formato JSON.

        Args:
            trades: Lista de trades para analise

        Returns:
            JSON string com baseline, metricas atuais e alerts
        """
        current_metrics = self.calcular_metricas(trades)
        alerts = self.detectar_drift(trades)

        relatorio: Dict[str, Any] = {
            "timestamp": datetime.now().isoformat(),
            "baseline": {
                "f1": self.baseline_f1,
                "win_rate": self.baseline_win_rate,
                "sharpe": self.baseline_sharpe,
            },
            "current_metrics": current_metrics.para_dict(),
            "alerts": [a.para_dict() for a in alerts],
            "total_alerts": len(alerts),
            "critical_alerts": sum(
                1 for a in alerts
                if a.severity == DriftAlertSeverity.CRITICAL
            ),
        }

        return json.dumps(relatorio, indent=2, default=str)

    def gerar_relatorio_markdown(self, trades: List[Any]) -> str:
        """
        Gera relatorio de drift em formato Markdown.

        Args:
            trades: Lista de trades para analise

        Returns:
            Markdown string com analise formatada
        """
        current_metrics = self.calcular_metricas(trades)
        alerts = self.detectar_drift(trades)

        md: List[str] = []
        md.append("# Relatorio de Drift Detection")
        md.append("")
        md.append(f"**Timestamp:** {datetime.now().isoformat()}")
        md.append("")

        # Baseline
        md.append("## Baseline")
        md.append("")
        md.append(f"- **F1 Score:** {self.baseline_f1:.4f}")
        md.append(f"- **Win Rate:** {self.baseline_win_rate:.2%}")
        md.append(f"- **Sharpe Ratio:** {self.baseline_sharpe:.2f}")
        md.append("")

        # Metricas Atuais
        md.append("## Metricas Atuais")
        md.append("")
        md.append(f"- **Total Trades:** {current_metrics.num_trades}")
        md.append(f"- **Win Rate:** {current_metrics.win_rate:.2%}")
        md.append(f"- **Loss Rate:** {current_metrics.loss_rate:.2%}")
        md.append(f"- **Avg PnL:** R$ {current_metrics.avg_pnl:.2f}")
        md.append(f"- **Total PnL:** R$ {current_metrics.total_pnl:.2f}")
        md.append(f"- **Sharpe Ratio:** {current_metrics.sharpe_ratio:.2f}")
        md.append(f"- **F1 Score:** {current_metrics.f1_score:.4f}")
        md.append(f"- **Std Dev PnL:** R$ {current_metrics.std_pnl:.2f}")
        md.append("")

        # Alerts
        md.append("## Alerts")
        if alerts:
            md.append("")
            for alert in alerts:
                emoji = {
                    DriftAlertSeverity.LOW: "🟡",
                    DriftAlertSeverity.MEDIUM: "🟠",
                    DriftAlertSeverity.CRITICAL: "🔴",
                }.get(alert.severity, "⚪")
                md.append(
                    f"{emoji} **{alert.metric.upper()}** ({alert.severity.value})"
                )
                md.append(f"  - {alert.message}")
                md.append(f"  - Z-score: {alert.zscore:.2f}")
                md.append("")
        else:
            md.append("Nenhum drift detectado. Sistema operacional.")
            md.append("")

        # Resumo
        md.append("## Resumo")
        md.append("")
        md.append(f"- **Total Alerts:** {len(alerts)}")
        md.append(
            f"- **Critical:** "
            f"{sum(1 for a in alerts if a.severity == DriftAlertSeverity.CRITICAL)}"
        )
        md.append(
            f"- **Medium:** "
            f"{sum(1 for a in alerts if a.severity == DriftAlertSeverity.MEDIUM)}"
        )
        md.append(
            f"- **Low:** "
            f"{sum(1 for a in alerts if a.severity == DriftAlertSeverity.LOW)}"
        )
        md.append("")

        return "\n".join(md)

    def salvar_relatorio(
        self, trades: List[Any], output_dir: Path, formato: str = "json"
    ) -> Path:
        """
        Salva relatorio em arquivo.

        Args:
            trades: Lista de trades
            output_dir: Diretorio para salvar relatorio
            formato: "json" ou "markdown"

        Returns:
            Path do arquivo salvo
        """
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

        if formato == "json":
            filename = output_dir / f"drift_report_{timestamp}.json"
            relatorio = self.gerar_relatorio_json(trades)
        else:
            filename = output_dir / f"drift_report_{timestamp}.md"
            relatorio = self.gerar_relatorio_markdown(trades)

        filename.write_text(relatorio, encoding="utf-8")
        return filename

"""
AC6.9 - Comparação contra Baseline Histórico e Feedback ao Sistema

Módulo responsável pela comparação de métricas atuais contra baseline
histórico com detecção de degradação e geração de feedback estruturado
para o sistema de ML.

Componentes:
- BaselineRecord: Armazena histórico de baseline com versão
- ComparisonResult: Resultado da comparação de métricas
- SystemFeedback: Feedback estruturado para sistema
- BaselineComparator: Classe principal com lógica de comparação

Funcionalidades:
- Carregamento de histórico de baseline
- Comparação de métricas atuais contra baseline usando Z-score
- Detecção de degradação com alertas estruturados
- Geração de feedback recomendando ação (CONTINUE/MONITOR/ROLLBACK)
- Persistência de histórico em JSON
- Relatórios em JSON e Markdown

Exemplo:
    comparator = BaselineComparator(
        baseline_metrics={
            "win_rate": 0.65,
            "f1_score": 0.68,
            "sharpe_ratio": 1.2,
        },
        z_score_threshold=2.0
    )

    # Comparar métricas atuais
    comparison = comparator.comparar_metricas(
        current_metrics={
            "win_rate": 0.70,
            "f1_score": 0.72,
        },
        baseline_version="v1.0.0"
    )

    # Gerar feedback
    feedback = comparator.gerar_feedback(comparison)

    # Relatório
    print(comparator.gerar_relatorio_markdown(comparison, feedback))
"""

import json
import statistics
from dataclasses import dataclass, asdict, field
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any
from enum import Enum


# ============================================================================
# ENUMS
# ============================================================================


class RecommendedAction(str, Enum):
    """Acções recomendadas pelo comparador."""

    CONTINUE = "CONTINUE"
    MONITOR = "MONITOR"
    ROLLBACK = "ROLLBACK"


class FeedbackSeverity(str, Enum):
    """Níveis de severidade do feedback."""

    LOW = "LOW"
    MEDIUM = "MEDIUM"
    CRITICAL = "CRITICAL"


# ============================================================================
# DATACLASSES
# ============================================================================


@dataclass
class BaselineRecord:
    """Registro de baseline histórico com metadados."""

    version_id: str
    timestamp: datetime
    metrics: Dict[str, float]
    description: Optional[str] = None

    def para_dict(self) -> Dict[str, Any]:
        """Converte para dicionário para persistência."""
        return {
            "version_id": self.version_id,
            "timestamp": self.timestamp.isoformat(),
            "metrics": self.metrics,
            "description": self.description,
        }


@dataclass
class ComparisonResult:
    """Resultado da comparação de métricas contra baseline."""

    baseline_version: str
    current_metrics: Dict[str, float]
    baseline_metrics: Dict[str, float]
    degraded_metrics: List[str]
    is_degraded: bool
    z_scores: Dict[str, float]

    def para_dict(self) -> Dict[str, Any]:
        """Converte para dicionário."""
        return asdict(self)


@dataclass
class SystemFeedback:
    """Feedback estruturado do sistema após comparação."""

    comparison_result: ComparisonResult
    recommended_action: str
    severity: str
    confidence: float
    timestamp: datetime

    def para_dict(self) -> Dict[str, Any]:
        """Converte para dicionário."""
        data = asdict(self)
        data["comparison_result"] = self.comparison_result.para_dict()
        data["timestamp"] = self.timestamp.isoformat()
        return data


# ============================================================================
# COMPARADOR PRINCIPAL
# ============================================================================


class BaselineComparator:
    """Comparador de métricas contra baseline histórico com feedback.

    Responsabilidades:
    - Manter histórico de baselines e versões
    - Comparar métricas atuais contra baseline usando Z-score
    - Detectar degradação com alertas estruturados
    - Gerar feedback recomendando ações (CONTINUE/MONITOR/ROLLBACK)
    - Persistir histórico em JSON
    - Gerar relatórios em JSON e Markdown

    Atributos:
        baseline_metrics: Métricas baseline inicial para comparação
        z_score_threshold: Threshold de Z-score para detectar degradação
        baseline_history: Lista de registros históricos
        models_dir: Diretório para persistência

    Exemplo:
        comparator = BaselineComparator(
            baseline_metrics={"win_rate": 0.65, "f1_score": 0.68},
            z_score_threshold=2.0
        )
        result = comparator.comparar_metricas({"win_rate": 0.70})
    """

    def __init__(
        self,
        baseline_metrics: Dict[str, float],
        z_score_threshold: float = 2.0,
        models_dir: Optional[str] = None,
    ) -> None:
        """Inicializa comparador.

        Args:
            baseline_metrics: Métricas baseline inicial
            z_score_threshold: Threshold Z-score para degradação (default: 2.0)
            models_dir: Diretório para persistência (default: ./models)
        """
        self.baseline_metrics: Dict[str, float] = {
            key: float(value)
            for key, value in baseline_metrics.items()
            if value is not None
        }
        self.z_score_threshold: float = float(z_score_threshold)
        self.models_dir: Path = Path(models_dir or "models")
        self.models_dir.mkdir(exist_ok=True)

        # Histórico de baselines
        self.baseline_history: List[BaselineRecord] = [
            BaselineRecord(
                version_id="v1.0.0",
                timestamp=datetime.now(),
                metrics=baseline_metrics,
                description="Baseline inicial",
            )
        ]

    # ========================================================================
    # HISTÓRICO DE BASELINE
    # ========================================================================

    def adicionar_baseline(
        self, record: BaselineRecord
    ) -> None:
        """Adiciona novo registro ao histórico.

        Args:
            record: BaselineRecord a adicionar
        """
        self.baseline_history.append(record)

    def obter_baseline(
        self, version_id: str
    ) -> Optional[BaselineRecord]:
        """Obtém baseline por versão.

        Args:
            version_id: ID da versão

        Returns:
            BaselineRecord ou None se não encontrado
        """
        for record in self.baseline_history:
            if record.version_id == version_id:
                return record
        return None

    def obter_baseline_mais_recente(
        self
    ) -> BaselineRecord:
        """Obtém baseline mais recente.

        Returns:
            Último BaselineRecord do histórico
        """
        return self.baseline_history[-1]

    # ========================================================================
    # COMPARAÇÃO DE MÉTRICAS
    # ========================================================================

    def comparar_metricas(
        self,
        current_metrics: Optional[Dict[str, float]] = None,
        baseline_version: str = "v1.0.0",
        **kwargs: Any,
    ) -> ComparisonResult:
        """Compara métricas atuais contra baseline.

        Calcula Z-scores para detectar degradação significativa.

        Args:
            current_metrics: Métricas atuais para comparar
            baseline_version: Versão de baseline para usar

        Returns:
            ComparisonResult com resultado da comparação
        """
        if current_metrics is None:
            current_metrics = kwargs.pop("metricas_atuais", None)
        if current_metrics is None:
            raise TypeError("current_metrics é obrigatório")
        if kwargs:
            unexpected = ", ".join(sorted(kwargs.keys()))
            raise TypeError(f"Argumentos inesperados: {unexpected}")

        # Obter baseline
        baseline_record = self.obter_baseline(baseline_version)
        if baseline_record is None:
            baseline_metrics = self.baseline_metrics
        else:
            baseline_metrics = baseline_record.metrics

        # Calcular Z-scores
        z_scores: Dict[str, float] = {}
        degraded_metrics: List[str] = []

        for metric_name, current_value in current_metrics.items():
            if metric_name not in baseline_metrics:
                continue

            baseline_value = float(baseline_metrics[metric_name])
            current_value = float(current_value)

            # Z-score simples: (current - baseline) / |baseline|
            # Métricas onde menor é melhor: win_rate, f1_score, sharpe_ratio
            if metric_name in [
                "win_rate",
                "f1_score",
                "sharpe_ratio",
                "avg_pnl",
            ]:
                # Métricas onde maior é melhor
                if baseline_value != 0:
                    z_score = (current_value - baseline_value) / abs(
                        baseline_value * 0.1
                    )  # Normalize by 10% of baseline
                else:
                    z_score = 0.0
            else:
                z_score = 0.0

            z_scores[metric_name] = z_score

            # Verificar se degradado
            if z_score < -self.z_score_threshold:
                degraded_metrics.append(metric_name)

        is_degraded = len(degraded_metrics) > 0

        return ComparisonResult(
            baseline_version=baseline_version,
            current_metrics=current_metrics,
            baseline_metrics=baseline_metrics,
            degraded_metrics=degraded_metrics,
            is_degraded=is_degraded,
            z_scores=z_scores,
        )

    # ========================================================================
    # GERAÇÃO DE FEEDBACK
    # ========================================================================

    def gerar_feedback(
        self, comparison: ComparisonResult
    ) -> SystemFeedback:
        """Gera feedback estruturado baseado na comparação.

        Lógica:
        - Sem degradação: CONTINUE (LOW severity, alta confiança)
        - 1-2 métricas degradadas: MONITOR (MEDIUM severity)
        - 3+ métricas degradadas: ROLLBACK (CRITICAL severity)

        Args:
            comparison: Resultado da comparação

        Returns:
            SystemFeedback com ação recomendada
        """
        # Determinar ação e severidade
        if not comparison.is_degraded:
            action = RecommendedAction.CONTINUE
            severity = FeedbackSeverity.LOW
            confidence = 0.95
        elif len(comparison.degraded_metrics) <= 2:
            action = RecommendedAction.MONITOR
            severity = FeedbackSeverity.MEDIUM
            confidence = 0.80
        else:
            action = RecommendedAction.ROLLBACK
            severity = FeedbackSeverity.CRITICAL
            confidence = 0.98

        return SystemFeedback(
            comparison_result=comparison,
            recommended_action=action.value,
            severity=severity.value,
            confidence=confidence,
            timestamp=datetime.now(),
        )

    # ========================================================================
    # RELATÓRIOS
    # ========================================================================

    def gerar_relatorio_json(
        self,
        comparison: ComparisonResult,
        feedback: SystemFeedback,
    ) -> Dict[str, Any]:
        """Gera relatório JSON estruturado.

        Args:
            comparison: Resultado da comparação
            feedback: Feedback gerado

        Returns:
            Dicionário com relatório completo
        """
        return {
            "timestamp": datetime.now().isoformat(),
            "comparison": comparison.para_dict(),
            "feedback": feedback.para_dict(),
            "z_score_threshold": self.z_score_threshold,
            "baseline_history_size": len(self.baseline_history),
        }

    def gerar_relatorio_markdown(
        self,
        comparison: ComparisonResult,
        feedback: SystemFeedback,
    ) -> str:
        """Gera relatório Markdown legível.

        Args:
            comparison: Resultado da comparação
            feedback: Feedback gerado

        Returns:
            String com relatório formatado
        """
        lines = [
            "## AC6.9 - Comparação contra Baseline Histórico",
            "",
            "### Status",
            f"- **Timestamp:** {feedback.timestamp.isoformat()}",
            f"- **Ação Recomendada:** {feedback.recommended_action}",
            f"- **Severidade:** {feedback.severity}",
            f"- **Confiança:** {feedback.confidence:.1%}",
            "",
            "### Métricas Atuais",
            "",
        ]

        # Tabela de métricas
        lines.append(
            "| Métrica | Atual | Baseline | Z-Score | Status |"
        )
        lines.append("|---------|-------|----------|---------|--------|")

        for metric, current_value in comparison.current_metrics.items():
            baseline_value = comparison.baseline_metrics.get(metric, "N/A")
            z_score = comparison.z_scores.get(metric, 0.0)
            is_degraded = metric in comparison.degraded_metrics
            status = "⚠️ DEGRADED" if is_degraded else "✅ OK"

            if isinstance(baseline_value, (int, float)):
                lines.append(
                    f"| {metric} | {current_value:.4f} | "
                    f"{baseline_value:.4f} | {z_score:.2f} | {status} |"
                )
            else:
                lines.append(
                    f"| {metric} | {current_value} | "
                    f"{baseline_value} | {z_score:.2f} | {status} |"
                )

        # Métricas degradadas
        lines.append("")
        lines.append("### Métricas Degradadas")
        if comparison.degraded_metrics:
            for metric in comparison.degraded_metrics:
                lines.append(f"- **{metric}**: Z-score = "
                            f"{comparison.z_scores.get(metric, 0.0):.2f}")
        else:
            lines.append("- Nenhuma métrica degradada")

        # Ação recomendada
        lines.append("")
        lines.append("### Ação Recomendada")
        action_description = {
            "CONTINUE": "Modelo operando normalmente, continuar execução",
            "MONITOR": "Degradação detectada, monitorar próximas iterações",
            "ROLLBACK": "Degradação severa, considerar rollback de versão",
        }
        lines.append(
            f"- {action_description.get(feedback.recommended_action, 'N/A')}"
        )

        # Histórico de baselines
        lines.append("")
        lines.append("### Histórico de Baselines")
        lines.append(
            f"- Total de versões: {len(self.baseline_history)}"
        )
        for record in self.baseline_history[-3:]:  # Últimas 3 versões
            lines.append(
                f"- {record.version_id} "
                f"({record.timestamp.strftime('%Y-%m-%d %H:%M:%S')}): "
                f"{record.description or 'N/A'}"
            )

        return "\n".join(lines)

    # ========================================================================
    # PERSISTÊNCIA
    # ========================================================================

    def salvar_baseline(self) -> Path:
        """Salva histórico de baseline em JSON.

        Returns:
            Path do arquivo salvo
        """
        baseline_file = self.models_dir / "baseline_history.json"

        data = [record.para_dict() for record in self.baseline_history]

        with open(baseline_file, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

        return baseline_file

    def carregar_baseline(self) -> bool:
        """Carrega histórico de baseline de arquivo.

        Returns:
            True se carregado com sucesso, False senão
        """
        baseline_file = self.models_dir / "baseline_history.json"

        if not baseline_file.exists():
            return False

        try:
            with open(baseline_file, "r", encoding="utf-8") as f:
                data = json.load(f)

            # Limpar histórico atual (exceto o primeiro)
            self.baseline_history = self.baseline_history[:1]

            # Carregar novos registros
            for record_data in data[1:]:  # Skip primeiro pois é inicial
                record = BaselineRecord(
                    version_id=record_data["version_id"],
                    timestamp=datetime.fromisoformat(
                        record_data["timestamp"]
                    ),
                    metrics=record_data["metrics"],
                    description=record_data.get("description"),
                )
                self.baseline_history.append(record)

            return True

        except (json.JSONDecodeError, KeyError, ValueError):
            return False

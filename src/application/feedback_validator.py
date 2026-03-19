"""
AC5.9: Feedback Validator

Módulo para validação de feedback entre trades executados e dados de
aprendizado para ML/RL.

O validador garante que:
1. Cada trade tem feedback correspondente (Correlação)
2. Tipos de outcome são válidos (OutcomeType)
3. Valores de PnL são consistentes
4. Sistema está saudável (Healthcheck)

Status: Implementacao v1.0 (19/03/2026)
Referencia: docs/BACKLOG.md (AC5.9)
"""

from dataclasses import dataclass, field, asdict
from datetime import datetime
from typing import Optional, List, Dict, Any
from enum import Enum
import logging
import json


# ═══════════════════════════════════════════════════════════════════════════
# ENUMS & VALUE OBJECTS
# ═══════════════════════════════════════════════════════════════════════════

class OutcomeType(Enum):
    """Tipos válidos de outcome de trade."""

    CLOSED = "CLOSED"              # Trade fechado com sucesso
    PARTIAL = "PARTIAL"            # Fechamento parcial
    REJECTED = "REJECTED"          # Rejeitado pela broker
    ABANDONED = "ABANDONED"        # Abandonado (timeout, etc)


@dataclass(frozen=True)
class FeedbackRecord:
    """
    Value Object: Record de feedback para trade.

    Imutável, garantia de integridade de dados.
    """

    trade_id: str
    outcome_type: OutcomeType
    pnl_actual: float
    pnl_expected: float
    timestamp: datetime

    def __post_init__(self) -> None:
        """Validação de invariantes."""
        if self.pnl_actual is None:
            raise ValueError("PnL actual não pode ser None")
        if self.pnl_expected is None:
            raise ValueError("PnL expected não pode ser None")


@dataclass
class FeedbackValidationResult:
    """
    Resultado de uma validação individual de feedback.

    Contém status, scores, erros e warnings.
    """

    is_valid: bool
    total_trades: int
    total_feedback: int
    correlation_rate: float  # 0.0 a 1.0
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())
    metadata: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        """Validar campos após inicialização."""
        if not 0.0 <= self.correlation_rate <= 1.0:
            raise ValueError("correlation_rate deve estar entre 0.0 e 1.0")

    def to_dict(self) -> Dict[str, Any]:
        """Converter para dicionário."""
        return {
            "is_valid": self.is_valid,
            "total_trades": self.total_trades,
            "total_feedback": self.total_feedback,
            "correlation_rate": self.correlation_rate,
            "error_count": len(self.errors),
            "warning_count": len(self.warnings),
            "timestamp": self.timestamp,
            "errors": self.errors[:5] if self.errors else [],
            "warnings": self.warnings[:5] if self.warnings else []
        }

    def to_json(self) -> str:
        """Serializar para JSON."""
        return json.dumps(self.to_dict(), indent=2, ensure_ascii=False)


@dataclass
class FeedbackHealthReport:
    """
    Relatório completo de saúde do sistema de feedback.

    Usado para decisões operacionais e monitoramento.
    """

    overall_status: str  # "HEALTHY", "WARNING", "CRITICAL"
    validation_timestamp: str
    correlation_rate: float
    data_quality_score: float  # 0.0 a 1.0
    missing_outcomes: int
    invalid_types: int
    valid_outcomes: int = 0
    total_trades: int = 0
    recommendations: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        """Validar campos após inicialização."""
        if self.overall_status not in ["HEALTHY", "WARNING", "CRITICAL"]:
            raise ValueError("overall_status deve ser HEALTHY, WARNING ou CRITICAL")
        if not 0.0 <= self.correlation_rate <= 1.0:
            raise ValueError("correlation_rate deve estar entre 0.0 e 1.0")

    def to_dict(self) -> Dict[str, Any]:
        """Converter para dicionário."""
        return {
            "overall_status": self.overall_status,
            "validation_timestamp": self.validation_timestamp,
            "correlation_rate": self.correlation_rate,
            "data_quality_score": self.data_quality_score,
            "missing_outcomes": self.missing_outcomes,
            "invalid_types": self.invalid_types,
            "valid_outcomes": self.valid_outcomes,
            "total_trades": self.total_trades,
            "recommendation_count": len(self.recommendations),
            "recommendations": self.recommendations[:3]
        }

    def to_json(self) -> str:
        """Serializar para JSON."""
        return json.dumps(self.to_dict(), indent=2, ensure_ascii=False)

    def to_markdown(self) -> str:
        """
        Serializar para Markdown legível.

        Formato: Headers, tabelas, bullet points.
        """
        lines = [
            f"# 📊 Feedback System Health Report",
            f"",
            f"**Status:** {self.overall_status}",
            f"**Timestamp:** {self.validation_timestamp}",
            f"",
            f"## Métricas",
            f"",
            f"| Métrica | Valor |",
            f"|---------|-------|",
            f"| Correlation Rate | {self.correlation_rate:.1%} |",
            f"| Data Quality | {self.data_quality_score:.1%} |",
            f"| Valid Outcomes | {self.valid_outcomes}/{self.total_trades} |",
            f"| Missing Feedback | {self.missing_outcomes} |",
            f"| Invalid Types | {self.invalid_types} |",
            f"",
        ]

        if self.recommendations:
            lines.extend([
                f"## 💡 Recomendações",
                f"",
            ])
            for i, rec in enumerate(self.recommendations[:5], 1):
                lines.append(f"{i}. {rec}")
            lines.append("")

        return "\n".join(lines)


# ═══════════════════════════════════════════════════════════════════════════
# FEEDBACK VALIDATOR SERVICE
# ═══════════════════════════════════════════════════════════════════════════

class FeedbackValidator:
    """
    Serviço para validação de feedback de trades.

    Responsabilidades:
    - Validar correlação trade ↔ feedback
    - Verificar tipos de outcome válidos
    - Validar consistência de PnL
    - Gerar relatório de saúde

    AC Coverage:
    - AC5.9.1 a AC5.9.15 (ver test_ac5_9_feedback_validator.py)
    """

    def __init__(
        self,
        correlation_threshold: float = 0.8,
        pnl_tolerance_percent: float = 5.0,
        logger: Optional[logging.Logger] = None
    ) -> None:
        """
        Inicializa validador.

        Args:
            correlation_threshold: Min correlation rate para HEALTHY (default 80%)
            pnl_tolerance_percent: Tolerância de PnL em % (default 5%)
            logger: Logger customizado (default cria novo)
        """
        self.correlation_threshold = correlation_threshold
        self.pnl_tolerance_percent = pnl_tolerance_percent
        self.logger = logger or logging.getLogger(__name__)
        self._validation_cache: Dict[str, FeedbackValidationResult] = {}

    def validar_correlacao(
        self,
        trades: List[Dict[str, Any]],
        feedbacks: List[Dict[str, Any]]
    ) -> FeedbackValidationResult:
        """
        Valida correlação entre trades e feedbacks.

        Args:
            trades: Lista de trades executados
            feedbacks: Lista de feedbacks correspondentes

        Returns:
            FeedbackValidationResult com correlation_rate e status

        AC5.9.1, AC5.9.11, AC5.9.12
        """
        # VALIDAÇÃO SE não há dados
        if not trades:
            return FeedbackValidationResult(
                is_valid=True,
                total_trades=0,
                total_feedback=0,
                correlation_rate=1.0,
                warnings=["Nenhum trade para validar"]
            )

        # Coletar IDs únicos
        trade_ids = set(t.get("trade_id") for t in trades if t.get("trade_id"))
        feedback_ids_raw = [f.get("trade_id") for f in feedbacks if f.get("trade_id")]
        feedback_ids = set(feedback_ids_raw)

        # Detectar duplicatas em feedback
        from collections import Counter
        feedback_duplicates = [tid for tid, count in Counter(feedback_ids_raw).items() if count > 1]

        # Calcular correlação
        if len(trade_ids) == 0:
            correlation_rate = 0.0
        else:
            correlation_rate = len(feedback_ids & trade_ids) / len(trade_ids)

        # Detectar discrepâncias
        missing = trade_ids - feedback_ids
        extra = feedback_ids - trade_ids
        errors: List[str] = []
        warnings: List[str] = []

        if missing:
            warnings.append(f"{len(missing)} trades sem feedback")
        if extra:
            warnings.append(f"{len(extra)} feedbacks sem trade correspondente")
        if feedback_duplicates:
            warnings.append(f"{len(feedback_duplicates)} feedbacks duplicados detectados")

        # Criar resultado
        result = FeedbackValidationResult(
            is_valid=correlation_rate >= self.correlation_threshold,
            total_trades=len(trade_ids),
            total_feedback=len(feedback_ids),
            correlation_rate=correlation_rate,
            errors=errors,
            warnings=warnings
        )

        self.logger.debug(f"Correlação validada: {correlation_rate:.1%}")
        return result

    def validar_tipos_outcome(
        self,
        feedback: Dict[str, Any]
    ) -> FeedbackValidationResult:
        """
        Valida tipos de outcome válidos.

        Args:
            feedback: Record de feedback

        Returns:
            FeedbackValidationResult com status de validação

        AC5.9.3, AC5.9.4
        """
        # Extrair tipo
        outcome_type = feedback.get("outcome_type")

        # Validar
        valid_types = {"CLOSED", "PARTIAL", "REJECTED", "ABANDONED"}
        errors = []

        if outcome_type not in valid_types:
            errors.append(f"Tipo inválido: {outcome_type}. Válidos: {valid_types}")

        result = FeedbackValidationResult(
            is_valid=len(errors) == 0,
            total_trades=1,
            total_feedback=1 if len(errors) == 0 else 0,
            correlation_rate=1.0 if len(errors) == 0 else 0.0,
            errors=errors
        )

        return result

    def validar_consistencia_pnl(
        self,
        feedback: Dict[str, Any]
    ) -> FeedbackValidationResult:
        """
        Valida consistência entre PnL atual e esperado.

        Args:
            feedback: Record de feedback

        Returns:
            FeedbackValidationResult com status de consistência

        AC5.9.5, AC5.9.6
        """
        pnl_actual = feedback.get("pnl_actual")
        pnl_expected = feedback.get("pnl_expected")

        warnings = []
        errors = []

        # Verificar se valores existem
        if pnl_actual is None or pnl_expected is None:
            errors.append("PnL actual ou expected é None")
        else:
            # Calcular divergência percentual
            if pnl_expected != 0:
                divergence_percent = abs(pnl_actual - pnl_expected) / abs(pnl_expected) * 100
            else:
                divergence_percent = 0 if pnl_actual == 0 else 100

            # Verificar tolerância
            if divergence_percent > self.pnl_tolerance_percent:
                warnings.append(f"PnL diverge {divergence_percent:.1f}% (tolerância: {self.pnl_tolerance_percent}%)")

        result = FeedbackValidationResult(
            is_valid=len(errors) == 0,
            total_trades=1,
            total_feedback=1 if len(errors) == 0 else 0,
            correlation_rate=1.0 if len(errors) == 0 else 0.0,
            errors=errors,
            warnings=warnings
        )

        return result

    def gerar_healthcheck(
        self,
        trades: List[Dict[str, Any]],
        feedbacks: List[Dict[str, Any]]
    ) -> FeedbackHealthReport:
        """
        Gera relatório de saúde do sistema de feedback.

        Args:
            trades: Lista de trades
            feedbacks: Lista de feedbacks

        Returns:
            FeedbackHealthReport com status geral e recomendações

        AC5.9.7, AC5.9.8
        """
        # Validar correlação
        corr_result = self.validar_correlacao(trades, feedbacks)

        # Validar tipos
        valid_count = 0
        invalid_types = 0
        for feedback in feedbacks:
            type_result = self.validar_tipos_outcome(feedback)
            if type_result.is_valid:
                valid_count += 1
            else:
                invalid_types += 1

        # Calcular scores
        correlation_rate = corr_result.correlation_rate
        type_validity = valid_count / len(feedbacks) if feedbacks else 1.0
        data_quality_score = (correlation_rate + type_validity) / 2

        # Determinar status
        if data_quality_score >= 0.9 and correlation_rate >= 0.95:
            status = "HEALTHY"
        elif data_quality_score >= 0.7:
            status = "WARNING"
        else:
            status = "CRITICAL"

        # Gerar recomendações
        recommendations = []
        if len(corr_result.warnings) > 0:
            recommendations.extend(corr_result.warnings)
        if invalid_types > 0:
            recommendations.append(f"Corrigir {invalid_types} tipos de outcome inválidos")

        report = FeedbackHealthReport(
            overall_status=status,
            validation_timestamp=datetime.now().isoformat(),
            correlation_rate=correlation_rate,
            data_quality_score=data_quality_score,
            missing_outcomes=len(trades) - len(feedbacks),
            invalid_types=invalid_types,
            valid_outcomes=valid_count,
            total_trades=len(trades),
            recommendations=recommendations[:5]
        )

        self.logger.info(f"Healthcheck: {status}, correlation={correlation_rate:.1%}")
        return report


# ═══════════════════════════════════════════════════════════════════════════
# HELPERS & UTILITIES
# ═══════════════════════════════════════════════════════════════════════════

def calcular_pnl_divergencia(
    pnl_actual: float,
    pnl_expected: float,
    tolerance_percent: float = 5.0
) -> Dict[str, Any]:
    """
    Calcula divergência de PnL.

    Args:
        pnl_actual: PnL real executado
        pnl_expected: PnL esperado
        tolerance_percent: Tolerância em %

    Returns:
        Dict com divergence, valid, details
    """
    if pnl_expected == 0:
        divergence_percent: float = 0.0 if pnl_actual == 0 else 100.0
    else:
        divergence_percent = abs(pnl_actual - pnl_expected) / abs(pnl_expected) * 100

    is_valid = divergence_percent <= tolerance_percent

    return {
        "divergence_percent": divergence_percent,
        "is_valid": is_valid,
        "pnl_actual": pnl_actual,
        "pnl_expected": pnl_expected,
        "tolerance_percent": tolerance_percent
    }

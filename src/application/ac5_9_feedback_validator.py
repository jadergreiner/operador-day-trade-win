"""
AC5.9: Validador de Feedback de Execucao

Componente que valida a saude do sistema de feedback entre trades executadas
e dados de aprendizado para ML/RL.

Validacoes:
1. Correlacao: Trade <-> Feedback (qual % de trades tem feedback?)
2. Tipos de Outcome: Valida tipos (WIN/LOSS/BREAKEVEN)
3. Consistencia PnL: Outcome compativel com valor de PnL
4. Healthcheck Geral: Relatorio de saude do sistema

Relatorios:
- JSON: Estruturado para processamento automatico
- Markdown: Legivel para analise manual

Exemplo de uso:
    validator = FeedbackValidator()
    trades = obter_trades_do_banco()
    feedback = obter_feedback_do_banco()
    report = validator.validate_feedback_health(trades, feedback)
    print(report.to_markdown())
"""

from dataclasses import dataclass, field, asdict
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any
import json
import logging

logger = logging.getLogger(__name__)


@dataclass
class FeedbackValidationResult:
    """Resultado de uma validacao individual de feedback."""

    is_valid: bool
    total_trades: int
    total_feedback: int
    correlation_rate: float  # 0.0 a 1.0
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())
    metadata: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        """Validar campos após inicializacao."""
        if not 0.0 <= self.correlation_rate <= 1.0:
            raise ValueError("correlation_rate deve estar entre 0.0 e 1.0")

    def to_dict(self) -> Dict[str, Any]:
        """Converter para dicionario."""
        return asdict(self)

    def to_json(self) -> str:
        """Serializar para JSON."""
        return json.dumps(self.to_dict(), indent=2, ensure_ascii=False)


@dataclass
class FeedbackHealthReport:
    """Relatorio completo de saude do sistema de feedback."""

    overall_status: str  # "HEALTHY", "WARNING", "CRITICAL"
    validation_timestamp: str
    correlation_rate: float
    data_quality_score: float  # 0.0 a 1.0
    missing_outcomes: int
    invalid_types: int
    recommendations: List[str] = field(default_factory=list)
    valid_outcomes: int = 0
    total_trades: int = 0
    metadata: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        """Validar campos apos inicializacao."""
        if self.overall_status not in ["HEALTHY", "WARNING", "CRITICAL"]:
            raise ValueError(
                'overall_status deve ser "HEALTHY", "WARNING" ou "CRITICAL"'
            )
        if not 0.0 <= self.correlation_rate <= 1.0:
            raise ValueError("correlation_rate deve estar entre 0.0 e 1.0")
        if not 0.0 <= self.data_quality_score <= 1.0:
            raise ValueError("data_quality_score deve estar entre 0.0 e 1.0")

    def to_dict(self) -> Dict[str, Any]:
        """Converter para dicionario."""
        return asdict(self)

    def to_json(self) -> str:
        """Serializar para JSON com formatacao legivel."""
        data = self.to_dict()
        return json.dumps(data, indent=2, ensure_ascii=False)

    def to_markdown(self) -> str:
        """Gerar relatorio em Markdown para leitura manual."""
        status_emoji = {
            "HEALTHY": "✅",
            "WARNING": "⚠️",
            "CRITICAL": "🔴",
        }
        emoji = status_emoji.get(self.overall_status, "❓")

        md_lines: List[str] = [
            "# Relatorio de Saude de Feedback AC5.9",
            "",
            f"## Status Geral: {emoji} {self.overall_status}",
            "",
            "### Metricas Principais",
            f"- **Taxa de Correlacao:** {self.correlation_rate*100:.1f}%",
            f"- **Score de Qualidade:** {self.data_quality_score*100:.1f}%",
            f"- **Trades Totais:** {self.total_trades}",
            f"- **Outcomes Validos:** {self.valid_outcomes}",
            "",
            "### Problemas Detectados",
            f"- **Outcomes Faltantes:** {self.missing_outcomes}",
            f"- **Tipos Invalidos:** {self.invalid_types}",
            "",
            "### Recomendacoes",
        ]

        if self.recommendations:
            for rec in self.recommendations:
                md_lines.append(f"- {rec}")
        else:
            md_lines.append("- Nenhuma acao recomendada no momento.")

        md_lines.extend(
            [
                "",
                "### Timestamp da Validacao",
                f"- {self.validation_timestamp}",
            ]
        )

        return "\n".join(md_lines)


class FeedbackValidator:
    """
    Validador de feedback de execucao com multiplas verificacoes.

    Responsabilidades:
    - Validar correlacao entre trades e feedback
    - Verificar tipos de outcome (WIN/LOSS/BREAKEVEN)
    - Validar consistencia entre outcome_type e PnL
    - Gerar relatorio de saude do sistema
    """

    # Tipos de outcome aceitos
    VALID_OUTCOME_TYPES: Tuple[str, ...] = ("WIN", "LOSS", "BREAKEVEN")

    # Threshold para qualidade aceitavel
    HEALTHY_CORRELATION_THRESHOLD: float = 0.90
    HEALTHY_QUALITY_THRESHOLD: float = 0.80

    def validate_correlation(
        self, trades: List[Dict[str, Any]], feedback: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Validar correlacao entre trades e feedback.

        Retorna:
            Dict com:
            - correlation_rate: percentual de trades com feedback (0.0-1.0)
            - matched_trades: numero de trades correlacionados
            - total_trades: numero total de trades
            - unmatched_trade_ids: IDs de trades sem feedback
        """
        if not trades:
            return {
                "correlation_rate": 0.0,
                "matched_trades": 0,
                "total_trades": 0,
                "unmatched_trade_ids": [],
            }

        total_trades = len(trades)
        trade_ids = {t.get("trade_id") for t in trades}

        # Feedback associados a trades conhecidos
        feedback_trade_ids = {
            f.get("trade_id") for f in feedback if f.get("trade_id") in trade_ids
        }

        matched_trades = len(feedback_trade_ids)
        correlation_rate = matched_trades / total_trades if total_trades > 0 else 0.0

        # Trades faltantes
        unmatched = trade_ids - feedback_trade_ids

        return {
            "correlation_rate": correlation_rate,
            "matched_trades": matched_trades,
            "total_trades": total_trades,
            "unmatched_trade_ids": sorted(list(unmatched)),
        }

    def validate_outcome_types(
        self, feedback: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Validar tipos de outcome em feedback.

        Retorna:
            Dict com:
            - valid_outcomes: numero de outcomes validos
            - invalid_outcomes: numero de outcomes invalidos
            - validity_rate: percentual de validez (0.0-1.0)
            - invalid_entries: lista de entradas invalidas
        """
        if not feedback:
            return {
                "valid_outcomes": 0,
                "invalid_outcomes": 0,
                "validity_rate": 0.0,
                "invalid_entries": [],
            }

        valid_count = 0
        invalid_entries: List[Dict[str, Any]] = []

        for entry in feedback:
            outcome_type = entry.get("outcome_type")
            if outcome_type in self.VALID_OUTCOME_TYPES:
                valid_count += 1
            else:
                invalid_entries.append(
                    {
                        "feedback_id": entry.get("feedback_id"),
                        "outcome_type": outcome_type,
                        "reason": f"Tipo invalido: {outcome_type}",
                    }
                )

        total = len(feedback)
        invalid_count = total - valid_count
        validity_rate = valid_count / total if total > 0 else 0.0

        return {
            "valid_outcomes": valid_count,
            "invalid_outcomes": invalid_count,
            "validity_rate": validity_rate,
            "invalid_entries": invalid_entries,
        }

    def validate_pnl_consistency(
        self, feedback: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Validar consistencia entre outcome_type e PnL.

        Regras:
        - WIN: pnl > 0
        - LOSS: pnl < 0
        - BREAKEVEN: pnl == 0 (ou muito proximo)

        Retorna:
            Dict com:
            - consistent: numero de entradas consistentes
            - inconsistent: numero de entradas inconsistentes
            - inconsistencies: detalhes das inconsistencias
        """
        if not feedback:
            return {
                "consistent": 0,
                "inconsistent": 0,
                "inconsistencies": [],
            }

        consistent = 0
        inconsistencies: List[Dict[str, Any]] = []

        for entry in feedback:
            outcome_type = entry.get("outcome_type")
            pnl = entry.get("pnl", 0.0)

            is_consistent = False
            if outcome_type == "WIN" and pnl > 0:
                is_consistent = True
            elif outcome_type == "LOSS" and pnl < 0:
                is_consistent = True
            elif outcome_type == "BREAKEVEN" and abs(pnl) < 0.01:
                is_consistent = True

            if is_consistent:
                consistent += 1
            else:
                inconsistencies.append(
                    {
                        "feedback_id": entry.get("feedback_id"),
                        "outcome_type": outcome_type,
                        "pnl": pnl,
                        "reason": f"{outcome_type} inconsistente com PnL={pnl}",
                    }
                )

        total = len(feedback)
        inconsistent_count = total - consistent

        return {
            "consistent": consistent,
            "inconsistent": inconsistent_count,
            "inconsistencies": inconsistencies,
        }

    def validate_feedback_health(
        self, trades: List[Dict[str, Any]], feedback: List[Dict[str, Any]]
    ) -> FeedbackHealthReport:
        """
        Validacao geral de saude do sistema de feedback.

        Executa todas as validacoes e gera relatorio consolidado.

        Retorna:
            FeedbackHealthReport com status e recomendacoes
        """
        # Executar validacoes individuais
        correlation_result = self.validate_correlation(trades, feedback)
        outcome_types_result = self.validate_outcome_types(feedback)
        pnl_consistency_result = self.validate_pnl_consistency(feedback)

        # Calcular metrics compostas
        correlation_rate = correlation_result["correlation_rate"]
        validity_rate = outcome_types_result["validity_rate"]
        consistency_rate = (
            pnl_consistency_result["consistent"]
            / len(feedback)
            if feedback
            else 0.0
        )

        # Data quality = media das taxas
        data_quality_score = (
            (validity_rate + consistency_rate) / 2
            if feedback
            else 0.0
        )

        # Missing outcomes = trades sem feedback
        missing_outcomes = correlation_result.get(
            "total_trades", 0
        ) - correlation_result.get("matched_trades", 0)

        # Invalid types
        invalid_types = outcome_types_result.get("invalid_outcomes", 0)

        # Determinar status geral
        if (
            correlation_rate >= self.HEALTHY_CORRELATION_THRESHOLD
            and data_quality_score >= self.HEALTHY_QUALITY_THRESHOLD
        ):
            overall_status = "HEALTHY"
        elif correlation_rate >= 0.50 and data_quality_score >= 0.60:
            overall_status = "WARNING"
        else:
            overall_status = "CRITICAL"

        # Gerar recomendacoes
        recommendations: List[str] = []
        if missing_outcomes > 0:
            recommendations.append(
                f"Investigue {missing_outcomes} trades sem feedback associado."
            )
        if invalid_types > 0:
            recommendations.append(
                f"Corrija {invalid_types} registros com tipos de outcome invalidos."
            )
        if pnl_consistency_result["inconsistent"] > 0:
            recommendations.append(
                f"Revise {pnl_consistency_result['inconsistent']} entradas "
                "com inconsistencia PnL/outcome."
            )
        if correlation_rate < self.HEALTHY_CORRELATION_THRESHOLD:
            recommendations.append(
                "Aumente a cobertura de feedback: "
                f"atualmente {correlation_rate*100:.1f}%, "
                f"alvo >= {self.HEALTHY_CORRELATION_THRESHOLD*100:.0f}%."
            )

        # Montar relatorio
        report = FeedbackHealthReport(
            overall_status=overall_status,
            validation_timestamp=datetime.now().isoformat(),
            correlation_rate=correlation_rate,
            data_quality_score=data_quality_score,
            missing_outcomes=missing_outcomes,
            invalid_types=invalid_types,
            recommendations=recommendations,
            valid_outcomes=outcome_types_result.get("valid_outcomes", 0),
            total_trades=correlation_result.get("total_trades", 0),
            metadata={
                "correlation_result": correlation_result,
                "outcome_types_result": outcome_types_result,
                "pnl_consistency_result": pnl_consistency_result,
                "validity_rate": validity_rate,
                "consistency_rate": consistency_rate,
            },
        )

        return report

    def save_report_to_file(
        self, report: FeedbackHealthReport, output_dir: Optional[str] = None
    ) -> str:
        """
        Salvar relatorio em arquivo JSON.

        Args:
            report: FeedbackHealthReport para salvar
            output_dir: Diretorio de saida (padrao: data/backtest/)

        Retorna:
            Caminho do arquivo salvo
        """
        if output_dir is None:
            output_dir = "data/backtest"

        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filepath = output_path / f"ac5_9_feedback_health_{timestamp}.json"

        with open(filepath, "w", encoding="utf-8") as f:
            f.write(report.to_json())

        logger.info(f"Relatorio de feedback salvo em {filepath}")
        return str(filepath)

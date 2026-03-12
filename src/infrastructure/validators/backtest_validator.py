"""
Backtest Validator - Validação de critérios GATE 2.

Responsabilidades:
- Implementar 4 critérios bloqueadores (Sharpe, Win Rate, Drawdown, Consistency)
- Gerar decisão GO/NO-GO para escalar capital
- Produzir relatório de validação detalhado
"""

from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional

import json


class GateDecision(Enum):
    """Decisão de GATE 2."""

    PASS = "PASS"  # Todos critérios atendidos
    FAIL = "FAIL"  # Um ou mais critérios não atendidos


@dataclass
class GateCriteria:
    """Critérios bloqueadores do GATE 2."""

    sharpe_target: float = 1.0
    win_rate_target: float = 0.59
    max_drawdown_target: float = 0.15  # 15%
    consistency_sigma_target: float = 0.30


@dataclass
class ValidationResult:
    """Resultado da validação de um critério."""

    criterion: str
    target: float
    actual: float
    passed: bool
    message: str


class BacktestValidator:
    """Valida resultados de backtest contra GATE 2 criteria."""

    def __init__(self, criteria: Optional[GateCriteria] = None) -> None:
        """
        Inicializa validator.

        Args:
            criteria: Critérios GATE 2 (usa padrão se None)
        """
        self.criteria = criteria or GateCriteria()
        self.validation_results: List[ValidationResult] = []
        self.overall_decision = GateDecision.FAIL

    def load_results(self, results_path: str) -> Dict[str, Any]:
        """
        Carrega resultados de backtest.

        Args:
            results_path: Caminho do JSON com resultados

        Returns:
            Dict com summary + folds

        Raises:
            FileNotFoundError: Se arquivo não existe
            ValueError: Se estrutura inválida
        """
        path = Path(results_path)
        if not path.exists():
            raise FileNotFoundError(f"Results file não encontrado: {results_path}")

        with open(path, "r") as f:
            data = json.load(f)

        # Validar estrutura
        if "summary" not in data:
            raise ValueError("Results deve conter 'summary'")
        if "folds" not in data:
            raise ValueError("Results deve conter 'folds'")

        return data

    def _validate_sharpe_ratio(self, summary: Dict[str, Any]) -> ValidationResult:
        """
        Valida Sharpe Ratio.

        Critério: Sharpe ≥ 1.0
        Justificativa: Retorno ajustado ao risco (1% risco = 1% retorno mínimo)
        """
        actual_sharpe = summary.get("mean_sharpe", 0)
        passed = actual_sharpe >= self.criteria.sharpe_target

        return ValidationResult(
            criterion="Sharpe Ratio",
            target=self.criteria.sharpe_target,
            actual=actual_sharpe,
            passed=passed,
            message=(
                f"{'✓' if passed else '✗'} Sharpe ratio {actual_sharpe:.2f} "
                f"{'≥' if passed else '<'} {self.criteria.sharpe_target:.1f} (alvo)"
            ),
        )

    def _validate_win_rate(self, summary: Dict[str, Any]) -> ValidationResult:
        """
        Valida Win Rate.

        Critério: Win Rate ≥ 59%
        Justificativa: Mais ganhos que perdas (expectancy positivo)
        """
        actual_wr = summary.get("mean_win_rate", 0)
        passed = actual_wr >= self.criteria.win_rate_target

        return ValidationResult(
            criterion="Win Rate",
            target=self.criteria.win_rate_target,
            actual=actual_wr,
            passed=passed,
            message=(
                f"{'✓' if passed else '✗'} Taxa de acerto {actual_wr*100:.1f}% "
                f"{'≥' if passed else '<'} {self.criteria.win_rate_target*100:.0f}% (alvo)"
            ),
        )

    def _validate_max_drawdown(self, summary: Dict[str, Any]) -> ValidationResult:
        """
        Valida Max Drawdown.

        Critério: Max Drawdown < 15%
        Justificativa: Proteção de capital (perda máxima suportável)
        """
        actual_dd = summary.get("mean_max_drawdown", 0)
        passed = actual_dd < self.criteria.max_drawdown_target

        return ValidationResult(
            criterion="Max Drawdown",
            target=self.criteria.max_drawdown_target,
            actual=actual_dd,
            passed=passed,
            message=(
                f"{'✓' if passed else '✗'} Drawdown máximo {actual_dd*100:.1f}% "
                f"{'<' if passed else '≥'} {self.criteria.max_drawdown_target*100:.0f}% (alvo)"
            ),
        )

    def _validate_consistency(self, summary: Dict[str, Any]) -> ValidationResult:
        """
        Valida Consistência Mensal (sigma).

        Critério: σ (monthly returns) < 0.30
        Justificativa: Variação mês-a-mês (previsibilidade)
        """
        actual_consistency = summary.get(
            "consistency_std",
            summary.get("mean_monthly_consistency", float("inf"))
        )
        passed = actual_consistency < self.criteria.consistency_sigma_target

        return ValidationResult(
            criterion="Consistência Mensal (σ)",
            target=self.criteria.consistency_sigma_target,
            actual=actual_consistency,
            passed=passed,
            message=(
                f"{'✓' if passed else '✗'} Sigma mensal {actual_consistency:.2f} "
                f"{'<' if passed else '≥'} {self.criteria.consistency_sigma_target:.2f} (alvo)"
            ),
        )

    def validate(self, results_path: str) -> GateDecision:
        """
        Executa validação completa contra GATE 2 criteria.

        Args:
            results_path: Caminho do backtest_results.json

        Returns:
            GateDecision.PASS ou FAIL

        Raises:
            FileNotFoundError: Se arquivo não existe
            ValueError: Se estrutura inválida
        """
        results = self.load_results(results_path)
        summary = results.get("summary", {})

        # Validar cada critério
        self.validation_results = [
            self._validate_sharpe_ratio(summary),
            self._validate_win_rate(summary),
            self._validate_max_drawdown(summary),
            self._validate_consistency(summary),
        ]

        # Decisão: TODOS os critérios devem passar (AND logic)
        all_passed = all(vr.passed for vr in self.validation_results)
        self.overall_decision = GateDecision.PASS if all_passed else GateDecision.FAIL

        return self.overall_decision

    def get_validation_report(self) -> str:
        """
        Gera relatório detalhado de validação.

        Returns:
            String com relatório formatado
        """
        decision_symbol = "✓ PASS" if self.overall_decision == GateDecision.PASS else "✗ FAIL"
        report = f"""
╔══════════════════════════════════════════════════════════════════════╗
║                  GATE 2 VALIDATION REPORT - P0-2                    ║
║              Backtest Validação ML - Decisão de Capital              ║
╚══════════════════════════════════════════════════════════════════════╝

DECISION: {decision_symbol}
{'✓ Escalar para R$ 100k (FASE 2)' if self.overall_decision == GateDecision.PASS else '✗ Manter em R$ 50k (revalidar modelo)'}

CRITÉRIOS DE VALIDAÇÃO (Bloqueadores - AND Logic):
"""

        for vr in self.validation_results:
            status_symbol = "✓ PASS" if vr.passed else "✗ FAIL"
            report += f"""
{status_symbol} {vr.criterion}
   Alvo:   {vr.target}
   Real:   {vr.actual:.2f}
   {vr.message}
"""

        report += f"""
RECOMENDAÇÃO:
"""

        if self.overall_decision == GateDecision.PASS:
            report += """
   ✓ MODELO APROVADO para escalar capital
   ✓ Recomendação: Escalar de R$ 50k para R$ 100k (FASE 2)
   ✓ Próximo passo: Integração com MT5 + deployment em staging (07/03)
   ✓ Timeline Go-Live Beta: 13/03/2026
"""
        else:
            report += """
   ✗ MODELO NÃO APROVADO
   ✗ Aç ão: Revisar features / rebalancear hiperparâmetros ML
   ✗ Timeline: Novo backtest em 3-5 dias úteis
   ✗ Mantém em R$ 50k até validação passar
"""

        return report

    def get_decision_json(self) -> Dict[str, Any]:
        """
        Retorna decisão em formato JSON (para automação).

        Returns:
            Dict com decisão + critérios
        """
        return {
            "decision": self.overall_decision.value,
            "timestamp": str(Path.cwd()),
            "criteria": [
                {
                    "criterion": vr.criterion,
                    "target": vr.target,
                    "actual": float(vr.actual),
                    "passed": vr.passed,
                }
                for vr in self.validation_results
            ],
            "all_passed": all(vr.passed for vr in self.validation_results),
            "recommendation": (
                "Escalar para R$ 100k"
                if self.overall_decision == GateDecision.PASS
                else "Manter em R$ 50k"
            ),
        }

    def save_validation_report(
        self,
        results_path: str,
        output_dir: str,
        decision_output_dir: Optional[str] = None,
    ) -> str:
        """
        Salva relatório de validação em arquivo.

        Args:
            results_path: Caminho do backtest_results.json
            output_dir: Diretório para salvar relatório
            decision_output_dir: Diretório para salvar gate2_decision.json

        Returns:
            Caminho do arquivo gerado

        Raises:
            FileNotFoundError: Se arquivo de resultados não existe
        """
        # Executar validação
        self.validate(results_path)

        # Salvar relatório texto
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)

        report_file = output_path / "gate2_validation_report.txt"
        with open(report_file, "w", encoding="utf-8") as f:
            f.write(self.get_validation_report())

        # Salvar decisão JSON (padrão: mesmo diretório do relatório)
        decision_path = Path(decision_output_dir) if decision_output_dir else output_path
        decision_path.mkdir(parents=True, exist_ok=True)
        decision_file = decision_path / "gate2_decision.json"
        with open(decision_file, "w", encoding="utf-8") as f:
            json.dump(self.get_decision_json(), f, indent=2)

        return str(report_file)

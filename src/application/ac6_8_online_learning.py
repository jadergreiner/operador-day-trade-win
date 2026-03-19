"""
AC6.8 - Online Learning Controlado

Modulo responsavel por treino incremental de modelos ML com
ajuste de parametros durante operacao e rollback automatico.

Componentes:
- OnlineLearningController: Controlador principal
- ModelVersion: Armazena versao do modelo
- TrainingResult: Resultado de treino

Funcionalidades:
- Treino incremental por batch
- Validacao contra baseline
- Persistencia versionada
- Rollback automatico por degradacao

Exemplo:
    controller = OnlineLearningController(
        model_name="operador_trader",
        baseline_metrics={
            "win_rate": 0.65,
            "f1_score": 0.68,
            "sharpe_ratio": 1.2,
        }
    )

    # Treinar com novo batch
    result = controller.train_incremental(new_data)

    # Validar contra baseline
    validation = controller.validate_model(new_data)
    if not validation["is_valid"]:
        # Rollback se degradacao
        controller.rollback_on_degradation(
            new_batch=new_data,
            previous_version="v1.0.0",
        )

    # Salvar versao se valida
    version_id = controller.save_model_version(new_data)
"""

import json
import statistics
from dataclasses import dataclass, asdict, field
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple
from enum import Enum


# ============================================================================
# ENUMS E TIPOS
# ============================================================================


class OutcomeType(str, Enum):
    """Tipos de outcome de trade."""

    WIN = "WIN"
    LOSS = "LOSS"
    BREAKEVEN = "BREAKEVEN"


# ============================================================================
# DATACLASSES
# ============================================================================


@dataclass
class ModelVersion:
    """Versao armazenada de modelo com metadados."""

    version_id: str
    timestamp: datetime
    model_state: Dict[str, Any]
    metrics: Dict[str, float]
    training_samples: int
    baseline_metrics: Dict[str, float]
    description: Optional[str] = None

    def para_dict(self) -> Dict[str, Any]:
        """Converte para dicionario para persistencia."""
        return {
            "version_id": self.version_id,
            "timestamp": self.timestamp.isoformat(),
            "model_state": self.model_state,
            "metrics": self.metrics,
            "training_samples": self.training_samples,
            "baseline_metrics": self.baseline_metrics,
            "description": self.description,
        }


@dataclass
class TrainingResult:
    """Resultado de uma sessao de treino."""

    samples_trained: int
    model_metrics: Dict[str, float]
    duration_seconds: float
    timestamp: datetime
    batch_size: int

    def para_dict(self) -> Dict[str, Any]:
        """Converte para dicionario."""
        return asdict(self)


@dataclass
class ValidationResult:
    """Resultado de validacao de modelo."""

    is_valid: bool
    metrics: Dict[str, float]
    comparison: Dict[str, Dict[str, float]]
    passed_checks: int
    total_checks: int
    degradation_metrics: List[str] = field(default_factory=list)

    def para_dict(self) -> Dict[str, Any]:
        """Converte para dicionario."""
        return asdict(self)


@dataclass
class RollbackResult:
    """Resultado de operacao rollback."""

    degradation_detected: bool
    rollback_performed: bool
    degraded_metrics: List[str]
    restored_version: Optional[str]
    timestamp: datetime
    reason: str = ""

    def para_dict(self) -> Dict[str, Any]:
        """Converte para dicionario."""
        data = asdict(self)
        data["timestamp"] = data["timestamp"].isoformat()
        return data


# ============================================================================
# CONTROLADOR PRINCIPAL
# ============================================================================


class OnlineLearningController:
    """Controlador de treino incremental com validacao e rollback.

    Responsabilidades:
    - Treino incremental por batch de dados
    - Calculo de metricas (win_rate, F1, Sharpe, etc)
    - Validacao contra baseline com deteccao de degradacao
    - Persistencia versionada de modelos
    - Rollback automatico por degradacao

    Atributos:
        model_name: Nome do modelo
        baseline_metrics: Metricas baseline para comparacao
        models_dir: Diretorio para persistencia
        samples_trained: Numero de amostras treinadas

    Exemplo:
        controller = OnlineLearningController(
            model_name="trader",
            baseline_metrics={"win_rate": 0.65}
        )
        result = controller.train_incremental(data)
    """

    def __init__(
        self,
        model_name: str,
        baseline_metrics: Dict[str, float],
        models_dir: Optional[str] = None,
    ) -> None:
        """Inicializa controlador.

        Args:
            model_name: Nome identificador do modelo
            baseline_metrics: Metricas baseline para validacao
            models_dir: Diretorio para salvar versoes (default: ./models)
        """
        self.model_name: str = str(model_name)
        self.baseline_metrics: Dict[str, float] = {
            key: float(value)
            for key, value in baseline_metrics.items()
            if value is not None
        }
        self.models_dir: Path = Path(models_dir or "models")
        self.models_dir.mkdir(exist_ok=True)

        self.samples_trained: int = 0
        self.current_metrics: Dict[str, float] = {}
        self.model_state: Dict[str, Any] = {}
        self.training_history: List[TrainingResult] = []
        self.version_counter: int = 0

    # ========================================================================
    # TREINO INCREMENTAL
    # ========================================================================

    def train_incremental(
        self,
        training_batch: List[Dict[str, Any]],
    ) -> Dict[str, Any]:
        """Treina modelo incrementalmente com batch de dados.

        Processa um batch de dados de entrada (features + outcome) e:
        1. Calcula metricas do batch
        2. Atualiza estado interno
        3. Retorna resultado estruturado

        Args:
            training_batch: Lista de dicts com campos:
                - features: Lista de valores numericos
                - outcome: "WIN", "LOSS" ou "BREAKEVEN"
                - pnl: Valor em reais (float)
                - timestamp: datetime do trade

        Returns:
            Dict com:
                - samples_trained: Quantidade de amostras
                - model_metrics: Metricas calculadas
                - duration_seconds: Tempo de execucao
        """
        if not training_batch:
            return {
                "samples_trained": 0,
                "model_metrics": self.current_metrics or {},
                "duration_seconds": 0.0,
            }

        start_time = datetime.now()

        # Extrair dados
        outcomes: List[str] = [d["outcome"] for d in training_batch]
        pnls: List[float] = [d["pnl"] for d in training_batch]

        # Calcular metricas
        metrics = self._calculate_metrics(outcomes, pnls)
        self.current_metrics = metrics

        # Atualizar estado
        self.samples_trained += len(training_batch)

        duration = (datetime.now() - start_time).total_seconds()

        result = TrainingResult(
            samples_trained=len(training_batch),
            model_metrics=metrics,
            duration_seconds=duration,
            timestamp=datetime.now(),
            batch_size=len(training_batch),
        )

        self.training_history.append(result)

        return {
            "samples_trained": result.samples_trained,
            "model_metrics": result.model_metrics,
            "duration_seconds": result.duration_seconds,
        }

    # ========================================================================
    # VALIDACAO
    # ========================================================================

    def validate_model(
        self,
        validation_batch: List[Dict[str, Any]],
        threshold_zscore: float = 2.0,
    ) -> Dict[str, Any]:
        """Valida modelo comparando metricas contra baseline.

        Compara metricas atuais contra baseline usando Z-score
        para deteccao de degradacao.

        Args:
            validation_batch: Dados de validacao (mesmo formato treino)
            threshold_zscore: Limiar Z-score para flagrar degradacao

        Returns:
            Dict com:
                - is_valid: True se passou validacao
                - metrics: Metricas atuais
                - comparison: Comparacao baseline vs atual
                - passed_checks: Numero de metricas OK
        """
        # Calcular metricas do batch
        outcomes = [d["outcome"] for d in validation_batch]
        pnls = [d["pnl"] for d in validation_batch]
        current_metrics = self._calculate_metrics(outcomes, pnls)

        # Comparar contra baseline
        comparison: Dict[str, Dict[str, float]] = {}
        degraded_metrics: List[str] = []
        passed_checks = 0

        for metric_name, baseline_value in self.baseline_metrics.items():
            if metric_name in current_metrics:
                current_value = current_metrics[metric_name]
                delta = current_value - baseline_value

                # Calcular Z-score (simplificado)
                zscore = 0.0
                baseline_value = float(baseline_value)
                current_value = float(current_value)
                if baseline_value != 0:
                    zscore = (current_value - baseline_value) / abs(baseline_value)

                comparison[metric_name] = {
                    "baseline": baseline_value,
                    "current": current_value,
                    "delta": delta,
                    "zscore": zscore,
                }

                # Checar degradacao
                if zscore < -threshold_zscore:
                    degraded_metrics.append(metric_name)
                else:
                    passed_checks += 1

        is_valid = len(degraded_metrics) == 0

        return {
            "is_valid": is_valid,
            "metrics": current_metrics,
            "comparison": comparison,
            "passed_checks": passed_checks,
            "total_checks": len(self.baseline_metrics),
            "degradation_metrics": degraded_metrics,
        }

    # ========================================================================
    # PERSISTENCIA
    # ========================================================================

    def save_model_version(
        self,
        training_data: List[Dict[str, Any]],
        description: str = "",
    ) -> str:
        """Salva versao atual do modelo com metadados.

        Incrementa versao semantic (v1.0.0, v1.0.1, etc) e
        persiste em JSON com timestamp e metricas.

        Args:
            training_data: Dados usados no treino
            description: Descricao opcional da versao

        Returns:
            version_id: Identificador da versao (ex: "v1.0.0")
        """
        # Gerar version_id
        self.version_counter += 1
        version_id = f"v1.0.{self.version_counter}"

        # Criar objeto versao
        version = ModelVersion(
            version_id=version_id,
            timestamp=datetime.now(),
            model_state=self.model_state,
            metrics=self.current_metrics,
            training_samples=len(training_data),
            baseline_metrics=self.baseline_metrics,
            description=description,
        )

        # Salvar em arquivo
        file_path = self.models_dir / f"{version_id}.json"
        with open(file_path, "w") as f:
            data = version.para_dict()
            json.dump(data, f, indent=2)

        return version_id

    def load_model_version(self, version_id: str) -> Optional[Dict[str, Any]]:
        """Carrega versao salva de modelo.

        Args:
            version_id: ID da versao (ex: "v1.0.0")

        Returns:
            Dict com dados da versao ou None se nao existe
        """
        file_path = self.models_dir / f"{version_id}.json"

        if not file_path.exists():
            return None

        with open(file_path, "r") as f:
            data: Dict[str, Any] = json.load(f)

        return data

    # ========================================================================
    # ROLLBACK
    # ========================================================================

    def rollback_on_degradation(
        self,
        new_batch: List[Dict[str, Any]],
        previous_version: str,
        win_rate_threshold: float = 0.55,
    ) -> Dict[str, Any]:
        """Detecta degradacao e faz rollback automatico.

        Se metricas do novo batch caem abaixo de threshold,
        restaura versao anterior automaticamente.

        Args:
            new_batch: Novo batch de dados
            previous_version: Version_id para rollback
            win_rate_threshold: Limiar minimo de win_rate

        Returns:
            Dict com:
                - degradation_detected: True se degradacao
                - rollback_performed: True se rollback executado
                - restored_version: Versao restaurada
        """
        # Calcular metricas do novo batch
        outcomes = [d["outcome"] for d in new_batch]
        pnls = [d["pnl"] for d in new_batch]
        new_metrics = self._calculate_metrics(outcomes, pnls)

        # Checar degradacao
        degradation_detected = False
        degraded_metrics: List[str] = []

        if new_metrics.get("win_rate", 0) < win_rate_threshold:
            degradation_detected = True
            degraded_metrics.append("win_rate")

        # Se degradacao, fazer rollback
        rollback_performed = False
        restored_version: Optional[str] = None

        if degradation_detected:
            loaded = self.load_model_version(previous_version)
            if loaded:
                # Restaurar estado
                self.current_metrics = loaded["metrics"]
                self.model_state = loaded["model_state"]
                rollback_performed = True
                restored_version = previous_version

        return {
            "degradation_detected": degradation_detected,
            "rollback_performed": rollback_performed,
            "degraded_metrics": degraded_metrics,
            "restored_version": restored_version,
            "timestamp": datetime.now().isoformat(),
            "reason": (
                "Degradacao de win_rate abaixo de threshold"
                if degradation_detected
                else ""
            ),
        }

    # ========================================================================
    # UTILITARIOS DE CALCULO
    # ========================================================================

    def _calculate_metrics(
        self,
        outcomes: List[str],
        pnls: List[float],
    ) -> Dict[str, float]:
        """Calcula metricas de performance.

        Args:
            outcomes: Lista de "WIN", "LOSS", "BREAKEVEN"
            pnls: Lista de valores de PnL

        Returns:
            Dict com metricas: win_rate, f1_score, sharpe_ratio, etc
        """
        if not outcomes:
            return {
                "win_rate": 0.0,
                "loss_rate": 0.0,
                "avg_pnl": 0.0,
                "total_pnl": 0.0,
                "f1_score": 0.0,
                "sharpe_ratio": 0.0,
                "std_pnl": 0.0,
            }

        # Contar outcomes
        wins = sum(1 for o in outcomes if o == OutcomeType.WIN.value)
        losses = sum(1 for o in outcomes if o == OutcomeType.LOSS.value)
        total = len(outcomes)

        # Win rate e loss rate
        win_rate = wins / total if total > 0 else 0.0
        loss_rate = losses / total if total > 0 else 0.0

        # PnL
        total_pnl = sum(pnls)
        avg_pnl = total_pnl / total if total > 0 else 0.0

        # Standard deviation
        std_pnl = (
            statistics.stdev(pnls)
            if len(pnls) > 1 and total > 1
            else 0.0
        )

        # Sharpe ratio (simplificado: avg_pnl / std_pnl)
        sharpe_ratio = (
            avg_pnl / std_pnl if std_pnl != 0 and avg_pnl != 0 else 0.0
        )

        # F1 score (simplificado: 2 * (precision * recall) / (precision + recall))
        # Aqui precision = recall = win_rate
        f1_base = 2 * win_rate * win_rate / (win_rate + win_rate + 0.0001)
        f1_score = max(0.0, min(1.0, f1_base))

        return {
            "win_rate": win_rate,
            "loss_rate": loss_rate,
            "avg_pnl": avg_pnl,
            "total_pnl": total_pnl,
            "f1_score": f1_score,
            "sharpe_ratio": sharpe_ratio,
            "std_pnl": std_pnl,
        }

    def gerar_relatorio_json(self) -> str:
        """Gera relatorio completo em JSON.

        Returns:
            String JSON com estado atual do controlador
        """
        data = {
            "model_name": self.model_name,
            "samples_trained": self.samples_trained,
            "current_metrics": self.current_metrics,
            "baseline_metrics": self.baseline_metrics,
            "training_history": [h.para_dict() for h in self.training_history],
            "timestamp": datetime.now().isoformat(),
        }

        return json.dumps(data, indent=2)

    def gerar_relatorio_markdown(self) -> str:
        """Gera relatorio em Markdown legivel.

        Returns:
            String Markdown com resumo do modelo
        """
        lines = [
            "# Relatorio Online Learning Controller",
            "",
            f"## Modelo: {self.model_name}",
            f"**Amostras Treinadas:** {self.samples_trained}",
            f"**Timestamp:** {datetime.now().isoformat()}",
            "",
            "## Metricas Baseline",
        ]

        for metric, value in self.baseline_metrics.items():
            lines.append(f"- **{metric}:** {value:.4f}")

        lines.extend(
            [
                "",
                "## Metricas Atuais",
            ]
        )

        for metric, value in self.current_metrics.items():
            lines.append(f"- **{metric}:** {value:.4f}")

        lines.extend(
            [
                "",
                f"## Historico ({len(self.training_history)} sessoes)",
            ]
        )

        for i, record in enumerate(self.training_history[-5:], 1):
            lines.append(
                f"- **Sessao {i}:** {record.samples_trained} amostras, "
                f"F1={record.model_metrics.get('f1_score', 0):.4f}"
            )

        return "\n".join(lines)

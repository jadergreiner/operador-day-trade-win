"""
RLRetainScheduler - Agendamento inteligente de retrain de modelo RL.

Objetivo: Detectar degradacao de modelo vs baseline e agendar retrain
em horario off-peak para melhorar performance operacional.

Componentes:
- RLSchedulerConfig: Configuracao de thresholds e horarios
- TrainingJob: Representacao de job de retrain agendado
- JobStatus: Status do job (scheduled, running, completed, failed)
- DegradationDetectionMethod: Metodo de deteccao (Z-score, percentual, threshold)
- RLScheduler: Orquestrador principal

Uso:
    scheduler = RLScheduler(
        config_path="data/scheduler",
        baseline_metrics={"win_rate": 65.0, "sharpe": 1.2}
    )

    # Detectar degradacao
    degradado, motivo = scheduler.detectar_degradacao({
        "win_rate": 58.0,
        "sharpe": 1.1
    })

    # Agendar retrain se degradado
    if degradado:
        job = scheduler.agendar_retrain(motivo, DegradationDetectionMethod.PERCENTUAL)
        scheduler.salvar_job(job)
"""

import json
import uuid
from dataclasses import asdict, dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, cast


class JobStatus(Enum):
    """Status de um job de retrain."""

    SCHEDULED = "scheduled"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


class DegradationDetectionMethod(Enum):
    """Metodo de deteccao de degradacao do modelo."""

    Z_SCORE = "z_score"
    PERCENTUAL = "percentual"
    THRESHOLD = "threshold"


@dataclass
class RLSchedulerConfig:
    """Configuracao do scheduler de retrain.

    Atributos:
        horario_inicio_offpeak: Hora inicial off-peak (HH:MM)
        horario_fim_offpeak: Hora final off-peak (HH:MM)
        threshold_win_rate_drop: Queda maxima aceita em win_rate (%)
        threshold_sharpe_min: Sharpe minimo aceitavel
        metodo_deteccao: Metodo de deteccao de degradacao
        intervalo_verificacao_minutos: Intervalo entre verificacoes
    """

    horario_inicio_offpeak: str = "18:30"
    horario_fim_offpeak: str = "23:00"
    threshold_win_rate_drop: float = 5.0
    threshold_sharpe_min: float = 0.8
    metodo_deteccao: DegradationDetectionMethod = (
        DegradationDetectionMethod.PERCENTUAL
    )
    intervalo_verificacao_minutos: int = 60
    z_score_threshold: float = 2.0


@dataclass
class TrainingJob:
    """Representacao de um job de retrain agendado.

    Atributos:
        job_id: Identificador unico do job
        scheduled_at: Timestamp de quando foi agendado
        motivo_degradacao: Descricao da degradacao detectada
        status: Status atual do job
        metodo_deteccao: Metodo usado para detectar degradacao
        started_at: Timestamp quando comecou execucao (opcional)
        completed_at: Timestamp quando terminou execucao (opcional)
    """

    job_id: str
    scheduled_at: str
    motivo_degradacao: str
    status: JobStatus
    metodo_deteccao: DegradationDetectionMethod
    started_at: Optional[str] = None
    completed_at: Optional[str] = None


class RLScheduler:
    """Orquestrador de scheduling de retrain de modelo RL.

    Funcionalidades:
    - Detecta degradacao de metricas vs baseline
    - Agenda retrain em horario off-peak
    - Persiste jobs em JSON
    - Fornece relatorios de status

    Uso:
        scheduler = RLScheduler("data/scheduler", baseline)
        degradacao, motivo = scheduler.detectar_degradacao(metricas_atuais)
        if degradacao:
            job = scheduler.agendar_retrain(motivo)
            scheduler.salvar_job(job)
    """

    def __init__(
        self,
        config_path: str,
        baseline_metrics: Dict[str, float],
        config: Optional[RLSchedulerConfig] = None,
    ) -> None:
        """Inicializar o scheduler.

        Args:
            config_path: Caminho para armazenar estado do scheduler
            baseline_metrics: Metricas baseline (win_rate, sharpe, etc)
            config: Configuracao customizada (opcional)
        """
        self.config_path = Path(config_path)
        self.config_path.mkdir(parents=True, exist_ok=True)

        self.baseline_metrics = baseline_metrics
        self.config = config or RLSchedulerConfig()

        self._arquivo_jobs = self.config_path / "scheduler_jobs.json"
        self._inicializar_jobs()

    def _inicializar_jobs(self) -> None:
        """Inicializar arquivo de jobs se nao existe."""
        if not self._arquivo_jobs.exists():
            self._arquivo_jobs.write_text(json.dumps([], indent=2))

    def detectar_degradacao(
        self,
        metricas_atuais: Dict[str, float],
        metodo_deteccao: Optional[DegradationDetectionMethod] = None,
        baseline_comparator: Optional[Any] = None,
    ) -> Tuple[bool, str]:
        """Detectar degradacao de modelo vs baseline.

        Criterios:
        - win_rate: queda > threshold_win_rate_drop
        - sharpe: < threshold_sharpe_min

        Args:
            metricas_atuais: Metricas do modelo atual

        Returns:
            Tupla (degradacao detectada, motivo)
        """
        metodo = metodo_deteccao or self.config.metodo_deteccao
        if metodo == DegradationDetectionMethod.Z_SCORE:
            return self._detectar_degradacao_z_score(
                metricas_atuais=metricas_atuais,
                baseline_comparator=baseline_comparator,
            )
        if metodo == DegradationDetectionMethod.THRESHOLD:
            return self._detectar_degradacao_threshold(metricas_atuais)
        return self._detectar_degradacao_percentual(metricas_atuais)

    def _detectar_degradacao_percentual(
        self, metricas_atuais: Dict[str, float]
    ) -> Tuple[bool, str]:
        motivos: List[str] = []

        if "win_rate" in self.baseline_metrics and "win_rate" in metricas_atuais:
            baseline_wr = self.baseline_metrics["win_rate"]
            atual_wr = metricas_atuais["win_rate"]
            drop = baseline_wr - atual_wr
            if drop > self.config.threshold_win_rate_drop:
                motivos.append(
                    f"win_rate drop de {baseline_wr:.1f}% para {atual_wr:.1f}%"
                )

        if "sharpe" in self.baseline_metrics and "sharpe" in metricas_atuais:
            atual_sh = metricas_atuais["sharpe"]
            if atual_sh < self.config.threshold_sharpe_min:
                motivos.append(
                    f"sharpe {atual_sh:.2f} abaixo do minimo {self.config.threshold_sharpe_min}"
                )

        return len(motivos) > 0, " | ".join(motivos) if motivos else ""

    def _detectar_degradacao_threshold(
        self, metricas_atuais: Dict[str, float]
    ) -> Tuple[bool, str]:
        motivos: List[str] = []
        # Regra threshold: degrade se qualquer métrica cruzar limite fixo de risco.
        if "win_rate" in metricas_atuais and metricas_atuais["win_rate"] < 50.0:
            motivos.append(
                f"win_rate {metricas_atuais['win_rate']:.1f}% abaixo do limite 50.0%"
            )
        if "sharpe" in metricas_atuais and metricas_atuais["sharpe"] < self.config.threshold_sharpe_min:
            motivos.append(
                f"sharpe {metricas_atuais['sharpe']:.2f} abaixo do minimo {self.config.threshold_sharpe_min}"
            )
        if "f1" in metricas_atuais and metricas_atuais["f1"] < 0.55:
            motivos.append(f"f1 {metricas_atuais['f1']:.2f} abaixo do limite 0.55")
        if "f1_score" in metricas_atuais and metricas_atuais["f1_score"] < 0.55:
            motivos.append(
                f"f1_score {metricas_atuais['f1_score']:.2f} abaixo do limite 0.55"
            )
        return len(motivos) > 0, " | ".join(motivos) if motivos else ""

    def _normalizar_metricas_para_baseline_comparator(
        self, metricas: Dict[str, float]
    ) -> Dict[str, float]:
        normalizadas: Dict[str, float] = dict(metricas)
        if "sharpe_ratio" not in normalizadas and "sharpe" in normalizadas:
            normalizadas["sharpe_ratio"] = float(normalizadas["sharpe"])
        if "f1_score" not in normalizadas and "f1" in normalizadas:
            normalizadas["f1_score"] = float(normalizadas["f1"])
        return normalizadas

    def _detectar_degradacao_z_score(
        self,
        metricas_atuais: Dict[str, float],
        baseline_comparator: Optional[Any] = None,
    ) -> Tuple[bool, str]:
        comparator = baseline_comparator
        if comparator is None:
            from src.application.ac6_9_baseline_comparator import BaselineComparator

            comparator = BaselineComparator(
                baseline_metrics=self._normalizar_metricas_para_baseline_comparator(
                    self.baseline_metrics
                ),
                z_score_threshold=self.config.z_score_threshold,
            )

        comparison = comparator.comparar_metricas(
            current_metrics=self._normalizar_metricas_para_baseline_comparator(
                metricas_atuais
            ),
            baseline_version="v1.0.0",
        )
        if comparison.is_degraded:
            motivos = ", ".join(comparison.degraded_metrics)
            return True, f"z_score degradado nas metricas: {motivos}"
        return False, ""

    def agendar_retrain(
        self,
        motivo_degradacao: str,
        metodo_deteccao: DegradationDetectionMethod,
    ) -> TrainingJob:
        """Agendar novo job de retrain.

        Args:
            motivo_degradacao: Descricao do motivo da degradacao
            metodo_deteccao: Metodo usado para detectar degradacao

        Returns:
            Job agendado
        """
        job_id = f"retrain_{uuid.uuid4().hex[:8]}"
        scheduled_at = datetime.now().isoformat()

        job = TrainingJob(
            job_id=job_id,
            scheduled_at=scheduled_at,
            motivo_degradacao=motivo_degradacao,
            status=JobStatus.SCHEDULED,
            metodo_deteccao=metodo_deteccao,
        )

        return job

    def salvar_job(self, job: TrainingJob) -> None:
        """Salvar job em arquivo JSON.

        Args:
            job: Job a salvar
        """
        jobs = self.listar_jobs()

        # Remover job se ja existe (para atualizar)
        jobs = [j for j in jobs if j.get("job_id") != job.job_id]

        # Adicionar novo job
        job_dict = {
            "job_id": job.job_id,
            "scheduled_at": job.scheduled_at,
            "motivo_degradacao": job.motivo_degradacao,
            "status": job.status.value,
            "metodo_deteccao": job.metodo_deteccao.value,
            "started_at": job.started_at,
            "completed_at": job.completed_at,
        }
        jobs.append(job_dict)

        self._arquivo_jobs.write_text(json.dumps(jobs, indent=2))

    def listar_jobs(self) -> List[Dict[str, Any]]:
        """Listar todos os jobs agendados.

        Returns:
            Lista de jobs em formato dict
        """
        if not self._arquivo_jobs.exists():
            return []

        conteudo = self._arquivo_jobs.read_text()
        if not conteudo:
            return []

        return cast(List[Dict[str, Any]], json.loads(conteudo))

    def obter_job(self, job_id: str) -> Optional[TrainingJob]:
        """Recuperar job especifico por ID.

        Args:
            job_id: ID do job

        Returns:
            Job se encontrado, None caso contrario
        """
        jobs = self.listar_jobs()

        for job_dict in jobs:
            if job_dict.get("job_id") == job_id:
                # Converter dict de volta para TrainingJob
                return TrainingJob(
                    job_id=job_dict["job_id"],
                    scheduled_at=job_dict["scheduled_at"],
                    motivo_degradacao=job_dict["motivo_degradacao"],
                    status=JobStatus(job_dict["status"]),
                    metodo_deteccao=DegradationDetectionMethod(
                        job_dict["metodo_deteccao"]
                    ),
                    started_at=job_dict.get("started_at"),
                    completed_at=job_dict.get("completed_at"),
                )

        return None

    def gerar_relatorio_json(self) -> str:
        """Gerar relatorio de todos os jobs em JSON.

        Returns:
            String JSON com estrutura de jobs
        """
        relatorio = {
            "timestamp": datetime.now().isoformat(),
            "baseline_metrics": self.baseline_metrics,
            "total_jobs": len(self.listar_jobs()),
            "jobs": self.listar_jobs(),
        }

        return json.dumps(relatorio, indent=2)

    def gerar_relatorio_markdown(self) -> str:
        """Gerar relatorio formatado em Markdown.

        Returns:
            String Markdown com resumo dos jobs
        """
        jobs = self.listar_jobs()

        linhas = [
            "# Relatorio de Scheduler de Retrain RL",
            "",
            f"**Timestamp:** {datetime.now().isoformat()}",
            "",
            "## Baseline Metrics",
            "",
        ]

        for metrica, valor in self.baseline_metrics.items():
            linhas.append(f"- {metrica}: {valor}")

        linhas.extend(
            [
                "",
                f"## Status (Total: {len(jobs)} jobs)",
                "",
            ]
        )

        if not jobs:
            linhas.append("Nenhum job agendado.")
        else:
            linhas.append("| Job ID | Status | Motivo | Metodo |")
            linhas.append("|--------|--------|--------|--------|")

            for job in jobs:
                linhas.append(
                    f"| {job['job_id']} | {job['status']} | "
                    f"{job['motivo_degradacao'][:50]} | {job['metodo_deteccao']} |"
                )

        return "\n".join(linhas)

    def contar_jobs_por_status(self) -> Dict[str, int]:
        """Contar jobs agrupados por status.

        Returns:
            Dicionario com contagem por status
        """
        jobs = self.listar_jobs()
        contagem: Dict[str, int] = {
            "scheduled": 0,
            "running": 0,
            "completed": 0,
            "failed": 0,
        }

        for job in jobs:
            status = job.get("status", "scheduled")
            contagem[status] = contagem.get(status, 0) + 1

        return contagem

    def _normalizar_metricas_para_rollback(
        self, metricas: Dict[str, float]
    ) -> Dict[str, float]:
        """Normaliza chaves para compatibilidade com ModelRollbackManager.

        O rollback manager usa `sharpe` e `f1`, enquanto alguns pipelines usam
        `sharpe_ratio` e `f1_score`.
        """
        normalizadas: Dict[str, float] = dict(metricas)
        if "sharpe" not in normalizadas and "sharpe_ratio" in normalizadas:
            normalizadas["sharpe"] = float(normalizadas["sharpe_ratio"])
        if "f1" not in normalizadas and "f1_score" in normalizadas:
            normalizadas["f1"] = float(normalizadas["f1_score"])
        return normalizadas

    def processar_degradacao_com_rollback(
        self,
        metricas_atuais: Dict[str, float],
        metodo_deteccao: Optional[DegradationDetectionMethod] = None,
        contexto_operacional: Optional[Dict[str, Any]] = None,
        rollback_manager: Optional[Any] = None,
    ) -> Dict[str, Any]:
        """Processa degradação e aciona retrain + rollback opcional.

        Fluxo:
        1. Detecta degradação com regras do scheduler.
        2. Se degradou, agenda e persiste job de retrain.
        3. Se rollback_manager foi informado, executa check_degradation e
           rollback automático quando recomendado.
        """
        metodo = self.resolver_metodo_deteccao_dinamico(
            metodo_override=metodo_deteccao,
            contexto_operacional=contexto_operacional or {},
        )
        degradacao_detectada, motivo = self.detectar_degradacao(
            metricas_atuais=metricas_atuais,
            metodo_deteccao=metodo,
        )

        resultado: Dict[str, Any] = {
            "degradacao_detectada": degradacao_detectada,
            "motivo_degradacao": motivo,
            "job_id": None,
            "retrain_agendado": False,
            "rollback_recomendado": False,
            "rollback_executado": False,
            "rollback_razao": "",
            "metodo_deteccao_aplicado": metodo.value,
        }

        if not degradacao_detectada:
            return resultado

        job = self.agendar_retrain(motivo_degradacao=motivo, metodo_deteccao=metodo)
        self.salvar_job(job)
        resultado["job_id"] = job.job_id
        resultado["retrain_agendado"] = True

        if rollback_manager is None:
            return resultado

        metricas_baseline = self._normalizar_metricas_para_rollback(
            self.baseline_metrics
        )
        metricas_atuais_rollback = self._normalizar_metricas_para_rollback(
            metricas_atuais
        )
        decisao = rollback_manager.check_degradation(
            current_metrics=metricas_atuais_rollback,
            baseline_metrics=metricas_baseline,
        )
        resultado["rollback_recomendado"] = bool(decisao.deve_fazer_rollback)
        resultado["rollback_razao"] = str(decisao.razao)

        if decisao.deve_fazer_rollback and decisao.versao_rollback:
            rollback_ok = bool(rollback_manager.executar_rollback(decisao.versao_rollback))
            resultado["rollback_executado"] = rollback_ok

        return resultado

    def resolver_metodo_deteccao_dinamico(
        self,
        metodo_override: Optional[DegradationDetectionMethod] = None,
        contexto_operacional: Optional[Dict[str, Any]] = None,
    ) -> DegradationDetectionMethod:
        """Resolve método de detecção por sessão/regime.

        Regras:
        - `metodo_override` sempre tem prioridade.
        - Cenário de estresse/alta vol prioriza `THRESHOLD`.
        - Cenário estável com drift monitorável prioriza `Z_SCORE`.
        - Caso contrário usa método configurado no scheduler.
        """
        if metodo_override is not None:
            return metodo_override

        contexto = contexto_operacional or {}
        regime = str(
            contexto.get("regime_mercado")
            or contexto.get("regime")
            or ""
        ).lower()
        stress_score = self._coerce_float(
            contexto.get("stress_score"), contexto.get("risk_stress_score")
        )
        volatilidade = self._coerce_float(
            contexto.get("volatilidade"), contexto.get("volatility")
        )
        drift_score = self._coerce_float(
            contexto.get("drift_score"), contexto.get("drift")
        )

        regime_estresse = any(
            token in regime
            for token in ("stress", "estresse", "high_vol", "ruptura", "crash")
        )
        if regime_estresse:
            return DegradationDetectionMethod.THRESHOLD
        if stress_score is not None and stress_score >= 0.70:
            return DegradationDetectionMethod.THRESHOLD
        if volatilidade is not None and volatilidade >= 75.0:
            return DegradationDetectionMethod.THRESHOLD

        regime_estavel = any(
            token in regime
            for token in ("estavel", "normal", "range", "trend", "trending")
        )
        if regime_estavel:
            return DegradationDetectionMethod.Z_SCORE
        if drift_score is not None and drift_score >= 0.30:
            return DegradationDetectionMethod.Z_SCORE

        return self.config.metodo_deteccao

    def _coerce_float(self, *values: Any) -> Optional[float]:
        for value in values:
            if value is None or isinstance(value, bool):
                continue
            try:
                return float(value)
            except (TypeError, ValueError):
                continue
        return None

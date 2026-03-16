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
        self, metricas_atuais: Dict[str, float]
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
        motivos: List[str] = []

        # Verificar win_rate drop
        if "win_rate" in self.baseline_metrics and "win_rate" in metricas_atuais:
            baseline_wr = self.baseline_metrics["win_rate"]
            atual_wr = metricas_atuais["win_rate"]
            drop = baseline_wr - atual_wr

            if drop > self.config.threshold_win_rate_drop:
                motivos.append(
                    f"win_rate drop de {baseline_wr:.1f}% para {atual_wr:.1f}%"
                )

        # Verificar sharpe minimo
        if "sharpe" in self.baseline_metrics and "sharpe" in metricas_atuais:
            baseline_sh = self.baseline_metrics["sharpe"]
            atual_sh = metricas_atuais["sharpe"]

            if atual_sh < self.config.threshold_sharpe_min:
                motivos.append(
                    f"sharpe {atual_sh:.2f} abaixo do minimo {self.config.threshold_sharpe_min}"
                )

        degradacao = len(motivos) > 0
        motivo = " | ".join(motivos) if motivos else ""

        return degradacao, motivo

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

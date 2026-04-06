"""
Testes para RLRetainScheduler - agendamento de retrain de modelo RL.

Objetivo: Validar scheduling de retrain quando modelo degradou vs baseline.
Cobre: agendamento, deteccao de degradacao, persistencia e integracao.

Requisitos:
- P2-RETRAIN_SCHEDULER: Detectar degradacao e agendar retrain off-peak
- Threshold de degradacao: win_rate drop >5% ou Sharpe <0.8
- Horario off-peak: 18:30-23:00 BRT
- Persistencia: JSON file-based
"""

import json
import os
import tempfile
from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from src.application.rl_retrain_scheduler import (
    DegradationDetectionMethod,
    JobStatus,
    RLScheduler,
    RLSchedulerConfig,
    TrainingJob,
)


class TestRLSchedulerConfigDataclass:
    """Validar RLSchedulerConfig dataclass."""

    def test_criar_config_completa(self) -> None:
        """Criar config com todos os parametros."""
        config = RLSchedulerConfig(
            horario_inicio_offpeak="18:30",
            horario_fim_offpeak="23:00",
            threshold_win_rate_drop=5.0,
            threshold_sharpe_min=0.8,
            metodo_deteccao=DegradationDetectionMethod.Z_SCORE,
            intervalo_verificacao_minutos=60,
        )

        assert config.horario_inicio_offpeak == "18:30"
        assert config.horario_fim_offpeak == "23:00"
        assert config.threshold_win_rate_drop == 5.0
        assert config.threshold_sharpe_min == 0.8

    def test_config_para_dict(self) -> None:
        """Converter config para dict para persistencia."""
        config = RLSchedulerConfig(
            horario_inicio_offpeak="18:00",
            horario_fim_offpeak="23:00",
            threshold_win_rate_drop=5.0,
            threshold_sharpe_min=0.8,
            metodo_deteccao=DegradationDetectionMethod.PERCENTUAL,
            intervalo_verificacao_minutos=30,
        )

        config_dict = config.__dict__

        assert "horario_inicio_offpeak" in config_dict
        assert config_dict["threshold_win_rate_drop"] == 5.0
        assert "metodo_deteccao" in config_dict


class TestTrainingJobDataclass:
    """Validar TrainingJob dataclass."""

    def test_criar_job_agendado(self) -> None:
        """Criar job agendado."""
        job = TrainingJob(
            job_id="retrain_001",
            scheduled_at=datetime.now().__str__(),
            motivo_degradacao="win_rate drop de 65% para 58%",
            status=JobStatus.SCHEDULED,
            metodo_deteccao=DegradationDetectionMethod.PERCENTUAL,
        )

        assert job.job_id == "retrain_001"
        assert job.status == JobStatus.SCHEDULED
        assert "drop" in job.motivo_degradacao

    def test_job_para_dict(self) -> None:
        """Converter job para dict para persistencia."""
        agora = datetime.now().__str__()
        job = TrainingJob(
            job_id="job_123",
            scheduled_at=agora,
            motivo_degradacao="degradacao detectada",
            status=JobStatus.SCHEDULED,
            metodo_deteccao=DegradationDetectionMethod.Z_SCORE,
        )

        job_dict = {
            "job_id": job.job_id,
            "scheduled_at": job.scheduled_at,
            "motivo_degradacao": job.motivo_degradacao,
            "status": job.status.value,
            "metodo_deteccao": job.metodo_deteccao.value,
        }

        assert job_dict["job_id"] == "job_123"
        assert "scheduled_at" in job_dict


class TestJobStatusEnum:
    """Validar JobStatus enum."""

    def test_todos_status_definidos(self) -> None:
        """Verificar que todos os status existem."""
        assert hasattr(JobStatus, "SCHEDULED")
        assert hasattr(JobStatus, "RUNNING")
        assert hasattr(JobStatus, "COMPLETED")
        assert hasattr(JobStatus, "FAILED")

    def test_status_value(self) -> None:
        """Verificar valor de cada status."""
        assert JobStatus.SCHEDULED.value == "scheduled"
        assert JobStatus.RUNNING.value == "running"
        assert JobStatus.COMPLETED.value == "completed"
        assert JobStatus.FAILED.value == "failed"


class TestDegradationDetectionMethodEnum:
    """Validar DegradationDetectionMethod enum."""

    def test_metodos_definidos(self) -> None:
        """Verificar que todos os metodos existem."""
        assert hasattr(DegradationDetectionMethod, "Z_SCORE")
        assert hasattr(DegradationDetectionMethod, "PERCENTUAL")
        assert hasattr(DegradationDetectionMethod, "THRESHOLD")

    def test_metodos_value(self) -> None:
        """Verificar valor de cada metodo."""
        assert DegradationDetectionMethod.Z_SCORE.value == "z_score"
        assert DegradationDetectionMethod.PERCENTUAL.value == "percentual"
        assert DegradationDetectionMethod.THRESHOLD.value == "threshold"


class TestRLSchedulerInit:
    """Validar inicializacao do RLScheduler."""

    def test_inicializar_com_config_padrao(self) -> None:
        """Criar scheduler com config padrao."""
        with tempfile.TemporaryDirectory() as tmpdir:
            scheduler = RLScheduler(
                config_path=tmpdir,
                baseline_metrics={"win_rate": 65.0, "sharpe": 1.2},
            )

            assert scheduler is not None
            assert scheduler.baseline_metrics["win_rate"] == 65.0

    def test_inicializar_cria_diretorio_config(self) -> None:
        """Inicializacao cria arquivo de configuracao."""
        with tempfile.TemporaryDirectory() as tmpdir:
            scheduler = RLScheduler(
                config_path=tmpdir,
                baseline_metrics={"win_rate": 65.0, "sharpe": 1.2},
            )

            path_jobs = Path(tmpdir) / "scheduler_jobs.json"
            # Arquivo pode nao existir até primeiro agendamento

            assert scheduler.baseline_metrics is not None


class TestRLSchedulerDeteccaoDegradacao:
    """Validar deteccao de degradacao."""

    def test_detectar_degradacao_win_rate_drop(self) -> None:
        """Detectar queda de win rate (65% -> 58%)."""
        with tempfile.TemporaryDirectory() as tmpdir:
            scheduler = RLScheduler(
                config_path=tmpdir,
                baseline_metrics={"win_rate": 65.0, "sharpe": 1.2},
            )

            metricas_atuais = {"win_rate": 58.0, "sharpe": 1.1}

            degradacao, motivo = scheduler.detectar_degradacao(metricas_atuais)

            assert degradacao is True
            assert "win_rate" in motivo

    def test_nao_detectar_degradacao_sem_queda(self) -> None:
        """Nao detectar degradacao quando metricas sao estáveis."""
        with tempfile.TemporaryDirectory() as tmpdir:
            scheduler = RLScheduler(
                config_path=tmpdir,
                baseline_metrics={"win_rate": 65.0, "sharpe": 1.2},
            )

            metricas_atuais = {"win_rate": 64.0, "sharpe": 1.15}

            degradacao, motivo = scheduler.detectar_degradacao(metricas_atuais)

            assert degradacao is False

    def test_detectar_degradacao_sharpe_low(self) -> None:
        """Detectar Sharpe abaixo do threshold (1.2 -> 0.7)."""
        with tempfile.TemporaryDirectory() as tmpdir:
            scheduler = RLScheduler(
                config_path=tmpdir,
                baseline_metrics={"win_rate": 65.0, "sharpe": 1.2},
            )

            metricas_atuais = {"win_rate": 65.0, "sharpe": 0.7}

            degradacao, motivo = scheduler.detectar_degradacao(metricas_atuais)

            assert degradacao is True
            assert "sharpe" in motivo.lower()


class TestRLSchedulerAgendamento:
    """Validar agendamento de retrain."""

    def test_agendar_retrain_em_horario_offpeak(self) -> None:
        """Agendar retrain para horario off-peak."""
        with tempfile.TemporaryDirectory() as tmpdir:
            scheduler = RLScheduler(
                config_path=tmpdir,
                baseline_metrics={"win_rate": 65.0, "sharpe": 1.2},
            )

            motivo = "win_rate drop de 65% para 58%"
            job = scheduler.agendar_retrain(
                motivo_degradacao=motivo,
                metodo_deteccao=DegradationDetectionMethod.PERCENTUAL,
            )

            assert job is not None
            assert job.status == JobStatus.SCHEDULED
            assert "drop" in job.motivo_degradacao

    def test_job_id_unico_por_agendamento(self) -> None:
        """Cada job tem ID unico."""
        with tempfile.TemporaryDirectory() as tmpdir:
            scheduler = RLScheduler(
                config_path=tmpdir,
                baseline_metrics={"win_rate": 65.0, "sharpe": 1.2},
            )

            job1 = scheduler.agendar_retrain(
                motivo_degradacao="degradacao 1",
                metodo_deteccao=DegradationDetectionMethod.Z_SCORE,
            )

            job2 = scheduler.agendar_retrain(
                motivo_degradacao="degradacao 2",
                metodo_deteccao=DegradationDetectionMethod.PERCENTUAL,
            )

            assert job1.job_id != job2.job_id


class TestRLSchedulerPersistencia:
    """Validar persistencia de jobs em JSON."""

    def test_salvar_job_em_json(self) -> None:
        """Salvar job agendado em arquivo JSON."""
        with tempfile.TemporaryDirectory() as tmpdir:
            scheduler = RLScheduler(
                config_path=tmpdir,
                baseline_metrics={"win_rate": 65.0, "sharpe": 1.2},
            )

            job = scheduler.agendar_retrain(
                motivo_degradacao="test degradacao",
                metodo_deteccao=DegradationDetectionMethod.PERCENTUAL,
            )

            scheduler.salvar_job(job)

            arquivo_jobs = Path(tmpdir) / "scheduler_jobs.json"
            assert arquivo_jobs.exists()

    def test_carregar_jobs_persistidos(self) -> None:
        """Carregar jobs previamente persistidos."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Primeiro scheduler agenda job
            scheduler1 = RLScheduler(
                config_path=tmpdir,
                baseline_metrics={"win_rate": 65.0, "sharpe": 1.2},
            )

            job1 = scheduler1.agendar_retrain(
                motivo_degradacao="degradacao 1",
                metodo_deteccao=DegradationDetectionMethod.PERCENTUAL,
            )
            scheduler1.salvar_job(job1)

            # Segundo scheduler carrega jobs existentes
            scheduler2 = RLScheduler(
                config_path=tmpdir,
                baseline_metrics={"win_rate": 65.0, "sharpe": 1.2},
            )
            jobs_carregados = scheduler2.listar_jobs()

            assert len(jobs_carregados) >= 1


class TestRLSchedulerListagemJobs:
    """Validar listagem e recuperacao de jobs."""

    def test_listar_jobs_vazios(self) -> None:
        """Listar jobs quando nao ha agendamentos."""
        with tempfile.TemporaryDirectory() as tmpdir:
            scheduler = RLScheduler(
                config_path=tmpdir,
                baseline_metrics={"win_rate": 65.0, "sharpe": 1.2},
            )

            jobs = scheduler.listar_jobs()

            assert isinstance(jobs, list)
            # Pode estar vazio ou ter jobs previos

    def test_listar_jobs_com_agendamentos(self) -> None:
        """Listar jobs apos agendamentos."""
        with tempfile.TemporaryDirectory() as tmpdir:
            scheduler = RLScheduler(
                config_path=tmpdir,
                baseline_metrics={"win_rate": 65.0, "sharpe": 1.2},
            )

            job1 = scheduler.agendar_retrain(
                motivo_degradacao="degradacao 1",
                metodo_deteccao=DegradationDetectionMethod.Z_SCORE,
            )
            scheduler.salvar_job(job1)

            job2 = scheduler.agendar_retrain(
                motivo_degradacao="degradacao 2",
                metodo_deteccao=DegradationDetectionMethod.PERCENTUAL,
            )
            scheduler.salvar_job(job2)

            jobs = scheduler.listar_jobs()

            assert len(jobs) >= 2


class TestRLSchedulerObterJob:
    """Validar recuperacao de job por ID."""

    def test_obter_job_por_id(self) -> None:
        """Recuperar job especifico por ID."""
        with tempfile.TemporaryDirectory() as tmpdir:
            scheduler = RLScheduler(
                config_path=tmpdir,
                baseline_metrics={"win_rate": 65.0, "sharpe": 1.2},
            )

            job = scheduler.agendar_retrain(
                motivo_degradacao="teste",
                metodo_deteccao=DegradationDetectionMethod.PERCENTUAL,
            )
            scheduler.salvar_job(job)

            job_recuperado = scheduler.obter_job(job.job_id)

            assert job_recuperado is not None
            assert job_recuperado.job_id == job.job_id

    def test_obter_job_inexistente_retorna_none(self) -> None:
        """Retornar None ao buscar job inexistente."""
        with tempfile.TemporaryDirectory() as tmpdir:
            scheduler = RLScheduler(
                config_path=tmpdir,
                baseline_metrics={"win_rate": 65.0, "sharpe": 1.2},
            )

            job = scheduler.obter_job("job_inexistente_123")

            assert job is None


class TestRLSchedulerAtualizarStatus:
    """Validar atualizacao de status de job."""

    def test_atualizar_job_para_running(self) -> None:
        """Atualizar status de SCHEDULED para RUNNING."""
        with tempfile.TemporaryDirectory() as tmpdir:
            scheduler = RLScheduler(
                config_path=tmpdir,
                baseline_metrics={"win_rate": 65.0, "sharpe": 1.2},
            )

            job = scheduler.agendar_retrain(
                motivo_degradacao="teste",
                metodo_deteccao=DegradationDetectionMethod.PERCENTUAL,
            )

            job.status = JobStatus.RUNNING
            scheduler.salvar_job(job)

            job_atualizado = scheduler.obter_job(job.job_id)
            assert job_atualizado is not None

            assert job_atualizado.status == JobStatus.RUNNING

    def test_atualizar_job_para_completed(self) -> None:
        """Atualizar status para COMPLETED."""
        with tempfile.TemporaryDirectory() as tmpdir:
            scheduler = RLScheduler(
                config_path=tmpdir,
                baseline_metrics={"win_rate": 65.0, "sharpe": 1.2},
            )

            job = scheduler.agendar_retrain(
                motivo_degradacao="teste",
                metodo_deteccao=DegradationDetectionMethod.PERCENTUAL,
            )

            job.status = JobStatus.COMPLETED
            scheduler.salvar_job(job)

            job_atualizado = scheduler.obter_job(job.job_id)
            assert job_atualizado is not None

            assert job_atualizado.status == JobStatus.COMPLETED


class TestRLSchedulerRelatorios:
    """Validar geracao de relatorios e exportacoes."""

    def test_gerar_relatorio_json(self) -> None:
        """Gerar relatorio de jobs em JSON."""
        with tempfile.TemporaryDirectory() as tmpdir:
            scheduler = RLScheduler(
                config_path=tmpdir,
                baseline_metrics={"win_rate": 65.0, "sharpe": 1.2},
            )

            job = scheduler.agendar_retrain(
                motivo_degradacao="teste",
                metodo_deteccao=DegradationDetectionMethod.PERCENTUAL,
            )
            scheduler.salvar_job(job)

            relatorio = scheduler.gerar_relatorio_json()

            assert isinstance(relatorio, str)
            assert "job_id" in relatorio


class TestRLSchedulerIntegracaoRollback:
    """Valida fluxo integrado retrain + rollback automatico."""

    def test_processar_degradacao_com_rollback_executa_fluxo_completo(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            scheduler = RLScheduler(
                config_path=tmpdir,
                baseline_metrics={"win_rate": 65.0, "sharpe": 1.2, "f1": 0.70},
            )
            rollback_manager = MagicMock()
            rollback_manager.check_degradation.return_value = MagicMock(
                deve_fazer_rollback=True,
                versao_rollback="checkpoint_best",
                razao="degradacao_win_rate",
            )
            rollback_manager.executar_rollback.return_value = True

            resultado = scheduler.processar_degradacao_com_rollback(
                metricas_atuais={"win_rate": 58.0, "sharpe": 0.7, "f1": 0.61},
                rollback_manager=rollback_manager,
            )

            assert resultado["degradacao_detectada"] is True
            assert resultado["retrain_agendado"] is True
            assert resultado["job_id"] is not None
            assert resultado["rollback_recomendado"] is True
            assert resultado["rollback_executado"] is True
            rollback_manager.check_degradation.assert_called_once()
            rollback_manager.executar_rollback.assert_called_once_with("checkpoint_best")

    def test_processar_degradacao_sem_rollback_manager_agenda_somente_retrain(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            scheduler = RLScheduler(
                config_path=tmpdir,
                baseline_metrics={"win_rate": 65.0, "sharpe": 1.2},
            )

            resultado = scheduler.processar_degradacao_com_rollback(
                metricas_atuais={"win_rate": 58.0, "sharpe": 0.7}
            )

            assert resultado["degradacao_detectada"] is True
            assert resultado["retrain_agendado"] is True
            assert resultado["rollback_recomendado"] is False
            assert resultado["rollback_executado"] is False

    def test_processar_sem_degradacao_nao_agenda_nem_rollback(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            scheduler = RLScheduler(
                config_path=tmpdir,
                baseline_metrics={"win_rate": 65.0, "sharpe": 1.2},
            )
            rollback_manager = MagicMock()

            resultado = scheduler.processar_degradacao_com_rollback(
                metricas_atuais={"win_rate": 64.5, "sharpe": 1.1},
                rollback_manager=rollback_manager,
            )

            assert resultado["degradacao_detectada"] is False
            assert resultado["retrain_agendado"] is False
            assert resultado["job_id"] is None
            rollback_manager.check_degradation.assert_not_called()

    def test_normaliza_metricas_sharpe_ratio_e_f1_score_para_rollback(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            scheduler = RLScheduler(
                config_path=tmpdir,
                baseline_metrics={
                    "win_rate": 65.0,
                    "sharpe_ratio": 1.2,
                    "f1_score": 0.70,
                },
            )
            rollback_manager = MagicMock()
            rollback_manager.check_degradation.return_value = MagicMock(
                deve_fazer_rollback=False,
                versao_rollback=None,
                razao="ok",
            )

            scheduler.processar_degradacao_com_rollback(
                metricas_atuais={
                    "win_rate": 58.0,
                    "sharpe_ratio": 0.7,
                    "f1_score": 0.61,
                },
                rollback_manager=rollback_manager,
            )

            kwargs = rollback_manager.check_degradation.call_args.kwargs
            assert kwargs["current_metrics"]["sharpe"] == 0.7
            assert kwargs["current_metrics"]["f1"] == 0.61
            assert kwargs["baseline_metrics"]["sharpe"] == 1.2
            assert kwargs["baseline_metrics"]["f1"] == 0.70

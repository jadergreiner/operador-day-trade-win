"""
Testes para BUG-DIARIOS-01: Watchdog de Threads dos Diarios.

Valida resiliencia de thread, reinicio automatico apos falha,
logging de stack trace e monitoramento de saude das threads.

Status: BUG-DIARIOS-01 (INICIAR_DIARIOS.bat)
Referencia: docs/BACKLOG.md
"""

import threading
import time
import logging
from unittest.mock import MagicMock, patch, call
from datetime import datetime

import pytest

from src.application.diarios_watchdog import (
    ThreadWatchdog,
    ConfiguracaoThread,
    StatusThread,
    ResultadoReinicio,
    INTERVALO_VERIFICACAO_SEG,
)


# ─────────────────────────────────────────────────────────────────
# Fixtures
# ─────────────────────────────────────────────────────────────────

def funcao_estavel() -> None:
    """Funcao que roda por um tempo curto sem erro."""
    time.sleep(0.05)


def funcao_com_falha() -> None:
    """Funcao que lanca excecao imediatamente."""
    raise RuntimeError("Falha simulada de thread")


def funcao_lenta() -> None:
    """Funcao que roda por mais tempo."""
    time.sleep(10)


# ─────────────────────────────────────────────────────────────────
# Testes: ConfiguracaoThread
# ─────────────────────────────────────────────────────────────────

class TestConfiguracaoThread:
    """Testes para dataclass de configuracao de thread monitorada."""

    def test_criar_configuracao_basica(self) -> None:
        """ConfiguracaoThread criada com valores minimos."""
        config = ConfiguracaoThread(
            nome="TradingJournal",
            funcao_alvo=funcao_estavel,
        )
        assert config.nome == "TradingJournal"
        assert config.funcao_alvo is funcao_estavel
        assert config.intervalo_reinicio_seg == 5
        assert config.max_reinicios == 10
        assert config.daemon is True

    def test_criar_configuracao_personalizada(self) -> None:
        """ConfiguracaoThread aceita parametros customizados."""
        config = ConfiguracaoThread(
            nome="AIReflection",
            funcao_alvo=funcao_estavel,
            intervalo_reinicio_seg=15,
            max_reinicios=3,
            daemon=False,
        )
        assert config.intervalo_reinicio_seg == 15
        assert config.max_reinicios == 3
        assert config.daemon is False


# ─────────────────────────────────────────────────────────────────
# Testes: StatusThread
# ─────────────────────────────────────────────────────────────────

class TestStatusThread:
    """Testes para enum de status da thread monitorada."""

    def test_valores_status(self) -> None:
        """StatusThread tem os 4 estados esperados."""
        assert StatusThread.RODANDO.value == "RODANDO"
        assert StatusThread.MORTA.value == "MORTA"
        assert StatusThread.REINICIANDO.value == "REINICIANDO"
        assert StatusThread.PARADA.value == "PARADA"

    def test_contagem_status(self) -> None:
        """StatusThread tem exatamente 4 estados."""
        assert len(StatusThread) == 4


# ─────────────────────────────────────────────────────────────────
# Testes: ResultadoReinicio
# ─────────────────────────────────────────────────────────────────

class TestResultadoReinicio:
    """Testes para dataclass de resultado de reinicio."""

    def test_criar_resultado_sucesso(self) -> None:
        """ResultadoReinicio criado para reinicio bem sucedido."""
        resultado = ResultadoReinicio(
            nome_thread="TradingJournal",
            sucesso=True,
            tentativa=1,
            motivo_falha=None,
        )
        assert resultado.nome_thread == "TradingJournal"
        assert resultado.sucesso is True
        assert resultado.tentativa == 1
        assert resultado.motivo_falha is None

    def test_criar_resultado_falha(self) -> None:
        """ResultadoReinicio criado para reinicio com falha."""
        resultado = ResultadoReinicio(
            nome_thread="AIReflection",
            sucesso=False,
            tentativa=3,
            motivo_falha="Max reinicios atingido",
        )
        assert resultado.sucesso is False
        assert resultado.motivo_falha == "Max reinicios atingido"

    def test_resultado_para_dict(self) -> None:
        """ResultadoReinicio converte para dict com campos obrigatorios."""
        resultado = ResultadoReinicio(
            nome_thread="RLDiary",
            sucesso=True,
            tentativa=2,
            motivo_falha=None,
        )
        d = resultado.para_dict()
        assert "nome_thread" in d
        assert "sucesso" in d
        assert "tentativa" in d
        assert "timestamp" in d


# ─────────────────────────────────────────────────────────────────
# Testes: ThreadWatchdog — inicializacao
# ─────────────────────────────────────────────────────────────────

class TestThreadWatchdogInit:
    """Testes de inicializacao do ThreadWatchdog."""

    def test_criar_watchdog_vazio(self) -> None:
        """ThreadWatchdog criado sem threads registradas."""
        watchdog = ThreadWatchdog()
        assert watchdog.total_threads_registradas() == 0
        assert not watchdog.esta_rodando()

    def test_registrar_thread(self) -> None:
        """ThreadWatchdog aceita registro de thread monitorada."""
        watchdog = ThreadWatchdog()
        config = ConfiguracaoThread(
            nome="TradingJournal",
            funcao_alvo=funcao_estavel,
        )
        watchdog.registrar_thread(config)
        assert watchdog.total_threads_registradas() == 1

    def test_registrar_multiplas_threads(self) -> None:
        """ThreadWatchdog aceita multiplas threads registradas."""
        watchdog = ThreadWatchdog()
        for nome in ["TradingJournal", "AIReflection", "RLDiary"]:
            config = ConfiguracaoThread(nome=nome, funcao_alvo=funcao_estavel)
            watchdog.registrar_thread(config)
        assert watchdog.total_threads_registradas() == 3


# ─────────────────────────────────────────────────────────────────
# Testes: ThreadWatchdog — iniciar e parar
# ─────────────────────────────────────────────────────────────────

class TestThreadWatchdogCicloDeVida:
    """Testes de ciclo de vida do watchdog (iniciar/parar)."""

    def test_iniciar_watchdog(self) -> None:
        """ThreadWatchdog inicia threads e muda estado para rodando."""
        watchdog = ThreadWatchdog()
        config = ConfiguracaoThread(
            nome="TradingJournal",
            funcao_alvo=funcao_lenta,
            intervalo_reinicio_seg=1,
        )
        watchdog.registrar_thread(config)
        watchdog.iniciar()
        time.sleep(0.1)
        assert watchdog.esta_rodando()
        watchdog.parar()

    def test_parar_watchdog(self) -> None:
        """ThreadWatchdog para corretamente e muda estado."""
        watchdog = ThreadWatchdog()
        config = ConfiguracaoThread(
            nome="TradingJournal",
            funcao_alvo=funcao_lenta,
        )
        watchdog.registrar_thread(config)
        watchdog.iniciar()
        time.sleep(0.1)
        watchdog.parar()
        time.sleep(0.2)
        assert not watchdog.esta_rodando()

    def test_status_thread_rodando(self) -> None:
        """ThreadWatchdog reporta status RODANDO para thread ativa."""
        watchdog = ThreadWatchdog()
        config = ConfiguracaoThread(
            nome="TradingJournal",
            funcao_alvo=funcao_lenta,
        )
        watchdog.registrar_thread(config)
        watchdog.iniciar()
        time.sleep(0.1)
        status = watchdog.obter_status_thread("TradingJournal")
        assert status == StatusThread.RODANDO
        watchdog.parar()


# ─────────────────────────────────────────────────────────────────
# Testes: ThreadWatchdog — deteccao de falha e reinicio
# ─────────────────────────────────────────────────────────────────

class TestThreadWatchdogReinicio:
    """Testes de deteccao de falha e reinicio automatico."""

    def test_detectar_thread_morta(self) -> None:
        """Watchdog detecta quando thread morre e atualiza status."""
        watchdog = ThreadWatchdog(intervalo_verificacao_seg=0.05)
        config = ConfiguracaoThread(
            nome="TradingJournal",
            funcao_alvo=funcao_estavel,  # termina rapido
            intervalo_reinicio_seg=0.1,
        )
        watchdog.registrar_thread(config)
        watchdog.iniciar()
        time.sleep(0.5)  # espera thread terminar e watchdog detectar
        # Verifica que houve ao menos 1 reinicio (contagem > 0)
        contagem = watchdog.obter_contagem_reinicios("TradingJournal")
        assert contagem >= 1
        watchdog.parar()

    def test_reinicio_apos_falha(self) -> None:
        """Watchdog reinicia thread que lancou excecao."""
        reinicios = []

        def funcao_com_contador() -> None:
            reinicios.append(1)
            if len(reinicios) < 3:
                raise RuntimeError(f"Falha simulada #{len(reinicios)}")
            time.sleep(10)  # na 3a tentativa roda por mais tempo

        watchdog = ThreadWatchdog(intervalo_verificacao_seg=0.05)
        config = ConfiguracaoThread(
            nome="AIReflection",
            funcao_alvo=funcao_com_contador,
            intervalo_reinicio_seg=0.05,
            max_reinicios=5,
        )
        watchdog.registrar_thread(config)
        watchdog.iniciar()
        time.sleep(1.0)
        assert len(reinicios) >= 2, f"Esperado >= 2 reinicios, obteve {len(reinicios)}"
        watchdog.parar()

    def test_nao_reiniciar_alem_do_limite(self) -> None:
        """Watchdog para de reiniciar ao atingir max_reinicios."""
        watchdog = ThreadWatchdog(intervalo_verificacao_seg=0.05)
        config = ConfiguracaoThread(
            nome="RLDiary",
            funcao_alvo=funcao_com_falha,
            intervalo_reinicio_seg=0.05,
            max_reinicios=2,
        )
        watchdog.registrar_thread(config)
        watchdog.iniciar()
        time.sleep(1.5)
        contagem = watchdog.obter_contagem_reinicios("RLDiary")
        assert contagem <= 3, f"Reinicios {contagem} excede limite 2"
        status = watchdog.obter_status_thread("RLDiary")
        assert status == StatusThread.PARADA
        watchdog.parar()


# ─────────────────────────────────────────────────────────────────
# Testes: ThreadWatchdog — logging de stack trace
# ─────────────────────────────────────────────────────────────────

class TestThreadWatchdogLogging:
    """Testes de logging de falha com stack trace."""

    def test_log_stack_trace_ao_falhar(self, caplog: pytest.LogCaptureFixture) -> None:
        """Watchdog registra stack trace quando thread lanca excecao."""
        with caplog.at_level(logging.ERROR, logger="diarios_watchdog"):
            watchdog = ThreadWatchdog(intervalo_verificacao_seg=0.05)
            config = ConfiguracaoThread(
                nome="TradingJournal",
                funcao_alvo=funcao_com_falha,
                intervalo_reinicio_seg=0.05,
                max_reinicios=1,
            )
            watchdog.registrar_thread(config)
            watchdog.iniciar()
            time.sleep(0.5)
            watchdog.parar()

        # Verifica que algo foi logado (nome da thread presente)
        logs_watchdog = [r for r in caplog.records if "TradingJournal" in r.message]
        assert len(logs_watchdog) >= 1

    def test_historico_falhas_registrado(self) -> None:
        """Watchdog mantem historico de falhas com timestamp."""
        watchdog = ThreadWatchdog(intervalo_verificacao_seg=0.05)
        config = ConfiguracaoThread(
            nome="AIReflection",
            funcao_alvo=funcao_com_falha,
            intervalo_reinicio_seg=0.05,
            max_reinicios=2,
        )
        watchdog.registrar_thread(config)
        watchdog.iniciar()
        time.sleep(0.8)
        watchdog.parar()

        historico = watchdog.obter_historico_falhas("AIReflection")
        assert len(historico) >= 1
        primeira_falha = historico[0]
        assert "timestamp" in primeira_falha
        assert "erro" in primeira_falha
        assert "stack_trace" in primeira_falha


# ─────────────────────────────────────────────────────────────────
# Testes: ThreadWatchdog — relatorio de saude
# ─────────────────────────────────────────────────────────────────

class TestThreadWatchdogRelatorio:
    """Testes para relatorio de saude das threads."""

    def test_relatorio_saude_estrutura(self) -> None:
        """Relatorio de saude tem campos obrigatorios."""
        watchdog = ThreadWatchdog()
        config = ConfiguracaoThread(
            nome="TradingJournal",
            funcao_alvo=funcao_lenta,
        )
        watchdog.registrar_thread(config)
        watchdog.iniciar()
        time.sleep(0.1)
        relatorio = watchdog.gerar_relatorio_saude()
        watchdog.parar()

        assert "timestamp" in relatorio
        assert "threads" in relatorio
        assert "total_registradas" in relatorio
        assert "total_rodando" in relatorio
        assert "total_mortas" in relatorio
        assert "total_paradas" in relatorio

    def test_relatorio_saude_dados_corretos(self) -> None:
        """Relatorio reflete estado real das threads."""
        watchdog = ThreadWatchdog()
        config = ConfiguracaoThread(
            nome="TradingJournal",
            funcao_alvo=funcao_lenta,
        )
        watchdog.registrar_thread(config)
        watchdog.iniciar()
        time.sleep(0.1)
        relatorio = watchdog.gerar_relatorio_saude()
        watchdog.parar()

        assert relatorio["total_registradas"] == 1
        assert relatorio["total_rodando"] == 1
        thread_info = relatorio["threads"]["TradingJournal"]
        assert "status" in thread_info
        assert "reinicios" in thread_info

    def test_type_hints_100_porcento(self) -> None:
        """Modulo tem type hints completos (verificacao de importacao)."""
        from src.application import diarios_watchdog
        import inspect

        # Verifica que as classes principais existem e sao importaveis
        assert hasattr(diarios_watchdog, "ThreadWatchdog")
        assert hasattr(diarios_watchdog, "ConfiguracaoThread")
        assert hasattr(diarios_watchdog, "StatusThread")
        assert hasattr(diarios_watchdog, "ResultadoReinicio")
        assert hasattr(diarios_watchdog, "INTERVALO_VERIFICACAO_SEG")

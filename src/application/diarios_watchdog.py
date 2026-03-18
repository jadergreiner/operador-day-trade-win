"""
BUG-DIARIOS-01: Watchdog de Threads dos Diarios.

Responsabilidades:
- Monitorar se cada thread de diario esta viva
- Reiniciar automaticamente thread morta com backoff
- Registrar stack trace de falha para auditoria
- Gerar relatorio de saude das threads

Pipeline:
    start_journals_full_display.py inicia threads
    -> ThreadWatchdog monitora em loop
    -> Thread morta detectada -> log stack trace -> reinicio
    -> Max reinicios atingido -> PARADA (nao reinicia mais)

Status: Implementacao v1.0 (18/03/2026)
Referencia: docs/BACKLOG.md (BUG-DIARIOS-01)
"""

import logging
import threading
import time
import traceback
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Callable, Optional

logger = logging.getLogger("diarios_watchdog")

# Constante exportada para uso externo e testes
INTERVALO_VERIFICACAO_SEG: float = 10.0


class StatusThread(Enum):
    """Estado atual de uma thread monitorada pelo watchdog."""

    RODANDO = "RODANDO"
    MORTA = "MORTA"
    REINICIANDO = "REINICIANDO"
    PARADA = "PARADA"


@dataclass
class ConfiguracaoThread:
    """Configuracao de uma thread monitorada pelo watchdog.

    Args:
        nome: Identificador unico da thread (ex: 'TradingJournal').
        funcao_alvo: Callable executado pela thread.
        intervalo_reinicio_seg: Segundos de espera antes de reiniciar.
        max_reinicios: Numero maximo de reinicios antes de desistir.
        daemon: Se True, thread e daemon (encerra com processo principal).

    """

    nome: str
    funcao_alvo: Callable[[], None]
    intervalo_reinicio_seg: float = 5.0
    max_reinicios: int = 10
    daemon: bool = True


@dataclass
class ResultadoReinicio:
    """Resultado de uma tentativa de reinicio de thread.

    Args:
        nome_thread: Nome da thread reiniciada.
        sucesso: True se reinicio foi bem sucedido.
        tentativa: Numero da tentativa (1-indexado).
        motivo_falha: Descricao do motivo de falha (se sucesso=False).

    """

    nome_thread: str
    sucesso: bool
    tentativa: int
    motivo_falha: Optional[str]
    timestamp: datetime = field(default_factory=datetime.now)

    def para_dict(self) -> dict[str, Any]:
        """Converte resultado para dicionario JSON-serializavel.

        Returns:
            dict com campos do resultado.

        """
        return {
            "nome_thread": self.nome_thread,
            "sucesso": self.sucesso,
            "tentativa": self.tentativa,
            "motivo_falha": self.motivo_falha,
            "timestamp": self.timestamp.isoformat(),
        }


@dataclass
class _EstadoThread:
    """Estado interno de uma thread monitorada (uso privado).

    Args:
        config: Configuracao da thread.
        thread: Objeto threading.Thread atual (ou None).
        status: Estado atual da thread.
        contagem_reinicios: Total de reinicios realizados.
        historico_falhas: Lista de ocorrencias de falha com stack trace.

    """

    config: ConfiguracaoThread
    thread: Optional[threading.Thread] = None
    status: StatusThread = StatusThread.PARADA
    contagem_reinicios: int = 0
    historico_falhas: list[dict[str, Any]] = field(default_factory=list)


class ThreadWatchdog:
    """Watchdog que monitora e reinicia threads de diarios automaticamente.

    Monitora periodicamente se cada thread registrada esta viva.
    Ao detectar thread morta, registra o erro com stack trace e
    reinicia a thread apos intervalo configurado.

    Exemplo de uso:
        watchdog = ThreadWatchdog(intervalo_verificacao_seg=10)
        watchdog.registrar_thread(ConfiguracaoThread(
            nome="TradingJournal",
            funcao_alvo=run_trading_journal,
            max_reinicios=10,
        ))
        watchdog.iniciar()

    """

    def __init__(
        self,
        intervalo_verificacao_seg: float = INTERVALO_VERIFICACAO_SEG,
    ) -> None:
        """Inicializa o watchdog.

        Args:
            intervalo_verificacao_seg: Frequencia de checagem das threads.

        """
        self._intervalo_verificacao = intervalo_verificacao_seg
        self._estados: dict[str, _EstadoThread] = {}
        self._rodando = False
        self._thread_watchdog: Optional[threading.Thread] = None
        self._lock = threading.Lock()

    # ─────────────────────────────────────────────────────────────
    # API publica
    # ─────────────────────────────────────────────────────────────

    def registrar_thread(self, config: ConfiguracaoThread) -> None:
        """Registra uma thread para ser monitorada pelo watchdog.

        Args:
            config: Configuracao da thread a monitorar.

        """
        with self._lock:
            self._estados[config.nome] = _EstadoThread(config=config)

    def iniciar(self) -> None:
        """Inicia todas as threads registradas e o loop de monitoramento.

        Raises:
            RuntimeError: Se watchdog ja estiver rodando.

        """
        if self._rodando:
            return
        self._rodando = True

        with self._lock:
            for nome, estado in self._estados.items():
                self._iniciar_thread_interna(estado)

        self._thread_watchdog = threading.Thread(
            target=self._loop_monitoramento,
            daemon=True,
            name="DiarioWatchdog",
        )
        self._thread_watchdog.start()

    def parar(self) -> None:
        """Para o watchdog e encerra o loop de monitoramento."""
        self._rodando = False

    def esta_rodando(self) -> bool:
        """Retorna True se o watchdog esta ativo.

        Returns:
            bool: True se watchdog rodando.

        """
        return self._rodando

    def total_threads_registradas(self) -> int:
        """Retorna numero de threads registradas.

        Returns:
            int: Quantidade de threads monitoradas.

        """
        return len(self._estados)

    def obter_status_thread(self, nome: str) -> StatusThread:
        """Retorna status atual de uma thread pelo nome.

        Args:
            nome: Identificador da thread.

        Returns:
            StatusThread: Estado atual da thread.

        Raises:
            KeyError: Se thread nao registrada.

        """
        with self._lock:
            return self._estados[nome].status

    def obter_contagem_reinicios(self, nome: str) -> int:
        """Retorna quantas vezes a thread foi reiniciada.

        Args:
            nome: Identificador da thread.

        Returns:
            int: Numero de reinicios.

        Raises:
            KeyError: Se thread nao registrada.

        """
        with self._lock:
            return self._estados[nome].contagem_reinicios

    def obter_historico_falhas(self, nome: str) -> list[dict[str, Any]]:
        """Retorna historico de falhas de uma thread.

        Cada entrada contem timestamp, mensagem de erro e stack trace.

        Args:
            nome: Identificador da thread.

        Returns:
            list: Lista de ocorrencias de falha.

        Raises:
            KeyError: Se thread nao registrada.

        """
        with self._lock:
            return list(self._estados[nome].historico_falhas)

    def gerar_relatorio_saude(self) -> dict[str, Any]:
        """Gera relatorio de saude de todas as threads monitoradas.

        Returns:
            dict com status geral e por thread.

        """
        with self._lock:
            threads_info: dict[str, Any] = {}
            total_rodando = 0
            total_mortas = 0
            total_paradas = 0

            for nome, estado in self._estados.items():
                threads_info[nome] = {
                    "status": estado.status.value,
                    "reinicios": estado.contagem_reinicios,
                    "falhas_totais": len(estado.historico_falhas),
                }
                if estado.status == StatusThread.RODANDO:
                    total_rodando += 1
                elif estado.status == StatusThread.MORTA:
                    total_mortas += 1
                elif estado.status == StatusThread.PARADA:
                    total_paradas += 1

            return {
                "timestamp": datetime.now().isoformat(),
                "total_registradas": len(self._estados),
                "total_rodando": total_rodando,
                "total_mortas": total_mortas,
                "total_paradas": total_paradas,
                "threads": threads_info,
            }

    # ─────────────────────────────────────────────────────────────
    # Metodos internos
    # ─────────────────────────────────────────────────────────────

    def _iniciar_thread_interna(self, estado: _EstadoThread) -> None:
        """Cria e inicia a thread monitorada com wrapper de captura de erro.

        Args:
            estado: Estado interno da thread a iniciar.

        """
        config = estado.config

        def _wrapper() -> None:
            """Wrapper que captura excecao e registra stack trace."""
            try:
                config.funcao_alvo()
            except Exception as exc:
                tb = traceback.format_exc()
                mensagem = (
                    f"[WATCHDOG] Thread '{config.nome}' encerrou com erro: "
                    f"{type(exc).__name__}: {exc}"
                )
                logger.error(mensagem)
                logger.error(f"[WATCHDOG] Stack trace:\n{tb}")

                with self._lock:
                    if config.nome in self._estados:
                        self._estados[config.nome].historico_falhas.append({
                            "timestamp": datetime.now().isoformat(),
                            "erro": str(exc),
                            "stack_trace": tb,
                        })

        thread = threading.Thread(
            target=_wrapper,
            daemon=config.daemon,
            name=config.nome,
        )
        thread.start()
        estado.thread = thread
        estado.status = StatusThread.RODANDO

    def _loop_monitoramento(self) -> None:
        """Loop principal do watchdog — verifica e reinicia threads mortas."""
        while self._rodando:
            time.sleep(self._intervalo_verificacao)
            if not self._rodando:
                break
            self._verificar_threads()

    def _verificar_threads(self) -> None:
        """Verifica estado de cada thread e reinicia se necessario."""
        with self._lock:
            for nome, estado in self._estados.items():
                if estado.status == StatusThread.PARADA:
                    continue  # parada permanente, nao reiniciar
                if estado.thread is None:
                    continue
                if estado.thread.is_alive():
                    estado.status = StatusThread.RODANDO
                    continue

                # Thread nao esta viva — verificar limite de reinicios
                if estado.contagem_reinicios >= estado.config.max_reinicios:
                    logger.warning(
                        f"[WATCHDOG] Thread '{nome}' atingiu limite de "
                        f"{estado.config.max_reinicios} reinicios. "
                        f"Marcando como PARADA."
                    )
                    estado.status = StatusThread.PARADA
                    continue

                # Reiniciar thread
                estado.status = StatusThread.REINICIANDO
                estado.contagem_reinicios += 1
                logger.warning(
                    f"[WATCHDOG] Thread '{nome}' morta. "
                    f"Reiniciando ({estado.contagem_reinicios}/"
                    f"{estado.config.max_reinicios}) em "
                    f"{estado.config.intervalo_reinicio_seg:.1f}s..."
                )

                # Aguardar intervalo fora do lock para nao bloquear
                threading.Thread(
                    target=self._reiniciar_apos_intervalo,
                    args=(estado,),
                    daemon=True,
                ).start()

    def _reiniciar_apos_intervalo(self, estado: _EstadoThread) -> None:
        """Aguarda intervalo e reinicia thread monitorada.

        Args:
            estado: Estado interno da thread a reiniciar.

        """
        time.sleep(estado.config.intervalo_reinicio_seg)
        if not self._rodando:
            return
        with self._lock:
            if estado.status == StatusThread.PARADA:
                return
            logger.info(
                f"[WATCHDOG] Reiniciando thread '{estado.config.nome}'..."
            )
            self._iniciar_thread_interna(estado)

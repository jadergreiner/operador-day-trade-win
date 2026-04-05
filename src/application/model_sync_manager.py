"""ModelSyncManager — Hot-reload de modelo entre agentes paralelos (BLID-039).

Quando um agente RL carrega novo modelo treinado, o ModelSyncManager detecta
automaticamente a mudanca via polling de mtime no sistema de arquivos e notifica
os demais agentes por meio de callbacks registrados.

Mecanismo:
- Polling de ``os.stat().st_mtime`` nos diretorios monitorados
- Marker file JSON em ``data/models/.sync_marker`` para comunicacao entre processos
- Callbacks invocados atomicamente para cada mudanca detectada
- Thread daemon background com intervalo configuravel (padrao: 30s)

Exemplo de uso:
    config = ConfiguracaoSync(
        diretorios_modelos=[Path("data/models/novo_agente_rl/modelo_final")],
        caminho_marker=Path("data/models/.sync_marker"),
        intervalo_polling=30.0,
        id_agente="agente_rl_5000",
    )

    manager = ModelSyncManager(configuracao=config)
    manager.registrar_callback(meu_callback)
    manager.iniciar()

    # ... operacao normal ...

    manager.parar()
"""

from __future__ import annotations

import json
import logging
import threading
from collections import deque
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable

logger = logging.getLogger(__name__)

# Timeout em segundos para aguardar encerramento da thread de polling
_TIMEOUT_ENCERRAMENTO_THREAD = 5.0


# ---------------------------------------------------------------------------
# Configuracao
# ---------------------------------------------------------------------------


@dataclass
class ConfiguracaoSync:
    """Parametros de configuracao do ModelSyncManager.

    Atributos:
        diretorios_modelos: Lista de diretorios a monitorar (ex: modelo_final/).
        caminho_marker: Caminho completo do arquivo marker de sincronizacao.
        intervalo_polling: Intervalo em segundos entre verificacoes (padrao: 30s).
        id_agente: Identificador do agente que instancia o manager.
        max_eventos_historico: Limite do buffer de historico de eventos.
    """

    diretorios_modelos: list[Path]
    caminho_marker: Path
    intervalo_polling: float = 30.0
    id_agente: str = "agente_principal"
    max_eventos_historico: int = 100

    def __post_init__(self) -> None:
        if not self.diretorios_modelos:
            raise ValueError(
                "diretorios_modelos nao pode ser lista vazia"
            )
        if self.intervalo_polling <= 0:
            raise ValueError(
                "intervalo_polling deve ser maior que zero"
            )


# ---------------------------------------------------------------------------
# Evento de sincronizacao
# ---------------------------------------------------------------------------


@dataclass
class EventoSincronizacao:
    """Registro imutavel de uma mudanca de modelo detectada.

    Atributos:
        caminho_modelo: Path do diretorio de modelo que mudou.
        id_agente_origem: ID do agente que gerou o evento.
        timestamp_iso: Timestamp ISO 8601 UTC do evento.
        mtime_anterior: mtime anterior (float, segundos Unix).
        mtime_novo: mtime novo (float, segundos Unix).
    """

    caminho_modelo: Path
    id_agente_origem: str
    timestamp_iso: str
    mtime_anterior: float
    mtime_novo: float

    def para_dict(self) -> dict[str, object]:
        """Serializa o evento para dict compativel com JSON."""
        return {
            "caminho_modelo": str(self.caminho_modelo),
            "id_agente_origem": self.id_agente_origem,
            "timestamp_iso": self.timestamp_iso,
            "mtime_anterior": self.mtime_anterior,
            "mtime_novo": self.mtime_novo,
        }


# ---------------------------------------------------------------------------
# Status do manager
# ---------------------------------------------------------------------------


@dataclass
class StatusSync:
    """Snapshot do estado atual do ModelSyncManager.

    Atributos:
        ativo: True se a thread de polling esta rodando.
        total_eventos: Numero de mudancas detectadas ate agora.
        ultimo_evento: Ultimo EventoSincronizacao detectado (ou None).
        id_agente: ID do agente dono deste manager.
        intervalo_polling: Intervalo de polling configurado em segundos.
        diretorios_monitorados: Lista de Paths monitorados.
    """

    ativo: bool
    total_eventos: int
    ultimo_evento: EventoSincronizacao | None
    id_agente: str
    intervalo_polling: float
    diretorios_monitorados: list[Path] = field(default_factory=list)


# ---------------------------------------------------------------------------
# Manager principal
# ---------------------------------------------------------------------------

# Tipo de callback: recebe um EventoSincronizacao, retorna None
CallbackSincronizacao = Callable[[EventoSincronizacao], None]


class ModelSyncManager:
    """Monitora diretorios de modelos e notifica agentes sobre mudancas.

    Usa polling de ``mtime`` via thread daemon. Cada vez que o mtime de um
    diretorio monitorado muda, gera um ``EventoSincronizacao``, escreve o
    marker file e invoca todos os callbacks registrados.

    Exemplo:
        manager = ModelSyncManager(configuracao=config)
        manager.registrar_callback(recarregar_modelo)
        manager.iniciar()
    """

    def __init__(self, configuracao: ConfiguracaoSync) -> None:
        """Inicializa o manager com a configuracao fornecida.

        Args:
            configuracao: Parametros de monitoramento e sincronizacao.
        """
        self._config = configuracao
        self._callbacks: list[CallbackSincronizacao] = []
        self._historico_eventos: deque[EventoSincronizacao] = deque(
            maxlen=configuracao.max_eventos_historico
        )
        self._mtimes_baseline: dict[Path, float] = {}
        self._ativo = False
        self._lock = threading.Lock()
        self._thread: threading.Thread | None = None
        self._evento_parar = threading.Event()

        logger.info(
            "[ModelSyncManager] Inicializado | agente=%s | diretorios=%s | intervalo=%.1fs",
            self._config.id_agente,
            [str(d) for d in self._config.diretorios_modelos],
            self._config.intervalo_polling,
        )

    # ------------------------------------------------------------------
    # Ciclo de vida
    # ------------------------------------------------------------------

    def iniciar(self) -> None:
        """Inicia a thread de polling em background.

        Se ja estiver ativo, a chamada e ignorada (idempotente).
        """
        with self._lock:
            if self._ativo:
                logger.debug(
                    "[ModelSyncManager] ja ativo — ignorando segunda chamada a iniciar()"
                )
                return

            self._inicializar_mtimes()
            self._evento_parar.clear()
            self._ativo = True

        self._thread = threading.Thread(
            target=self._loop_polling,
            name=f"model-sync-{self._config.id_agente}",
            daemon=True,
        )
        self._thread.start()
        logger.info(
            "[ModelSyncManager] Thread de polling iniciada | agente=%s",
            self._config.id_agente,
        )

    def parar(self) -> None:
        """Para a thread de polling de forma segura.

        Aguarda ate a thread encerrar (timeout 5s) antes de retornar.
        Idempotente: chamadas repetidas sao ignoradas.
        """
        with self._lock:
            if not self._ativo:
                return
            self._ativo = False

        self._evento_parar.set()
        if self._thread is not None:
            self._thread.join(timeout=_TIMEOUT_ENCERRAMENTO_THREAD)
            self._thread = None

        logger.info(
            "[ModelSyncManager] Thread de polling encerrada | agente=%s",
            self._config.id_agente,
        )

    # ------------------------------------------------------------------
    # Callbacks
    # ------------------------------------------------------------------

    def registrar_callback(self, callback: CallbackSincronizacao) -> None:
        """Registra funcao a ser chamada quando modelo muda.

        Args:
            callback: Funcao com assinatura (EventoSincronizacao) -> None.
        """
        with self._lock:
            self._callbacks.append(callback)
        logger.debug(
            "[ModelSyncManager] Callback registrado | total=%d",
            len(self._callbacks),
        )

    def remover_callback(self, callback: CallbackSincronizacao) -> None:
        """Remove callback previamente registrado.

        Args:
            callback: Referencia ao callback a ser removido.
                      Se nao encontrado, a operacao e ignorada.
        """
        with self._lock:
            try:
                self._callbacks.remove(callback)
            except ValueError:
                pass

    # ------------------------------------------------------------------
    # Status e historico
    # ------------------------------------------------------------------

    def obter_status(self) -> StatusSync:
        """Retorna snapshot do estado atual do manager.

        Returns:
            StatusSync com ativo, total_eventos, ultimo_evento etc.
        """
        with self._lock:
            ultimo = (
                self._historico_eventos[-1] if self._historico_eventos else None
            )
            return StatusSync(
                ativo=self._ativo,
                total_eventos=len(self._historico_eventos),
                ultimo_evento=ultimo,
                id_agente=self._config.id_agente,
                intervalo_polling=self._config.intervalo_polling,
                diretorios_monitorados=list(self._config.diretorios_modelos),
            )

    def obter_historico_eventos(self) -> list[EventoSincronizacao]:
        """Retorna copia do historico de eventos detectados.

        Returns:
            Lista de EventoSincronizacao (copia — modificacoes nao afetam interno).
        """
        with self._lock:
            return list(self._historico_eventos)

    # ------------------------------------------------------------------
    # Internos
    # ------------------------------------------------------------------

    def _inicializar_mtimes(self) -> None:
        """Popula o baseline de mtimes para os diretorios configurados.

        Diretorios que nao existem sao ignorados silenciosamente.
        """
        for diretorio in self._config.diretorios_modelos:
            if diretorio.exists():
                self._mtimes_baseline[diretorio] = diretorio.stat().st_mtime
            else:
                logger.warning(
                    "[ModelSyncManager] Diretorio nao existe — ignorado | path=%s",
                    diretorio,
                )

    def _loop_polling(self) -> None:
        """Loop principal de polling executado na thread daemon."""
        logger.debug("[ModelSyncManager] Loop de polling iniciado")
        while not self._evento_parar.wait(timeout=self._config.intervalo_polling):
            try:
                eventos = self._verificar_mudancas()
                for evento in eventos:
                    self._registrar_evento(evento)
                    self._escrever_marker(evento)
                    self._disparar_callbacks(evento)
            except Exception:
                logger.exception(
                    "[ModelSyncManager] Erro inesperado no loop de polling"
                )
        logger.debug("[ModelSyncManager] Loop de polling encerrado")

    def _verificar_mudancas(self) -> list[EventoSincronizacao]:
        """Verifica todos os diretorios monitorados por mudancas de mtime.

        Returns:
            Lista de EventoSincronizacao para cada diretorio que mudou.
        """
        eventos: list[EventoSincronizacao] = []
        agora = datetime.now(tz=timezone.utc).isoformat()

        for diretorio in self._config.diretorios_modelos:
            if not diretorio.exists():
                continue

            mtime_atual = diretorio.stat().st_mtime
            mtime_anterior = self._mtimes_baseline.get(diretorio, 0.0)

            if mtime_atual > mtime_anterior:
                evento = EventoSincronizacao(
                    caminho_modelo=diretorio,
                    id_agente_origem=self._config.id_agente,
                    timestamp_iso=agora,
                    mtime_anterior=mtime_anterior,
                    mtime_novo=mtime_atual,
                )
                self._mtimes_baseline[diretorio] = mtime_atual
                logger.info(
                    "[ModelSyncManager] Mudanca detectada | path=%s | mtime_anterior=%.3f | mtime_novo=%.3f",
                    diretorio,
                    mtime_anterior,
                    mtime_atual,
                )
                eventos.append(evento)

        return eventos

    def _escrever_marker(self, evento: EventoSincronizacao) -> None:
        """Escreve marker file JSON com dados do evento de sincronizacao.

        O marker file e atomicamente substituido a cada escrita.
        Erros de IO sao logados mas nao propagados.

        Args:
            evento: Evento de sincronizacao a persistir no marker.
        """
        try:
            caminho = self._config.caminho_marker
            caminho.parent.mkdir(parents=True, exist_ok=True)
            caminho_tmp = caminho.with_suffix(".tmp")
            caminho_tmp.write_text(
                json.dumps(evento.para_dict(), ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
            caminho_tmp.replace(caminho)
            logger.debug(
                "[ModelSyncManager] Marker file escrito | path=%s",
                caminho,
            )
        except OSError:
            logger.exception(
                "[ModelSyncManager] Falha ao escrever marker file | path=%s",
                self._config.caminho_marker,
            )

    def _ler_marker(self) -> dict[str, object] | None:
        """Le e parseia o marker file JSON.

        Returns:
            Dict com dados do marker, ou None se ausente ou invalido.
        """
        caminho = self._config.caminho_marker
        if not caminho.exists():
            return None
        try:
            conteudo = caminho.read_text(encoding="utf-8")
            dados: dict[str, object] = json.loads(conteudo)
            return dados
        except (json.JSONDecodeError, OSError):
            logger.warning(
                "[ModelSyncManager] Marker file invalido ou ilegivel | path=%s",
                caminho,
            )
            return None

    def _disparar_callbacks(self, evento: EventoSincronizacao) -> None:
        """Invoca todos os callbacks registrados para o evento dado.

        Exceptions em callbacks individuais sao capturadas e logadas, sem
        interromper a execucao dos demais callbacks.

        Args:
            evento: Evento de sincronizacao a entregar aos callbacks.
        """
        with self._lock:
            callbacks = list(self._callbacks)

        for callback in callbacks:
            try:
                callback(evento)
            except Exception:
                logger.exception(
                    "[ModelSyncManager] Erro em callback | callback=%r",
                    callback,
                )

    def _registrar_evento(self, evento: EventoSincronizacao) -> None:
        """Adiciona evento ao historico interno, respeitando o limite configurado.

        Args:
            evento: Evento a adicionar ao historico.
        """
        with self._lock:
            # deque com maxlen gerencia automaticamente o limite de historico
            self._historico_eventos.append(evento)

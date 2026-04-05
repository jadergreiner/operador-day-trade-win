"""CoordinationManager — Coordenação de agentes de trading (BLID-041).

Monitora drawdowns individuais e conjuntos dos agentes RL em operação,
emitindo sinais de coordenação para ajuste de comportamento operacional:

    NORMAL           → todos os limites dentro do esperado
    MODO_CONSERVADOR → drawdown individual de algum agente ultrapassou o limiar
    MODO_DEFENSIVO   → drawdown conjunto ultrapassou o limiar de portfólio
    STOP_OPERACOES   → capital estimado abaixo do mínimo configurado

Mecanismo:
- Polling periódico via thread daemon com intervalo configurável
- Leitura SQLite read-only dos trades de hoje para cada agente
- Cálculo de drawdown máximo por equity curve
- Persistência atômica do sinal atual em JSON (write tmp → replace)
- Callbacks invocados quando sinal != NORMAL

Exemplo de uso::

    config = ConfiguracaoCoordinacao(
        drawdown_individual_pct=10.0,
        drawdown_conjunto_pct=15.0,
        capital_minimo_reais=500.0,
        capital_inicial_sessao_reais=5000.0,
    )
    manager = CoordinationManager(config=config)
    manager.registrar_callback(meu_callback)
    manager.iniciar()

    # ... operação normal ...

    manager.parar()
"""

from __future__ import annotations

import json
import logging
import sqlite3
import threading
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Callable, List, Optional

from config.settings import AGENT_MAGIC_NUMBERS

logger = logging.getLogger(__name__)

# Timeout em segundos para aguardar encerramento da thread daemon
_TIMEOUT_ENCERRAMENTO_THREAD: float = 5.0

# Query SQL de leitura dos trades do dia para um agente específico
_QUERY_TRADES_HOJE: str = (
    "SELECT profit_loss FROM trades "
    "WHERE magic_number = ? "
    "AND date(entry_time) = date('now','localtime') "
    "AND exit_time IS NOT NULL "
    "AND profit_loss IS NOT NULL "
    "ORDER BY exit_time ASC"
)


# ---------------------------------------------------------------------------
# Enum de sinais de coordenação
# ---------------------------------------------------------------------------


class CoordinationSignal(str, Enum):
    """Sinais de coordenação emitidos pelo CoordinationManager.

    Valores:
        NORMAL: Todos os limites dentro do esperado — operação normal.
        MODO_CONSERVADOR: Drawdown individual de algum agente ultrapassou o limiar.
        MODO_DEFENSIVO: Drawdown conjunto de portfólio ultrapassou o limiar.
        STOP_OPERACOES: Capital estimado abaixo do mínimo — parar operações.
    """

    NORMAL = "NORMAL"
    MODO_CONSERVADOR = "MODO_CONSERVADOR"
    MODO_DEFENSIVO = "MODO_DEFENSIVO"
    STOP_OPERACOES = "STOP_OPERACOES"


# ---------------------------------------------------------------------------
# Configuração
# ---------------------------------------------------------------------------


@dataclass
class ConfiguracaoCoordinacao:
    """Parâmetros de configuração do CoordinationManager.

    Atributos:
        drawdown_individual_pct: Limiar de drawdown individual (%) — padrão 10.0.
        drawdown_conjunto_pct: Limiar de drawdown conjunto de portfólio (%) — padrão 15.0.
        capital_minimo_reais: Capital mínimo em reais abaixo do qual STOP é emitido.
        capital_inicial_sessao_reais: Capital inicial da sessão para cálculo de drawdown.
        intervalo_polling_segundos: Intervalo de polling da thread daemon em segundos.
        agentes_monitorados: Lista de nomes de agentes a monitorar (devem estar em AGENT_MAGIC_NUMBERS).
        db_path: Caminho para o banco SQLite de trades.
        sinal_atual_path: Caminho do arquivo JSON com o sinal atual.
        log_dir: Diretório de logs.
    """

    drawdown_individual_pct: float = 10.0
    drawdown_conjunto_pct: float = 15.0
    capital_minimo_reais: float = 500.0
    capital_inicial_sessao_reais: float = 5000.0
    intervalo_polling_segundos: float = 60.0
    agentes_monitorados: List[str] = field(
        default_factory=lambda: ["rl_5000", "rl_direto"]
    )
    db_path: str = "data/db/trading.db"
    sinal_atual_path: str = "outputs/coordination_signal_current.json"
    log_dir: str = "outputs"

    def __post_init__(self) -> None:
        """Valida a consistência dos parâmetros de configuração."""
        if self.drawdown_individual_pct >= self.drawdown_conjunto_pct:
            raise ValueError(
                f"drawdown_individual_pct ({self.drawdown_individual_pct}) deve ser "
                f"estritamente menor que drawdown_conjunto_pct ({self.drawdown_conjunto_pct})"
            )
        if self.intervalo_polling_segundos <= 0:
            raise ValueError(
                f"intervalo_polling_segundos deve ser maior que zero, "
                f"recebido: {self.intervalo_polling_segundos}"
            )
        if self.capital_inicial_sessao_reais <= 0:
            raise ValueError(
                f"capital_inicial_sessao_reais deve ser maior que zero, "
                f"recebido: {self.capital_inicial_sessao_reais}"
            )
        if self.capital_minimo_reais <= 0:
            raise ValueError(
                f"capital_minimo_reais deve ser maior que zero, "
                f"recebido: {self.capital_minimo_reais}"
            )
        if self.capital_minimo_reais >= self.capital_inicial_sessao_reais:
            raise ValueError(
                f"capital_minimo_reais ({self.capital_minimo_reais}) deve ser "
                f"menor que capital_inicial_sessao_reais ({self.capital_inicial_sessao_reais})"
            )
        for nome_agente in self.agentes_monitorados:
            if nome_agente not in AGENT_MAGIC_NUMBERS:
                raise ValueError(
                    f"Agente '{nome_agente}' não encontrado em AGENT_MAGIC_NUMBERS. "
                    f"Agentes válidos: {list(AGENT_MAGIC_NUMBERS.keys())}"
                )


# ---------------------------------------------------------------------------
# Estado de um agente individual
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class EstadoAgente:
    """Snapshot imutável do estado de um agente lido do banco de dados.

    Atributos:
        nome: Nome do agente (ex: 'rl_5000').
        drawdown_pct: Drawdown máximo da sessão atual em percentual.
        pnl_total_reais: PnL acumulado da sessão em reais.
        total_trades: Número de trades fechados no dia.
    """

    nome: str
    drawdown_pct: float
    pnl_total_reais: float
    total_trades: int


# ---------------------------------------------------------------------------
# Decisão de coordenação
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class DecisaoCoordinacao:
    """Resultado imutável de um ciclo de coordenação.

    Atributos:
        ciclo_id: UUID4 único do ciclo.
        timestamp_iso: Timestamp ISO 8601 do momento da decisão.
        sinal: Sinal de coordenação emitido.
        drawdown_rl_5000_pct: Drawdown individual do agente rl_5000 (%).
        drawdown_rl_direto_pct: Drawdown individual do agente rl_direto (%).
        drawdown_conjunto_pct: Drawdown conjunto do portfólio (%).
        capital_estimado_reais: Capital estimado da sessão em reais.
        threshold_violado: Nome do threshold violado (ou None).
        agente_gatilho: Nome do agente que trigou o threshold (ou None).
        total_trades_rl_5000: Total de trades do agente rl_5000 no dia.
        total_trades_rl_direto: Total de trades do agente rl_direto no dia.
    """

    ciclo_id: str
    timestamp_iso: str
    sinal: CoordinationSignal
    drawdown_rl_5000_pct: float
    drawdown_rl_direto_pct: float
    drawdown_conjunto_pct: float
    capital_estimado_reais: float
    threshold_violado: Optional[str]
    agente_gatilho: Optional[str]
    total_trades_rl_5000: int
    total_trades_rl_direto: int

    def para_dict(self) -> dict[str, object]:
        """Serializa a decisão para dicionário compatível com JSON."""
        return {
            "schema_version": "1.0",
            "ciclo_id": self.ciclo_id,
            "timestamp_iso": self.timestamp_iso,
            "sinal": self.sinal.value,
            "drawdown_rl_5000_pct": self.drawdown_rl_5000_pct,
            "drawdown_rl_direto_pct": self.drawdown_rl_direto_pct,
            "drawdown_conjunto_pct": self.drawdown_conjunto_pct,
            "capital_estimado_reais": self.capital_estimado_reais,
            "threshold_violado": self.threshold_violado,
            "agente_gatilho": self.agente_gatilho,
            "total_trades_rl_5000": self.total_trades_rl_5000,
            "total_trades_rl_direto": self.total_trades_rl_direto,
        }


# ---------------------------------------------------------------------------
# Tipo de callback
# ---------------------------------------------------------------------------

CallbackCoordinacao = Callable[[DecisaoCoordinacao], None]


# ---------------------------------------------------------------------------
# Funções auxiliares de cálculo
# ---------------------------------------------------------------------------


def _calcular_drawdown(
    pnl_sequencia: List[float],
    capital_inicial: float,
) -> float:
    """Calcula o drawdown máximo da sequência de PnL em percentual.

    O drawdown é calculado como o maior recuo relativo ao capital inicial:
        drawdown = max((peak_acumulado - valley_acumulado) / capital_inicial)

    Args:
        pnl_sequencia: Lista de profit_loss individuais em ordem temporal.
        capital_inicial: Capital inicial da sessão para normalização.

    Returns:
        Drawdown máximo em percentual (ex: 14.0 para 14%). Zero se < 2 trades.
    """
    if len(pnl_sequencia) < 2:
        return 0.0

    pico_equity: float = capital_inicial
    drawdown_maximo: float = 0.0
    equity_acumulada: float = capital_inicial

    for pnl in pnl_sequencia:
        equity_acumulada += pnl
        if equity_acumulada > pico_equity:
            pico_equity = equity_acumulada
        recuo_atual = (pico_equity - equity_acumulada) / capital_inicial * 100.0
        if recuo_atual > drawdown_maximo:
            drawdown_maximo = recuo_atual

    return drawdown_maximo


def _calcular_drawdown_conjunto(
    pnl_rl_5000: List[float],
    pnl_rl_direto: List[float],
    capital_inicial: float,
) -> float:
    """Calcula o drawdown conjunto do portfólio combinando os trades de ambos agentes.

    Concatena apenas os trades de agentes que possuem >= 2 trades individualmente
    (mesma regra da spec: "Se total_trades < 2: drawdown = 0.0"), depois calcula
    o drawdown sobre a equity curve resultante.

    Args:
        pnl_rl_5000: Sequência de PnL do agente rl_5000.
        pnl_rl_direto: Sequência de PnL do agente rl_direto.
        capital_inicial: Capital inicial da sessão.

    Returns:
        Drawdown máximo conjunto em percentual. Zero se combinação < 2 trades.
    """
    # Apenas inclui trades de agentes que têm dados suficientes (>= 2 trades).
    # Nota: a concatenação preserva a ordem interna de cada agente (ORDER BY exit_time ASC
    # da query SQL), mas não garante interleaving temporal entre agentes diferentes.
    # Para fins de drawdown de portfólio, esta ordenação é considerada suficiente.
    pnl_conjunto: List[float] = []
    if len(pnl_rl_5000) >= 2:
        pnl_conjunto.extend(pnl_rl_5000)
    if len(pnl_rl_direto) >= 2:
        pnl_conjunto.extend(pnl_rl_direto)
    return _calcular_drawdown(pnl_conjunto, capital_inicial)


def _ler_trades_agente(
    db_path: str,
    magic_number: int,
) -> List[float]:
    """Lê os profit_loss dos trades de hoje para um agente do banco SQLite.

    Usa conexão read-only para não interferir com agentes em operação.
    Em caso de qualquer erro, retorna lista vazia e loga WARNING.

    Args:
        db_path: Caminho do arquivo SQLite.
        magic_number: Número mágico do agente (MT5 magic number).

    Returns:
        Lista de profit_loss em ordem temporal (ORDER BY exit_time ASC).
        Lista vazia em caso de erro de acesso ao banco.
    """
    try:
        uri_readonly = f"file:{db_path}?mode=ro"
        with sqlite3.connect(uri_readonly, uri=True, check_same_thread=False) as conn:
            conn.execute("PRAGMA busy_timeout = 30000")
            cursor = conn.execute(_QUERY_TRADES_HOJE, (magic_number,))
            linhas = cursor.fetchall()
        return [float(linha[0]) for linha in linhas]
    except sqlite3.OperationalError as erro:
        logger.warning(
            "[CoordinationManager] Banco inacessível para magic=%d — retornando zerado. Erro: %s",
            magic_number,
            erro,
        )
        return []
    except (sqlite3.DatabaseError, OSError) as erro:
        logger.warning(
            "[CoordinationManager] Erro ao ler trades magic=%d — retornando zerado. Erro: %s",
            magic_number,
            erro,
        )
        return []


def _determinar_sinal(
    capital_estimado: float,
    capital_minimo: float,
    drawdown_conjunto: float,
    threshold_conjunto: float,
    estados_agentes: List[EstadoAgente],
    threshold_individual: float,
) -> tuple[CoordinationSignal, Optional[str], Optional[str]]:
    """Determina o sinal de coordenação com base nos thresholds configurados.

    Prioridade decrescente:
        1. capital_estimado < capital_minimo    → STOP_OPERACOES
        2. drawdown_conjunto > threshold_conjunto → MODO_DEFENSIVO
        3. drawdown_individual > threshold_individual → MODO_CONSERVADOR
        4. Nenhum threshold violado             → NORMAL

    Args:
        capital_estimado: Capital estimado atual em reais.
        capital_minimo: Limite mínimo de capital em reais.
        drawdown_conjunto: Drawdown conjunto calculado (%).
        threshold_conjunto: Limiar de drawdown conjunto (%).
        estados_agentes: Lista de EstadoAgente com drawdowns individuais.
        threshold_individual: Limiar de drawdown individual (%).

    Returns:
        Tupla (sinal, threshold_violado, agente_gatilho).
    """
    # Prioridade 1: capital mínimo
    if capital_estimado < capital_minimo:
        logger.warning(
            "[CoordinationManager] threshold violado: capital_minimo "
            "| capital_estimado=%.2f < minimo=%.2f",
            capital_estimado,
            capital_minimo,
        )
        return CoordinationSignal.STOP_OPERACOES, "capital_minimo", None

    # Prioridade 2: drawdown conjunto
    if drawdown_conjunto > threshold_conjunto:
        logger.warning(
            "[CoordinationManager] threshold violado: drawdown_conjunto "
            "| drawdown=%.2f%% > limiar=%.2f%%",
            drawdown_conjunto,
            threshold_conjunto,
        )
        return CoordinationSignal.MODO_DEFENSIVO, "drawdown_conjunto", None

    # Prioridade 3: drawdown individual
    for estado in estados_agentes:
        if estado.drawdown_pct > threshold_individual:
            logger.warning(
                "[CoordinationManager] threshold violado: drawdown_individual "
                "| agente=%s | drawdown=%.2f%% > limiar=%.2f%%",
                estado.nome,
                estado.drawdown_pct,
                threshold_individual,
            )
            return CoordinationSignal.MODO_CONSERVADOR, "drawdown_individual", estado.nome

    # Nenhum threshold violado
    return CoordinationSignal.NORMAL, None, None


# ---------------------------------------------------------------------------
# Manager principal
# ---------------------------------------------------------------------------


class CoordinationManager:
    """Coordena os agentes de trading monitorando drawdowns e capital.

    Executa ciclos de avaliação periodicamente via thread daemon,
    emitindo sinais de coordenação e notificando callbacks registrados.

    Exemplo::

        manager = CoordinationManager(config=config)
        manager.registrar_callback(meu_handler)
        manager.iniciar()
        # ... operação normal ...
        manager.parar()
    """

    def __init__(self, config: ConfiguracaoCoordinacao) -> None:
        """Inicializa o manager com a configuração fornecida.

        Args:
            config: Parâmetros de coordenação e thresholds.
        """
        self._config = config
        self._ultimo_sinal: CoordinationSignal = CoordinationSignal.NORMAL
        self._callbacks: List[CallbackCoordinacao] = []
        self._lock = threading.Lock()
        self._ativo = False
        self._thread: Optional[threading.Thread] = None
        self._evento_parar = threading.Event()

        logger.info(
            "[CoordinationManager] Inicializado | agentes=%s | db=%s",
            config.agentes_monitorados,
            config.db_path,
        )

    # ------------------------------------------------------------------
    # Ciclo de vida
    # ------------------------------------------------------------------

    def iniciar(self) -> None:
        """Inicia a thread daemon de polling em background.

        Idempotente: chamadas subsequentes sem parar() são ignoradas.
        """
        with self._lock:
            if self._ativo:
                logger.debug(
                    "[CoordinationManager] Já ativo — ignorando segunda chamada a iniciar()"
                )
                return
            self._ativo = True
            self._evento_parar.clear()

        self._thread = threading.Thread(
            target=self._loop_polling,
            name="coordination-manager",
            daemon=True,
        )
        self._thread.start()
        logger.info("[CoordinationManager] Thread daemon iniciada")

    def parar(self) -> None:
        """Para a thread daemon de forma segura com timeout.

        Idempotente: chamadas após o encerramento são ignoradas.
        """
        with self._lock:
            if not self._ativo:
                return
            self._ativo = False

        self._evento_parar.set()
        if self._thread is not None:
            self._thread.join(timeout=_TIMEOUT_ENCERRAMENTO_THREAD)
            self._thread = None

        logger.info("[CoordinationManager] Thread daemon encerrada")

    def esta_ativo(self) -> bool:
        """Retorna True se a thread daemon está em execução.

        Returns:
            True se a thread está viva, False caso contrário.
        """
        thread = self._thread
        return thread is not None and thread.is_alive()

    # ------------------------------------------------------------------
    # Ciclo de avaliação
    # ------------------------------------------------------------------

    def executar_ciclo(self) -> DecisaoCoordinacao:
        """Executa um ciclo completo de avaliação de coordenação.

        Pode ser chamado diretamente (sem thread) para uso em testes ou
        em execução síncrona. A cada ciclo:
        1. Lê trades de hoje de cada agente do SQLite
        2. Calcula drawdowns individuais e conjunto
        3. Determina sinal de coordenação pelos thresholds
        4. Persiste sinal em JSON atômico
        5. Invoca callbacks se sinal != NORMAL
        6. Atualiza último sinal

        Returns:
            DecisaoCoordinacao com todos os campos preenchidos.
        """
        ciclo_id = str(uuid.uuid4())
        timestamp_iso = datetime.now().isoformat()
        capital_inicial = self._config.capital_inicial_sessao_reais

        # Leitura dos trades de cada agente
        pnl_5000: List[float] = []
        pnl_direto: List[float] = []

        for nome_agente in self._config.agentes_monitorados:
            magic = AGENT_MAGIC_NUMBERS[nome_agente]
            pnl_agente = _ler_trades_agente(self._config.db_path, magic)
            if nome_agente == "rl_5000":
                pnl_5000 = pnl_agente
            elif nome_agente == "rl_direto":
                pnl_direto = pnl_agente

        # Cálculo de drawdowns individuais
        drawdown_5000 = _calcular_drawdown(pnl_5000, capital_inicial)
        drawdown_direto = _calcular_drawdown(pnl_direto, capital_inicial)

        # Cálculo de drawdown conjunto
        drawdown_conjunto = _calcular_drawdown_conjunto(pnl_5000, pnl_direto, capital_inicial)

        # Capital estimado
        capital_estimado = capital_inicial + sum(pnl_5000) + sum(pnl_direto)

        # Estados dos agentes
        estado_5000 = EstadoAgente(
            nome="rl_5000",
            drawdown_pct=drawdown_5000,
            pnl_total_reais=sum(pnl_5000),
            total_trades=len(pnl_5000),
        )
        estado_direto = EstadoAgente(
            nome="rl_direto",
            drawdown_pct=drawdown_direto,
            pnl_total_reais=sum(pnl_direto),
            total_trades=len(pnl_direto),
        )

        # Determinação do sinal
        sinal, threshold_violado, agente_gatilho = _determinar_sinal(
            capital_estimado=capital_estimado,
            capital_minimo=self._config.capital_minimo_reais,
            drawdown_conjunto=drawdown_conjunto,
            threshold_conjunto=self._config.drawdown_conjunto_pct,
            estados_agentes=[estado_5000, estado_direto],
            threshold_individual=self._config.drawdown_individual_pct,
        )

        # Construção da decisão
        decisao = DecisaoCoordinacao(
            ciclo_id=ciclo_id,
            timestamp_iso=timestamp_iso,
            sinal=sinal,
            drawdown_rl_5000_pct=drawdown_5000,
            drawdown_rl_direto_pct=drawdown_direto,
            drawdown_conjunto_pct=drawdown_conjunto,
            capital_estimado_reais=capital_estimado,
            threshold_violado=threshold_violado,
            agente_gatilho=agente_gatilho,
            total_trades_rl_5000=len(pnl_5000),
            total_trades_rl_direto=len(pnl_direto),
        )

        # Persistência atômica do sinal
        self._persistir_sinal(decisao)

        # Atualização do último sinal
        with self._lock:
            self._ultimo_sinal = sinal

        # Disparo de callbacks apenas quando sinal != NORMAL
        if sinal != CoordinationSignal.NORMAL:
            self._disparar_callbacks(decisao)

        return decisao

    # ------------------------------------------------------------------
    # Consulta de estado
    # ------------------------------------------------------------------

    def obter_ultimo_sinal(self) -> CoordinationSignal:
        """Retorna o último sinal de coordenação emitido.

        Returns:
            CoordinationSignal mais recente. NORMAL antes do primeiro ciclo.
        """
        with self._lock:
            return self._ultimo_sinal

    # ------------------------------------------------------------------
    # Callbacks
    # ------------------------------------------------------------------

    def registrar_callback(self, cb: CallbackCoordinacao) -> None:
        """Registra função a ser invocada quando sinal != NORMAL.

        Args:
            cb: Função com assinatura (DecisaoCoordinacao) -> None.
        """
        with self._lock:
            self._callbacks.append(cb)
        logger.debug(
            "[CoordinationManager] Callback registrado | total=%d",
            len(self._callbacks),
        )

    # ------------------------------------------------------------------
    # Internos
    # ------------------------------------------------------------------

    def _loop_polling(self) -> None:
        """Loop principal da thread daemon — executa ciclos periodicamente."""
        logger.debug("[CoordinationManager] Loop de polling iniciado")
        while not self._evento_parar.wait(timeout=self._config.intervalo_polling_segundos):
            try:
                self.executar_ciclo()
            except Exception:  # noqa: BLE001
                logger.exception(
                    "[CoordinationManager] Erro inesperado no loop de polling"
                )
        logger.debug("[CoordinationManager] Loop de polling encerrado")

    def _persistir_sinal(self, decisao: DecisaoCoordinacao) -> None:
        """Persiste o sinal atual em JSON de forma atômica.

        Usa padrão write-tmp-then-replace para garantir que leitores externos
        nunca vejam arquivo parcialmente escrito.

        Args:
            decisao: Decisão a persistir.
        """
        try:
            caminho_sinal = Path(self._config.sinal_atual_path)
            caminho_sinal.parent.mkdir(parents=True, exist_ok=True)
            caminho_tmp = caminho_sinal.with_suffix(".tmp")
            conteudo = json.dumps(decisao.para_dict(), ensure_ascii=False)
            caminho_tmp.write_text(conteudo, encoding="utf-8")
            caminho_tmp.replace(caminho_sinal)
            logger.debug(
                "[CoordinationManager] Sinal persistido | sinal=%s | path=%s",
                decisao.sinal.value,
                caminho_sinal,
            )
        except OSError:
            logger.exception(
                "[CoordinationManager] Falha ao persistir sinal | path=%s",
                self._config.sinal_atual_path,
            )

    def _disparar_callbacks(self, decisao: DecisaoCoordinacao) -> None:
        """Invoca todos os callbacks registrados com a decisão.

        Exceptions em callbacks individuais são capturadas e logadas sem
        interromper os demais callbacks.

        Args:
            decisao: Decisão a entregar aos callbacks.
        """
        with self._lock:
            callbacks = list(self._callbacks)

        for callback in callbacks:
            try:
                callback(decisao)
            except Exception:  # noqa: BLE001
                logger.exception(
                    "[CoordinationManager] Erro em callback | callback=%r",
                    callback,
                )

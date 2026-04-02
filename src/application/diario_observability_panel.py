"""
ROADMAP-DIARIOS-01: Observabilidade e Watchdog dos Diarios

Responsabilidades:
- Rastrear ultimo timestamp de gravacao por diario
- Alertar quando diario ficar > limite_min sem gravar
- Exibir painel ASCII no terminal com status em tempo real
- Integrar com ThreadWatchdog para historico de restarts
- Persistir eventos de observabilidade no SQLite (v1.1)
- Exportar snapshot JSON atomico a cada 60s (v1.1)

Diarios monitorados (nomes canonicos):
    TradingJournal | AIReflection | RLDiary | MacroGuardian | DiarioExecucao

Pipeline:
    Diario grava -> registrar_gravacao(nome)
    -> verificar_alertas_inatividade()
    -> exibir_painel_terminal() a cada 60s
    -> _exportar_snapshot_json() a cada 60s

Status: Implementacao v1.1 (02/04/2026)
Referencia: docs/BACKLOG.md (ROADMAP-DIARIOS-01)
"""

from __future__ import annotations

import datetime
import json
import logging
import os
import uuid
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

from src.application.opening_context_report import load_latest_opening_context_report
from src.infrastructure.persistence.repositorio_watchdog_eventos import (
    RegistroEvento,
    RepositorioWatchdogEventos,
)

logger = logging.getLogger("diario_observability_panel")

# ─────────────────────────────────────────────────────────────────
# Constantes retrocompatíveis (nomes logicos antigos)
# ─────────────────────────────────────────────────────────────────

DIARIOS_MONITORADOS: list[str] = [
    "TradingJournal",
    "AIReflection",
    "RLDiary",
    "MacroGuardian",
    "DiarioExecucao",
]

# Nomes legados preservados para retrocompatibilidade com testes
# e consumidores antigos do painel v1.0.
DIARIOS_MONITORADOS_LEGADOS: list[str] = [
    "MICRO_TENDENCIA",
    "RL_5000",
    "RL_DIRETO",
    "DIARIOS",
]

TODOS_OS_NOMES_MONITORADOS: list[str] = list(
    dict.fromkeys(DIARIOS_MONITORADOS + DIARIOS_MONITORADOS_LEGADOS)
)

# Janela operacional padrao (BRT) — configuravel no construtor
JANELA_OPERACIONAL_PADRAO: tuple[str, str] = ("09:00", "17:30")

# Caminho padrao do banco SQLite dos diarios
CAMINHO_BANCO_DIARIOS_PADRAO: Path = Path("data/db/trading_diarios.db")

# Caminho padrao de exportacao JSON
CAMINHO_JSON_EXPORTACAO_PADRAO: Path = Path(
    "outputs/diarios/diarios_status_latest.json"
)


# ─────────────────────────────────────────────────────────────────
# Tipos de monitoramento
# ─────────────────────────────────────────────────────────────────

TIPO_GRAVACAO_E_HEARTBEAT = "GRAVACAO_E_HEARTBEAT"
TIPO_APENAS_HEARTBEAT = "APENAS_HEARTBEAT"


# ─────────────────────────────────────────────────────────────────
# Configuracao por thread (v1.1)
# ─────────────────────────────────────────────────────────────────


@dataclass(frozen=True)
class ConfiguracaoMonitoramento:
    """Configuracao de monitoramento de uma thread de diario.

    Args:
        nome_logico: Nome interno usado nos relatorios.
        cadencia_min: Cadencia esperada de gravacao em minutos.
        threshold_alerta_min: Minutos sem gravacao para emitir alerta.
        tipo_monitoramento: GRAVACAO_E_HEARTBEAT ou APENAS_HEARTBEAT.

    """

    nome_logico: str
    cadencia_min: int
    threshold_alerta_min: int
    tipo_monitoramento: str


# Mapeamento canonico: nome real da thread -> configuracao de monitoramento
# UNICA FONTE DE VERDADE para os 5 diarios do launcher.
MAPEAMENTO_THREADS_CANONICO: dict[str, ConfiguracaoMonitoramento] = {
    "TradingJournal": ConfiguracaoMonitoramento(
        nome_logico="TRADING_JOURNAL",
        cadencia_min=5,
        threshold_alerta_min=20,
        tipo_monitoramento=TIPO_GRAVACAO_E_HEARTBEAT,
    ),
    "AIReflection": ConfiguracaoMonitoramento(
        nome_logico="AI_REFLECTION",
        cadencia_min=10,
        threshold_alerta_min=20,
        tipo_monitoramento=TIPO_GRAVACAO_E_HEARTBEAT,
    ),
    "RLDiary": ConfiguracaoMonitoramento(
        nome_logico="RL_PERFORMANCE",
        cadencia_min=15,
        threshold_alerta_min=20,
        tipo_monitoramento=TIPO_GRAVACAO_E_HEARTBEAT,
    ),
    "MacroGuardian": ConfiguracaoMonitoramento(
        nome_logico="MACRO_GUARDIAN",
        cadencia_min=0,
        threshold_alerta_min=20,
        tipo_monitoramento=TIPO_GRAVACAO_E_HEARTBEAT,
    ),
    "DiarioExecucao": ConfiguracaoMonitoramento(
        nome_logico="DIARIO_EXECUCAO",
        cadencia_min=0,
        threshold_alerta_min=20,
        tipo_monitoramento=TIPO_APENAS_HEARTBEAT,
    ),
}


# ─────────────────────────────────────────────────────────────────
# Dataclasses de eventos e snapshots (v1.1)
# ─────────────────────────────────────────────────────────────────


@dataclass(frozen=True)
class EventoObservabilidadeDiario:
    """Registro imutavel de um evento de observabilidade de diario.

    Args:
        session_id: Identificador unico da sessao do painel.
        nome_thread: Nome real da thread (ex: 'TradingJournal').
        evento: Tipo (GRAVACAO/HEARTBEAT/FALHA/REINICIO/ALERTA).
        estado_resultante: Estado da thread apos o evento.
        mensagem: Mensagem de contexto opcional.
        stack_trace: Stack trace (apenas para FALHA).
        gravacoes_sessao: Total de gravacoes da sessao ate o evento.
        timestamp: Momento do evento.

    """

    session_id: str
    nome_thread: str
    evento: str
    estado_resultante: str
    mensagem: Optional[str]
    stack_trace: Optional[str]
    gravacoes_sessao: int
    timestamp: datetime.datetime


@dataclass
class StatusDiarioEstendido:
    """Estado detalhado de uma thread de diario (v1.1).

    Args:
        nome_thread: Nome real da thread.
        nome_logico: Nome interno usado nos relatorios.
        estado: Estado operacional atual (None antes do 1o sinal).
        ultimo_registro: Timestamp da ultima gravacao.
        ultimo_heartbeat: Timestamp do ultimo heartbeat.
        total_registros_sessao: Gravacoes acumuladas na sessao.
        restarts_sessao: Reinicializacoes na sessao.
        em_alerta: True se inatividade ultrapassou threshold.
        minutos_sem_gravacao: Minutos desde ultima gravacao.

    """

    nome_thread: str
    nome_logico: str
    estado: Optional[str] = None  # None = aguardando_sinal
    ultimo_registro: Optional[datetime.datetime] = None
    ultimo_heartbeat: Optional[datetime.datetime] = None
    total_registros_sessao: int = 0
    restarts_sessao: int = 0
    em_alerta: bool = False
    minutos_sem_gravacao: Optional[float] = None

    def para_dict(self) -> dict[str, object]:
        """Converte para dicionario JSON-serializavel.

        Returns:
            dict com todos os campos serializaveis.

        """
        return {
            "nome_thread": self.nome_thread,
            "nome_logico": self.nome_logico,
            "estado": self.estado,
            "ultimo_registro": (
                self.ultimo_registro.isoformat()
                if self.ultimo_registro
                else None
            ),
            "ultimo_heartbeat": (
                self.ultimo_heartbeat.isoformat()
                if self.ultimo_heartbeat
                else None
            ),
            "total_registros_sessao": self.total_registros_sessao,
            "restarts_sessao": self.restarts_sessao,
            "em_alerta": self.em_alerta,
            "minutos_sem_gravacao": self.minutos_sem_gravacao,
        }


@dataclass
class SnapshotSaudeDiario:
    """Snapshot consolidado de saude de todos os diarios.

    Args:
        session_id: Identificador da sessao do painel.
        timestamp_exportacao: Momento da geracao do snapshot.
        threads: Mapa de nome_thread -> StatusDiarioEstendido.

    """

    session_id: str
    timestamp_exportacao: datetime.datetime
    threads: dict[str, StatusDiarioEstendido] = field(default_factory=dict)

    def para_dict(self) -> dict[str, object]:
        """Converte para dicionario JSON-serializavel.

        Returns:
            dict com todos os campos, incluindo threads.

        """
        return {
            "session_id": self.session_id,
            "timestamp_exportacao": self.timestamp_exportacao.isoformat(),
            "threads": {
                nome: status.para_dict()
                for nome, status in self.threads.items()
            },
        }

_LARGURA_PAINEL = 60


@dataclass
class StatusDiario:
    """Estado de monitoramento de um diario especifico.

    Args:
        nome: Identificador do diario (ex: 'MICRO_TENDENCIA').
        ultimo_registro: Timestamp da ultima gravacao registrada.
        total_registros: Contador acumulado de gravacoes.
        em_alerta: True se diario ultrapassou limite de inatividade.

    """

    nome: str
    ultimo_registro: Optional[datetime.datetime] = None
    total_registros: int = 0
    em_alerta: bool = False


class ObservabilidadeDiarios:
    """Painel de observabilidade para os diarios do sistema.

    Rastreia o ultimo timestamp de gravacao de cada diario e
    emite alertas quando algum fica inativo por mais do que o
    limite configurado. Exibe painel ASCII para o terminal.

    v1.1: Estendido com mapeamento canonico de 5 threads, persistencia
    SQLite em diarios_watchdog_eventos, exportacao JSON atomica e
    maquina de estados operacionais por thread.

    Exemplo de uso:
        painel = ObservabilidadeDiarios(limite_inatividade_min=20)
        painel.registrar_gravacao("TradingJournal")
        painel.registrar_heartbeat("DiarioExecucao")
        snapshot = painel.gerar_snapshot_operacional()

    """

    def __init__(
        self,
        limite_inatividade_min: int = 20,
        report_dir: str | Path = "outputs/analysis",
        caminho_banco: str | Path = CAMINHO_BANCO_DIARIOS_PADRAO,
        caminho_json: str | Path = CAMINHO_JSON_EXPORTACAO_PADRAO,
        janela_operacional: tuple[str, str] = JANELA_OPERACIONAL_PADRAO,
    ) -> None:
        """Inicializa o painel com limite de inatividade configuravel.

        Args:
            limite_inatividade_min: Minutos sem gravacao para emitir alerta.
            report_dir: Diretorio com o relatorio consolidado latest.
            caminho_banco: Caminho para o SQLite de persistencia de eventos.
            caminho_json: Caminho de exportacao do snapshot JSON.
            janela_operacional: Tupla (HH:MM, HH:MM) inicio/fim pregao.

        """
        self._limite_min = limite_inatividade_min
        self._report_dir = Path(report_dir)
        # ── Estado retrocompat para nomes antigos ──────────────────────
        self._status: dict[str, StatusDiario] = {
            nome: StatusDiario(nome=nome) for nome in TODOS_OS_NOMES_MONITORADOS
        }
        self._historico_restarts: dict[str, int] = {
            nome: 0 for nome in TODOS_OS_NOMES_MONITORADOS
        }
        # ── v1.1: Estado estendido para 5 threads canonicas ────────────
        self._session_id: str = str(uuid.uuid4())
        self._status_estendido: dict[str, StatusDiarioEstendido] = {
            nome: StatusDiarioEstendido(
                nome_thread=nome,
                nome_logico=cfg.nome_logico,
            )
            for nome, cfg in MAPEAMENTO_THREADS_CANONICO.items()
        }
        self._caminho_json = Path(caminho_json)
        self._janela_operacional = janela_operacional
        # Repositorio SQLite com fail-open
        self._repositorio = RepositorioWatchdogEventos(caminho_banco)
        self._repositorio.inicializar()

    # ─────────────────────────────────────────────────────────────────
    # Metodos retrocompat (nomes antigos — DIARIOS_MONITORADOS)
    # ─────────────────────────────────────────────────────────────────

    def registrar_gravacao(self, nome_diario: str) -> None:
        """Registra uma gravacao bem-sucedida de um diario.

        Atualiza o timestamp de ultimo registro e incrementa o
        contador de gravacoes. Aceita tanto nomes legados
        (MICRO_TENDENCIA, RL_5000 etc.) quanto nomes canonicos
        (TradingJournal, AIReflection etc.).

        Args:
            nome_diario: Nome do diario que gravou dados.

        Raises:
            ValueError: Se nome_diario for canonical inexistente
                (nomes legados desconhecidos sao ignorados silenciosamente).

        """
        agora = datetime.datetime.now()

        # Verifica se e um nome canonico (v1.1)
        if nome_diario in self._status_estendido:
            self._registrar_gravacao_canonico(nome_diario)
            if nome_diario in self._status:
                status_retro = self._status[nome_diario]
                status_retro.ultimo_registro = agora
                status_retro.total_registros += 1
                status_retro.em_alerta = False
            return

        # Comportamento retrocompat: ignora nomes nao monitorados
        if nome_diario not in self._status:
            return
        status = self._status[nome_diario]
        status.ultimo_registro = agora
        status.total_registros += 1
        status.em_alerta = False

    # ─────────────────────────────────────────────────────────────────
    # Metodos canonicos v1.1 (5 threads: TradingJournal ... DiarioExecucao)
    # ─────────────────────────────────────────────────────────────────

    def registrar_heartbeat(self, nome_thread: str) -> None:
        """Registra que a thread esta viva sem contar como gravacao.

        Atualiza `ultimo_heartbeat` e estado para 'rodando'.
        Nao altera `total_registros_sessao` nem `ultimo_registro`.

        Args:
            nome_thread: Nome canonico da thread (ex: 'TradingJournal').

        Raises:
            ValueError: Se nome_thread nao estiver no mapeamento canonico.

        """
        self._validar_nome_canonico(nome_thread)
        status = self._status_estendido[nome_thread]
        agora = datetime.datetime.now()
        status.ultimo_heartbeat = agora
        # Transicao de estado
        if status.estado in (None, "pausado", "reiniciando"):
            status.estado = "rodando"
        elif status.estado == "com_erro":
            # com_erro nao va diretamente para rodando sem reiniciando
            pass  # permanece com_erro ate registrar_reinicio ser chamado

    def registrar_falha(
        self,
        nome_thread: str,
        excecao: BaseException,
        stack_trace: Optional[str],
    ) -> None:
        """Registra falha de uma thread, isolando seu estado como com_erro.

        Nao afeta o estado das demais threads.

        Args:
            nome_thread: Nome canonico da thread.
            excecao: Excecao que causou a falha.
            stack_trace: Stack trace formatado (pode ser None).

        Raises:
            ValueError: Se nome_thread nao estiver no mapeamento canonico.

        """
        self._validar_nome_canonico(nome_thread)
        status = self._status_estendido[nome_thread]
        status.estado = "com_erro"
        mensagem = f"{type(excecao).__name__}: {excecao}"
        registro = RegistroEvento(
            session_id=self._session_id,
            nome_thread=nome_thread,
            evento="FALHA",
            estado_resultante="com_erro",
            gravacoes_sessao=status.total_registros_sessao,
            mensagem=mensagem,
            stack_trace=stack_trace,
        )
        self._repositorio.inserir(registro)

    def registrar_reinicio(self, nome_thread: str) -> None:
        """Registra que o watchdog iniciou o reinicio de uma thread.

        Transiciona estado de com_erro para reiniciando.
        Deve ser chamado pelo ThreadWatchdog antes de relaunchar a thread.

        Args:
            nome_thread: Nome canonico da thread.

        Raises:
            ValueError: Se nome_thread nao estiver no mapeamento canonico.

        """
        self._validar_nome_canonico(nome_thread)
        status = self._status_estendido[nome_thread]
        status.estado = "reiniciando"
        status.restarts_sessao += 1
        registro = RegistroEvento(
            session_id=self._session_id,
            nome_thread=nome_thread,
            evento="REINICIO",
            estado_resultante="reiniciando",
            gravacoes_sessao=status.total_registros_sessao,
            mensagem=f"Reinicio #{status.restarts_sessao} iniciado pelo watchdog",
        )
        self._repositorio.inserir(registro)

    def gerar_snapshot_operacional(self) -> SnapshotSaudeDiario:
        """Gera snapshot consolidado de saude de todas as 5 threads.

        Calcula minutos_sem_gravacao para cada thread e verifica alertas.

        Returns:
            SnapshotSaudeDiario com estado atual de todas as threads.

        """
        agora = datetime.datetime.now()
        snapshot = SnapshotSaudeDiario(
            session_id=self._session_id,
            timestamp_exportacao=agora,
        )
        for nome, status in self._status_estendido.items():
            cfg = MAPEAMENTO_THREADS_CANONICO[nome]
            minutos: Optional[float] = None
            if status.ultimo_registro is not None:
                delta = agora - status.ultimo_registro
                minutos = delta.total_seconds() / 60.0
            em_alerta = self._calcular_alerta(nome, status, agora)
            status.em_alerta = em_alerta
            status.minutos_sem_gravacao = minutos
            snapshot.threads[nome] = status
        return snapshot

    def verificar_alertas_inatividade_canonico(self) -> list[str]:
        """Verifica alertas de inatividade para as 5 threads canonicas.

        So gera alerta dentro da janela operacional e para threads
        com tipo_monitoramento == GRAVACAO_E_HEARTBEAT.

        Returns:
            Lista de nomes de threads com alerta de inatividade.

        """
        agora = datetime.datetime.now()
        if not self._dentro_janela_operacional(agora):
            return []
        alertas: list[str] = []
        for nome, status in self._status_estendido.items():
            if self._calcular_alerta(nome, status, agora):
                alertas.append(nome)
                logger.warning(
                    "[Observabilidade] Thread '%s' em alerta de inatividade."
                    " Ultimo registro: %s | Minutos sem gravacao: %.1f",
                    nome,
                    status.ultimo_registro,
                    (agora - status.ultimo_registro).total_seconds() / 60.0
                    if status.ultimo_registro
                    else float("inf"),
                )
        return alertas

    def exportar_snapshot_json(
        self,
        caminho_destino: Optional[Path] = None,
    ) -> None:
        """Exporta snapshot de saude no formato JSON de forma atomica.

        Escreve em arquivo .tmp e renomeia para o destino final, evitando
        arquivo corrompido em caso de crash. Usa estado em memoria se
        SQLite estiver indisponivel, marcando "fonte": "memoria".

        Args:
            caminho_destino: Caminho final do JSON. Usa padrao se None.

        """
        destino = caminho_destino or self._caminho_json
        snapshot = self.gerar_snapshot_operacional()
        payload = snapshot.para_dict()
        payload["fonte"] = (
            "sqlite" if self._repositorio.disponivel else "memoria"
        )
        tmp = destino.with_suffix(".tmp")
        try:
            destino.parent.mkdir(parents=True, exist_ok=True)
            tmp.write_text(json.dumps(payload, ensure_ascii=False, indent=2))
            os.replace(str(tmp), str(destino))
        except OSError as exc:
            logger.warning(
                "[Observabilidade] Falha ao exportar JSON para '%s': %s.",
                destino,
                exc,
            )

    # ─────────────────────────────────────────────────────────────────
    # Metodos internos
    # ─────────────────────────────────────────────────────────────────

    def _validar_nome_canonico(self, nome_thread: str) -> None:
        """Valida que nome_thread pertence ao mapeamento canonico.

        Args:
            nome_thread: Nome a validar.

        Raises:
            ValueError: Se nome nao reconhecido no mapeamento canonico.

        """
        if nome_thread not in MAPEAMENTO_THREADS_CANONICO:
            nomes_validos = ", ".join(sorted(MAPEAMENTO_THREADS_CANONICO))
            raise ValueError(
                f"Thread '{nome_thread}' nao reconhecida no mapeamento "
                f"canonico. Nomes validos: {nomes_validos}"
            )

    def _registrar_gravacao_canonico(self, nome_thread: str) -> None:
        """Registra gravacao no estado estendido e persiste no SQLite.

        Args:
            nome_thread: Nome canonico da thread.

        """
        status = self._status_estendido[nome_thread]
        agora = datetime.datetime.now()
        status.ultimo_registro = agora
        status.total_registros_sessao += 1
        status.estado = "rodando"
        status.em_alerta = False
        status.ultimo_heartbeat = agora  # gravacao implica heartbeat
        registro = RegistroEvento(
            session_id=self._session_id,
            nome_thread=nome_thread,
            evento="GRAVACAO",
            estado_resultante="rodando",
            gravacoes_sessao=status.total_registros_sessao,
        )
        self._repositorio.inserir(registro)

    def _calcular_alerta(
        self,
        nome: str,
        status: StatusDiarioEstendido,
        agora: datetime.datetime,
    ) -> bool:
        """Calcula se thread esta em alerta de inatividade.

        Args:
            nome: Nome canonico da thread.
            status: Estado atual da thread.
            agora: Momento da verificacao.

        Returns:
            True se thread deve emitir alerta de inatividade.

        """
        cfg = MAPEAMENTO_THREADS_CANONICO[nome]
        if cfg.tipo_monitoramento == TIPO_APENAS_HEARTBEAT:
            return False
        if status.ultimo_registro is None:
            return False
        threshold = datetime.timedelta(minutes=cfg.threshold_alerta_min)
        return (agora - status.ultimo_registro) > threshold

    def _dentro_janela_operacional(self, agora: datetime.datetime) -> bool:
        """Verifica se horario atual esta dentro da janela de pregao.

        Args:
            agora: Momento atual.

        Returns:
            True se dentro da janela operacional configurada.

        """
        inicio_str, fim_str = self._janela_operacional
        hi, mi = (int(x) for x in inicio_str.split(":"))
        hf, mf = (int(x) for x in fim_str.split(":"))
        t_inicio = agora.replace(hour=hi, minute=mi, second=0, microsecond=0)
        t_fim = agora.replace(hour=hf, minute=mf, second=0, microsecond=0)
        return t_inicio <= agora <= t_fim

    # ─────────────────────────────────────────────────────────────────
    # Metodos retrocompat (nomes antigos — DIARIOS_MONITORADOS)
    # ─────────────────────────────────────────────────────────────────

    def verificar_alertas_inatividade(self) -> list[str]:
        agora = datetime.datetime.now()
        limite_delta = datetime.timedelta(minutes=self._limite_min)
        alertas: list[str] = []

        for nome, status in self._status.items():
            if status.ultimo_registro is None:
                # Nunca gravou — nao alerta ate ter referencia
                continue
            tempo_inativo = agora - status.ultimo_registro
            if tempo_inativo > limite_delta:
                status.em_alerta = True
                alertas.append(nome)
            else:
                status.em_alerta = False

        return alertas

    def exibir_painel_terminal(self) -> str:
        """Gera o painel ASCII com status das 5 threads canonicas.

        Produz uma string formatada com cabecalho, estado operacional
        de cada thread e indicadores visuais (RODANDO / ALERTA /
        COM_ERRO / AGUARDANDO).

        Returns:
            String com o painel pronto para impressao no terminal.

        """
        agora = datetime.datetime.now()
        self.verificar_alertas_inatividade_canonico()
        alertas_legados = self.verificar_alertas_inatividade()

        linhas: list[str] = []
        separador = "=" * _LARGURA_PAINEL
        separador_fino = "-" * _LARGURA_PAINEL

        linhas.append(separador)
        linhas.append(
            " PAINEL DE OBSERVABILIDADE — DIARIOS".center(_LARGURA_PAINEL)
        )
        linhas.append(
            f" Atualizado: {agora.strftime('%d/%m/%Y %H:%M:%S')}".center(
                _LARGURA_PAINEL
            )
        )
        linhas.append(separador)

        _MAPA_ESTADO: dict[Optional[str], str] = {
            "rodando": "[+] RODANDO",
            "pausado": "[~] PAUSADO",
            "reiniciando": "[~] REINICIANDO",
            "com_erro": "[!] COM_ERRO",
            None: "[ ] AGUARDANDO",
        }

        for nome, status in self._status_estendido.items():
            estado_str = _MAPA_ESTADO.get(status.estado, f"[?] {status.estado}")
            if status.em_alerta:
                estado_str = "[!] ALERTA"
            tempo_grav = _formatar_inatividade(agora, status.ultimo_registro)
            tempo_hb = _formatar_inatividade(agora, status.ultimo_heartbeat)
            linha = (
                f"  {nome:<18} {estado_str:<15}"
                f" | grav: {tempo_grav:<9}"
                f" | hb: {tempo_hb:<9}"
                f" | n: {status.total_registros_sessao}"
                f" | reinit: {status.restarts_sessao}"
            )
            linhas.append(linha)

        linhas.append(separador_fino)
        linhas.append(
            f"  Limite inatividade: {self._limite_min} min"
            f"  |  Threads monitoradas: {len(self._status_estendido)}"
        )
        if alertas_legados:
            linhas.append(
                "  ALERTA legado ativo em: " + ", ".join(alertas_legados)
            )
        report_payload = load_latest_opening_context_report(self._report_dir)
        if report_payload:
            generated_at = str(report_payload.get("generated_at", "") or "")
            generated_suffix = generated_at[11:19] if len(generated_at) >= 19 else "N/D"
            linhas.append(separador_fino)
            linhas.append(
                "  Contexto x resultado latest: "
                f"{report_payload.get('target_date', 'N/D')}"
            )
            linhas.append(
                "  Agentes: "
                f"{report_payload.get('total_agents', 0)}"
                " | Trades: "
                f"{report_payload.get('total_trades_closed', 0)}"
                " | PnL: "
                f"R$ {float(report_payload.get('total_pnl', 0.0) or 0.0):.2f}"
            )
            linhas.append(f"  Gerado em: {generated_suffix}")
        linhas.append(separador)

        return "\n".join(linhas)

    def historico_restarts_por_diario(self) -> dict[str, int]:
        """Retorna o historico de restarts registrados por diario.

        Returns:
            dict mapeando nome do diario para numero de restarts.

        """
        return dict(self._historico_restarts)

    def registrar_restart(self, nome_diario: str) -> None:
        """Incrementa o contador de restarts de um diario.

        Args:
            nome_diario: Nome do diario que foi reiniciado.

        """
        if nome_diario in self._historico_restarts:
            self._historico_restarts[nome_diario] += 1

    def obter_status(self, nome_diario: str) -> StatusDiario:
        """Retorna o objeto StatusDiario de um diario especifico.

        Args:
            nome_diario: Nome do diario a consultar.

        Returns:
            StatusDiario com informacoes do diario.

        Raises:
            KeyError: Se o diario nao estiver na lista monitorada.

        """
        return self._status[nome_diario]


def _formatar_inatividade(
    agora: datetime.datetime,
    ultimo: Optional[datetime.datetime],
) -> str:
    """Formata o tempo de inatividade em string legivel.

    Args:
        agora: Timestamp atual.
        ultimo: Timestamp do ultimo registro (pode ser None).

    Returns:
        String como '5m30s' ou '---' se ultimo for None.

    """
    if ultimo is None:
        return "---"
    delta = agora - ultimo
    total_seg = int(delta.total_seconds())
    minutos = total_seg // 60
    segundos = total_seg % 60
    return f"{minutos}m{segundos:02d}s"

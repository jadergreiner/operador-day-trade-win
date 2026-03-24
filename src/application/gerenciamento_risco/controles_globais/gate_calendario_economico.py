"""
GateCalendarioEconomico: Bloqueia operacoes proximas a eventos economicos.

Responsabilidades:
- Consultar provider de calendario economico
- Bloquear novas entradas quando evento iminente (< minutos_antes_fechar)
- Sinalizar fechamento de posicoes antes do evento
- Bloquear reabertura apos evento por minutos_apos_abrir
- Fail-open: provider offline ou com erro nao bloqueia operacoes

Logica temporal:
    [evento - minutos_antes_fechar] → deve_fechar_posicoes=True, aprovado=False
    [evento]                        → bloqueado
    [evento + minutos_apos_abrir]   → aprovado=True novamente

Pipeline:
    GerenciadorRiscoExterno.avaliar_todos()
    → GateCalendarioEconomico.verificar()
    → ResultadoCalendario.aprovado_abertura determina EXECUTE/REJECT no AC4
    → ResultadoCalendario.deve_fechar_posicoes propaga para loop do agente

Status: v1.0 (24/03/2026)
Referencia: docs/BACKLOG.md (Camada Risco Externo - Calendario)
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone

from src.infrastructure.providers.calendario_economico_provider import (
    ICalendarioEconomicoProvider,
)

logger = logging.getLogger(__name__)


@dataclass
class ResultadoCalendario:
    """
    Resultado da verificacao do calendario economico.

    Atributos:
        aprovado_abertura: True se novas posicoes podem ser abertas agora.
        deve_fechar_posicoes: True quando evento iminente e posicoes devem ser fechadas.
        eventos_proximos: Nomes dos eventos que causaram bloqueio.
        motivo: Descricao textual da decisao.
    """

    aprovado_abertura: bool
    deve_fechar_posicoes: bool
    eventos_proximos: list[str] = field(default_factory=list)
    motivo: str = ""


class GateCalendarioEconomico:
    """
    Bloqueia novas entradas e sinaliza fechamento antes de eventos economicos.

    Usa o provider injetado para obter a lista de eventos proximos.
    Qualquer excecao do provider e capturada e trata como fail-open.

    Exemplo de uso:
        provider = CalendarioEconomicoFinnhub(api_key=os.environ["FINNHUB_API_KEY"])
        gate = GateCalendarioEconomico(provider=provider)
        resultado = gate.verificar()
        if resultado.deve_fechar_posicoes:
            # fechar posicoes abertas
        if not resultado.aprovado_abertura:
            # bloquear nova entrada
    """

    def __init__(
        self,
        provider: ICalendarioEconomicoProvider,
        minutos_antes_fechar: int = 5,
        minutos_apos_abrir: int = 2,
    ) -> None:
        self._provider = provider
        self._minutos_antes_fechar = minutos_antes_fechar
        self._minutos_apos_abrir = minutos_apos_abrir

    def verificar(self) -> ResultadoCalendario:
        """
        Verifica o calendario e decide sobre abertura/fechamento de posicoes.

        Returns:
            ResultadoCalendario com aprovado_abertura e deve_fechar_posicoes.
        """
        try:
            # Eventos futuros proximos (iminentes)
            janela = self._minutos_antes_fechar + 10
            eventos_futuros = self._provider.obter_proximos_eventos(
                janela_minutos=janela
            )
            # Eventos recentemente ocorridos (janela pos-evento)
            eventos_recentes = self._provider.obter_eventos_recentes(
                janela_passado_minutos=self._minutos_apos_abrir + 1
            )
            eventos = eventos_futuros + eventos_recentes
        except Exception as e:
            logger.warning(
                "Erro no provider de calendario — fail-open: %s", e
            )
            return ResultadoCalendario(
                aprovado_abertura=True,
                deve_fechar_posicoes=False,
                motivo="Provider de calendario indisponivel — operacoes liberadas (fail-open)",
            )

        agora = datetime.now(tz=timezone.utc)
        bloqueantes: list[str] = []
        deve_fechar = False

        for evento in eventos:
            ts = evento.timestamp_evento
            if ts.tzinfo is None:
                ts = ts.replace(tzinfo=timezone.utc)

            janela_antes = ts - timedelta(minutes=self._minutos_antes_fechar)
            janela_apos = ts + timedelta(minutes=self._minutos_apos_abrir)

            # Dentro da janela de bloqueio: [ts - antes] ate [ts + apos]
            if janela_antes <= agora <= janela_apos:
                bloqueantes.append(evento.nome)
                if agora < ts:
                    # Antes do evento: sinalizar fechamento
                    deve_fechar = True

        if not bloqueantes:
            return ResultadoCalendario(
                aprovado_abertura=True,
                deve_fechar_posicoes=False,
                eventos_proximos=[],
                motivo="Nenhum evento economico relevante proximo",
            )

        nomes = ", ".join(bloqueantes)
        motivo = (
            f"Evento(s) economico(s) iminente(s): {nomes} — "
            f"novas entradas bloqueadas"
        )
        if deve_fechar:
            motivo += " e fechamento de posicoes recomendado"

        logger.info(motivo)
        return ResultadoCalendario(
            aprovado_abertura=False,
            deve_fechar_posicoes=deve_fechar,
            eventos_proximos=bloqueantes,
            motivo=motivo,
        )

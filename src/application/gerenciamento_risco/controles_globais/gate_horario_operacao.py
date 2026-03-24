"""
GateHorarioOperacao: Controla abertura/fechamento de posicoes por horario.

Responsabilidades:
- Bloquear abertura de novas posicoes fora da janela hora_inicio/hora_fim
- Sinalizar fechamento de posicoes abertas quando hora_fim e atingida
- Usar fuso horario America/Sao_Paulo (B3)
- Aceitar injecao de funcao _agora para testes deterministas

Comportamento no fim do pregao:
    aprovado_abertura=False  (bloqueia novas ordens)
    deve_fechar_posicoes=True  (sinaliza agentes para fechar posicoes abertas)

Pipeline:
    GerenciadorRiscoExterno.avaliar_todos()
    → GateHorarioOperacao.verificar()
    → ResultadoHorario.aprovado_abertura determina EXECUTE/REJECT no AC4
    → ResultadoHorario.deve_fechar_posicoes propaga para loop do agente

    GerenciadorRiscoExterno.deve_fechar_posicoes_agora()
    → loop principal do agente verifica e fecha posicoes

Status: v1.0 (24/03/2026)
Referencia: docs/BACKLOG.md (Camada Risco Externo - Horario)
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import datetime, time, timezone
from typing import Callable, Optional
from zoneinfo import ZoneInfo

from src.domain.value_objects.risco_externo import ConfiguracaoHorario

logger = logging.getLogger(__name__)


@dataclass
class ResultadoHorario:
    """
    Resultado da verificacao de horario de operacao.

    Atributos:
        aprovado_abertura: True se novas posicoes podem ser abertas agora.
        deve_fechar_posicoes: True quando passou hora_fim e fechar_posicao_no_fim=True.
        horario_atual: Horario local no fuso configurado.
        motivo: Descricao textual da decisao.
    """

    aprovado_abertura: bool
    deve_fechar_posicoes: bool
    horario_atual: time
    motivo: str


class GateHorarioOperacao:
    """
    Controla abertura e fechamento de posicoes por horario de pregao.

    Fuso horario padrao: America/Sao_Paulo (UTC-3/UTC-2 no horario de verao).

    Para testes, injete _agora com um callable que retorna datetime fixo:
        gate = GateHorarioOperacao(config, _agora=lambda: datetime(2026,3,24,17,5,...))

    Exemplo de uso em producao:
        gate = GateHorarioOperacao(config)
        resultado = gate.verificar()
        if not resultado.aprovado_abertura:
            # rejeitar nova entrada
        if resultado.deve_fechar_posicoes:
            # fechar posicoes abertas
    """

    def __init__(
        self,
        configuracao: ConfiguracaoHorario,
        _agora: Optional[Callable[[], datetime]] = None,
    ) -> None:
        self._configuracao = configuracao
        self._tz = ZoneInfo(configuracao.fuso_horario)
        self._agora = _agora or self._agora_real

    def verificar(self) -> ResultadoHorario:
        """
        Verifica o horario atual e decide sobre abertura/fechamento de posicoes.

        Returns:
            ResultadoHorario com aprovado_abertura e deve_fechar_posicoes.
        """
        agora = self._agora()
        # Converter para o fuso horario configurado se necessario
        if agora.tzinfo is None:
            agora = agora.replace(tzinfo=self._tz)
        elif agora.tzinfo != self._tz:
            agora = agora.astimezone(self._tz)

        horario_atual = agora.time().replace(microsecond=0)
        hora_inicio = self._configuracao.hora_inicio
        hora_fim = self._configuracao.hora_fim

        dentro_da_janela = hora_inicio <= horario_atual < hora_fim
        apos_fim = horario_atual >= hora_fim

        if dentro_da_janela:
            return ResultadoHorario(
                aprovado_abertura=True,
                deve_fechar_posicoes=False,
                horario_atual=horario_atual,
                motivo=(
                    f"Horario {horario_atual.strftime('%H:%M')} dentro da janela "
                    f"{hora_inicio.strftime('%H:%M')}-{hora_fim.strftime('%H:%M')}"
                ),
            )

        if apos_fim:
            deve_fechar = self._configuracao.fechar_posicao_no_fim
            aprovado = not self._configuracao.bloquear_abertura_apos_fim

            motivo_bloqueio = (
                f"Horario {horario_atual.strftime('%H:%M')} apos fim do pregao "
                f"({hora_fim.strftime('%H:%M')})"
            )
            if deve_fechar:
                motivo_bloqueio += " — posicoes abertas devem ser encerradas"

            logger.info(motivo_bloqueio)
            return ResultadoHorario(
                aprovado_abertura=aprovado,
                deve_fechar_posicoes=deve_fechar,
                horario_atual=horario_atual,
                motivo=motivo_bloqueio,
            )

        # Antes do inicio
        return ResultadoHorario(
            aprovado_abertura=False,
            deve_fechar_posicoes=False,
            horario_atual=horario_atual,
            motivo=(
                f"Horario {horario_atual.strftime('%H:%M')} anterior ao inicio do pregao "
                f"({hora_inicio.strftime('%H:%M')})"
            ),
        )

    def _agora_real(self) -> datetime:
        """Retorna o datetime atual no fuso configurado."""
        return datetime.now(tz=self._tz)

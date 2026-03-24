"""
GerenciadorRiscoExterno: Facade que agrega todos os controles de risco externo.

Responsabilidades:
- Orquestrar avaliacao sequencial dos 6 gates de risco
- Retornar resultado consolidado para injecao no AC4
- Notificar controles internos apos fechamento de posicao
- Expor sinal de fechamento imediato para loop do agente

Ordem de avaliacao (fail-fast: para no primeiro gate reprovado):
    1. GateUnicaOrdemPorAgente  — agente ja tem posicao aberta?
    2. GerenciadorCooldown      — cooldown ainda ativo?
    3. ValidadorSLMaximo        — SL excede perda maxima?
    4. GateHorarioOperacao      — fora do horario de pregao?
    5. GateCalendarioEconomico  — evento economico iminente?
    6. LimitadorGanhoDiario     — limite de ganho diario atingido?

Fail-safe: excecoes internas em gates individuais sao capturadas e
tratadas como REPROVADO com codigo "GATE_ERRO_INTERNO".

Pipeline de integracao com AC4:
    DecisionFilter.make_decision(signal)
    → GerenciadorRiscoExterno.avaliar_todos(agent_id, sinal)
    → ResultadoAvaliacaoRisco.aprovado
    → DecisionType.EXECUTE ou REJECT

Notificacao de fechamento (apos AC5.8 fechar posicao):
    GerenciadorRiscoExterno.notificar_fechamento(agent_id, pnl_reais)
    → GerenciadorCooldown.registrar_fechamento()
    → LimitadorGanhoDiario.registrar_resultado()

Status: v1.0 (24/03/2026)
Referencia: docs/BACKLOG.md (Camada Risco Externo)
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any, Optional

from src.application.gerenciamento_risco.controles_agente.gate_unica_ordem import (
    GateUnicaOrdemPorAgente,
)
from src.application.gerenciamento_risco.controles_agente.gerenciador_cooldown import (
    GerenciadorCooldown,
)
from src.application.gerenciamento_risco.controles_agente.validador_sl_maximo import (
    ValidadorSLMaximo,
)
from src.application.gerenciamento_risco.controles_globais.gate_calendario_economico import (
    GateCalendarioEconomico,
)
from src.application.gerenciamento_risco.controles_globais.gate_horario_operacao import (
    GateHorarioOperacao,
)
from src.application.gerenciamento_risco.controles_globais.limitador_ganho_diario import (
    LimitadorGanhoDiario,
)
from src.domain.value_objects.risco_externo import ResultadoGateRisco

logger = logging.getLogger(__name__)


@dataclass
class ResultadoAvaliacaoRisco:
    """
    Resultado consolidado da avaliacao de todos os gates de risco externo.

    Atributos:
        aprovado: True se todos os gates aprovaram a operacao.
        gates_avaliados: Lista de resultados individuais de cada gate.
        primeiro_gate_reprovado: Codigo do primeiro gate que reprovou (ou None).
        motivo: Descricao textual da decisao final.
    """

    aprovado: bool
    gates_avaliados: list[ResultadoGateRisco] = field(default_factory=list)
    primeiro_gate_reprovado: Optional[str] = None
    motivo: str = ""


class GerenciadorRiscoExterno:
    """
    Facade que agrega e orquestra todos os controles de risco externo.

    Todos os seis gates sao avaliados em ordem com fail-fast:
    a avaliacao para no primeiro gate reprovado.

    Para o ValidadorSLMaximo, os parametros de preco/SL/volume sao
    extraidos do dicionario 'sinal' com as chaves:
        - 'entry_price' ou 'preco_entrada': float
        - 'stop_loss': float
        - 'volume': float (default 1.0 se ausente)

    Exemplo de uso:
        gerenciador = GerenciadorRiscoExterno(
            gate_unica_ordem=GateUnicaOrdemPorAgente(),
            gerenciador_cooldown=GerenciadorCooldown(config_cooldown),
            validador_sl=ValidadorSLMaximo(config_sl),
            gate_horario=GateHorarioOperacao(config_horario),
            gate_calendario=GateCalendarioEconomico(provider),
            limitador_ganho=LimitadorGanhoDiario(config_ganho, repositorio),
        )
        resultado = gerenciador.avaliar_todos("agente_rl_5000", sinal)
        if not resultado.aprovado:
            # rejeitar entrada
    """

    def __init__(
        self,
        gate_unica_ordem: GateUnicaOrdemPorAgente,
        gerenciador_cooldown: GerenciadorCooldown,
        validador_sl: ValidadorSLMaximo,
        gate_horario: GateHorarioOperacao,
        gate_calendario: GateCalendarioEconomico,
        limitador_ganho: LimitadorGanhoDiario,
    ) -> None:
        self._gate_unica_ordem = gate_unica_ordem
        self._gerenciador_cooldown = gerenciador_cooldown
        self._validador_sl = validador_sl
        self._gate_horario = gate_horario
        self._gate_calendario = gate_calendario
        self._limitador_ganho = limitador_ganho

    def avaliar_todos(
        self,
        agent_id: str,
        sinal: dict[str, Any],
    ) -> ResultadoAvaliacaoRisco:
        """
        Avalia todos os gates em ordem, com fail-fast no primeiro reprovado.

        Args:
            agent_id: Identificador do agente solicitando a operacao.
            sinal: Dicionario com dados do sinal (entry_price, stop_loss, volume...).

        Returns:
            ResultadoAvaliacaoRisco com aprovado=True apenas se todos passaram.
        """
        gates_avaliados: list[ResultadoGateRisco] = []

        # --- Gate 1: Unica ordem por agente ---
        resultado = self._avaliar_gate_seguro(
            codigo="UNICA_ORDEM",
            fn=lambda: self._gate_unica_ordem.verificar(agent_id),
        )
        gates_avaliados.append(resultado)
        if not resultado.aprovado:
            return ResultadoAvaliacaoRisco(
                aprovado=False,
                gates_avaliados=gates_avaliados,
                primeiro_gate_reprovado="UNICA_ORDEM",
                motivo=resultado.motivo,
            )

        # --- Gate 2: Cooldown ---
        resultado_cd = self._gerenciador_cooldown.verificar_cooldown(agent_id)
        resultado = ResultadoGateRisco(
            aprovado=resultado_cd.aprovado,
            codigo_gate="COOLDOWN",
            motivo=resultado_cd.motivo,
            detalhes={
                "segundos_restantes": resultado_cd.segundos_restantes,
                "agent_id": agent_id,
            },
        )
        gates_avaliados.append(resultado)
        if not resultado.aprovado:
            return ResultadoAvaliacaoRisco(
                aprovado=False,
                gates_avaliados=gates_avaliados,
                primeiro_gate_reprovado="COOLDOWN",
                motivo=resultado.motivo,
            )

        # --- Gate 3: SL maximo ---
        resultado = self._avaliar_sl(sinal)
        gates_avaliados.append(resultado)
        if not resultado.aprovado:
            return ResultadoAvaliacaoRisco(
                aprovado=False,
                gates_avaliados=gates_avaliados,
                primeiro_gate_reprovado="SL_MAXIMO",
                motivo=resultado.motivo,
            )

        # --- Gate 4: Horario ---
        resultado = self._avaliar_gate_seguro(
            codigo="HORARIO",
            fn=lambda: self._converter_horario(),
        )
        gates_avaliados.append(resultado)
        if not resultado.aprovado:
            return ResultadoAvaliacaoRisco(
                aprovado=False,
                gates_avaliados=gates_avaliados,
                primeiro_gate_reprovado="HORARIO",
                motivo=resultado.motivo,
            )

        # --- Gate 5: Calendario ---
        resultado = self._avaliar_gate_seguro(
            codigo="CALENDARIO",
            fn=lambda: self._converter_calendario(),
        )
        gates_avaliados.append(resultado)
        if not resultado.aprovado:
            return ResultadoAvaliacaoRisco(
                aprovado=False,
                gates_avaliados=gates_avaliados,
                primeiro_gate_reprovado="CALENDARIO",
                motivo=resultado.motivo,
            )

        # --- Gate 6: Ganho diario ---
        resultado = self._avaliar_gate_seguro(
            codigo="GANHO_DIARIO",
            fn=lambda: self._converter_ganho_diario(),
        )
        gates_avaliados.append(resultado)
        if not resultado.aprovado:
            return ResultadoAvaliacaoRisco(
                aprovado=False,
                gates_avaliados=gates_avaliados,
                primeiro_gate_reprovado="GANHO_DIARIO",
                motivo=resultado.motivo,
            )

        logger.debug(
            "Todos os %d gates aprovados para agent_id=%s",
            len(gates_avaliados),
            agent_id,
        )
        return ResultadoAvaliacaoRisco(
            aprovado=True,
            gates_avaliados=gates_avaliados,
            primeiro_gate_reprovado=None,
            motivo="Todos os gates de risco aprovaram a operacao",
        )

    def notificar_fechamento(
        self,
        agent_id: str,
        pnl_reais: float,
        ticket: Optional[int] = None,
    ) -> None:
        """
        Notifica os controles internos sobre o fechamento de uma posicao.

        Deve ser chamado imediatamente apos fechar qualquer posicao,
        independente do motivo (SL, TP, manual, horario, calendario).

        Args:
            agent_id: Identificador do agente.
            pnl_reais: Resultado em R$ (positivo=ganho, negativo=perda).
            ticket: Numero do ticket no broker (opcional).
        """
        self._gerenciador_cooldown.registrar_fechamento(agent_id)
        self._limitador_ganho.registrar_resultado(
            agent_id=agent_id,
            pnl_reais=pnl_reais,
            ticket=ticket,
        )
        logger.info(
            "Fechamento notificado: agent=%s, pnl=R$%.2f, ticket=%s",
            agent_id,
            pnl_reais,
            ticket,
        )

    def deve_fechar_posicoes_agora(self) -> bool:
        """
        Verifica se algum gate de tempo solicita fechamento imediato.

        Usado pelo loop principal do agente para fechar posicoes
        proativamente (fim de pregao ou evento economico iminente).

        Returns:
            True se posicoes abertas devem ser encerradas agora.
        """
        try:
            resultado_horario = self._gate_horario.verificar()
            if resultado_horario.deve_fechar_posicoes:
                return True
        except Exception as e:
            logger.warning("Erro ao verificar horario para fechamento: %s", e)

        try:
            resultado_calendario = self._gate_calendario.verificar()
            if resultado_calendario.deve_fechar_posicoes:
                return True
        except Exception as e:
            logger.warning("Erro ao verificar calendario para fechamento: %s", e)

        return False

    # --- Metodos auxiliares ---

    def _avaliar_gate_seguro(
        self,
        codigo: str,
        fn: Any,
    ) -> ResultadoGateRisco:
        """Executa gate capturando excecoes (fail-safe)."""
        try:
            return fn()  # type: ignore[no-any-return]
        except Exception as e:
            logger.error("Erro interno no gate %s: %s", codigo, e)
            return ResultadoGateRisco(
                aprovado=False,
                codigo_gate="GATE_ERRO_INTERNO",
                motivo=f"Erro interno no gate {codigo}: {e}",
                detalhes={"codigo_original": codigo, "erro": str(e)},
            )

    def _avaliar_sl(self, sinal: dict[str, Any]) -> ResultadoGateRisco:
        """Extrai parametros do sinal e valida SL maximo."""
        try:
            preco_entrada = float(
                sinal.get("entry_price") or sinal.get("preco_entrada") or 0.0
            )
            stop_loss = float(sinal.get("stop_loss") or 0.0)
            volume = float(sinal.get("volume") or 1.0)

            if preco_entrada == 0.0 or stop_loss == 0.0:
                # Sem dados de SL no sinal: liberar (gate nao aplicavel)
                return ResultadoGateRisco(
                    aprovado=True,
                    codigo_gate="SL_MAXIMO",
                    motivo="Dados de SL ausentes no sinal — gate nao aplicavel",
                )

            resultado_sl = self._validador_sl.validar(
                preco_entrada=preco_entrada,
                stop_loss=stop_loss,
                volume=volume,
            )
            return ResultadoGateRisco(
                aprovado=resultado_sl.aprovado,
                codigo_gate="SL_MAXIMO",
                motivo=resultado_sl.motivo,
                detalhes={
                    "perda_estimada_reais": resultado_sl.perda_estimada_reais,
                    "perda_maxima_reais": resultado_sl.perda_maxima_reais,
                },
            )
        except Exception as e:
            logger.error("Erro ao validar SL maximo: %s", e)
            return ResultadoGateRisco(
                aprovado=False,
                codigo_gate="GATE_ERRO_INTERNO",
                motivo=f"Erro ao validar SL maximo: {e}",
            )

    def _converter_horario(self) -> ResultadoGateRisco:
        """Converte ResultadoHorario para ResultadoGateRisco."""
        resultado = self._gate_horario.verificar()
        return ResultadoGateRisco(
            aprovado=resultado.aprovado_abertura,
            codigo_gate="HORARIO",
            motivo=resultado.motivo,
            detalhes={
                "horario_atual": str(resultado.horario_atual),
                "deve_fechar_posicoes": resultado.deve_fechar_posicoes,
            },
        )

    def _converter_calendario(self) -> ResultadoGateRisco:
        """Converte ResultadoCalendario para ResultadoGateRisco."""
        resultado = self._gate_calendario.verificar()
        return ResultadoGateRisco(
            aprovado=resultado.aprovado_abertura,
            codigo_gate="CALENDARIO",
            motivo=resultado.motivo,
            detalhes={
                "eventos_proximos": resultado.eventos_proximos,
                "deve_fechar_posicoes": resultado.deve_fechar_posicoes,
            },
        )

    def _converter_ganho_diario(self) -> ResultadoGateRisco:
        """Converte ResultadoGanhoDiario para ResultadoGateRisco."""
        resultado = self._limitador_ganho.verificar_limite()
        return ResultadoGateRisco(
            aprovado=resultado.aprovado,
            codigo_gate="GANHO_DIARIO",
            motivo=resultado.motivo,
            detalhes={
                "ganho_total_hoje_reais": resultado.ganho_total_hoje_reais,
                "limite_reais": resultado.limite_reais,
                "percentual_atingido": resultado.percentual_atingido,
            },
        )

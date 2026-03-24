"""
LimitadorGanhoDiario: Controla o ganho total diario somando todos os agentes.

Responsabilidades:
- Verificar se o ganho total do pregao atingiu o limite configurado
- Registrar resultados de operacoes encerradas
- Bloquear apenas novas entradas (fechamentos sempre permitidos)
- Persiste via IGanhosDiarioRepository (SQLite ou em memoria)

Comportamento:
- congelar_novas_entradas=True (padrao): bloqueia abertura de novas posicoes
- congelar_novas_entradas=False: apenas loga alerta, nao bloqueia

Pipeline:
    AC5.8/MotorDecisaoIsolado fecha posicao →
    → GerenciadorRiscoExterno.notificar_fechamento()
    → LimitadorGanhoDiario.registrar_resultado()

    AC4.DecisionFilter.make_decision() →
    → GerenciadorRiscoExterno.avaliar_todos()
    → LimitadorGanhoDiario.verificar_limite()
    → ResultadoGanhoDiario.aprovado determina EXECUTE/REJECT

Status: v1.0 (24/03/2026)
Referencia: docs/BACKLOG.md (Camada Risco Externo - Ganho Diario)
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import date, datetime, timezone
from typing import Optional

from src.domain.value_objects.risco_externo import ConfiguracaoGanhoDiario
from src.infrastructure.repositories.repositorio_ganho_diario import (
    IGanhosDiarioRepository,
)

logger = logging.getLogger(__name__)


@dataclass
class ResultadoGanhoDiario:
    """
    Resultado da verificacao do limite de ganho diario.

    Atributos:
        aprovado: True se novas entradas estao permitidas.
        ganho_total_hoje_reais: Soma de P&L de todos os agentes no pregao.
        limite_reais: Teto configurado em R$.
        percentual_atingido: Percentual do limite ja consumido (0-100+).
        motivo: Descricao textual da decisao.
    """

    aprovado: bool
    ganho_total_hoje_reais: float
    limite_reais: float
    percentual_atingido: float
    motivo: str


class LimitadorGanhoDiario:
    """
    Controla o ganho diario total somando todos os agentes.

    Quando o limite e atingido:
    - congelar_novas_entradas=True: bloqueia abertura de novas posicoes
    - congelar_novas_entradas=False: apenas registra alerta no log

    Fechamentos de posicoes abertas NUNCA sao bloqueados por este gate.

    Exemplo de uso:
        config = ConfiguracaoGanhoDiario(limite_ganho_diario_reais=1000.0)
        limitador = LimitadorGanhoDiario(config, repositorio_sqlite)
        resultado = limitador.verificar_limite()
        if not resultado.aprovado:
            # rejeitar nova entrada
    """

    def __init__(
        self,
        configuracao: ConfiguracaoGanhoDiario,
        repositorio: IGanhosDiarioRepository,
    ) -> None:
        self._configuracao = configuracao
        self._repositorio = repositorio

    def verificar_limite(
        self, data_pregao: Optional[str] = None
    ) -> ResultadoGanhoDiario:
        """
        Verifica se o ganho total do pregao atingiu o limite.

        Args:
            data_pregao: Data no formato "YYYY-MM-DD". Se None, usa hoje.

        Returns:
            ResultadoGanhoDiario com aprovado=True se pode abrir nova posicao.
        """
        if data_pregao is None:
            data_pregao = date.today().isoformat()

        ganho_total = self._repositorio.consultar_total_dia(data_pregao)
        limite = self._configuracao.limite_ganho_diario_reais
        percentual = (ganho_total / limite * 100.0) if limite > 0 else 0.0

        if ganho_total <= limite:
            return ResultadoGanhoDiario(
                aprovado=True,
                ganho_total_hoje_reais=ganho_total,
                limite_reais=limite,
                percentual_atingido=percentual,
                motivo=(
                    f"Ganho diario R${ganho_total:.2f} dentro do limite "
                    f"R${limite:.2f} ({percentual:.1f}%)"
                ),
            )

        # Limite atingido
        if not self._configuracao.congelar_novas_entradas:
            logger.warning(
                "Limite de ganho diario atingido (R$%.2f > R$%.2f) "
                "— congelamento desativado, apenas alerta",
                ganho_total,
                limite,
            )
            return ResultadoGanhoDiario(
                aprovado=True,
                ganho_total_hoje_reais=ganho_total,
                limite_reais=limite,
                percentual_atingido=percentual,
                motivo=(
                    f"ALERTA: Ganho diario R${ganho_total:.2f} excede limite "
                    f"R${limite:.2f} — congelamento desativado"
                ),
            )

        logger.info(
            "Limite de ganho diario atingido: R$%.2f de R$%.2f — novas entradas bloqueadas",
            ganho_total,
            limite,
        )
        return ResultadoGanhoDiario(
            aprovado=False,
            ganho_total_hoje_reais=ganho_total,
            limite_reais=limite,
            percentual_atingido=percentual,
            motivo=(
                f"Limite de ganho diario atingido: R${ganho_total:.2f} "
                f"excede R${limite:.2f} ({percentual:.1f}%) "
                f"— novas entradas bloqueadas"
            ),
        )

    def registrar_resultado(
        self,
        agent_id: str,
        pnl_reais: float,
        ticket: Optional[int] = None,
        data_pregao: Optional[str] = None,
    ) -> None:
        """
        Registra o resultado de uma operacao encerrada.

        Deve ser chamado pelo GerenciadorRiscoExterno.notificar_fechamento()
        apos cada posicao fechada.

        Args:
            agent_id: Identificador do agente.
            pnl_reais: Resultado em R$ (positivo=ganho, negativo=perda).
            ticket: Numero do ticket no broker (opcional).
            data_pregao: Data no formato "YYYY-MM-DD". Se None, usa hoje.
        """
        if data_pregao is None:
            data_pregao = date.today().isoformat()

        self._repositorio.registrar_pnl(
            data_pregao=data_pregao,
            agent_id=agent_id,
            pnl_reais=pnl_reais,
            ticket=ticket,
        )
        logger.info(
            "P&L registrado: agent=%s, data=%s, pnl=R$%.2f, ticket=%s",
            agent_id,
            data_pregao,
            pnl_reais,
            ticket,
        )

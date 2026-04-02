"""
ROADMAP-MICRO-03: Validador de Sincronizacao MT5.

Responsabilidades:
- Comparar contagem de fechamentos sem resultado local vs MT5.
- Classificar status de sincronizacao da sessao.
- Persistir relatorio de validacao como JSON.

Pipeline:
    TradeOutcomeReconciler.reconciliar_ordem() preenche resultados
    -> MT5SyncValidator.validar_sincronizacao() confirma consistencia final
    -> SINCRONIZADO se delta == 0; DIVERGENCIA_CRITICA caso contrario
"""

import json
import logging
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Dict, Optional

from src.infrastructure.repositories.fechamento_repository import (
    IFechamentoRepository,
)


class SyncStatus(Enum):
    """Status de sincronizacao de uma sessao."""

    SINCRONIZADO = "SINCRONIZADO"
    DIVERGENCIA_CRITICA = "DIVERGENCIA_CRITICA"


@dataclass(frozen=True)
class ValidationReport:
    """Relatorio de validacao de sincronizacao."""

    session_id: str
    agent_id: str
    status: SyncStatus
    contagem_local: int
    contagem_mt5: int
    delta: int
    timestamp: str
    arquivo_relatorio: str


class MT5SyncValidator:
    """
    ROADMAP-MICRO-03: Validador de sincronizacao MT5.

    validar_sincronizacao() compara o numero de fechamentos sem resultado
    no repositorio local com a contagem que MT5 reporta para o agent_id.

    delta == 0  -> SINCRONIZADO
    delta != 0  -> DIVERGENCIA_CRITICA
    """

    def __init__(
        self,
        fechamento_repo: IFechamentoRepository,
        mt5_adapter: Any,
        logger: Optional[logging.Logger] = None,
    ) -> None:
        self._repo = fechamento_repo
        self._mt5 = mt5_adapter
        self._log = logger or logging.getLogger(__name__)

    # ------------------------------------------------------------------
    # Interface publica
    # ------------------------------------------------------------------

    def validar_sincronizacao(
        self,
        session_id: str,
        agent_id: str,
    ) -> ValidationReport:
        """Compara contagens locais vs MT5 e gera ValidationReport.

        Args:
            session_id: Identificador da sessao.
            agent_id: Identificador do agente.

        Returns:
            ValidationReport com status e deltas.
        """
        ts = datetime.now().isoformat()

        sem_resultado_local = self._repo.listar_sem_resultado(
            agent_id=agent_id, magic_number=None
        )
        contagem_local = len(sem_resultado_local)

        try:
            contagem_mt5 = self._obter_contagem_mt5(session_id=session_id, agent_id=agent_id)
        except Exception as exc:
            self._log.warning(
                "validar_sincronizacao: erro ao consultar MT5: %s", exc
            )
            contagem_mt5 = -1

        delta = abs(contagem_local - contagem_mt5) if contagem_mt5 >= 0 else -1

        status = (
            SyncStatus.SINCRONIZADO
            if delta == 0
            else SyncStatus.DIVERGENCIA_CRITICA
        )

        self._log.info(
            "validar_sincronizacao session=%s agent=%s status=%s delta=%s",
            session_id,
            agent_id,
            status.value,
            delta,
        )

        return ValidationReport(
            session_id=session_id,
            agent_id=agent_id,
            status=status,
            contagem_local=contagem_local,
            contagem_mt5=max(contagem_mt5, 0),
            delta=max(delta, 0),
            timestamp=ts,
            arquivo_relatorio="",
        )

    # ------------------------------------------------------------------
    # Metodo auxiliar
    # ------------------------------------------------------------------

    def _obter_contagem_mt5(self, session_id: str, agent_id: str) -> int:
        """Consulta MT5 e retorna numero de fechamentos sem resultado.

        Delega ao mt5_adapter; pode ser sobrescrito em testes.
        """
        return int(self._mt5.contar_fechamentos_sem_resultado(agent_id=agent_id))
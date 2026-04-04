"""
ROADMAP-MICRO-03: Reconciliador de Resultados de Trade.

Responsabilidades:
- Classificar resultado (WIN/LOSS/BREAKEVEN) a partir de pnl_pct.
- Reconciliar resultado via dado local ou consulta MT5 como fallback.
- Persistir resultado preenchido via IFechamentoRepository.
- Gerar relatorio JSON de sessao.

Pipeline:
    UnknownResultDetector.detectar_lacunas() identifica tickets sem resultado
    -> TradeOutcomeReconciler.reconciliar_ordem() preenche resultado
    -> MT5SyncValidator.validar_sincronizacao() confirma consistencia
"""

import json
import logging
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional

from config.settings import AGENT_MAGIC_NUMBERS
from src.application.p1_learning_closure import EpisodeClosureEngine
from src.infrastructure.repositories.fechamento_repository import (
    IFechamentoRepository,
)

_BREAKEVEN_THRESHOLD = EpisodeClosureEngine.BREAKEVEN_THRESHOLD_PCT


class ReconcileStatus(Enum):
    """Status de uma reconciliacao individual."""

    RECONCILIADO_LOCAL = "RECONCILIADO_LOCAL"
    RECONCILIADO_MT5 = "RECONCILIADO_MT5"
    ERRO = "ERRO"
    PENDENTE = "PENDENTE"


@dataclass(frozen=True)
class ReconciliationResult:
    """Resultado de uma reconciliacao de trade."""

    ticket: int
    agent_id: str
    resultado: Optional[str]
    status: ReconcileStatus
    fonte: str
    timestamp: str
    mensagem: str
    reconciled: bool


class TradeOutcomeReconciler:
    """
    ROADMAP-MICRO-03: Reconciliador de resultados de trade.

    Fluxo de reconciliar_ordem():
        1. Verificar idempotencia (resultado ja preenchido -> PENDENTE).
        2. Se local pnl_pct disponivel: classificar sem chamar MT5.
        3. Caso contrario: consultar obter_pnl_fechado() do mt5_adapter.
        4. Se MT5 retorna None: status ERRO.
        5. Persistir via fechamento_repo.atualizar_resultado_fechamento().
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
        self._historico: List[ReconciliationResult] = []

    # ------------------------------------------------------------------
    # Classificacao de resultado
    # ------------------------------------------------------------------

    def _classificar_resultado(self, pnl_pct: Optional[float]) -> str:
        """Classifica resultado com base em pnl_pct.

        Regras:
          - None ou abs(pnl_pct) <= BREAKEVEN_THRESHOLD -> BREAKEVEN
          - pnl_pct > 0 -> WIN
          - pnl_pct < 0 -> LOSS
        """
        if pnl_pct is None:
            return "BREAKEVEN"
        if abs(pnl_pct) <= _BREAKEVEN_THRESHOLD:
            return "BREAKEVEN"
        return "WIN" if pnl_pct > 0 else "LOSS"

    # ------------------------------------------------------------------
    # Reconciliacao de ordem individual
    # ------------------------------------------------------------------

    def reconciliar_ordem(
        self,
        ticket: int,
        agent_id: str,
    ) -> ReconciliationResult:
        """Reconcilia resultado de um ticket para o agente informado."""
        ts = datetime.now().isoformat()

        # Idempotencia: ja reconciliado?
        resultado_existente = self._repo.obter_resultado_local(ticket)
        if resultado_existente is not None:
            return ReconciliationResult(
                ticket=ticket,
                agent_id=agent_id,
                resultado=resultado_existente,
                status=ReconcileStatus.PENDENTE,
                fonte="local_cache",
                timestamp=ts,
                mensagem="Resultado ja preenchido; idempotencia aplicada.",
                reconciled=True,
            )

        # Tentativa 1: dado local (sem chamar MT5)
        sem_resultado = self._repo.listar_sem_resultado(
            agent_id=agent_id, magic_number=None
        )
        ordem_local: Optional[Dict[str, Any]] = None
        for item in sem_resultado:
            if int(item.get("ticket", -1)) == ticket:
                ordem_local = item
                break

        if ordem_local is not None and ordem_local.get("pnl_pct") is not None:
            resultado = self._classificar_resultado(float(ordem_local["pnl_pct"]))
            sucesso = self._repo.atualizar_resultado_fechamento(
                ticket=ticket,
                resultado=resultado,
                pnl=float(ordem_local.get("pnl_reais", 0.0)),
            )
            if sucesso:
                self._log.info("reconciliar_ordem ticket=%s -> %s (LOCAL)", ticket, resultado)
                r = ReconciliationResult(
                    ticket=ticket,
                    agent_id=agent_id,
                    resultado=resultado,
                    status=ReconcileStatus.RECONCILIADO_LOCAL,
                    fonte="local",
                    timestamp=ts,
                    mensagem="Classificado por dado local.",
                    reconciled=True,
                )
                self._historico.append(r)
                return r

        # Tentativa 2: consultar MT5
        try:
            magic_number = _magic_por_agent_id(agent_id)
            pnl_mt5 = self._mt5.obter_pnl_fechado(ticket=ticket, magic_number=magic_number)
        except Exception as exc:
            self._log.warning("reconciliar_ordem ticket=%s: erro MT5: %s", ticket, exc)
            pnl_mt5 = None

        if pnl_mt5 is None:
            r = ReconciliationResult(
                ticket=ticket,
                agent_id=agent_id,
                resultado=None,
                status=ReconcileStatus.ERRO,
                fonte="mt5",
                timestamp=ts,
                mensagem="MT5 nao retornou PnL para o ticket.",
                reconciled=False,
            )
            self._historico.append(r)
            return r

        resultado = self._classificar_resultado(pnl_mt5)
        self._repo.atualizar_resultado_fechamento(ticket=ticket, resultado=resultado, pnl=pnl_mt5)

        self._log.info("reconciliar_ordem ticket=%s -> %s (MT5)", ticket, resultado)
        r = ReconciliationResult(
            ticket=ticket,
            agent_id=agent_id,
            resultado=resultado,
            status=ReconcileStatus.RECONCILIADO_MT5,
            fonte="mt5",
            timestamp=ts,
            mensagem="Classificado por dado MT5.",
            reconciled=True,
        )
        self._historico.append(r)
        return r

    # ------------------------------------------------------------------
    # Relatorio de sessao
    # ------------------------------------------------------------------

    def gerar_relatorio_sessao(
        self,
        session_id: str,
        outputs_path: Path,
    ) -> Path:
        """Gera relatorio JSON de reconciliacao da sessao."""
        outputs_path = Path(outputs_path)
        outputs_path.mkdir(parents=True, exist_ok=True)

        hoje = datetime.now().strftime("%Y%m%d")
        caminho = outputs_path / f"reconciliacao_{hoje}.json"

        n_total = len(self._historico)
        n_local = sum(1 for r in self._historico if r.status == ReconcileStatus.RECONCILIADO_LOCAL)
        n_mt5 = sum(1 for r in self._historico if r.status == ReconcileStatus.RECONCILIADO_MT5)
        n_erro = sum(1 for r in self._historico if r.status == ReconcileStatus.ERRO)
        pct_desconhecido = (n_erro / n_total * 100.0) if n_total > 0 else 0.0

        agent_id = self._historico[0].agent_id if self._historico else "desconhecido"

        relatorio: Dict[str, Any] = {
            "session_id": session_id,
            "agent_id": agent_id,
            "n_total": n_total,
            "n_reconciliados_local": n_local,
            "n_reconciliados_mt5": n_mt5,
            "n_erro": n_erro,
            "pct_desconhecido_sessao": round(pct_desconhecido, 2),
            "timestamp_geracao": datetime.now().isoformat(),
        }

        caminho.write_text(json.dumps(relatorio, indent=2, ensure_ascii=False))
        self._log.info("Relatorio de sessao gravado em %s", caminho)
        return caminho


# ------------------------------------------------------------------
# Utilitario de mapeamento agent_id -> magic_number
# ------------------------------------------------------------------

_MAGIC_POR_AGENT: Dict[str, int] = AGENT_MAGIC_NUMBERS


def _magic_por_agent_id(agent_id: str) -> int:
    """Retorna magic_number para um agent_id conhecido."""
    magic = _MAGIC_POR_AGENT.get(agent_id)
    if magic is None:
        raise ValueError(f"agent_id desconhecido: {agent_id!r}")
    return magic
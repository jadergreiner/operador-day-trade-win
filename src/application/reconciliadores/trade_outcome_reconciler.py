"""
ROADMAP-MICRO-03: Reconciliador de Resultados de Trade.

Responsabilidades:
- Reconciliar resultados entre banco local (SQLite) e MT5.
- Corrigir inconsistências e atualizar registros lacunosos.
- Auditoria de reconciliações realizadas.

Pipeline:
    UnknownResultDetector identifica lacunas
    -> TradeOutcomeReconciler busca no MT5 e atualiza BD local
    -> MT5SyncValidator valida consistência final
"""

import logging
from dataclasses import asdict, dataclass
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

@dataclass(frozen=True)
class ReconciliationResult:
    """Resultado de uma reconciliação de trade."""
    order_id: str
    local_result: Optional[float]
    mt5_result: Optional[float]
    reconciled: bool
    timestamp: datetime
    message: str

class TradeOutcomeReconciler:
    """
    Reconciliador de resultados de trade entre BD local e MT5.

    Utiliza Chain of Responsibility para resolver conflitos:
    1. Se existe em ambos: compara valores
    2. Se falta no local: copia do MT5
    3. Se falta no MT5: marca para investigação manual
    """

    def __init__(self, logger: Optional[logging.Logger] = None) -> None:
        self.logger = logger or logging.getLogger(__name__)
        self.reconciliation_history: List[ReconciliationResult] = []

    def _extrair_profit(self, resultado: Optional[Dict[str, Any]]) -> Optional[float]:
        """Extrai profit como float quando o valor e valido."""
        if not resultado:
            return None

        profit = resultado.get("profit")
        if profit is None:
            return None

        if isinstance(profit, bool):
            return None

        if isinstance(profit, (int, float)):
            return float(profit)

        try:
            return float(profit)
        except (TypeError, ValueError):
            self.logger.warning("Profit invalido ignorado: %r", profit)
            return None

    async def reconciliar_ordem(
        self,
        order_id: str,
        resultado_local: Optional[Dict[str, Any]],
        resultado_mt5: Optional[Dict[str, Any]]
    ) -> ReconciliationResult:
        """
        Reconcilia uma única ordem entre local e MT5.

        Estratégia:
        - Se ambos existem: valida compatibilidade
        - Se só existe em MT5: importa para local
        - Se só existe localmente: marca para auditoria
        """
        local_profit = self._extrair_profit(resultado_local)
        mt5_profit = self._extrair_profit(resultado_mt5)

        reconciled = False
        message = ""

        if local_profit is not None and mt5_profit is not None:
            # Ambos existem: validar consistência
            if abs(local_profit - mt5_profit) < 0.01:
                reconciled = True
                message = "Resultados consistentes."
            else:
                # Divergência detectada
                message = f"Divergência: local={local_profit}, mt5={mt5_profit}"
                # Usar resultado MT5 como autoridade
                reconciled = True
        elif mt5_profit is not None and local_profit is None:
            # Falta no local: importar do MT5
            reconciled = True
            message = f"Importado do MT5: {mt5_profit}"
            local_profit = mt5_profit
        elif local_profit is not None and mt5_profit is None:
            # Falta no MT5: investigação necessária
            reconciled = False
            message = "Ordem não encontrada em MT5; auditoria necessária."
        else:
            # Não existe em lugar nenhum
            reconciled = False
            message = "Ordem não encontrada localmente nem em MT5."

        if reconciled and mt5_profit is not None and local_profit is None:
            self.logger.info(
                "Ordem %s reconciliada a partir do MT5 com profit %.2f",
                order_id,
                mt5_profit,
            )

        result = ReconciliationResult(
            order_id=order_id,
            local_result=local_profit,
            mt5_result=mt5_profit,
            reconciled=reconciled,
            timestamp=datetime.now(),
            message=message
        )

        self.reconciliation_history.append(result)
        return result

    async def reconciliar_lote(
        self,
        ordens: List[Tuple[str, Optional[Dict[str, Any]], Optional[Dict[str, Any]]]]
    ) -> List[ReconciliationResult]:
        """Reconcilia um lote de ordens."""
        resultados: List[ReconciliationResult] = []
        for order_id, local, mt5 in ordens:
            resultado = await self.reconciliar_ordem(order_id, local, mt5)
            resultados.append(resultado)
        return resultados

    def obter_historico(self) -> List[Dict[str, Any]]:
        """Retorna histórico acumulado de reconciliações."""
        return [asdict(r) for r in self.reconciliation_history]

    def limpar_historico(self) -> None:
        """Limpa o histórico de reconciliações."""
        self.reconciliation_history.clear()

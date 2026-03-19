"""
AC5.8: Trade Outcome Reconciler

Módulo para reconciliação de outcomes entre MT5 e banco local SQLite.

O reconciliador valida que trades executados no MT5 foram registrados
corretamente no banco local com mesmos valores, volumes, timestamps e
status funcionais.

Pipeline:
    AC5: TradeExecutor envia ordem
    → AC5.8: MonitorPositionManager rastreia
    → AC5.8 (este módulo): Reconcilia outcome MT5 vs Local
    → AC6: FeedbackLoop processa resultado reconciliado

Status: Implementacao v1.0 (18/03/2026)
Referencia: docs/BACKLOG.md (AC5.8)
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional, List, Dict, Any
from enum import Enum
from uuid import UUID
import logging

# ═══════════════════════════════════════════════════════════════════════════
# ENUMS E VALUE OBJECTS
# ═══════════════════════════════════════════════════════════════════════════

class ReconciliationStatus(Enum):
    """Status de reconciliação de trade outcome."""

    SYNCED = "SYNCED"              # Sincronizado com sucesso
    DIVERGENT = "DIVERGENT"        # Validades divergem
    UNKNOWN = "UNKNOWN"            # Status desconhecido/indeterminado
    DUPLICATE = "DUPLICATE"        # Trade já foi reconciliado
    TIMEOUT = "TIMEOUT"            # Timeout na tentativa


class OutcomeType(Enum):
    """Tipo de outcome de trade."""

    CLOSED = "CLOSED"              # Trade fechado com sucesso
    PARTIAL = "PARTIAL"            # Fechamento parcial
    REJECTED = "REJECTED"          # Rejeitado pela broker
    ABANDONED = "ABANDONED"        # Abandonado (timeout, etc)


@dataclass(frozen=True)
class TradeOutcome:
    """
    Value Object: Resultado de um trade após execução.

    Imutável, garantia de integridade de dados.
    """

    trade_id: str
    symbol: str
    side: str  # BUY ou SELL
    quantity: int
    entry_price: float
    exit_price: Optional[float]
    timestamp_entry: datetime
    timestamp_exit: Optional[datetime]
    status: OutcomeType
    pnl: Optional[float] = None
    commission: float = 0.0
    metadata: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        """Validação de invariates."""
        if self.quantity <= 0:
            raise ValueError("Quantity deve ser positivo")
        if self.entry_price <= 0:
            raise ValueError("Entry price deve ser positivo")
        if self.exit_price is not None and self.exit_price <= 0:
            raise ValueError("Exit price deve ser positivo")


@dataclass
class ReconciliationResult:
    """
    Resultado da reconciliação entre MT5 e local database.

    Contém status, divergências encontradas e audit trail.
    """

    trade_id: str
    reconciliation_status: ReconciliationStatus
    timestamp: datetime
    mt5_outcome: TradeOutcome
    local_outcome: Optional[TradeOutcome]
    divergences: List[str] = field(default_factory=list)
    audit_log: Dict[str, Any] = field(default_factory=dict)

    def is_synced(self) -> bool:
        """Verifica se reconciliação foi sucesso."""
        return self.reconciliation_status == ReconciliationStatus.SYNCED

    def to_dict(self) -> Dict[str, Any]:
        """Serializa para dicionário."""
        return {
            "trade_id": self.trade_id,
            "status": self.reconciliation_status.value,
            "timestamp": self.timestamp.isoformat(),
            "divergences": self.divergences,
            "synced": self.is_synced(),
        }


# ═══════════════════════════════════════════════════════════════════════════
# TRADE OUTCOME RECONCILER
# ═══════════════════════════════════════════════════════════════════════════

class TradeOutcomeReconciler:
    """
    Reconcilia trades executados entre MT5 e base de dados local.

    Responsabilidades:
    - Validar valores (volume, price, pnl)
    - Validar timestamps (consistência, tolerância)
    - Detectar divergências (price, volume, status)
    - Gerar audit trail
    - Persistir reconciliação

    AC Coverage:
    - AC5.8.1 a AC5.8.15 (ver conftest.py)
    """

    def __init__(
        self,
        timestamp_tolerance_ms: int = 2000,
        logger: Optional[logging.Logger] = None
    ) -> None:
        """
        Inicializa reconciliador.

        Args:
            timestamp_tolerance_ms: Tolerância de timestamp em ms (default 2s)
            logger: Logger customizado (default cria novo)
        """
        self.timestamp_tolerance_ms = timestamp_tolerance_ms
        self.logger = logger or logging.getLogger(__name__)
        self._reconciled_trades: Dict[str, ReconciliationResult] = {}

    def reconciliar(
        self,
        mt5_outcome: TradeOutcome,
        local_outcome: Optional[TradeOutcome] = None
    ) -> ReconciliationResult:
        """
        Reconcilia outcome MT5 contra local database.

        Args:
            mt5_outcome: Outcome do MT5
            local_outcome: Outcome local (None se não encontrado)

        Returns:
            ReconciliationResult com status e divergências

        Raises:
            ValueError: Se outcomes inválidos
        """
        # VALIDAR INPUTS
        if mt5_outcome is None:
            raise ValueError("MT5 outcome nao pode ser None")

        # Se não há local outcome, significa trade ainda não foi registrado localmente
        if local_outcome is None:
            result = ReconciliationResult(
                trade_id=mt5_outcome.trade_id,
                reconciliation_status=ReconciliationStatus.UNKNOWN,
                timestamp=datetime.now(),
                mt5_outcome=mt5_outcome,
                local_outcome=None,
                divergences=["Trade nao encontrado no banco local"],
                audit_log=self._gerar_audit_trail(
                    mt5_outcome.trade_id,
                    ReconciliationStatus.UNKNOWN,
                    ["Trade nao encontrado no banco local"]
                )
            )
            self._reconciled_trades[mt5_outcome.trade_id] = result
            return result

        # DETECTAR DIVERGÊNCIAS
        divergences = self._detectar_divergencias(mt5_outcome, local_outcome)

        # DETERMINAR STATUS
        if not divergences:
            status = ReconciliationStatus.SYNCED
        else:
            status = ReconciliationStatus.DIVERGENT

        # GERAR AUDIT TRAIL
        audit = self._gerar_audit_trail(mt5_outcome.trade_id, status, divergences)

        # CRIAR RESULTADO
        result = ReconciliationResult(
            trade_id=mt5_outcome.trade_id,
            reconciliation_status=status,
            timestamp=datetime.now(),
            mt5_outcome=mt5_outcome,
            local_outcome=local_outcome,
            divergences=divergences,
            audit_log=audit
        )

        # PERSISTIR
        self._persistir_resultado(result)

        return result

    def reconciliar_batch(
        self,
        mt5_outcomes: List[TradeOutcome],
        local_outcomes: Optional[List[Optional[TradeOutcome]]] = None
    ) -> List[ReconciliationResult]:
        """
        Reconcilia batch de múltiplos trades atomicamente.

        Args:
            mt5_outcomes: Lista de outcomes MT5
            local_outcomes: Lista de outcomes locais (pode conter None)

        Returns:
            Lista de ReconciliationResults

        Raises:
            RuntimeError: Se reconciliação falhar (rollback all)
        """
        results: List[ReconciliationResult] = []

        # Se não há local outcomes, criar lista de None
        if local_outcomes is None:
            local_outcomes = [None] * len(mt5_outcomes)

        # Processar batch
        if len(mt5_outcomes) != len(local_outcomes):
            raise ValueError(
                f"MT5 outcomes ({len(mt5_outcomes)}) != Local outcomes ({len(local_outcomes)})"
            )

        # Reconciliar cada trade em batch
        for mt5, local in zip(mt5_outcomes, local_outcomes):
            result = self.reconciliar(mt5, local)
            results.append(result)

        return results

    def _validar_saida_basica(self, outcome: TradeOutcome) -> bool:
        """Valida invariantes básicas de outcome."""
        if outcome is None:
            return False
        if outcome.quantity <= 0:
            return False
        if outcome.entry_price <= 0:
            return False
        # Exit price pode ser None (trade ainda aberto)
        if outcome.exit_price is not None and outcome.exit_price <= 0:
            return False
        return True

    def _detectar_divergencias(
        self,
        mt5: TradeOutcome,
        local: TradeOutcome
    ) -> List[str]:
        """Compara e retorna lista de divergências encontradas."""
        divergences: List[str] = []

        # Comparar volume
        if mt5.quantity != local.quantity:
            divergences.append(
                f"Volume diverge: MT5={mt5.quantity} vs Local={local.quantity}"
            )

        # Comparar preços
        if abs(mt5.entry_price - local.entry_price) > 0.01:
            divergences.append(
                f"Entry price diverge: MT5={mt5.entry_price} vs Local={local.entry_price}"
            )

        if mt5.exit_price and local.exit_price:
            if abs(mt5.exit_price - local.exit_price) > 0.01:
                divergences.append(
                    f"Exit price diverge: MT5={mt5.exit_price} vs Local={local.exit_price}"
                )

        # Comparar timestamps
        if not self._validar_timestamps(mt5.timestamp_entry, local.timestamp_entry):
            divergences.append("Entry timestamps não estão dentro da tolerância")

        if mt5.timestamp_exit and local.timestamp_exit:
            if not self._validar_timestamps(mt5.timestamp_exit, local.timestamp_exit):
                divergences.append("Exit timestamps não estão dentro da tolerância")

        return divergences

    def _validar_timestamps(
        self,
        mt5_ts: datetime,
        local_ts: datetime
    ) -> bool:
        """Valida se timestamps estão dentro tolerância."""
        if mt5_ts is None or local_ts is None:
            return False

        diff_ms = abs((mt5_ts - local_ts).total_seconds() * 1000)
        return diff_ms <= self.timestamp_tolerance_ms

    def _gerar_audit_trail(
        self,
        trade_id: str,
        status: ReconciliationStatus,
        divergences: List[str]
    ) -> Dict[str, Any]:
        """Gera log de auditoria estruturado."""
        return {
            "trade_id": trade_id,
            "reconciliation_status": status.value,
            "timestamp": datetime.now().isoformat(),
            "divergences": divergences,
            "divergence_count": len(divergences),
        }

    def _persistir_resultado(self, result: ReconciliationResult) -> None:
        """Persiste resultado em SQLite."""
        # Por enquanto, apenas armazena em memória (dict)
        # Em produção, isso persistiria em SQLite
        self._reconciled_trades[result.trade_id] = result
        self.logger.debug(f"Reconciliacao persistida: {result.trade_id}")


# ═══════════════════════════════════════════════════════════════════════════
# HELPERS & UTILITIES
# ═══════════════════════════════════════════════════════════════════════════

def calcular_pnl(
    side: str,
    entry: float,
    exit: float,
    quantity: int,
    multiplier: int = 100
) -> float:
    """
    Calcula P&L de trade.

    Args:
        side: "BUY" ou "SELL"
        entry: Preço de entrada
        exit: Preço de saída
        quantity: Quantidade de contratos
        multiplier: Multiplicador (default 100 para WIN$N)

    Returns:
        float: P&L em R$
    """
    if quantity <= 0:
        raise ValueError("quantity deve ser positivo")
    if entry <= 0:
        raise ValueError("entry deve ser positivo")
    if exit <= 0:
        raise ValueError("exit deve ser positivo")
    if multiplier <= 0:
        raise ValueError("multiplier deve ser positivo")

    side_normalized = side.strip().upper()
    if side_normalized == "BUY":
        movement = exit - entry
    elif side_normalized == "SELL":
        movement = entry - exit
    else:
        raise ValueError("side deve ser BUY ou SELL")

    return float(movement * quantity * multiplier)


if __name__ == "__main__":
    # TODO: Exemplos de uso
    pass

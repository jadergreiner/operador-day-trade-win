"""
AC4: Decision Filter - Camada de Decisão (Signal → Trade)

Filtra sinais da pipeline AC1→AC2→AC3.

Pipeline Completo:
    AC1: SignalGenerator cria sinais (M5 SMC patterns)
    ↓
    AC2: SignalPersistence persiste em DB
    ↓
    AC3: SignalTracker rastreia lifecycle
    ↓
    AC4: DecisionFilter decide ENTRAR vs FICAR_FORA (THIS LAYER)

Responsabilidades:
    - Recuperar sinais abertos de AC3
    - Aplicar regras de decisão (gates de risco)
    - Gerar decisões com confiança e justificativa
    - Feedback para ML training (decisão → outcome)

Status: Implementação v1.1 (23/03/2026) - BDI Removido
Referência: docs/BACKLOG_UNIFICADO.md (AC4 Decision Filter)
"""

from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Optional, List, Dict, Any, TYPE_CHECKING
import sqlite3
import logging

if TYPE_CHECKING:
    from src.application.gerenciamento_risco.gerenciador_risco_externo import (
        GerenciadorRiscoExterno,
    )

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


# ============================================================================
# ENUMS & TYPE DEFINITIONS
# ============================================================================


class DecisionType(str, Enum):
    """Tipo de decisão sobre um sinal."""
    EXECUTE = "EXECUTE"
    HOLD = "HOLD"
    REJECT = "REJECT"
    CANCEL = "CANCEL"


class RiskGate(str, Enum):
    """Gates de risco na decisão."""
    GATE_2 = "GATE_2"  # Correlação com mercado macro
    GATE_3 = "GATE_3"  # Drawdown protection


# ============================================================================
# DATA MODELS
# ============================================================================


@dataclass
class DecisionGateResult:
    """Resultado de um gate de risco."""
    gate: RiskGate
    passed: bool
    score: float
    reason: str
    timestamp: datetime


@dataclass
class Decision:
    """Decisão final sobre um sinal."""
    signal_id: str
    decision_type: DecisionType
    trade_id: Optional[int]
    risk_gates: List[DecisionGateResult]
    confidence: float
    justification: str
    created_at: datetime
    executed_at: Optional[datetime] = None
    pnl_if_executed: Optional[float] = None


# ============================================================================
# DECISION FILTER CLASS
# ============================================================================


class DecisionFilter:
    """
    AC4: Filtro de decisão.

    Integra sinais (AC1→AC2→AC3) com análise de risco para decidir
    se deve executar um trade ou não.

    Fluxo:
    1. Recuperar sinais abertos de AC3
    2. Aplicar gates de risco
    3. Gerar decisão com justificativa
    4. Fornecer feedback para ML training
    """

    def __init__(
        self,
        db_path: str = "data/db/trading.db",
        gerenciador_risco: Optional["GerenciadorRiscoExterno"] = None,
        agent_id: str = "default",
    ):
        """
        Inicializa filtro de decisao.

        Args:
            db_path: Caminho do banco SQLite
            gerenciador_risco: Facade de risco externo (opcional).
                Se fornecido, e avaliado antes dos gates internos.
            agent_id: Identificador do agente dono deste filtro.
        """
        self.db_path = db_path
        self.gerenciador_risco = gerenciador_risco
        self.agent_id = agent_id
        self.connection: Optional[sqlite3.Connection] = None
        self._connect()
        logger.info(f"[AC4-INIT] Decision Filter initialized at {db_path}")

    def _connect(self) -> None:
        """Estabelece conexão com DB."""
        try:
            self.connection = sqlite3.connect(self.db_path)
            self.connection.row_factory = sqlite3.Row
            logger.info(f"[AC4-DB] Connected to {self.db_path}")
        except sqlite3.Error as e:
            logger.error(f"[AC4-DB-ERROR] Connection failed: {e}")
            raise

    def get_signals_for_decision(self) -> List[Dict[str, Any]]:
        """
        AC4.1: Recuperar sinais abertos aguardando decisão.
        """
        try:
            cursor = self.connection.cursor()
            cursor.execute("""
                SELECT
                    id, signal_id, timestamp, symbol, signal_type,
                    smc_score, smc_detector, entry_price,
                    market_context_json, status, outcome_trade_id
                FROM signals
                WHERE status IN ('OPEN', 'LINKED')
                ORDER BY timestamp DESC
            """)
            rows = cursor.fetchall()
            signals = [dict(row) for row in rows]
            logger.info(f"[AC4-SIGNAL] Retrieved {len(signals)} open signals for decision")
            return signals
        except sqlite3.Error as e:
            logger.error(f"[AC4-SIGNAL-ERROR] Failed to get signals: {e}")
            return []

    def apply_risk_gates(self, signal: Dict) -> List[DecisionGateResult]:
        """
        AC4.2: Aplicar gates de risco.

        Gates:
        1. GATE_2: Correlação com mercado macro
        2. GATE_3: Drawdown protection
        """
        gates = []

        # GATE_2: Correlação macro
        gate2 = self._gate_macro_correlation(signal)
        gates.append(gate2)

        # GATE_3: Drawdown
        gate3 = self._gate_drawdown_protection(signal)
        gates.append(gate3)

        logger.info(f"[AC4-GATES] Applied {len(gates)} gates: {[g.passed for g in gates]}")
        return gates

    def _gate_macro_correlation(self, signal: Dict) -> DecisionGateResult:
        """Gate 2: Validar correlação macro."""
        # TODO: Integrar com macro indicators (índice, dólar, taxa)
        return DecisionGateResult(
            gate=RiskGate.GATE_2,
            passed=True,
            score=80.0,
            reason="Macro correlation acceptable (placeholder)",
            timestamp=datetime.now(),
        )

    def _gate_drawdown_protection(self, signal: Dict) -> DecisionGateResult:
        """Gate 3: Validar proteção contra drawdown."""
        # TODO: Verificar drawdown máximo no sinal
        return DecisionGateResult(
            gate=RiskGate.GATE_3,
            passed=True,
            score=85.0,
            reason="Drawdown protection OK (placeholder)",
            timestamp=datetime.now(),
        )

    def make_decision(self, signal: Dict[str, Any]) -> Decision:
        """
        AC4.3: Tomar decisão final sobre um sinal.

        Process:
        1. Aplicar gates de risco
        2. Combinar resultados
        3. Gerar decisão com justificativa
        """
        try:
            signal_id = signal.get("signal_id")

            # Avaliar gates de risco externo (se configurado)
            if self.gerenciador_risco is not None:
                resultado_risco = self.gerenciador_risco.avaliar_todos(
                    agent_id=self.agent_id,
                    sinal=signal,
                )
                if not resultado_risco.aprovado:
                    logger.info(
                        "[AC4-RISCO-EXT] %s REJEITADO por gate externo %s: %s",
                        signal_id,
                        resultado_risco.primeiro_gate_reprovado,
                        resultado_risco.motivo,
                    )
                    return Decision(
                        signal_id=signal_id,
                        decision_type=DecisionType.REJECT,
                        trade_id=signal.get("outcome_trade_id"),
                        risk_gates=[],
                        confidence=0.0,
                        justification=(
                            f"Gate externo [{resultado_risco.primeiro_gate_reprovado}]: "
                            f"{resultado_risco.motivo}"
                        ),
                        created_at=datetime.now(),
                    )

            # Aplicar gates internos
            gates = self.apply_risk_gates(signal)

            # Todos os gates devem passar
            all_passed = all(gate.passed for gate in gates)

            # Gerar decisão
            if all_passed:
                decision_type = DecisionType.EXECUTE
                confidence = min((g.score for g in gates), default=0.0)
                justification = "All risk gates passed"
            else:
                decision_type = DecisionType.REJECT
                failed_gates = [g.gate.name for g in gates if not g.passed]
                confidence = 100 - (len(failed_gates) / len(gates)) * 100 if gates else 0
                justification = f"Failed gates: {', '.join(failed_gates)}"

            decision = Decision(
                signal_id=signal_id,
                decision_type=decision_type,
                trade_id=signal.get("outcome_trade_id"),
                risk_gates=gates,
                confidence=confidence,
                justification=justification,
                created_at=datetime.now(),
            )

            logger.info(
                f"[AC4-DECISION] {signal_id}: {decision_type.value} "
                f"(conf: {confidence:.1f}%)"
            )
            return decision

        except Exception as e:
            logger.error(f"[AC4-DECISION-ERROR] Failed to make decision: {e}")
            return Decision(
                signal_id=signal.get("signal_id", "UNKNOWN"),
                decision_type=DecisionType.REJECT,
                trade_id=None,
                risk_gates=[],
                confidence=0.0,
                justification="Error during decision making",
                created_at=datetime.now(),
            )

    def get_decision_stats(self) -> Dict[str, Any]:
        """
        AC4.4: Calcular estatísticas de decisões.
        """
        try:
            cursor = self.connection.cursor()
            cursor.execute("""
                SELECT
                    COUNT(*) as total_decisions,
                    SUM(CASE WHEN decision_type = 'EXECUTE' THEN 1 ELSE 0 END)
                        as executed,
                    SUM(CASE WHEN decision_type = 'REJECT' THEN 1 ELSE 0 END)
                        as rejected,
                    AVG(confidence) as avg_confidence
                FROM ac4_decisions
            """)
            row = cursor.fetchone()
            if row:
                return {
                    "total": row[0] or 0,
                    "executed": row[1] or 0,
                    "rejected": row[2] or 0,
                    "avg_confidence": round(row[3] or 0, 2),
                }
            return {"total": 0, "executed": 0, "rejected": 0, "avg_confidence": 0.0}
        except sqlite3.Error as e:
            logger.error(f"[AC4-STATS-ERROR] Failed to get stats: {e}")
            return {}

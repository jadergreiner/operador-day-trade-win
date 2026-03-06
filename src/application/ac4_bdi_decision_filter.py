"""
AC4: BDI-Based Decision Filter - Camada de Decisão (Signal → Trade)

Filtra sinais perseguindo AC1→AC2→AC3 baseado em padrões BDI.

Pipeline Completo:
    AC1: SignalGenerator cria sinais (M5 SMC patterns)
    ↓
    AC2: SignalPersistence persiste em DB
    ↓
    AC3: SignalTracker rastreia lifecycle
    ↓
    AC4: BDIDecisionFilter decide ENTRAR vs FICAR_FORA (THIS LAYER)

Responsabilidades:
    - Recuperar sinais abertos de AC3
    - Validar contra padrões BDI do ProcessadorBDI
    - Aplicar regras de decisão (3 gates de risco)
    - Gerar decisões com confiança e justificativa
    - Feedback para ML training (decisão → outcome)

Status: Implementação v1.0 (05/03/2026)
Referência: docs/BACKLOG_UNIFICADO.md (AC4 Decision Filter)
           docs/AC4_PLAN.md (especificação completa)
"""

from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Optional, List, Dict, Any
from uuid import UUID
import sqlite3
import logging
from decimal import Decimal

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


# ============================================================================
# ENUMS & TYPE DEFINITIONS
# ============================================================================


class DecisionType(str, Enum):
    """Tipo de decisão sobre um sinal."""
    EXECUTE = "EXECUTE"  # Pronto para trade
    HOLD = "HOLD"  # Aguardar melhores condições
    REJECT = "REJECT"  # Não ejecutar
    CANCEL = "CANCEL"  # Cancelar execução anterior


class RiskGate(str, Enum):
    """Gates de risco na decisão."""
    GATE_1 = "GATE_1"  # Volatilidade aceitável (BDI analysis)
    GATE_2 = "GATE_2"  # Correlação com mercado macro
    GATE_3 = "GATE_3"  # Drawdown protection


# ============================================================================
# DATA MODELS
# ============================================================================


@dataclass
class BDIContext:
    """Contexto BDI para decisão."""
    volatility_level: str  # LOW, NORMAL, HIGH, EXTREME
    pattern_detected: str  # BOS, CHoCH, FVG, etc
    confidence_score: float  # 0-100 (BDI analyzer confidence)
    lookback_bars: int  # Quantas barras foram analisadas
    last_update: datetime


@dataclass
class DecisionGateResult:
    """Resultado de um gate de risco."""
    gate: RiskGate
    passed: bool  # True = passou no gate
    score: float  # 0-100 (quanto passou do threshold)
    reason: str  # Por que passou ou falhou
    timestamp: datetime


@dataclass
class BDIDecision:
    """Decisão final sobre um sinal baseada em BDI."""
    signal_id: str
    decision_type: DecisionType
    trade_id: Optional[int]  # FK trades se executado
    bdi_context: BDIContext
    risk_gates: List[DecisionGateResult]
    confidence: float  # 0-100 (confiança na decisão)
    justification: str  # Motivo da decisão
    created_at: datetime
    executed_at: Optional[datetime] = None
    pnl_if_executed: Optional[float] = None  # P&L teórico


# ============================================================================
# BDI DECISION FILTER CLASS
# ============================================================================


class BDIDecisionFilter:
    """
    AC4: Filtro de decisão baseado em BDI.

    Integra sinais (AC1→AC2→AC3) com análise BDI para decidir
    se deve executar trade ou não.

    Fluxo:
    1. Recuperar sinais abertos de AC3
    2. Validar contra ProcessadorBDI patterns
    3. Aplicar 3 gates de risco
    4. Gerar decisão com justificativa
    5. Fornecer feedback para ML training
    """

    def __init__(self, db_path: str = "data/db/trading.db"):
        """
        Inicializa filtro de decisão.

        Args:
            db_path: Caminho do banco SQLite
        """
        self.db_path = db_path
        self.connection: Optional[sqlite3.Connection] = None
        self._connect()
        logger.info(f"[AC4-INIT] BDI Decision Filter initialized at {db_path}")

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

        Busca sinais com status OPEN ou LINKED (ainda não fechados)
        de forma que possamos avaliar se devem executar.

        Returns:
            Lista de sinais com todas as informações necessárias
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

            logger.info(
                f"[AC4-SIGNAL] Retrieved {len(signals)} open signals for decision"
            )
            return signals

        except sqlite3.Error as e:
            logger.error(f"[AC4-SIGNAL-ERROR] Failed to get signals: {e}")
            return []

    def evaluate_bdi_context(self, signal: Dict[str, Any]) -> BDIContext:
        """
        AC4.2: Avaliar contexto BDI do sinal.

        Analisa o mercado BDI e gera contexto para decisão.

        Args:
            signal: Sinal recuperado de get_signals_for_decision()

        Returns:
            BDIContext com análise BDI
        """
        try:
            symbol = signal.get("symbol", "UNKNOWN")
            smc_score = signal.get("smc_score", 0.0)
            smc_detector = signal.get("smc_detector", "UNKNOWN")

            # TODO: Integrar com ProcessadorBDI.analisar_bdi()
            # Por enquanto, análise simplificada
            volatility_level = self._assess_volatility(smc_score)
            confidence = min(100, max(0, (abs(smc_score) / 3.0) * 100))

            bdi_context = BDIContext(
                volatility_level=volatility_level,
                pattern_detected=smc_detector,
                confidence_score=confidence,
                lookback_bars=100,
                last_update=datetime.now(),
            )

            logger.info(
                f"[AC4-BDI] BDI context for {symbol}: "
                f"{volatility_level} (conf: {confidence:.1f}%)"
            )
            return bdi_context

        except Exception as e:
            logger.error(f"[AC4-BDI-ERROR] Failed to evaluate BDI context: {e}")
            # Fallback: contexto neutro
            return BDIContext(
                volatility_level="NORMAL",
                pattern_detected="UNKNOWN",
                confidence_score=50.0,
                lookback_bars=0,
                last_update=datetime.now(),
            )

    def apply_risk_gates(
        self, signal: Dict, bdi_context: BDIContext
    ) -> List[DecisionGateResult]:
        """
        AC4.3: Aplicar 3 gates de risco.

        Gates:
        1. GATE_1: Volatilidade aceitável (BDI analysis)
        2. GATE_2: Correlação com mercado macro
        3. GATE_3: Drawdown protection

        Args:
            signal: Sinal para avaliar
            bdi_context: Contexto BDI

        Returns:
            Lista de resultados dos gates
        """
        gates = []

        # GATE_1: Volatilidade
        gate1 = self._gate_volatility(signal, bdi_context)
        gates.append(gate1)

        # GATE_2: Correlação macro
        gate2 = self._gate_macro_correlation(signal)
        gates.append(gate2)

        # GATE_3: Drawdown
        gate3 = self._gate_drawdown_protection(signal)
        gates.append(gate3)

        logger.info(f"[AC4-GATES] Applied 3 gates: {[g.passed for g in gates]}")
        return gates

    def _gate_volatility(self, signal: Dict, bdi: BDIContext) -> DecisionGateResult:
        """Gate 1: Validar volatilidade."""
        vola_level = bdi.volatility_level
        threshold = 75  # Minimum confidence for volatility

        passed = bdi.confidence_score >= threshold and vola_level != "EXTREME"
        score = bdi.confidence_score

        return DecisionGateResult(
            gate=RiskGate.GATE_1,
            passed=passed,
            score=score,
            reason=f"Volatility {vola_level} (conf: {score:.1f}%)" if passed else
                   f"Volatility {vola_level} REJECTED (conf: {score:.1f}%)",
            timestamp=datetime.now(),
        )

    def _gate_macro_correlation(self, signal: Dict) -> DecisionGateResult:
        """Gate 2: Validar correlação macro."""
        # TODO: Integrar com macro indicators (índice, dólar, taxa)
        # Por enquanto, sempre passa (placeholder)
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
        # Por enquanto, sempre passa
        return DecisionGateResult(
            gate=RiskGate.GATE_3,
            passed=True,
            score=85.0,
            reason="Drawdown protection OK (placeholder)",
            timestamp=datetime.now(),
        )

    def _assess_volatility(self, smc_score: float) -> str:
        """Classificar volatilidade baseada em SMC score."""
        abs_score = abs(smc_score)
        if abs_score < 1.0:
            return "LOW"
        elif abs_score < 2.0:
            return "NORMAL"
        elif abs_score < 2.5:
            return "HIGH"
        else:
            return "EXTREME"

    def make_decision(self, signal: Dict[str, Any]) -> BDIDecision:
        """
        AC4.4: Tomar decisão final sobre um sinal.

        Process:
        1. Avaliar contexto BDI
        2. Aplicar 3 gates de risco
        3. Combinar resultados
        4. Gerar decisão com justificativa

        Args:
            signal: Sinal para decidir

        Returns:
            BDIDecision com tipo e justificativa
        """
        try:
            signal_id = signal.get("signal_id")

            # Avaliar BDI
            bdi_context = self.evaluate_bdi_context(signal)

            # Aplicar gates
            gates = self.apply_risk_gates(signal, bdi_context)

            # Todos os gates devem passar
            all_passed = all(gate.passed for gate in gates)

            # Gerar decisão
            if all_passed:
                decision_type = DecisionType.EXECUTE
                confidence = min(g.score for g in gates)
                justification = f"All risk gates passed (BDI: {bdi_context.pattern_detected})"
            else:
                decision_type = DecisionType.REJECT
                failed_gates = [g.gate.name for g in gates if not g.passed]
                confidence = 100 - (len(failed_gates) / 3.0) * 100
                justification = f"Failed gates: {', '.join(failed_gates)}"

            decision = BDIDecision(
                signal_id=signal_id,
                decision_type=decision_type,
                trade_id=signal.get("outcome_trade_id"),
                bdi_context=bdi_context,
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
            # Fallback: REJECT por segurança
            return BDIDecision(
                signal_id=signal.get("signal_id", "UNKNOWN"),
                decision_type=DecisionType.REJECT,
                trade_id=None,
                bdi_context=BDIContext(
                    volatility_level="UNKNOWN",
                    pattern_detected="ERROR",
                    confidence_score=0.0,
                    lookback_bars=0,
                    last_update=datetime.now(),
                ),
                risk_gates=[],
                confidence=0.0,
                justification="Error during decision making",
                created_at=datetime.now(),
            )

    def get_decision_stats(self) -> Dict[str, Any]:
        """
        AC4.5: Calcular estatísticas de decisões.

        Returns:
            Dict com métricas agregadas
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
            else:
                return {
                    "total": 0,
                    "executed": 0,
                    "rejected": 0,
                    "avg_confidence": 0.0,
                }

        except sqlite3.Error as e:
            logger.error(f"[AC4-STATS-ERROR] Failed to get stats: {e}")
            return {}

"""
S2-5 Task 5: Score T+60 e SMC Confluência (Validação Dupla)

Módulo responsável por integrar o Score T+60 com o sistema SMC (Suporte/
Resistência/Meio Termo) para criar uma validação de confluência dupla.

Resultado: Matriz 4 estados (BULL_SEGURO, BEAR_SEGURO, CONFLITO, AGUARDAR)
com decisões robustas baseadas em convergência de sinais.

Exemplo:
    >>> confluence_engine = ScoreT60Confluence()
    >>> t60_result = {"score_t60": 0.725, "classe": "BULL"}
    >>> smc_status = {"direction": "BULL", "strength": 0.85}
    >>> result = confluence_engine.compute_confluence(t60_result, smc_status)
    >>> result
    {
      'state': 'BULL_SEGURO',
      'score_confluencia': 0.7875,
      'confidence': 'ALTA',
      'trigger': 'BUY',
      'timestamp': '2026-02-24T14:30:00Z'
    }

Author: Arquiteto de Sistemas
Date: 2026-02-24
Version: 1.0.0
"""

import json
import logging
import os
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

# ════════════════════════════════════════════════════════════════════════════
# LOGGER CONFIGURATION
# ════════════════════════════════════════════════════════════════════════════

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)


# ════════════════════════════════════════════════════════════════════════════
# CONSTANTS
# ════════════════════════════════════════════════════════════════════════════

# Thresholds para Score T60 (contínuo [0, 1])
THRESHOLD_BULL: float = 0.62  # Score > 0.62 = BULL
THRESHOLD_BEAR: float = 0.38  # Score < 0.38 = BEAR
THRESHOLD_NEUTRO: float = 0.50  # ~0.50 = NEUTRO/indeciso

# Estados válidos
STATES = ["BULL_SEGURO", "BEAR_SEGURO", "CONFLITO", "AGUARDAR"]
TRIGGERS = ["BUY", "SELL", "HOLD", "AGUARDAR"]
SMC_DIRECTIONS = ["BULL", "BEAR", "NEUTRO"]
CONFIDENCE_LEVELS = ["ALTA", "BAIXA"]

# Persistência
DEFAULT_CONFLUENCE_PATH: str = os.path.expanduser(
    "~/.operador_score_t60_confluence.json"
)


# ════════════════════════════════════════════════════════════════════════════
# CLASSES & FUNCTIONS
# ════════════════════════════════════════════════════════════════════════════


class ScoreT60Confluence:
    """
    Integrador de Score T60 com SMC para confluência dupla (validação).

    Attributes:
        threshold_bull: Threshold superior para BULL (default 0.62)
        threshold_bear: Threshold inferior para BEAR (default 0.38)
        confluence_history: Histórico de confluências calculadas
    """

    def __init__(
        self,
        threshold_bull: float = THRESHOLD_BULL,
        threshold_bear: float = THRESHOLD_BEAR,
    ) -> None:
        """
        Inicializa engine de confluência.

        Args:
            threshold_bull: Score mínimo para BULL (default 0.62)
            threshold_bear: Score máximo para BEAR (default 0.38)

        Raises:
            ValueError: Se thresholds inválidos
        """
        if not (0.0 < threshold_bear < threshold_bull < 1.0):
            raise ValueError(
                f"Thresholds inválidos: "
                f"bear={threshold_bear}, bull={threshold_bull}"
            )

        self.threshold_bull = threshold_bull
        self.threshold_bear = threshold_bear
        self.confluence_history: List[Dict[str, Any]] = []
        self.last_result: Optional[Dict[str, Any]] = None

        logger.info(
            f"✅ Confluência engine inicializado "
            f"(BEAR<{threshold_bear}, BULL>{threshold_bull})"
        )

    def compute_confluence(
        self,
        t60_result: Dict[str, Any],
        smc_status: Dict[str, Any],
    ) -> Dict[str, Any]:
        """
        Computa confluência entre Score T60 e SMC status.

        Args:
            t60_result: Dict com score_t60, classe, confianca
            smc_status: Dict com direction (BULL|BEAR|NEUTRO), strength

        Returns:
            Dict com:
            - state: BULL_SEGURO|BEAR_SEGURO|CONFLITO|AGUARDAR
            - score_confluencia: [0, 1]
            - confidence: ALTA|BAIXA
            - trigger: BUY|SELL|HOLD|AGUARDAR
            - timestamp: ISO 8601
            - validities: {t60_valid, smc_valid, convergence}

        Raises:
            ValueError: Se inputs inválidos
        """
        try:
            # Validar inputs
            self._validate_inputs(t60_result, smc_status)

            # Extrair valores
            t60_score = float(t60_result.get("score_t60", 0.5))
            smc_direction = str(smc_status.get("direction", "NEUTRO"))
            smc_strength = float(smc_status.get("strength", 0.5))

            logger.info(
                f"Computando confluência: "
                f"T60={t60_score:.3f}, SMC={smc_direction}({smc_strength:.2f})"
            )

            # Classificar estado
            state = self._classify_state(t60_score, smc_direction)

            # Calcular score confluência
            score_confluencia = self._calculate_score(
                t60_score, smc_direction, smc_strength
            )

            # Determinar confiança
            confidence = self._calculate_confidence(
                t60_score, smc_direction, state
            )

            # Determinar trigger
            trigger = self._get_trigger(state)

            # Validities
            validities = {
                "t60_valid": 0.0 <= t60_score <= 1.0,
                "smc_valid": smc_direction in SMC_DIRECTIONS,
                "convergence": self._check_convergence(
                    t60_score, smc_direction
                ),
            }

            # Build resultado
            result = {
                "state": state,
                "score_confluencia": float(score_confluencia),
                "confidence": confidence,
                "trigger": trigger,
                "timestamp": datetime.utcnow().isoformat() + "Z",
                "validities": validities,
            }

            self.last_result = result
            self.confluence_history.append(result)

            logger.info(
                f"✅ Confluência: {state} (score={score_confluencia:.3f}, "
                f"conf={confidence}, trigger={trigger})"
            )

            return result

        except Exception as e:
            logger.error(f"❌ Erro em compute_confluence: {e}")
            raise

    def _validate_inputs(
        self,
        t60_result: Dict[str, Any],
        smc_status: Dict[str, Any],
    ) -> None:
        """
        Valida formato e rangos dos inputs.

        Raises:
            ValueError: Se inputs inválidos
        """
        # Check 1: Dicts não vazios
        if not t60_result or not smc_status:
            raise ValueError("Inputs não podem ser vazios")

        # Check 2: Score T60 [0, 1]
        t60_score = t60_result.get("score_t60")
        if t60_score is None or not isinstance(t60_score, (int, float)):
            raise ValueError(f"score_t60 inválido: {t60_score}")
        if not (0.0 <= t60_score <= 1.0):
            raise ValueError(f"score_t60 fora range: {t60_score}")

        # Check 3: SMC direction
        smc_dir = smc_status.get("direction")
        if smc_dir not in SMC_DIRECTIONS:
            raise ValueError(f"SMC direction inválido: {smc_dir}")

        # Check 4: SMC strength [0, 1]
        smc_str = smc_status.get("strength", 0.5)
        if not isinstance(smc_str, (int, float)) or not (
            0.0 <= smc_str <= 1.0
        ):
            raise ValueError(f"SMC strength inválido: {smc_str}")

    def _classify_state(
        self, t60_score: float, smc_direction: str
    ) -> str:
        """
        Classifica em um dos 4 estados.

        Args:
            t60_score: Score T60 [0, 1]
            smc_direction: BULL | BEAR | NEUTRO

        Returns:
            BULL_SEGURO | BEAR_SEGURO | CONFLITO | AGUARDAR
        """
        # BULL SEGURO: Ambos BULL
        if t60_score > self.threshold_bull and smc_direction == "BULL":
            return "BULL_SEGURO"

        # BEAR SEGURO: Ambos BEAR
        if t60_score < self.threshold_bear and smc_direction == "BEAR":
            return "BEAR_SEGURO"

        # CONFLITO: Divergentes
        if (
            t60_score > self.threshold_bull and smc_direction == "BEAR"
        ) or (t60_score < self.threshold_bear and smc_direction == "BULL"):
            return "CONFLITO"

        # AGUARDAR: Sinal fraco ou SMC neutro
        if (
            self.threshold_bear <= t60_score <= self.threshold_bull
            or smc_direction == "NEUTRO"
        ):
            return "AGUARDAR"

        # Fallback
        return "AGUARDAR"

    def _calculate_score(
        self,
        t60_score: float,
        smc_direction: str,
        smc_strength: float,
    ) -> float:
        """
        Calcula score confluência baseado em estado.

        Args:
            t60_score: Score T60 [0, 1]
            smc_direction: BULL | BEAR | NEUTRO
            smc_strength: SMC strength [0, 1]

        Returns:
            Score confluência [0, 1]
        """
        state = self._classify_state(t60_score, smc_direction)

        # BULL_SEGURO: Média dos dois sinais
        if state == "BULL_SEGURO":
            return (t60_score + smc_strength) / 2.0

        # BEAR_SEGURO: Inverte T60 (força BEAR) + SMC strength
        if state == "BEAR_SEGURO":
            return ((1.0 - t60_score) + smc_strength) / 2.0

        # CONFLITO ou AGUARDAR: Neutro (0.5)
        return 0.5

    def _calculate_confidence(
        self, t60_score: float, smc_direction: str, state: str
    ) -> str:
        """
        Calcula nível de confiança.

        Args:
            t60_score: Score T60 [0, 1]
            smc_direction: BULL | BEAR | NEUTRO
            state: Estado classificado

        Returns:
            ALTA | BAIXA
        """
        # ALTA confiança: Estados seguros (BULL_SEGURO, BEAR_SEGURO)
        if state in ["BULL_SEGURO", "BEAR_SEGURO"]:
            return "ALTA"

        # BAIXA confiança: CONFLITO ou AGUARDAR
        return "BAIXA"

    def _check_convergence(self, t60_score: float, smc_direction: str) -> bool:
        """
        Verifica se T60 e SMC convergem (sinal similar).

        Args:
            t60_score: Score T60 [0, 1]
            smc_direction: BULL | BEAR | NEUTRO

        Returns:
            True se convergentes, False se divergentes
        """
        # BULL convergência
        if (
            t60_score > self.threshold_bull
            and smc_direction == "BULL"
        ):
            return True

        # BEAR convergência
        if (
            t60_score < self.threshold_bear
            and smc_direction == "BEAR"
        ):
            return True

        # SMC NEUTRO = sem divergência
        if smc_direction == "NEUTRO":
            return True

        # Divergência detectada
        return False

    def _get_trigger(self, state: str) -> str:
        """
        Retorna decisão de trade baseado em estado.

        Args:
            state: BULL_SEGURO | BEAR_SEGURO | CONFLITO | AGUARDAR

        Returns:
            BUY | SELL | HOLD | AGUARDAR
        """
        if state == "BULL_SEGURO":
            return "BUY"
        elif state == "BEAR_SEGURO":
            return "SELL"
        elif state == "CONFLITO":
            return "AGUARDAR"  # Não operar em conflito
        else:  # AGUARDAR
            return "HOLD"

    def persist_result(
        self, filepath: str = DEFAULT_CONFLUENCE_PATH
    ) -> None:
        """
        Persiste último resultado em JSON.

        Args:
            filepath: Caminho do arquivo (~/.operador_score_t60_confluence.json)

        Raises:
            ValueError: Se não há resultado para persistir
            RuntimeError: Se persistência falhar
        """
        if not self.last_result:
            raise ValueError("Sem resultado para persistir")

        try:
            folderpath = Path(filepath).parent
            folderpath.mkdir(parents=True, exist_ok=True)

            with open(filepath, "w", encoding="utf-8") as f:
                json.dump(self.last_result, f, indent=2)

            logger.info(f"✅ Confluência persistida: {filepath}")

        except Exception as e:
            raise RuntimeError(
                f"Failed to persist confluence result: {e}"
            ) from e

    def get_history_stats(self) -> Dict[str, Any]:
        """
        Retorna estatísticas do histórico de confluências.

        Returns:
            Dict com counts por estado, média score, etc
        """
        if not self.confluence_history:
            return {
                "total": 0,
                "bull_seguro_count": 0,
                "bear_seguro_count": 0,
                "conflito_count": 0,
                "aguardar_count": 0,
                "avg_score": 0.0,
            }

        history = self.confluence_history
        scores = [r.get("score_confluencia", 0.5) for r in history]

        return {
            "total": len(history),
            "bull_seguro_count": len([r for r in history if r["state"] == "BULL_SEGURO"]),
            "bear_seguro_count": len([r for r in history if r["state"] == "BEAR_SEGURO"]),
            "conflito_count": len([r for r in history if r["state"] == "CONFLITO"]),
            "aguardar_count": len([r for r in history if r["state"] == "AGUARDAR"]),
            "avg_score": float(sum(scores) / len(scores)) if scores else 0.0,
        }


# ════════════════════════════════════════════════════════════════════════════
# MAIN ENTRY POINT
# ════════════════════════════════════════════════════════════════════════════


def main() -> None:
    """
    Exemplo de uso do confluence engine.
    """
    logger.info("🚀 Score T60 + SMC Confluência Engine")

    # Initialize
    confluence = ScoreT60Confluence()

    # Exemplo 1: BULL SEGURO
    t60_result = {"score_t60": 0.725, "classe": "BULL"}
    smc_status = {"direction": "BULL", "strength": 0.85}
    result = confluence.compute_confluence(t60_result, smc_status)
    logger.info(f"Resultado 1: {result}")
    confluence.persist_result()

    # Exemplo 2: CONFLITO
    t60_result = {"score_t60": 0.72, "classe": "BULL"}
    smc_status = {"direction": "BEAR", "strength": 0.75}
    result = confluence.compute_confluence(t60_result, smc_status)
    logger.info(f"Resultado 2: {result}")

    # Exemplo 3: BEAR SEGURO
    t60_result = {"score_t60": 0.25, "classe": "BEAR"}
    smc_status = {"direction": "BEAR", "strength": 0.80}
    result = confluence.compute_confluence(t60_result, smc_status)
    logger.info(f"Resultado 3: {result}")

    # Stats
    stats = confluence.get_history_stats()
    logger.info(f"📊 Histórico: {stats}")


if __name__ == "__main__":
    main()

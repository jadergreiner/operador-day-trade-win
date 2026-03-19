"""
ROADMAP-MICRO-03: Detector de Resultados Desconhecidos.

Responsabilidades:
- Identificar ordens sem resultado claro no banco local vs MT5.
- Marcar transações para reconciliação manual ou automática.
"""

from dataclasses import dataclass
from enum import Enum
import logging
from typing import Any, Dict, List, Optional

class ReconcileStatus(Enum):
    PENDENTE = "pendente"
    RECONCILIADO = "reconciliado"
    DESCONHECIDO = "desconhecido"
    ERRO = "erro"

@dataclass(frozen=True)
class TradeOutcome:
    order_id: str
    symbol: str
    result: float
    status: ReconcileStatus
    metadata: Dict[str, Any]

class UnknownResultDetector:
    """
    ROADMAP-MICRO-03: Detector de Resultados Desconhecidos.

    Responsabilidades:
    - Identificar ordens sem resultado claro no banco local vs MT5.
    - Marcar transações para reconciliação manual ou automática.
    """

    def __init__(self, logger: Optional[logging.Logger] = None) -> None:
        self.logger = logger or logging.getLogger(__name__)

    def _normalizar_identificador(self, valor: Any) -> Optional[str]:
        """Normaliza identificadores de ordem para texto aproveitavel."""
        if valor is None:
            return None

        texto = str(valor).strip()
        return texto or None

    async def detectar_lacunas(
        self,
        ordens_locais: List[Dict[str, Any]],
        ordens_mt5: List[Dict[str, Any]],
    ) -> List[str]:
        """Detecta IDs de ordens que existem no MT5 mas não possuem resultado local."""
        ids_locais: set[str] = set()
        for ordem in ordens_locais:
            identificador = self._normalizar_identificador(ordem.get("order_id"))
            if identificador is not None and ordem.get("result") is not None:
                ids_locais.add(identificador)

        ids_mt5: set[str] = set()
        for ordem in ordens_mt5:
            identificador = self._normalizar_identificador(ordem.get("ticket"))
            if identificador is not None:
                ids_mt5.add(identificador)

        lacunas = sorted(ids_mt5 - ids_locais)
        if lacunas:
            self.logger.warning(f"Detectadas {len(lacunas)} lacunas de informação.")

        return lacunas

    def validar_integridade_resultado(self, resultado: Dict[str, Any]) -> bool:
        """Valida se os dados do resultado são consistentes (Preço, Volume, Profit)."""
        if not resultado:
            return False

        required = ["price", "volume", "profit"]
        for chave in required:
            if chave not in resultado:
                return False

            valor = resultado[chave]
            if valor is None:
                return False

            if chave == "volume" and isinstance(valor, bool):
                return False

        return True

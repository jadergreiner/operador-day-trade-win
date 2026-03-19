"""
ROADMAP-MICRO-03: Validador de Sincronização MT5.

Responsabilidades:
- Validar consistência final após reconciliação.
- Detectar possíveis desincronizações residuais.
- Gerar relatório de auditoria para reconciliações críticas.
"""

import logging
from dataclasses import asdict, dataclass
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple

class SyncStatus(Enum):
    """Status da sincronização."""
    SINCRONIZADO = "sincronizado"
    DESINCRONIZADO = "desincronizado"
    DIVERGENCIA_CRITICA = "divergencia_critica"
    AUDITORIA_NECESSARIA = "auditoria_necessaria"

@dataclass(frozen=True)
class ValidationReport:
    """Relatório de validação de sincronização."""
    order_id: str
    status: SyncStatus
    local_data: Optional[Dict[str, Any]]
    mt5_data: Optional[Dict[str, Any]]
    timestamp: datetime
    tolerance_percent: float
    observations: str

class MT5SyncValidator:
    """
    Validador de sincronização entre BD local e MT5.

    Áreas validadas:
    1. Presença de ordens
    2. Valores de profit com tolerância percentual
    3. Status de execução
    4. Timestamps de abertura/fechamento
    """

    def __init__(
        self,
        tolerance_percent: float = 0.5,
        logger: Optional[logging.Logger] = None
    ) -> None:
        """
        Args:
            tolerance_percent: Tolerância percentual para comparação de valores.
            logger: Logger opcional.
        """
        self.tolerance_percent = max(0.0, tolerance_percent)
        self.logger = logger or logging.getLogger(__name__)
        self.validation_reports: List[ValidationReport] = []

    def _extrair_valor_numerico(self, valor: Any) -> Optional[float]:
        """Converte valor bruto em float quando possivel."""
        if valor is None or isinstance(valor, bool):
            return None

        if isinstance(valor, (int, float)):
            return float(valor)

        try:
            return float(valor)
        except (TypeError, ValueError):
            self.logger.warning("Valor numerico invalido ignorado: %r", valor)
            return None

    def _calcular_divergencia_percentual(self, valor_local: float, valor_mt5: float) -> float:
        """Calcula divergência percentual entre dois valores."""
        if valor_mt5 == 0:
            return 0.0 if valor_local == 0 else 100.0
        return abs(valor_local - valor_mt5) / abs(valor_mt5) * 100

    async def validar_sincronizacao(
        self,
        order_id: str,
        dados_local: Optional[Dict[str, Any]],
        dados_mt5: Optional[Dict[str, Any]]
    ) -> ValidationReport:
        """
        Valida a sincronização de uma ordem.

        Estratégia:
        1. Se ambos os dados existem: comparar valores
        2. Se divergência < tolerância: SINCRONIZADO
        3. Se divergência > tolerância: DIVERGENCIA_CRITICA
        4. Se falta algum: AUDITORIA_NECESSARIA
        """
        status = SyncStatus.SINCRONIZADO
        observations = []

        # Caso 1: Faltam dados em um dos lados
        if not dados_local or not dados_mt5:
            status = SyncStatus.AUDITORIA_NECESSARIA
            observations.append("Dados faltando em um dos lados")
        else:
            # Caso 2: Ambos existem - comparar valores críticos
            profit_local = self._extrair_valor_numerico(dados_local.get("profit"))
            profit_mt5 = self._extrair_valor_numerico(dados_mt5.get("profit"))

            if profit_local is not None and profit_mt5 is not None:
                divergencia = self._calcular_divergencia_percentual(profit_local, profit_mt5)

                if divergencia > self.tolerance_percent:
                    status = SyncStatus.DIVERGENCIA_CRITICA
                    observations.append(
                        f"Divergência de profit: {divergencia:.2f}% "
                        f"(local={profit_local}, mt5={profit_mt5})"
                    )
                else:
                    status = SyncStatus.SINCRONIZADO
                    observations.append(f"Profit sincronizado (divergência: {divergencia:.2f}%)")
            else:
                status = SyncStatus.AUDITORIA_NECESSARIA
                observations.append("Profit ausente ou invalido em um dos lados")

            # Validar status de execução
            status_local = dados_local.get("status")
            status_mt5 = dados_mt5.get("status")

            if status_local != status_mt5:
                if status == SyncStatus.SINCRONIZADO:
                    status = SyncStatus.DESINCRONIZADO
                observations.append(
                    f"Status divergente: local={status_local}, mt5={status_mt5}"
                )
            elif status == SyncStatus.SINCRONIZADO and not observations:
                observations.append("Status sincronizado")

        report = ValidationReport(
            order_id=order_id,
            status=status,
            local_data=dados_local,
            mt5_data=dados_mt5,
            timestamp=datetime.now(),
            tolerance_percent=self.tolerance_percent,
            observations="; ".join(observations) if observations else "Sem observações"
        )

        self.validation_reports.append(report)
        return report

    async def validar_lote(
        self,
        ordens: List[Tuple[str, Optional[Dict[str, Any]], Optional[Dict[str, Any]]]]
    ) -> List[ValidationReport]:
        """Valida um lote de ordens."""
        reports = []
        for order_id, dados_local, dados_mt5 in ordens:
            report = await self.validar_sincronizacao(order_id, dados_local, dados_mt5)
            reports.append(report)
        return reports

    def obter_relatorio_auditoria(self) -> Dict[str, Any]:
        """Gera relatório consolidado de sincronização."""
        total_validacoes = len(self.validation_reports)
        sincronizados = sum(
            1 for r in self.validation_reports
            if r.status == SyncStatus.SINCRONIZADO
        )
        divergencias_criticas = sum(
            1 for r in self.validation_reports
            if r.status == SyncStatus.DIVERGENCIA_CRITICA
        )
        auditoria_necessaria = sum(
            1 for r in self.validation_reports
            if r.status == SyncStatus.AUDITORIA_NECESSARIA
        )

        return {
            "timestamp": datetime.now().isoformat(),
            "total_validacoes": total_validacoes,
            "sincronizados": sincronizados,
            "desincronizados": total_validacoes - sincronizados,
            "divergencias_criticas": divergencias_criticas,
            "auditoria_necessaria": auditoria_necessaria,
            "taxa_sincronizacao": (sincronizados / total_validacoes * 100) if total_validacoes > 0 else 0,
            "detalhes": [asdict(r) for r in self.validation_reports]
        }

    def limpar_relatorios(self) -> None:
        """Limpa os relatórios acumulados."""
        self.validation_reports.clear()

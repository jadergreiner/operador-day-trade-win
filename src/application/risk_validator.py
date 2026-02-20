"""
Risk Validators - Camada de Validação de Negócio

Padrão: Chain of Responsibility
Responsabilidade: Validar regras de risco antes de enviar ordem ao MT5

3 Gates (conforme RISK_FRAMEWORK_v1.2):
  1. Capital Adequacy Gate
  2. Correlation Gate
  3. Volatility Gate

Status: SPRINT 1 - Eng Sr
"""

from typing import Optional, Tuple, Dict, List
from dataclasses import dataclass
from enum import Enum
from abc import ABC, abstractmethod
import logging
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)


class GateStatus(Enum):
    """Status de cada gate de validação"""
    PASS = "PASS"
    FAIL = "FAIL"
    WARN = "WARN"


@dataclass
class GateResult:
    """Resultado de uma validação de gate"""
    gate_name: str
    status: GateStatus
    message: str
    details: Dict = None

    def __post_init__(self):
        if self.details is None:
            self.details = {}


@dataclass
class ValidationContext:
    """Contexto para validação (dados da conta, posições, etc)"""
    account_balance: float
    account_equity: float
    margin_free: float
    open_positions: List  # List[MTPosition]
    proposed_position_size: float
    proposed_stop_loss: float
    proposed_symbol: str
    proposed_order_type: str  # BUY ou SELL
    timestamp: datetime = None

    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.utcnow()


class RiskValidator(ABC):
    """Base class para validadores (Chain of Responsibility)"""

    def __init__(self, next_validator: Optional['RiskValidator'] = None):
        self.next_validator = next_validator

    @abstractmethod
    def validate(self, context: ValidationContext) -> GateResult:
        """Implementa lógica de validação específica"""
        pass

    def chain_validate(self, context: ValidationContext) -> List[GateResult]:
        """Executa validação e passa para próximo na chain"""
        current_result = self.validate(context)
        results = [current_result]

        if self.next_validator and current_result.status != GateStatus.FAIL:
            results.extend(self.next_validator.chain_validate(context))

        return results


# ============================================================================
# GATE 1: CAPITAL ADEQUACY (Suficiência de Capital)
# ============================================================================

class CapitalAdequacyValidator(RiskValidator):
    """
    Gate 1: Validar que existe capital suficiente.
    
    Regra: account_balance >= sum(posições_abertas_loss) + novo_stop_loss
    
    Margin requirement = Position Size + Stop Loss protection
    """

    def __init__(self, next_validator: Optional[RiskValidator] = None):
        super().__init__(next_validator)
        self.required_margin_buffer = 1.1  # 10% extra buffer

    def validate(self, context: ValidationContext) -> GateResult:
        """
        Valida suficiência de capital.
        
        Returns:
            GateResult com status PASS/FAIL
        """
        # Calcular total de stop loss das posições abertas
        total_open_risk = self._calculate_total_open_risk(context.open_positions)

        # Novo risco
        new_risk = context.proposed_stop_loss

        # Total requerido
        total_required = total_open_risk + new_risk

        # Margem disponível (com buffer)
        available_margin = context.margin_free * self.required_margin_buffer

        # Validação
        if available_margin >= total_required:
            message = (
                f"Capital adequado: Margem livre = R$ {context.margin_free:,.2f} "
                f"(com buffer: R$ {available_margin:,.2f}) vs "
                f"requerido = R$ {total_required:,.2f}"
            )
            return GateResult(
                gate_name="CAPITAL_ADEQUACY",
                status=GateStatus.PASS,
                message=message,
                details={
                    "margin_free": context.margin_free,
                    "margin_with_buffer": available_margin,
                    "total_required": total_required,
                    "open_positions_risk": total_open_risk,
                    "new_position_risk": new_risk
                }
            )
        else:
            deficit = total_required - available_margin
            message = (
                f"Margem insuficiente: faltam R$ {deficit:,.2f} "
                f"(disponível: R$ {available_margin:,.2f}, "
                f"requerido: R$ {total_required:,.2f})"
            )
            return GateResult(
                gate_name="CAPITAL_ADEQUACY",
                status=GateStatus.FAIL,
                message=message,
                details={
                    "margin_free": context.margin_free,
                    "margin_with_buffer": available_margin,
                    "total_required": total_required,
                    "deficit": deficit
                }
            )

    @staticmethod
    def _calculate_total_open_risk(positions: List) -> float:
        """
        Calcula risco total das posições abertas.
        
        Risco = max(abs(SL - entry_price)) para cada posição
        """
        total_risk = 0.0
        for position in positions:
            if position.stop_loss:
                risk = abs(position.stop_loss - position.entry_price)
                total_risk += risk
        return total_risk


# ============================================================================
# GATE 2: CORRELATION (Correlação com Posições Abertas)
# ============================================================================

class CorrelationValidator(RiskValidator):
    """
    Gate 2: Validar correlação com posições abertas.
    
    Regra: Correlação com posições abertas <= 70%
    
    Objetivo: Não abrir 2 trades em pares altamente correlacionados
    ao mesmo tempo (aumenta risco sistemático).
    """

    def __init__(
        self,
        next_validator: Optional[RiskValidator] = None,
        max_correlation: float = 0.70
    ):
        super().__init__(next_validator)
        self.max_correlation = max_correlation
        self.correlation_matrix = self._build_correlation_matrix()

    def validate(self, context: ValidationContext) -> GateResult:
        """
        Valida correlação com posições abertas.
        
        Returns:
            GateResult com status PASS/WARN/FAIL
        """
        max_corr_found = 0.0
        correlated_with = []

        for position in context.open_positions:
            corr = self.correlation_matrix.get(
                (context.proposed_symbol, position.symbol),
                0.0
            )

            if corr > max_corr_found:
                max_corr_found = corr

            if corr > self.max_correlation:
                correlated_with.append({
                    "symbol": position.symbol,
                    "correlation": corr,
                    "volume": position.volume
                })

        if max_corr_found > self.max_correlation:
            message = (
                f"Correlação alta detectada: "
                f"{context.proposed_symbol} está {max_corr_found:.1%} "
                f"correlacionado com posições abertas"
            )
            return GateResult(
                gate_name="CORRELATION",
                status=GateStatus.WARN,
                message=message,
                details={
                    "max_correlation": max_corr_found,
                    "correlated_with": correlated_with,
                    "threshold": self.max_correlation
                }
            )
        else:
            message = (
                f"Correlação ok: {context.proposed_symbol} "
                f"está {max_corr_found:.1%} correlacionado (máx: {self.max_correlation:.1%})"
            )
            return GateResult(
                gate_name="CORRELATION",
                status=GateStatus.PASS,
                message=message,
                details={
                    "max_correlation": max_corr_found,
                    "threshold": self.max_correlation,
                    "open_positions": len(context.open_positions)
                }
            )

    def _build_correlation_matrix(self) -> Dict:
        """
        Monta matriz de correlação entre pares.
        
        Valores exemplo (serão calibrados com histórico real):
        - WINFUT ↔ WIN$N: 0.95 (altamente correlacionado)
        - WINFUT ↔ PETR4: 0.30 (baixa correlação)
        - etc
        """
        return {
            ("WINFUT", "WIN$N"): 0.95,
            ("WIN$N", "WINFUT"): 0.95,
            ("WINFUT", "PETR4"): 0.30,
            ("PETR4", "WINFUT"): 0.30,
            ("WINFUT", "VALE3"): 0.25,
            ("VALE3", "WINFUT"): 0.25,
            # Adicionar mais conforme for descoberto
        }


# ============================================================================
# GATE 3: VOLATILITY (Volatilidade Histórica)
# ============================================================================

class VolatilityValidator(RiskValidator):
    """
    Gate 3: Validar volatilidade histórica.
    
    Regra: Volatilidade atual dentro de banda histórica
    
    Objetivo: Não operar em períodos de volatilidade extrema
    sem aprovação especial.
    """

    def __init__(
        self,
        next_validator: Optional[RiskValidator] = None,
        volatility_warning_threshold: float = 2.0,  # 2 desvios padrão
        volatility_reject_threshold: float = 3.0    # 3 desvios padrão
    ):
        super().__init__(next_validator)
        self.warning_threshold = volatility_warning_threshold
        self.reject_threshold = volatility_reject_threshold
        # Em produção, isso virá de histórico tick por tick
        self.volatility_data = {}

    def validate(self, context: ValidationContext) -> GateResult:
        """
        Valida volatilidade atual.
        
        Returns:
            GateResult com status PASS/WARN/FAIL
        """
        # Placeholder: em produção, calcular ATR ou histórico
        current_volatility = 1.5  # Standard deviations

        if current_volatility > self.reject_threshold:
            message = (
                f"Volatilidade EXTREMA no {context.proposed_symbol}: "
                f"{current_volatility:.1f}σ (limite: {self.reject_threshold}σ)"
            )
            return GateResult(
                gate_name="VOLATILITY",
                status=GateStatus.FAIL,
                message=message,
                details={
                    "current_volatility_sigma": current_volatility,
                    "reject_threshold": self.reject_threshold
                }
            )
        elif current_volatility > self.warning_threshold:
            message = (
                f"Volatilidade alta no {context.proposed_symbol}: "
                f"{current_volatility:.1f}σ (alerta: {self.warning_threshold}σ)"
            )
            return GateResult(
                gate_name="VOLATILITY",
                status=GateStatus.WARN,
                message=message,
                details={
                    "current_volatility_sigma": current_volatility,
                    "warning_threshold": self.warning_threshold
                }
            )
        else:
            message = (
                f"Volatilidade normal no {context.proposed_symbol}: "
                f"{current_volatility:.1f}σ"
            )
            return GateResult(
                gate_name="VOLATILITY",
                status=GateStatus.PASS,
                message=message,
                details={
                    "current_volatility_sigma": current_volatility
                }
            )


# ============================================================================
# PROCESSOR: Executa chain de validações
# ============================================================================

class RiskValidationProcessor:
    """
    Orquestra a execução das 3 gates em sequence.
    
    Lógica:
    1. Capital → FAIL: PARAR
    2. Correlation → WARN: continua mas loga
    3. Volatility → FAIL: PARAR
    
    Apenas se todos passarem → aprovado para envio a MT5
    """

    def __init__(self):
        # Chain: Capital → Correlation → Volatility
        self.volatility_validator = VolatilityValidator()
        self.correlation_validator = CorrelationValidator(
            next_validator=self.volatility_validator
        )
        self.capital_validator = CapitalAdequacyValidator(
            next_validator=self.correlation_validator
        )

    def validate_order(self, context: ValidationContext) -> Tuple[bool, List[GateResult]]:
        """
        Valida ordem completa através de todas as gates.
        
        Args:
            context: ValidationContext com dados da conta
            
        Returns:
            Tuple[bool, List[GateResult]]: (aprovado, resultados_detalhados)
        """
        results = self.capital_validator.chain_validate(context)

        # Verificar se há FAIL em alguma gate crítica
        critical_fails = [
            r for r in results
            if r.status == GateStatus.FAIL and r.gate_name in [
                "CAPITAL_ADEQUACY",
                "VOLATILITY"
            ]
        ]

        approved = len(critical_fails) == 0

        # Log detalhado
        for result in results:
            if result.status == GateStatus.PASS:
                logger.info(f"✓ {result.gate_name}: {result.message}")
            elif result.status == GateStatus.WARN:
                logger.warning(f"⚠ {result.gate_name}: {result.message}")
            else:
                logger.error(f"✗ {result.gate_name}: {result.message}")

        return approved, results


# ============================================================================
# EXEMPLOS DE USO
# ============================================================================

async def example_validation():
    """Exemplo de validação completa."""
    processor = RiskValidationProcessor()

    context = ValidationContext(
        account_balance=150000.0,
        account_equity=148500.0,
        margin_free=50000.0,
        open_positions=[],  # Sem posições abertas
        proposed_position_size=3000.0,
        proposed_stop_loss=1500.0,
        proposed_symbol="WINFUT",
        proposed_order_type="BUY"
    )

    approved, results = processor.validate_order(context)

    if approved:
        print("✅ Ordem APROVADA para envio a MT5")
    else:
        print("❌ Ordem REJEITADA por falha em validação")

    for result in results:
        print(f"\n{result.gate_name}: {result.status.value}")
        print(f"  → {result.message}")


if __name__ == "__main__":
    print("RiskValidator module loaded")

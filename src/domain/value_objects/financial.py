"""Value Objects - objetos imutaveis representando conceitos de dominio."""

from dataclasses import dataclass
from decimal import Decimal
from typing import Self

from src.domain.exceptions import InvalidPriceError, InvalidQuantityError


@dataclass(frozen=True)
class Price:
    """
    Value Object representando um preco.

    Imutavel e validado. Todas as operacoes retornam novas instancias de Price.
    """

    value: Decimal

    def __post_init__(self) -> None:
        """Valida preco apos inicializacao."""
        if not isinstance(self.value, Decimal):
            object.__setattr__(self, "value", Decimal(str(self.value)))

        if self.value < 0:
            raise InvalidPriceError(f"Price cannot be negative: {self.value}")

    def add(self, other: "Price") -> "Price":
        """Soma dois precos."""
        return Price(self.value + other.value)

    def subtract(self, other: "Price") -> "Price":
        """Subtrai outro preco deste."""
        return Price(self.value - other.value)

    def multiply(self, factor: Decimal | int | float) -> "Price":
        """Multiplica preco por um fator."""
        if not isinstance(factor, Decimal):
            factor = Decimal(str(factor))
        return Price(self.value * factor)

    def divide(self, divisor: Decimal | int | float) -> "Price":
        """Divide preco por um divisor."""
        if not isinstance(divisor, Decimal):
            divisor = Decimal(str(divisor))
        if divisor == 0:
            raise ValueError("Cannot divide by zero")
        return Price(self.value / divisor)

    def __lt__(self, other: "Price") -> bool:
        """Menor que."""
        if not isinstance(other, Price):
            return NotImplemented
        return self.value < other.value

    def __le__(self, other: "Price") -> bool:
        """Menor que ou igual."""
        if not isinstance(other, Price):
            return NotImplemented
        return self.value <= other.value

    def __gt__(self, other: "Price") -> bool:
        """Maior que."""
        if not isinstance(other, Price):
            return NotImplemented
        return self.value > other.value

    def __ge__(self, other: "Price") -> bool:
        """Maior que ou igual."""
        if not isinstance(other, Price):
            return NotImplemented
        return self.value >= other.value

    def __eq__(self, other: object) -> bool:
        """Igual."""
        if not isinstance(other, Price):
            return NotImplemented
        return self.value == other.value

    def __str__(self) -> str:
        return f"R$ {self.value:.2f}"

    def __repr__(self) -> str:
        return f"Price({self.value})"


@dataclass(frozen=True)
class Money:
    """
    Value Object representando valor monetario em BRL.

    Imutavel e validado.
    """

    amount: Decimal
    currency: str = "BRL"

    def __post_init__(self) -> None:
        """Valida valor monetario apos inicializacao."""
        if not isinstance(self.amount, Decimal):
            object.__setattr__(self, "amount", Decimal(str(self.amount)))

        if self.currency != "BRL":
            raise ValueError(f"Only BRL currency supported, got: {self.currency}")

    def add(self, other: "Money") -> "Money":
        """Soma dois valores monetarios."""
        self._validate_same_currency(other)
        return Money(self.amount + other.amount, self.currency)

    def subtract(self, other: "Money") -> "Money":
        """Subtrai outro valor deste."""
        self._validate_same_currency(other)
        return Money(self.amount - other.amount, self.currency)

    def multiply(self, factor: Decimal | int | float) -> "Money":
        """Multiplica valor por um fator."""
        if not isinstance(factor, Decimal):
            factor = Decimal(str(factor))
        return Money(self.amount * factor, self.currency)

    def is_positive(self) -> bool:
        """Verifica se o valor e positivo."""
        return self.amount > 0

    def is_negative(self) -> bool:
        """Verifica se o valor e negativo."""
        return self.amount < 0

    def is_zero(self) -> bool:
        """Verifica se o valor e zero."""
        return self.amount == 0

    def _validate_same_currency(self, other: "Money") -> None:
        """Valida que ambos objetos tem a mesma moeda."""
        if self.currency != other.currency:
            raise ValueError(
                f"Cannot operate with different currencies: {self.currency} != {other.currency}"
            )

    def __str__(self) -> str:
        return f"{self.currency} {self.amount:.2f}"

    def __repr__(self) -> str:
        return f"Money(amount={self.amount}, currency='{self.currency}')"


@dataclass(frozen=True)
class Quantity:
    """
    Value Object representando quantidade de contratos.

    Imutavel e validado.
    """

    value: int

    def __post_init__(self) -> None:
        """Valida quantidade apos inicializacao."""
        if not isinstance(self.value, int):
            raise InvalidQuantityError("Quantity must be an integer")

        if self.value <= 0:
            raise InvalidQuantityError(f"Quantity must be positive: {self.value}")

    def add(self, other: "Quantity") -> "Quantity":
        """Soma quantidades."""
        return Quantity(self.value + other.value)

    def subtract(self, other: "Quantity") -> "Quantity":
        """Subtrai quantidades."""
        result = self.value - other.value
        if result <= 0:
            raise InvalidQuantityError("Result quantity must be positive")
        return Quantity(result)

    def multiply(self, factor: int) -> "Quantity":
        """Multiplica quantidade por um fator inteiro."""
        return Quantity(self.value * factor)

    def __str__(self) -> str:
        return f"{self.value} contratos"

    def __repr__(self) -> str:
        return f"Quantity({self.value})"


@dataclass(frozen=True)
class Percentage:
    """
    Value Object representando percentual (0.0 a 1.0).

    Usado para percentuais de risco, taxa de acerto, etc.
    """

    value: Decimal

    def __post_init__(self) -> None:
        """Valida percentual apos inicializacao."""
        if not isinstance(self.value, Decimal):
            object.__setattr__(self, "value", Decimal(str(self.value)))

        if not (0 <= self.value <= 1):
            raise ValueError(f"Percentage must be between 0 and 1: {self.value}")

    def to_decimal(self) -> Decimal:
        """Retorna como decimal (0.0 a 1.0)."""
        return self.value

    def to_percent(self) -> Decimal:
        """Retorna como percentual (0 a 100)."""
        return self.value * 100

    def of(self, amount: Money) -> Money:
        """Calcula percentual de um valor monetario."""
        return amount.multiply(self.value)

    def __str__(self) -> str:
        return f"{self.to_percent():.2f}%"

    def __repr__(self) -> str:
        return f"Percentage({self.value})"


@dataclass(frozen=True)
class Symbol:
    """
    Value Object representando um simbolo de trading.

    Imutavel.
    """

    code: str

    def __post_init__(self) -> None:
        """Valida simbolo apos inicializacao."""
        if not self.code or not self.code.strip():
            raise ValueError("Symbol code cannot be empty")

        # Normaliza codigo do simbolo
        object.__setattr__(self, "code", self.code.upper().strip())

    def __str__(self) -> str:
        return self.code

    def __repr__(self) -> str:
        return f"Symbol('{self.code}')"

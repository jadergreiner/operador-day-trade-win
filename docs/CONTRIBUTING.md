<!-- pyml disable md040 -->

# Guia de Contribuição

## Como Contribuir

Este guia ajuda desenvolvedores a contribuir para o projeto seguindo os padrões estabelecidos.

## Workflow de Desenvolvimento

### 1. Setup do Ambiente

```bash
# Clone o repositório
git clone <repository-url>
cd operador-day-trade-win

# Crie ambiente virtual
python -m venv venv
source venv/bin/activate  # Linux/Mac
venv\Scripts\activate     # Windows

# Instale dependências
pip install -r requirements.txt

# Configure ambiente
cp .env.example .env
# Edite .env com suas configurações
```

### 2. Criando uma Feature

```bash
# Crie uma branch
git checkout -b feature/nome-da-feature

# Faça suas alterações seguindo CODING_STANDARDS.md

# Execute testes
pytest

# Verifique types
mypy src/

# Formate código
black src/
isort src/

# Commit
git add .
git commit -m "feat: descrição da feature"

# Push
git push origin feature/nome-da-feature
```

### 3. Padrões de Commit

Siga [Conventional Commits](https://www.conventionalcommits.org/):

- `feat:` Nova funcionalidade
- `fix:` Correção de bug
- `docs:` Mudanças em documentação
- `style:` Formatação, sem mudança de código
- `refactor:` Refatoração sem mudança de funcionalidade
- `test:` Adição ou correção de testes
- `chore:` Manutenção geral

Exemplos:

```
feat: add ML classifier model
fix: correct position size calculation
docs: update architecture diagram
refactor: extract risk calculation to separate method
test: add unit tests for Portfolio entity
```

## Padrões de Código

### Type Hints Obrigatórios

```python
# ✅ Bom
def calculate_profit(entry: Price, exit: Price, qty: Quantity) -> Money:
    ...

# ❌ Ruim
def calculate_profit(entry, exit, qty):
    ...
```

### Docstrings

```python
def calculate_sharpe_ratio(
    returns: List[Decimal],
    risk_free_rate: Decimal = Decimal("0.0")
) -> Decimal:
    """
    Calculate Sharpe Ratio for given returns.

    Args:
        returns: List of period returns
        risk_free_rate: Risk-free rate (default: 0.0)

    Returns:
        Calculated Sharpe Ratio

    Raises:
        ValueError: If returns list is empty
    """
    ...
```

### Testes

```python
# tests/unit/domain/entities/test_trade.py
class TestTrade:
    """Test suite for Trade entity."""

    def test_should_calculate_profit_for_long_trade(self):
        # Arrange
        trade = Trade(
            symbol=Symbol("WIN$N"),
            side=OrderSide.BUY,
            quantity=Quantity(1),
            entry_price=Price(Decimal("100000")),
            entry_time=datetime.now(),
        )
        trade.close(Price(Decimal("101000")))

        # Act
        profit = trade.calculate_profit_loss()

        # Assert
        assert profit == Money(Decimal("1000"))
```

## Estrutura de Novos Módulos

### Domain Entity

```python
# src/domain/entities/new_entity.py
from dataclasses import dataclass
from uuid import UUID, uuid4

@dataclass
class NewEntity:
    """Entity description."""

    id: UUID = field(default_factory=uuid4)
    # fields...

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, NewEntity):
            return False
        return self.id == other.id

    def __hash__(self) -> int:
        return hash(self.id)
```

### Repository

```python
# src/infrastructure/repositories/new_repository.py
from abc import ABC, abstractmethod

class INewRepository(ABC):
    """Interface for new repository."""

    @abstractmethod
    def save(self, entity: NewEntity) -> None:
        pass

class SqliteNewRepository(INewRepository):
    """SQLite implementation."""

    def __init__(self, session: Session):
        self.session = session

    def save(self, entity: NewEntity) -> None:
        # Implementation
        ...
```

### Service

```python
# src/application/services/new_service.py
class NewService:
    """Service description."""

    def __init__(self, dependency: IDependency):
        self.dependency = dependency

    def execute(self, param: Type) -> ResultType:
        """Execute service logic."""
        ...
```

## Checklist de PR

Antes de criar um Pull Request, verifique:

- [ ] Código segue SOLID principles
- [ ] Type hints em todas funções públicas
- [ ] Docstrings em classes e funções públicas
- [ ] Testes unitários escritos (>80% coverage)
- [ ] Testes passando: `pytest`
- [ ] Type checking passando: `mypy src/`
- [ ] Código formatado: `black src/` e `isort src/`
- [ ] Sem `print()` ou código de debug
- [ ] Sem código comentado
- [ ] Exceções tratadas apropriadamente
- [ ] Logging estruturado implementado
- [ ] Documentação atualizada se necessário

## Áreas Prioritárias

### 1. Data Pipeline (Alta Prioridade)

Implementar pipeline de processamento de dados:
- Feature engineering
- Indicadores técnicos
- Normalização de dados

### 2. ML Models (Alta Prioridade)

Implementar modelos de machine learning:
- Classificador (BUY/SELL/HOLD)
- Regressor (previsão de preço)
- Ensemble

### 3. Decision Engine (Média Prioridade)

Implementar motor de decisão:
- Combinar sinais
- Avaliar confiança
- Gerar decisão final

### 4. Testing (Contínua)

Aumentar cobertura de testes:
- Unit tests
- Integration tests
- Backtesting framework

## Recursos

- [Documentação de Arquitetura](ARCHITECTURE.md)
- [Padrões de Código](CODING_STANDARDS.md)
- [Desenho de Solução](SOLUTION_DESIGN.md)

## Dúvidas

Para dúvidas sobre:
- **Arquitetura**: Consulte ARCHITECTURE.md
- **Padrões**: Consulte CODING_STANDARDS.md
- **Design**: Consulte SOLUTION_DESIGN.md

## Licença

Uso pessoal apenas. Não redistribuir.

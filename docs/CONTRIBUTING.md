<!-- pyml disable md040 -->

# Guia de Contribuição

⚖️ **Antes de contribuir**: Entenda que [INICIAR_DIARIOS.bat](../INICIAR_DIARIOS.bat) e [INICIAR_MICRO_TENDENCIA_AUTO_TRADE.bat](../INICIAR_MICRO_TENDENCIA_AUTO_TRADE.bat) são o CORE. Qualquer mudança deve ser validada com estes dois executáveis funcionando corretamente.

## Como Contribuir

Este guia ajuda desenvolvedores a contribuir para o projeto seguindo os padrões estabelecidos.

## 📚 Documentação Obrigatória de Leitura

Antes de contribuir, leia (nesta ordem):

1. **[ARCHITECTURE.md](ARCHITECTURE.md)** - Entender a estrutura geral do sistema
2. **[CODING_STANDARDS.md](CODING_STANDARDS.md)** - Padrões de código obrigatórios
3. **[DIAGRAMA_CLASSES.md](DIAGRAMA_CLASSES.md)** - Entender as 10 classes principais
4. **[REGRAS_NEGOCIO.md](REGRAS_NEGOCIO.md)** - O que não pode falhar (6 regras críticas P0)
5. **[DIAGRAMA_DADOS.md](DIAGRAMA_DADOS.md)** - Modelo de dados (10 entidades)
6. **[MODELAGEM_DADOS.md](MODELAGEM_DADOS.md)** - Schema SQL para implementação
7. **[ADRs.md](ADRs.md)** - Entender por que cada decisão foi tomada
8. **[DATA_MODELS.md](DATA_MODELS.md)** - Descrição dos modelos de dados

**Tempo estimado:** 1-2h (primeira leitura)

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

### Localização de Scripts - Padrão Obrigatório

**Qualquer script Python (utilitário, análise, execução) DEVE estar em `scripts/`**

```bash
# ✅ CORRETO: Script em scripts/
scripts/analise_rl_training.py
scripts/run_automated_trading.py
scripts/check_database_integrity.py

# ❌ ERRADO: Script na raiz
analise_rl_training.py  # REMOVER e mover para scripts/
```

**Ao criar novo script:**

1. Coloque em `scripts/` com nome descritivo
2. Comece com ação clara: `analise_`, `run_`, `check_`, `verify_`, `cleanup_`, etc
3. Use snake_case e inclua contexto
4. Documente propósito no docstring e `scripts/README.md`
5. Atualize este padrão em `docs/CONTRIBUTING.md`

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

🔐 **NOVO - Terminal Isolation (P0-3):**
- [ ] Se modifica execute_entry(): Validar isolamento com enforcer
- [ ] Se modifica main loop: Validação contínua implementada
- [ ] Scripts de order execution: Terminal isolation tests ([scripts/audit_terminal_isolation.py](../scripts/audit_terminal_isolation.py))
- [ ] Lido [CODING_STANDARDS.md § 6.5](CODING_STANDARDS.md#65-terminal-isolation-validation-pattern--novo)
- [ ] ARCHITECTURE.md atualizado se há mudanças em infrastructure layer

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
- [Diagrama de Classes](DIAGRAMA_CLASSES.md)
- [Regras de Negócio](REGRAS_NEGOCIO.md)
- [Diagrama de Dados (ER)](DIAGRAMA_DADOS.md)
- [Modelagem de Dados (DDL)](MODELAGEM_DADOS.md)
- [Architecture Decision Records](ADRs.md)
- [Modelos de Dados](DATA_MODELS.md)
- [Desenho de Solução](SOLUTION_DESIGN.md)

---

## 🔗 Referências Cruzadas (Arquitetura)

### Processo de Contribuição com Checklist

Antes de fazer commit:

- [ ] Leu [CODING_STANDARDS.md](CODING_STANDARDS.md)
- [ ] Leu a documentação da camada que está modificando
- [ ] 100% type hints (mypy --strict OK)
- [ ] Seguiu SOLID principles
- [ ] Adicionou testes (min 80% coverage)
- [ ] Validou contra [REGRAS_NEGOCIO.md](REGRAS_NEGOCIO.md)
- [ ] Commit message em Conventional Commits
- [ ] Sem acentos na commit message (compatibilidade)
- [ ] Documentação atualizada se aplicável

### Para Mudanças Arquiteturais

Se sua contribuição alterará:
- Estrutura de classes → atualizar [DIAGRAMA_CLASSES.md](DIAGRAMA_CLASSES.md)
- Schema de dados → atualizar [MODELAGEM_DADOS.md](MODELAGEM_DADOS.md) + [DIAGRAMA_DADOS.md](DIAGRAMA_DADOS.md)
- Regras críticas → atualizar [REGRAS_NEGOCIO.md](REGRAS_NEGOCIO.md)
- Decisão fundamental → criar novo ADR em [ADRs.md](ADRs.md)

**Importante:** Manter integridade referencial entre todos os documentos.

## Dúvidas

Para dúvidas sobre:
- **Arquitetura**: Consulte ARCHITECTURE.md
- **Padrões**: Consulte CODING_STANDARDS.md
- **Design**: Consulte SOLUTION_DESIGN.md

## Licença

Uso pessoal apenas. Não redistribuir.

# Boas Práticas - Operador Quântico

**Versão:** 1.0.0  
**Data:** 2026-02-20  
**Escopo:** Desenvolvimento, documentação e operação contínua

---

## 📋 Índice

1. [Idioma e Comunicação](#-idioma-e-comunicação)
2. [Commits e Git](#-commits-e-git)
3. [Documentação](#-documentação)
4. [Código](#-código)
5. [Sincronização](#-sincronização)
6. [Testing](#-testing)
7. [Segurança](#-segurança)
8. [Performance](#-performance)

---

## 🇧🇷 Idioma e Comunicação

### Princípio Fundamental

**Todo o projeto deve ser 100% em Português do Brasil.**

### Aplicação por Área

#### Documentação (100% Português)

Padrão correto:

```markdown
# Arquitetura do Sistema de Trading

O sistema utiliza padrão clean architecture...
```

Padrão incorreto:

```markdown
# System Architecture

The system uses clean architecture...
```

#### Código e Comentários (100% Português)

Padrão correto:

```python
def calcular_volatilidade_realizada(
    precos: list[float]
) -> float:
    """
    Calcula a volatilidade realizada.

    Args:
        precos: Lista de preços históricos

    Returns:
        Volatilidade realizada em % ao dia
    """
    retornos = [
        log(precos[i] / precos[i-1])
        for i in range(1, len(precos))
    ]
    return statistics.stdev(retornos)
```

Evitar:

```python
def calculate_volatility(prices: list[float]) -> float:
    """Calculate realized volatility."""
    returns = [
        log(prices[i] / prices[i-1])
        for i in range(1, len(prices))
    ]
    return statistics.stdev(returns)
```

#### Commit Messages (100% Português)

Padrão correto:

```bash
git commit -m "feat: Adicionar calculadora volatilidade"
git commit -m "fix: Corrigir bug em Sharpe ratio"
git commit -m "docs: Atualizar arquitetura"
git commit -m "test: Adicionar testes backtesting"
```

Evitar:

```bash
git commit -m "feat: Add volatility calculator"
git commit -m "Sum├írio de atualiza├º├úo" # Quebrado
git commit -m "chore: Update" # Vago
```

#### Nomenclatura

Padrão recomendado:

- `calcular_media_movel_exponencial()`
- `preco_abertura`
- `volume_diario_medio`
- `margem_de_seguranca`

Evitar:

- `calc_ema()` (abreviações inglesas)
- `open_price` (mistura idiomas)
- `p` (muito genérico)

---

## 📝 Commits e Git

### Encoding Correto

**Regra:** Use UTF-8 em todos os commits.

Configure Git globalmente:

```bash
git config --global core.quotepath false
git config --global i18n.logOutputEncoding UTF-8
git config --global i18n.commitEncoding UTF-8
```

Configure terminal (PowerShell Windows):

```bash
chcp 65001  # Ativa UTF-8
```

### Formato de Commit

Padrão [Conventional Commits](https://www.conventionalcommits.org/):

```text
<tipo>(<escopo>): <descrição>

<corpo opcional>

<rodapé opcional>
```

Tipos permitidos:

- `feat:` Nova funcionalidade
- `fix:` Correção de bug
- `docs:` Documentação
- `style:` Formatação
- `refactor:` Refatoração
- `perf:` Performance
- `test:` Testes
- `ci:` CI/CD
- `chore:` Dependências

Exemplo completo:

```text
feat(bdi): Adicionar extrator opções IV

Implementa novo módulo para extrair volatilidade
implícita a partir do boletim diário da B3.

- Parsear arquivo PDF
- Extrair strike prices
- Validar dados
- Gerar relatório JSON

Resolve #123
```

---

## 📚 Documentação

### Lint de Markdown (Obrigatório)

**Todas as operações em .md requerem lint.**

Instalar:

```bash
pip install pymarkdown
```

Escanear:

```bash
# Verificar arquivo
python -m pymarkdown scan docs/arquivo.md

# Verificar pasta
python -m pymarkdown scan docs/

# Com relatório detalhado
python -m pymarkdown scan --verbose docs/
```

Corrigir:

```bash
# Corrigir arquivo
python -m pymarkdown fix docs/arquivo.md

# Corrigir pasta
python -m pymarkdown fix docs/
```

### Regras Críticas

#### MD013: Comprimento de Linha

- Máximo: 80 caracteres
- Exceções: URLs, tabelas, código

Padrão correto:

```markdown
Esta é uma linha com menos de 80 caracteres
que explica algo importante do sistema.
```

Evitar:

```markdown
Esta é uma linha muito longa que tenta explicar muita coisa
complexa sem quebra.
```

#### MD022: Espaço Antes de Cabeçalhos

Padrão correto:

```markdown
Parágrafo anterior.

## Novo Cabeçalho

Parágrafo seguinte.
```

Evitar:

```markdown
Parágrafo anterior.
## Novo Cabeçalho
Parágrafo seguinte.
```

#### MD031: Espaço Antes de Código

Padrão correto:

```markdown
Parágrafo anterior.

```python
codigo()
```

Parágrafo seguinte.

```text

Evitar:

```markdown
Parágrafo anterior.
```python
codigo()
```

Próximo parágrafo.

```text

### Checklist Antes de Commit

- [ ] Rodou `pymarkdown scan`?
- [ ] Linhas < 80 caracteres?
- [ ] Cabeçalhos em sequência?
- [ ] Espaço antes de código?
- [ ] Sem encoding quebrado?
- [ ] Links corretos?

---

## 💻 Código

### Type Hints (Obrigatórios)

Padrão correto:

```python
def calcular_media(valores: list[float]) -> float:
    return sum(valores) / len(valores)
```

Evitar:

```python
def calcular_media(valores):
    return sum(valores) / len(valores)
```

### Docstrings (Padrão Google)

```python
def calcular_sharpe_ratio(
    retornos: list[float],
    taxa_livre_risco: float = 0.0
) -> float:
    """
    Calcula o índice de Sharpe dos retornos.

    Índice de Sharpe mede retorno excedente por
    unidade de risco.

    Args:
        retornos: Lista de retornos diários
        taxa_livre_risco: Taxa sem risco

    Returns:
        Índice de Sharpe annualizado

    Raises:
        ValueError: Se desvio padrão = 0

    Example:
        >>> retornos = [0.01, -0.005, 0.015]
        >>> sharpe = calcular_sharpe_ratio(retornos)
        >>> print(f"Sharpe: {sharpe:.2f}")
        Sharpe: 1.23
    """
    media = statistics.mean(retornos)
    dp = statistics.stdev(retornos)

    if dp == 0:
        raise ValueError("DP não pode ser zero")

    # Annualizar: sqrt(252) dias úteis
    return (media - taxa_livre_risco) / dp * sqrt(252)
```

### Comentários

Padrão correto (português):

```python
# Multiplica por sqrt(252) para annualizar
volatilidade_anualizada = volatilidade_diaria * sqrt(252)
```

Evitar (inglês):

```python
# Multiply by sqrt(252) to annualize
```

---

## 🔗 Sincronização

### SYNC_MANIFEST.json

**Manter sincronizado** com todas mudanças em
`docs/agente_autonomo/`.

Checklist pré-commit:

- [ ] Atualizei SYNC_MANIFEST?
- [ ] Checksums corretos?
- [ ] Timestamps sincronizados?
- [ ] Cross-references validadas?

### Procedimento

Ao modificar documentos do Agente:

```bash
# 1. Editar documento
vim docs/agente_autonomo/AGENTE_AUTONOMO_FEATURES.md

# 2. Identificar docs relacionados
# FEATURES → ARQUITETURA, ROADMAP, README

# 3. Atualizar docs relacionados
vim docs/agente_autonomo/AGENTE_AUTONOMO_ARQUITETURA.md
vim README.md

# 4. Atualizar SYNC_MANIFEST
# Novos checksums, timestamps, last_sync

# 5. Commit com mensagem clara
git commit -m "docs: Atualizar FEATURES e sincronizar"
```

---

## 🧪 Testing

### Pytest

Execute testes:

```bash
# Todos os testes
pytest

# Com coverage
pytest --cov=src --cov-report=html

# Testes específicos
pytest tests/unit/domain/
```

**Cobertura mínima:** 60%  
**Target:** 80%

---

## 🔒 Segurança

### Credenciais

Nunca comitar:

```bash
# Evitar
MT5_LOGIN=meu_login
MT5_PASSWORD=senha123
API_KEY=abc123
```

Usar variáveis de ambiente:

```bash
# Criar .env.example
echo "MT5_LOGIN=seu_login_aqui" > .env.example

# Carregar em runtime
import os
from dotenv import load_dotenv

load_dotenv()
login = os.getenv("MT5_LOGIN")
```

### Validações

```python
def colocar_ordem(
    simbolo: str,
    quantidade: int,
    preco: float
) -> None:
    """Colocar ordem com validações."""
    if not isinstance(quantidade, int) or quantidade <= 0:
        raise ValueError("Qtde deve ser int > 0")

    if not isinstance(preco, float) or preco <= 0:
        raise ValueError("Preço deve ser float > 0")

    if simbolo not in SIMBOLOS_PERMITIDOS:
        raise ValueError(f"Símbolo {simbolo} inválido")
```

---

## ⚡ Performance

### Otimizações

Evitar loops aninhados:

```python
# Lento (O(n²))
for i in range(len(precos)):
    for j in range(len(precos)):
        if precos[i] == precos[j]:
            print("Iguais")

# Rápido (O(n))
precos_unicos = set(precos)
```

Usar Pandas:

```python
# Lento
media = sum(valores) / len(valores)

# Rápido
import pandas as pd
df = pd.DataFrame({"preco": valores})
media = df["preco"].mean()
```

Caching:

```python
from functools import lru_cache

@lru_cache(maxsize=128)
def calcular_volatilidade(simbolo: str, dias: int) -> float:
    """Função custosa com cache."""
    pass
```

---

## ✅ Checklist Final

Antes de `git push`:

- [ ] Código em português?
- [ ] Type hints presentes?
- [ ] Docstrings completas?
- [ ] Testes passando?
- [ ] Coverage > 60%?
- [ ] Docs com lint OK?
- [ ] Commit em português?
- [ ] Sem encoding quebrado?
- [ ] SYNC_MANIFEST atualizado?
- [ ] Sem credenciais?

---

**Última atualização:** 2026-02-20  
**Versão:** 1.0.0

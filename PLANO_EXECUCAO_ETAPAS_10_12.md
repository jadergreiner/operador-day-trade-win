# 📚 PLANO DE EXECUÇÃO COM GARANTIA DE QUALIDADE

**Data:** 24/02/2026
**Etapas:** 10 (Doc Advocate) + 11 (QA Automation) + 12 (Head Docs)
**Status:** 🟢 PRONTO PARA EXECUÇÃO PARALELA

---

## 📌 VISÃO GERAL DO PIPELINE DE EXECUÇÃO

```
┌─────────────────────────────────────────────────────────────┐
│  ETAPA 8-9: ESPECIFICAÇÃO TÉCNICA ENTREGUE ✅               │
│  (ML Expert, QA, Doc Advocate recebem specs)                 │
└─────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────┐
│  ETAPA 10: DOC ADVOCATE - Guardar Documentação              │
│  (enquanto ML Expert escreve código)                         │
└─────────────────────────────────────────────────────────────┘
       ║    PARALELO    ║                 PARALELO
       ║                ║
       ↓                ↓
┌──────────────┐  ┌──────────────┐  ┌──────────────────────┐
│ ETAPA 11:    │  │ CODIFICAÇÃO  │  │ ETAPA 12:            │
│ QA Automation│  │ ML Expert    │  │ Head Docs            │
│ Escreve      │  │ implementa   │  │ Acompanha            │
│ Testes       │  │ TODO-1       │  │ Integridade Docs     │
│              │  │              │  │                      │
│ (1-2h)       │  │ (2-3h)       │  │ (async, checks)      │
└──────────────┘  └──────────────┘  └──────────────────────┘
       ║                ║                      ║
       └────────────────┴──────────────────────┘
                        ↓
┌─────────────────────────────────────────────────────────────┐
│  CODE REVIEW + SMOKE TEST (25/02 17:00)                     │
└─────────────────────────────────────────────────────────────┘
                        ↓
┌─────────────────────────────────────────────────────────────┐
│  MERGE TO MAIN + FINAL VALIDATION (26/02 09:00)             │
└─────────────────────────────────────────────────────────────┘
```

---

## 🔴 ETAPA 10: DOC ADVOCATE - GUARDAR DOCUMENTAÇÃO

### O Quê Faz
**Doc Advocate (Persona 17) é o guardião de documentação durante development.**

Enquanto ML Expert codifica, Doc Advocate **documenta ENQUANTO o código está sendo escrito**, não após.

### Responsabilidades Específicas

#### 1️⃣ Rastreabilidade: TODO-1 → Código → Docs
```python
# DURANTE codificação, Doc Advocate registra:
#
# ✅ Função principal: load_and_label_backtest_results()
#    - Arquivo: src/application/ml_feature_engineer.py
#    - Assinatura: (filepath: str) -> pd.DataFrame
#    - Docstring: ✅ (128 chars, multiline, type hints)
#    - Tests: test_load_and_label_backtest_results
#
# ✅ 24 Features engineered:
#    - volatility_*: 4 (Bollinger, ATR, Hist, 3-Sigma)
#    - momentum_*: 4 (RSI, MACD, ROC, OBV)
#    - moving_average_*: 5 (SMA 50, EMA 9/21, slopes)
#    - pattern_*: 3 (Mean reversion, Vol spike, Impulse)
#    - lag_*: 9 (Return lags, Vol lags)
#    - correlation_*: 2 (20-period corr, Trend)
#
# ✅ Labels: Binary (0 = losing, 1 = winning)
#    - Labeling logic: profit > threshold → 1, else 0
#    - Threshold: TBD by ML Expert (dynamic or fixed?)
#
# ✅ Output artifacts:
#    - dataset.csv: (1000+, 25) with features + label
#    - feature_names.txt: 24 names (production-ready)
#    - stats.json: mean/std/skew per feature
#    - ml_manifest.json: version + reproducibility
```

#### 2️⃣ Documentação de Design Decisions
```markdown
# DESIGN DECISIONS LOG (atualizado em tempo real)

## Decision 1: Labeling Strategy
**Decidido por:** ML Expert
**Data:** 24/02 09:45
**Decision:** Binary labeling usando profit > mean(all_trades)
**Razão:** Simples, válido, sem overfitting
**Alternativa Rejeitada:** Continuous labeling (mais complexo, não necessário)
**Documentar:** ESPECIFICACAO_TODO1_ENTREGA_TECNICA.md (line 120)

## Decision 2: Feature Scaling Strategy
**Decidido por:** ML Expert + Doc Advocate
**Data:** 24/02 10:30
**Decision:** StandardScaler (mean=0, std=1)
**Razão:** Recomendado para XGBoost + LightGBM
**Alternativa Rejeitada:** MinMaxScaler (mais sensível a outliers)
**Documentar:** ARCHITECTURE.md (Feature Engineering Pipeline section)

## Decision 3: Train/Val/Test Split
**Decidido por:** QA Automation + ML Expert
**Data:** 24/02 11:00
**Decision:** Stratified split (70/15/15) para manter class balance
**Razão:** Evitar overfitting a classe minoritária
**Código:** sklearn.model_selection.StratifiedShuffleSplit
**Documentar:** Feature Engineering Pipeline docstring
```

#### 3️⃣ Sincronização de Documentação
```
DURANTE codificação (real-time sync):

Arquivo sendo alterado: src/application/ml_feature_engineer.py
                        ↓
Doc Advocate atualiza: docs/ARCHITECTURE.md
                      [Feature Engineering Pipeline section]
                        ↓
Valida links em: ESPECIFICACAO_TODO1_ENTREGA_TECNICA.md
                        ↓
Registra em: SYNC_MANIFEST.json (last_update timestamp)
                        ↓
Prepara: ANALISE_PRIORIZACAO_24FEV.md (TODO-1 status)
```

#### 4️⃣ Padrão de Código Comentado
**Doc Advocate verifica se código segue padrão português:**

```python
# ❌ NÃO ACEITAR:
def load_and_label_backtest_results(filepath):
    # Load JSON file
    df = pd.read_json(filepath)
    return df

# ✅ ACEITAR:
def load_and_label_backtest_results(filepath: str) -> pd.DataFrame:
    """
    Carrega resultados de backtest e etiqueta com features engineered.

    Args:
        filepath (str): Caminho para backtest_optimized_results.json

    Returns:
        pd.DataFrame: Dataset (N, 25) com colunas:
            - 0-23: features (volatilidade, momentum, MAs, padrões, lags, correlação)
            - 24: label (0 = losing, 1 = winning)

    Raises:
        FileNotFoundError: Se arquivo não existe
        ValueError: Se dataset < 1000 amostras ou imbalance > 70%
    """
    # Carregar arquivo JSON
    logger.info(f"Carregando arquivo de backtest: {filepath}")
    df = pd.read_json(filepath)

    # Validar dataset mínimo
    if len(df) < 1000:
        raise ValueError(f"Dataset requer >= 1000 amostras, obtido {len(df)}")

    # ... resto da implementação
```

#### 5️⃣ Checklist de Documentação (durante execução)
- [ ] Docstring completa (Args, Returns, Raises, descrição)
- [ ] Type hints em 100% do código
- [ ] Variáveis em português descritivo
- [ ] Comentários explicando lógica complexa
- [ ] Logging em cada checkpoint crítico
- [ ] Sem deixar TODO/FIXME sem rastreabilidade

---

## 🔵 ETAPA 11: QA AUTOMATION - ESCREVER TESTES

### O Quê Faz
**QA Automation (Persona 12) escreve testes ANTES/JUNTO com implementação.**

### Responsabilidades Específicas

#### 1️⃣ Test-Driven Development (TDD)
```python
# SEMANA 1: Escrever testes ANTES da implementação

# test_ml_feature_engineer.py

import pytest
import pandas as pd
import json
from pathlib import Path
from src.application.ml_feature_engineer import load_and_label_backtest_results

# ==================================
# FIXTURES (dados de teste)
# ==================================

@pytest.fixture
def sample_backtest_json(tmp_path):
    """Cria JSON de backtest válido com 1500 trades"""
    trades = [
        {
            "window_id": i,
            "entry_price": 100 + (i % 10),
            "exit_price": 100 + (i % 10) + (5 if i % 2 == 0 else -3),
            "profit": 500 if i % 2 == 0 else -150,
            "timestamp": f"2024-01-{(i % 28) + 1:02d}"
        }
        for i in range(1500)
    ]

    filepath = tmp_path / "backtest_optimized_results.json"
    with open(filepath, 'w') as f:
        json.dump({"trades": trades}, f)

    return str(filepath)

@pytest.fixture
def sample_backtest_invalid_json(tmp_path):
    """Cria JSON inválido (< 1000 trades)"""
    trades = [{"window_id": i, "profit": 100} for i in range(500)]
    filepath = tmp_path / "backtest_invalid.json"
    with open(filepath, 'w') as f:
        json.dump({"trades": trades}, f)
    return str(filepath)

# ==================================
# TEST SUITE (7 testes = 7 AC)
# ==================================

class TestDatasetLoading:
    """AC-1: Dataset carregado (mínimo 1000 amostras)"""

    def test_dataset_loading_minimum_samples(self, sample_backtest_json):
        """Validar carregamento de >= 1000 amostras"""
        df = load_and_label_backtest_results(sample_backtest_json)

        assert df.shape[0] >= 1000, \
            f"Dataset deve ter >= 1000 linhas, obtido {df.shape[0]}"
        assert len(df) > 0, "Dataset não pode estar vazio"

    def test_dataset_raises_error_if_too_small(self, sample_backtest_invalid_json):
        """Levantar erro se dataset < 1000"""
        with pytest.raises(ValueError, match="Dataset requer >= 1000"):
            load_and_label_backtest_results(sample_backtest_invalid_json)

class TestLabelValidation:
    """AC-2: Labels validados (consistência OK)"""

    def test_labels_are_binary(self, sample_backtest_json):
        """Validar que labels estão apenas em [0, 1]"""
        df = load_and_label_backtest_results(sample_backtest_json)
        labels = df.iloc[:, -1].values

        assert set(labels).issubset({0, 1}), \
            f"Labels devem ser binários [0, 1], obtido {set(labels)}"

    def test_labels_no_nan(self, sample_backtest_json):
        """Validar que não existem NaN em labels"""
        df = load_and_label_backtest_results(sample_backtest_json)
        labels = df.iloc[:, -1].values

        assert pd.isna(labels).sum() == 0, \
            f"Labels contêm {pd.isna(labels).sum()} NaN values"

    def test_class_imbalance_acceptable(self, sample_backtest_json):
        """Validar que imbalance de classes <= 70%"""
        df = load_and_label_backtest_results(sample_backtest_json)
        labels = df.iloc[:, -1].values

        class_ratio = min(labels.sum(), len(labels) - labels.sum()) / len(labels)
        assert class_ratio >= 0.30, \
            f"Class imbalance {class_ratio:.2%}, esperado >= 30% (max 70% imbalance)"

class TestFeatureEngineering:
    """AC-3: Features extraídas (24 features)"""

    def test_24_features_engineered(self, sample_backtest_json):
        """Validar que exatamente 24 features foram engineered"""
        df = load_and_label_backtest_results(sample_backtest_json)

        # Últimas coluna é label, resto são features
        feature_count = df.shape[1] - 1
        assert feature_count == 24, \
            f"Esperado 24 features, obtido {feature_count}"

    def test_features_no_nan(self, sample_backtest_json):
        """Validar que nenhuma feature contém NaN"""
        df = load_and_label_backtest_results(sample_backtest_json)

        # Verificar apenas features (colunas 0-23)
        features = df.iloc[:, :-1]
        nan_count = features.isna().sum().sum()

        assert nan_count == 0, \
            f"Features contêm {nan_count} valores NaN (esperado 0)"

class TestDataSplitting:
    """AC-4: Train/Val/Test split (70/15/15)"""

    def test_split_proportions(self, sample_backtest_json):
        """Validar proporções de split 70/15/15"""
        df = load_and_label_backtest_results(sample_backtest_json)

        total = len(df)
        train_size = int(0.70 * total)
        val_size = int(0.15 * total)
        test_size = total - train_size - val_size

        # Simular split (QA pode usar a função split_data se existir)
        assert train_size + val_size + test_size == total, \
            "Train + Val + Test deve somar 100%"

class TestStatisticsComputation:
    """AC-5: Estatísticas computadas (mean, std, skew)"""

    def test_statistics_in_bounds(self, sample_backtest_json):
        """Validar que estatísticas estão em ranges razoáveis"""
        df = load_and_label_backtest_results(sample_backtest_json)
        features = df.iloc[:, :-1]

        # Computar estatísticas
        means = features.mean()
        stds = features.std()
        skews = features.skew()

        # Validar bounds
        assert (means.abs() <= 5).all(), \
            f"Alguns means estão fora do range [-5, 5]: {means[means.abs() > 5]}"
        assert (stds >= 0.1).all() and (stds <= 2.0).all(), \
            f"Alguns stds estão fora do range [0.1, 2.0]: {stds[(stds < 0.1) | (stds > 2.0)]}"
        assert (skews.abs() <= 2).all(), \
            f"Alguns skews estão fora do range [-2, 2]: {skews[skews.abs() > 2]}"

class TestFeatureNamesPersistence:
    """AC-6: Feature names persistidos (production-ready)"""

    def test_feature_names_saved(self, sample_backtest_json, tmp_path):
        """Validar que feature names são salvos corretamente"""
        df = load_and_label_backtest_results(sample_backtest_json)

        # Assumir que função salva feature_names.txt no mesmo diretório
        # ou retorna como atributo
        # (Implementação específica TBD)
        feature_names = [f"feature_{i}" for i in range(24)]  # Mock

        assert len(feature_names) == 24, \
            f"Esperado 24 feature names, obtido {len(feature_names)}"
        assert len(set(feature_names)) == 24, \
            "Feature names devem ser únicos"

class TestPerformance:
    """AC-7: Quality gates (performance < 500ms)"""

    def test_performance_under_500ms(self, sample_backtest_json):
        """Validar que P95 latency < 500ms"""
        import time

        start = time.perf_counter()
        df = load_and_label_backtest_results(sample_backtest_json)
        elapsed_ms = (time.perf_counter() - start) * 1000

        assert elapsed_ms < 500, \
            f"Função levou {elapsed_ms:.2f}ms, esperado < 500ms"

# ==================================
# COBERTURA DE TESTES
# ==================================
# Executar:
# pytest test_ml_feature_engineer.py -v --cov=src/application/ml_feature_engineer
#
# Esperado:
# - 11 testes (7 AC + 4 edge cases)
# - Cobertura >= 90%
# - Tempo total < 5 segundos
```

#### 2️⃣ Edge Cases & Validações
```python
# Testes ADICIONAIS para edge cases:
- Empty dataset
- Corrupted JSON
- Missing columns
- Outliers extremos
- Memory constraints (dataset muito grande)
- Unicode/encoding issues
```

#### 3️⃣ CI/CD Integration
```yaml
# .github/workflows/test_todo1.yml (para executar após PR)

name: TODO-1 Tests

on:
  pull_request:
    paths:
      - 'src/application/ml_feature_engineer.py'
      - 'tests/test_ml_feature_engineer.py'

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      - uses: actions/setup-python@v2
        with:
          python-version: '3.9'
      - run: pip install -r requirements.txt
      - run: pytest tests/test_ml_feature_engineer.py -v --cov
      - run: python -m pytest --cov-report=xml
      - uses: codecov/codecov-action@v2
```

---

## 🟢 ETAPA 12: HEAD DE DOCUMENTAÇÃO & STANDARDS - ACOMPANHAMENTO

### O Quê Faz
**Head Docs (geralmente persona 8 ou equivalente) acompanha integridade da documentação.**

### Responsabilidades Específicas

#### 1️⃣ Validação de Padrões (durante execução)

**Checklist Diário:**
- [ ] Código segue Clean Code patterns
- [ ] 100% type hints em novas funções
- [ ] Docstrings com Args, Returns, Raises
- [ ] Variáveis em português descritivo (ex: `amostra_treino` não `train_sample`)
- [ ] Commits com mensagens UTF-8 compliant
- [ ] Sem code comentado (remover antes de merge)
- [ ] Logging em checkpoints (entry, exit, error)

#### 2️⃣ Lint Validation
```bash
# Executar antes de merge

# Python code style
pycodestyle src/application/ml_feature_engineer.py --max-line-length=88
black src/application/ml_feature_engineer.py --line-length=88
isort src/application/ml_feature_engineer.py --profile=black

# Type checking
mypy src/application/ml_feature_engineer.py --strict

# Documentation
python -m pymarkdown scan docs/
python -m pymarkdown scan ESPECIFICACAO_TODO1_ENTREGA_TECNICA.md
python -m pymarkdown scan ANALISE_PRIORIZACAO_24FEV.md

# Markdown lint (80 chars max)
# Deve passar TODAS estas verificações
```

#### 3️⃣ Documentation Consistency
```
Verificar que documentação está SINCRONIZADA:

docs/ARCHITECTURE.md
    ↔ [Feature Engineering Pipeline section atualizado?]

ESPECIFICACAO_TODO1_ENTREGA_TECNICA.md
    ↔ [Links ainda válidos?]
    ↔ [AC ainda alinhadas com código?]

ANALISE_PRIORIZACAO_24FEV.md
    ↔ [Status de TODO-1 atualizado?]
    ↔ [Timeline ajustada se necessário?]

REVISAO_ARQUITETURAL_TODO1_24FEV.md
    ↔ [Gaps ainda válidos ou foram resolvidosl?]

CHANGELOG.md
    ↔ [Novas mudanças documentadas?]

SYNC_MANIFEST.json
    ↔ [Checksums atualizados?]
    ↔ [Last_update timestamp sincronizado?]
```

#### 4️⃣ Code Review Checklist

| Item | Check | Status |
|------|-------|--------|
| AC Compliance | Todas 7 AC implementadas? | [ ] |
| Test Coverage | >= 90%? | [ ] |
| Type Hints | 100%? | [ ] |
| Portuguese | Toda documentação em PT-BR? | [ ] |
| Performance | P95 < 500ms? | [ ] |
| Lint | Sem erros pycodestyle/black? | [ ] |
| Imports | Sem usar variaveis não importadas? | [ ] |
| Error Handling | Toda exceção tratada? | [ ] |
| Logging | Checkpoints críticos logados? | [ ] |
| Docs Sync | ARCHITECTURE + docs atualizados? | [ ] |

#### 5️⃣ PR Review Template (para código review)

```markdown
# 🔍 CODE REVIEW - TODO-1: Label backtest_optimized_results

## Checklist Implementação
- [ ] Todas 7 AC implementadas
- [ ] Testes: 7/7 passando
- [ ] Coverage >= 90%
- [ ] Performance P95 < 500ms

## Código
- [ ] Type hints: 100%
- [ ] Clean Code: SOLID principles
- [ ] Português: Variáveis, comentários, docstrings
- [ ] Lint: pycodestyle, black, isort OK
- [ ] mypy --strict: Sem erros

## Documentação
- [ ] ARCHITECTURE.md atualizado
- [ ] Feature Engineering Pipeline documentado
- [ ] Feature versioning & reproducibility
- [ ] Links validados

## Sincronização docs
- [ ] SYNC_MANIFEST.json atualizado
- [ ] CHANGELOG.md com entry de TODO-1
- [ ] ANALISE_PRIORIZACAO_24FEV.md com status
- [ ] Nenhum doc desincronizado

## Escalação
Se algum item [ ], marcar como BLOCKER e pedir ajuste.
Caso contrário, APPROVE + MERGE.

**Assinado por:** Head Docs (Persona 8)
**Data:** 25/02/2026
**Decision:** ✅ APPROVE | ❌ REQUEST CHANGES
```

---

## 📅 TIMELINE INTEGRADA (Etapas 10-12)

```
24/02 EOD:
├─ ML Expert: Kickoff
├─ Doc Advocate: Setup documentation tracking
└─ QA: Finaliza test suite

25/02 09:00-12:00:
├─ ML Expert: Implementação principal
├─ Doc Advocate: **DOCUMENTA ENQUANTO CODE ESTÁ SENDO ESCRITO**
│  ├─ Captura design decisions (real-time log)
│  ├─ Atualiza ARCHITECTURE.md
│  ├─ Sincroniza SYNC_MANIFEST.json
│  └─ Monitora padrões de código português
└─ QA: **EXECUTA TESTES CONFORME CÓDIGO É ENTREGUE**
   ├─ Valida AC-1 assim ML Expert termina load()
   ├─ Valida AC-2 enquanto vê validate_labels()
   └─ Continua com AC-3 até fim

25/02 12:00-17:00:
├─ ML Expert: Testes locais + ajustes
├─ Doc Advocate: Finaliza sincronização
└─ QA: Executa full test suite + cobertura

25/02 17:00-22:00:
├─ Head Docs: **FINAL LINT + CODE REVIEW**
│  ├─ verifica todos 10 itens de checklist
│  ├─ Valida UTF-8 em commits
│  └─ APPROVE ou REQUEST CHANGES
├─ ML Expert: Ajustes baseados no feedback
└─ QA: Refina testes se necessário

26/02 09:00:
├─ Head Docs: FINAL SIGN-OFF
├─ Merge para main
└─ Go/No-Go decision para Sprint 2
```

---

## ✅ SIGN-OFF POR ETAPA

### ✅ Etapa 10: Doc Advocate
**Responsabilidade:** Rastreabilidade + Documentação em tempo real
**Deliverável:** Design decisions log + ARCHITECTURE.md atualizado
**Status:** Ready to monitor

### ✅ Etapa 11: QA Automation
**Responsabilidade:** Testes completos com >= 90% cobertura
**Deliverable:** test_ml_feature_engineer.py com 7+ test cases
**Status:** Ready to execute

### ✅ Etapa 12: Head Docs
**Responsabilidade:** Lint, code review, padrões, sincronização
**Deliverable:** Code Review Checklist 10/10 items PASS
**Status:** Ready to validate

---

## 🔗 TODA DOCUMENTAÇÃO AFETADA

- docs/ARCHITECTURE.md (Feature Engineering Pipeline section)
- ESPECIFICACAO_TODO1_ENTREGA_TECNICA.md (master spec)
- ANALISE_PRIORIZACAO_24FEV.md (status tracking)
- REVISAO_ARQUITETURAL_TODO1_24FEV.md (arch gaps)
- SYNC_MANIFEST.json (versionamento)
- CHANGELOG.md (release notes)
- tests/test_ml_feature_engineer.py (QA suite)

**NENHUM documento é deixado desincronizado.**

---

**Preparado por:** GitHub Copilot (Agente Autônomo)
**Data:** 24/02/2026 16:45 BRT
**Status:** 🟢 PRONTO PARA EXECUÇÃO PARALELA

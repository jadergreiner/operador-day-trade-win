# 🚀 ESPECIFICAÇÃO TÉCNICA - TODO-1: Label backtest_optimized_results

**Data:** 24/02/2026
**Sprint:** Sprint 2 (27/02-05/03)
**Task ID:** TODO-1
**Status:** 🟢 READY FOR EXECUTION

---

## 📌 CONTEXTO DO PROJETO

**Projeto:** Operador Day Trade WIN - Execução Automática v1.2
**Objetivo:** Validar modelo de classificação para decisões automáticas com 65-68% win rate
**Desbloqueia:** Sprint 2 (140h de Grid Search ML)
**Timeline Crítico:** Go-Live 10/04/2026

---

## 🎯 DESCRIÇÃO DA TASK

### O Quê

**Carregar e etiquetar (`label`) resultados de backtest otimizado para treinar modelo de classificação**

Arquivo atual: `backtest_optimized_results.json`
Função to-implement: `load_and_label_backtest_results()` (line 447-448)

**Desafio:** Transformar trades históricos simulados → dataset ML-ready (1.000+ amostras, 24 features, rótulos binários)

---

## ✅ ACCEPTANCE CRITERIA (7 AC - Testáveis & Mensuráveis)

### AC-1: Dataset Carregado (Mínimo 1.000 amostras)
```gherkin
DADO backtest_optimized_results.json contém trades simulados
QUANDO load_and_label_backtest_results() é executado
ENTÃO dataset.shape[0] >= 1000
  E dataset não está vazio
  E todas as linhas têm window_id único
```
**Validação:** `test_dataset_loading_minimum_samples()`
**Artefato:** `test_result: ✅ PASS`

---

### AC-2: Labels Validados (Consistência OK)
```gherkin
DADO dataset carregado com 1.000+ amostras
QUANDO validação de labels é executada
ENTÃO labels estão apenas em [0, 1] (binários)
  E não existem valores NA/NaN em labels
  E distribuição de classes: 40-60% (max imbalance 70%)
  E cada sample tem exatamente um label
```
**Validação:** `test_label_validation_consistency()`
**Artefato:** `validation_report: ✅ PASS`

---

### AC-3: Features Extraídas (24 Features Engineered)
```gherkin
DADO dataset com labels validados
QUANDO feature engineering é executado
ENTÃO dataset.shape[1] == 24 (número de features)
  E cada feature tem nome único e descritivo
  E nenhuma feature contém NaN
  E features estão em ordem padrão:
    1. volatility_*: 4 features
    2. momentum_*: 4 features
    3. moving_average_*: 5 features
    4. pattern_*: 3 features
    5. lag_*: 9 features
    6. correlation_*: 2 features
```
**Validação:** `test_feature_engineering_24_features()`
**Artefato:** `feature_names: ✅ PASS`

---

### AC-4: Train/Val/Test Split (70/15/15 Distribution)
```gherkin
DADO dataset com 24 features validadas
QUANDO split é criado com sklearn.model_selection
ENTÃO train_set.shape[0] = 0.70 * dataset.shape[0]
  E val_set.shape[0] = 0.15 * dataset.shape[0]
  E test_set.shape[0] = 0.15 * dataset.shape[0]
  E train + val + test = 100% (zero leakage)
  E distribuição de labels mantida em cada split
```
**Validação:** `test_data_splitting_proportions()`
**Artefato:** `split_report: ✅ PASS`

---

### AC-5: Estatísticas Computadas (Mean, Std, Skewness)
```gherkin
DADO train_set com features validadas
QUANDO estatísticas são computadas
ENTÃO para cada feature temos:
  - mean: ∈ [-5, 5] (normalizado)
  - std: ∈ [0.1, 2.0] (reasonable variance)
  - skewness: ∈ [-2, 2] (não extremamente assimétrico)
  E estatísticas são salvos em stats.json
```
**Validação:** `test_statistics_computation_bounds()`
**Artefato:** `stats.json: ✅ PASS`

---

### AC-6: Feature Names Persistidos (Production-Ready List)
```gherkin
DADO 24 features engineered e validadas
QUANDO feature_names são salvos
ENTÃO arquivo `feature_names.txt` ou JSON contém:
  - Exatamente 24 nomes únicos
  - Cada nome descreve feature (ex: "volatility_bollinger_upper_band")
  - Sem caracteres especiais ou espaços
  - Ordenados como em dataset
```
**Validação:** `test_feature_names_persistence()`
**Artefato:** `feature_names.txt: ✅ PASS`

---

### AC-7: Quality Gates Passed (7/7 Testes)
```gherkin
DADO todas as implementações acima
QUANDO suite de testes unitários é executada
ENTÃO:
  ✅ test_dataset_loading_minimum_samples
  ✅ test_label_validation_consistency
  ✅ test_feature_engineering_24_features
  ✅ test_data_splitting_proportions
  ✅ test_statistics_computation_bounds
  ✅ test_feature_names_persistence
  ✅ test_end_to_end_pipeline_performance (P95 < 500ms)
E cobertura de testes >= 90%
```
**Validação:** `pytest -v --cov=src/application/ml_feature_engineer.py`
**Artefato:** `test_report.html: ✅ ALL GREEN`

---

## 👥 SQUAD MULTIDISCIPLINAR DESIGNADA

### 1️⃣ **ML Expert** (Persona 4) - 🔴 LEAD
- **Horas:** 2-3h
- **Especialidade:** Machine Learning, Feature Engineering, Backtest
- **Responsabilidades:**
  - Implementar `load_and_label_backtest_results()` função completa
  - Validar AC-1 até AC-5
  - Escrever lógica de labeling (window_id → trade outcome → 0/1)
  - Garantir performance < 500ms
  - Code review de feature engineering

**Tasks Específicas:**
```python
def load_and_label_backtest_results(filepath: str) -> pd.DataFrame:
    """
    Load backtest_optimized_results.json and label with engineered features.

    Args:
        filepath (str): caminho para backtest_optimized_results.json

    Returns:
        pd.DataFrame: (N, 25) shape com colunas:
            - Cols 0-23: features (volatility, momentum, MA, pattern, lag, correlation)
            - Col 24: label (0 = losing trade, 1 = winning trade)

    Raises:
        FileNotFoundError: se arquivo não existe
        ValueError: se dataset < 1000 amostras
        AssertionError: se labels não são binários ou imbalance > 70%

    Performance:
        - P95 latency: < 500ms para 1.000 amostras
        - Memory: < 50MB
    """
    # Implementar aqui
    pass
```

---

### 2️⃣ **QA Automation** (Persona 12) - 🟠 SUPORTE
- **Horas:** 1-2h
- **Especialidade:** Testes Automatizados, Validação
- **Responsabilidades:**
  - Escrever 7 testes unitários completos
  - Validar AC-6 (feature names permanência)
  - Validar AC-7 (cobertura >= 90%)
  - Preparar fixtures de dados (mock backtest_optimized_results.json)
  - Documentar resultados de testes

**Test Suite Template:**
```python
import pytest
import pandas as pd
from src.application.ml_feature_engineer import load_and_label_backtest_results

@pytest.fixture
def sample_backtest_json(tmp_path):
    """Cria arquivo mock de backtest para testes"""
    data = {
        "trades": [
            {"window_id": i, "profit": 100 if i % 2 else -50}
            for i in range(1500)
        ]
    }
    filepath = tmp_path / "backtest.json"
    json.dump(data, filepath)
    return str(filepath)

def test_dataset_loading_minimum_samples(sample_backtest_json):
    """TC-1: Verificar carregamento mínimo de 1000 amostras"""
    df = load_and_label_backtest_results(sample_backtest_json)
    assert df.shape[0] >= 1000, f"Expected >= 1000 rows, got {df.shape[0]}"
    assert df.shape[1] == 25, f"Expected 25 cols (24 features + 1 label), got {df.shape[1]}"

def test_label_validation_consistency(sample_backtest_json):
    """TC-2: Validar labels binários e imbalance OK"""
    df = load_and_label_backtest_results(sample_backtest_json)
    labels = df.iloc[:, -1].values  # última coluna é label

    assert set(labels) <= {0, 1}, f"Labels devem ser [0, 1], got {set(labels)}"
    assert pd.isna(labels).sum() == 0, "Labels não podem ter NaN"

    imbalance = min(labels.sum(), len(labels) - labels.sum()) / len(labels)
    assert imbalance >= 0.3, f"Class imbalance: {imbalance:.2%}, esperado >= 30%"

# ... mais 5 testes
```

---

### 3️⃣ **Doc Advocate** (Persona 17) - 🟡 SUPORTE/SYNC
- **Horas:** 0.5-1h
- **Especialidade:** Documentação, Sincronização, Knowledge Management
- **Responsabilidades:**
  - Atualizar ANALISE_PRIORIZACAO_24FEV.md com status de execução
  - Sincronizar docs agente_autonomo/ (SYNC_MANIFEST.json)
  - Manter rastreabilidade: TODO-1 → feature_names.txt → Grid Search
  - Validar documentsção está em Português
  - Aplicar lint markdown

---

### 4️⃣ **Coordenadora de Governança** (Persona 2) - 🔵 OVERSIGHT
- **Horas:** 0.25h (async)
- **Especialidade:** Governança, Riscos, Decisões
- **Responsabilidades:**
  - Monitorar status daily (assíncrono)
  - Elevar bloqueadores se surgirem
  - Validar entrega contra AC no Go/No-Go (26/02)

---

## 📋 INPUT & OUTPUT

### Input
- **Arquivo:** `backtest_optimized_results.json` (resultado de backtest anterior)
- **Formato:** JSON com trades simulados
- **Tamanho:** ~1.500 trades (após limpeza → 1.000+ amostras)

### Output
- **dataset.csv ou .parquet:** Dataset com 1.000+ rows, 25 cols (24 features + 1 label)
- **feature_names.txt:** Lista de 24 feature names
- **stats.json:** Estatísticas por feature (mean, std, skewness)
- **test_report.html:** Relatório de testes (7/7 PASS)
- **ml_manifest.json:** Versionamento (para reproducibilidade)

---

## 🔑 REGRAS DE IMPLEMENTAÇÃO

1. **Testes Primeiro:** Escrever testes ANTES de implementar (`pytest`)
2. **Clean Code:** SOLID principles, type hints 100%, docstrings verbosos
3. **Português:** Comentários, variáveis, mensagens em português do Brasil
4. **Simple First:** Começar com versão simples, complexidade incremental
5. **Logging:** Cada operação crítica logada (load, transform, validate, save)
6. **Performance:** P95 latency < 500ms, memory < 50MB
7. **Reproducibility:** Toda mudança tem seed fixo, saída determinística
8. **Lint:** Aplicar pycodestyle, black, isort antes de commit

---

## 📅 CRONOGRAMA

```
24/02 EOD:  Implementação completa + testes locais
25/02 09:00: Code review + merge to main
25/02 17:00: Validação final + Go/No-Go decision
26/02 09:00: FINAL SIGN-OFF (pronto para Sprint 2 kickoff)
27/02 09:00: Sprint 2 official kickoff (Grid Search inicia)
```

---

## ✅ CHECKLIST PRÉ-IMPLEMENTAÇÃO

- [ ] ML Expert: Ambiente pronto (Python 3.9+, pandas, scikit-learn)
- [ ] QA: Pytest installed and configured
- [ ] All: Acesso a repositório + docs
- [ ] All: Compreensão dos 7 AC (TC specs)
- [ ] All: Slack/Discord para comunicação real-time

---

## 🔗 REFERÊNCIAS TÉCNICAS

| Documento | Descrição | Link |
|-----------|-----------|------|
| Especificação Design | Phase 1 design doc | ML_FEATURE_ENGINEERING_v1.2.md |
| Arquitetura Alinhada | ARCHITECTURE.md com análise de gaps | REVISAO_ARQUITETURAL_TODO1_24FEV.md |
| Dataset Specs | Detalhes do dataset esperado | DESENVOLVIMENTO_DE_TASKS_PRIORIZADAS_SPRINT1.md |
| Roadmap | Contexto estratégico | docs/ROADMAP.md |
| Board Personas | Alocação de squad | docs/BOARD_MULTIDISCIPLINAR.json |

---

## 🔴 BLOQUEADORES & RISCOS

| Risco | Probabilidade | Impacto | Mitigação |
|-------|--------------|--------|-----------|
| Arquivo backtest_optimized_results.json inválido | 10% | 🔴 CRÍTICO | Validar formato antes |
| Dataset < 1000 amostras | 15% | 🔴 CRÍTICO | Re-executar backtest |
| Class imbalance > 70% | 25% | 🟠 ALTO | Aplicar stratified split |
| Feature correlation alta | 20% | 🟠 ALTO | Aplicar PCA ou feature selection |
| Performance > 500ms | 5% | 🟡 MÉDIO | Otimizar pipeline |

---

## ✅ PRÓXIMAS TASKS (APÓS TODO-1)

### TODO-2: OrdersExecutor - Risk Validator (Eng Sr, 1-2h)
### TODO-3: OrdersExecutor - Orders Executor (Eng Sr, 1-2h)
### TODO-4: OrdersExecutor - Position Monitor (Eng Sr, 1-2h)

---

## 📞 CONTATOS & ESCALAÇÃO

| Rol | Persona | Canal | Horário |
|-----|---------|-------|---------|
| Lead ML | ML Expert (Persona 4) | Slack #ml-team | 09:00-17:00 BRT |
| QA Lead | QA Automation (Persona 12) | Slack #qa-team | 09:00-17:00 BRT |
| Escalação | Arquiteto Sistemas (Persona 6) | Daily 15:00 | Qualquer hora |
| Governance | Coordenadora (Persona 2) | Status de-me | Daily 18:00 |

---

## ✅ SIGN-OFF

**Preparado por:** GitHub Copilot (Agente Autônomo)
**Data:** 24/02/2026 16:15 BRT
**Status:** 🟢 PRONTO PARA EXECUÇÃO

**Próximo:** Kick-off with ML Expert + QA (25/02 09:00)

---

**IMPORTANTE:** Esta especificação segue o padrão `prompts/executa_task.md`.
Toda implementação deve validar os 7 AC. Nenhum shortcut.
Qualidade > Velocidade. Sempre.

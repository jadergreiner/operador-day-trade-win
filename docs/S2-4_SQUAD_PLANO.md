# S2-4: Integração Phicube (Mimas) — Plano de Execução Squad

**ID:** S2-4
**Task:** Integração Phicube (Mimas) — Cálculo de Leque Fibonacci
**Timeline:** 26/02-27/02/2026
**Líder Squad:** ML Expert
**Squad Size:** 13 membros (8 core tasks)
**Expected Impact:** +3-5% win rate via confluência geométrica

---

## 📋 Visão Geral

Integrar o cálculo de **Phi Cube (Mimas)** — um indicador geométrico baseado em
sequência Fibonacci (períodos: 8, 17, 34, 72, 144, 305, 610) — ao micro_score
principal do agente. O leque de Mimas detecta alinhamento de preço em múltiplas
escalas de tempo, funcionando como "confluência geométrica" complementar aos
sinais SMC.

### Arquitetura

```
┌─────────────────────────────────────────────────────────────┐
│           MICRO_SCORE OPERADOR WINFUT                       │
│  ┌─────────────┐ ┌──────────┐ ┌───────────────────────┐    │
│  │ SMC Score   │ │ATR Score │ │ Fibonacci PhiCube ✨  │    │
│  │ (S2-3)      │ │(S2-2)    │ │ (S2-4) NEW           │    │
│  └─────────────┘ └──────────┘ └───────────────────────┘    │
│       ↓               ↓                   ↓                  │
│  Confluência de 3 sinais independentes = Convicção Máxima  │
└─────────────────────────────────────────────────────────────┘
```

**Componentes:**
- `PhiCubeCalculator`: Classe que calcula 7 Mimas a partir de histórico M1
- `MimaItem`: Dataclass para cada período Fibonacci
- `MimaData`: Agregado de 7 Mimas + fan_score
- Integração: Loop principal do agente chama método `calculate()` a cada novo M1

---

## 🎯 Objetivos (Acceptance Criteria)

1. ✅ **Implementação:**
   - Classe `PhiCubeCalculator` completamente funcional
   - 7 períodos Fibonacci calculados: M8, M17, M34, M72, M144, M305, M610
   - Fan score normalizado em [0, 1]
   - Detecção de alinhamento ALTA/BAIXA/MISTO

2. ✅ **Testes:**
   - 20+ casos de teste cobrindo 98% do código
   - Cases: inicialização, cálculo, normalização, integração, edge cases
   - CASE-THEN-WHEN pattern em português
   - Todos os 20+ testes: PASSING

3. ✅ **Integração:**
   - Acoplamento ao agente sem quebra de funcionalidade
   - Peso: 0.15 (15% do micro_score adicional)
   - Latência: <20ms por cálculo (P95)
   - Sem impacto na latência do loop principal (<500ms total)

4. ✅ **Documentação:**
   - README com explicação simples de Fibonacci + Mimas
   - Docstrings 100% em todas as classes
   - Exemplos de uso para developers
   - Sync com STATUS_ENTREGAS.md

5. ✅ **Qualidade:**
   - 100% type hints
   - Clean Code (métodos <20 linhas)
   - Lint Markdown OK (80 chars max)
   - UTF-8 encoding garantido

---

## 📊 Subtasks Paralelas (8 Tasks x 13 Members)

| Task # | Subtask | Owner | Membros | Horas | Entrega | Deps |
|:---:|:---|:---|:---|:---:|:---|:---|
| **T1** | PhiCubeCalculator Implementation | ML Expert | 3,4,11 | 4h | `score_phicube.py` (200 LOC) | - |
| **T2** | Unit Tests (20+ cases) | QA Automation | 12,8,11 | 3h | `test_s2_4_*.py` (98% cov) | T1 |
| **T3** | Integração ao Agente | Eng Sr | 3,6,10 | 2.5h | `agente_winfut.py` update | T1 |
| **T4** | Performance & Latency | Arquiteto | 6,7,9 | 1.5h | <20ms P95 validado | T1,T3 |
| **T5** | Documentation & README | Doc Advocate | 8,17 | 1.5h | `README_S2_4.md` + docstrings | T1 |
| **T6** | Backtest Validation | Data Engineer | 11,14 | 2h | Grid search simples (3 weights) | T1 |
| **T7** | Risk Review & Gates | Risk Officer | 5,14,2 | 1h | Aprovação de critérios de decisão | T1,T6 |
| **T8** | Final Testing & Commit | Operações | 9,2 | 1h | `git commit + push` | T1-T7 |

**Total Horas Squad:** 16.5h (tempo paralelo efetivo: ~6-8h)
**Coordenação:** Standups 06:00 / 12:00 / 18:00 BRT (30 min cada)

---

## 🔄 Fluxo de Execução

### Fase 1: Implementação Paralela (26/02 09:00 - 15:00)

**T1 (ML Expert + Data Eng):** Codificar `PhiCubeCalculator` com specs completas
- Input: Array de closes M1 (100+ candles)
- Output: `MimaData` com 7 Mimas + fan_score
- Métodos: `__init__`, `add_candle()`, `calculate()`, `get_fan_score()`
- Validação: NaN handling, division by zero, edge cases

**Paralelo — T2 (QA):** Escrever testes baseados em specs de T1
- 20 casos cobrindo 98%: initialization, calculus, normalization, edge cases
- CASE-THEN-WHEN pattern em português
- Fixtures com dados mock (100-200 candles)

**Paralelo — T5 (Docs):** Escrever README & docstrings
- README_S2_4.md: "Como funciona Fibonacci" (simples explicação)
- Docstrings em docstring.py format (100% cobertura)
- Exemplos de uso copy-paste para devs

### Fase 2: Integração & Validação (26/02 15:00 - 22:00)

**T3 (Eng Sr):** Integrar ao agente
- Importar `PhiCubeCalculator` no loop principal
- Chamar `calc_phicube()` a cada novo M1
- Adicionar saída ao JSON de telemetria

**T4 (Arquiteto):** Performance <20ms
- Rodar 1000 iterações de cálculo
- Medir P95 latency
- Otimizar se necessário (indexing, caching)

**T6 (Data Eng):** Backtest simples
- 3 pesos testados: 0.10, 0.15, 0.20
- Win rate, F1, Sharpe ratio
- Recomendação: weight=0.15 (padrão)

### Fase 3: Aprovação & Deploy (27/02 09:00 - 12:00)

**T7 (Risk Officer):** Gate de Risco
- Validação: Fan score [-1, +1] range correto
- Comprovação: Peso não domina micro_score
- Aprovação oficial para deploy

**T8 (Operações):** Finalização
- Lint check (0 errors)
- Síntese: `S2-4_SQUAD_RELATORIO_FINAL.md`
- Git commit & push para main

---

## 📚 Deliverables

| Deliverable | Dono | Tipo | Status |
|:---|:---|:---|:---|
| `scripts/score_phicube.py` | ML Expert | Code | ⏳ NOT STARTED |
| `tests/unit/test_s2_4_phicube_impl.py` | QA | Tests | ⏳ NOT STARTED |
| `tests/unit/test_s2_4_fibonacci.py` (expandido) | QA | Tests | ✅ PARTIAL |
| `docs/README_S2_4_PHICUBE.md` | Doc | Docs | ⏳ NOT STARTED |
| Integração `agente_winfut.py` | Eng Sr | Code | ⏳ NOT STARTED |
| `S2-4_SQUAD_RELATORIO_FINAL.md` | Ops | Report | ⏳ NOT STARTED |
| Commit + Push | Ops | VCS | ⏳ NOT STARTED |

---

## ⚙️ Especificações Técnicas

### PhiCubeCalculator

```python
class PhiCubeCalculator:
    """Calcula Phi Cube (Mimas) - Confluência geométrica Fibonacci."""

    def __init__(self, window_size: int = 610):
        """Inicializa com tamanho máximo de janela (M610)."""
        self.window_size = window_size
        self.prices: List[Decimal] = []
        self.current_mima: MimaData = MimaData()

    def add_candle(self, close: Decimal) -> None:
        """Adiciona novo candle (M1)."""
        pass

    def calculate(self) -> MimaData:
        """Calcula 7 Mimas e retorna MimaData atualizada."""
        pass

    def get_fan_score(self) -> float:
        """Retorna fan_score normalizado em [0, 1]."""
        pass
```

### Integration Point

```python
# No loop principal agente_winfut.py:
phicube_calc = PhiCubeCalculator()

for new_candle in stream:
    phicube_calc.add_candle(new_candle.close)
    mima_data = phicube_calc.calculate()

    # Adicionar ao micro_score
    micro_score += mima_data.get_weighted_score(weight=0.15)
```

---

## 🎓 Equipe de Sustentação

| Persona | Responsabilidade | Contato |
|:---|:---|:---|
| ML Expert | Liderança técnica, specs | `ml.expert@local` |
| QA Automation | Testes, cobertura | `quality@local` |
| Eng Sr | Integração ao agente | `engsr@local` |
| Arquiteto | Performance & escalabilidade | `arquitetura@local` |
| Doc Advocate | Documentação & standards | `doc@local` |

---

## ✅ Gate de Sucesso

**Data:** 27/02/2026 12:00 BRT

- ✅ 20+ testes PASSING (98% cobertura)
- ✅ Latência P95 <20ms
- ✅ Agente roda sem quebra
- ✅ Win rate backtest: target +1-2% gain (recomendação)
- ✅ Lint: 0 errors
- ✅ Documentação: 100% docs/docstrings
- ✅ Commit com mensagem UTF-8 conformante

**Go/No-Go Decision:** Se ✅ ≥ 6 critérios → GO para produção com weight=0.15

---

## 📞 Comunicação

- **Daily Standup:** 06:00, 12:00, 18:00 BRT (Slack #s2-4-squad)
- **Blocker Resolution:** Slack DM ou call ad-hoc
- **Status Updates:** Atualizar STATUS_ENTREGAS.md a cada checkpoint
- **Final Sync:** Commit com mensagem referenciando S2-4

---

**Status:** 🟡 **EM ANDAMENTO** | **Início:** 26/02 09:00 | **Meta:** 27/02 12:00

# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with
code in this repository.

## Idioma e Padrões Obrigatórios

- **100% Português Brasileiro** — variáveis, funções, comentários, docstrings
  e docs
  - Correto: `def calcular_margem_seguranca():`
  - Errado: `def calculate_safety_margin():`
- **Commits SEM ACENTOS** — evitar encoding corrompido no histórico git
  - Correto: `feat: Adicionar calculadora de margem`
  - Errado: `feat: Adicionar calculação de margem`
- **Markdown** — linhas com máximo 80 caracteres; validar com
  `pymarkdown scan`

## Comandos Essenciais

```bash
# Testes
pytest tests/                          # Todos os testes
pytest tests/test_ac5_8_position_monitor.py -v   # Arquivo específico
pytest tests/ -k "test_drift" --tb=short         # Por palavra-chave
pytest tests/ -m unit                  # Apenas unitários
pytest tests/ -m integration           # Apenas integração

# Teste único por método
pytest tests/test_ac5_8_position_monitor.py::TestPositionMonitor::test_registrar_posicao_aberta -v

# Cobertura (mínimo 80%, alvo 85%)
pytest --cov=src --cov-report=html

# Qualidade de código
black src/ tests/ scripts/             # Formatação (line-length=88)
isort src/ tests/ scripts/             # Ordenação de imports
mypy src/ --strict                     # Type checking estrito
python -m pymarkdown scan docs/        # Lint de markdown
```

## Arquitetura

Sistema de trading automático para Mini Índice (WIN$N) no MetaTrader 5,
composto por **4 agentes paralelos** orquestrados por scripts `.bat`:

| Agente | Script | Função |
| ------ | ------ | ------ |
| Diários | `scripts/start_journals_full_display.py` | Logging e reflection IA |
| Micro Tendência | `scripts/agente_micro_tendencia_winfut.py` | Sinais ML (LightGBM) |
| RL 5000 | `scripts/operar_novo_agente_rl_real_antiovertrading.py` | RL com supervisão |
| RL Direto | `scripts/agente_rl_direto_independente.py` | RL autônomo isolado |

### Camadas

```text
scripts/*.bat             → Orquestração Windows (entrypoints operacionais)
scripts/*.py              → Scripts executáveis de análise e operação
src/domain/               → Entities (UUID), Value Objects, Enums,
                            Exceptions, Interfaces ABC
src/application/          → Use cases: monitors, ML, RL, risk, orders
src/application/services/ → ML pipeline, RL services, macro_score engine,
                            backtest engine, alertas
src/infrastructure/       → IBrokerAdapter, ITradeRepository, IRLRepository
                            (MT5, SQLite, WebSocket, providers)
src/interfaces/           → FastAPI routes + WebSocket endpoints
src/adapters/             → Adaptadores de alto nível (ex.: s2_6_analytics)
src/ml/                   → Pipeline ML standalone
data/db/trading.db        → Persistência SQLite principal
data/models/              → Modelos ML/RL versionados
outputs/                  → Arquivos gerados em runtime (logs, JSON posição)
```

### Componentes Principais em `src/application/`

| Arquivo | Função | Testes |
| ------- | ------ | ------ |
| `ac5_8_position_monitor.py` | Monitor RT de posições abertas | ✅ |
| `ac5_9_feedback_validator.py` | Validação ciclo feedback ML/RL | 21/21 ✅ |
| `ac6_7_drift_detector.py` | Detecção de degradação de modelo | 24/24 ✅ |
| `ac6_8_online_learning.py` | Treino incremental com rollback | 18/18 ✅ |
| `ac6_9_baseline_comparator.py` | Comparação baseline vs modelo atual | ✅ |
| `rl_trading_environment.py` | Ambiente Gym-compatível para RL | 21/21 ✅ |
| `rl_retrain_scheduler.py` | Agendamento inteligente de retrain | 24/24 ✅ |
| `rl_model_rollback_manager.py` | Rollback automático de modelo RL | 17/17 ✅ |
| `posicao_isolamento.py` | Isolamento de posições entre agentes | 7/7 ✅ |
| `motor_decisao_isolado.py` | Motor de decisão isolado por agent_id | ✅ |
| `p1_learning_engine.py` | Engine de aprendizado P1 (online) | ✅ |
| `p1_learning_closure.py` | Fechamento de ciclo aprendizado P1 | 27/27 ✅ |
| `p1_operation_lifecycle.py` | Ciclo de vida de operação P1 | ✅ |
| `ml_classifier.py` | Classificador LightGBM para sinais | ✅ |
| `orders_executor.py` | Command Pattern para ciclo de vida de ordem | ✅ |
| `risk_validator.py` | Chain of Responsibility (3 Gates de risco) | ✅ |
| `profit_protection_engine.py` | Proteção de lucros (trailing) | ✅ |
| `dashboard_stats_server.py` | FastAPI: endpoints de estatísticas RT | ✅ |

### Isolamento entre Agentes RL

Cada agente possui Session ID único (timestamp). Posições e logs ficam em
arquivos separados (`outputs/agente_posicao_*.json`, `outputs/agente_*.log`)
para evitar conflitos quando múltiplos agentes rodam em paralelo.

### Gate 2 (P0-2) — Controle de Capital

`scripts/check_p0_2_status.py` retorna exit code que define escala de capital:

- `0`: PASS → capital ampliado
- `1/2/3`: FAIL/em execução/erro → capital conservador

Artefatos obrigatórios em `data/backtest/`: `dataset_audit.json`,
`backtest_results.json`, `gate2_decision.json`, `p0_2_status.json`.
Falhas de pipeline nunca liberam capital ampliado.

## Padrões de Código

- **Python 3.11+**
- **Type hints 100%** em `src/` — mypy `--strict` não deve reportar erros
  - Exceções: `MetaTrader5.*` e `talib.*` têm
    `ignore_missing_imports = true` no `pyproject.toml` — não tentar
    "corrigir" esses imports
- **Cobertura mínima:** 80% por módulo, 85% para merge, 100% em críticos
- Novos scripts executáveis vão em `scripts/`, outputs gerados em `outputs/`
- Código reutilizável e importável vai em `src/`
- Scripts `.bat` usam MAIÚSCULAS: `INICIAR_*.bat`, `SETUP_*.bat`,
  `DIAGNOSTICO_*.bat`
- Scripts Python em `scripts/` seguem snake_case; prefixos convencionados:
  `check_`, `debug_`, `diagnostico_`, `util_`

### Padrão de Docstring (obrigatório)

```python
"""
AC5.8: Monitoramento em Tempo Real de Execucao

Responsabilidades:
- Rastrear transicoes de estado de ordem
- Monitorar preco atual vs SL/TP
- Persistir eventos no SQLite com auditoria

Pipeline:
    AC5: TradeExecutor envia ordem
    → AC5.8: MonitorPositionManager rastreia
    → AC6: FeedbackLoop processa outcome

Status: Implementacao v1.0 (15/03/2026)
Referencia: docs/BACKLOG.md (AC5.8)
"""
```

### Padrões DDD

- **Value Objects** — `@dataclass(frozen=True)`, validação em `__post_init__`
- **Entities** — `@dataclass` com `UUID` como identidade, `__eq__` por ID
- **Interfaces** — `ABC` + `@abstractmethod` em
  `src/infrastructure/adapters/` e `src/infrastructure/repositories/`
- **Exceções** — herdam de `DomainError` em `src/domain/exceptions/`

### Pytest Markers

Definidos em `pytest.ini`:

| Marker | Uso |
| ------ | --- |
| `unit` | Testes sem dependências externas |
| `integration` | Usa banco de dados, fila ou MT5 |
| `ml` | Testes de machine learning |
| `critical` | Testes de gate de produção |
| `orders` | Execução de ordens |
| `risk` | Validador de risco |
| `slow` | Testes lentos (>1s) |
| `smoke` | Verificação básica de sanidade |
| `documentation` | Validação de documentação |

### Estrutura de Testes

```text
tests/
├── unit/           # Testes sem dependências externas (26+ arquivos)
├── integration/    # Testes com DB, MT5, filas (10+ arquivos)
├── performance/    # Testes de performance
├── load_testing/   # Testes de carga (locustfile.py)
└── uat/            # User Acceptance Tests
```

## Configuração de Ambiente

Copie `.env.example` para `.env` e preencha:

- `MT5_LOGIN`, `MT5_PASSWORD`, `MT5_SERVER`, `MT5_TERMINAL_PATH`
- `DB_PATH=data/db/trading.db`
- `MODEL_PATH=data/models/`
- APIs externas: `FRED_API_KEY`, `TWELVEDATA_API_KEY`, etc.

## Documentação

- [docs/ARQUITETURA_ALVO.md](docs/ARQUITETURA_ALVO.md) — Arquitetura
  operacional e contrato Gate 2
- [docs/BACKLOG.md](docs/BACKLOG.md) — Backlog único por agente (source of
  truth)
- [docs/REGRAS_DE_NEGOCIO.md](docs/REGRAS_DE_NEGOCIO.md) — Regras canônicas
- [docs/OPERACAO_4_AGENTES.md](docs/OPERACAO_4_AGENTES.md) — Como operar
- [docs/MODELAGEM_DE_DADOS.md](docs/MODELAGEM_DE_DADOS.md) — Schema SQLite
- [docs/AGENTES_RL_PARALELOS.md](docs/AGENTES_RL_PARALELOS.md) — Isolamento
  entre agentes RL
- [START_HERE.md](START_HERE.md) — Quick start em 5 minutos

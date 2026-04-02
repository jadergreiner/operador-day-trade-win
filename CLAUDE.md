# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with
code in this repository.

## Idioma e Padroes Obrigatorios

- **100% Portugues Brasileiro** — variaveis, funcoes, comentarios, docstrings
  e docs
  - Correto: `def calcular_margem_seguranca():`
  - Errado: `def calculate_safety_margin():`
- **Commits SEM ACENTOS** — evitar encoding corrompido no historico git
  - Correto: `feat: Adicionar calculadora de margem`
  - Errado: `feat: Adicionar calculacao de margem`
- **Markdown** — linhas com maximo 80 caracteres; validar com
  `pymarkdown scan`

## Comandos Essenciais

```bash
# Testes
pytest tests/                          # Todos os testes
pytest tests/unit/ -v                  # So unitarios
pytest tests/ -k "test_drift" --tb=short   # Por palavra-chave
pytest tests/ -m unit                  # Apenas unitarios
pytest tests/ -m integration           # Apenas integracao

# Teste unico por metodo
pytest tests/unit/test_ac5_8_position_monitor.py \
  ::TestPositionMonitor::test_registrar_posicao_aberta -v

# Cobertura (minimo 80%, alvo 85%)
pytest --cov=src --cov-report=html

# Qualidade de codigo
black src/ tests/ scripts/             # Formatacao (line-length=88)
isort src/ tests/ scripts/             # Ordenacao de imports
mypy src/ --strict                     # Type checking estrito
python -m pymarkdown scan docs/        # Lint de markdown
```

## Arquitetura

Sistema de trading automatico para Mini Indice (WIN$N) no MetaTrader 5,
composto por **5 launchers operacionais prioritarios** orquestrados por
`.bat` na raiz (**4 executores + 1 camada de observabilidade web**):

| Agente | .bat (raiz) | Script Python |
| ------ | ----------- | ------------- |
| Diarios | `INICIAR_DIARIOS.bat` | `scripts/start_journals_full_display.py` |
| Micro Tendencia | `INICIAR_MICRO_TENDENCIA_AUTO_TRADE.bat` | `scripts/agente_micro_tendencia_winfut.py` |
| RL 5000 | `INICIAR_AGENTE_RL_5000.bat` | `scripts/agente_com_supervision.py` |
| RL Direto | `INICIAR_AGENTE_RL_DIRETO.bat` | `scripts/agente_rl_direto_independente.py` |
| Monitor Quantico | `INICIAR_MONITOR_QUANTICO.bat` | `scripts/monitor_quantico_tendencia.py` |

### Camadas

```text
*.bat (raiz)              → Entrypoints operacionais Windows (INICIAR_*.bat)
scripts/*.py              → Scripts executaveis de analise e operacao (240+)
src/domain/               → Entities (UUID), Value Objects, Enums,
                            Exceptions, Interfaces ABC
src/application/          → Use cases: monitores, ML, RL, risco, ordens,
                            diarios, aprendizado, reflexao, governanca
src/application/services/ → ML pipeline, RL services, macro_score engine,
                            backtest engine, alertas, analises
src/application/gerenciamento_risco/ → Gates de risco por agente e globais
src/application/reconciliadores/     → Reconciliacao de resultados
src/infrastructure/       → IBrokerAdapter, ITradeRepository, IRLRepository
                            (MT5, SQLite, WebSocket, providers)
src/interfaces/           → FastAPI routes + WebSocket endpoints + CLI
src/adapters/             → Adaptadores de alto nivel (s2_6_analytics)
src/ml/                   → Pipeline ML standalone (ati5/ati8)
agente_micro_tendencia_winfut/ → Modulo do agente micro tendencia
data/db/                  → Bancos SQLite por agente (8 databases)
data/models/              → Modelos ML/RL versionados
data/backtest/            → Artefatos Gate 2 obrigatorios
data/BDI/                 → Boletins diarios B3 (PDFs + extraidos)
outputs/                  → Arquivos gerados em runtime (logs, JSON posicao)
config/                   → settings.py, backtest_config.py
```

### Pipeline de Decisao (AC1→AC6)

```text
AC1: SignalGenerator    → Gera sinais (padroes SMC em M5)
AC2: SignalPersistence  → Persiste sinais no SQLite
AC3: SignalTracker      → Rastreia ciclo de vida do sinal
AC4: DecisionFilter     → Decide EXECUTE/HOLD/REJECT (gates de risco)
AC5: TradeExecutor      → Executa ordem no MT5
AC5.8: PositionMonitor  → Monitora posicao aberta (SL/TP em tempo real)
AC5.9: FeedbackValidator → Valida outcome da operacao
AC6: FeedbackLoop       → Atualiza modelos ML/RL com resultado
  AC6.7: DriftDetector      → Detecta degradacao do modelo
  AC6.8: OnlineLearning     → Treino incremental com rollback
  AC6.9: BaselineComparator → Compara baseline vs modelo atual
```

`macro_guardian_universal.py` — snapshot de contexto macro consumido por
todos os agentes como gate transversal (regimes: FAVORAVEL/ESTAVEL/
CAUTELOSO/ALERTA/CRITICO).

`universal_kill_switch.py` — kill switch global; bloqueia operacoes de
todos os agentes quando acionado.

### Componentes Principais em `src/application/`

#### Pipeline AC (core)

| Arquivo | Funcao | Testes |
| ------- | ------ | ------ |
| `ac5_8_position_monitor.py` | Monitor RT de posicoes abertas | ✅ |
| `ac5_9_feedback_validator.py` | Validacao ciclo feedback ML/RL | 21/21 ✅ |
| `ac6_7_drift_detector.py` | Deteccao de degradacao de modelo | 24/24 ✅ |
| `ac6_8_online_learning.py` | Treino incremental com rollback | 18/18 ✅ |
| `ac6_9_baseline_comparator.py` | Comparacao baseline vs modelo atual | ✅ |
| `rl_trading_environment.py` | Ambiente Gym-compativel para RL | 21/21 ✅ |
| `rl_retrain_scheduler.py` | Agendamento inteligente de retrain | 24/24 ✅ |
| `rl_model_rollback_manager.py` | Rollback automatico de modelo RL | 17/17 ✅ |
| `posicao_isolamento.py` | Isolamento de posicoes entre agentes | 7/7 ✅ |
| `motor_decisao_isolado.py` | Motor de decisao isolado por agent_id | ✅ |
| `ml_classifier.py` | Classificador LightGBM para sinais | ✅ |
| `orders_executor.py` | Command Pattern para ciclo de vida de ordem | ✅ |
| `risk_validator.py` | Chain of Responsibility (3 Gates de risco) | ✅ |
| `profit_protection_engine.py` | Protecao de lucros (trailing) | ✅ |
| `dashboard_stats_server.py` | FastAPI: endpoints de estatisticas RT | ✅ |

#### Sistema de Diarios (Journals)

| Arquivo | Funcao |
| ------- | ------ |
| `diario_episodio_operador.py` | Journaling de episodios por operacao |
| `diario_leitura_operador.py` | Leitura e analise de diarios |
| `diario_market_features.py` | Features de mercado nos diarios |
| `diario_observability_panel.py` | Painel de observabilidade |
| `diario_order_manager.py` | Gerenciador de ordens no diario |
| `diarios_health_monitor.py` | Monitoramento de saude dos diarios |
| `diarios_watchdog.py` | Watchdog service dos diarios |
| `diarios_runtime_mlops_bridge.py` | Bridge MLOps <-> diarios |

#### Aprendizado P1 (Online Learning)

| Arquivo | Funcao | Testes |
| ------- | ------ | ------ |
| `p1_learning_engine.py` | Engine de aprendizado P1 (online) | ✅ |
| `p1_learning_closure.py` | Fechamento de ciclo aprendizado P1 | 27/27 ✅ |
| `p1_learning_monitoring.py` | Monitoramento P1 em tempo real | ✅ |
| `p1_operation_lifecycle.py` | Ciclo de vida de operacao P1 | ✅ |

#### Sistema de Reflexao e Narrativa

| Arquivo | Funcao |
| ------- | ------ |
| `reflection_action_channel.py` | Canal de reflexao de acoes |
| `reflection_question_evolution.py` | Evolucao de perguntas de reflexao |
| `session_narrative_logger.py` | Logging narrativo por sessao |
| `narrative_persistence.py` | Persistencia de narrativas |
| `narrative_dataset_exporter.py` | Exportacao de dataset narrativo |
| `trade_narrative_correlator.py` | Correlacao narrativa de trades |

#### Governanca e Orquestracao

| Arquivo | Funcao |
| ------- | ------ |
| `release_gates.py` | Gates de liberacao para producao |
| `universal_kill_switch.py` | Kill switch global de todos os agentes |
| `multi_agent_conflict_resolver.py` | Resolucao de conflitos multi-agente |
| `guardian_agent_coordinator.py` | Coordenacao guardian entre agentes |

#### Contexto de Abertura de Mercado

| Arquivo | Funcao |
| ------- | ------ |
| `opening_context_audit.py` | Auditoria de contexto de abertura |
| `opening_context_policy.py` | Politica de abertura de mercado |
| `opening_context_report.py` | Relatorio de contexto de abertura |
| `opening_context_runtime.py` | Runtime do contexto de abertura |
| `opening_market_confirmation.py` | Confirmacao de abertura do mercado |

#### Ordens e Execucao

| Arquivo | Funcao |
| ------- | ------ |
| `order_queue_sqlite.py` | Fila de ordens persistida no SQLite |
| `orders_executor_todo234.py` | Executor estendido (variante) |
| `ordem_backoff_retry.py` | Estrategia de backoff/retry |
| `order_manager_learner.py` | Gerenciador de ordens com aprendizado |
| `position_closure_detector.py` | Detector de fechamento de posicao |
| `sl_breakeven_validator.py` | Validador de SL no breakeven |

#### Analise e Deteccao

| Arquivo | Funcao |
| ------- | ------ |
| `execution_pattern_analyzer.py` | Analise de padroes de execucao |
| `directional_bias_detector.py` | Detector de vies direcional |
| `micro_bloqueios_reporter.py` | Reporter de micro-bloqueios |
| `trade_performance_tracker.py` | Rastreamento de performance |
| `rl_episode_quality_scorer.py` | Avaliacao de qualidade de episodio RL |

#### Autenticacao e WebSocket

| Arquivo | Funcao |
| ------- | ------ |
| `auth_endpoints_ati2.py` | Endpoints de autenticacao ATI2 |
| `oauth_auth_ati2.py` | Autenticacao OAuth2 |
| `oauth_schemas_ati2.py` | Schemas OAuth2 |
| `token_manager_ati2.py` | Gerenciamento de tokens |
| `websocket_auth_integration.py` | Integracao auth WebSocket |
| `websocket_server_ati1.py` | Servidor WebSocket ATI1 |

### Subdiretorio: `gerenciamento_risco/`

```text
controles_agente/
  gate_unica_ordem.py         → Gate: apenas 1 ordem por agente
  gerenciador_cooldown.py     → Gerenciador de periodo de cooldown
  validador_sl_maximo.py      → Validador de SL maximo permitido
controles_globais/
  gate_calendario_economico.py → Gate: calendario economico
  gate_horario_operacao.py     → Gate: horario de operacao
  limitador_ganho_diario.py    → Limitador de ganho/perda diarios
gerenciador_risco_externo.py  → Coordenador de risco externo
```

### Subdiretorio: `reconciliadores/`

```text
trade_outcome_reconciler.py → Reconciliacao de outcomes de trade
mt5_sync_validator.py       → Validacao de sincronia MT5
unknown_result_detector.py  → Deteccao de trades com resultado desconhecido
```

### Servicos em `src/application/services/`

```text
backtest/
  backtest_engine.py          → Engine de execucao de backtest
  display.py                  → Visualizacao de backtest
  historical_data_provider.py → Provedor de dados historicos
macro_score/
  engine.py                   → Motor de calculo do macro score
  feedback_evaluator.py       → Avaliador de feedback do score
  forex_handler.py            → Tratamento de forex
  futures_resolver.py         → Resolucao de simbolos futuros
  item_registry.py            → Registro de itens do score
  technical_scorer.py         → Scoring tecnico
ml/
  feature_engineering_v2.py   → Feature engineering v2
  lgbm_agent_integrator.py    → Integracao LightGBM
  target_engineering.py       → Engenharia de targets
  winfut_dataset.py           → Dataset WinFUT
  winfut_feature_engineer.py  → Features WinFUT
  winfut_model_trainer.py     → Treinamento WinFUT
novo_agente/
  agente_q_learning.py        → Agente Q-Learning
  ambiente_trading.py         → Ambiente de trading
  pipeline_treinamento.py     → Pipeline de treinamento
automated_trading.py          → Orquestracao de trading automatizado
trading_journal.py            → Servico de diario de trading
fundamental_analysis.py       → Analise fundamentalista
technical_analysis.py         → Analise tecnica
macro_analysis.py             → Analise macroeconomica
sentiment_analysis.py         → Analise de sentimento
volume_analysis.py            → Analise de volume
risk_manager.py               → Servico de gerenciamento de risco
processador_bdi.py            → Processamento de boletins BDI (B3)
quantum_operator.py           → Operador quantico (override de confianca)
premarket_briefing.py         → Analise pre-mercado
macro_scenario_guardian.py    → Guardiao de cenario macro
forced_activation_manager.py  → Controle de ativacao forcada
inactivity_penalty_manager.py → Penalidades por inatividade
head_directives.py            → Diretivas do head trader
ai_reflection_journal.py      → Diario de reflexao da IA
rl_persistence_service.py     → Persistencia de RL
win_data_ingestion.py         → Ingestao de dados WinFUT
sl_tp_ab_backtest.py          → Backtest A/B de SL/TP
diary_feedback.py             → Feedback via diario
detector_padroes_tecnico.py   → Detector de padroes tecnicos
detector_volatilidade.py      → Detector de volatilidade
alerta_delivery.py            → Entrega de alertas
alerta_formatter.py           → Formatacao de alertas
```

### Infraestrutura e Interfaces

`src/infrastructure/` (41 modulos):

```text
adapters/
  mt5_adapter.py              → Integracao MetaTrader5
  mt5_adapter_proxy.py        → Proxy com cache/retry para MT5
database/
  schema.py                   → Schema principal trading.db
  rl_schema.py                → Schema especifico RL
  auditoria_alertas.py        → Schema de auditoria de alertas
  db_paths.py                 → Configuracao de caminhos dos DBs
  sqlite_write_lock.py        → Lock de escrita SQLite (multi-agente)
persistence/
  resilient_reflection_persistence.py → Persistencia resiliente
  transaction_log_service.py  → Log transacional
  mt5_synchronization_service.py      → Sincronizacao MT5
monitoring/
  health_checker.py           → Health check por agente
  heartbeat_monitor.py        → Monitor de heartbeat
backtests/
  backtest_engine.py          → Engine de backtest
  dataset_auditor.py          → Auditoria de dataset
  metrics_calculator.py       → Calculo de metricas
reports/
  backtest_reporter.py        → Reporter de backtest
  backtest_visualizer.py      → Visualizacao de backtest
repositories/
  trade_repository.py         → Persistencia de trades
  rl_repository.py            → Persistencia de dados RL
  macro_score_repository.py   → Persistencia de macro score
  repositorio_ganho_diario.py → Rastreamento de ganho diario
providers/
  forex_api_provider.py       → API de forex
  calendario_economico_provider.py → Calendario economico
  fila_alertas.py             → Fila de alertas
mt5_executor.py               → Execucao de ordens MT5
terminal_isolation_enforcer.py → Isolamento de terminal entre agentes
execution_monitor.py          → Monitoramento de execucao
position_monitor.py           → Monitoramento de posicao
position_broadcaster.py       → Broadcasting de posicoes
queue_processor.py            → Processador de filas
ati1_broadcast_client.py      → Cliente broadcast ATI1
clients/order_api_client.py   → Cliente API de ordens
config/alerta_config.py       → Configuracao de alertas
validators/backtest_validator.py → Validacao de backtest
```

`src/interfaces/` expõe dois servidores concorrentes:

```text
api/
  fastapi_server.py           → REST API com OAuth/JWT (porta configuravel)
  models.py                   → Modelos Pydantic request/response
  routes/dashboard.py         → Rotas do dashboard
  routes/orders.py            → Rotas de ordens
websocket_server.py           → WebSocket para streaming de posicoes RT
websocket_fila_integrador.py  → Integracao fila <-> WebSocket
cli/quantum_operator_cli.py   → Interface de linha de comando
```

`src/ml/` — pipeline ML standalone (nomenclatura `ati5`/`ati8`):

```text
feature_pipeline_ati5.py     → Feature engineering ATI5
dataset_loader_ati8.py       → Carregamento de dataset ATI8
model_trainer_ati8.py        → Treinamento de modelo ATI8
train_xgboost_ati8.py        → Treinamento XGBoost ATI8
backtest_server_xgboost.py   → Servidor de backtest XGBoost
```

`agente_micro_tendencia_winfut/` — modulo do agente micro tendencia:

```text
s2_6_analytics/
  analytics_dashboard.py     → Interface do dashboard S2.6
  config.py                  → Configuracao de analytics
  manual_override_logger.py  → Log de overrides manuais
  models.py                  → Modelos de dados
  trader_feedback_api.py     → API de feedback do trader
```

### Isolamento entre Agentes RL

Cada agente possui Session ID unico (timestamp). Posicoes e logs ficam em
arquivos separados (`outputs/agente_posicao_*.json`, `outputs/agente_*.log`)
para evitar conflitos quando multiplos agentes rodam em paralelo.

### Gate 2 (P0-2) — Controle de Capital

`scripts/check_p0_2_status.py` retorna exit code que define escala de capital:

- `0`: PASS → capital ampliado
- `1/2/3`: FAIL/em execucao/erro → capital conservador

Artefatos obrigatorios em `data/backtest/`: `dataset_audit.json`,
`backtest_results.json`, `gate2_decision.json`, `p0_2_status.json`.
Falhas de pipeline nunca liberam capital ampliado.

### Bancos de Dados SQLite

| Arquivo | Agente/Uso |
| ------- | ---------- |
| `data/db/trading.db` | Principal (todos os agentes) |
| `data/db/trading_analise.db` | Analise geral |
| `data/db/trading_micro_tendencia.db` | Agente Micro Tendencia |
| `data/db/trading_rl_5000.db` | Agente RL 5000 |
| `data/db/trading_rl_direto.db` | Agente RL Direto |
| `data/db/trading_diarios.db` | Agente Diarios |
| `data/db/api_orders.db` | Ordens via API REST |
| `data/db/wdo_winfut.db` | WDO/WinFUT combinado |

## Estrutura de Scripts (`scripts/`)

240+ scripts Python organizados por prefixo/categoria:

| Categoria | Prefixos/Exemplos | Contagem |
| --------- | ----------------- | -------- |
| Diagnostico | `diagnostico_*.py`, `analyze_*.py`, `debug_*.py` | ~40 |
| Treinamento | `train_*.py`, `s2_*.py`, `score_t60_*.py` | ~50 |
| Validacao | `test_*.py`, `validate_*.py`, `check_*.py` | ~60 |
| Monitoramento | `monitor_*.py`, `health_check_*.py`, `live_*.py` | ~20 |
| Dados | `processar_*.py`, `import_*.py`, `export_*.py` | ~30 |
| Ordens | `enviar_ordem_*.py`, `executar_*.py` | ~15 |
| RL/Learning | `rl_*.py`, `treinar_*.py`, `aprendizado_*.py` | ~20 |
| Relatorios | `relatorio_*.py`, `audit_*.py` | ~15 |

Subdiretorios em `scripts/`:

```text
scripts/agente_wdo_winfut/   → Modulo WDO agent
scripts/execution/           → .bat de ativacao (ativar_producao_*.bat)
scripts/ml/                  → Scripts de treinamento ML
scripts/utilities/           → Utilitarios de validacao
scripts/validacao/           → Scripts de validacao
```

## Workflow de Desenvolvimento

### Git

Ao commitar, use `/commit` (skill disponivel) ou siga estas regras:

- `git add -A` — incluir TODOS os arquivos alterados, incluindo deletados,
  **sem pedir confirmacao**
- Mensagem em Portugues, **sem acentos** (ex: `feat: Adicionar monitor`)
- Nunca usar `--no-verify`

### Antes de editar codigo

Antes de modificar qualquer arquivo `.py`, leia o arquivo completo para
evitar duplicacao de blocos. Apos cada edicao de codigo, execute os testes
relevantes imediatamente para verificar que nao houve regressao.

### Backlog (TDD)

Ao implementar um item do backlog:

1. Escrever testes que falham primeiro
2. Implementar o codigo para os testes passarem
3. Executar `mypy src/ --strict` e corrigir todos os erros
4. Executar `pytest tests/ -q` e garantir que tudo passa
5. Commitar apenas quando tudo estiver verde

Ao **adicionar** itens ao backlog: escrever imediatamente, sem ler outros
arquivos primeiro.

### Hook pre-commit (automatico)

O projeto tem um hook configurado em `.claude/settings.json` que executa
`mypy --strict` + `pytest` automaticamente antes de qualquer `git commit`.
Se falhar, o commit e bloqueado.

## Padroes de Codigo

- **Python 3.11+**
- **Type hints 100%** em `src/` — mypy `--strict` nao deve reportar erros
  - Excecoes: `MetaTrader5.*` e `talib.*` tem
    `ignore_missing_imports = true` no `pyproject.toml` — nao tentar
    "corrigir" esses imports
- **Cobertura minima:** 80% por modulo, 85% para merge, 100% em criticos
- Novos scripts executaveis vao em `scripts/`, outputs gerados em `outputs/`
- Codigo reutilizavel e importavel vai em `src/`
- Scripts `.bat` usam MAIUSCULAS: `INICIAR_*.bat`, `SETUP_*.bat`,
  `DIAGNOSTICO_*.bat`
- Scripts Python em `scripts/` seguem snake_case; prefixos convencionados:
  `spec_`, `run_`, `launch_`, `check_`, `cleanup_`, `verify_`, `analyze_`,
  `debug_`, `export_`, `import_`, `utility_`
- Scripts Python **nunca** ficam na raiz — apenas em `scripts/` ou `src/`

### Padrao de Docstring (obrigatorio)

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

### Padroes DDD

- **Value Objects** — `@dataclass(frozen=True)`, validacao em `__post_init__`
- **Entities** — `@dataclass` com `UUID` como identidade, `__eq__` por ID
- **Interfaces** — `ABC` + `@abstractmethod` em
  `src/infrastructure/adapters/` e `src/infrastructure/repositories/`
- **Excecoes** — herdam de `DomainError` em `src/domain/exceptions/`

### Pytest Markers

Definidos em `pytest.ini`:

| Marker | Uso |
| ------ | --- |
| `unit` | Testes sem dependencias externas |
| `integration` | Usa banco de dados, fila ou MT5 |
| `ml` | Testes de machine learning |
| `critical` | Testes de gate de producao |
| `orders` | Execucao de ordens |
| `risk` | Validador de risco |
| `slow` | Testes lentos (>1s) |
| `smoke` | Verificacao basica de sanidade |
| `documentation` | Validacao de documentacao |

### Estrutura de Testes

```text
tests/
├── unit/           # 138 arquivos — testes sem dependencias externas
├── integration/    # 12 arquivos — DB, MT5, filas, WebSocket, OAuth
├── performance/    # Testes de performance WebSocket
├── load_testing/   # Testes de carga (locustfile.py)
└── uat/            # User Acceptance Tests
```

## Configuracao de Ambiente

Copie `.env.example` para `.env` e preencha:

- `MT5_LOGIN`, `MT5_PASSWORD`, `MT5_SERVER`, `MT5_TERMINAL_PATH`
- `DB_PATH=data/db/trading.db`
- `MODEL_PATH=data/models/`
- APIs externas: `FRED_API_KEY`, `TWELVEDATA_API_KEY`,
  `ALPHAVANTAGE_API_KEY`, `FINNHUB_API_KEY`, `TELEGRAM_BOT_TOKEN`

Variantes de ambiente disponiveis: `config/.env.test` e
`config/.env.staging`.

## Documentacao

- [docs/ARQUITETURA_ALVO.md](docs/ARQUITETURA_ALVO.md) — Arquitetura
  operacional e contrato Gate 2
- [docs/BACKLOG.md](docs/BACKLOG.md) — Backlog unico por agente (source of
  truth)
- [docs/REGRAS_DE_NEGOCIO.md](docs/REGRAS_DE_NEGOCIO.md) — Regras canonicas
- [docs/OPERACAO_4_AGENTES.md](docs/OPERACAO_4_AGENTES.md) — Como operar
- [docs/MODELAGEM_DE_DADOS.md](docs/MODELAGEM_DE_DADOS.md) — Schema SQLite
- [docs/AGENTES_RL_PARALELOS.md](docs/AGENTES_RL_PARALELOS.md) — Isolamento
  entre agentes RL
- [docs/ADRS.md](docs/ADRS.md) — Architecture Decision Records
- [docs/STATUS_ENTREGAS.md](docs/STATUS_ENTREGAS.md) — Status das entregas
- [docs/arquitetura/](docs/arquitetura/) — Diagramas, planos e ADRs
- [docs/checklists/](docs/checklists/) — Go-live, clean arch, MLOps
- [docs/sessoes/](docs/sessoes/) — Logs de sessoes de desenvolvimento
- [docs/legacy/](docs/legacy/) — Documentacao arquivada de versoes anteriores
- [scripts/README.md](scripts/README.md) — Guia de padroes de scripts
- [START_HERE.md](START_HERE.md) — Quick start em 5 minutos

## Estatisticas do Projeto

| Metrica | Quantidade |
| ------- | ---------- |
| Scripts Python (`scripts/`) | 240+ |
| Modulos de aplicacao (`src/application/`) | 92 |
| Modulos de infraestrutura | 41 |
| Modulos de dominio | 19 |
| Modulos de interface | 12 |
| Pipeline ML standalone | 5 |
| Arquivos de teste | 198 |
| Arquivos de documentacao | 126+ |
| Entrypoints `.bat` | 4 |
| Bancos SQLite | 8 |

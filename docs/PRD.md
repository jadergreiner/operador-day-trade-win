# PRD - Documento de Requisitos do Produto

**Produto:** Operador Day Trade WIN
**Versao:** 1.0
**Data:** 19/03/2026
**Status:** Base funcional ampla concluída em código; gate operacional (`BL-01` + `BL-07` + `BL-08`) aprovado com `GO_LIVE` às `22:41:47` de `19/03/2026`; `Gate 2` corrente segue em `FAIL` para escala de capital

---

## 1. Visao Geral do Produto

### 1.1 Descricao

Sistema de trading automatico para Mini Indice Futuro
(WIN/WIN$N) na B3, operando via MetaTrader 5. Composto por
4 agentes paralelos independentes que combinam Machine
Learning (LightGBM/XGBoost), Reinforcement Learning
(Q-Learning) e analise macro para gerar sinais, executar
ordens e gerenciar risco em tempo real.

### 1.2 Problema

Operacoes manuais de day trade sofrem de:

- Vieses emocionais (medo, ganancia, revenge trading)
- Inconsistencia na execucao de regras
- Incapacidade de processar multiplas fontes de dados
  simultaneamente
- Fadiga e limitacao de atencao humana no intraday

### 1.3 Solucao

Automacao completa do ciclo de trading:

1. **Captura** - Ticks RT do MT5 + dados macro
2. **Analise** - ML classifica, RL aprende politicas
3. **Decisao** - Motor isolado com 3 gates de risco
4. **Execucao** - Ordens automaticas com SL/TP dinamicos
5. **Feedback** - Aprendizado causal P1 + deteccao drift
6. **Reflexao** - Diarios IA com narrativa

### 1.4 Proposta de Valor

| Aspecto | Manual | Automatizado |
|---------|--------|--------------|
| Decisao | Segundos | Milissegundos |
| Consistencia | Variavel | 100% regras |
| Dados | 3-5 indicadores | 85 itens macro |
| Operacao | 1 ativo | 4 agentes |
| Aprendizado | Subjetivo | Causal + RL |

### 1.5 Precedência Documental e Contrato Operacional

- Verdade operacional de pendências e fechamento: `docs/BACKLOG.md`, `docs/STATUS_ENTREGAS.md` e `docs/PLANO_MULTI_AGENTES.md`.
- O PRD espelha esses documentos para rastreabilidade de release, não para substituir o status operacional deles.
- Governança do micro tendência: `docs/MICRO_TENDENCIA_CHANGELOG_GOVERNANCA.md` e `docs/MICRO_TENDENCIA_CHANGELOG_TEMPLATE.md`.
- O contrato imediato do fechamento diário é `prompts/fechamento_diario.md`, com `ResultadoAgente`, `agente_impactado`, `resultado_por_agente`, `resultado_consolidado` e `melhorias_por_agente`.
- `Gate 2` neste documento significa apenas escala de capital; o gate final operacional é separado e depende de staging/UAT e evidência diária por agente.

---

## 2. Objetivos e Metricas de Sucesso

### 2.1 Objetivos de Negocio

| ID | Objetivo | Meta |
|----|----------|------|
| ON-1 | Operar WIN$N producao | GO LIVE 10/04 |
| ON-2 | Rentabilidade consistente | Win rate >55% |
| ON-3 | Controle de risco | Drawdown <500pts |
| ON-4 | Escalar capital | Gate2 → R$100k |

### 2.2 Metricas Tecnicas

| Metrica | Alvo | Critico |
|---------|------|---------|
| Latencia decisao | <10ms | <50ms |
| Cobertura testes | 85% | 80% min |
| Type hints mypy | 100% | 100% |
| Disponibilidade MT5 | 99.5% | 95% |
| Retrain RL | <5min | <15min |
| Drift detection | Z-score | Continuo |

### 2.3 Metricas Operacionais

| Metrica | Alvo |
|---------|------|
| Trades/dia (por agente) | Max 6 |
| Posicoes simultaneas | Max 1 |
| Horario operacao | 09:00-17:25 BRT |
| Cooling apos SL | 30 minutos |
| Confianca minima | 45% |
| Risk/Reward minimo | 1.5:1 |

---

## 3. Personas e Usuarios

### 3.1 Operador Principal

- **Perfil:** Trader individual com conhecimento tecnico
- **Responsabilidades:**
  - Iniciar/parar agentes via BAT
  - Monitorar dashboards e diarios
  - Decidir modo (simulado/auto-trade)
  - Avaliar reflexoes IA e ajustar parametros
  - Definir diretivas do Head Financeiro

### 3.2 Sistema Autonomo (Agentes)

- **Perfil:** 4 agentes Python em paralelo
- **Responsabilidades:**
  - Gerar sinais e executar ordens
  - Gerenciar risco automaticamente
  - Aprender com resultados (feedback loop)
  - Reportar status via logs e WebSocket

---

## 4. Requisitos Funcionais

### 4.1 Pipeline de Sinais (AC1-AC4)

| RF | Descricao | Status |
|----|-----------|--------|
| RF-01 | Sinais via analise tecnica | Impl. |
| RF-02 | Classificar com LightGBM (F1>0.65) | Impl. |
| RF-03 | Persistir sinais SQLite | Impl. |
| RF-04 | Deduplicacao de sinais (80%) | Impl. |
| RF-05 | Filtro BDI (calendario economico) | Impl. |
| RF-06 | Score macro (85 itens, 15+ cat.) | Impl. |

### 4.2 Execucao de Ordens (AC5)

| RF | Descricao | Status |
|----|-----------|--------|
| RF-07 | Command Pattern ciclo de ordem | Impl. com hardening operacional pendente |
| RF-08 | Estados: ENQUEUED→CLOSED | Impl. com hardening operacional pendente |
| RF-09 | Monitor RT posicoes (15s) | Impl. com hardening operacional pendente |
| RF-10 | Fechamento por ticket | Impl. com hardening operacional pendente |
| RF-11 | Auditoria SQLite | Impl. com hardening operacional pendente |
| RF-12 | Trailing stop (ProfitProtection) | Impl. com hardening operacional pendente |
| RF-13 | SL/TP dinamico por ATR | Impl. com hardening operacional pendente |

### 4.3 Feedback e Aprendizado (AC6)

| RF | Descricao | Status |
|----|-----------|--------|
| RF-14 | Saude feedback ML/RL | Em validação operacional |
| RF-15 | Drift Z-score (100 trades) | Em validação operacional |
| RF-16 | Online learning + rollback | Em validação operacional |
| RF-17 | Baseline vs atual | Em validação operacional |
| RF-18 | Versionamento semantico | Em validação operacional |

### 4.4 Reinforcement Learning

| RF | Descricao | Status |
|----|-----------|--------|
| RF-19 | Ambiente Gym-compativel | Impl. |
| RF-20 | Retrain off-peak | Impl. |
| RF-21 | Rollback modelo RL | Impl. |
| RF-22 | Episode quality scoring | Impl. |
| RF-23 | 7 filtros anti-overtrading | Impl. |

### 4.5 Aprendizado Causal P1 (7 etapas)

| RF | Descricao | Status |
|----|-----------|--------|
| RF-24 | Etapa 1: Deteccao de sinal | Em validação operacional |
| RF-25 | Etapa 2: Registro de decisao | Em validação operacional |
| RF-26 | Etapa 3: Monitoramento | Em validação operacional |
| RF-27 | Etapa 4: Fechamento c/ motivo | Em validação operacional |
| RF-28 | Ligacao causal via episode_id | Em validação operacional |

### 4.6 Gestao de Risco

| RF | Descricao | Status |
|----|-----------|--------|
| RF-29 | Gate 1: Capital (>=1.5x ticket) | Impl. |
| RF-30 | Gate 2: Correlacao (<=70%) | Impl. |
| RF-31 | Gate 3: Volatilidade (ATR) | Impl. |
| RF-32 | Chain of Responsibility | Impl. |
| RF-33 | P0-2 capital scaling | Impl. |

### 4.7 Multi-Agente e Isolamento

| RF | Descricao | Status |
|----|-----------|--------|
| RF-34 | Magic Number MT5 | Impl. |
| RF-35 | Motor decisao por agent_id | Impl. |
| RF-36 | Posicoes separadas/agente | Impl. |
| RF-37 | Session ID unico | Impl. |
| RF-38 | Terminal isolation enforcer | Impl. |
| RF-39 | Resolucao de conflitos | Impl. |

### 4.8 Guardian e Monitoramento Macro

| RF | Descricao | Status |
|----|-----------|--------|
| RF-40 | Monitor USD/BRL (0.50%) | Impl. |
| RF-41 | Monitor S&P500 (0.80%) | Impl. |
| RF-42 | Eventos COPOM/FOMC/NFP/CPI | Impl. |
| RF-43 | Deteccao de divergencias | Impl. |
| RF-44 | Kill switch emergencias | Impl. |
| RF-45 | Log universal Guardian | Impl. |

### 4.9 Observabilidade e Diarios

| RF | Descricao | Status |
|----|-----------|--------|
| RF-46 | Diarios automaticos Markdown | Impl. |
| RF-47 | Reflexao IA sobre operacoes | Impl. |
| RF-48 | Narrativa de sessao | Impl. |
| RF-49 | Thread watchdog + health | Em validação operacional |
| RF-50 | Detector de vies direcional | Em validação operacional |
| RF-51 | Retreino adaptativo | Em validação operacional |

### 4.10 Interfaces e APIs

| RF | Descricao | Status |
|----|-----------|--------|
| RF-52 | REST API FastAPI | Impl. |
| RF-53 | WebSocket streaming RT | Impl. |
| RF-54 | OAuth/JWT (ATI-2) | Impl. |
| RF-55 | CLI operador quantum | Impl. |

---

## 5. Requisitos Nao-Funcionais

### 5.1 Performance

| RNF | Descricao | Meta |
|-----|-----------|------|
| RNF-01 | Latencia decisao trading | <10ms |
| RNF-02 | Resposta API REST | <100ms |
| RNF-03 | Atualizacao WebSocket | <500ms |
| RNF-04 | Ciclo monitor posicao | 15s |
| RNF-05 | Intervalo Guardian macro | 120s |

### 5.2 Confiabilidade

| RNF | Descricao | Meta |
|-----|-----------|------|
| RNF-06 | Disponibilidade mercado | 99.5% (em validação operacional) |
| RNF-07 | Recuperacao falha MT5 | Auto retry (em validação operacional) |
| RNF-08 | Persistencia transacional | Obrigatorio (em validação operacional) |
| RNF-09 | Backup diario automatico | data/backups/ (em validação operacional) |
| RNF-10 | Rollback modelo degradado | Automatico (em validação operacional) |

### 5.3 Qualidade de Codigo

| RNF | Descricao | Meta |
|-----|-----------|------|
| RNF-11 | Type hints src/ | 100% mypy |
| RNF-12 | Cobertura por modulo | >=85% |
| RNF-13 | Cobertura minima merge | 80% |
| RNF-14 | Cobertura criticos | 100% |
| RNF-15 | Formatacao Black (88) | Obrigatorio |
| RNF-16 | Imports isort | Obrigatorio |
| RNF-17 | Markdown max 80 chars | Obrigatorio |

### 5.4 Seguranca

| RNF | Descricao | Meta |
|-----|-----------|------|
| RNF-18 | Credenciais em .env | Obrigatorio |
| RNF-19 | OAuth/JWT para API | Implementado |
| RNF-20 | Isolamento 3 niveis | Obrigatorio |
| RNF-21 | Confirmacao auto-trade | Obrigatorio |
| RNF-22 | Kill switch emergencia | Implementado |

### 5.5 Manutenibilidade

| RNF | Descricao | Meta |
|-----|-----------|------|
| RNF-23 | Arquitetura DDD | Implementado |
| RNF-24 | Interfaces ABC | Obrigatorio |
| RNF-25 | Docstrings padrao | Obrigatorio |
| RNF-26 | ADRs formais | 12+ |
| RNF-27 | 100% Portugues BR | Obrigatorio |

---

## 6. Arquitetura de Alto Nivel

### 6.1 Camadas

```text
[Orquestracao]   BAT canonicos → 4 agentes paralelos
       |
[Scripts]        scripts/*.py → pontos de entrada
       |
[Interfaces]     FastAPI REST + WebSocket RT
       |
[Application]    Use cases, ML, RL, Risk
       |
[Domain]         Entities, VOs, Enums, ABC
       |
[Infrastructure] MT5, SQLite, Providers
       |
[Dados]          SQLite + JSON + JSONL + MD
```

### 6.2 Fluxo de Dados Principal

```text
MT5 (ticks RT)
  → MT5Adapter (TickData/Candle)
  → FeatureEngineering (24+ features)
  → MLClassifier (LightGBM/XGBoost)
  → MacroScoreEngine (85 itens)
  → RiskValidator (3 Gates)
  → OrdersExecutor (máquina de estados)
  → PositionMonitor (15s por ticket)
  → ProfitProtection (trailing stop)
  → FeedbackLoop (drift + learning)
  → P1Learning (causal 7 etapas)
  → DiarioReflexao (narrativa IA)
```

### 6.3 Decisoes Arquiteturais (ADRs)

| ADR | Decisao | Razao |
|-----|---------|-------|
| 001 | SQLite primario | <10ms latencia |
| 002 | 3 Gates risco | Rejeicao rapida |
| 011 | Session ID | Substituido 012 |
| 012 | Magic Number | 3 niveis isol. |

---

## 7. Componentes do Sistema

### 7.1 Os 4 Agentes Operacionais

| Agente | Magic | Funcao |
|--------|-------|--------|
| Diarios | 234800 | Operador contextual, reflexao IA e publicacao de features intraday |
| Micro Tend. | 234700 | Sinais ML LightGBM |
| RL 5000 | 234500 | RL supervisionado |
| RL Direto | 234600 | RL autonomo |

Scripts de lançamento:

- **Diarios:** `start_journals_full_display.py`
- **Micro Tendencia:** `agente_micro_tendencia_winfut.py`
- **RL 5000:** `INICIAR_AGENTE_RL_5000.bat` -> `scripts/agente_com_supervision.py` -> `operar_novo_agente_rl_real_antiovertrading.py`
- **RL Direto:** `INICIAR_AGENTE_RL_DIRETO.bat` -> `scripts/agente_rl_direto_independente.py`

#### 7.1.1 Governanca operacional do Micro Tendencia

- O micro tendencia registra o aprendizado em `data/models/micro_tendencia/CHANGELOG.md`.
- O changelog de cada versao descreve:
  - episodios usados
  - win rate de treino e validacao
  - delta vs versao anterior
  - rollback quando aplicavel
  - observacoes de aprendizado e mudancas de comportamento
- O retreino automatizado do micro usa governanca atual de:
  - `500` rewards novos como threshold
  - `180` minutos de cooldown minimo entre retreinos
- O modelo LightGBM recarrega automaticamente apos retreino bem-sucedido, sem exigir restart do `INICIAR_MICRO_TENDENCIA_AUTO_TRADE.bat`.
- O painel e o terminal exibem o aprendizado corrente, o ultimo treino persistido e o cooldown restante.

### 7.2 Modulos Criticos (src/application/)

| Modulo | Arquivo | Testes |
|--------|---------|--------|
| Monitor Posicoes | ac5_8_position_monitor | 21/21 |
| Feedback Valid. | ac5_9_feedback_validator | 21/21 |
| Drift Detector | ac6_7_drift_detector | 24/24 |
| Online Learning | ac6_8_online_learning | 18/18 |
| Baseline Comp. | ac6_9_baseline_comparator | 20/20 |
| Ambiente RL | rl_trading_environment | 21/21 |
| Retrain Sched. | rl_retrain_scheduler | 24/24 |
| Rollback RL | rl_model_rollback_manager | 17/17 |
| Motor Decisao | motor_decisao_isolado | 24/24 |
| Isolamento Pos. | posicao_isolamento | 7/7 |
| P1 Closure | p1_learning_closure | 27/27 |
| Classificador | ml_classifier | Sim |
| Executor Ordens | orders_executor | Sim |
| Validador Risco | risk_validator | Sim |
| Profit Protect. | profit_protection_engine | Sim |
| Conflitos | multi_agent_conflict_resolver | Sim |
| Guardian Coord. | guardian_agent_coordinator | Sim |
| Guardian Log | macro_guardian_universal_log | Sim |

### 7.3 Infraestrutura

| Componente | Arquivo |
|------------|---------|
| MT5 Adapter | mt5_adapter.py |
| MT5 Proxy | mt5_adapter_proxy.py |
| Trade Repo | trade_repository.py |
| Forex Provider | forex_api_provider.py |
| Terminal Enforcer | terminal_isolation_enforcer.py |
| Schema ORM | schema.py (SQLAlchemy 2.x) |

### 7.4 Persistencia de Dados

| Armazenamento | Tipo | Conteudo |
|---------------|------|----------|
| data/db/*.db | SQLite | Bancos operacionais isolados por agente |
| outputs/*.json | JSON | Posicoes ativas |
| outputs/*.log | Log | Logs por agente |
| outputs/diario_*.md | Markdown | Diarios |
| outputs/analysis/diario_market_features_latest.json | JSON | Snapshot canonico do Diario para consumo multiagente |
| data/backtest/*.json | JSON | Artefatos Gate 2 |
| data/models/ | Pickle | Modelos ML/RL |
| data/BDI/ | CSV | Calendario econ. |

### 7.5 Convencao de Identificacao no MT5

- O campo `magic` segue o Magic Number do agente.
- O comentario das ordens usa o padrao:
  - `agente|EA<magic>|MA<order_prefix>`
- Isso facilita auditoria de ordens no MT5 e triagem de tickets por agente.

---

## 8. Regras de Negocio

### 8.1 Regras de Entrada

| ID | Regra | Valor |
|----|-------|-------|
| RN-01 | Confianca minima | 45% |
| RN-02 | Risk/Reward minimo | 1.5:1 |
| RN-03 | Max posicoes/agente | 1 |
| RN-04 | Max trades/dia/agente | 6 |
| RN-05 | Horario limite entradas | 17:25 BRT |
| RN-06 | Inicio operacoes | 09:00 BRT |

### 8.2 Regras de Aprendizado do Micro Tendencia

| ID | Regra | Valor |
|----|-------|-------|
| RL-01 | Threshold de retreino | 500 rewards novos |
| RL-02 | Cooldown minimo entre retreinos | 180 minutos |
| RL-03 | Recarregamento do LGBM | Automatico apos retreino bem-sucedido |
| RL-04 | Fonte de episodios do micro | `rl_episodes` com `source = 'MICRO_AGENT'` |

### 8.2 Regras de Saida

| ID | Regra | Valor |
|----|-------|-------|
| RN-07 | Loss maximo diario | 500 pontos |
| RN-08 | Cooling apos SL | 30 minutos |
| RN-09 | Motivos fechamento | TP/SL/MANUAL/TIMEOUT |
| RN-10 | Trailing stop | Dinamico por ATR |

### 8.3 Regras de Capital (Gate 2 de Escala)

| Condicao | Capital | Exit Code |
|----------|---------|-----------|
| P0-2 PASS | R$100k (ampliado) | 0 |
| P0-2 FAIL | R$50k (conservador) | 1 |
| P0-2 executando | R$50k (conservador) | 2 |
| P0-2 erro | R$50k (conservador) | 3 |

Artefatos obrigatorios em `data/backtest/`:

- `dataset_audit.json`
- `backtest_results.json`
- `gate2_decision.json`
- `p0_2_status.json`

**Falha NUNCA libera capital ampliado.**

> Neste PRD, `Gate 2` refere-se exclusivamente à escala de capital validada por backtest.
> A liberação para produção depende de um gate final operacional separado, coberto por staging/UAT
> e pelas evidências diárias por agente.

### 8.4 Regras de Isolamento

| Nivel | Mecanismo | Garantia |
|-------|-----------|----------|
| 1 | Magic Number MT5 | Broker persiste |
| 2 | Session ID + JSON | Arquivo/agente |
| 3 | MotorDecisaoIsolado | Modulo Python |

### 8.5 Regras de Startup

1. Validar ambiente (Python, MT5, SQLite)
2. Operador escolhe o launcher canonico do agente: `INICIAR_AGENTE_RL_5000.bat` ou `INICIAR_AGENTE_RL_DIRETO.bat`
   - `launch_agent_with_ml_v1_2_3.py` usa `data/db/trading_micro_tendencia.db`
   - `agente_com_supervision.py` usa `data/db/trading_rl_5000.db`
   - `agente_rl_direto_independente.py` usa `data/db/trading_rl_direto.db`
   - `INICIAR_DIARIOS.bat` usa `data/db/trading_diarios.db` e exporta `DIARIOS_DB_PATH`
3. Em modo simulado, usar a opção de avaliação correspondente; em modo real, exigir confirmação humana explícita
4. Pre-flight: confianca, heartbeat, latencia
5. Sincronizar trades MT5 → SQLite em modo best effort; se o lock do banco estiver ocupado, o pre-flight registra o aviso e segue sem bloquear a operação real
6. Aplicar licoes BDI
7. Carregar dataset ML
8. Iniciar diarios de observabilidade

### 8.6 Regras do Guardian

| Indicador | Threshold | Acao |
|-----------|-----------|------|
| USD/BRL | 0.50% | Penalidade confianca |
| S&P500 | 0.80% | Possivel kill switch |
| WIN | 500 pontos | Alerta critico |
| Macro score | +/-15 | Reavaliacao cenario |

---

## 9. Integracoes e Dependencias

### 9.1 Dependencias Externas

| Sistema | Uso | Critico |
|---------|-----|---------|
| MetaTrader 5 | Broker gateway | Sim |
| SQLite | Banco principal | Sim |
| AwesomeAPI | Forex (12+ pares) | Nao |
| FRED API | Dados econ. EUA | Nao |
| TwelveData | Dados mercado | Nao |
| AlphaVantage | Dados alternativos | Nao |
| Finnhub | Dados globais | Nao |
| Telegram Bot | Notificacoes | Nao |

### 9.2 Stack Tecnologico

| Camada | Tecnologia |
|--------|------------|
| Linguagem | Python 3.11+ |
| Broker API | MetaTrader5 (lib) |
| Indicadores | TA-Lib |
| ML | scikit-learn, LightGBM, XGBoost |
| RL | gymnasium (OpenAI Gym) |
| API REST | FastAPI |
| Streaming | WebSocket (nativo) |
| Banco | SQLite3 + SQLAlchemy 2.x |
| Testes | pytest |
| Tipos | mypy (strict) |
| Formatacao | Black (88) + isort |
| SO | Windows 11 (obrigatorio MT5) |

### 9.3 Variaveis de Ambiente

| Variavel | Descricao | Obrig. |
|----------|-----------|--------|
| MT5_LOGIN | Login broker | Sim |
| MT5_PASSWORD | Senha broker | Sim |
| MT5_SERVER | Servidor MT5 | Sim |
| MT5_TERMINAL_PATH | Caminho terminal | Sim |
| DB_PATH | Caminho SQLite | Sim |
| MICRO_TENDENCIA_DB_PATH | Override do SQLite do launcher micro tendência | Nao |
| RL5000_DB_PATH | Override do SQLite do launcher RL 5000 | Nao |
| RL_DIRETO_DB_PATH | Override do SQLite do launcher RL direto | Nao |
| MODEL_PATH | Dir. modelos | Sim |
| FRED_API_KEY | API FRED | Nao |
| TWELVEDATA_API_KEY | API TwelveData | Nao |
| ALPHAVANTAGE_API_KEY | API AlphaVantage | Nao |
| FINNHUB_API_KEY | API Finnhub | Nao |
| TELEGRAM_BOT_TOKEN | Bot Telegram | Nao |

---

## 10. Restricoes e Premissas

### 10.1 Restricoes

| ID | Restricao |
|----|-----------|
| C-01 | Windows obrigatorio (MT5) |
| C-02 | SQLite ate 04/2026 |
| C-03 | Single connection SQLite |
| C-04 | B3: 09:00-17:55 BRT |
| C-05 | Apenas WIN$N |
| C-06 | Capital conservador default |

### 10.2 Premissas

| ID | Premissa |
|----|----------|
| P-01 | MT5 instalado e configurado |
| P-02 | Internet estavel no mercado |
| P-03 | Python 3.11+ c/ dependencias |
| P-04 | Operador confirma auto-trade |
| P-05 | Dados historicos (min 30 dias) |
| P-06 | APIs externas com chaves |

---

## 11. Roadmap e Fases

### 11.1 Fase 1 - Fundacao (Concluida)

- Arquitetura DDD com camadas
- Entities, Value Objects, Enums, Exceptions
- MT5 Adapter com proxy (cache/retry)
- SQLite schema com SQLAlchemy 2.x
- Pipeline AC1-AC4

### 11.2 Fase 2 - Execucao e Risco (Concluida)

- AC5: Command Pattern para ordens
- AC5.8: Monitoramento RT posicoes
- AC5.9: Validacao de feedback
- Risk Validator (3 Gates)
- Profit Protection Engine
- ATR Calibrator

### 11.3 Fase 3 - Aprendizado e RL (Concluida)

- AC6.7: Deteccao de drift
- AC6.8: Online learning controlado
- AC6.9: Comparador baseline
- RL Trading Environment (Gym)
- RL Retrain Scheduler
- RL Model Rollback Manager
- P1 Learning Engine (causal 7 etapas)

### 11.4 Fase 4 - Multi-Agente e Guardian (Concluida)

- Isolamento Magic Number (ADR-012)
- Motor de Decisao Isolado
- Resolucao de conflitos entre agentes
- Guardian Agent Coordinator
- Macro Guardian Universal Log
- Storytelling (Reflection Action Channel)

### 11.5 Fase 5 - Validacao Operacional e GO LIVE (Atual)

- Validacao final de producao
- Operacao com Gate 2 de escala de capital ja validado
- Gate final operacional separado de Gate 2
- Monitoramento diario + diarios IA
- Emergency rollback procedures
- Metricas de sucesso em producao

### 11.6 Fase 6 - Evolucao (Pos-GO LIVE)

- Migracao SQLite → PostgreSQL
- Suporte multi-terminal MT5
- Modelos ML avancados
- Expansao para outros mercados

### 11.7 Status de Entregas (19/03/2026)

> Os itens abaixo refletem entrega em código; a validação operacional final segue separada e prevalece o estado dos artefatos correntes em `19/03/2026`.

| Componente | Status | Testes |
|------------|--------|--------|
| AC5.8 Position Monitor | Impl. | 21/21 |
| AC5.9 Feedback Valid. | Impl. | 21/21 |
| AC6.7 Drift Detector | Impl. | 24/24 |
| AC6.8 Online Learning | Impl. | 18/18 |
| AC6.9 Baseline Comp. | Impl. | 20/20 |
| RL Trading Env. | Impl. | 21/21 |
| RL Retrain Scheduler | Impl. | 24/24 |
| RL Model Rollback | Impl. | 17/17 |
| Motor Decisao Isolado | Impl. | 24/24 |
| Posicao Isolamento | Impl. | 7/7 |
| P1 Learning Closure | Impl. | 27/27 |
| Multi-Agent Conflict | Impl. | Sim |
| Guardian Universal | Impl. | Sim |
| Storytelling B | Impl. | Sim |
| Order Manager Learner | Impl. | Sim |
| **Total testes** | **2.237** | **350+** |

### 11.8 Backlog de Evolução do Micro Tendência (Capturado 19/03/2026)

> Itens capturados em reunião estratégica com Head de Finanças.
> Origem: Reflexões IA do diário + análise de operações do dia.
> Governança: Nenhuma evolução é executada sem priorização formal.

#### 11.8.1 Itens de Alta Prioridade

| ID | Evolução | Justificativa | Seção Impactada |
|----|----------|---------------|-----------------|
| EV-MT-01 | **Calibrar threshold confidence de 50% para 35%** em regime CAUTELOSO | Sistema manteve 30% de confidence e não executou; 62 oportunidades perdidas | RN-01 (8.1) |
| EV-MT-02 | **Integrar Macro Score ao decision gate** — Score >=30 deve forçar pelo menos 1 avaliação/hora | Macro Score 33.6 (excelente) foi ignorado pelo motor de decisão | Guardian (8.6) + Pipeline (4.1) |

#### 11.8.2 Itens de Média Prioridade

| ID | Evolução | Justificativa | Seção Impactada |
|----|----------|---------------|-----------------|
| EV-MT-03 | **Revisar cascata dos 7 filtros Anti-OT** — Possível bloqueio excessivo em série | Reflexão IA: "Estou só gerando ruído"; filtros podem estar sobrepostos | R-09 (13) |
| EV-MT-04 | **Criar detector de "oportunidade óbvia"** — Range >3000 pts + ADX >30 = não ficar 100% HOLD | Dia com 4.165 pts de range e nenhuma execução pelo micro | RF novo (4.2) |

#### 11.8.3 Itens de Baixa Prioridade

| ID | Evolução | Justificativa | Seção Impactada |
|----|----------|---------------|-----------------|
| EV-MT-05 | **Reduzir dependência de indicadores atrasados** | Reflexão IA: "Meus dados não estão capturando o que move o preço" | Pipeline (4.1) |
| EV-MT-06 | **Adicionar price action puro ao modelo LightGBM** | Correlação fraca entre features atuais e movimento de preço | Governança (7.1.1) |

#### 11.8.4 Métricas de Referência (19/03/2026)

| Métrica | Valor Atual | Observação |
|---------|-------------|------------|
| Oportunidades detectadas | 62 | Pelo micro tendência |
| Oportunidades executadas | 0 | 0% taxa de execução |
| Movimento perdido | 19.885 pts | ~R$ 99 em rewards |
| Confidence médio | 30% | Abaixo do threshold 50% |
| Macro Score médio | 33.6 | Acima do limiar 15 |
| Status final | INATIVIDADE_INJUSTA | Excesso de conservadorismo |

#### 11.8.5 Governança de Implementação

1. Cada item deve passar por **deliberação técnica** antes de desenvolvimento
2. Alterações em regras de negócio (Seção 8) exigem **aprovação do Head de Finanças**
3. Novos RFs (Seção 4) devem ter **AC testáveis** definidos antes da implementação
4. Toda evolução deve ser **versionada** no changelog do micro tendência
5. Rollback automático se **win rate cair >5%** após implementação

---

## 12. Criterios de Aceitacao

### 12.1 Criterios por Modulo

| Modulo | Criterio | Status |
|--------|----------|--------|
| Pipeline ML | F1 >0.65 classificador | OK |
| Risk Gates | 3 gates sem bypass | OK |
| Isolamento | Zero interferencia 4 agentes | OK |
| Posicoes | Check ticket cada 15s | Em validacao operacional |
| Drift | Alerta Z-score threshold | Em validacao operacional |
| Online Learning | Rollback se degrada | Em validacao operacional |
| Guardian | Kill switch funcional | Em validacao operacional |
| Gate 2 | FAIL nunca libera ampliado | Artefato atual `FAIL` em 19/03/2026; PASS historico de 12/03/2026 nao substitui o estado corrente |

### 12.2 Criterios Globais para GO LIVE

| ID | Descricao | Status |
|----|-----------|--------|
| CA-01 | Testes unitarios passando | PASS em 19/03/2026 (suite canônica `BL-07`: 257 testes verdes) |
| CA-02 | mypy --strict sem erros | PASS em 19/03/2026 (baseline canônico de type-check no `BL-07`) |
| CA-03 | Cobertura >=80% modulos | PASS em 19/03/2026 (`BL-07` com 88.51% nos módulos canônicos) |
| CA-04 | 5 dias simulado sem bugs | Pend. evidencia operacional |
| CA-05 | Gate 2 P0-2 com dados reais | FAIL no artefato atual de 19/03/2026; PASS historico em 12/03/2026 mantido apenas como referencia |
| CA-06 | Diarios IA coerentes | Em validacao operacional; bootstrap e narrativas agora exibem `daily_confidence_gate` em `INICIAR_DIARIOS.bat`, `INICIAR_AGENTE_RL_5000.bat` e `start_journals_full_display.py` |
| CA-07 | 4 agentes paralelos OK | Em validacao operacional |
| CA-08 | Kill switch testado | Em validacao operacional |
| CA-09 | Backup/restore validado | Em validacao operacional |
| CA-10 | Documentacao atualizada | PASS em 19/03/2026; PRD/STATUS/BACKLOG sincronizados com os artefatos correntes de gate |

### 12.3 Matriz de Evidencias

| Criterio | Script/Teste | Evidencia | Owner |
|---------|--------------|-----------|-------|
| BL-01 | `scripts/validate_staging_readiness.py` | `outputs/release_gates/bl01_*.json` | Agente 2 |
| BL-07 | `scripts/validate_release_quality_gate.py` + `scripts/validate_go_live_gates.py` | `outputs/release_gates/bl07_*.json` | Agente 2 |
| BL-08 | `tests/uat/uat_test_cases.py` + `scripts/validate_go_live_gates.py` | `outputs/release_gates/bl08_*.json` e `go_live_decision.json` com `last_session_summary.json` parseavel e fresco (`<=36h`) | Agente 2 |
| Runtime RL/MT5 sem `preco_saida=0.0` e sem `DESCONHECIDO` persistente | `tests/unit/test_agente_rl_direto_runtime.py` + `tests/unit/test_mt5_adapter_runtime.py` | `outputs/agente_posicao_*.json` e logs do `RL_DIRETO` | Agente 1 |
| Fechamento diario por agente | `prompts/fechamento_diario.py` + `tests/unit/test_fechamento_diario.py` | `data/fechamento_diario/*` e `docs/agente_autonomo/AGENTE_AUTONOMO_BACKLOG.md` | Agente 3 |
| Gate 2 de escala de capital | `data/backtest/gate2_decision.json` | `data/backtest/*.json` | Produto/Trading |

---

## 13. Riscos e Mitigacoes

### R-01: Desconexao MT5

- **Impacto:** Alto | **Prob.:** Media
- **Mitigacao:** MT5 Proxy com retry + heartbeat

### R-02: Degradacao modelo ML

- **Impacto:** Alto | **Prob.:** Media
- **Mitigacao:** Drift AC6.7 + rollback automatico

### R-03: Conflito entre agentes

- **Impacto:** Alto | **Prob.:** Baixa
- **Mitigacao:** 3 niveis isolamento (ADR-012)

### R-04: Loss acima do limite

- **Impacto:** Alto | **Prob.:** Baixa
- **Mitigacao:** Gate risco + kill switch Guardian

### R-05: Dados macro indisponiveis

- **Impacto:** Medio | **Prob.:** Media
- **Mitigacao:** Fallback score neutro + cache TTL

### R-06: SQLite concorrencia

- **Impacto:** Medio | **Prob.:** Media
- **Mitigacao:** Transaction log + PostgreSQL (Fase 6)

### R-07: Latencia rede broker

- **Impacto:** Medio | **Prob.:** Baixa
- **Mitigacao:** SQLite local + proxy cache

### R-08: Evento macro nao mapeado

- **Impacto:** Medio | **Prob.:** Media
- **Mitigacao:** Guardian + BDI calendario

### R-09: Overtrading

- **Impacto:** Medio | **Prob.:** Baixa
- **Mitigacao:** 7 filtros + max 6 trades/dia

### R-10: Perda de dados

- **Impacto:** Alto | **Prob.:** Baixa
- **Mitigacao:** Backup diario + transaction log

### R-11: Revenge trading

- **Impacto:** Medio | **Prob.:** Media
- **Mitigacao:** Cooling 30min mesma direcao

### R-12: Capital ampliado sem validacao

- **Impacto:** Alto | **Prob.:** Baixa
- **Mitigacao:** Gate 2: falha NUNCA libera

---

## Apendice A - Glossario

| Termo | Definicao |
|-------|-----------|
| WIN$N | Mini Indice Futuro B3 |
| MT5 | MetaTrader 5 |
| Magic Number | ID unico de EA no MT5 |
| SL | Stop Loss |
| TP | Take Profit |
| ATR | Average True Range |
| BDI | Calendario economico |
| Gate 2 | Escala de capital validada por backtest |
| Gate final | Validacao operacional antes do GO LIVE |
| Drift | Degradacao modelo ML |
| P1 Learning | Causal 7 etapas |
| Guardian | Monitor macro emergencias |

## Apendice B - Estrutura de Arquivos

```text
operador-day-trade-win/
├── BAT/              # Orquestracao Windows
├── scripts/          # 309 scripts Python
├── src/
│   ├── domain/       # Entities, VOs, Enums
│   ├── application/  # 75+ use cases
│   │   ├── services/ # 27+ servicos
│   │   │   ├── macro_score/
│   │   │   ├── ml/
│   │   │   └── backtest/
│   │   └── reconciliadores/
│   ├── infrastructure/ # 40+ adaptadores
│   │   ├── adapters/
│   │   ├── providers/
│   │   ├── repositories/
│   │   ├── database/
│   │   └── persistence/
│   ├── interfaces/   # FastAPI + WebSocket
│   ├── ml/           # ML standalone
│   └── adapters/     # Alto nivel
├── tests/            # 154 arq., 2.237 testes
│   ├── unit/         # 98 arquivos
│   ├── integration/  # 11 arquivos
│   ├── performance/
│   └── uat/
├── data/
│   ├── db/*.db
│   ├── models/
│   ├── backtest/
│   └── BDI/
├── outputs/          # Runtime
├── docs/             # Documentacao
└── config/           # Ambiente
```

## Apendice C - Metricas de Qualidade

| Metrica | Valor |
|---------|-------|
| Arquivos Python src/ | 206 |
| Scripts operacionais | 309 |
| Arquivos de teste | 154 |
| Testes coletados | 2.237 |
| Testes passando | 350+ |
| Type hints mypy | 100% |
| Pre-commit hook | mypy + pytest |
| Pytest markers | 12 |
| ADRs registrados | 12+ |
| Documentos canonicos | 9 |

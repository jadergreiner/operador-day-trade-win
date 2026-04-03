# Arquitetura Alvo

## Indice

- [Escopo de Execucao (4 Agentes)](#escopo-de-execucao-4-agentes)
- [Isolamento por Magic Number
  (EA ID)](#isolamento-por-magic-number-ea-id)
- [Arquitetura Alvo e Contrato](#arquitetura-alvo-e-contrato)
- [Objetivo](#objetivo)
- [Fluxo Macro](#fluxo-macro)
- [Contrato Gate 2 (P0-2)](#contrato-gate-2-p0-2)
- [Invariantes
  de Compatibilidade](#invariantes-de-compatibilidade)
- [Diarios e Treinamento
  de Modelos](#diarios-e-treinamento-de-modelos)
- [Arquitetura Executada
  (Fluxo Real Atual)](#arquitetura-executada-fluxo-real-atual)
- [Resumo](#resumo)
- [Visao Executiva do Launcher](#visao-executiva-do-launcher)

## Escopo de Execucao (4 Agentes)

Todas as decisoes arquiteturais e evolucoes devem ter como
alvo um destes quatro executores:

| Agente | Launcher | Magic Number |
|---|---|---|
| Diários | `INICIAR_DIARIOS.bat` | 234800 (operador contextual) |
| Micro Tendência | `INICIAR_MICRO_TENDENCIA_AUTO_TRADE.bat` | 234700 |
| RL 5000 | `INICIAR_AGENTE_RL_5000.bat` | 234500 |
| RL Direto | `INICIAR_AGENTE_RL_DIRETO.bat` | 234600 |

Cada agente possui um Magic Number (EA ID) exclusivo no MT5
para isolamento total de ordens e posicoes. Detalhes na secao
[Isolamento por Magic Number](#isolamento-por-magic-number-ea-id).

Estado atual: os Grupos 1 e 2 ja estao materializados no runtime;
staging, UAT e Gate 2 permanecem como validacao operacional final.

## Isolamento por Magic Number (EA ID)

**Status:** Implementado (16/03/2026)
**Referência:** ADR-012 em `docs/ADRS.md`

### Problema Resolvido

Quando dois ou mais agentes RL operavam em paralelo no mesmo
símbolo WIN$N, um agente detectava posições abertas pelo outro
e tentava modificar SL/TP, resultando em erro MT5 retcode
10013 (request rejected). Monitoramento de posições e proteção
de lucros também conflitavam.

### Decisão Arquitetural

Atribuir um Magic Number (EA ID) único e fixo por agente.
Toda ordem enviada ao MT5 carrega o magic do agente emissor.
Toda consulta de posições filtra pelo magic do agente corrente.

### Implementação — 3 Níveis de Isolamento

**Nível 1 — MT5 Magic Number (EA ID):**

- Campo `magic_number` na entidade `Order`
  (`src/domain/entities/trade.py`)
- `MT5Adapter.send_order()` usa `order.magic_number`
- Cada script define constante `MAGIC_NUMBER`
- Filtragem em `mt5.positions_get()` por magic

**Nível 2 — Session ID + JSON isolado:**

- Cada agente grava arquivo próprio:
  `outputs/agente_posicao_{session_id}.json`
- `PosicaoIsoladaManager` valida ownership
  (`src/application/posicao_isolamento.py`)

**Nível 3 — Memória e variáveis de processo:**

- `tickets_proprios: set[int]` no RL 5000
- `AgentePosicaoStatus` com ticket no RL Direto
- Sem variável global compartilhada entre processos

### Tabela de Magic Numbers

| Faixa | Agente | Constante |
|---|---|---|
| 234000 | Default (entidade Order) | `Order.magic_number` |
| 234500 | RL 5000 | `MAGIC_NUMBER` |
| 234600 | RL Direto | `MAGIC_NUMBER` |
| 234700 | Micro Tendência | `MAGIC_NUMBER` |
| 234800 | Diários (operador contextual) | `MAGIC_NUMBER` |

### Funções Protegidas por Magic

- `monitorar_posicoes()` — filtra por magic (RL 5000)
- `processar_protecao_lucros()` — filtra por magic
- `proteger_lucro_trade()` — filtra por magic
- `verificar_posicao_no_mt5()` — filtra por magic (Direto)
- `monitor_hedge_orphans()` — filtra por magic (Micro)
- `execute_entry()` — envia magic na Order (Micro)
- `_close_position()` — envia magic na Order (Micro)

### Invariante

Nenhum agente pode operar sobre posições de outro agente.
Ordens sem magic correto sao rejeitadas ou ignoradas.

## Arquitetura Alvo e Contrato

### Objetivo

Definir o contrato arquitetural ativo para operacao dos launchers:

- `INICIAR_DIARIOS.bat`
- `INICIAR_MICRO_TENDENCIA_AUTO_TRADE.bat`
- `INICIAR_AGENTE_RL_5000.bat`
- `INICIAR_AGENTE_RL_5000_FIXED.bat`

Este documento e canonico para decisoes de fluxo operacional.

### Fluxo Macro

1. Preparacao de ambiente e pre-flight.
2. Sincronizacao local MT5 -> SQLite.
3. Aplicacao de contexto diario (BDI/ML).
4. Consulta de status P0-2 (Gate 2) para escala de capital.
5. Bootstrap Python e execucao do agente.
6. Sincronizacao final e encerramento rastreavel.
7. Manutencao operacional: load test e cleanup programado (Etapa 4).

### Contrato Gate 2 (P0-2)

Entrada: `scripts/check_p0_2_status.py` (exit code).

- `0`: PASS -> capital ampliado.
- `1`: FAIL -> capital conservador.
- `2`: em execucao -> capital conservador.
- `3`: indefinido/erro -> capital conservador.

Artefatos obrigatorios:

- `data/backtest/dataset_audit.json`
- `data/backtest/backtest_results.json`
- `data/backtest/gate2_decision.json`
- `data/backtest/p0_2_status.json`

### Invariantes de Compatibilidade

- Gate 2 altera somente escala de capital.
- Nenhuma regra de entrada/saida do runtime e alterada por este fluxo.
- Falhas de pipeline nao podem liberar capital ampliado.

### Diarios e Treinamento de Modelos

Os diarios sao parte do contrato operacional e devem alimentar treinamento de
modelos (ML/RL). O fluxo atual gera diarios por dois caminhos:

- `INICIAR_DIARIOS.bat` inicia diarios automatizados (via `scripts/start_journals_full_display.py`).
- `INICIAR_MICRO_TENDENCIA_AUTO_TRADE.bat` gera `data/diarios/diario_head_YYYYMMDD.md`
  via `scripts/aplicar_licoes_bdi.py`.

---

## Componentes Core Implementados

### AC5.9 Validador de Feedback de Execucao

**Status:** ✅ IMPLEMENTADO (15/03/2026)

**Localizacao:** `src/application/ac5_9_feedback_validator.py`

**Propósito:** Validar saude do ciclo de feedback entre trades
executadas e dados de aprendizado para ML/RL.

**Classes:**
- `FeedbackValidator`: Modulo principal com 5 validacoes
- `FeedbackHealthReport`: Relatorio compilado com status geral
- `FeedbackValidationResult`: Resultado estruturado

**Validacoes Implementadas:**
1. **Correlacao:** Percentual de trades com feedback associado
2. **Tipos de Outcome:** Validacao de WIN/LOSS/BREAKEVEN
3. **Consistencia PnL:** Compatibilidade outcome <-> valor
4. **Healthcheck Geral:** Score qualidade + recomendacoes

**Relatorios:**
- JSON: Estruturado para processamento automatico
- Markdown: Legivel para analise manual com recomendacoes

**Testes:** 21 testes unitarios, 21/21 PASSING (100%)

---

### P2 - Trilha RL Operacional: Ambiente Gym de Trading

**Status:** ✅ IMPLEMENTADO (16/03/2026)

**Localizacao:** `src/application/rl_trading_environment.py`

**Propósito:** Fornecer ambiente compativel com OpenAI Gym para
treinar agentes RL (Reinforcement Learning) em contexto de trading.

**Classes:**
- `TradingGymEnvironment`: Classe principal compativel Gym
  - Metodos: `reset()`, `step()`, `render()` (interface Gym padrao)
  - Persistencia de episodios e historico
  - Calculo de metricas de reward
  - Save/load checkpoints versionados (JSON)
- `RLRewardMetrics`: Dataclass com metricas consolidadas
  - total_reward, win_rate, sharpe_ratio, max_drawdown, trades_executados
- `EpisodeCallback`: Dataclass para rastreamento de episodios
  - episodio, timestamp (ISO), trades_abertos, win_rate, total_pnl
- `TrainingState`: Dataclass para estado do treino
  - episodio, iteracao, melhor_reward, reward_medio, versao_modelo

**Funcionalidades:**
1. **Interface Gym Completa:** reset(), step(), render()
2. **Episode Callbacks:** Rastreamento de episodios com metricas
3. **Metricas de Reward:** Win rate, Sharpe ratio, Drawdown maximo, PnL
4. **Save/Load Checkpoints:** Versionado semanticamente (v1.2.3)
5. **Historico Completo:** Persistencia de episodios em memoria + JSON
6. **Relatorios:** Exportacao em JSON estruturado + Markdown legivel

**Acoes Suportadas:**
- 0: HOLD (manter posicao aberta)
- 1: BUY (abrir posicao comprada)
- 2: SELL (fechar posicao)
- 3: FECHAR FORCA (fechar imediatamente)

**Estado Ambiente:** [capital_disponivel, preco_atual, posicao_ativa]

**Exemplo de Uso:**

```python
from src.application.rl_trading_environment import TradingGymEnvironment

env = TradingGymEnvironment(
    capital_inicial=10000.0,
    alavancagem=2.0,
)

estado = env.reset()
episodio = 0

for _ in range(5):
    episodio += 1
    estado = env.reset()

    for step in range(100):
        acao = agent.escolher_acao(estado)
        estado, reward, done, info = env.step(acao)
        if done:
            break

    # Registrar episodio
    env.registrar_episodio(
        episodio=episodio,
        trades=10,
        win_rate=0.65,
        total_pnl=1500.0,
    )

    # Salvar checkpoint periodicamente
    if episodio % 10 == 0:
        env.salvar_checkpoint(
            versao=f"v1.0.{episodio}",
            melhor_reward=2000.0,
        )

# Gerar relatorio final
relatorio = env.gerar_relatorio_markdown()
print(relatorio)
```

**Metricas Monitoradas:**
- Total Reward: Somatorio de rewards dos episodios
- Win Rate: % de episodios/trades vencedores
- Sharpe Ratio: Retorno ajustado por desvio padrao
- Max Drawdown: Maior perda percentual
- Trades Executados: Contagem total

**Testes:** 21 testes unitarios, 21/21 PASSING (100%)

**Capacidades:**
- ✅ Compativel com OpenAI Gym (interface padrao)
- ✅ Episode callbacks para rastreamento
- ✅ Save/load checkpoints versionados
- ✅ Metricas automaticas (Sharpe, drawdown, win rate)
- ✅ 100% type hints (mypy validado)
- ✅ 100% em Portugues (docstrings, variaveis)

**Proximos Passos Opcionais (P2):**
1. Scheduler de retrain automatico
2. Rollback automatico por degradacao
3. Dashboard de metricas em tempo real

---

### AC6.7 Detector de Drift de Modelo em Producao

**Status:** ✅ IMPLEMENTADO (15/03/2026)

**Localizacao:** `src/application/ac6_7_drift_detector.py`

**Propósito:** Detectar degradacao de performance do modelo
em producao comparando metricas atuais contra baseline com Z-score.

**Classes:**
- `DriftAlertSeverity`: Enum com niveis (LOW, MEDIUM, CRITICAL)
- `DriftMetrics`: Dataclass com metricas calculadas
- `DriftAlert`: Alerta de degradacao detectada
- `DriftDetector`: Classe principal com logica de deteccao

**Funcionalidades:**
1. **Sliding Window:** Ultimos N trades para analise (default 100)
2. **Calculo de Metricas:** Win_rate, Sharpe, F1, PnL, Std Dev
3. **Deteccao Estatistica:** Z-score contra baseline
4. **Alertas Estruturados:** COM severidade (LOW/MEDIUM/CRITICAL)
5. **Relatorios:** JSON (processamento) + Markdown (leitura humana)
6. **Persistencia:** Salva relatorios em arquivo para auditoria

**Metricas Monitoradas:**
- Win Rate: % de trades vencedores
- Sharpe Ratio: Retorno ajustado por risco
- F1 Score: Balance precision/recall
- Avg PnL: PnL medio por trade
- Std Dev: Consistencia de resultado

**Z-score Threshold:** Default 2.0 (configuravel)
- Z-score < 2.0: Normal (sem alerta)
- 2.0 ≤ Z-score < 3.0: MEDIUM (possivel degradacao)
- Z-score ≥ 3.0: CRITICAL (degradacao significativa)

**Testes:** 24 testes unitarios, 24/24 PASSING (100%)

**Metricas de Codigo:**
- LOC: 422 linhas de codigo
- Type hints: 100%
- Docstrings: Cobertura completa
- mypy --strict: OK (sem erros)

---

### AC6.8 Online Learning Controlado

**Status:** ✅ IMPLEMENTADO (15/03/2026)

**Localizacao:** `src/application/ac6_8_online_learning.py`

**Propósito:** Treino incremental de modelos ML com ajuste de
parametros durante operacao e rollback automatico por degradacao.

**Classes Principais:**
- `OnlineLearningController`: Controlador principal
- `ModelVersion`: Armazena versao do modelo com metadados
- `TrainingResult`: Resultado de uma sessao de treino
- `ValidationResult`: Resultado de validacao
- `RollbackResult`: Resultado de operacao rollback

**Funcionalidades:**

1. **Treino Incremental:**
   - Processa batch de dados por sessao
   - Calcula metricas automaticamente
   - Atualiza estado interno do modelo
   - Persistencia de historico de treinamento

2. **Validacao Contra Baseline:**
   - Compara metricas atuais vs baseline
   - Deteccao de degradacao com Z-score
   - Relatorios em JSON e Markdown
   - Comparacao estruturada (baseline, current, delta, zscore)

3. **Persistencia Versionada:**
   - Semantic versioning (v1.0.0, v1.0.1, etc)
   - Salva metadados completos (timestamp,  metricas, samples)
   - Carregamento de versao anterior
   - Auditoria de todas as versoes

4. **Rollback Automatico:**
   - Deteccao de degradacao automatica
   - Restauracao de versao anterior se necessario
   - Threshold configuravel de win_rate
   - Rastreamento completo de rollback

**Metricas Calculadas:**
- Win Rate: % de trades WIN
- Loss Rate: % de trades LOSS
- Avg PnL: PnL medio
- Total PnL: PnL cumulativo
- F1 Score: Metrica balance
- Sharpe Ratio: Retorno ajustado por risco
- Std Dev PnL: Desvio padrao

**Fluxo Tipico:**

```text
1. controller = OnlineLearningController(
     model_name="trader",
     baseline_metrics={"win_rate": 0.65}
   )

2. result = controller.train_incremental(new_data)
   # Treina e calcula metricas

3. validation = controller.validate_model(new_data)
   # Valida contra baseline

4. if validation["is_valid"]:
     version_id = controller.save_model_version(new_data)
   else:
     controller.rollback_on_degradation(
       new_batch=new_data,
       previous_version=last_version
     )
```

**Persistencia:**

Modelos salvos em `models/vX.Y.Z.json` com estrutura:

```json
{
  "version_id": "v1.0.0",
  "timestamp": "2026-03-15T15:30:00",
  "model_state": { ... },
  "metrics": {
    "win_rate": 0.60,
    "f1_score": 0.62,
    ...
  },
  "training_samples": 100,
  "baseline_metrics": { ... },
  "description": "Primeiro modelo v1.0"
}
```

**Testes:** 18 testes unitarios, 18/18 PASSING (100%)

**Metricas de Codigo:**
- LOC: 442 linhas de codigo
- Classes: 4 (OnlineLearningController + 3 dataclasses)
- Metodos: 8 principais + utilitarios
- Type hints: 100%
- Docstrings:Cobertura completa
- mypy --strict: OK (sem erros)

**Integracoes:**
- AC6.7 (Drift Detector): Detecta quando chamar rollback
- QueueProcessor: Alimenta dados de trades para treino
- Dashboard ML: Exibe metricas e histórico

---

### AC6.9 Comparacao Baseline e Feedback ao Sistema

**Status:** ✅ IMPLEMENTADO (16/03/2026)

**Localizacao:** `src/application/ac6_9_baseline_comparator.py`

**Propósito:** Comparar metricas atuais do modelo contra
baseline historico e gerar feedback estruturado com
recomendacoes (CONTINUE/MONITOR/ROLLBACK).

**Classes:**
- `BaselineComparator`: Classe principal
- `BaselineRecord`: Registro de baseline historico
- `ComparisonResult`: Resultado da comparacao
- `SystemFeedback`: Feedback com recomendacao

**Testes:** 20 testes unitarios, 20/20 PASSING (100%)

---

### Grupo 2: Pipeline Feedback/Aprendizado nos Agentes

**Status:** ✅ INTEGRADO (17/03/2026) — ADR-015

**Pipeline:** AC5.8 → AC5.9 → AC6.7 → AC6.8 → AC6.9

```text
Ordem executada
  → AC5.8: registra posicao + monitora preco
  → AC5.9: valida feedback trade↔ML
  → AC6.7: detecta drift contra baseline
  → AC6.8: treino incremental (se drift)
  → AC6.9: compara vs baseline + recomendacao
```

**Integracao por agente:**

| Modulo | Micro Tend. | RL 5000 | Diarios |
|--------|-------------|---------|---------|
| AC5.8  | ✅          | ✅      | —       |
| AC5.9  | ✅          | —       | ✅      |
| AC6.7  | ✅          | —       | —       |
| AC6.8  | ✅          | —       | —       |
| AC6.9  | ✅          | —       | —       |

---

### P0: Isolamento de Posicoes entre Agentes RL

**Status:** ✅ IMPLEMENTADO (16/03/2026)

**Localizacao:** `src/application/posicao_isolamento.py`

**Problema Resolvido:** RL Direto detectava posicoes criadas pelo RL 5000,
causando conflitos e bloqueios de operacao. Necessário isolamento total.

**Classes Principais:**
- `PosicaoIsoladaManager`: Gerenciador de posicao com isolamento por session

**Funcionalidades Implemented:**

1. **Session ID Unico por Agente:**
   - RL 5000: `agente_5000_{TIMESTAMP}_v1`
   - RL Direto: `agente_direto_{TIMESTAMP}_v2`
   - Arquivo isolado: `outputs/agente_posicao_{session_id}.json`

2. **Validacao de Ownership:**
   - Cada posicao registra quem a criou (owner_version)
   - Impede leitura de posicao de outro agente
   - Log de erro se tentativa de violacao detectada

3. **Metadados Completos:**

   ```json
   {
     "session_id": "agente_direto_20260316_123354",
     "owner": "DIRETO_v2",
     "owner_version": "DIRETO_v2",
     "aberta": true,
     "preco_entrada": 182000.0,
     "open_time": "2026-03-16T12:34:02.059882",
     "ticket": 123456789,
     "lado": "BUY",
     "quantidade": 1,
     "timestamp": "2026-03-16T12:34:02.059882"
   }
   ```

4. **Operacoes Suportadas:**
   - `registrar_posicao_aberta()`: Registra abertura BY THIS AGENT
   - `registrar_posicao_fechada()`: Registra fechamento
   - `tem_posicao_aberta()`: Verifica se posicao aberta
   - `eh_dono_posicao()`: Valida ownership
   - `obter_metadados_posicao()`: Retorna dados (com validacao)
   - `obter_infos_resumidas()`: Info resumida + status isolamento
   - `validar_integridade()`: Audit trail

**Type Hints:** 100% (mypy --strict OK)

**Testes:** 7 testes unitarios, 7/7 PASSING (100%), cobertura >80%

**Metricas de Codigo:**
- LOC: 387 linhas de codigo
- Metodos: 8 principais
- Docstrings: Cobertura completa
- Type hints: 100%
- Logging: Detalhado para audit
- Encoding: UTF-8 (compativel com acentos)

**Integracoes:**
- RL 5000: Usar `agente_posicao_agente_5000_*.json`
- RL Direto: Usar `agente_posicao_agente_direto_*.json`
- Anti-overtrading: Valida ownership antes de protecoes
- Trade Tracker: Registra com agente_version para rastreamento

**Fluxo Tipico:**

```python
from src.application.posicao_isolamento import PosicaoIsoladaManager

# Inicializar (cada agente com seu session ID)
manager = PosicaoIsoladaManager(
    session_id="agente_direto_20260316_123354",
    agent_version="DIRETO_v2",
    outputs_dir=Path("outputs")
)

# Ao abrir posicao
manager.registrar_posicao_aberta(
    preco_entrada=182000.0,
    ticket=123456,
    lado="BUY",
    quantidade=1
)

# Verificar ja no ciclo
if manager.tem_posicao_aberta():
    if manager.eh_dono_posicao():
        # Pode operar, eh nosso agente
        metadados = manager.obter_metadados_posicao()
    else:
        # Posicao de outro agente, aguardar
        logger.warning("Posicao de outro agente - nao operando")

# Ao fechamento
manager.registrar_posicao_fechada()
```

**Garantias de Isolamento (3 Níveis):**

1. ✅ Magic Number (EA ID) único por agente no MT5
2. ✅ Filtragem de `positions_get()` por magic
3. ✅ RL Direto NAO consegue ler posicao do RL 5000
4. ✅ RL 5000 NAO consegue sobrescrever arquivo Direto
5. ✅ Arquivo JSON existe apenas para o agente criador
6. ✅ Validacao de ownership a cada leitura
7. ✅ `MotorDecisaoIsolado` por agent_id (17/03)
8. ✅ Log detalhado de violacoes (se tentadas)

> **Nota (17/03/2026):** O set inline
> `tickets_proprios` foi substituido por
> `MotorDecisaoIsolado` no RL 5000. A classe inline
> `AgentePosicaoStatus` foi removida do RL Direto e
> substituida por `PosicaoIsoladaManager` +
> `MotorDecisaoIsolado`. Codigo duplicado eliminado.

Ver secao completa:
[Isolamento por Magic Number](#isolamento-por-magic-number-ea-id)

---

### P0-NOVO: Motor de Decisao Isolado por Agent ID

**Status:** ✅ IMPLEMENTADO (16/03) | INTEGRADO (17/03)

**Localizacao:** `src/application/motor_decisao_isolado.py`

**Problema Resolvido:** Agentes paralelos compartilhavam
estado de decisao e posicao, causando bloqueios falsos
de 60s. Cada agente precisa motor proprio.

**Classes Principais:**

- `MotorDecisaoIsolado`: Motor completo por agent_id
- `PosicaoAberta`: Dataclass de posicao ativa
- `DecisaoRegistrada`: Dataclass de decisao tomada
- `HistoricoFechamento`: Dataclass de fechamento
- `DecisaoOperacional` (Enum, 6 valores)
- `TipoPosicao` (Enum, 2 valores)
- `MotivoFechamento` (Enum, 6 valores)

**Funcionalidades:**

1. **Persistencia por agent_id:**
   - `posicoes_ativas_{agent_id}.json`
   - `decisoes_{agent_id}.json`
   - `historico_fechamentos_{agent_id}.json`
2. **Max 1 posicao simultanea por agente**
3. **P&L com pontos_por_contrato=100 (WINFUT)**
4. **10+ metodos:** abrir, atualizar, fechar,
   registrar_decisao, obter_estatisticas

**Testes:** 24/24 + 7/7 = 31 PASSING

**Complemento:** Trabalha junto com
`posicao_isolamento.py` para fornecer
Grupo 1 — Isolamento entre Agentes.

**Integracao (17/03/2026):**

- RL 5000: `motor_isolado` substitui
  `tickets_proprios` (set inline volátil)
- RL Direto: `PosicaoIsoladaManager` +
  `MotorDecisaoIsolado` substituem classe
  inline `AgentePosicaoStatus` (removida)

---

### P2-RETRAIN_SCHEDULER Scheduler Inteligente de Retrain

**Status:** ✅ IMPLEMENTADO (16/03/2026)

**Localizacao:** `src/application/rl_retrain_scheduler.py`

**Propósito:** Detectar degradacao de modelo vs baseline e agendar
retrain em horario off-peak para manter qualidade operacional.

**Classes Principais:**

- `JobStatus`: Enum com ciclo de vida do job
  - SCHEDULED: Agendado, aguardando execucao
  - RUNNING: Em execucao neste momento
  - COMPLETED: Completado com sucesso
  - FAILED: Falhou durante execucao

- `DegradationDetectionMethod`: Enum com estrategias de deteccao
  - Z_SCORE: Desvio em sigmas da baseline
  - PERCENTUAL: Drop percentual vs baseline
  - THRESHOLD: Limite fixo aceitavel

- `RLSchedulerConfig`: Configuracao do scheduler
  - horario_inicio_offpeak: Inicio (ex: "18:30")
  - horario_fim_offpeak: Fim (ex: "23:00")
  - threshold_win_rate_drop: Queda maxima aceita (ex: 5.0%)
  - threshold_sharpe_min: Sharpe minimo exigido (ex: 0.8)
  - metodo_deteccao: Estrategia principal
  - intervalo_verificacao_minutos: Frequencia check (ex: 60 min)

- `TrainingJob`: Representacao de um job agendado
  - job_id: Identificador unico (uuid)
  - scheduled_at: ISO timestamp de agendamento
  - motivo_degradacao: Descricao da degradacao detectada
  - status: Estado atual do job
  - metodo_deteccao: Qual metodo o detectou
  - started_at / completed_at: Timestamps executivos (opcionais)

- `RLScheduler`: Orquestrador principal
  - detectar_degradacao(): Compara metricas atuais vs baseline
  - agendar_retrain(): Cria novo job
  - salvar_job() / obter_job(): Persistencia JSON
  - listar_jobs(): Recupera todos agendados
  - gerar_relatorio_json(): Export estruturado
  - gerar_relatorio_markdown(): Report legivel
  - contar_jobs_por_status(): Estatisticas

**Exemplo de Uso:**

```python
from src.application.rl_retrain_scheduler import (
    RLScheduler,
    DegradationDetectionMethod,
)

# Inicializar scheduler com baseline
scheduler = RLScheduler(
    config_path="data/scheduler",
    baseline_metrics={"win_rate": 65.0, "sharpe": 1.2}
)

# Detectar degradacao periodicamente (ex: a cada hora)
metricas_atuais = {
    "win_rate": 58.0,  # Drop de 65% -> 58% (7% de queda)
    "sharpe": 1.05,    # Ainda acima do minimo 0.8
}

degradacao, motivo = scheduler.detectar_degradacao(metricas_atuais)

if degradacao:
    # Agendar retrain
    job = scheduler.agendar_retrain(
        motivo_degradacao=motivo,
        metodo_deteccao=DegradationDetectionMethod.PERCENTUAL,
    )

    # Persistir
    scheduler.salvar_job(job)

    # Gerar relatorio
    print(scheduler.gerar_relatorio_markdown())

# Recuperar jobs agendados
jobs = scheduler.listar_jobs()
contagem = scheduler.contar_jobs_por_status()
# {'scheduled': 2, 'running': 0, 'completed': 1, 'failed': 0}
```

**Criterios de Degradacao:**

1. **Win Rate Drop:** baseline_wr - atual_wr > threshold
   - Exemplo: 65% - 58% = 7% > threshold 5% → DEGRADE

2. **Sharpe Minimo:** atual_sharpe < threshold_sharpe_min
   - Exemplo: Sharpe 0.7 < minimo 0.8 → DEGRADE

3. **Ambos Detectam:** Se ambos criterios sao acionados
   - Motivo: "win_rate drop de 65% para 58% | sharpe 0.7 abaixo minimo 0.8"

**Agendamento Off-Peak:**

- Default: 18:30 - 23:00 BRT
- Customizavel via RLSchedulerConfig
- Suporta multiplos windows (ex: 18:30-23:00, depois 23:00-06:00)
- Permite agendamento imediato (campo scheduled_at preserva timestamp real)

**Persistencia:**

- Arquivo: `{config_path}/scheduler_jobs.json`
- Formato: JSON array de jobs
- Atomicidade: Reescreve arquivo completo (simples, confiavel)
- Backup: Permite exportacao manual

**Testes:** 24 testes unitarios, 24/24 PASSING

**Metricas de Codigo:**
- LOC: 350 linhas de codigo
- Type hints: 100% (mypy --strict OK)
- Docstrings: Completo
- Cobertura: >= 85%

**Capacidades Implementadas:**
1. ✅ Deteccao multi-criterio (win_rate + sharpe)
2. ✅ 3 estrategias de deteccao (z_score, percentual, threshold)
3. ✅ Agendamento inteligente off-peak
4. ✅ Persistencia file-based (sem database externo)
5. ✅ ID unico por job (uuid)
6. ✅ Relatorios JSON + Markdown
7. ✅ Ciclo de vida completo (scheduled -> running -> completed/failed)
8. ✅ Contagem de jobs por status
9. ✅ 100% type hints compliance
10. ✅ 100% portugues

**Proximos Passos (Integracao):**

1. **Incorporar em Training Loop:**
   - Executar detectar_degradacao() apos cada sessao de treino
   - Agendar retrain se detectado
   - Registrar motivo no job para auditoria

2. **Ligar com BaselineComparator:**
   - Usar z_score do BaselineComparator para threshold dinamico
   - Atualizar baseline periodicamente (ex: a cada semana)

3. **Scheduler Cron/APScheduler:**
   - Executar job agendado em horario off-peak
   - Integrar com RL environment para retrain

---

## Resumo

Este documento descreve a arquitetura real executada pelo launcher
`INICIAR_MICRO_TENDENCIA_AUTO_TRADE.bat`.

O foco aqui nao e backlog, roadmap ou componentes historicos. O foco e o que
de fato acontece quando o operador inicia a sessao automatizada do agente de
micro-tendencia.

O launcher coordena uma sessao local de trading para WINFUT com:

- preparo operacional antes do mercado;
- controles de saude e protecao;
- sincronizacao entre MT5 e SQLite;
- inicializacao de integracoes locais;
- execucao do agente em modo simulado ou real;
- encerramento com rastreabilidade.

## Visao Executiva do Launcher

`INICIAR_MICRO_TENDENCIA_AUTO_TRADE.bat` e o orquestrador da sessao.
Ele nao e apenas um atalho para rodar Python. Ele define a ordem operacional da
abertura, aplica controles previos e so depois entrega a execucao ao agente.

Sequencia operacional observada no launcher:

1. valida se Python esta disponivel no ambiente;
2. apresenta cabecalho operacional e parametros da sessao;
3. permite ao operador escolher entre modo simulado ou auto-trade;
4. em modo real, exige confirmacao explicita antes de seguir;
5. executa verificacoes P50 para recuperar ou recalibrar confidence;
6. roda o pre-flight de saude do sistema;
7. sincroniza trades do MT5 para o SQLite local;
8. calcula datas de pregrao e aplica licoes BDI do dia;
9. tenta carregar o dataset de ML;
10. inicia servicos auxiliares em background, como journals e feedback logger;
11. consulta o status do Gate 2 para definir a escala de capital;
12. chama `scripts/launch_agent_with_ml_v1_2_3.py`;
13. ao encerrar o agente, sincroniza novamente as operacoes.

Em termos arquiteturais, o BAT funciona como a camada de orquestracao da
sessao e delega para scripts Python especializados cada responsabilidade.

## Arquitetura por Camadas em Uso Real

### 1. Orquestracao da Sessao

Responsavel por abrir, configurar e encerrar a sessao operacional.

Componentes centrais:

- `INICIAR_MICRO_TENDENCIA_AUTO_TRADE.bat`
- `scripts/launch_agent_with_ml_v1_2_3.py`

Responsabilidades:

- definir o modo de execucao;
- garantir confirmacao humana para ordens reais;
- preparar o ambiente antes do loop do agente;
- subir integracoes locais;
- repassar controle ao runtime principal.

### 2. Preparacao Operacional

Responsavel por validar se a sessao esta apta a operar antes de qualquer
decisao de trade.

Componentes usados pelo launcher:

- `scripts/system_health_monitor.py`
- `scripts/check_confidence_health.py`
- `scripts/reset_pessimism_mode.py`
- `scripts/daily_confidence_retraining.py`
- `scripts/sync_mt5_trades_to_db.py`
- `scripts/aplicar_licoes_bdi.py`
- `scripts/start_journals_full_display.py`
- `scripts/feedback_logger_realtime.py`
- `scripts/check_p0_2_status.py`

Responsabilidades:

- verificar saude operacional minima;
- corrigir estado de confidence pessimista;
- recalibrar confidence com base em resultado recente;
- reconciliar operacoes reais no banco local;
- aplicar contexto BDI antes do pregrao;
- iniciar observabilidade da sessao.

### 3. Runtime do Agente

Responsavel por analisar o mercado, gerar oportunidades, decidir entradas e
gerenciar posicoes.

Componente central:

- `scripts/agente_micro_tendencia_winfut.py`

Responsabilidades:

- carregar configuracao operacional;
- abrir sessao de trading no banco;
- manter loop ciclico durante o pregrao;
- conectar ao MT5;
- produzir analise macro e micro;
- persistir snapshots do ciclo;
- decidir se entra, simula ou rejeita a oportunidade;
- executar e acompanhar posicoes, quando permitido;
- enviar ordens reais via
  `ProcessadorBDI.enviar_ordem()`
  (MT5AdapterProxy + fallback MT5);
- registrar feedback de aprendizado.

### 4. Servicos de Apoio e Protecao

Responsavel por validar configuracao, protecao de terminal e saude minima.

Componentes centrais:

- `config/settings.py`
- `src.infrastructure.terminal_isolation_enforcer`
- `src.infrastructure.monitoring.health_checker`

Responsabilidades:

- ler `.env` e materializar configuracoes operacionais;
- garantir que o terminal MT5 permitido seja o da Clear;
- impedir envio de ordem se houver risco de terminal incorreto;
- registrar health checks e logs basicos de operacao.

### 5. Persistencia e Integracoes Locais

Responsavel por manter estado, historico e interfaces locais da sessao.

Componentes centrais:

- `data/db/trading.db`
- MetaTrader 5
- `scripts/start_api_server.py`
- `src/interfaces/api/fastapi_server.py`
- `src/application/orders_executor.py`
- `src/application/services/processador_bdi.py`

Responsabilidades:

- persistir sessoes, snapshots, trades e logs operacionais;
- sincronizar historico do MT5 com o banco local;
- expor uma API REST local para ordens e health check;
- permitir fallback entre API local e envio direto ao MT5.

### 6. Manutencao Operacional (Etapa 4)

Responsavel por garantir throughput minimo, perfil de memoria e limpeza segura
do banco de ordens.

Componentes centrais:

- `scripts/load_test_order_queue.py`
- `scripts/cleanup_old_orders_scheduler.py`
- `BAT/AGENDA_LIMPEZA_DIARIA.bat`

Responsabilidades:

- validar 100+ ordens/min com evidencia em `outputs/`;
- registrar perfil de memoria e CPU;
- remover ordens antigas com backup e verificacao de integridade;
- executar limpeza fora do pregao (agendada para 23:00).

### 7. Monitoramento de Execucao (AC5.8)

Responsavel por acompanhar ordens, posicoes e risco em tempo real durante a
sessao.

Componentes centrais:

- `src/infrastructure/execution_monitor.py`
- `src/infrastructure/position_monitor.py`
- `src/infrastructure/position_broadcaster.py`
- `src/application/websocket_server_ati1.py`

Responsabilidades:

- emitir eventos de transicao de ordens (ORDER_STATUS_UPDATE);
- atualizar posicoes abertas e PnL em tempo real;
- disparar alertas de risco (RISK_VIOLATION) via WebSocket ATI-1;
- manter um status de saude do monitor (MONITOR_STATUS).

### 8. Protecao de Lucros — ADR-018

**Status:** ✅ IMPLEMENTADO (02/04/2026)
**Referência:** `src/application/profit_protection_engine.py`

#### Propósito

Preservar ganhos de trades lucrativos mediante:
- **Break-even SL:** Move SL para entrada quando TP intermediário é atingido
- **Partial Close:** Reduz posição quando meta de lucro é alcançada
- **Protection Profile:** Configuração por instrumento/agente

#### Aplicações Atuais

| Agente | Launcher | Status Implementação |
|--------|----------|-------------|
| RL 5000 | `INICIAR_AGENTE_RL_5000.bat` | ✅ Ativo (MAGIC 234500) |
| RL Direto | `INICIAR_AGENTE_RL_DIRETO.bat` | ✅ Ativo (MAGIC 234600) v2 |
| Micro Tendência | `INICIAR_MICRO_TENDENCIA.bat` | ✅ Planejado para v3 |

#### Componentes

- **ProfitProtectionEngine:** Motor central, injetável por Pydantic
- **ProfitProtectionProfile:** Config estruturada (config/profit_protection.yaml)
- **Shadow Mode:** Logs sem executar MT5 (validação staging)
- **Magic Number Filter:** Cada agente processa apenas suas próprias ordens

#### Fluxo de Execução

1. **Inicialização:** `ProfitProtectionEngine` + `Profile` carregada
2. **Periodic Call:** Agente chama `processar_protecao(trade_dict, preco_atual)` a cada ciclo
3. **Validação:** Verifica if `magic == agente_magic && estado == "aberta"`
4. **Ação:** Se TP intermediário atingido → move SL para breakeven
5. **Persistência:** Cada ação registrada em SQLite + logs

#### Acceptance Criteria (AC-018)

```
AC-018.1: Função inicializado sem erros para ambos agentes
AC-018.2: Periodic calls em loop principal (cada 15-30s)
AC-018.3: Magic number filtering 100% funcional
AC-018.4: Exception handling não quebra o loop
AC-018.5: Profile compliance validado em staging
```

#### Validação de Produção

- **Staging:** Shadow mode LOG-ONLY (AC-V1 PASSAR)
- **Rollback:** Documentado em `docs/DEPLOYMENT_RUNBOOK.md`
- **Monitoring:** Métricas expostas via logs e SQLite
- **Gates:** Feature bloqueada até AC-018.1-5 e AC-V1 validarem

#### Referências

- Feature Spec: `notebooks/release_management_profit_protection_v2.ipynb`
- Tests: `tests/unit/test_rl_direto_profit_protection_integration.py`
- Deployment: `docs/DEPLOYMENT_RUNBOOK.md`

---

## Fluxo de Execucao Fim a Fim

### 1. Pre-abertura da sessao

O launcher valida a disponibilidade do Python e entra no diretorio do projeto.
Sem esse requisito, a sessao nao inicia.

Em seguida, o BAT exibe o contexto operacional da versao, dos gates e dos
parametros principais da sessao, como conta MT5, risco e limites operacionais.

### 2. Selecao do modo de execucao

O operador escolhe entre:

- `--simulate`: o sistema avalia oportunidades e registra sinais, mas nao envia
  ordens reais;
- `--auto-trade`: o sistema fica autorizado a enviar ordens reais ao MT5.

Quando o operador escolhe `--auto-trade`, o launcher exige uma confirmacao
explicita antes de continuar. Essa confirmacao e um controle humano de ultima
milha antes do modo real.

### 3. Controles de saude e protecao

Antes de o agente entrar em operacao, o launcher executa controles previos:

- verifica se o sistema entrou em estado de pessimismo de confidence;
- se necessario, reseta thresholds operacionais;
- aplica retraining diario de confidence;
- inicia o logger de feedback em background;
- executa o pre-flight com `HealthChecker`.

O `HealthChecker` valida tres pontos basicos:

- sincronismo de governanca documental via `BACKLOG.md`;
- heartbeat do ambiente MT5;
- latencia basica de acesso local.

Se o pre-flight falha, a sessao e bloqueada.

### 4. Sincronizacao de historico e contexto

Ainda antes do agente principal, o launcher roda servicos de contexto:

- sincroniza trades do MT5 para `data/db/trading.db`;
- calcula a data BDI e a data alvo do pregrao;
- aplica licoes BDI no contexto do dia;
- tenta carregar dataset de ML para uso posterior;
- inicia journals de apoio em background.

Esse conjunto deixa o agente com historico local, contexto diario e observacao
de sessao antes do primeiro ciclo de mercado.

### 5. Gate 2 e escala de capital

O launcher consulta `scripts/check_p0_2_status.py` e transforma o resultado em
uma variavel de escala de capital:

- aprovado: capital ampliado;
- reprovado ou indefinido: capital conservador;
- ainda em execucao: continua com capital conservador.

Essa decisao e tomada antes da chamada ao bootstrap Python do agente.

### 6. Bootstrap Python e integracoes

`scripts/launch_agent_with_ml_v1_2_3.py` prepara o runtime antes de delegar para
o agente principal.

Ele executa quatro blocos centrais:

- sobe `scripts/start_api_server.py` em subprocesso;
- inicializa o `TerminalIsolationEnforcer`;
- carrega e injeta dados de ML no ambiente do agente;
- tenta conectar o proxy da API P0-1 para interceptar `send_order`.

Esse bootstrap transforma o agente em uma sessao integrada, com protecao de
terminal, ML carregado e API local disponivel.

### 7. Runtime do agente

Depois do bootstrap, o controle vai para
`scripts/agente_micro_tendencia_winfut.py`.

No startup do runtime, o agente:

- carrega configuracao de `.env` via `config/settings.py`;
- cria ou valida tabelas do SQLite;
- abre uma sessao de trading;
- carrega diretivas do Head Financeiro;
- carrega feedback do diario;
- inicializa o IntraDayLearner;
- inicializa managers auxiliares de inactivity e forced activation;
- tenta inicializar o integrador LightGBM;
- executa pre-flight adicional do terminal MT5.

Depois disso, entra no loop principal.

### 8. Loop principal do agente

A cada ciclo, o runtime executa a seguinte sequencia:

1. valida continuamente o isolamento de terminal;
2. checa se esta dentro da janela de pregrao;
3. conecta ao MT5;
4. valida novamente o isolamento da conexao ativa;
5. inicializa ou atualiza o `MicroTradingManager`;
6. recarrega diretivas e feedback periodicamente;
7. roda `_run_cycle(mt5)` para produzir um `CycleResult`;
8. aplica ajustes de confidence por inatividade e aprendizado intradiario;
9. persiste snapshot do ciclo no SQLite;
10. exibe o resultado operacional do ciclo;
11. decide entre simular, executar ou rejeitar a oportunidade;
12. gerencia posicoes abertas quando ha modo real;
13. persiste episodios e recompensas RL quando disponivel;
14. desconecta do MT5;
15. espera o proximo ciclo.

### 9. Decisao de entrada

A decisao de entrada e centralizada no `MicroTradingManager`.

Ele aplica, entre outros, os seguintes guard rails:

- limite de posicoes simultaneas, hoje configurado em 1;
- limite diario de trades, hoje configurado em 6;
- perda diaria maxima, hoje configurada em 500 pontos;
- bloqueio de novas entradas nos ultimos 30 minutos do pregao, a partir de
  17:25;
- confianca minima, hoje configurada em 45%;
- risco/retorno minimo, hoje configurado em 1.5:1;
- cooling-off de 30 minutos apos stop loss na mesma direcao;
- restricoes de diretivas do Head Financeiro;
- proibicao de abrir posicao contra uma posicao ja aberta.

Definicao de SL/TP no runtime atual:

- **Alvos fixos em pontos**: stop e alvo calculados por distancia fixa em pontos
  a partir do preco de entrada.
  Referencias no codigo:
  - `scripts/agente_micro_tendencia_winfut.py:2006` (BUY: SL ATR, TP ATR fallback)
  - `scripts/agente_micro_tendencia_winfut.py:2170` (SELL: SL ATR, TP ATR fallback)
  - `scripts/agente_micro_tendencia_winfut.py:2316` (Trend follow BUY: SL/TP ATR)
  - `scripts/agente_micro_tendencia_winfut.py:2388` (Trend follow SELL: SL/TP ATR)
  - `scripts/agente_micro_tendencia_winfut.py:2008` (SL fixo do Head)
  - `scripts/agente_micro_tendencia_winfut.py:2172` (SL fixo do Head)
  - `scripts/agente_micro_tendencia_winfut.py:2318` (SL fixo do Head, trend BUY)
  - `scripts/agente_micro_tendencia_winfut.py:2390` (SL fixo do Head, trend SELL)
- **Alvos por topos e fundos anteriores**: stop e alvo calculados com base nos
  ultimos topos/fundos relevantes, usando esses niveis como referencia de
  protecao e objetivo.
  Referencias no codigo:
  - `scripts/agente_micro_tendencia_winfut.py:746` (deteccao de swing highs/lows)
  - `scripts/agente_micro_tendencia_winfut.py:1036` (topos/fundos com volume)
  - `scripts/agente_micro_tendencia_winfut.py:1276` (mapeamento de regioes)
  - `scripts/agente_micro_tendencia_winfut.py:1782` (supports/resistances)
  - `scripts/agente_micro_tendencia_winfut.py:2011` (BUY: TP por resistencia)
  - `scripts/agente_micro_tendencia_winfut.py:2175` (SELL: TP por suporte)
  - `scripts/agente_micro_tendencia_winfut.py:2322` (Trend follow BUY: TP por resistencia)
  - `scripts/agente_micro_tendencia_winfut.py:2393` (Trend follow SELL: TP por suporte)

Se a oportunidade for aprovada:

- no modo simulado, ela e apenas registrada;
- no modo real, `execute_entry()` tenta enviar a ordem.

### 10. Execucao e protecao de ordem

Antes de qualquer envio real, `execute_entry()` chama a validacao critica do
`TerminalIsolationEnforcer`.

Isso cria uma barreira final antes do envio de ordem:

- se o terminal Clear nao estiver rodando;
- se outro terminal perigoso estiver ativo;
- ou se houver violacao de isolamento,

a ordem nao segue.

No modo real, a ordem enviada passa a ser acompanhada pelo manager de trading,
que controla trailing, fechamento e resumo de sessao.

### 11. Encerramento

Quando o agente termina, o launcher ainda executa uma sincronizacao final de
trades do MT5 para o SQLite.

No runtime do agente, o encerramento tambem pode:

- fechar posicoes abertas;
- exportar audit log do aprendizado intradiario;
- encerrar a sessao de trading no banco.

O resultado e uma sessao rastreavel do inicio ao fim.

## Componentes Centrais e Responsabilidades

### `INICIAR_MICRO_TENDENCIA_AUTO_TRADE.bat`

Papel:

- orquestrar a sessao operacional;
- decidir ordem de execucao dos preparativos;
- fazer a ponte entre operador humano e runtime automatizado.

### `scripts/launch_agent_with_ml_v1_2_3.py`

Papel:

- inicializar integracoes antes do agente;
- subir a API local;
- preparar ML;
- ativar protecao de terminal;
- aplicar proxy de envio de ordem.

### `scripts/agente_micro_tendencia_winfut.py`

Papel:

- ser o motor principal de analise, decisao e execucao;
- manter o loop ciclico durante o pregrao;
- consolidar estado de sessao, oportunidade e posicao.

### `MicroTradingManager`

Papel:

- aplicar guard rails operacionais;
- decidir se uma oportunidade pode ser executada;
- enviar ordens quando permitido;
- acompanhar posicoes abertas e PnL da sessao.

### `TerminalIsolationEnforcer`

Papel:

- garantir que a automacao opere apenas no terminal MT5 permitido;
- bloquear startup, operacao critica ou execucao continua em caso de violacao.

### `HealthChecker`

Papel:

- funcionar como gate minimo de saude antes da sessao;
- registrar evidencias no SQLite sobre governanca, heartbeat e latencia.

### `scripts/sync_mt5_trades_to_db.py`

Papel:

- reconciliar operacoes reais do MT5 com `data/db/trading.db`;
- manter o historico local consistente antes e depois da sessao.

### `scripts/start_api_server.py` e FastAPI

Papel:

- expor uma camada local de API para ordens e health check;
- suportar a integracao P0-1 usada pelo bootstrap.

Interfaces publicas visiveis nessa camada:

- `GET /health`
- `GET /api/v1/orders`
- `GET /api/v1/stats/snapshot` — snapshot completo (dashboard)
- `GET /api/v1/stats/recentes` — ultimos N trades fechados
- `GET /api/v1/stats/periodo/{periodo}` — stats por periodo
- demais rotas sob `/api/v1/*`

Implementado em `src/interfaces/api/routes/dashboard.py`
via `StatsQueryService` (`src/application/dashboard_stats_server.py`).

## Configuracao e Contratos Relevantes

Para entendimento da arquitetura, os contratos mais importantes sao:

- executor principal: `INICIAR_MICRO_TENDENCIA_AUTO_TRADE.bat`;
- bootstrap Python: `scripts/launch_agent_with_ml_v1_2_3.py`;
- runtime do agente: `scripts/agente_micro_tendencia_winfut.py`;
- configuracao local: `.env` via `config/settings.py`;
- banco principal: `data/db/trading.db`;
- API local FastAPI:
  - `GET /health`
  - `GET /api/v1/orders`
  - `GET /api/v1/stats/snapshot`
  - `GET /api/v1/stats/recentes`
  - `GET /api/v1/stats/periodo/{periodo}`
  - demais rotas em `/api/v1/*`.

## Pontos de Arquitetura e Limitacoes Atuais

Algumas caracteristicas da arquitetura atual sao importantes
para leitura correta do sistema:

- o launcher concentra regras operacionais e mensagens de
  sessao no proprio BAT;
- ha forte dependencia de scripts Python acionados por linha
  de comando;
- o estado operacional depende de arquivos locais, SQLite,
  `.env` e do MT5 na mesma maquina;
- o bootstrap da API P0-1 local sobe um executor com mocks
  no startup, o que indica uma camada de integracao util para
  acoplamento local, mas nao um servico externo completo;
- o agente principal concentra muita logica em um unico
  script, misturando ciclo operacional, regras de decisao,
  exibicao e integracoes;
- existem componentes historicos e experimentais no
  repositorio, mas eles nao devem ser tratados como parte da
  arquitetura principal deste executor, a menos que sejam
  chamados diretamente por esse fluxo.

### Limitacoes Resolvidas (16/03/2026)

- **Interferencia entre agentes RL:** Resolvida com Magic
  Number (EA ID) por agente. Cada agente filtra posicoes
  exclusivamente pelo seu magic. (ADR-012)
- **Deteccao de SL/TP no Agente Direto:** Resolvida com
  verificacao por ticket no MT5 a cada 15s em vez de espera
  cega de 60s.

## Delimitacao deste Documento

Este documento assume como fonte principal de verdade:

- `INICIAR_MICRO_TENDENCIA_AUTO_TRADE.bat`;
- os scripts chamados direta ou indiretamente por ele;
- os modulos centrais usados durante a execucao dessa sessao.

Por isso, a arquitetura aqui descrita representa a operacao local observavel do
executor, mesmo quando isso diverge de backlog, roadmap ou documentacao antiga.

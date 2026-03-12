# BACKLOG

## Indice

- [Escopo de Execucao (4 Agentes)](#escopo-de-execucao-4-agentes)
- [Regras de uso](#regras-de-uso)
- [Backlog por agente](#backlog-por-agente)
- [Backlog — INICIAR_MICRO_TENDENCIA_AUTO_TRADE.bat](#backlog--iniciar_micro_tendencia_auto_tradebat)
- [Backlog — INICIAR_DIARIOS.bat](#backlog--iniciar_diariosbat)
- [Backlog — INICIAR_AGENTE_RL_5000.bat](#backlog--iniciar_agente_rl_5000bat)
- [Backlog — INICIAR_AGENTE_RL_5000_FIXED.bat](#backlog--iniciar_agente_rl_5000_fixedbat)


## Escopo de Execucao (4 Agentes)

O backlog existe para evoluir os seguintes executores:

- `INICIAR_DIARIOS.bat`
- `INICIAR_MICRO_TENDENCIA_AUTO_TRADE.bat`
- `INICIAR_AGENTE_RL_5000.bat`
- `INICIAR_AGENTE_RL_5000_FIXED.bat`

## Regras de uso

- A ordem abaixo e a ordem oficial de execucao.
- Somente itens ainda pendentes aparecem aqui.
- Cada item precisa resultar em codigo, testes e evidencia objetiva.
- Itens documentais ou de suporte so entram se destravarem entrega tecnica.
- Todo item precisa evoluir diretamente um dos quatro executores do escopo.

## Backlog por agente

Cada backlog abaixo contem apenas itens que evoluem diretamente o executor
respectivo. Itens comuns foram atribuídos ao agente principal impactado.

## Backlog — INICIAR_MICRO_TENDENCIA_AUTO_TRADE.bat

### P0 - Bloqueadores de entrega

#### 1. P0-2 Gate 2 Retest com dados e risco confiaveis

**Status:** DONE (GATE 2 PASS definitivo em 12/03/2026)

**Objetivo:** reexecutar a validacao de capital com base confiavel e criterio
reprodutivel.

**Motivo da prioridade:** desbloqueio de escala de capital concluido com
retorno auditavel (Gate 2 PASS).

**Entregar:**

- dataset/historico confiavel para reteste;
- execucao completa do backtest sem dados sinteticos como base principal;
- relatorio final de Gate 2 com decisao `PASS` ou `FAIL`;
- evidencia de drawdown e consistencia dentro do contrato.
- impacto explicito no executor (Gate 2 afeta capital).

**Pronto quando:**

- `scripts/check_p0_2_status.py` refletir a decisao final real;
- drawdown e consistencia estiverem medidos de forma auditavel;
- Gate 2 PASS registrado em 12/03/2026 (decisao final).

#### 2. AC5.7 Integracao real de envio de ordens MT5

**Status:** DONE (12/03/2026)

**Objetivo:** conectar o executor de trades ao envio real de ordens via MT5.

**Motivo da prioridade:** sem isso, a pipeline AC1-AC6 segue sem execucao real
fim a fim.

**Entregar:**

- integracao do `TradeExecutor` com `ProcessadorBDI.enviar_ordem()`;
- tratamento de falha, timeout e retorno de ordem;
- persistencia correta de `signal_id -> trade_id`;
- testes cobrindo sucesso, rejeicao e erro operacional.

**Pronto quando:**

- uma decisao `EXECUTE` gerar tentativa real de envio com rastreabilidade;
- a falha operacional nao quebrar a sessao;
- a execucao ficar auditavel no banco e nos logs.

#### 3. P1-CORE Etapa 4 de operacao

**Status:** DONE (12/03/2026)

**Objetivo:** concluir os bloqueios tecnicos restantes da trilha core.

**Entregar:**

- load testing `100+ ordens/min`;
- memory profiling;
- cleanup scheduler de ordens antigas;
- evidencia de throughput e manutencao segura do banco.

**Pronto quando:**

- throughput, memoria e CPU tiverem resultado registrado;
- limpeza automatizada estiver implementada e testada;
- nao houver dependencia manual para manutencao basica do runtime.

**Evidencias:**

- `outputs/load_test_results_*.json`
- `outputs/memory_profile_*.json`
- `outputs/cleanup_report_*.json`

### P1 - Entregas de execucao e aprendizado

#### 4. AC5.8 Monitoramento em tempo real de execucao

**Status:** DONE (12/03/2026)

**Objetivo:** acompanhar ordens abertas, transicoes e risco em runtime.

**Entregar:**

- trade manager/position monitor em tempo real;
- atualizacao de status de ordem e posicao;
- reacao a erro, parcial, cancelamento e encerramento.

**Evidencias:**

- `outputs/` (logs + eventos de monitor)

#### 5. AC5.9 Feedback de execucao para ML

**Objetivo:** fechar o ciclo entre ordem executada e dado de aprendizado.

**Entregar:**

- outcome de execucao convertido em sinal rotulado;
- persistencia pronta para reuso pelo loop ML;
- testes de correlacao entre trade e signal.

#### 6. AC6.7 a AC6.9 Evolucao do loop de ML

**Objetivo:** sair do feedback estatico para aprendizado operacional.

**Entregar:**

- treino real com XGBoost/LightGBM;
- online learning controlado;
- drift detection contra baseline.

### P2 - Capacidade futura

#### 7. Observabilidade e governanca tecnica

**Objetivo:** reduzir manutencao manual e risco documental.

**Entregar:**

- `validate_documentation.py`;
- `SYNC_MANIFEST.json`;
- health-checks de CI/CD;
- lint documental quando nao conflitar com artefatos historicos.

## Backlog — INICIAR_DIARIOS.bat

### P0 - Bloqueadores de entrega

#### 1. P0-2 Gate 2 Retest com dados e risco confiaveis

**Status:** DONE (GATE 2 PASS definitivo em 12/03/2026)

**Objetivo:** reexecutar a validacao de capital com base confiavel e criterio
reprodutivel.

**Motivo da prioridade:** desbloqueio de escala de capital concluido com
retorno auditavel (Gate 2 PASS).

**Entregar:**

- dataset/historico confiavel para reteste;
- execucao completa do backtest sem dados sinteticos como base principal;
- relatorio final de Gate 2 com decisao `PASS` ou `FAIL`;
- evidencia de drawdown e consistencia dentro do contrato.
- impacto explicito no executor (prepara dataset real).

**Pronto quando:**

- `scripts/run_p0_2_backtest.py` gerar artefatos finais validos;
- drawdown e consistencia estiverem medidos de forma auditavel;
- Gate 2 PASS registrado em 12/03/2026 (decisao final).

### P1 - Entregas de execucao e aprendizado

#### 2. AC5.9 Feedback de execucao para ML

**Objetivo:** fechar o ciclo entre ordem executada e dado de aprendizado.

**Entregar:**

- outcome de execucao convertido em sinal rotulado;
- persistencia pronta para reuso pelo loop ML;
- testes de correlacao entre trade e signal.

### P2 - Capacidade futura

#### 3. Observabilidade e governanca tecnica

**Objetivo:** reduzir manutencao manual e risco documental.

**Entregar:**

- `validate_documentation.py`;
- `SYNC_MANIFEST.json`;
- health-checks de CI/CD;
- lint documental quando nao conflitar com artefatos historicos.

## Backlog — INICIAR_AGENTE_RL_5000.bat

### P2 - Capacidade futura

#### 1. Trilha RL operacional

**Objetivo:** preparar a trilha de reinforcement learning sem competir com os
bloqueadores do core.

**Entregar:**

- ambiente Gym compativel;
- episode callback por trade;
- training loop;
- save/load versionado;
- scheduler de retrain;
- rollback de modelo ruim;
- metricas de recompensa e melhoria.

#### 2. Observabilidade e governanca tecnica

**Objetivo:** reduzir manutencao manual e risco documental.

**Entregar:**

- `validate_documentation.py`;
- `SYNC_MANIFEST.json`;
- health-checks de CI/CD;
- lint documental quando nao conflitar com artefatos historicos.

## Backlog — INICIAR_AGENTE_RL_5000_FIXED.bat

### P2 - Capacidade futura

#### 1. Trilha RL operacional

**Objetivo:** preparar a trilha de reinforcement learning sem competir com os
bloqueadores do core.

**Entregar:**

- ambiente Gym compativel;
- episode callback por trade;
- training loop;
- save/load versionado;
- scheduler de retrain;
- rollback de modelo ruim;
- metricas de recompensa e melhoria.

#### 2. Observabilidade e governanca tecnica

**Objetivo:** reduzir manutencao manual e risco documental.

**Entregar:**

- `validate_documentation.py`;
- `SYNC_MANIFEST.json`;
- health-checks de CI/CD;
- lint documental quando nao conflitar com artefatos historicos.

## Fora do backlog ativo

Itens historicos, checklists de ambiente, reunioes antigas, sprints fechadas e
entradas ja entregues nao devem voltar para este arquivo.

## Estado atual

- Gate 2: `PASS` (12/03/2026), capital escalavel.
- Pipeline P0-2: concluido.
- Proxima entrega recomendada: `AC5.8 Monitoramento em tempo real de execucao`.

# BACKLOG

## Indice

- [Escopo de Execucao (4 Agentes)](#escopo-de-execucao-4-agentes)
- [Regras de uso](#regras-de-uso)
- [P0 - Bloqueadores de entrega](#p0-bloqueadores-de-entrega)
- [P0 - Bloqueadores de entrega — 1. P0-2 Gate 2 Retest com dados e risco confiaveis](#1-p0-2-gate-2-retest-com-dados-e-risco-confiaveis)
- [P0 - Bloqueadores de entrega — 2. AC5.7 Integracao real de envio de ordens MT5](#2-ac57-integracao-real-de-envio-de-ordens-mt5)
- [P0 - Bloqueadores de entrega — 3. P1-CORE Etapa 4 de operacao](#3-p1-core-etapa-4-de-operacao)
- [P1 - Entregas de execucao e aprendizado](#p1-entregas-de-execucao-e-aprendizado)
- [P1 - Entregas de execucao e aprendizado — 4. AC5.8 Monitoramento em tempo real de execucao](#4-ac58-monitoramento-em-tempo-real-de-execucao)
- [P1 - Entregas de execucao e aprendizado — 5. AC5.9 Feedback de execucao para ML](#5-ac59-feedback-de-execucao-para-ml)
- [P1 - Entregas de execucao e aprendizado — 6. AC6.7 a AC6.9 Evolucao do loop de ML](#6-ac67-a-ac69-evolucao-do-loop-de-ml)


## Escopo de Execucao (4 Agentes)

O backlog existe para evoluir os seguintes executores:

- `INICIAR_DIARIOS.bat`
- `INICIAR_MICRO_TENDENCIA_AUTO_TRADE.bat`
- `BAT/INICIAR_AGENTE_RL_5000.bat`
- `BAT/INICIAR_AGENTE_RL_5000_FIXED.bat`

## Regras de uso

- A ordem abaixo e a ordem oficial de execucao.
- Somente itens ainda pendentes aparecem aqui.
- Cada item precisa resultar em codigo, testes e evidencia objetiva.
- Itens documentais ou de suporte so entram se destravarem entrega tecnica.
- Todo item precisa evoluir diretamente um dos quatro executores do escopo.

## P0 - Bloqueadores de entrega

### 1. P0-2 Gate 2 Retest com dados e risco confiaveis

**Objetivo:** reexecutar a validacao de capital com base confiavel e criterio
reprodutivel.

**Motivo da prioridade:** hoje o Gate 2 continua em `FAIL`, entao o projeto
segue preso em capital conservador.

**Entregar:**

- dataset/historico confiavel para reteste;
- execucao completa do backtest sem dados sinteticos como base principal;
- relatorio final de Gate 2 com decisao `PASS` ou `FAIL`;
- evidencia de drawdown e consistencia dentro do contrato.

**Pronto quando:**

- `scripts/run_p0_2_backtest.py` gerar artefatos finais validos;
- `scripts/check_p0_2_status.py` refletir a decisao final real;
- drawdown e consistencia estiverem medidos de forma auditavel.

### 2. AC5.7 Integracao real de envio de ordens MT5

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

### 3. P1-CORE Etapa 4 de operacao

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

## P1 - Entregas de execucao e aprendizado

### 4. AC5.8 Monitoramento em tempo real de execucao

**Objetivo:** acompanhar ordens abertas, transicoes e risco em runtime.

**Entregar:**

- trade manager/position monitor em tempo real;
- atualizacao de status de ordem e posicao;
- reacao a erro, parcial, cancelamento e encerramento.

### 5. AC5.9 Feedback de execucao para ML

**Objetivo:** fechar o ciclo entre ordem executada e dado de aprendizado.

**Entregar:**

- outcome de execucao convertido em sinal rotulado;
- persistencia pronta para reuso pelo loop ML;
- testes de correlacao entre trade e signal.

### 6. AC6.7 a AC6.9 Evolucao do loop de ML

**Objetivo:** sair do feedback estatico para aprendizado operacional.

**Entregar:**

- treino real com XGBoost/LightGBM;
- online learning controlado;
- drift detection contra baseline.

## P2 - Capacidade futura

### 7. Trilha RL operacional

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

### 8. Observabilidade e governanca tecnica

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

- Gate 2: `FAIL`, capital conservador.
- Pipeline P0-2: estabilizado tecnicamente.
- Proxima entrega recomendada: `P0-2 Gate 2 Retest com dados e risco confiaveis`.

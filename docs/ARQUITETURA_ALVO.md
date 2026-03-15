# Arquitetura Alvo

## Indice

- [Escopo de Execucao (4 Agentes)](#escopo-de-execucao-4-agentes)
- [Arquitetura Alvo e Contrato](#arquitetura-alvo-e-contrato)
- [Arquitetura Alvo e Contrato — Objetivo](#objetivo)
- [Arquitetura Alvo e Contrato — Fluxo Macro](#fluxo-macro)
- [Arquitetura Alvo e Contrato — Contrato Gate 2 (P0-2)](#contrato-gate-2-p0-2)
- [Arquitetura Alvo e Contrato — Invariantes de Compatibilidade](#invariantes-de-compatibilidade)
- [Arquitetura Alvo e Contrato — Diarios e Treinamento de Modelos](#diarios-e-treinamento-de-modelos)
- [Arquitetura Executada (Fluxo Real Atual)](#arquitetura-executada-fluxo-real-atual)
- [Resumo](#resumo)
- [Visao Executiva do Launcher](#visao-executiva-do-launcher)


## Escopo de Execucao (4 Agentes)

Todas as decisoes arquiteturais e evolucoes devem ter como alvo um destes quatro executores:

- `INICIAR_DIARIOS.bat`
- `INICIAR_MICRO_TENDENCIA_AUTO_TRADE.bat`
- `INICIAR_AGENTE_RL_5000.bat`
- `INICIAR_AGENTE_RL_5000_FIXED.bat`

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

## Arquitetura Executada (Fluxo Real Atual)

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
- enviar ordens reais via `ProcessadorBDI.enviar_ordem()` (MT5AdapterProxy + fallback MT5);
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
- rotas sob `/api/v1/*`

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
  - demais rotas em `/api/v1/*`.

## Pontos de Arquitetura e Limitacoes Atuais

Algumas caracteristicas da arquitetura atual sao importantes para leitura
correta do sistema:

- o launcher concentra regras operacionais e mensagens de sessao no proprio BAT;
- ha forte dependencia de scripts Python acionados por linha de comando;
- o estado operacional depende de arquivos locais, SQLite, `.env` e do MT5 na
  mesma maquina;
- o bootstrap da API P0-1 local sobe um executor com mocks no startup, o que
  indica uma camada de integracao util para acoplamento local, mas nao um
  servico externo completo;
- o agente principal concentra muita logica em um unico script, misturando
  ciclo operacional, regras de decisao, exibicao e integracoes;
- existem componentes historicos e experimentais no repositorio, mas eles nao
  devem ser tratados como parte da arquitetura principal deste executor, a menos
  que sejam chamados diretamente por esse fluxo.

## Delimitacao deste Documento

Este documento assume como fonte principal de verdade:

- `INICIAR_MICRO_TENDENCIA_AUTO_TRADE.bat`;
- os scripts chamados direta ou indiretamente por ele;
- os modulos centrais usados durante a execucao dessa sessao.

Por isso, a arquitetura aqui descrita representa a operacao local observavel do
executor, mesmo quando isso diverge de backlog, roadmap ou documentacao antiga.


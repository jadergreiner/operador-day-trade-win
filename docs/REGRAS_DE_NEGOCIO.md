# Regras de Negocio Canonicas

## Indice

- [Escopo de Execucao (4 Agentes)](#escopo-de-execucao-4-agentes)
- [Diarios e Treinamento de Modelos](#diarios-e-treinamento-de-modelos)
- [Regras Operacionais (Fluxo do Executor)](#regras-operacionais-fluxo-do-executor)
- [Resumo](#resumo)
- [Como a Sessao Comeca](#como-a-sessao-comeca)
- [Como a Sessao Comeca — O sistema so inicia se o ambiente minimo existir](#o-sistema-so-inicia-se-o-ambiente-minimo-existir)
- [Como a Sessao Comeca — O operador escolhe o modo de operacao](#o-operador-escolhe-o-modo-de-operacao)
- [Como a Sessao Comeca — Ordens reais exigem confirmacao explicita](#ordens-reais-exigem-confirmacao-explicita)
- [Como a Sessao Comeca — O sistema tenta entrar no dia em estado saudavel](#o-sistema-tenta-entrar-no-dia-em-estado-saudavel)
- [Quando o Sistema Pode Operar](#quando-o-sistema-pode-operar)


## Escopo de Execucao (4 Agentes)

As regras de negocio devem sempre evoluir um destes quatro executores:

- `INICIAR_DIARIOS.bat`
- `INICIAR_MICRO_TENDENCIA_AUTO_TRADE.bat`
- `INICIAR_AGENTE_RL_5000.bat`
- `INICIAR_AGENTE_RL_5000_FIXED.bat`

## Diarios e Treinamento de Modelos

Os diarios operacionais sao obrigatorios e devem alimentar o ciclo de ML/RL.
Sem diarios, o treinamento e a auditoria ficam incompletos.

Regras:

- diários devem ser gerados em toda sessao operacional;
- diários devem ser preservados para uso em treinamento;
- falha de geracao de diarios deve ser tratada como problema operacional.

## Regras Operacionais (Fluxo do Executor)

## Resumo

Este documento descreve, em linguagem de operacao, como o sistema decide quando
pode operar, quando deve bloquear, quando pode entrar em uma operacao e como
encerra a sessao.

O foco nao e a implementacao tecnica. O foco e a logica de negocio observada no
fluxo real do launcher `INICIAR_MICRO_TENDENCIA_AUTO_TRADE.bat` e do agente de
micro-tendencia que ele aciona.

## Como a Sessao Comeca

### O sistema so inicia se o ambiente minimo existir

Antes de qualquer analise, o launcher verifica se Python esta disponivel. Sem
isso, a sessao nao comeca.

### O operador escolhe o modo de operacao

O sistema sempre pede ao operador uma escolha:

- modo simulado, para observar sinais sem enviar ordens reais;
- modo auto-trade, para permitir ordens reais no MetaTrader 5.

### Ordens reais exigem confirmacao explicita

Se o operador escolher o modo real, o sistema ainda pede uma confirmacao final.
Sem essa confirmacao, a sessao e cancelada.

### O sistema tenta entrar no dia em estado saudavel

Antes de operar, o launcher roda verificacoes para detectar se a confidence do
sistema ficou excessivamente pessimista.

Se detectar esse problema, ele tenta:

- resetar o modo pessimista;
- recalibrar a confidence com base no desempenho recente;
- iniciar registro de feedback em background para acompanhar a sessao.

Em outras palavras, o sistema tenta comecar o dia menos travado e mais
alinhado ao desempenho real recente.

## Quando o Sistema Pode Operar

### O sistema so opera dentro da janela do pregao

O agente foi configurado para trabalhar durante a janela normal do pregao.
Hoje essa janela vai de 09:00 a 17:55. Fora desse horario, ele nao abre novas
operacoes e fica aguardando.

### O sistema para de abrir novas entradas nos minutos finais

Mesmo dentro do pregao, o sistema nao abre novas entradas nos ultimos
30 minutos da sessao. Na configuracao atual, isso significa nao abrir novas
entradas a partir de 17:25. A ideia e evitar iniciar operacoes quando sobra
pouco tempo para o mercado desenvolver.

### O sistema precisa passar no health check

Antes de entregar o controle ao agente, o launcher roda um health check.
Se esse teste falhar, a sessao e bloqueada.

Esse controle existe para impedir operacao em ambiente considerado instavel,
desalinhado ou mal sincronizado.

### O sistema precisa estar conectado ao terminal MT5 correto

O sistema nao aceita operar em qualquer terminal MetaTrader 5 encontrado na
maquina. Ele exige o terminal esperado para a sessao.

Se o terminal permitido nao estiver disponivel, a operacao nao segue.

### O envio real usa ProcessadorBDI com fallback MT5

Quando o modo auto-trade esta habilitado, o envio real segue este fluxo:

- `TradeExecutor` → `ProcessadorBDI.enviar_ordem()`
- `MT5AdapterProxy` (REST P0-1) com fallback automatico
- `MT5Adapter` direto (se API falhar ou ticket nao numerico)

Isso garante rastreabilidade, resiliencia e isolamento antes do envio real.

## Como o Sistema se Protege

### Ele bloqueia terminal MT5 de corretora errada

Se detectar terminal de corretora errada ou terminal nao autorizado, o sistema
bloqueia a operacao.

Esse bloqueio pode acontecer em tres momentos:

- no inicio da sessao;
- imediatamente antes de enviar uma ordem;
- durante a execucao continua do agente.

Se a violacao acontecer durante a execucao, o sistema pode interromper a
sessao para proteger a conta.

### Ele limita a quantidade de posicoes abertas

O sistema nao abre nova entrada se o limite de posicoes simultaneas ja tiver
sido atingido. Na configuracao atual, o limite operacional e 1 posicao.

Na pratica, ele evita empilhar operacoes acima do que foi definido como
aceitavel para a estrategia.

### Ele limita o numero de trades por dia

Existe um teto diario de trades. Quando esse teto e atingido, o sistema para de
abrir novas entradas naquele dia. Hoje esse teto esta configurado em 6 trades.

Esse limite existe para evitar excesso de operacoes e perda de disciplina.

### Ele para novas entradas se a perda diaria maxima for atingida

O sistema acompanha o resultado do dia. Se a perda acumulada atingir o limite
diario configurado, ele deixa de abrir novas operacoes. Hoje esse limite esta
configurado em 500 pontos de perda no dia.

Isso reduz o risco de insistencia em um dia ruim.

### Ele exige stop e alvo validos

No modo real, a ordem so pode ser enviada se houver protecao de perda e alvo de
ganho validos.

Se o sistema identificar stop invalido, alvo inconsistente ou especificacao
incompleta, a entrada e recusada.

Atualmente existem duas formas de calcular stop e alvo:

- **Alvos fixos em pontos**: o stop e o alvo sao definidos por uma distancia
  fixa em pontos a partir do preco de entrada.
  Referencias no codigo:
  - `scripts/agente_micro_tendencia_winfut.py:2006` (BUY: SL ATR, TP ATR fallback)
  - `scripts/agente_micro_tendencia_winfut.py:2170` (SELL: SL ATR, TP ATR fallback)
  - `scripts/agente_micro_tendencia_winfut.py:2316` (Trend follow BUY: SL/TP ATR)
  - `scripts/agente_micro_tendencia_winfut.py:2388` (Trend follow SELL: SL/TP ATR)
  - `scripts/agente_micro_tendencia_winfut.py:2008` (SL fixo do Head)
  - `scripts/agente_micro_tendencia_winfut.py:2172` (SL fixo do Head)
  - `scripts/agente_micro_tendencia_winfut.py:2318` (SL fixo do Head, trend BUY)
  - `scripts/agente_micro_tendencia_winfut.py:2390` (SL fixo do Head, trend SELL)
- **Alvos por topos e fundos anteriores**: o stop e o alvo sao definidos
  respeitando o ultimo topo ou fundo relevante do mercado, usando esses niveis
  como referencia de protecao e objetivo.
  Referencias no codigo:
  - `scripts/agente_micro_tendencia_winfut.py:746` (deteccao de swing highs/lows)
  - `scripts/agente_micro_tendencia_winfut.py:1036` (topos/fundos com volume)
  - `scripts/agente_micro_tendencia_winfut.py:1276` (mapeamento de regioes)
  - `scripts/agente_micro_tendencia_winfut.py:1782` (supports/resistances)
  - `scripts/agente_micro_tendencia_winfut.py:2011` (BUY: TP por resistencia)
  - `scripts/agente_micro_tendencia_winfut.py:2175` (SELL: TP por suporte)
  - `scripts/agente_micro_tendencia_winfut.py:2322` (Trend follow BUY: TP por resistencia)
  - `scripts/agente_micro_tendencia_winfut.py:2393` (Trend follow SELL: TP por suporte)

### Ele impede reentrada imediata apos stop loss na mesma direcao

Se uma operacao tiver sido encerrada em stop loss, o sistema entra em periodo
de espera antes de aceitar nova entrada na mesma direcao. Hoje essa espera esta
configurada em 30 minutos.

Essa regra existe para evitar reacao impulsiva e repeticao imediata do erro.

## Manutencao Operacional (Etapa 4)

### Retencao minima de ordens antigas

- o sistema deve manter, no minimo, 7 dias de historico de ordens (configuravel);
- a limpeza so remove ordens em status final (EXECUTED/FAILED).

### Backup obrigatorio antes de limpeza real

- toda limpeza real deve criar backup do SQLite antes de deletar;
- dry-run nao altera o banco, apenas informa o que seria removido.

### Limpeza fora do pregao

- a limpeza automatica deve rodar fora do pregao;
- janela padrao: 23:00 (ajustavel via scheduler).

### Load test obrigatorio antes de go-live

- toda mudanca de infraestrutura ou base de dados requer load test;
- criterio minimo: 100 ordens/min, p95 < 500ms, CPU < 80%, memoria < 50MB.

## Monitoramento em Tempo Real (AC5.8)

### Inicio automatico do monitor

- o monitor deve iniciar junto da sessao do executor;
- o monitor deve parar junto com o encerramento do agente.

### Transicoes de ordem obrigatorias

- toda transicao de ordem deve gerar evento em tempo real;
- eventos minimos: ENQUEUED, VALIDATED, SENT_TO_MT5, ACCEPTED, EXECUTED,
  PARTIALLY_CLOSED, CLOSED, REJECTED, CANCELLED.

### Alertas de risco

- drawdown <= -15% deve gerar RISK_VIOLATION imediato via WebSocket ATI-1.

### Modo degradado

- se o monitor nao estiver ativo, a sessao segue operando, mas registra alerta
  de degradacao (sem bloqueio automatico).

## Como o Sistema Decide Entrar

### Precisa existir uma oportunidade concreta

O sistema primeiro precisa identificar uma oportunidade com justificativa de
mercado. Sem oportunidade valida, nao existe entrada.

### A confianca minima precisa ser suficiente

Cada oportunidade passa por um nivel minimo de confidence. Se a confianca da
oportunidade estiver abaixo do minimo exigido, o sistema fica de fora. Hoje o
minimo operacional esta configurado em 45%.

### A relacao risco-retorno precisa ser aceitavel

Mesmo quando existe oportunidade, o sistema nao entra se a relacao entre risco
e retorno esperado for considerada fraca.

Ele busca evitar operacoes em que o potencial de ganho nao compense o risco.
Hoje o minimo operacional esta configurado em 1.5 para 1.

### O score tecnico pode ser reforcado ou enfraquecido pelo modelo ML

O sistema nao olha apenas para a leitura tecnica. Quando o modelo de ML esta
disponivel, ele mistura essa opiniao com a leitura tecnica.

Com isso, a confidence final pode:

- subir, se o ML reforcar a leitura;
- cair, se o ML discordar ou enfraquecer a oportunidade.

### Ajustes intradiarios podem subir ou baixar a confidence

Ao longo da sessao, o sistema tambem aplica ajustes por aprendizado intradiario
e por periodos longos sem entrada.

Esses ajustes tornam a regra de entrada mais rigida ou mais permissiva,
dependendo do comportamento recente observado.

### Diretivas do Head Financeiro podem endurecer os criterios

Se houver uma diretiva ativa do Head Financeiro, o sistema pode impor filtros
adicionais, como:

- aumentar exigencia de confianca;
- reduzir agressividade;
- limitar numero de trades;
- reforcar zonas ou condicoes a evitar.

Ou seja, uma oportunidade tecnicamente aceitavel ainda pode ser recusada se
desrespeitar a diretriz do dia.

### O sistema nao entra contra posicao ja aberta

Se ja existir uma posicao aberta em direcao oposta, o sistema nao abre nova
entrada contra essa exposicao.

Isso evita conflito interno entre ordens da propria estrategia.

## Diferenca Entre Simulado e Real

### No modo simulado, o sistema avalia tudo mas nao envia ordens

Em modo simulado, o agente:

- analisa o mercado;
- calcula oportunidades;
- aplica filtros e guard rails;
- registra o sinal para analise posterior.

Mas ele nao envia ordem real ao MetaTrader 5.

### No modo real, o sistema envia ordem e gerencia a posicao

Em auto-trade, quando a oportunidade passa por todos os filtros, o sistema:

- tenta enviar a ordem;
- registra a entrada;
- passa a acompanhar a posicao aberta;
- controla gestao, saida e encerramento.

## Como o Sistema Aprende e se Ajusta

### Ele sincroniza historico MT5 com o banco local

Antes de operar e ao encerrar a sessao, o sistema sincroniza as operacoes do
MetaTrader 5 com o banco local.

Isso ajuda a manter o historico consolidado e auditavel.

### Ele registra sinais, decisoes e resultados

Durante a sessao, o agente grava snapshots e eventos no banco local.
Assim, a operacao nao fica dependente apenas da memoria da sessao atual.

### Ele aplica licoes BDI do dia

Antes da abertura do agente, o launcher aplica as licoes BDI referentes ao dia.

Na pratica, o sistema entra no pregao com um contexto diario adicional ja
carregado.

### Ele recalibra confidence diariamente

O launcher roda um ajuste diario de confidence com base no desempenho recente.

Quando necessario, ele deixa o sistema:

- mais conservador, se o desempenho piorou;
- menos travado, se o historico recente justificar.

### Ele registra feedback durante a sessao

O sistema inicia um logger de feedback em background e tambem usa mecanismos de
aprendizado intradiario durante o runtime.

Isso permite observar:

- por que oportunidades foram rejeitadas;
- como a confidence esta se comportando;
- como o sistema pode se ajustar ao longo do dia.

## O que Acontece no Encerramento

### O sistema sincroniza novamente as operacoes

Ao final da sessao, o launcher faz uma sincronizacao final entre MT5 e banco
local.

### O sistema encerra a sessao com rastreabilidade

No encerramento, o runtime pode:

- fechar posicoes remanescentes;
- registrar o fim da sessao;
- exportar logs de auditoria do aprendizado intradiario.

Isso preserva rastreabilidade do inicio ao fim da operacao.

## Regras Operacionais que Devem Permanecer Visiveis

Para leitura rapida de negocio, estas regras merecem destaque permanente:

- o sistema so inicia se o ambiente basico estiver disponivel;
- ordens reais exigem confirmacao explicita do operador;
- a operacao so acontece dentro da janela do pregao;
- nao ha novas entradas nos ultimos 30 minutos;
- existe limite diario de trades;
- existe limite de perda diaria;
- a oportunidade precisa ter confidence minima;
- a oportunidade precisa ter risco/retorno minimo aceitavel;
- ordens reais so seguem com stop e alvo validos;
- terminal MT5 incorreto bloqueia a operacao;
- modo simulado registra, modo real executa;
- a sessao comeca e termina com sincronizacao e rastreabilidade.

## Relacao com a Arquitetura

Este documento deve ser lido junto com `ARQUITETURA_ALVO.md`.

Os dois documentos foram alinhados com a mesma premissa:

- a fonte principal de verdade e o fluxo real disparado por
  `INICIAR_MICRO_TENDENCIA_AUTO_TRADE.bat`;
- componentes nao chamados por esse fluxo nao definem a regra principal de
  operacao;
- quando houver conflito com documentacao historica, vale o comportamento atual
  observavel no executor.


---

## Regras de Risco do Runtime (inalteradas)

- Janela de pregao e respeitada.
- Sem novas entradas nos minutos finais.
- Limite de trades diarios e respeitado.
- Limite de perda diaria e respeitado.
- Ordem real exige stop e alvo validos.
- Confidence minima e risco-retorno minimo devem ser atendidos.

## Regra Gate 2 para Escala de Capital

Gate 2 e uma regra de **escala de capital**, nao de entrada de trade.

- PASS -> pode ampliar capital.
- FAIL -> mantem capital conservador.
- Em execucao -> mantem capital conservador.
- Indefinido/erro -> mantem capital conservador.

## Regra de Auditabilidade do Gate 2

- A decisao Gate 2 so e considerada final se o dataset for auditavel (nao sintetico).
- `data/backtest/dataset_audit.json` deve indicar `audit_passed=true`.
- Falha de auditoria ou dataset sintetico => decisao conservadora.

## Regra de PnL Realista

- PnL e drawdown do Gate 2 devem ser calculados com trades reais (1-bar hold) e custos aplicados.
- Custos incluem slippage e taxas por lado, conforme perfil de custo.

## Regra de Falha Segura

Qualquer falha de pipeline P0-2 deve resultar em postura conservadora
(sem ampliacao de capital).

## Rastreabilidade

- Inicio e fim da sessao devem manter sincronizacao com historico local.
- Decisao Gate 2 deve ficar persistida em artefatos locais de `data/backtest`.


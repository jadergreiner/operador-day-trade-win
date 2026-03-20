# ANALISE BDI OPERACIONAL - 20/03/2026

Fonte principal: `data/BDI/BDI_00_20260319.pdf`
Fonte complementar de calibracao intraday: `outputs/analysis/diario_market_features_latest.json`
Extracao textual de apoio: `data/BDI/bdi_20260319_key_data.txt`

Objetivo: transformar o fechamento de 19/03/2026 em contexto acionavel para o pregao de 20/03/2026 sem usar o BDI como bloqueio operacional.

## 1. O que o BDI mostrou no fechamento

Leitura objetiva da pagina 1 do boletim:

- Ibovespa fechou em `180.270,00`, com variacao de `+0,35%`.
- Derivativos com minis: `69.016.730` contratos.
- Derivativos sem minis: `43.189.768` contratos.
- Quantidade de negocios: `4.572.498`.
- Volume financeiro: `R$ 38.027,53 mi`.

Comparando com a media do mes no proprio BDI:

- minis `+3,60%` acima da media mensal;
- sem minis `+4,17%` acima da media mensal;
- negocios `+5,11%` acima da media mensal;
- volume financeiro `+3,10%` acima da media mensal.

### Interpretacao senior

O fechamento nao foi de mercado apatico. Foi um dia com:

- liquidez acima da media;
- participacao suficiente para continuidade intraday no dia seguinte;
- leitura mais confiavel para price discovery do que em sessoes de volume fraco.

Em outras palavras: o contexto de 20/03/2026 comeca com mercado negociando de verdade. Isso melhora a utilidade de features de fluxo, range e confirmacao entre ativos.

## 2. Como o fechamento de 19/03 terminou de fato

Calibracao pelo snapshot do Diario no encerramento:

- `IBOV`: abertura `179.624,0`, fechamento `180.271,0`, variacao `+0,36%`.
- `DOL`: abertura `5.256,0`, fechamento `5.240,5`, variacao `-0,29%`.
- `VALE3`: `+3,28%` vs abertura.
- `ENEV3`: `+4,07%` vs abertura.
- `ITUB4`: `+0,85%` no dia.
- `BBAS3`: `+0,46%` no dia.
- `PETR4`: `-1,17%` vs abertura.
- `PRIO3`: `-2,07%` vs abertura.
- `B3SA3`: `-1,57%` no dia.
- `PETR3`: `-0,05%` no dia.

### Interpretacao senior

O mercado fechou positivo, mas a lideranca foi seletiva:

- mineracao e nomes especificos de energia sustentaram melhor;
- bancos ajudaram no suporte;
- petroleo ficou para tras;
- B3SA3 terminou fraca, sinal de que a leitura nao foi de "risk-on limpo".

Isso tira forca da ideia de compra automatica e empurra o contexto para:

- `viés neutro para levemente comprador`;
- `confirmacao obrigatoria pelos pesos pesados`;
- `menos confianca em breakout cego`;
- `mais valor em trades que alinhem WIN + DOL + VALE3 + pelo menos um banco`.

## 3. Leitura operacional para o pregao de 20/03/2026

### Regime base

`ESTAVEL`, com `vies intraday neutro para levemente comprador`.

Motivos:

- fechamento positivo do IBOV;
- liquidez acima da media do mes;
- DOL cedeu no fechamento;
- mas PETR4 e PRIO3 terminaram fracas, o que impede leitura de compra ampla e limpa.

### O que favorece compra em WIN hoje

- `DOL` trabalhando abaixo do fechamento de ontem (`5.240,5`) ou sem retomar a pressao da abertura anterior (`5.256,0`);
- `VALE3` sustentando a forca de ontem;
- `ITUB4` e/ou `BBAS3` positivos, ajudando a espalhar a alta;
- `PETR4` pelo menos neutra, sem continuar puxando o indice para baixo;
- `WIN` acima da abertura e segurando pullbacks rasos.

### O que favorece venda em WIN hoje

- `DOL` retomando forca e recuperando a faixa de `5.256,0` para cima;
- `PETR4` permanecendo fraca e `VALE3` devolvendo parte relevante da alta;
- bancos falhando em confirmar a compra;
- `WIN` perdendo minima de abertura com repique fraco e curta duracao.

### O que evitar

- compra de rompimento quando so `VALE3` estiver positiva e o resto dos pesos pesados nao acompanhar;
- venda precoce contra `DOL` em queda e `IBOV` sustentado;
- projetar alvo longo demais em mercado misto sem confirmacao adicional.

## 4. Features soft recomendadas para os modelos

Use como features/contexto, nao como hard blocks:

- `bdi_ibov_close = 180270.0`
- `bdi_ibov_change_pct = 0.35`
- `bdi_minis_vs_month_pct = 3.60`
- `bdi_non_minis_vs_month_pct = 4.17`
- `bdi_trades_vs_month_pct = 5.11`
- `bdi_volume_vs_month_pct = 3.10`
- `session_ibov_delta_pct = 0.3602`
- `session_dol_delta_pct = -0.2949`
- `session_vale3_delta_pct = 3.2763`
- `session_petr4_delta_pct = -1.1653`
- `session_enev3_delta_pct = 4.0657`
- `session_prio3_delta_pct = -2.0741`
- `session_itub4_delta_pct = 0.85`
- `session_bbas3_delta_pct = 0.46`
- `session_b3sa3_delta_pct = -1.57`
- `leadership_state = MISTO_COM_VALE_E_BANCOS`
- `oil_beta_state = FRACO`
- `liquidity_regime = ACIMA_MEDIA`

## 5. Referencia para alvo e stop no WIN

O snapshot mais recente do Diario traz `ATR de referencia = 613,93 pts`.

Isso funciona bem como feature de calibracao:

- stop curto/tatico: `0,20 a 0,25 ATR` = `123 a 154 pts`
- stop padrao: `0,25 a 0,33 ATR` = `154 a 203 pts`
- alvo de scalp: `0,20 a 0,33 ATR` = `123 a 203 pts`
- alvo direcional: `0,50 a 0,80 ATR` = `307 a 491 pts`
- expansao cheia do dia: `1,00 ATR` = `614 pts`

### Como usar isso de forma util

- Se abrir com confirmacao de `DOL fraco + VALE3 forte + bancos positivos`, faz sentido permitir alvo entre `0,50` e `0,80 ATR`.
- Se abrir misto, prefira tratar `0,20` a `0,50 ATR` como zona mais realista de realizacao.
- Se `PETR4` continuar sendo arrasto do indice, use stops um pouco mais curtos e reduza a expectativa de follow-through.

## 6. Instrucao objetiva por agente

### Guardian / Coordenacao

- Subir o dia com `regime_macro = ESTAVEL`.
- Manter `bias inicial = NEUTRO_LEVEMENTE_COMPRADOR`.
- Tratar `DOL forte + PETR4 fraca + perda de minima` como gatilho de atencao, nao de bloqueio automatico.

### Microtendencia

- Dar peso maior para alinhamento entre `WIN`, `DOL`, `VALE3` e bancos.
- Evitar aumentar agressividade compradora se `PETR4` continuar negativa e o indice andar sustentado por poucos nomes.

### Momentum / Breakout

- Comprar rompimento so quando houver confirmacao minima de duas frentes:
  `VALE3` ou bancos junto com `DOL comportado`.
- Em rompimento vendedor, priorizar sinais onde `DOL` reacelera e `PETR4` nao reage.

### Risco

- Usar `ATR = 613,93` como ancora principal de sizing.
- Nao tratar o BDI como gate binario.
- Ajustar alvo e stop conforme a qualidade da confirmacao intermercado.

## 7. Watchlist de hoje

- `VALE3`
- `PETR4`
- `ITUB4`
- `BBAS3`
- `ENEV3`
- `PRIO3`
- `B3SA3`
- `DOL`

## 8. Resumo final acionavel

O BDI de 19/03/2026 deixa um mercado com liquidez boa e fechamento positivo, mas sem unanimidade entre os pesos pesados. O melhor enquadramento para 20/03/2026 e:

- abrir o dia com viés levemente comprador, nao euforico;
- usar `DOL`, `VALE3`, `PETR4` e bancos como validadores primarios;
- aceitar alvo maior so quando a confirmacao intermercado aparecer;
- usar o ATR como feature de calibracao de alvo/stop, nao como trava fixa;
- lembrar que o contexto e informacional: ele melhora a qualidade da decisao, mas nao deve bloquear operacoes por si so.

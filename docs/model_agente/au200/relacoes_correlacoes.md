# AU200 - Relações e Correlações

## Objetivo

Listar as principais relações que impactam o AU200, com explicação, forma de
monitoramento e atribuição de pontuação técnica para tomada de decisão e
treinamento de modelo.

---

## Mapa de Relações

### 1) Fluxo de Risco Global (US500, US30, DE30)

- **Porque importa:** O AU200 reage ao apetite por risco global e ciclo de
  lucros.
- **Como monitorar:** Correlação D1 e tendência intraday; observar gaps de
  abertura.
- **Regras de pontuação (snapshot):**
  - **US500:** +1 se cotação atual > abertura do dia (D1 open), -1 se <.
  - **US30:** +1 se cotação atual > abertura do dia (D1 open), -1 se <.
  - **DE30:** +1 se cotação atual > abertura do dia (D1 open), -1 se <.

### 2) China e Ciclo de Commodities (HK50, Metais)

- **Porque importa:** Austrália é grande exportadora de minério e metais para a
  China.
- **Como monitorar:** Proxies de China (HK50) e ativos de metais/energia
  (XAUUSD, XTIUSD).
- **Regras de pontuação (snapshot):**
  - **HK50:** +1 se cotação atual > abertura do dia (D1 open), -1 se <.
  - **XAUUSD:** +1 se cotação atual > abertura do dia (D1 open), -1 se <.
  - **XTIUSD:** +1 se cotação atual > abertura do dia (D1 open), -1 se <.

### 3) FX Australiano (Pares de AUD)

- **Porque importa:** O AUD reflete termos de troca e liquidez externa.
- **Como monitorar:** Divergência AUDUSD vs AU200 e reversões do AUDJPY.
- **Regras de pontuação (snapshot):**
  - **AUDCAD, AUDCHF, AUDJPY, AUDNZD, AUDUSD:** +1 se > D1 open, -1 se <.
  - **EURAUD, GBPAUD:** +1 se < D1 open, -1 se >.

### 4) Energia e Matérias-primas

- **Porque importa:** Alto peso de setores de energia e mineradoras no índice.
- **Como monitorar:** Correlação de retornos e volatilidade relativa.
- **Regras de pontuação (snapshot):**
  - **XTIUSD / XBRUSD:** +1 se > D1 open, -1 se <.
  - **XAUUSD:** +1 se > D1 open, -1 se <.

### 5) Volatilidade e Aversão ao Risco (VIX/USVIX)

- **Porque importa:** Aumento de volatilidade global pressiona índices
  negativamente.
- **Como monitorar:** Movimentos abruptos e relação inversa em janelas curtas.
- **Regras de pontuação (snapshot):**
  - **VIX/USVIX:** +1 se < D1 open (queda de vol), -1 se > (alta de vol).

### 6) Política Monetária (RBA vs Fed)

- **Porque importa:** Diferencial de juros altera fluxo para a bolsa local.
- **Regras de pontuação (snapshot):**
  - **UsDollar (DXY):** +1 se < D1 open, -1 se >.

### 7) Dados Macro Domésticos (AUD)

- **Porque importa:** Direciona expectativa de crescimento e juros locais.
- **Regras de pontuação (calendário econômico):**
  - **CPI:** +1 se abaixo do anterior, -1 se acima.
  - **EMP / GDP / RETAIL:** +1 se acima do anterior, -1 se abaixo.
  - **Risco Proativo:** -1 adicional se houver evento AUD High Impact nas
    próximas 24h.
  - **Regra de defasagem:** se não houver eventos na janela, usar o último
    evento disponível e marcar como defasado.

### 8) Setor Financeiro Local

- **Porque importa:** Bancos têm peso majoritário no AU200.
- **Regras de pontuação (snapshot):**
  - **AUS_BANKS:** +1 se > D1 open, -1 se <.
  - **AU10Y:** +1 se < D1 open (juros em queda), -1 se >.

### 9) Smart Money Concepts - Estrutura e Zonas (H4)

- **Porque importa:** Identifica o posicionamento institucional e o fluxo de
  ordens.
- **Como monitorar:** Mapeamento de BOS, CHoCH e FVG no H4.
- **Regras de pontuação (SMC Context):**
  - **Direção do Fluxo:** +1 se BOS de alta recente, -1 se BOS de baixa recente.
  - **Zonas de Negociação (Equilibrium):**
    - **DISCOUNT:** +3 se preço em zona de desconto + confirmação em POI.
    - **PREMIUM:** -3 se preço em zona premium + confirmação em POI.
  - **Liquidez/Imbalance:** +1 se FVG abaixo (suporte), -1 se FVG acima
    (resistência).

- **Implementação técnica (H4/MT5):**
  - **Fonte:** candles H4 do AU200 via MT5.
  - **Persistência:** cotações H4 gravadas no SQLite (timeframe `H4`).
  - **Detecção BOS/CHoCH:** último close rompendo swing high/low recente.
  - **Equilibrium:** comparação com o meio do range H4 (lookback).
  - **POI:** zona de interesse do SMC a até 2% do preço.

### 10) Indicadores de Exaustão e Momentum (D1/H4)

- **Porque importa:** Sinaliza exaustão de movimento e preço esticado.
- **Regras de pontuação (snapshot):**
  - **RSI & Stochastic:** +1 se ambos em sobrevenda (RSI < 30 / Stoch < 20),
    -1 se ambos em sobrecompra.
  - **Bollinger Bands:** +1 se abaixo da banda inferior, -1 se acima da
    superior.
  - **ADX (14):** +1 se ADX > 40 e caindo (perda de força da tendência).
  - **OBV:** +1 se divergência de alta (preço cai, OBV sobe), -1 se divergência
    de baixa.
  - **Afastamento Média (SMA 20):** +1 se preço > 2% abaixo da média, -1 se >
    2% acima.

  - **Implementação técnica (D1/H4):**
    - **Fonte:** candles D1/H4 do AU200 via MT5.
    - **Persistência:** cotações D1/H4 gravadas no SQLite.
    - **RSI/Stoch:** RSI(14) e Stoch(14) no último candle.
    - **Bollinger:** bandas 20 períodos e 2 desvios.
    - **ADX:** ADX(14) > 40 e último valor menor que o anterior.
    - **OBV:** divergência por variação do OBV vs preço (janela 20).
    - **SMA 20:** distância percentual vs SMA(20).

---

## Instruções de Saída e Persistência

### 1. Checklist Individual

A IA deve listar individualmente cada item acima, informando o valor apurado e
 a justificativa técnica fundamentada nos dados fornecidos.

### 2. Veredito Final

Calcular o Score Total somando todos os pontos.

### 3. Persistência SQLite

Gerar obrigatoriamente o código SQL para armazenamento dos dados.

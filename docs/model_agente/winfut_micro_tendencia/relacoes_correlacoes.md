# WINFUT Micro Tendências - Relações e Correlações

## Objetivo

Listar as principais relações que impactam o WINFUT para captura de micro
tendências intraday, com explicação, forma de monitoramento e atribuição de
pontuação técnica para tomada de decisão.

O foco é identificar:
1. **Direcional do dia** — via sistema de pontuação agregada
2. **Regiões de interesse** — zonas de liquidez, suportes, resistências e POIs
3. **Micro tendências** — movimentos de curta duração para surfar ou reverter

---

## Sistema de Pontuação — Direcional do Dia

### Score Total

- **COMPRA** (viés alta): Score >= +4
- **VENDA** (viés baixa): Score <= -4
- **NEUTRO** (sem direcional claro): Score entre -3 e +3

### Confiança

- **Alta**: >= 70% dos itens disponíveis convergem
- **Média**: 50-69% convergem
- **Baixa**: < 50% convergem

---

## Mapa de Relações — Contexto Macro para Micro Tendências

### 1) Índices Globais — Contexto de Risco

- **Porque importa:** O WINFUT segue o apetite por risco global, especialmente
  antes da abertura e nos primeiros 30 minutos. Gaps de abertura frequentemente
  refletem o fechamento do S&P 500 e a sessão europeia.
- **Como monitorar:** Cotação atual vs abertura do dia (D1 open).
- **Regras de pontuação (snapshot):**
  - **ES/WSP (S&P 500 Futuro):** +1 se cotação atual > abertura do dia, -1 se <.
  - **NQ/NASD (Nasdaq Futuro):** +1 se > abertura, -1 se <.
  - **DAX/DE30 (Europa):** +1 se > abertura, -1 se <.

### 2) Dólar / Câmbio — Correlação Inversa Principal

- **Porque importa:** O dólar é o principal driver inverso do WINFUT. Dólar
  subindo = IBOV caindo e vice-versa. Monitorar WDO e DOL é essencial.
- **Como monitorar:** Preço atual vs abertura + tendência intraday.
- **Regras de pontuação (snapshot):**
  - **WDO$N (Mini Dólar):** +1 se < abertura (dólar caindo = bom para bolsa), -1 se >.
  - **DOL$N (Dólar Cheio):** +1 se < abertura, -1 se >.
  - **USDBRL:** +1 se < abertura, -1 se >.

### 3) Juros Futuros — DI e Treasuries

- **Porque importa:** Juros futuros em queda são bullish para bolsa (fluxo para
  renda variável). DI subindo pressiona negativamente.
- **Como monitorar:** Taxa vs abertura do dia.
- **Regras de pontuação (snapshot):**
  - **DI1$N (DI Futuro):** +1 se < abertura (juros caindo), -1 se >.
  - **US10Y (T-Note 10Y):** +1 se < abertura, -1 se >.

### 4) Commodities — Petróleo e Minério

- **Porque importa:** PETR4 e VALE3 juntos representam ~25% do IBOV. Petróleo e
  minério de ferro movem essas ações e, por consequência, o índice.
- **Como monitorar:** Preço atual vs abertura.
- **Regras de pontuação (snapshot):**
  - **XTIUSD (WTI Petróleo):** +1 se > abertura, -1 se <.
  - **XBRUSD (Brent Petróleo):** +1 se > abertura, -1 se <.
  - **VALE3 (proxy minério):** +1 se > abertura, -1 se <.

### 5) Blue Chips Brasileiras — Peso no Índice

- **Porque importa:** PETR4, VALE3, ITUB4, BBDC4 e BBAS3 juntos representam
  ~40% do IBOV. Seus movimentos arrastam o índice.
- **Como monitorar:** Cotação atual vs abertura; tendência intraday.
- **Regras de pontuação (snapshot):**
  - **PETR4:** +1 se > abertura, -1 se <.
  - **ITUB4:** +1 se > abertura, -1 se <.
  - **BBDC4:** +1 se > abertura, -1 se <.
  - **BBAS3:** +1 se > abertura, -1 se <.

### 6) ETFs e Índices de Referência

- **Porque importa:** ETFs capturam o fluxo agregado. BOVA11 replica o IBOV
  e SMLL sinaliza risco de small caps.
- **Como monitorar:** Preço vs abertura.
- **Regras de pontuação (snapshot):**
  - **BOVA11:** +1 se > abertura, -1 se <.
  - **IVVB11 (S&P 500 em BRL):** +1 se > abertura, -1 se <.

### 7) Volatilidade e Aversão ao Risco

- **Porque importa:** Alta volatilidade = incerteza = pressão vendedora.
  VIX alto sinaliza cautela.
- **Como monitorar:** VIX atual vs abertura do dia.
- **Regras de pontuação (snapshot):**
  - **VIX/USVIX:** +1 se < abertura (queda de vol), -1 se > (alta de vol).

### 8) Criptomoedas — Proxy de Apetite por Risco

- **Porque importa:** Bitcoin forte indica apetite por risco global.
- **Regras de pontuação (snapshot):**
  - **BTCUSD:** +1 se > abertura, -1 se <.

---

## Mapa de Relações — Micro Tendências Intraday (Timeframe M5/M15)

### 9) Smart Money Concepts — Estrutura e Zonas (M15/H1)

- **Porque importa:** Identifica o posicionamento institucional e o fluxo de
  ordens no intraday. BOS (Break of Structure) e CHoCH (Change of Character)
  marcam transições de micro tendência.
- **Como monitorar:** Mapeamento de BOS, CHoCH e FVG no M15 e H1.
- **Regras de pontuação (SMC Context):**
  - **Direção do Fluxo:** +2 se BOS de alta recente, -2 se BOS de baixa recente.
  - **Zonas de Negociação (Equilibrium):**
    - **DISCOUNT:** +3 se preço em zona de desconto + confirmação em POI.
    - **PREMIUM:** -3 se preço em zona premium + confirmação em POI.
  - **Liquidez/Imbalance:** +1 se FVG abaixo (suporte), -1 se FVG acima
    (resistência).

- **Implementação técnica (M15/H1 via MT5):**
  - **Fonte:** candles M15 e H1 do WIN$N via MT5.
  - **Persistência:** cotações M15/H1 gravadas no SQLite.
  - **Detecção BOS/CHoCH:** último close rompendo swing high/low recente.
  - **Equilibrium:** comparação com o meio do range (lookback).
  - **POI:** zona de interesse do SMC a até 0.5% do preço (~300-400 pontos WIN).

### 10) VWAP e Desvios — Regiões de Interesse Intraday

- **Porque importa:** VWAP é a referência principal de preço justo intraday.
  Desvios de +1σ e +2σ marcam zonas de sobrecompra; -1σ e -2σ de sobrevenda.
- **Como monitorar:** Posição do preço relativa ao VWAP e seus desvios.
- **Regras de pontuação (snapshot):**
  - **Preço > VWAP+2σ:** -2 (sobrecompra extrema, potencial reversão).
  - **Preço > VWAP+1σ:** -1 (esticado para cima).
  - **Preço entre VWAP-1σ e VWAP+1σ:** 0 (zona neutra / fair value).
  - **Preço < VWAP-1σ:** +1 (desconto, potencial compra).
  - **Preço < VWAP-2σ:** +2 (sobrevenda extrema, potencial reversão alta).

### 11) Volume e Agressão — Fluxo de Ordens

- **Porque importa:** Volume confirma movimentos. Volume crescente na direção
  valida a tendência; volume decrescente indica exaustão.
- **Regras de pontuação (snapshot):**
  - **Volume atual > 1.5× média 20 períodos:** +1 se preço subindo, -1 se caindo.
  - **Volume < 0.5× média:** sinaliza indecisão (0 pontos).
  - **OBV divergência:** +1 se preço cai mas OBV sobe, -1 se preço sobe mas OBV cai.

### 12) Indicadores de Exaustão e Momentum (M5/M15)

- **Porque importa:** Sinaliza exaustão de micro tendência e preço esticado
  dentro do intraday.
- **Regras de pontuação (snapshot):**
  - **RSI(14) M5:** +1 se < 30 (sobrevenda), -1 se > 70 (sobrecompra).
  - **Stochastic(14) M5:** +1 se < 20, -1 se > 80.
  - **MACD M5:** +1 se cruzamento alta, -1 se cruzamento baixa.
  - **Bollinger Bands M5:** +1 se abaixo da banda inferior, -1 se acima da
    superior.
  - **ADX(14) M15:** +1 se ADX > 25 (tendência forte presente), -1 se < 15
    (mercado lateral, evitar).
  - **Afastamento EMA9 M5:** +1 se preço > 0.3% abaixo, -1 se > 0.3% acima.

### 13) Suportes, Resistências e Pivôs

- **Porque importa:** Regiões clássicas de reversão e continuação. Pivôs
  diários são referência para operadores institucionais.
- **Regras de pontuação (snapshot):**
  - **Próximo a suporte forte (S1/S2):** +1 (região de compra potencial).
  - **Próximo a resistência forte (R1/R2):** -1 (região de venda potencial).
  - **Pivô central (PP):** 0 (referência neutra).
  - **Rompimento com volume:** +2 se rompe R1 para cima, -2 se rompe S1 para
    baixo.

### 14) Candle Patterns — Padrões de Reversão (M5/M15)

- **Porque importa:** Padrões de candle em regiões de interesse (suporte,
  resistência, VWAP) confirmam reversões.
- **Regras de pontuação (snapshot):**
  - **Engolfo de alta em suporte:** +2.
  - **Engolfo de baixa em resistência:** -2.
  - **Doji/Martelo em zona de interesse:** +1/-1 conforme contexto.
  - **Pin bar (rejeição):** +1 se rejeição de mínima, -1 se rejeição de máxima.

---

## Score Zones — Leitura para Operação

| Score Total     | Leitura               | Ação Recomendada                                     |
|-----------------|-----------------------|------------------------------------------------------|
| >= +10          | Forte Alta            | Surfar tendência compradora; buscar pullbacks M5     |
| +4 a +9         | Alta Moderada         | Viés comprador; entradas em desconto/VWAP-           |
| -3 a +3         | Neutro / Lateralizado | Scalp em extremos; evitar posições grandes           |
| -4 a -9         | Baixa Moderada        | Viés vendedor; entradas em premium/VWAP+             |
| <= -10          | Forte Baixa           | Surfar tendência vendedora; buscar reversões em VWAP |

---

## Regiões de Interesse e Liquidez

### Zonas Chave para Micro Tendências

1. **VWAP + Desvios:** Principal referência intraday. Operações a favor da
   tendência no desvio +/-1σ. Reversões no desvio +/-2σ.

2. **Suporte/Resistência D1:** Regiões onde o preço reagiu em dias anteriores.
   Confluência com VWAP = zona de alta probabilidade.

3. **POI (Points of Interest) SMC:** Zonas de Order Block, FVG e liquidez
   mapeadas em M15/H1. Forte confluência quando alinhadas ao direcional.

4. **Pivôs Diários:** PP, S1, S2, R1, R2 calculados da sessão anterior.
   Amplamente monitorados por algoritmos e institucionais.

5. **Máxima/Mínima do dia anterior:** Rompimento com volume = continuação.
   Falso rompimento = reversão.

6. **Abertura do dia (9h):** Preço de abertura como referência. Acima = viés
   comprador. Abaixo = viés vendedor.

---

## Instruções de Saída e Persistência

### 1. Checklist Individual

Listar individualmente cada item, informando o valor apurado e a justificativa
técnica.

### 2. Veredito Final — Direcional do Dia

Calcular o Score Total somando todos os pontos das relações 1-8 (contexto macro)
e apresentar as regiões de interesse das relações 9-14 (micro tendências).

### 3. Micro Tendências Ativas

Classificar a micro tendência atual:
- **CONTINUAÇÃO:** Score macro + indicadores M5 alinhados
- **REVERSÃO:** Score macro diverge dos indicadores M5
- **CONSOLIDAÇÃO:** Indicadores M5 sem direcional (ADX < 15)

### 4. Regiões de Entrada

Para cada direção (COMPRA/VENDA), informar:
- Preço de entrada sugerido
- Stop Loss (baseado em ATR ou POI)
- Take Profit (próxima região de interesse)
- R/R esperado

### 5. Persistência SQLite

Gerar obrigatoriamente os dados para armazenamento na tabela
`micro_trend_decisions` e `micro_trend_items`.

# WDO (Dolar Futuro) e WINFUT (Indice Futuro) — Relacoes e Correlacoes

## Objetivo

Listar as principais relacoes que impactam o USDBRL (WDO — Dolar Futuro) e
o WINFUT (Indice Futuro Ibovespa), com explicacao, forma de monitoramento e
atribuicao de pontuacao tecnica para tomada de decisao e treinamento de modelo.

O agente produz **duas pontuacoes distintas e independentes:**

- **Score WDO (Dolar):** Direcao do USDBRL. Score positivo = BRL fraco (dolar sobe).
  Score negativo = BRL forte (dolar cai).
- **Score WINFUT (Indice):** Direcao do Ibovespa Futuro. Score positivo = Ibovespa sobe.
  Score negativo = Ibovespa cai.

> **Correlacao inversa:** WDO e WINFUT possuem correlacao historica
> fortemente negativa (-0.75 a -0.90). Quando o dolar sobe, o Ibovespa
> tende a cair, e vice-versa. Porem, em momentos de estresse extremo ou
> euforia global, ambos podem se mover na mesma direcao temporariamente.

---

## Mapa de Relacoes

### 1) Commodities — Exportacoes Brasileiras (Peso: Alto)

- **Porque importa:** O Brasil e exportador liquido de minerio de ferro,
  soja, petroleo, cafe, acucar, milho e celulose. Precos de commodities
  em alta geram entrada de dolares no Brasil (superavit comercial),
  fortalecendo o BRL e impulsionando acoes de commodities no Ibovespa
  (Vale, Petrobras representam ~25% do indice).

#### Regras de Pontuacao — Cap. 1 Commodities

| # | Simbolo | Tipo | Regra | Score WDO | Score WINFUT |
| --- | --- | --- | --- | --- | --- |
| 1.1 | `XAUUSD` (Ouro) | `snapshot_pares` | +1 se last > D1 open, -1 se < | ±1 (inv) | ±1 |
| 1.2 | `XTIUSD` (Petroleo WTI) | `snapshot_pares` | +1 se last > D1 open, -1 se < | ±1 (inv) | ±1 |
| 1.3 | `SOYBEAN` (Soja) | `snapshot_pares` | +1 se last > D1 open, -1 se < | ±1 (inv) | ±1 |
| 1.4 | `IRON_ORE` (Minerio Ferro) | `tendencia_h4` | close > SMA(20) H4 = +1, < = -1 | ±1 (inv) | ±1 |
| 1.5 | `COFFEE` (Cafe) | `snapshot_pares` | +1 se last > D1 open, -1 se < | ±1 (inv) | ±1 |

> **WDO:** Commodities em alta = BRL forte = dolar cai = score WDO **invertido** (commodity sobe → WDO score -1).
> **WINFUT:** Commodities em alta = Vale/Petrobras sobem = Ibovespa sobe = score WINFUT **direto** (+1).

#### Coleta Multi-Source (MT5 → Yahoo → FRED)

| Simbolo | MT5 (primario) | Yahoo Finance (fb 1) | FRED (fb 2) |
| --- | --- | --- | --- |
| `XAUUSD` | XAUUSD, GOLD | `GC=F` | — |
| `XTIUSD` | XTIUSD, WTICOUSD, USOIL | `CL=F` | — |
| `SOYBEAN` | SOYBEAN, ZS, SOYB | `ZS=F`, `SOYB` | — |
| `IRON_ORE` | IRON, IRONORE, XFEUSD | `BHP`, `RIO`, `VALE` (proxy) | `PIORECRUSDM` (mensal) |
| `COFFEE` | COFFEE, KC, XCOFFEE | `KC=F` | — |

**Score maximo capitulo 1:** ±5 pontos (WDO invertido) / ±5 pontos (WINFUT direto)

---

### 2) Fluxo de Risco Global — Risk-On / Risk-Off (Peso: Muito Alto)

- **Porque importa:** O Brasil e mercado emergente. Em risk-on, capital
  flui para emergentes (BRL forte, Ibovespa sobe). Em risk-off, capital
  foge para ativos seguros (USD, Treasuries), BRL enfraquece e Ibovespa cai.

#### Regras de Pontuacao — Cap. 2 Risco Global

| # | Simbolo | Tipo | Regra | Score WDO | Score WINFUT |
| --- | --- | --- | --- | --- | --- |
| 2.1 | `US500` (S&P 500) | `snapshot_pares` | +1 se last > D1 open | -1 (inv) | +1 |
| 2.2 | `STOXX50` (Euro Stoxx) | `snapshot_pares` | +1 se last > D1 open | -1 (inv) | +1 |
| 2.3 | `CN50` (China 50) | `snapshot_pares` | +1 se last > D1 open | -1 (inv) | +1 |
| 2.4 | `VIX` | `threshold` | -1 se > 20 (risk-off), +1 se < 15, 0 entre | +1 (rof) / -1 (ron) | -1 (rof) / +1 (ron) |
| 2.5 | `EEM` (ETF Emergentes) | `snapshot_pares` | +1 se last > D1 open | -1 (inv) | +1 |
| 2.6 | `HYG` (High Yield Bonds) | `snapshot_pares` | +1 se last > D1 open | -1 (inv) | +1 |
| 2.7 | `MOVE` (Vol Bonds) | `snapshot_pares` (inv) | -1 se last > D1 open | +1 | -1 |

#### Coleta Multi-Source — Cap. 2

| Simbolo | MT5 (primario) | Yahoo Finance (fb 1) |
| --- | --- | --- |
| `US500` | US500, SPX500 | `^GSPC`, `SPY` |
| `STOXX50` | STOXX50, SX5E | `^STOXX50E` |
| `CN50` | CN50, CHINA50 | `FXI`, `ASHR` |
| `VIX` | VIX, USVIX | `^VIX` |
| `EEM` | — | `EEM` |
| `HYG` | — | `HYG` |
| `MOVE` | MOVE | `^MOVE` |

**Score maximo capitulo 2:** ±7 pontos (WDO) / ±7 pontos (WINFUT)

---

### 3) Diferencial de Juros — Carry Trade BRL (Peso: Muito Alto)

- **Porque importa:** O Brasil historicamente possui uma das taxas de juros
  reais mais altas do mundo. A SELIC elevada atrai capital externo via carry
  trade (investidores tomam emprestado em USD/EUR/JPY e investem em titulos
  brasileiros). O diferencial SELIC vs Fed Funds Rate e o principal driver
  de fluxo para o BRL.

#### Regras de Pontuacao — Cap. 3 Carry Trade

| # | Indicador | Tipo | Regra | Score WDO | Score WINFUT |
| --- | --- | --- | --- | --- | --- |
| 3.1 | `BR10Y-US10Y` (Spread 10Y) | `spread_trend` | +1 se spread subindo | -1 (inv) | +1 |
| 3.2 | `BR2Y-US2Y` (Spread 2Y) | `spread_trend` | +1 se spread subindo | -1 (inv) | +1 |
| 3.3 | `DI1F` (DI Futuro 1 ano) | `snapshot_par` | -1 se subindo forte (aperto monetario), +1 se caindo | +1/-1 | -1/+1 |

> **Nota DI1F para WINFUT:** DI subindo = juros maiores = custo de capital maior =
> pressiona bolsa para baixo. Porem, DI subindo tambem atrai carry = BRL forte.
> O score para WINFUT e invertido em relacao ao WDO neste caso.

#### Coleta Multi-Source — Cap. 3

| Simbolo | MT5 (primario) | Yahoo Finance (fb 1) | FRED (fb 2) |
| --- | --- | --- | --- |
| `BR10Y` | — | `BR10Y=RR` | — |
| `US10Y` | US10Y | `^TNX` | `DGS10` |
| `BR2Y` | — | — | — |
| `US2Y` | US2Y | `^IRX` (proxy) | `DGS2` |
| `DI1F` | DI1F, DI1! | `DI1F25.SA` | — |

**Score maximo capitulo 3:** ±3 pontos (WDO) / ±3 pontos (WINFUT)

---

### 4) Politica Monetaria — BCB (Banco Central do Brasil) (Peso: Muito Alto)

- **Porque importa:** O COPOM (Comite de Politica Monetaria) define a SELIC
  e sinaliza a direcao futura. Decisoes hawkish fortalecem BRL via carry
  e reduzem atratividade da bolsa. Decisoes dovish enfraquecem BRL e
  favorecem bolsa (custo de capital menor).

#### Regras de Pontuacao — Cap. 4 BCB Policy

| # | Sinal | Campo Config | Valores | Score WDO | Score WINFUT |
| --- | --- | --- | --- | --- | --- |
| 4.1 | Reuniao COPOM | `copom_tone` | hawkish/dovish/neutral | -1 hawk, +1 dov | +1 hawk(-), -1 dov(+) |
| 4.2 | Ata do COPOM | `copom_ata_tone` | hawkish/dovish/neutral | -1 hawk, +1 dov | +1 hawk(-), -1 dov(+) |
| 4.3 | Relatorio Inflacao (RI) | `bcb_ri_tone` | hawkish/dovish/neutral | -1 hawk, +1 dov | -1 hawk, +1 dov |
| 4.4 | Focus (Expectativas) | `focus_selic_direction` | up/down/stable | -1 up, +1 down | -1 up, +1 down |
| 4.5 | Intervencao Cambial BCB | `bcb_intervencao_fx` | true/false | -1 se swap/leilao (BRL forte) | 0 |

> **WDO:** COPOM hawkish = SELIC sobe = BRL forte = dolar cai = WDO -1.
> **WINFUT:** COPOM hawkish misto. SELIC sobe = custo capital maior = bolsa pressionada.
> Porem, Para RI e Focus, hawkish = inflacao maior = preocupacao economica.
> A logica e: hawkish no juros fortalece BRL (bom para WDO short) mas pressiona bolsa.

**Campos manuais no JSON:**
```json
{
  "copom_tone": "hawkish",
  "copom_ata_tone": "hawkish",
  "bcb_ri_tone": "neutral",
  "focus_selic_direction": "up",
  "bcb_intervencao_fx": false
}
```

> **Calendario COPOM 2026:** 28-29 Jan, 18-19 Mar, 6-7 Mai, 17-18 Jun,
> 29-30 Jul, 16-17 Set, 28-29 Out, 9-10 Dez.

**Score maximo capitulo 4:** ±5 pontos (WDO) / ±5 pontos (WINFUT)

---

### 5) Politica Monetaria — Fed (Federal Reserve) (Peso: Alto)

- **Porque importa:** O Fed define a taxa de juros do dolar americano.
  Fed hawkish = USD forte globalmente = dolar sobe vs BRL. Fed dovish =
  USD fraco = capital flui para emergentes = BRL forte.

#### Regras de Pontuacao — Cap. 5 Fed Policy

| # | Sinal | Campo Config | Valores | Score WDO | Score WINFUT |
| --- | --- | --- | --- | --- | --- |
| 5.1 | Reuniao FOMC | `fed_tone` | hawkish/dovish/neutral | +1 hawk, -1 dov | -1 hawk, +1 dov |
| 5.2 | Dot Plot / SEP | `fed_dots_direction` | up/down/stable | +1 up, -1 down | -1 up, +1 down |
| 5.3 | Fed Minutes | `fed_minutes_tone` | hawkish/dovish/neutral | +1 hawk, -1 dov | -1 hawk, +1 dov |
| 5.4 | QT/QE Status | `fed_qt_status` | qt_active/qe_active/neutral | +1 QT, -1 QE | -1 QT, +1 QE |

**Campos manuais no JSON:**
```json
{
  "fed_tone": "neutral",
  "fed_dots_direction": "stable",
  "fed_minutes_tone": "neutral",
  "fed_qt_status": "qt_active"
}
```

> **Calendario FOMC 2026:** 27-28 Jan, 17-18 Mar, 5-6 Mai, 16-17 Jun,
> 28-29 Jul, 15-16 Set, 27-28 Out, 15-16 Dez.

**Score maximo capitulo 5:** ±4 pontos (WDO) / ±4 pontos (WINFUT)

---

### 6) Politica Fiscal Brasileira e Risco Soberano (Peso: Muito Alto)

- **Porque importa:** O risco fiscal brasileiro e o principal driver
  domestico do USDBRL. Percepcao de irresponsabilidade fiscal causa
  fuga de capital, BRL despenca, e Ibovespa cai por aumento do risco-pais.

#### Regras de Pontuacao — Cap. 6 Risco Fiscal

| # | Indicador | Tipo | Regra | Score WDO | Score WINFUT |
| --- | --- | --- | --- | --- | --- |
| 6.1 | CDS 5Y Brasil | `threshold` | +1 se > 200bps (risco alto), -1 se < 150bps | +1 (BRL fraco) | -1 |
| 6.2 | EMBI+ Brasil | `snapshot_pares` | +1 se subindo (risco-pais piorando) | +1 | -1 |
| 6.3 | Resultado Primario | Config manual | +1 superavit, -1 deficit | -1 (inv) | +1 |
| 6.4 | Arcabouco Fiscal | Config manual | `cumprindo`/`risco`/`rompido` | -1/0/+2 | +1/0/-2 |
| 6.5 | Rating Soberano | Config manual | `upgrade`/`stable`/`downgrade` | -1/0/+1 | +1/0/-1 |

**Campos manuais no JSON:**
```json
{
  "resultado_primario_tone": "deficit",
  "arcabouco_fiscal": "cumprindo",
  "rating_soberano": "stable"
}
```

#### Coleta Multi-Source — Cap. 6

| Simbolo | MT5 | Yahoo Finance | Descricao |
| --- | --- | --- | --- |
| `CDS_5Y_BR` | — | — | Fonte manual (Bloomberg/Reuters) |
| `EMBI_BR` | — | `EMB` (proxy ETF) | JP Morgan EMBI+ |

**Score maximo capitulo 6:** ±5 pontos (WDO) / ±5 pontos (WINFUT)

---

### 7) Forca do Dolar Global — DXY e Pares (Peso: Alto)

- **Porque importa:** O DXY (Dollar Index) reflete a forca global do USD.
  Um dolar forte globalmente pressiona todas as moedas emergentes,
  incluindo o BRL. O USDBRL tem correlacao > 0.80 com o DXY.

#### Regras de Pontuacao — Cap. 7 Forca USD Global

| # | Simbolo | Tipo | Regra | Score WDO | Score WINFUT |
| --- | --- | --- | --- | --- | --- |
| 7.1 | `DXY` (Dollar Index) | `snapshot_pares` | +1 se > D1 open (USD forte) | +1 | -1 |
| 7.2 | `EURUSD` | `snapshot_pares` | +1 se EUR forte (DXY fraco) | -1 | +1 |
| 7.3 | `USDMXN` (Peso Mexicano) | `snapshot_pares` | +1 se MXN fraco (peers EM) | +1 | -1 |
| 7.4 | `USDCLP` (Peso Chileno) | `snapshot_pares` | +1 se CLP fraco (peers LatAm) | +1 | -1 |
| 7.5 | `USDZAR` (Rand Sul-africano) | `snapshot_pares` | +1 se ZAR fraco (peers comm.) | +1 | -1 |

#### Coleta Multi-Source — Cap. 7

| Simbolo | MT5 (primario) | Yahoo Finance (fb 1) | ExchangeRate (fb 2) |
| --- | --- | --- | --- |
| `DXY` | UsDollar, USDX | `DX-Y.NYB`, `UUP` | — |
| `EURUSD` | EURUSD | `EURUSD=X` | `EURUSD` |
| `USDMXN` | USDMXN | `USDMXN=X` | `USDMXN` |
| `USDCLP` | USDCLP | `USDCLP=X` | `USDCLP` |
| `USDZAR` | USDZAR | `USDZAR=X` | `USDZAR` |

> **Nota peers EM:** USDMXN, USDCLP e USDZAR servem como confirmacao
> cruzada. Se todos os emergentes enfraquecem juntos, o movimento e global
> (DXY-driven). Se apenas BRL enfraquece, o problema e domestico (fiscal/politico).

**Score maximo capitulo 7:** ±5 pontos (WDO) / ±5 pontos (WINFUT)

---

### 8) Smart Money Concepts (SMC) — H4 Context (Peso: Alto)

- **Porque importa:** Identifica acao institucional em USDBRL e WINFUT.
  Os dois ativos sao analisados separadamente com scores independentes.

#### Regras de Pontuacao — Cap. 8 SMC (por ativo)

| # | Componente | Tipo | Regra | Score |
| --- | --- | --- | --- | --- |
| 8.1 | BOS (Break of Structure) | `bos_detection` | +1 se BOS de alta, -1 se BOS de baixa | ±1 |
| 8.2 | CHoCH (Change of Character) | `choch_detection` | +2 se CHoCH bullish, -2 se bearish | ±2 |
| 8.3 | Zona OTE + POI | `ote_zone` | +3 se discount + POI, -3 se premium + POI | ±3 |
| 8.4 | FVG (Fair Value Gap) | `fvg_detection` | +1 se FVG bullish abaixo, -1 se bearish acima | ±1 |
| 8.5 | Liquidez (Sweep) | `liquidity_sweep` | +1 sweep sell-side, -1 sweep buy-side | ±1 |

> **SMC WDO:** Score positivo = USDBRL deve subir (dolar forte).
> **SMC WINFUT:** Score positivo = Ibovespa deve subir.
> Cada ativo tem seu proprio calculo SMC independente.

**Parametros configurados:**
```json
{
  "smc_context_wdo": {
    "symbol": "USDBRL", "timeframe": "H4", "barras": 600,
    "lookback_zona": 120, "swing_window": 3, "poi_distancia_pct": 2.0
  },
  "smc_context_winfut": {
    "symbol": "WINFUT", "timeframe": "H4", "barras": 600,
    "lookback_zona": 120, "swing_window": 3, "poi_distancia_pct": 2.0
  }
}
```

**Score maximo capitulo 8:** ±8 pontos (WDO) / ±8 pontos (WINFUT)

---

### 9) Filtro de Sazonalidade Intraday (Peso: Medio)

- **Porque importa:** O mercado brasileiro tem horarios especificos de
  maior liquidez e volatilidade. O WINFUT e WDO operam das 9:00 as 18:00
  (horario de Brasilia, UTC-3).

#### Regras de Aplicacao — Cap. 9 (Multiplicador)

| # | Sessao | Inicio (BRT) | Fim (BRT) | Multiplicador | Justificativa |
| --- | --- | --- | --- | --- | --- |
| 9.1 | Pre-abertura | 08:30 | 09:00 | x0.5 | Leilao de abertura, spreads largos |
| 9.2 | Abertura B3 | 09:00 | 10:30 | x1.5 | **Pico de liquidez**, ajuste overnight, gaps |
| 9.3 | Manha | 10:30 | 12:00 | x1.2 | Boa liquidez, dados EUA pre-market |
| 9.4 | Almoco | 12:00 | 13:30 | x0.7 | Liquidez reduzida |
| 9.5 | Overlap NY | 13:30 | 16:00 | x1.3 | **Dados EUA**, NY aberta, alta volatilidade |
| 9.6 | Final pregao | 16:00 | 17:30 | x1.0 | Ajuste posicoes, PM fixing |
| 9.7 | After-market | 17:30 | 18:00 | x0.5 | Liquidez minima |

> **Formula:** `score_ajustado = score_raw * multiplicador_sessao`
> Horarios em UTC-3 (Brasilia).

#### Configuracao — Cap. 9

```json
{
  "ajuste_horario": {
    "pre_abertura":  {"inicio": "11:30", "fim": "12:00", "tipo": "multiplicador", "valor": 0.5},
    "abertura_b3":   {"inicio": "12:00", "fim": "13:30", "tipo": "multiplicador", "valor": 1.5},
    "manha":         {"inicio": "13:30", "fim": "15:00", "tipo": "multiplicador", "valor": 1.2},
    "almoco":        {"inicio": "15:00", "fim": "16:30", "tipo": "multiplicador", "valor": 0.7},
    "overlap_ny":    {"inicio": "16:30", "fim": "19:00", "tipo": "multiplicador", "valor": 1.3},
    "final_pregao":  {"inicio": "19:00", "fim": "20:30", "tipo": "multiplicador", "valor": 1.0},
    "after_market":  {"inicio": "20:30", "fim": "21:00", "tipo": "multiplicador", "valor": 0.5}
  }
}
```

> **Nota:** Os horarios no JSON estao em UTC para compatibilidade.
> BRT = UTC-3. Abertura B3 09:00 BRT = 12:00 UTC.

---

### 10) Dados Macro BRL — Brasil (Peso: Alto)

- **Porque importa:** Indicadores macro brasileiros impactam expectativas
  de crescimento, inflacao e juros, afetando BRL e bolsa.

#### Regras de Pontuacao — Cap. 10 Macro Brasil

| # | Indicador | Invert WDO | Regra | Score WDO | Score WINFUT |
| --- | --- | --- | --- | --- | --- |
| 10.1 | IPCA | true (WDO) | +1 se acima do esperado | -1 (hawk→BRL forte) | -1 (inflacao=ruim) |
| 10.2 | PIB | true | +1 se acima do esperado | -1 (crescimento→BRL) | +1 (crescimento=bolsa) |
| 10.3 | CAGED/PNAD (Emprego) | true | +1 se forte | -1 | +1 |
| 10.4 | PMI Industria | true | +1 se > 50 | -1 | +1 |
| 10.5 | Vendas Varejo | true | +1 se crescendo | -1 | +1 |
| 10.6 | Producao Industrial | true | +1 se crescendo | -1 | +1 |
| 10.7 | Balanca Comercial | true | +1 se superavit | -1 | +1 |
| 10.8 | IBC-Br (Proxy PIB mensal) | true | +1 se crescendo | -1 | +1 |
| 10.9 | Confianca Consumidor (FGV) | true | +1 se crescendo | -1 | +1 |
| 10.10 | Confianca Industria (CNI) | true | +1 se crescendo | -1 | +1 |
| 10.R | Risco Proativo | — | -1 se evento BRL High Impact < 24h | -1 | -1 |

> **WDO:** Dados fortes = BCB hawkish = BRL forte = dolar cai = score WDO invertido.
> **WINFUT:** Dados fortes = economia saudavel = bolsa sobe. Excecao: IPCA alto e negativo
> para bolsa (custo de capital sobe).

#### Config JSON — Cap. 10

```json
{
  "macro_domesticos_brl": {
    "moeda": "BRL",
    "impacto_minimo": "Low",
    "variacao_threshold_pct": 0.001,
    "usar_ultimo_evento": true,
    "max_defasagem_dias": 3650,
    "indicadores": [
      {"id": "BRL_IPCA",    "titulo_keywords": ["ipca", "consumer price", "inflation"], "invert_wdo": true, "invert_winfut": true},
      {"id": "BRL_PIB",     "titulo_keywords": ["pib", "gdp br", "gdp brazil"],        "invert_wdo": true, "invert_winfut": false},
      {"id": "BRL_EMPREGO", "titulo_keywords": ["caged", "pnad", "employment br"],     "invert_wdo": true, "invert_winfut": false},
      {"id": "BRL_PMI",     "titulo_keywords": ["pmi br", "pmi brazil", "purchasing"], "invert_wdo": true, "invert_winfut": false},
      {"id": "BRL_VAREJO",  "titulo_keywords": ["retail br", "varejo", "vendas"],      "invert_wdo": true, "invert_winfut": false},
      {"id": "BRL_PROD_IND","titulo_keywords": ["producao industrial", "industrial br"],"invert_wdo": true, "invert_winfut": false},
      {"id": "BRL_TRADE",   "titulo_keywords": ["trade balance br", "balanca comercial"],"invert_wdo": true, "invert_winfut": false},
      {"id": "BRL_IBC",     "titulo_keywords": ["ibc-br", "ibc br", "economic activity"],"invert_wdo": true, "invert_winfut": false},
      {"id": "BRL_CONF_CONS","titulo_keywords": ["confianca consumidor", "consumer confidence br"],"invert_wdo": true, "invert_winfut": false},
      {"id": "BRL_CONF_IND","titulo_keywords": ["confianca industria", "cni", "industry confidence"],"invert_wdo": true, "invert_winfut": false}
    ]
  }
}
```

**Score maximo capitulo 10:** ±10 pontos (WDO) / ±10 pontos (WINFUT)

---

### 11) Dados Macro USD — Estados Unidos (Peso: Alto)

- **Porque importa:** Dados americanos impactam diretamente o DXY e,
  por consequencia, o USDBRL. Dados fortes = Fed hawkish = USD forte = BRL fraco.

#### Regras de Pontuacao — Cap. 11 Macro USD

| # | Indicador | Regra | Score WDO | Score WINFUT |
| --- | --- | --- | --- | --- |
| 11.1 | CPI USA | +1 se acima esperado (hawkish) | +1 | -1 |
| 11.2 | NFP (Non-Farm Payrolls) | +1 se forte | +1 | -1 |
| 11.3 | Unemployment Rate | -1 se subindo (invertido) | -1 | +1 |
| 11.4 | GDP USA | +1 se forte | +1 | -1 |
| 11.5 | Retail Sales USA | +1 se forte | +1 | -1 |
| 11.6 | ISM Manufacturing | +1 se > 50 | +1 | -1 |
| 11.7 | PCE (Deflator Fed) | +1 se acima | +1 | -1 |
| 11.8 | ADP Employment | +1 se forte | +1 | -1 |
| 11.9 | Consumer Confidence | +1 se forte | +1 | -1 |
| 11.10 | Initial Jobless Claims | -1 se subindo (invertido) | -1 | +1 |
| 11.R | Risco Proativo | -1 se evento USD High Impact < 24h | -1 | -1 |

#### Config JSON — Cap. 11 (FRED series)

| Serie FRED | Indicador | Frequencia |
| --- | --- | --- |
| `CPIAUCSL` | CPI USA | Mensal |
| `PAYEMS` | NFP/Employment | Mensal |
| `UNRATE` | Unemployment Rate | Mensal |
| `GDP` | GDP USA | Trimestral |
| `RSXFS` | Retail Sales | Mensal |
| `MANEMP` | Manufacturing | Mensal |
| `PCEPI` | PCE Price Index | Mensal |
| `ICSA` | Jobless Claims | Semanal |

**Score maximo capitulo 11:** ±10 pontos (WDO) / ±10 pontos (WINFUT)

---

### 12) Indicadores de Exaustao e Momentum — D1/H4 (Peso: Medio)

- **Porque importa:** Sinaliza exaustao de movimento em USDBRL e WINFUT.
  Ambos ativos sao analisados separadamente.

#### Regras de Pontuacao — Cap. 12 (por ativo)

| # | Indicador | Parametros | Condicao | Score |
| --- | --- | --- | --- | --- |
| 12.1 | RSI | periodo=14 | < 30 → +1, > 70 → -1 | ±1 |
| 12.2 | Stochastic | (14,3,3) | %K < 20 → +1, > 80 → -1 | ±1 |
| 12.3 | RSI + Stoch Combo | — | ambos extremos simultaneamente | ±1 |
| 12.4 | Bollinger Bands | (20,2) | fora das bandas | ±1 |
| 12.5 | ADX | periodo=14 | ADX > 40 E caindo | ±1 |
| 12.6 | OBV | lookback=20 | divergencia preco/volume | ±1 |
| 12.7 | MACD | (12,26,9) | cruzamento bullish/bearish | ±1 |
| 12.8 | Afastamento SMA 20 | periodo=20 | > 2% de afastamento | ±1 |
| 12.I | ATR (informacional) | periodo=14 | ATR > 1.5x media | flag |

**Score maximo capitulo 12:** ±8 pontos por ativo (D1+H4 = ±16 teorico)

---

### 13) Sentimento e Posicionamento — B3 e CFTC (Peso: Alto)

- **Porque importa:** Fluxo de investidores estrangeiros na B3 e um dos
  principais drivers do WINFUT e WDO. Dados de posicionamento do COT
  (BRL futures na CME) e fluxo estrangeiro na B3 revelam direcao do smart money.

#### Regras de Pontuacao — Cap. 13 Sentimento

| # | Indicador | Condicao | Score WDO | Score WINFUT |
| --- | --- | --- | --- | --- |
| 13.1 | COT BRL Net (CFTC) | net long BRL crescente | -1 | +1 |
| 13.2 | Fluxo Estrangeiro B3 | positivo (entrada) | -1 | +1 |
| 13.3 | | negativo (saida) | +1 | -1 |
| 13.4 | Posicao Cambial Bancos | comprada em USD (hedge) | +1 | -1 |
| 13.5 | Extreme Positioning | mudanca > 20% OI | ±2 | ±2 |
| 13.R | Retail Contrarian | non-reportable > 60% | ±1 | ±1 |

#### Coleta de Dados — Cap. 13

| Fonte | Descricao |
| --- | --- |
| CFTC Socrata API | COT BRL Futures (CME) `contract_market_name = "BRAZILIAN REAL"` |
| B3 (manual) | Fluxo estrangeiro diario (B3 website / config manual) |

**Score maximo capitulo 13:** ±5 pontos (WDO) / ±5 pontos (WINFUT)

---

### 14) Sazonalidade Macro e Eventos Estruturais (Peso: Medio)

- **Porque importa:** USDBRL exibe padroes sazonais ligados ao calendario
  fiscal brasileiro e fluxos de dividendos/remessas de multinacionais.

#### Regras de Pontuacao — Cap. 14 Sazonalidade

| # | Indicador | Condicao | Score WDO | Score WINFUT |
| --- | --- | --- | --- | --- |
| 14.1 | Score Mensal Jan-Fev | Fluxo dividendos, volatilidade alta | +1 | -1 |
| 14.1 | Score Mensal Mar-Abr | Repatriacao IR, entrada dolares | -1 | +1 |
| 14.1 | Score Mensal Mai-Jun | Remessas dividendos exterior | +1 | -1 |
| 14.1 | Score Mensal Jul-Ago | Periodo neutro | 0 | 0 |
| 14.1 | Score Mensal Set-Out | Pre-eleitoral (ciclo par), fluxo | -1 | +1 |
| 14.1 | Score Mensal Nov | Black Friday, fluxo comercial | -1 | +1 |
| 14.1 | Score Mensal Dez | Remessas fim de ano, reducao risco | +1 | -1 |
| 14.2 | Carnaval | 3 dias antes + durante | -1 | -1 |
| 14.3 | Vencimento WINFUT | Quarta-feira do mes de venc. | 0 | -1 |

```json
{
  "sazonalidade_macro": {
    "regras_mensais_wdo":    {"1": 1, "2": 1, "3": -1, "4": -1, "5": 1, "6": 1, "7": 0, "8": 0, "9": -1, "10": -1, "11": -1, "12": 1},
    "regras_mensais_winfut": {"1": -1, "2": -1, "3": 1, "4": 1, "5": -1, "6": -1, "7": 0, "8": 0, "9": 1, "10": 1, "11": 1, "12": -1},
    "carnaval": {"mes": 2, "dia_inicio": 14, "dia_fim": 18, "score_wdo": -1, "score_winfut": -1}
  }
}
```

**Score maximo capitulo 14:** ±2 pontos (WDO) / ±2 pontos (WINFUT)

---

### 15) Fluxos de Capital e Balanca de Pagamentos (Peso: Medio)

- **Porque importa:** Fluxos de capital de longo prazo determinam a direcao
  estrutural do BRL.

#### Regras de Pontuacao — Cap. 15 Fluxos

| # | Indicador | Condicao | Score WDO | Score WINFUT |
| --- | --- | --- | --- | --- |
| 15.1 | Balanca Comercial (FRED) | superavit crescente | -1 | +1 |
| 15.2 | IDP (Investimento Direto) | entrada crescente | -1 | +1 |
| 15.3 | Reservas Internacionais | crescentes | -1 | 0 |
| 15.4 | Swaps Cambiais BCB (estoque) | crescente (BCB vendendo USD) | -1 | 0 |

#### Coleta — Cap. 15

| Serie FRED | Descricao |
| --- | --- |
| `XTNTVA01BRM664S` | Brazil Trade Balance (OECD, mensal) |

**Score maximo capitulo 15:** ±4 pontos (WDO) / ±2 pontos (WINFUT)

---

### 16) Geopolitica e Riscos de Cauda (Peso: Condicional)

- **Porque importa:** Eventos geopoliticos e crises politicas domesticas
  afetam o BRL desproporcionalmente por ser moeda emergente.

#### Regras de Pontuacao — Cap. 16 Geopolitica

| # | Evento | Score WDO | Score WINFUT | Logica |
| --- | --- | --- | --- | --- |
| 16.1 | Crise politica domestica | +3 | -3 | Impeachment/CPI/greve geral |
| 16.2 | Tensao EUA-China | +2 | -2 | Impacto em commodities e risk-off |
| 16.3 | Crise fiscal aguda | +3 | -3 | Furo de teto/arcabouco |
| 16.4 | Intervencao judicial STF | +1 | -1 | Inseguranca juridica |
| 16.5 | Escalada belica global | +2 | -2 | Risk-off emergentes |
| 16.6 | Crise energetica (secas) | +1 | -1 | Impacto inflacionario |
| 16.7 | Greve bloqueio estradas | +1 | -1 | Impacto logistico |

```json
{
  "geopolitica": {
    "eventos": {
      "crise_politica": {"ativo": false, "score_wdo": 3, "score_winfut": -3},
      "tensao_eua_china": {"ativo": false, "score_wdo": 2, "score_winfut": -2},
      "crise_fiscal_aguda": {"ativo": false, "score_wdo": 3, "score_winfut": -3},
      "intervencao_stf": {"ativo": false, "score_wdo": 1, "score_winfut": -1},
      "escalada_belica": {"ativo": false, "score_wdo": 2, "score_winfut": -2},
      "crise_energetica": {"ativo": false, "score_wdo": 1, "score_winfut": -1},
      "greve_bloqueio": {"ativo": false, "score_wdo": 1, "score_winfut": -1}
    }
  }
}
```

**Score maximo capitulo 16:** 0 / +13 (WDO) | 0 / -13 (WINFUT)

---

## Logica de Veredito e Execucao

### Faixas de Score — WDO (Dolar)

| Faixa | Veredito | Significado |
| --- | --- | --- |
| Score > +10 | STRONG BUY WDO | Dolar deve subir fortemente |
| Score +6 a +10 | BUY WDO | Dolar deve subir |
| Score -5 a +5 | NEUTRAL | Sem direcao clara |
| Score -10 a -5 | SELL WDO | Dolar deve cair |
| Score < -10 | STRONG SELL WDO | Dolar deve cair fortemente |

### Faixas de Score — WINFUT (Ibovespa)

| Faixa | Veredito | Significado |
| --- | --- | --- |
| Score > +10 | STRONG BUY WINFUT | Ibovespa deve subir fortemente |
| Score +6 a +10 | BUY WINFUT | Ibovespa deve subir |
| Score -5 a +5 | NEUTRAL | Sem direcao clara |
| Score -10 a -5 | SELL WINFUT | Ibovespa deve cair |
| Score < -10 | STRONG SELL WINFUT | Ibovespa deve cair fortemente |

### Ajustes de Confianca

- **VIX > 30:** confianca maxima de 50% para qualquer sinal BUY WINFUT / SELL WDO.
- **Crise fiscal ativa (Cap. 6):** reduzir confianca BUY WINFUT em 30%.
- **Intervencao cambial BCB ativa:** suspender sinais BUY WDO por 48h.
- **DXY > 110:** bias positivo estrutural WDO, reduzir score SELL WDO em -2.

### Condicoes de Veto (Nao Operar)

- VIX > 35 + S&P500 caindo > 3% intraday.
- Intervencao direta BCB (leilao spot USD) nas ultimas 24h.
- COPOM + FOMC na mesma semana (incerteza extrema).
- ATR D1 > 2x da media de 20 periodos (volatilidade excessiva).

---

## Persistencia SQLite

```sql
INSERT INTO sinais_wdo_winfut (
    ativo, timeframe, timestamp_ms, tipo_sinal,
    score_total, confianca, veredito,
    score_commodities, score_risco, score_carry,
    score_bcb, score_fed, score_fiscal,
    score_usd_global, score_smc, score_sazonalidade_intraday,
    score_macro_brl, score_macro_usd,
    score_momentum, score_sentimento,
    score_sazonalidade_macro, score_fluxos,
    score_geopolitica,
    vix_valor, sp500_var_pct, yield_spread_10y,
    crise_fiscal_alert, intervencao_bcb_alert,
    modelo, notas
) VALUES (...);
```

---

## Fontes de Dados

| Indicador | Fonte | Frequencia |
| --- | --- | --- |
| USDBRL, WINFUT | MT5 / B3 | Real-time |
| Commodities | MT5 / Yahoo Finance | Real-time |
| DXY, Pares FX | MT5 / Yahoo / ExchangeRate | Real-time |
| VIX, S&P 500 | MT5 / Yahoo | Real-time |
| SELIC, DI Futuro | BCB / B3 | Diaria |
| IPCA, PIB, CAGED | IBGE / FRED | Mensal |
| CPI USA, NFP | BLS / FRED | Mensal |
| COT Report BRL | CFTC Socrata | Semanal |
| Fluxo Estrangeiro B3 | B3 / Config manual | Diario |
| CDS 5Y Brasil | Bloomberg / Manual | Diario |

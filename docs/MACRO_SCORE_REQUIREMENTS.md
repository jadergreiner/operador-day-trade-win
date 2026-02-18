<!-- pyml disable md013 -->
<!-- pyml disable md022 -->
<!-- pyml disable md040 -->

# Sistema de Analise Macro - Documento de Requisitos

## Autor: Head de Financas
## Status: Aprovado para desenvolvimento

---

## 1. VISAO GERAL

Sistema de pontuacao macro para o Mini Indice Brasileiro (WIN) que sintetiza multiplas dimensoes de mercado em um score unico de decisao.

- **Score positivo** → Sinal de COMPRA
- **Score negativo** → Sinal de VENDA
- **Score zero ou proximo** → NEUTRO (sem operacao)

## 2. PRINCIPIOS FUNDAMENTAIS

1. **Persistencia Total**: Todas as analises e decisoes devem ser persistidas em banco de dados com timestamp e contexto.
2. **Aprendizado por Reforco**: O sistema comeca simples e evolui comparando decisoes passadas com resultados reais.
3. **Inteligencia Hibrida**: Head de Financas contribui com conhecimento de mercado; IA contribui com algoritmos e reconhecimento de padroes. Aprendizado mutuo.
4. **Pesos Dinamicos**: Fase inicial com peso 1 para todos os itens. Pesos ajustados no futuro com base em aprendizado e contribuicao do Head.

## 3. FORMULA

```
score_final = SUM(pontuacao_item_i * peso_i)

Se score_final > 0  -> COMPRA
Se score_final < 0  -> VENDA
Se score_final == 0 -> NEUTRO
```

## 4. ITENS DE PONTUACAO - FASE 1 (Intraday via MT5)

### 4.1 Logica padrao para ativos intraday

```
Se preco_atual > preco_abertura_do_dia -> pontuacao conforme correlacao
Se preco_atual < preco_abertura_do_dia -> pontuacao conforme correlacao
Se preco_atual == preco_abertura_do_dia -> 0
```

- Correlacao DIRETA: ativo subindo = +1 para WIN, ativo caindo = -1 para WIN
- Correlacao INVERSA: ativo subindo = -1 para WIN, ativo caindo = +1 para WIN

### 4.2 Indices Brasil

| #  | Simbolo | Nome                          | Correlacao | Alta | Queda | Contrato Futuro |
|----|---------|-------------------------------|------------|------|-------|-----------------|
| 1  | IBOV    | Indice Bovespa                | Direta     | +1   | -1    | Nao             |
| 2  | SMLL    | Small Caps                    | Direta     | +1   | -1    | Nao             |
| 3  | MLCX    | MidLarge Cap                  | Direta     | +1   | -1    | Nao             |
| 4  | INDX    | Setor Industrial              | Direta     | +1   | -1    | Nao             |
| 5  | IMOB    | Imobiliario                   | Direta     | +1   | -1    | Nao             |
| 6  | IMAT    | Materiais Basicos             | Direta     | +1   | -1    | Nao             |
| 7  | IGNM    | Governanca - Novo Mercado     | Direta     | +1   | -1    | Nao             |
| 8  | AGFS    | Agronegocio                   | Direta     | +1   | -1    | Nao             |
| 9  | BDRX    | BDRs                          | Direta     | +1   | -1    | Nao             |
| 10 | IBRASIL | Indice Brasil                 | Direta     | +1   | -1    | Nao             |
| 11 | IBXL    | IBrX-50 Large Cap             | Direta     | +1   | -1    | Nao             |
| 12 | IBXX    | IBrX-100                      | Direta     | +1   | -1    | Nao             |
| 13 | ICO2    | Carbono Eficiente             | Direta     | +1   | -1    | Nao             |
| 14 | ICON    | Consumo                       | Direta     | +1   | -1    | Nao             |
| 15 | IDIV    | Dividendos                    | Direta     | +1   | -1    | Nao             |
| 16 | IEEX    | Energia Eletrica              | Direta     | +1   | -1    | Nao             |
| 17 | IFIX    | Fundos Imobiliarios           | Direta     | +1   | -1    | Nao             |
| 18 | IFNC    | Financeiro                    | Direta     | +1   | -1    | Nao             |
| 19 | ISEE    | Sustentabilidade              | Direta     | +1   | -1    | Nao             |
| 20 | UTIL    | Utilidade Publica             | Direta     | +1   | -1    | Nao             |

### 4.3 Acoes Brasil

| #  | Simbolo | Nome                 | Correlacao | Alta | Queda |
|----|---------|----------------------|------------|------|-------|
| 21 | PETR4   | Petrobras PN         | Direta     | +1   | -1    |
| 22 | VALE3   | Vale ON              | Direta     | +1   | -1    |
| 23 | ITUB3   | Itau Unibanco ON     | Direta     | +1   | -1    |
| 24 | ABEV3   | Ambev                | Direta     | +1   | -1    |
| 25 | B3SA3   | B3                   | Direta     | +1   | -1    |
| 26 | BBDC3   | Bradesco             | Direta     | +1   | -1    |
| 27 | BOVA11  | ETF Ibovespa         | Direta     | +1   | -1    |
| 28 | CXSE3   | Caixa Seguridade     | Direta     | +1   | -1    |
| 29 | EGIE3   | Engie Brasil         | Direta     | +1   | -1    |
| 30 | EQPA3   | Equatorial           | Direta     | +1   | -1    |
| 31 | MRVE3   | MRV Engenharia       | Direta     | +1   | -1    |
| 32 | RIIA3   | A confirmar          | Direta     | +1   | -1    |
| 33 | SANB3   | Santander Brasil     | Direta     | +1   | -1    |
| 34 | SAPR4   | Sanepar              | Direta     | +1   | -1    |
| 35 | VIVT3   | Vivo/Telefonica      | Direta     | +1   | -1    |
| 36 | WEGE3   | WEG                  | Direta     | +1   | -1    |

### 4.4 Dolar / Cambio Local

| #  | Simbolo | Nome              | Correlacao | Alta | Queda | Contrato Futuro |
|----|---------|-------------------|------------|------|-------|-----------------|
| 37 | WDO     | Mini Dolar         | Inversa    | -1   | +1    | Sim             |
| 39 | DXY     | Indice Dolar Global| Inversa    | -1   | +1    | Nao             |

### 4.5 Moedas Forex

**NOTA TECNICA**: A direcao do score depende da convencao de cotacao no MT5.
Para pares XXXUSD: alta = moeda fortalecendo. Para pares USDXXX: alta = dolar fortalecendo (inverter logica).
O arquiteto deve confirmar a convencao de cada par e ajustar a logica.

| #  | Simbolo | Nome                  | Correlacao | Logica (moeda fortalecendo) |
|----|---------|-----------------------|------------|----------------------------|
| 40 | EUR     | Euro                  | Direta     | +1 se fortalece, -1 se enfraquece |
| 41 | GBP     | Libra Esterlina       | Direta     | +1 se fortalece, -1 se enfraquece |
| 42 | CAD     | Dolar Canadense       | Direta     | +1 se fortalece, -1 se enfraquece |
| 43 | AUD     | Dolar Australiano     | Direta     | +1 se fortalece, -1 se enfraquece |
| 44 | NZD     | Dolar Neozelandes     | Direta     | +1 se fortalece, -1 se enfraquece |
| 45 | CNY     | Yuan Chines           | Direta     | +1 se fortalece, -1 se enfraquece |
| 46 | MXN     | Peso Mexicano         | Direta     | +1 se fortalece, -1 se enfraquece |
| 47 | ZAR     | Rand Sul-Africano     | Direta     | +1 se fortalece, -1 se enfraquece |
| 48 | TRY     | Lira Turca            | Direta     | +1 se fortalece, -1 se enfraquece |
| 49 | CLP     | Peso Chileno          | Direta     | +1 se fortalece, -1 se enfraquece |
| 50 | CHF     | Franco Suico          | Inversa    | -1 se fortalece, +1 se enfraquece |
| 51 | JPY     | Iene Japones          | Inversa    | -1 se fortalece, +1 se enfraquece |

### 4.6 Commodities

| #  | Simbolo  | Nome                | Correlacao | Alta | Queda | Contrato Futuro |
|----|----------|---------------------|------------|------|-------|-----------------|
| 52 | GLDG     | Ouro (Global)       | Inversa    | -1   | +1    | Sim             |
| 54 | IFBOI    | Boi Gordo           | Direta     | +1   | -1    | Sim             |
| 55 | IFMILHO  | Milho (IFMILHO)     | Direta     | +1   | -1    | Sim             |
| 56 | CCM      | Milho (B3)          | Direta     | +1   | -1    | Sim             |
| 57 | ICF      | Cafe Arabica        | Direta     | +1   | -1    | Sim             |
| 58 | SJC      | Soja                | Direta     | +1   | -1    | Sim             |
| 59 | BGI      | Boi Gordo Indice    | Direta     | +1   | -1    | A confirmar     |
| 60 | DAP      | Fosfato/Fertilizante| Direta     | +1   | -1    | A confirmar     |
| 61 | Petroleo WTI  | Crude Oil WTI  | Direta     | +1   | -1    | A confirmar     |
| 62 | Petroleo Brent| Brent          | Direta     | +1   | -1    | A confirmar     |
| 63 | Minerio Ferro | Iron Ore       | Direta     | +1   | -1    | A confirmar     |
| 64 | Cobre         | Copper         | Direta     | +1   | -1    | A confirmar     |

### 4.7 Juros e Renda Fixa

| #  | Simbolo | Nome                    | Correlacao | Alta | Queda | Contrato Futuro |
|----|---------|-------------------------|------------|------|-------|-----------------|
| 65 | DI      | DI Futuro               | Inversa    | -1   | +1    | Sim             |
| 66 | T10     | US Treasury 10Y         | Inversa    | -1   | +1    | A confirmar     |
| 67 | TSLC    | Tesouro Selic           | Inversa    | -1   | +1    | Nao             |

### 4.8 Criptomoedas

| #  | Simbolo | Nome       | Correlacao | Alta | Queda |
|----|---------|------------|------------|------|-------|
| 68 | BIT     | Bitcoin    | Direta     | +1   | -1    |
| 69 | ETH     | Ethereum   | Direta     | +1   | -1    |
| 70 | SOL     | Solana     | Direta     | +1   | -1    |
| 71 | ETR     | A confirmar| Direta     | +1   | -1    |

### 4.9 Indices Globais

| #  | Simbolo     | Nome             | Correlacao | Alta | Queda | Contrato Futuro |
|----|-------------|------------------|------------|------|-------|-----------------|
| 72 | WSP         | S&P 500 Futuro   | Direta     | +1   | -1    | Sim             |
| 73 | Nasdaq/US100| Nasdaq           | Direta     | +1   | -1    | A confirmar     |
| 74 | DAX         | Alemanha         | Direta     | +1   | -1    | A confirmar     |
| 75 | Hang Seng   | China/HK         | Direta     | +1   | -1    | A confirmar     |

### 4.10 Volatilidade

| #  | Simbolo | Nome         | Correlacao | Alta | Queda |
|----|---------|--------------|------------|------|-------|
| 76 | VXBR    | VIX Brasil   | Inversa    | -1   | +1    |
| 77 | VIX     | VIX US       | Inversa    | -1   | +1    |

### 4.11 Indicadores Intraday Tecnicos (aplicados ao WIN)

Estes itens tem logica de pontuacao propria, diferente do padrao "preco vs abertura".

| #  | Indicador         | Logica de Pontuacao                                                                 |
|----|-------------------|-------------------------------------------------------------------------------------|
| 78 | Volume Financeiro | Vol > media + preco subindo: +1. Vol > media + preco caindo: -1. Vol < media: 0     |
| 79 | Saldo Agressao    | Saldo positivo (compra): +1. Saldo negativo (venda): -1. Equilibrado: 0             |
| 80 | IFR/RSI (14)      | < 30 (sobrevendido): +1. > 70 (sobrecomprado): -1. 30-70: 0                        |
| 81 | Estocastico       | < 20 (sobrevendido): +1. > 80 (sobrecomprado): -1. 20-80: 0                        |
| 82 | ADX + DI+/DI-     | ADX>25 e DI+>DI-: +1. ADX>25 e DI->DI+: -1. ADX<20: 0                             |
| 83 | VWAP              | Preco > VWAP: +1. Preco < VWAP: -1. Preco na VWAP: 0                               |
| 84 | MACD (12,26,9)    | MACD > sinal e positivo: +1. MACD < sinal e negativo: -1. Indefinido: 0            |
| 85 | OBV               | OBV subindo (acumulacao): +1. OBV caindo (distribuicao): -1. Lateral: 0             |

## 5. ITENS DE PONTUACAO - FASE 2 (Dados Periodicos / Fontes Externas)

### 5.1 Logica de pontuacao diferente

```
Se dado_divulgado melhor que expectativa -> +1
Se dado_divulgado pior que expectativa  -> -1
Se sem divulgacao recente               -> manter ultimo score
```

### 5.2 Indicadores

| #  | Indicador              | Frequencia | Favoravel (+1)             | Desfavoravel (-1)           |
|----|------------------------|------------|----------------------------|-----------------------------|
| B1 | Taxa Desemprego (PNAD) | Mensal     | Caindo                     | Subindo                     |
| B2 | IPCA (Inflacao)        | Mensal     | Abaixo da expectativa      | Acima da expectativa        |
| B3 | Decisao COPOM (SELIC)  | ~45 dias   | Corte / tom dovish         | Alta / tom hawkish          |
| B4 | Decisao FOMC (FED)     | ~45 dias   | Corte / tom dovish         | Alta / tom hawkish          |
| B5 | PIB Brasil             | Trimestral | Acima da expectativa       | Abaixo da expectativa       |
| B6 | PMI Brasil             | Mensal     | Acima de 50                | Abaixo de 50                |
| B7 | Fluxo Estrangeiro B3   | Diario     | Entrada liquida            | Saida liquida               |
| B8 | Boletim Focus          | Semanal    | Revisao positiva           | Deterioracao                |
| B9 | Risco Pais (CDS/EMBI+) | Diario     | Spread caindo              | Spread subindo              |

## 6. REQUISITOS TECNICOS

### 6.1 Persistencia

- Todas as analises devem ser salvas com: timestamp, simbolo, preco_abertura, preco_atual, pontuacao, peso, score_contribuicao
- Todas as decisoes finais devem ser salvas com: timestamp, score_final, sinal (COMPRA/VENDA/NEUTRO), detalhamento por item
- Historico completo para auditoria e aprendizado por reforco

### 6.2 Contratos Futuros

Itens que operam com contratos futuros com vencimento requerem:
- Descoberta automatica do contrato vigente
- Troca automatica na rolagem
- Nunca buscar dados de contrato vencido

**Itens com contrato futuro:** WDO, WSP, GLDG, IFBOI, IFMILHO, CCM, ICF, SJC, DI, DAP

### 6.3 Moedas Forex

- Confirmar convencao de cotacao no MT5 (XXXUSD vs USDXXX)
- Ajustar direcao do score conforme convencao
- Par tipo EURUSD: alta = EUR fortalecendo
- Par tipo USDJPY: alta = USD fortalecendo (inverter)

### 6.4 Simbolos a Confirmar

Os seguintes simbolos precisam ser validados no MT5 da corretora:
- BGI, DAP, ETR, RIIA3
- Petroleo WTI/Brent (simbolo exato)
- Minerio de Ferro (disponibilidade)
- Cobre (simbolo exato)
- VIX US (simbolo exato)
- DXY (simbolo exato)
- Nasdaq/US100 (simbolo exato)
- DAX (simbolo exato)
- Hang Seng/China A50 (simbolo exato)
- T10 (preco ou yield)

### 6.5 Aprendizado por Reforco

- Comparar score_final com resultado real do WIN apos N minutos (30min, 1h, 2h)
- Calcular acuracia de cada item individualmente
- Permitir ajuste de pesos baseado em correlacao historica
- Itens com alta correlacao ganham peso; itens com ruido perdem peso

### 6.6 Fase 2 - Dados Periodicos

- APIs externas necessarias: BCB, IBGE, B3, ou agregadores
- Scheduler para captura no momento da divulgacao
- Cache do ultimo score valido entre divulgacoes
- Score persiste ate proxima atualizacao

## 7. RESUMO QUANTITATIVO

| Categoria              | Itens | Inversos                    |
|------------------------|-------|-----------------------------|
| Indices Brasil         | 20    | VXBR                        |
| Acoes Brasil           | 16    | -                           |
| Dolar/Cambio local     | 2     | WDO, DXY                    |
| Moedas Forex           | 12    | CHF, JPY                    |
| Commodities            | 12    | GLDG                        |
| Juros/Renda Fixa       | 3     | DI, T10, TSLC               |
| Criptomoedas           | 4     | -                           |
| Indices Globais        | 4     | -                           |
| Volatilidade           | 2     | VXBR, VIX                   |
| Intraday Tecnico WIN   | 8     | (logica propria)            |
| **TOTAL FASE 1**       | **83**| **10 inversos**             |
| Dados Periodicos (F2)  | 9     | -                           |
| **TOTAL GERAL**        | **93**| -                           |

# WINFUT Micro Tendências - Plano de Monitoramento

## Ciclo de Execução

O agente opera em ciclos de **2 minutos** (120 segundos) durante o horário de
pregão (09:00 - 17:55 horário de Brasília).

---

## Ações Principais (cada ciclo)

### 1) Atualizar Contexto Macro (Direcional do Dia)

- Coletar preço atual vs abertura do dia para todos os ativos de contexto:
  - Índices Globais: ES/WSP, NQ/NASD, DAX/DE30
  - Dólar/Câmbio: WDO$N, DOL$N, USDBRL
  - Juros: DI1$N, US10Y
  - Commodities: XTIUSD, XBRUSD, VALE3
  - Blue Chips: PETR4, ITUB4, BBDC4, BBAS3
  - ETFs: BOVA11, IVVB11
  - Volatilidade: VIX/USVIX
  - Crypto: BTCUSD
- Calcular Score Macro → determinar direcional do dia
- Rastrear mudanças > 2 pontos no score entre ciclos

### 2) Mapear Micro Tendência Atual (M5/M15)

- Coletar candles M5 e M15 do WIN$N (últimos 100 candles)
- Detectar estrutura SMC (BOS, CHoCH, FVG) no M15 e H1
- Calcular VWAP + desvios (±1σ, ±2σ)
- Calcular Pivôs Diários (PP, S1, S2, R1, R2)
- Avaliar indicadores de momentum M5: RSI, Stochastic, MACD, Bollinger, ADX
- Detectar padrões de candle em zonas de interesse
- Calcular Score Micro → classificar micro tendência

### 3) Identificar Regiões de Interesse

- Mapear confluências:
  - VWAP ± desvios
  - Suportes/Resistências D1
  - Pivôs Diários
  - POIs do SMC (Order Blocks, FVG)
  - Máxima/Mínima do dia anterior
  - Abertura do dia
- Ranquear regiões por nível de confluência (1-5 confluências)

### 4) Gerar Oportunidades

- Avaliar se existe oportunidade operacional:
  - Score macro alinhado com micro tendência → CONTINUAÇÃO
  - Preço em região de interesse com divergência → REVERSÃO
  - Indicadores sem direcional → AGUARDAR
- Para cada oportunidade, gerar:
  - Tipo: COMPRA ou VENDA
  - Entrada sugerida
  - Stop Loss (baseado em ATR(14) do M5)
  - Take Profit (próxima região de interesse)
  - R/R esperado (mínimo 2:1)
  - Confiança (%, baseada no score e confluências)

---

## Gatilhos Operacionais (Alertas)

### Gatilhos de Entrada

- Score Macro >= +4 **E** preço próximo a suporte/VWAP- **E** RSI M5 < 35
  → **ALERTA: Compra em desconto com macro favorável**

- Score Macro <= -4 **E** preço próximo a resistência/VWAP+ **E** RSI M5 > 65
  → **ALERTA: Venda em premium com macro desfavorável**

- BOS de alta M15 **E** preço retorna para FVG **E** Volume > 1.5× média
  → **ALERTA: Entrada SMC em pullback de alta**

- BOS de baixa M15 **E** preço retorna para FVG **E** Volume > 1.5× média
  → **ALERTA: Entrada SMC em pullback de baixa**

### Gatilhos de Reversão

- Score Macro >= +4 **MAS** CHoCH de baixa no M15 **E** RSI M5 > 70
  → **ALERTA: Possível reversão intraday — cautela**

- Preço rompe VWAP+2σ **E** Volume decrescente **E** Doji/Pin Bar
  → **ALERTA: Exaustão de alta — potencial reversão**

- Preço rompe VWAP-2σ **E** Volume decrescente **E** Engolfo de alta
  → **ALERTA: Exaustão de baixa — potencial reversão de alta**

### Gatilhos de Proteção

- WDO$N inverte com volume alto (>2× média) → ajustar Score Macro
- VIX spike > 5% vs abertura → reduzir tamanho de posição
- Score Macro muda de sinal (compra → venda) → fechar posições abertas
- Horário 17:30-17:55 → evitar novas entradas (fim do pregão)

---

## Horários Críticos para Micro Tendências

| Horário (Brasília) | Evento                                   | Ação                                    |
|--------------------|------------------------------------------|-----------------------------------------|
| 08:50 - 09:00      | Pré-abertura WIN                        | Coletar context macro, preparar pivôs   |
| 09:00 - 09:15      | Abertura + leilão                       | Observar gap e fluxo; não operar        |
| 09:15 - 10:30      | Tendência matinal                       | Primeiras micro tendências do dia       |
| 10:30 - 11:00      | Dados EUA (geralmente)                  | Volatilidade; cautela                   |
| 11:00 - 13:00      | Mercado estabelecido                    | Melhor janela para micro tendências     |
| 13:00 - 14:00      | Almoço / menor volume                  | Evitar ou scalp curto                   |
| 14:00 - 16:00      | Abertura EUA afeta fluxo               | Segunda janela de micro tendências      |
| 16:00 - 17:00      | Final da sessão regular                 | Tendência de fechamento                 |
| 17:00 - 17:55      | After market / baixa liquidez          | Evitar novas posições; encerrar dia     |

---

## Dashboard de Console

```
╔══════════════════════════════════════════════════════════════════╗
║  AGENTE MICRO TENDÊNCIA WINFUT  │  10/02/2026 11:35:42         ║
╠══════════════════════════════════════════════════════════════════╣
║                                                                  ║
║  DIRECIONAL DO DIA              │  MICRO TENDÊNCIA ATUAL         ║
║  Score Macro: +7 (COMPRA)       │  CONTINUAÇÃO DE ALTA           ║
║  Confiança: 72%                 │  BOS Alta M15 │ RSI 55         ║
║                                                                  ║
║  WIN$N: 132.450  (▲ +0.85%)     │  VWAP: 131.920                ║
║  Abertura: 131.325              │  VWAP+1σ: 132.680             ║
║                                 │  VWAP-1σ: 131.160             ║
║                                                                  ║
║  REGIÕES DE INTERESSE           │  OPORTUNIDADE                  ║
║  R2: 133.100                    │  COMPRA em pullback VWAP       ║
║  R1: 132.700 ← resistência     │  Entrada: 131.920              ║
║  PP: 132.200                    │  Stop: 131.550 (ATR)           ║
║  S1: 131.700 ← suporte alvo    │  TP: 132.700 (R1)             ║
║  S2: 131.200                    │  R/R: 2.1:1                    ║
║                                                                  ║
╚══════════════════════════════════════════════════════════════════╝
```

---

## Persistência por Ciclo

Cada ciclo deve persistir no SQLite:

1. **micro_trend_decisions:** Score macro, score micro, classificação da micro
   tendência, timestamp
2. **micro_trend_items:** Score individual de cada item (macro + micro)
3. **micro_trend_regions:** Regiões de interesse mapeadas com nível de
   confluência
4. **micro_trend_opportunities:** Oportunidades geradas com preço, SL, TP, R/R

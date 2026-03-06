"""
EXEMPLOS DE LOG: SIGNAL GENERATION & MONITORING (Camada 1)

Demonstração realista de como sinais AC1 serão exibidos em logs
quando integrados com INICIAR_MICRO_TENDENCIA_AUTO_TRADE.bat

Reference: docs/prompts/OPERATIVE_BRIEF_BACKTEST_V1_2.md (AC1-AC3)
Date: 05/03/2026
"""

# ============================================================================
# EXEMPLO 1: SIGNAL GENERATION LOG (Camada 1 - Detection Phase)
# ============================================================================

LOG_SIGNAL_GENERATION = """
============================================================================
[2026-03-05 14:23:15.342] OPERADOR MICRO TENDENCIA - v1.2.3 START
============================================================================

[PRE-FLIGHT] Verificando saude do sistema v1.2.3...
  [OK] Python version: 3.11.9
  [OK] SQLite: data/db/trading.db (45.2 MB, accessible)
  [OK] ML Dataset: 1,000 samples loaded (24 features)
  [OK] MT5 Connection: Connected to account 1234567 (DEMO)
  [PASS] Pre-flight check PASSED

[SYNC] Sincronizando operacoes MT5...
  [OK] MT5 trades sincronizados (3 days back)

[BDI] Aplicando licoes BDI...
  [OK] Licoes BDI aplicadas (06/03/2026)

[JOURNAL] Iniciando Diario RL em background...
  [OK] Diario RL iniciado

============================================================================
[14:23:45.123] AGENT EXECUTOR INICIADO - Aguardando sinais em M5
============================================================================

[14:24:00.000] [M5-CANDLE-CLOSED] Timeframe=M5, Symbol=WIN, Candle_Index=2845

[14:24:00.001] [DETECTOR] Processando candle M5...
  ├─ Open:  123.450
  ├─ High:  123.650
  ├─ Low:   123.250
  ├─ Close: 123.600
  ├─ Volume: 450 contratos
  └─ Prev_High: 123.450 | Prev_Low: 123.200

[14:24:00.005] [AC1-Signal] BOS detectado (score=+1.50)
  ├─ Type: BUY (bullish break of structure)
  ├─ Detector: BOS (Close 123.600 > Prev_High 123.450)
  ├─ Score: +1.50 (range: [-3, +3])
  ├─ Entry_Price: 123.600
  └─ Candle_Index: 2845

[14:24:00.008] [MARKET-CONTEXT] Capturando contexto de mercado...
  ├─ RSI(14): 65.5 (overbought zone)
  ├─ ATR(14): 50.0 pontos
  ├─ Bollinger Bands:
  │  ├─ Upper: 123.750
  │  └─ Lower: 123.150
  ├─ Volume: 450 (acima da media: 280)
  ├─ Spread: 2.0 pontos
  ├─ Trend_Direction: UP (últimas 5 velas)
  └─ Last_Close: 123.450

[14:24:00.012] [SIGNAL-CREATED] Sinal gerado e pronto para Camada 2
  ├─ signal_id: d4a82f1c-3e91-4f22-9c2e-7b4a8d2e5c1f
  ├─ timestamp: 2026-03-05T14:24:00.012Z
  ├─ symbol: WIN
  ├─ signal_type: BUY
  ├─ smc_score: +1.50
  ├─ smc_detector: BOS
  ├─ entry_price: 123.600
  └─ market_context: CAPTURED (8 fields)

[14:24:00.015] [AC1-PERSISTENCE] Persistindo sinal em DB...
  ├─ Table: signals
  ├─ Signal_ID: d4a82f1c-3e91-4f22-9c2e-7b4a8d2e5c1f
  ├─ Status: INSERTED successfully
  └─ Ready for Camada 2 (Decision Motor)

============================================================================
[14:24:00.020] [CAMADA-1-COMPLETE] Signal generation FINISHED
  └─ Aguardando Camada 2 (Decision Motor) para ENTRAR/FICAR_DE_FORA
============================================================================

"""

# ============================================================================
# EXEMPLO 2: SIGNAL MONITORING LOG (Camada 1 - Lifecycle Tracking)
# ============================================================================

LOG_SIGNAL_MONITORING = """
============================================================================
[14:24:05.000] [SIGTRACKER] Iniciando rastreamento de signals...
============================================================================

[AC1-TRACKING] Sinal gerado: d4a82f1c-3e91-4f22-9c2e-7b4a8d2e5c1f
  ├─ Type: BUY (score +1.50)
  ├─ Entry_Price: 123.600
  ├─ Time_Alive: 5s
  └─ Status: OPEN (aguardando Camada 2)

[14:24:10.000] [M5-CANDLE-CLOSED] Timeframe=M5, Index=2846

[AC1-CHECK] Sinal d4a82f1c ainda em rastreamento...
  ├─ Current_Close: 123.620
  ├─ High desde geração: 123.750
  ├─ Low desde geração: 123.250
  ├─ P&L se tivesse entrado: +20 pontos
  └─ Status: WINNING_POTENTIAL (não entrou, mas sinalizava certo)

[14:24:15.000] [M5-CANDLE-CLOSED] Timeframe=M5, Index=2847

[AC1-CHECK] Sinal d4a82f1c ainda em rastreamento...
  ├─ Current_Close: 123.750 (NEW HIGH)
  ├─ High máximo desde geração: 123.750
  ├─ P&L se tivesse entrado: +150 pontos
  └─ Status: WINNING_SIGNAL (rastreado com sucesso)

[14:24:30.000] [M5-CANDLE-CLOSED] Timeframe=M5, Index=2848

[AC1-CHECK] Sinal d4a82f1c rastreado por 30s...
  ├─ Current_Close: 123.680
  ├─ Peak_High: 123.750 (atingido 15s atrás)
  ├─ Current_Low: 123.150
  ├─ P&L máximo: +150 pontos
  ├─ P&L atual: +80 pontos
  └─ Status: WINNING_SIGNAL (descendo de peak)

[14:25:00.000] [M5-CANDLE-CLOSED] Timeframe=M5, Index=2849

[AC1-FINALIZE] Sinal d4a82f1c encerrado...
  ├─ Close_Price: 123.595
  ├─ Duration: 60 segundos (12 candles M5)
  ├─ Peak_PnL: +150 pontos
  ├─ Final_PnL: -5 pontos (touch & go)
  ├─ Outcome: WHIPSAW (movimentou para cima, depois retraiu)
  └─ Razão encerramento: Modelo detectou reversão, sinal encerrado

[AC1-ARCHIVED] Sinal armazenado para Camada 3 Learning...
  ├─ signal_id: d4a82f1c-3e91-4f22-9c2e-7b4a8d2e5c1f
  ├─ status: ARCHIVED
  ├─ outcome_type: WHIPSAW
  ├─ outcome_pnl: -5 pontos
  ├─ days_open: 0.001 (1 minuto)
  └─ Awaiting Camada 3: Learning Feedback analysis

============================================================================
[14:25:02.000] [SUMMARY-AC1] Primeira hora de operacao
============================================================================

[AC1-METRICS]
  ├─ Sinais gerados: 8
  ├─ Sinais WINNING: 5 (62.5%)
  ├─ Sinais WHIPSAW: 2 (25%)
  ├─ Sinais MISSED_OPPORTUNITY: 1 (12.5%)
  ├─ Average_Duration: 45s
  ├─ Max_PnL: +150 pontos
  ├─ Min_PnL: -45 pontos
  └─ Outcome_Distribution:
     ├─ WINNING_SIGNAL: 62.5%
     ├─ WHIPSAW: 25%
     └─ MISSED_OPPORTUNITY: 12.5%

[AC1-PERSISTENCE] Status DB
  ├─ Table: signals
  ├─ Total registered: 8
  ├─ With market_context: 8 (100%)
  ├─ Ready for Camada 2: 8
  └─ Awaiting Camada 3: 8

"""

# ============================================================================
# EXEMPLO 3: INTEGRATION WITH INICIAR_MICRO_TENDENCIA_AUTO_TRADE.bat
# ============================================================================

LOG_BAT_INTEGRATION = """
============================================================================
[14:23:00] INICIAR_MICRO_TENDENCIA_AUTO_TRADE.bat v1.2.3
============================================================================

[PRE-FLIGHT] Verificando saude do sistema v1.2.3...
   [✓] Python 3.11.9 detected
   [✓] SQLite database accessible
   [✓] ML dataset loaded: 1,000 samples
   [✓] MT5 API online

[SYNC] Sincronizando operacoes MT5...
   [✓] 3 days back imported into statistics

[BDI] Aplicando licoes BDI...
   [✓] Previous day lessons loaded

[JOURNAL] Iniciando Diario RL...
   [✓] Background logger started

[GATE2] Validando GATE 2 (Backtest readiness)...
   [✓] GATE 2 PASSED - Escalando para R$ 100k

============================================================================
[14:23:45] AGENT EXECUTOR - AC1 Signal Detection Hook
============================================================================

Chamando: python scripts/agent_executor_with_ml.py --mode auto-trade

  ├─ Loading ML model: XGBoost (F1=0.68, Win Rate=62%)
  ├─ Initializing SMC detector para M5...
  ├─ Connecting to MT5 live feed...
  └─ Waiting for M5 candles...

[14:24:00] LIVE M5 CANDLE EVENT
  └─ Trigger: M5 candle closed @14:24:00

[AC1-ACTIVATION] Signal Generation Pipeline Started
  ├─ Extract M5 OHLC (open, high, low, close, volume)
  ├─ Detect SMC pattern (BOS/CHoCH/FVG)
  ├─ Calculate score [-3, +3]
  ├─ Capture market context (RSI, ATR, BB, volume, spread, trend)
  └─ Generate signal_id (UUID)

[AC1-SIGNAL-BUS] Publishing signal to Message Queue
  └─ Signal ready for Camada 2 (Decision Motor)
     └─ [DECISION-QUEUE] ENTRAR ou FICAR_DE_FORA?

============================================================================
[14:24:05] SUBSEQUENT CANDLES - AC1 Monitoring Active
============================================================================

[14:24:10] [M5-CANDLE] Signal tracking update
  ├─ Signal: d4a82f1c-3e91-4f22-9c2e-7b4a8d2e5c1f
  ├─ Current_Price: 123.620
  ├─ Signal_Price: 123.600
  ├─ P&L: +20 pontos
  └─ Status: WINNING_POTENTIAL

[14:24:15] [M5-CANDLE] Signal tracking update
  ├─ Current_Price: 123.750 (NEW HIGH)
  ├─ P&L: +150 pontos
  └─ Status: WINNING_SIGNAL

============================================================================
[14:25:00] MONITORING DASHBOARD (AC1 View)
============================================================================

┌─────────────────────────────────────────────────────────────────────────┐
│ CAMADA 1: SIGNAL GENERATION & MONITORING                               │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│ Signal_ID               │ Type │ Score │ Status        │ P&L     │ Age  │
│ d4a82f1c-3e91-4f22...  │ BUY  │ +1.50 │ WINNING       │ +150pts │ 1m   │
│ a7c3f9d2-5e71-2d...    │ SELL │ -2.00 │ WHIPSAW       │ -5pts   │ 25s  │
│ b1e4a8f3-9d82-4b...    │ BUY  │ +1.00 │ OPEN          │ +45pts  │ 8s   │
│                                                                         │
│ Signals in monitoring: 3                                               │
│ Signals completed today: 5                                             │
│ Win rate (today): 60%                                                  │
│ Average duration: 45 seconds                                           │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘

"""

# ============================================================================
# EXEMPLO 4: DETAILED SIGNAL LOG WITH ALL FIELDS (Technical Reference)
# ============================================================================

LOG_DETAILED_SIGNAL_FIELDS = """
============================================================================
[14:24:00.012] [AC1-SIGNAL-JSON] Full Signal Object (DB Insert Preview)
============================================================================

{
  "signal_id": "d4a82f1c-3e91-4f22-9c2e-7b4a8d2e5c1f",
  "timestamp": "2026-03-05T14:24:00.012Z",
  "symbol": "WIN",
  "signal_type": "BUY",
  "smc_score": 1.50,
  "smc_detector": "BOS",
  "entry_price": 123.600,
  "candle_index": 2845,
  
  "market_context": {
    "rsi": 65.5,
    "atr": 50.0,
    "bb_upper": 123.750,
    "bb_lower": 123.150,
    "volume": 450,
    "spread": 2.0,
    "trend_direction": "UP",
    "last_close": 123.450
  },
  
  "created_at": "2026-03-05T14:24:00.012Z",
  "updated_at": null,
  "outcome_type": null,
  "outcome_pnl": null,
  "outcome_days_open": null,
  "closed_at": null
}

============================================================================
[14:24:00.015] [AC1-DB-INSERT] SQL Statement Generated
============================================================================

INSERT INTO signals (
  signal_id, timestamp, symbol, signal_type, smc_score, smc_detector, 
  entry_price, candle_index, market_context_json, created_at
) VALUES (
  'd4a82f1c-3e91-4f22-9c2e-7b4a8d2e5c1f',
  '2026-03-05 14:24:00.012',
  'WIN',
  'BUY',
  1.50,
  'BOS',
  123.600,
  2845,
  '{\"rsi\":65.5,\"atr\":50.0,\"bb_upper\":123.750,\"bb_lower\":123.150,\"volume\":450,\"spread\":2.0,\"trend_direction\":\"UP\",\"last_close\":123.450}',
  '2026-03-05 14:24:00.012'
)

============================================================================
[14:25:00.000] [AC1-DB-UPDATE] Signal Closing (Outcome Known)
============================================================================

UPDATE signals SET
  outcome_type = 'WHIPSAW',
  outcome_pnl = -5.0,
  outcome_days_open = 0.001,
  closed_at = '2026-03-05 14:25:00.000',
  updated_at = '2026-03-05 14:25:00.000'
WHERE signal_id = 'd4a82f1c-3e91-4f22-9c2e-7b4a8d2e5c1f'

"""

# ============================================================================
# EXEMPLO 5: ERROR CASES & EDGE CASES (Logging)
# ============================================================================

LOG_ERROR_CASES = """
============================================================================
[AC1-ERROR SCENARIOS & HANDLING]
============================================================================

SCENARIO 1: Weak Signal Rejection
────────────────────────────────────────────────────────────────────────

[14:26:00.000] [M5-CANDLE-CLOSED] Timeframe=M5, Symbol=WIN, Index=2852

[DETECTOR] Processando candle M5...
  ├─ Open:  123.400
  ├─ Close: 123.405  (movimento muito pequeno)
  └─ Prev_High: 123.400

[AC1-DETECTOR] SMC evaluation:
  └─ Close 123.405 NOT > Prev_High 123.400 (|0.005| < 1.0)
  └─ No structure detected (BOS/CHoCH/FVG)

[AC1-REJECTED] Signal fraco (score < |1.0|)
  ├─ Reason: Movimento insuficiente para trading
  ├─ Score: 0.0 (abaixo do limite 1.0)
  └─ Status: IGNORED (not persisted to DB)

────────────────────────────────────────────────────────────────────────

SCENARIO 2: Market Context Capture with NaN Values
────────────────────────────────────────────────────────────────────────

[14:27:00.000] [MARKET-CONTEXT] RSI calculation unavailable

[AC1-CONTEXT] Capturando contexto...
  ├─ RSI(14): NaN (apenas 5 candles de historico)
  ├─ ATR(14): 45.0
  ├─ BB: OK
  ├─ Volume: OK
  ├─ Spread: OK
  ├─ Trend: OK
  └─ last_close: OK

[AC1-SIGNAL] Sinal criado mesmo com RSI=NaN
  └─ Reasoning: 7/8 contexto fields preenchidos (87.5%)
  └─ MarketContext(rsi=None, atr=45.0, ...)

────────────────────────────────────────────────────────────────────────

SCENARIO 3: Duplicate Signal Rejection (Same conditions)
────────────────────────────────────────────────────────────────────────

[14:28:00.000] [M5-CANDLE-CLOSED] Timeframe=M5, Index=2854

[AC1-SIGNAL] BOS detectado (score=+1.50)
  └─ signal_id: 9f7c2e1a-4b65-3d82-1e9f-8c4a2d5e7b3f (UNIQUE)

[14:28:05.000] [M5-CANDLE-CLOSED] Timeframe=M5, Index=2855

[DETECTOR] Processando candle M5...
  ├─ Mesma estrutura BOS
  ├─ Score: +1.50
  └─ [AC1-SIGNAL] signal_id: 0a8d3f2b-5c76-4e93-2f0a-9d5b3e6f8c4a (UNIQUE!)

[DB-CONSTRAINT] UNIQUE(timestamp, symbol, signal_type, smc_score)
  └─ Constraint prevents exact duplicates
  └─ But different signal_ids track different instances

────────────────────────────────────────────────────────────────────────

SCENARIO 4: Edge Case - Exact same price but different context
────────────────────────────────────────────────────────────────────────

[14:29:00.000] SINAL 1: BOS @ 123.600
  │
  ├─ RSI: 65.5 (overbought)
  ├─ Volume: 450 (alta)
  ├─ ATR: 50.0
  └─ signal_id: A123 → CREATED

[14:29:20.000] SINAL 2: BOS @ 123.600
  │
  ├─ RSI: 45.0 (neutral)
  ├─ Volume: 100 (baixa)
  ├─ ATR: 20.0
  └─ signal_id: B456 → CREATED (different context!)

[AC1-CONTEXT-CAPTURE] Ambos sinais salvos com market_context_json distinto
  │
  ├─ Signal A: market_context = {...,\"rsi\":65.5,\"volume\":450,...}
  ├─ Signal B: market_context = {...,\"rsi\":45.0,\"volume\":100,...}
  │
  └─ Learning (Camada 3): Pode comparar resultados
      ├─ Sinal com contexto forte (RSI overbought): +150 pnl (sorte?)
      ├─ Sinal com contexto fraco (RSI neutral): -5 pnl
      └─ Conclusão: contexto importa para aprendizado!

"""

if __name__ == "__main__":
    print(__doc__)
    print(LOG_SIGNAL_GENERATION)
    print(LOG_SIGNAL_MONITORING)
    print(LOG_BAT_INTEGRATION)
    print(LOG_DETAILED_SIGNAL_FIELDS)
    print(LOG_ERROR_CASES)

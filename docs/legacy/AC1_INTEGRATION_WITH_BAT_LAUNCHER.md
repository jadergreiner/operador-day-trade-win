"""
AC1 SIGNAL GENERATION - INTEGRAÇÃO COM INICIAR_MICRO_TENDENCIA_AUTO_TRADE.bat

Demonstração de como o signal detection (AC1) seria ativado e exibido
quando você executa o launcher do operador automático.

Reference: INICIAR_MICRO_TENDENCIA_AUTO_TRADE.bat
           AC1 Implementation: tests/test_camada1_ac1_signal_generation.py
Date: 05/03/2026
"""

# ============================================================================
# FLUXO EXECUTIVO: BAT → Python Agent → AC1 Signal Detection
# ============================================================================

FLUXO_EXECUTIVO = """

┌─────────────────────────────────────────────────────────────────────┐
│ 1. USER LAUNCHES: INICIAR_MICRO_TENDENCIA_AUTO_TRADE.bat           │
└─────────────────────────────────────────────────────────────────────┘
                                ↓
        [Batch file: Pre-flight checks, BDI, ML sync]
                                ↓
┌─────────────────────────────────────────────────────────────────────┐
│ 2. BATCH CALLS: python scripts/agent_executor_with_ml.py           │
│    Command: python scripts/agent_executor_with_ml.py               │
│             --mode auto-trade --symbol WIN --timeframe M5          │
└─────────────────────────────────────────────────────────────────────┘
                                ↓
        [Python agent initializes with ML model + MT5 live feed]
                                ↓
┌─────────────────────────────────────────────────────────────────────┐
│ 3. AC1 INITIALIZATION: SignalGenerator.detect_smc()                │
│    ├─ Load market data (live M5 candles from MT5)                  │
│    └─ Monitor ogni M5 candle close event                           │
└─────────────────────────────────────────────────────────────────────┘
                                ↓
┌─────────────────────────────────────────────────────────────────────┐
│ 4. LIVE SIGNAL DETECTION: M5 Candle Closed = Signal Check          │
│    Every 5 minutes:                                                 │
│    ├─ Check SMC pattern (BOS/CHoCH/FVG)                           │
│    ├─ Calculate score [-3, +3]                                     │
│    ├─ Capture market context                                       │
│    └─ Generate signal_id (UUID)                                    │
└─────────────────────────────────────────────────────────────────────┘
                                ↓
        [Signal generated OR rejected if score < |1.0|]
                                ↓
┌─────────────────────────────────────────────────────────────────────┐
│ 5. SIGNAL PERSISTENCE & MONITORING: DB + Tracking                  │
│    ├─ INSERT signal into DB (tabela signals)                       │
│    ├─ Capture market_context_json (RSI, ATR, BB, etc)              │
│    └─ Track until signal resolves (WINNING/WHIPSAW/MISSED)        │
└─────────────────────────────────────────────────────────────────────┘
                                ↓
┌─────────────────────────────────────────────────────────────────────┐
│ 6. NEXT LAYERS: Signal → Camada 2 (Decision) → Camada 3 (Learning)│
│    [AC2-AC3 not yet implemented, but signal ready]                 │
└─────────────────────────────────────────────────────────────────────┘

"""


# ============================================================================
# CONSOLE OUTPUT: WHAT YOU WOULD SEE WHEN RUNNING
# ============================================================================

CONSOLE_OUTPUT = """

C:\\repo\\operador-day-trade-win> INICIAR_MICRO_TENDENCIA_AUTO_TRADE.bat

============================================================================
                  OPERADOR MICRO TENDENCIA - v1.2.3
                    Day Trade Automation Framework
                         [05/03/2026 14:23:00]
============================================================================

[PRE-FLIGHT] Verificando saude do sistema v1.2.3...
   ✓ Python 3.11.9 detected
   ✓ SQLite database accessible: data/db/trading.db (45.2 MB)
   ✓ ML model loaded: XGBoost v1.2.3 (F1=0.68, Win=62%)
   ✓ MT5 Connection: Connected to account 1234567 (DEMO)

[SYNC] Sincronizando operacoes MT5...
   ✓ 3 days back imported (45 trades synchronized)

[BDI] Aplicando licoes BDI...
   ✓ Previous day lessons loaded (8 rules applied)

[JOURNAL] Iniciando Diario RL em background...
   ✓ Journal logger active on port 5000

[GATE2] Validando GATE 2 (Backtest readiness)...
   ✓ GATE 2 PASSED - Escalando para R$ 100k

============================================================================
[14:23:45] Starting Agent Executor with AC1 Signal Detection...
============================================================================

   Calling: python scripts/agent_executor_with_ml.py
   Mode: auto-trade
   Symbols: WIN, WDO
   Timeframe: M5
   Capital: R$ 100.000

   [✓] ML model initialized (XGBoost)
   [✓] MT5 API connected (live feed)
   [✓] Signal detector ready (AC1 - BOS/CHoCH/FVG)
   [✓] Market context capture enabled
   [✓] Database connection active

============================================================================
[14:24:00] *** LIVE SIGNAL DETECTION ACTIVE ***
============================================================================

   Waiting for M5 candle close events...
   └─ Monitoring: WIN, WDO
   └─ Target: Comprar em BOS/CHoCH (score > +1.0) ou Vender (score < -1.0)

[-----] M5 candles waiting... [-----]

[14:24:00] [M5-CANDLE-CLOSED] WIN - Candle Index #2845

   Processing M5 candle...
   ├─ Open:   123.450
   ├─ High:   123.650
   ├─ Low:    123.250
   ├─ Close:  123.600  ← Current price
   ├─ Volume: 450 contratos
   └─ Duration: Last 5 minutes (M5)

   [DETECTOR] Checking SMC patterns...

      BOS Check: Close 123.600 > Prev_High 123.450? → YES ✓
      ├─ Bullish Break of Structure detected!
      ├─ Score: +1.50 (range: [-3, +3])
      └─ Signal Type: BUY

   [MARKET-CONTEXT] Capturing market indicators...

      └─ RSI(14): 65.5 (⚠️  overbought zone)
      └─ ATR(14): 50.0 pontos
      └─ Bollinger: Upper=123.750, Lower=123.150
      └─ Volume: 450 (130% normal average)
      └─ Spread: 2.0 pontos
      └─ Trend: UP (5 candles consecutivas)
      └─ Last_Close: 123.450

   [✓] AC1-SIGNAL GENERATED & READY FOR PERSISTENCE

      signal_id:           d4a82f1c-3e91-4f22-9c2e-7b4a8d2e5c1f
      timestamp:           2026-03-05 14:24:00.012
      symbol:              WIN
      signal_type:         BUY
      smc_score:           +1.50
      smc_detector:        BOS
      entry_price:         123.600
      candle_index:        2845
      ────────────────────────────────────────
      market_context:      CAPTURED (8 fields)
      ────────────────────────────────────────

   [✓] PERSISTING TO DATABASE...
      Table: signals
      Status: INSERTED successfully
      Market context JSON: 267 bytes

   [✓] SIGNAL TRACKING STARTED
      ├─ Monitoring price movement
      ├─ Current P&L: 0 (just generated)
      └─ Awaiting next M5 candle

[14:25:00] [M5-CANDLE-CLOSED] WIN - Candle Index #2846

   [AC1-TRACKING] Signal d4a82f1c update...
   ├─ Current Price: 123.620
   ├─ Price chg: +20 pontos desde sinal
   ├─ High peak: 123.750 (1:30 atrás)
   ├─ P&L if entered: +20 pontos (current)
   ├─ P&L max: +150 pontos
   └─ Status: WINNING_POTENTIAL ⭐

[14:25:05] [M5-CANDLE-CLOSED] WDO - Candle Index #1523

   Processing M5 candle...
   ├─ Open:   45.320
   ├─ Close:  45.325  ← Movement too small
   ├─ Volume: 80 contratos

   [DETECTOR] Checking SMC patterns...
      └─ No structure detected (close NOT > prev_high OR < prev_low)
      └─ Score would be: 0.0 (< 1.0 minimum)

   [AC1-REJECTED] Signal too weak
      └─ Reason: Insufficient movement for trading
      └─ No entry created (expected: false signal rejection)

[14:25:30] [M5-CANDLE-CLOSED] WIN - Candle Index #2847

   [AC1-TRACKING] Signal d4a82f1c update...
   ├─ Current Price: 123.750 (NEW HIGH!)
   ├─ P&L if entered: +150 pontos ✓
   └─ Status: WINNING_SIGNAL 🎯

[14:26:00] [M5-CANDLE-CLOSED] WIN - Candle Index #2848

   [AC1-TRACKING] Signal d4a82f1c update...
   ├─ Current Price: 123.680
   ├─ High reached: 123.750 (descending now)
   ├─ P&L current: +80 pontos
   └─ Status: WINNING (consolidating)

[14:26:30] [M5-CANDLE-CLOSED] WIN - Candle Index #2849

   [AC1-TRACKING] Signal d4a82f1c final update...
   ├─ Current Price: 123.595
   ├─ Duration: 90 segundos
   ├─ Final P&L: -5 pontos
   ├─ Peak P&L: +150 pontos
   └─ Outcome: WHIPSAW 📊

   [✓] SIGNAL ARCHIVED
      ├─ outcome_type: WHIPSAW
      ├─ outcome_pnl: -5.0
      ├─ days_open: 0.0015
      └─ Status: Ready for Camada 3 Learning Feedback

============================================================================
[14:27:00] *** AC1 SUMMARY - FIRST HOUR ***
============================================================================

   Signals Generated: 8
   ├─ WINNING_SIGNAL: 5 (62.5% - as expected)
   ├─ WHIPSAW: 2 (25% - natural volatility)
   └─ MISSED_OPPORTUNITY: 1 (12.5%)

   Average Duration: 45 segundos
   Max P&L: +150 pontos
   Min P&L: -45 pontos

   Database Status:
   ├─ Signals inserted: 8
   ├─ Market context captured: 100%
   └─ Ready for Camada 2 Decision Motor: 8

   [✓] AC1 Signal Generation Operating Normally

============================================================================

   [Continuing to monitor M5 candles...]
   [Ready to accept manual commands via OPERADOR.bat interface]
   [Press Ctrl+C to stop]

"""


# ============================================================================
# EXAMPLE: HOW TO MONITOR LOGS IN REAL-TIME
# ============================================================================

MONITORING_GUIDE = """

============================================================================
COMO MONITORAR SINAIS AO VIVO (Real-time Monitoring)
============================================================================

OPÇÃO 1: Ver logs em tempo real (novo terminal)
──────────────────────────────────────────────────────────────────────────

   C:\\repo\\operador-day-trade-win> python scripts/monitor_signals_live.py

   Exibe:
   ├─ Sinais gerados nos últimos 30 minutos
   ├─ P&L de cada sinal
   ├─ Status: WINNING/WHIPSAW/OPEN
   ├─ Atualização a cada M5 candle close (5 segundos)
   └─ Gráfico ASCII simples do movimento

OPÇÃO 2: Ver banco de dados diretamente
──────────────────────────────────────────────────────────────────────────

   C:\\repo\\operador-day-trade-win> python
   >>> import sqlite3
   >>> conn = sqlite3.connect('data/db/trading.db')
   >>> cursor = conn.cursor()
   >>> cursor.execute("SELECT signal_id, signal_type, smc_score, entry_price, \\
   ...                outcome_pnl, outcome_type FROM signals \\
   ...                ORDER BY timestamp DESC LIMIT 10")
   >>> for row in cursor.fetchall():
   ...     print(f"{row[0][:8]}... {row[1]:4s} Score:{row[2]:+.1f} \\
   ...            PnL:{row[4]:+.0f} Outcome:{row[5]}")

OPÇÃO 3: Web Dashboard (quando implementado)
──────────────────────────────────────────────────────────────────────────

   http://localhost:5000/dashboard/signals

   Display:
   ├─ Live candle chart com sinais marcados
   ├─ Tabela de sinais recentes
   ├─ Estatísticas em tempo real
   └─ Market context (RSI, ATR, BB)

OPÇÃO 4: Log file parsing
──────────────────────────────────────────────────────────────────────────

   C:\\repo\\operador-day-trade-win> python scripts/parse_signal_logs.py \\
                                        --time-window 1h \\
                                        --output-format json

   Output: signal_logs_2026-03-05_14h.json
   ├─ Structured JSON com todos sinais da última hora
   ├─ Fácil análise com pandas/matplotlib
   └─ Pronto para upload em reports

"""


# ============================================================================
# DATABASE QUERY CHEAT SHEET: AC1 Signals
# ============================================================================

QUERY_CHEATSHEET = """

============================================================================
DATABASE QUERIES: AC1 SIGNAL MONITORING
============================================================================

1. ÚLTIMOS 10 SINAIS GERADOS
───────────────────────────────────────────────────────────────────────

SELECT
  signal_id,
  timestamp,
  symbol,
  signal_type,
  smc_score,
  smc_detector,
  entry_price,
  outcome_pnl,
  outcome_type
FROM signals
ORDER BY timestamp DESC
LIMIT 10;

Resultado esperado:
┌─────────────────────────────────────────────────────────────────┐
│ signal_id     │ timestamp            │ signal │ score │ outcome  │
├─────────────────────────────────────────────────────────────────┤
│ d4a82f1c-... │ 2026-03-05 14:26:30 │ BUY   │ +1.50 │ WHIPSAW  │
│ a7c3f9d2-... │ 2026-03-05 14:25:00 │ SELL  │ -2.00 │ WINNING  │
│ b1e4a8f3-... │ 2026-03-05 14:24:00 │ BUY   │ +1.50 │ WINNING  │
└─────────────────────────────────────────────────────────────────┘


2. SINAIS POR TIPO DE DETECTOR (SMC Pattern)
───────────────────────────────────────────────────────────────────────

SELECT
  smc_detector,
  COUNT(*) as count,
  AVG(CASE WHEN outcome_pnl > 0 THEN 1 ELSE 0 END) as win_rate,
  AVG(ABS(outcome_pnl)) as avg_pnl
FROM signals
WHERE outcome_pnl IS NOT NULL
GROUP BY smc_detector;

Resultado esperado:
┌───────────┬───────┬─────────┬──────────┐
│ detector  │ count │ win_rate│ avg_pnl  │
├───────────┼───────┼─────────┼──────────┤
│ BOS       │ 45    │ 62%     │ +45pts   │
│ CHOCH     │ 12    │ 75%     │ +65pts   │
│ FVG       │ 8     │ 50%     │ +20pts   │
└───────────┴───────┴─────────┴──────────┘


3. SINAIS ABERTOS (AINDA SENDO MONITORADOS)
───────────────────────────────────────────────────────────────────────

SELECT
  signal_id,
  timestamp,
  symbol,
  signal_type,
  smc_score,
  entry_price,
  strftime('%M:%S', 'now') - strftime('%M:%S', timestamp) as duration_sec
FROM signals
WHERE outcome_type IS NULL OR outcome_type = 'OPEN'
ORDER BY timestamp DESC;

Resultado esperado:
┌─────────────────────────────────────────────────────────────────┐
│ Sinais ainda abertos (outcome_type = NULL)                      │
│ b1e4a8f3-... │ 2026-03-05 14:29:45 │ GBP │ +1.50 │ 5s  │
│ c2f5b9g4-... │ 2026-03-05 14:28:30 │ RDI │ -1.00 │ 20s │
└─────────────────────────────────────────────────────────────────┘


4. MARKET CONTEXT ANALYSIS (RSI, ATR, etc)
───────────────────────────────────────────────────────────────────────

SELECT
  symbol,
  AVG(json_extract(market_context_json, '$.rsi')) as avg_rsi,
  AVG(json_extract(market_context_json, '$.atr')) as avg_atr,
  AVG(json_extract(market_context_json, '$.volume')) as avg_volume
FROM signals
GROUP BY symbol;

Resultado esperado:
┌─────────┬──────────┬──────────┬────────────┐
│ symbol  │ avg_rsi  │ avg_atr  │ avg_volume │
├─────────┼──────────┼──────────┼────────────┤
│ WIN     │ 58.5     │ 48.2     │ 385        │
│ WDO     │ 52.3     │ 35.1     │ 220        │
└─────────┴──────────┴──────────┴────────────┘


5. ESTATÍSTICAS DO DIA
───────────────────────────────────────────────────────────────────────

SELECT
  DATE(timestamp) as date,
  COUNT(*) as total_signals,
  SUM(CASE WHEN outcome_pnl > 0 THEN 1 ELSE 0 END) as winners,
  ROUND(100.0 * SUM(CASE WHEN outcome_pnl > 0 THEN 1 ELSE 0 END) /
        COUNT(*), 1) as win_rate_pct,
  SUM(outcome_pnl) as total_pnl
FROM signals
WHERE outcome_pnl IS NOT NULL
GROUP BY DATE(timestamp);

Resultado esperado:
┌────────────┬────────────┬───────┬──────────┬────────────┐
│ date       │ total_sig  │ winners│ win_rate │ total_pnl  │
├────────────┼────────────┼───────┼──────────┼────────────┤
│ 2026-03-05 │ 24         │ 15    │ 62.5%    │ +240pts    │
│ 2026-03-04 │ 18         │ 11    │ 61.1%    │ +185pts    │
└────────────┴────────────┴───────┴──────────┴────────────┘

"""

if __name__ == "__main__":
    print(__doc__)
    print(FLUXO_EXECUTIVO)
    print(CONSOLE_OUTPUT)
    print(MONITORING_GUIDE)
    print(QUERY_CHEATSHEET)

# ADR-010: Causal Feedback Loop for Continuous RL Learning

**Status:** PROPOSED (05/03/2026)
**Author:** Architecture Team
**Type:** Framework Design - Critical for Model Improvement

---

## CONTEXT

**Current State:**
- Model makes enter/hold decisions based on confidence + technical signals
- Feedback is simple: Win Rate (trades won / trades total)
- Problem: Model learns CORRELATIONS not CAUSATION
  - Example: Model enters on RSI > 70 and wins 60% of time
  - But actual cause might be "market rallying hard" not "RSI > 70"
  - If market conditions change, RSI still > 70 but win rate drops

**Desired State:**
Structured loop that captures:
1. **Signal Detection** (opportunity identified)
2. **Decision Reasoning** (why enter or why hold)
3. **Signal Evolution** (what happened to opportunity)
4. **Outcome** (profit/loss and how closed)
5. **Post-Mortem Analysis** (was decision correct for RIGHT reasons?)
6. **Causal Learning** (update model with ROOT CAUSE not correlation)

---

## DECISION

Implement **7-Step Causal Feedback Loop** with persistent context at each step:

```
Step 1: SIGNAL DETECTION
  ↓ [Persist: signal_id, conditions, parameters, timestamp]
Step 2: DECISION + REASONING
  ↓ [Persist: decision, confidence, reasoning_factors, threshold_values]
Step 3: SIGNAL MONITORING
  ↓ [Persist: evolution log, parameter drift, market regime changes]
Step 4: SIGNAL CLOSURE
  ↓ [Persist: outcome (win/loss/timeout), exit_reason, final_conditions]
Step 5: FIRST-LEVEL ANALYSIS
  ↓ [Persist: was_entry_decision_correct?, was_hold_decision_correct?]
Step 6: CAUSAL ANALYSIS
  ↓ [Persist: were_market_conditions_at_END same as detected_at_START?]
Step 7: ROOT CAUSE LEARNING
  ↓ [Update model: causal_weight not correlation_weight]
```

---

## RATIONALE

### Why This Matters

**Example: Entry on RSI > 70 (Overbought Signal)**

#### Current Loop (Correlation Only):

```
Signal detected: RSI > 70, Price = 187.500
Decision: ENTER (confidence = 0.72)
Outcome: Win (P&L = +R$ 450)
Learning: "RSI > 70 → +0.02 confidence"

Problem: Next time RSI > 70:
  - Market conditions completely different
  - But model still enters → loses R$ 300
```

#### Proposed Loop (Causal):

```
Signal detected: RSI > 70, Price = 187.500
  [PERSIST CONDITIONS: volatility=2.1%, trend=UP, volume_vs_avg=+45%]

Decision: ENTER (confidence = 0.72)
  [PERSIST REASONING: "RSI > 70 + UPTREND consensus signaling"]

Monitoring: RSI stays 70-75, Price holds
  [PERSIST LOG: no drift, conditions stable, up +0.8%]

Closure: Price +1.2%, EXIT on TP
  [PERSIST OUTCOME: PROFIT R$ 450, exit_reason=TP_HIT]

First-Level: Was ENTRY correct? YES ✓ (Made money)

Causal Analysis: Were market conditions at END same as at START?
  [Check: volatility=2.1% (same) ✓, trend=UP (same) ✓, volume_high (same) ✓]
  [Conclusion: Market conditions STABLE → Decision was FUNDAMENTALLY SOUND]

Root Cause Learning:
  "RSI > 70 + STABLE_UPTREND + HIGH_VOLUME → +0.04 confidence" (stronger)
  (Not just "RSI > 70 → +0.02")

Next scenario: RSI > 70 but SIDEWAYS trend
  [Model enters with LOWER confidence because conditions don't match]
```

### Why This Prevents False Learning

**Scenario: Lucky Guess**

```
Signal: RSI > 70 (but actually just noise)
Decision: ENTER (confidence = 0.50)
Outcome: Price rallies 2% due to macro news (NOT because of RSI)
  → Trade wins
First-Level: YES, made money ✓
Causal Analysis: RSI > 70 (detected) but price move driven by macro news (not RSI)
  → Market conditions changed DURING signal
Root Cause: Learn NOTHING from RSI because correlation was SPURIOUS
```

---

## DATA MODEL

### 1. Signal Table (signals.db)

```json
{
  "signal_id": "SIG_20260305_123045_001",
  "timestamp_detection": "2026-03-05T12:30:45Z",
  "symbol": "WINM26",
  "signal_type": "MICRO_TENDENCIA",
  "technical_factors": {
    "rsi_14": 72.5,
    "bbands_upper": 187.890,
    "bbands_lower": 187.120,
    "atr_14": 0.380,
    "close": 187.685
  },
  "market_conditions": {
    "volatility_atr_20d": 2.1,
    "trend_ema9_vs_ema21": "UP",
    "volume_vs_avg_20d": 1.45,
    "bid_ask_spread": 0.010,
    "book_depth_10_contract": 450,
    "news_sentiment": "neutral"
  },
  "macro_context": {
    "dollar_index": 98.81,
    "vix_level": 21.15,
    "selic_rate": 15.00,
    "embi_spread": 285,
    "market_regime": "trending_up"
  },
  "status": "OPEN"
}
```

### 2. Decision Table (decisions.db)

```json
{
  "decision_id": "DEC_20260305_123100_001",
  "signal_id": "SIG_20260305_123045_001",
  "timestamp_decision": "2026-03-05T12:31:00Z",
  "decision": "ENTER",
  "entry_type": "BUY",
  "confidence": 0.72,
  "reasoning": {
    "primary_factors": [
      "RSI > 70 (overbought reversal)",
      "Price at upper Bollinger Band",
      "Strong 20-day volume"
    ],
    "threshold_values": {
      "rsi_threshold": 70.0,
      "actual_rsi": 72.5,
      "confidence_threshold": 0.65,
      "actual_confidence": 0.72
    },
    "risk_assessment": {
      "stop_loss_price": 187.300,
      "stop_loss_pips": 3.85,
      "take_profit_price": 188.500,
      "take_profit_pips": 8.15,
      "risk_reward_ratio": 2.12
    }
  },
  "market_regime_match": {
    "expected_regime": "trending_up",
    "actual_regime": "trending_up",
    "match_score": 1.0
  },
  "status": "PENDING_EXECUTION"
}
```

### 3. Monitoring Log (monitoring_logs.db)

```json
{
  "monitoring_id": "MON_20260305_123045_001",
  "signal_id": "SIG_20260305_123045_001",
  "timestamp": "2026-03-05T12:35:00Z",
  "price_current": 187.720,
  "signal_evolution": {
    "rsi_current": 71.2,
    "rsi_trend": "stable",
    "bbands_position": "inside_upper_band",
    "trend_status": "UP (still)",
    "volume_vs_avg": 1.42
  },
  "market_conditions_current": {
    "volatility_atr_current": 2.08,
    "volatility_drift": "stable",
    "trend_status": "UP (unchanged)",
    "volume_status": "high (unchanged)",
    "news_sentiment": "neutral (unchanged)"
  },
  "drift_detection": {
    "conditions_drifted": false,
    "drift_severity": 0.0,
    "alerts": []
  },
  "log_note": "Signal conditions STABLE. Price +0.35c (+0.19%). No risk factors."
}
```

### 4. Closure Record (closures.db)

```json
{
  "closure_id": "CLS_20260305_123045_001",
  "signal_id": "SIG_20260305_123045_001",
  "decision_id": "DEC_20260305_123100_001",
  "timestamp_closure": "2026-03-05T12:47:12Z",
  "price_closure": 188.500,
  "outcome": {
    "pnl_points": 8.15,
    "pnl_reais": 450,
    "pnl_percent": 0.43,
    "exit_type": "TAKE_PROFIT_HIT",
    "exit_reason": "Price reached TP at 188.500"
  },
  "market_conditions_at_closure": {
    "rsi_at_closure": 68.5,
    "volatility_atr_at_closure": 2.12,
    "trend_status_at_closure": "UP",
    "volume_at_closure": 1.38,
    "bid_ask_spread_at_closure": 0.015,
    "news_sentiment_at_closure": "neutral"
  },
  "signal_lifetime": {
    "detected_at": "2026-03-05T12:30:45Z",
    "closed_at": "2026-03-05T12:47:12Z",
    "lifetime_minutes": 16.45,
    "price_movement_detection_to_closure": 0.815
  },
  "status": "CLOSED_PROFIT"
}
```

### 5. Analysis Record (analysis.db)

```json
{
  "analysis_id": "ANA_20260305_123045_001",
  "signal_id": "SIG_20260305_123045_001",
  "closure_id": "CLS_20260305_123045_001",

  "level_1_decision_correctness": {
    "entry_decision_was_correct": true,
    "entry_pnl": 450,
    "entry_was_profitable": true,
    "explanation": "Decision to ENTER yielded profit. Decision correctness: YES ✓"
  },

  "level_2_causal_analysis": {
    "market_conditions_comparable": {
      "volatility_change": {
        "at_detection": 2.1,
        "at_closure": 2.12,
        "drift_percent": 0.95,
        "comparable": true
      },
      "trend_consistency": {
        "at_detection": "UP",
        "at_closure": "UP",
        "drift_severity": 0.0,
        "comparable": true
      },
      "volume_consistency": {
        "at_detection": 1.45,
        "at_closure": 1.38,
        "drift_percent": 4.8,
        "comparable": true
      },
      "overall_market_stability": true,
      "regime_match_score": 0.96
    },

    "decision_was_fundamentally_sound": true,
    "causation_vs_correlation": {
      "factor_rsi_overbought": {
        "present_at_detection": true,
        "caused_profit": true,
        "confidence": "HIGH",
        "reasoning": "RSI reversal + stable conditions = valid signal"
      },
      "factor_volume_high": {
        "present_at_detection": true,
        "contributed_to_profit": true,
        "confidence": "MEDIUM",
        "reasoning": "High volume confirmed reversal momentum"
      },
      "primary_cause": "RSI > 70 (overbought reversal) in stable UP trend",
      "secondary_cause": "High volume confirming entry",
      "spurious_factors": "none detected"
    }
  },

  "root_cause_learning_update": {
    "original_rule": "RSI > 70 → +0.02 confidence",
    "refined_rule": "RSI > 70 + UPTREND + HIGH_VOLUME + STABLE_VOLATILITY → +0.04 confidence",
    "learning_weight": 0.04,
    "confidence_update": "+0.02 (base) +0.02 (causal confirmation)",
    "conditions_required": [
      "RSI > 70",
      "Trend = UP",
      "Volume > 1.3x average",
      "Volatility change < 5%"
    ]
  },

  "timestamp_analysis": "2026-03-05T12:50:00Z"
}
```

---

## WORKFLOW (7-STEP LOOP)

### Step 1: Signal Detection

```python
@dataclass
class SignalDetected:
    signal_id: str
    timestamp: datetime
    symbol: str
    technical_factors: dict  # RSI, Bollinger, ATR, etc
    market_conditions: dict  # Volatility, Trend, Volume, News
    macro_context: dict     # Dollar, VIX, Selic, EMBI, Regime

    def persist(self):
        """Save to signals.db"""
        save_to_sqlite("signals.db", self)
        logger.info(f"✓ Signal detected and persisted: {self.signal_id}")
```

**Example Output:**

```
[12:30:45] Signal SIG_20260305_123045_001 detected
  Technical: RSI=72.5, BB_Upper=187.89, ATR=0.38
  Market: Volatility=2.1%, Trend=UP, Volume=+45%
  Macro: Dollar=98.81, VIX=21.15, Regime=trending_up
  ✓ Persisted
```

### Step 2: Decision + Reasoning

```python
@dataclass
class DecisionMade:
    decision_id: str
    signal_id: str
    decision: str  # "ENTER" or "HOLD"
    confidence: float
    reasoning: dict
    threshold_values: dict
    risk_assessment: dict

    def persist(self):
        """Save to decisions.db"""
        save_to_sqlite("decisions.db", self)
        logger.info(f"✓ Decision {self.decision} with {self.confidence:.0%} confidence")
```

**Example Output:**

```
[12:31:00] Decision: ENTER with 72% confidence
  Reasoning:
    - RSI > 70 (overbought reversal) ✓
    - Price at upper Bollinger Band ✓
    - 20-day volume high ✓
  Risk: SL=187.30 (-3.85p), TP=188.50 (+8.15p), R:R=2.12
  ✓ Persisted
```

### Step 3: Signal Monitoring (Continuous)

```python
@dataclass
class SignalMonitoring:
    monitoring_id: str
    signal_id: str
    timestamp: datetime
    price_current: float
    signal_evolution: dict  # RSI trend, BB position, etc
    market_conditions_current: dict
    drift_detection: dict  # Are conditions changing?

    def persist(self):
        """Save to monitoring_logs.db"""
        save_to_sqlite("monitoring_logs.db", self)
```

**Example Outputs (every 1-5 minutes):**

```
[12:35:00] Monitoring SIG_20260305_123045_001
  Price: 187.720 (+0.035 from detection)
  Signal: RSI=71.2 (stable), BB inside upper band (stable)
  Market: Volatility=2.08% (stable), Trend=UP (stable), Volume=1.42 (stable)
  Drift: NO - Conditions stable ✓
  Note: Signal conditions STABLE. Price +0.19%. No risk factors.

[12:40:00] Monitoring SIG_20260305_123045_001
  Price: 188.100 (+0.415 from detection)
  Signal: RSI=69.8 (declining), BB inside upper band
  Market: Volatility=2.15% (slight increase), Trend=UP (stable), Volume=1.40 (stable)
  Drift: MINOR - Volatility +2.4%, RSI declining slightly (normal for reversal)
  Note: Minor drift detected but within normal parameters. Signal still valid.
```

### Step 4: Signal Closure

```python
@dataclass
class SignalClosure:
    closure_id: str
    signal_id: str
    decision_id: str
    timestamp_closure: datetime
    price_closure: float
    outcome: dict  # PNL, exit_type, exit_reason
    market_conditions_at_closure: dict  # CRITICAL: Capture final conditions
    signal_lifetime: dict

    def persist(self):
        """Save to closures.db"""
        save_to_sqlite("closures.db", self)
        logger.info(f"✓ Signal {self.signal_id} CLOSED")
        logger.info(f"  Outcome: {self.outcome['pnl_reais']:.0f}R$ ({self.outcome['exit_reason']})")
```

**Example Output:**

```
[12:47:12] Signal SIG_20260305_123045_001 CLOSED
  Price Closure: 188.500 (TP_HIT)
  P&L: +R$ 450 (15 pips)
  Duration: 16.45 min

  FINAL MARKET CONDITIONS (Critical for causal analysis):
    RSI at closure: 68.5
    Volatility at closure: 2.12%
    Trend at closure: UP
    Volume at closure: 1.38x avg
    News sentiment: neutral (unchanged)
  ✓ Persisted
```

### Step 5: First-Level Decision Correctness

```python
@dataclass
class DecisionCorrectnessAnalysis:
    analysis_id: str
    signal_id: str
    closure_id: str

    entry_decision_was_correct: bool  # Did we profit?
    entry_pnl: float
    explanation: str

    def analyze(self):
        closure = load_closure(self.signal_id)
        self.entry_pnl = closure.outcome['pnl_reais']
        self.entry_decision_was_correct = self.entry_pnl > 0

        if self.entry_decision_was_correct:
            self.explanation = f"Decision to ENTER yielded +R${self.entry_pnl}. CORRECT ✓"
        else:
            self.explanation = f"Decision to ENTER yielded -R${abs(self.entry_pnl)}. INCORRECT ✗"

        self.persist()
```

**Example Output:**

```
[12:50:00] Analysis LEVEL 1: Decision Correctness
  Signal SIG_20260305_123045_001
  Decision: ENTER ✓
  Outcome: +R$ 450 (PROFIT)
  Analysis: Was ENTER decision correct? YES ✓

  Could we have made more if we held longer?
    → Price continued UP to 189.50 (not evaluated here)
    → But TP was hit first, objective met
```

### Step 6: Causal Analysis (Market Conditions)

```python
@dataclass
class CausalAnalysis:
    market_conditions_comparable: bool
    conditions_drift_score: float  # 0=identical, 1=completely different
    decision_was_fundamentally_sound: bool

    def analyze(self):
        signal = load_signal(self.signal_id)
        closure = load_closure(self.signal_id)

        # Compare conditions at detection vs closure
        volatility_drift = abs(
            signal.market_conditions['volatility'] -
            closure.market_conditions_at_closure['volatility']
        ) / signal.market_conditions['volatility']

        trend_match = (
            signal.market_conditions['trend'] ==
            closure.market_conditions_at_closure['trend']
        )

        volume_drift = abs(
            signal.market_conditions['volume_vs_avg'] -
            closure.market_conditions_at_closure['volume_vs_avg']
        ) / signal.market_conditions['volume_vs_avg']

        # Decision is fundamentally sound if conditions stayed similar
        self.market_conditions_comparable = (
            volatility_drift < 0.10 and
            trend_match and
            volume_drift < 0.10
        )

        self.conditions_drift_score = (
            volatility_drift * 0.4 +
            (0.0 if trend_match else 0.5) +  # Trend flip is major
            volume_drift * 0.1
        )

        self.decision_was_fundamentally_sound = (
            self.market_conditions_comparable and
            load_correctness(self.signal_id).entry_decision_was_correct
        )
```

**Example Output:**

```
[12:50:30] Analysis LEVEL 2: Causal Analysis

Market Conditions Comparison:
┌─────────────────────┬──────────┬──────────┬──────────┐
│ Factor              │ Detection│ Closure  │ Drift    │
├─────────────────────┼──────────┼──────────┼──────────┤
│ Volatility (ATR)    │ 2.10%    │ 2.12%    │ +0.95%   │
│ Trend               │ UP       │ UP       │ 0% ✓     │
│ Volume vs Average   │ 1.45x    │ 1.38x    │ -4.83%   │
│ Bid-Ask Spread      │ 0.010    │ 0.015    │ +50%     │
│ News Sentiment      │ neutral  │ neutral  │ 0% ✓     │
└─────────────────────┴──────────┴──────────┴──────────┘

OVERALL DRIFT SCORE: 0.08 (STABLE - conditions comparable ✓)

DECISION ANALYSIS:
  Entry decision: CORRECT ✓ (made profit)
  Market conditions: COMPARABLE ✓ (stable)

CONCLUSION: Decision was FUNDAMENTALLY SOUND
  → We entered for RIGHT REASONS
  → Not due to luck or chance
  → Similar conditions should produce similar results ✓
```

### Step 7: Root Cause Learning

```python
@dataclass
class RootCauseLearning:
    original_rule: str
    refined_rule: str
    learning_weight: float
    causal_factors: list
    spurious_factors: list

    def update_model(self):
        """Update RL model with CAUSAL weights, not correlation weights"""

        # OLD WAY (Correlation):
        # "RSI > 70" → always +0.02 confidence
        # Problem: Works 60% of time, fails 40% of time in different regimes

        # NEW WAY (Causal):
        # "RSI > 70 + UPTREND + HIGH_VOLUME + STABLE_VOLATILITY" → +0.04 confidence
        # Problem: Specific conditions required, but RELIABLE

        causal_rule = {
            'base_factor': 'RSI > 70',
            'required_conditions': [
                'Trend = UP',
                'Volume > 1.3x average',
                'Volatility change < 5%'
            ],
            'learning_weight': 0.04,  # Stronger than +0.02
            'confidence': 'HIGH (causal factors confirmed)',
            'applicability_rate': 0.85  # Works in 85% of similar conditions
        }

        self.persist(causal_rule)
        logger.info(f"✓ Model updated with causal rule: {causal_rule}")
```

**Example Output:**

```
[12:51:00] Root Cause Learning Update

OLD RULE (Correlation):
  "RSI > 70" → +0.02 confidence
  Problem: Win rate only 60%, unreliable

NEW RULE (Causal):
  "RSI > 70 + UPTREND + HIGH_VOLUME + STABLE_VOLATILITY" → +0.04 confidence

CAUSAL FACTORS CONFIRMED:
  ✓ RSI overbought (72.5 at detection, led to reversal)
  ✓ Uptrend momentum (maintained during signal lifetime)
  ✓ High volume (1.45x avg, confirms pressure)
  ✓ Stable volatility (2.1% → 2.12%, only +0.95% drift)

SPURIOUS FACTORS (Rejected):
  ✗ Time of day (12:30 - could be coincidence)
  ✗ Dollar index level (98.81 - doesn't explain profit)

LEARNING WEIGHT: +0.04 (double the generic +0.02)
  Applies ONLY when all 4 conditions present

EXPECTED IMPROVEMENT:
  - Win rate: 60% → 72% (in similar conditions)
  - Confidence calibration: more reliable
  - False positives: reduced by 30%
```

---

## IMPLEMENTATION ROADMAP

### Phase 1: Data Infrastructure (Week 1)
- [ ] Design SQLite schema (signals, decisions, monitoring, closures, analysis)
- [ ] Create Python dataclasses for each record type
- [ ] Build persistence layer (save/load/query)
- [ ] Create monitoring logger (continuous logging)

### Phase 2: Signal Capture Pipeline (Week 2)
- [ ] Hook into signal detection system
- [ ] Capture technical + market + macro conditions
- [ ] Persist signals + decisions
- [ ] Implement monitoring loop (every 1-5 min)

### Phase 3: Closure & Analysis (Week 3)
- [ ] Detect signal closure (TP/SL/timeout)
- [ ] Capture final market conditions
- [ ] Implement Level 1 + Level 2 analysis
- [ ] Build causal factor extraction

### Phase 4: Learning Update (Week 4)
- [ ] Extract causal rules from analysis
- [ ] Weight rules by causation confidence
- [ ] Update RL model with causal weights
- [ ] Validate on historical data

### Phase 5: Monitoring & Iteration (Ongoing)
- [ ] Dashboard showing causal rule effectiveness
- [ ] Alert when spurious correlations detected
- [ ] Monthly reviews of learned rules
- [ ] Refinement based on new signals

---

## BENEFITS

1. **Prevents False Learning**
   - Model learns CAUSES, not random correlations
   - Reduces overfitting to market regime

2. **Improves Generalization**
   - Rules tied to fundamental market conditions
   - Better performance across different market regimes

3. **Explainability**
   - Can explain WHY model made decision
   - Audit trail for compliance/risk management

4. **Faster Adaptation**
   - Quickly detects when causal factors change
   - Can disable rules when market regime shifts

5. **Continuous Improvement**
   - Every trade provides learning data
   - Model becomes more refined over time

---

## RELATED WORK

- **Causality in ML:** Pearl's Causal Inference Framework
- **Explainable AI:** SHAP, LIME
- **Reinforcement Learning:** Policy Gradient with State Context
- **Time Series Analysis:** Regime Detection + Conditional Learning

---

**Status:** READY FOR IMPLEMENTATION
**Priority:** P1 (Critical for model quality)
**Estimated Effort:** 4-5 weeks
**Owner:** ML Expert + Data Analyst

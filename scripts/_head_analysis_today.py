"""Script temporário: Análise Head Global de Finanças — Pregão 11/02/2026."""
import sqlite3
from datetime import date

db = "data/db/trading.db"
today = date.today().isoformat()
conn = sqlite3.connect(db)
conn.row_factory = sqlite3.Row
cur = conn.cursor()

print("=" * 80)
print(f"  HEAD GLOBAL DE FINANÇAS — ANÁLISE DO PREGÃO {today}")
print("=" * 80)

# 1. Episódios RL
cur.execute("""SELECT timestamp, action, win_price, win_open_price, win_high_of_day, win_low_of_day,
               macro_score_final, micro_score, micro_trend, alignment_score, overall_confidence,
               market_regime, smc_direction, smc_equilibrium, vwap_position,
               probability_up, probability_down, macro_bias, technical_bias, sentiment_bias
               FROM rl_episodes WHERE session_date = ? OR date(timestamp) = ?
               ORDER BY timestamp ASC""", (today, today))
episodes = [dict(r) for r in cur.fetchall()]

print(f"\n--- EPISÓDIOS RL: {len(episodes)} ---")
if episodes:
    first = episodes[0]
    last = episodes[-1]
    print(f"Primeiro: {first['timestamp'][:19]} | Preço: {first['win_price']} | Ação: {first['action']}")
    print(f"Último:   {last['timestamp'][:19]} | Preço: {last['win_price']} | Ação: {last['action']}")
    print(f"Open: {first['win_open_price']} | High: {last['win_high_of_day']} | Low: {last['win_low_of_day']}")

    # Distribuição
    actions = {}
    for ep in episodes:
        a = ep["action"]
        actions[a] = actions.get(a, 0) + 1
    print(f"Distribuição: {dict(actions)}")

    # Macro scores
    scores = [float(ep["macro_score_final"]) for ep in episodes if ep["macro_score_final"]]
    if scores:
        print(f"Macro Score: min={min(scores):.0f} max={max(scores):.0f} avg={sum(scores)/len(scores):.1f} last={scores[-1]:.0f}")

    micros = [ep["micro_score"] for ep in episodes if ep["micro_score"] is not None]
    if micros:
        print(f"Micro Score: min={min(micros)} max={max(micros)} last={micros[-1]}")

    regimes = {}
    for ep in episodes:
        r = ep.get("market_regime", "N/A")
        regimes[r] = regimes.get(r, 0) + 1
    print(f"Regimes: {dict(regimes)}")

    smc_dirs = {}
    for ep in episodes:
        d = ep.get("smc_direction", "N/A")
        smc_dirs[d] = smc_dirs.get(d, 0) + 1
    print(f"SMC Direction: {dict(smc_dirs)}")

    smc_eq = {}
    for ep in episodes:
        e = ep.get("smc_equilibrium", "N/A")
        smc_eq[e] = smc_eq.get(e, 0) + 1
    print(f"SMC Equilibrium: {dict(smc_eq)}")

    print(f"Last biases: macro={last['macro_bias']} tech={last['technical_bias']} sent={last['sentiment_bias']}")
    print(f"Prob UP={last['probability_up']} DOWN={last['probability_down']}")

    print("\n--- EVOLUÇÃO INTRADAY ---")
    step = max(1, len(episodes) // 12)
    for i in range(0, len(episodes), step):
        ep = episodes[i]
        print(f"  {ep['timestamp'][:19]} | {str(ep['win_price']):>10} | {ep['action']:>4} | macro={str(ep['macro_score_final']):>5} micro={str(ep['micro_score']):>3} | {str(ep['smc_equilibrium']):>12} | vwap={ep['vwap_position']}")
    ep = episodes[-1]
    print(f"  {ep['timestamp'][:19]} | {str(ep['win_price']):>10} | {ep['action']:>4} | macro={str(ep['macro_score_final']):>5} micro={str(ep['micro_score']):>3} | {str(ep['smc_equilibrium']):>12} | vwap={ep['vwap_position']}")

# 2. Rewards avaliados
cur.execute("""SELECT r.episode_id, r.horizon_minutes, r.action_at_decision,
               r.win_price_at_decision, r.win_price_at_evaluation,
               r.price_change_points, r.was_correct, r.reward_normalized, r.is_evaluated
               FROM rl_rewards r WHERE date(r.timestamp_decision) = ?
               ORDER BY r.timestamp_decision ASC, r.horizon_minutes ASC""", (today,))
rewards = [dict(r) for r in cur.fetchall()]

evaluated = [r for r in rewards if r["is_evaluated"] == 1]
pending = [r for r in rewards if r["is_evaluated"] == 0]
correct = sum(1 for r in evaluated if r["was_correct"] == 1)
print(f"\n--- REWARDS RL ---")
print(f"Total: {len(rewards)} | Avaliados: {len(evaluated)} | Pendentes: {len(pending)}")
print(f"Corretos: {correct} | Incorretos: {len(evaluated) - correct}")
if evaluated:
    wr = correct / len(evaluated) * 100
    print(f"Win Rate: {wr:.1f}%")

# Por horizonte
horizons = {}
for r in evaluated:
    h = r["horizon_minutes"]
    if h not in horizons:
        horizons[h] = {"total": 0, "correct": 0, "pts": []}
    horizons[h]["total"] += 1
    if r["was_correct"] == 1:
        horizons[h]["correct"] += 1
    if r["price_change_points"] is not None:
        horizons[h]["pts"].append(float(r["price_change_points"]))

for h in sorted(horizons.keys()):
    d = horizons[h]
    wr = d["correct"] / d["total"] * 100 if d["total"] > 0 else 0
    avg = sum(d["pts"]) / len(d["pts"]) if d["pts"] else 0
    print(f"  {h:>4} min: {d['total']:>3} aval | {d['correct']:>3} ✓ | WR {wr:>5.1f}% | avg {avg:>+8.1f} pts")

# 3. Micro decisions
cur.execute("""SELECT timestamp, macro_score, macro_signal, macro_confidence,
               micro_score, micro_trend, price_current, price_open,
               vwap, adx, rsi, num_opportunities
               FROM micro_trend_decisions WHERE date(timestamp) = ?
               ORDER BY timestamp ASC""", (today,))
decisions = [dict(r) for r in cur.fetchall()]
print(f"\n--- DECISÕES MICRO: {len(decisions)} ---")
if decisions:
    prices = [float(d["price_current"]) for d in decisions if d.get("price_current")]
    if prices:
        print(f"Preço: min={min(prices):.0f} max={max(prices):.0f} range={max(prices)-min(prices):.0f} pts")
    opps = sum(d.get("num_opportunities", 0) for d in decisions)
    print(f"Total oportunidades geradas: {opps}")
    adxs = [float(d["adx"]) for d in decisions if d.get("adx")]
    if adxs:
        print(f"ADX: min={min(adxs):.1f} max={max(adxs):.1f} avg={sum(adxs)/len(adxs):.1f} last={adxs[-1]:.1f}")
    rsis = [float(d["rsi"]) for d in decisions if d.get("rsi")]
    if rsis:
        print(f"RSI: min={min(rsis):.1f} max={max(rsis):.1f} avg={sum(rsis)/len(rsis):.1f} last={rsis[-1]:.1f}")
    # Trends
    trends = {}
    for d in decisions:
        t = d.get("micro_trend", "N/A")
        trends[t] = trends.get(t, 0) + 1
    print(f"Micro Trends: {dict(trends)}")
    # Signals
    signals = {}
    for d in decisions:
        s = d.get("macro_signal", "N/A")
        signals[s] = signals.get(s, 0) + 1
    print(f"Macro Signals: {dict(signals)}")

# 4. Oportunidades
cur.execute("""SELECT direction, entry, stop_loss, take_profit, risk_reward, confidence, reason, region, timestamp
               FROM micro_trend_opportunities WHERE date(timestamp) = ?
               ORDER BY timestamp ASC""", (today,))
opps = [dict(r) for r in cur.fetchall()]
print(f"\n--- OPORTUNIDADES: {len(opps)} ---")
for o in opps:
    print(f"  {o['timestamp'][:19]} | {o['direction']:>6} @ {o['entry']:.0f} | SL {o['stop_loss']:.0f} | TP {o['take_profit']:.0f} | R:R {o['risk_reward']:.1f} | Conf {o['confidence']:.0f}% | {o['reason']}")

# 5. Regiões
cur.execute("""SELECT DISTINCT r.price, r.label, r.tipo, r.confluences
               FROM micro_trend_regions r
               WHERE date(r.timestamp) = ?
               ORDER BY r.price DESC""", (today,))
regions = [dict(r) for r in cur.fetchall()]
# Dedup por preço (±30 pts)
unique = []
seen = []
for reg in regions:
    p = float(reg["price"])
    dup = False
    for s in seen:
        if abs(p - s) <= 30:
            dup = True
            break
    if not dup:
        seen.append(p)
        unique.append(reg)

print(f"\n--- REGIÕES ÚNICAS: {len(unique)} ---")
last_price = float(episodes[-1]["win_price"]) if episodes else 0
for reg in unique[:20]:
    p = float(reg["price"])
    dist = ((p - last_price) / last_price * 100) if last_price else 0
    stars = "*" * min(reg["confluences"], 5)
    marker = " <-- PREÇO" if abs(p - last_price) < 100 else ""
    print(f"  {p:>10.0f} | {reg['tipo']:>12} | {reg['label'][:35]:<35} | {stars:<5} | {dist:>+6.2f}%{marker}")

conn.close()
print("\n" + "=" * 80)

"""
Funding Decay Predictor

Predicts whether APR will fall >50% within the next 7 days.
If yes: reduce or exit position before the decay, not after.

This increases realised APR by:
  - Avoiding stale positions that look profitable but are already fading
  - Freeing capital for new spike entries earlier

Model: logistic regression on 5 features (no external dependencies)
  1. rate_slope_7d    — direction of rate over last 7 days
  2. vol_ratio        — recent vol vs baseline (rising vol = instability)
  3. oi_change_7d     — open interest trend (falling OI = longs leaving)
  4. streak_pct       — consecutive positive / total periods (persistence)
  5. apr_vs_floor     — how far above Binance floor rate (6 multiples = safer)

Output:
  P(decay_50pct_7d) — probability APR halves within 7 days
  Action: HOLD / REDUCE / EXIT_SOON
"""

import math
import numpy as np
from dataclasses import dataclass, field
from typing import Optional

FLOOR_APR     = 5.5    # %/yr Binance minimum
DECAY_THRESH  = 0.50   # 50% APR drop = significant decay


@dataclass
class DecayPrediction:
    symbol:          str
    current_apr:     float
    p_decay:         float       # 0-1 probability of >50% APR drop in 7 days
    confidence:      str         # LOW / MEDIUM / HIGH
    action:          str         # HOLD / REDUCE_25 / REDUCE_50 / EXIT_SOON
    features:        dict = field(default_factory=dict)
    reasoning:       list[str] = field(default_factory=list)


# ── Simple logistic regression weights (hand-calibrated on backtest data) ──
# Positive weight = increases decay probability
WEIGHTS = {
    'rate_slope_7d':  -8.0,   # falling rate → high decay risk
    'vol_ratio':       3.0,   # rising vol → instability
    'oi_change_7d':   -4.0,   # falling OI → longs leaving
    'streak_pct':     -3.0,   # low positive streak % → less sticky
    'apr_vs_floor':   -1.5,   # closer to floor → nowhere to fall
}
BIAS = 1.2   # baseline decay probability calibration


def _sigmoid(x: float) -> float:
    return 1.0 / (1.0 + math.exp(-x))


def _normalise(val: float, min_: float, max_: float) -> float:
    """Scale to 0-1."""
    if max_ == min_: return 0.5
    return max(0.0, min(1.0, (val - min_) / (max_ - min_)))


def extract_features(
    rate_history:   list[float],   # 8h rates in % (recent first or chronological)
    oi_change_7d:   float = 0.0,   # % change in open interest over 7 days
    current_apr:    float = 0.0,   # %/yr
) -> dict:
    """Extract 5 normalised features for the decay model."""
    if len(rate_history) < 4:
        return {k: 0.5 for k in WEIGHTS}

    arr = np.array(rate_history[-min(90, len(rate_history)):])  # last 30 days max

    # 1. rate_slope_7d: slope of rate over last 21 periods (7 days)
    recent = arr[-min(21, len(arr)):]
    if len(recent) >= 2:
        x = np.arange(len(recent))
        slope = float(np.polyfit(x, recent, 1)[0])
    else:
        slope = 0.0
    # Normalise: slope in [-0.1, 0.1] range
    slope_norm = _normalise(slope, -0.1, 0.1)

    # 2. vol_ratio: std of last 7 periods vs std of full history
    recent_vol   = float(np.std(arr[-7:])) if len(arr) >= 7 else float(np.std(arr))
    baseline_vol = float(np.std(arr)) + 1e-9
    vol_ratio    = _normalise(recent_vol / baseline_vol, 0.0, 3.0)

    # 3. oi_change_7d: already a ratio
    oi_norm = _normalise(oi_change_7d, -0.5, 0.3)

    # 4. streak_pct: fraction of recent periods that are positive
    positive_pct = float(np.mean(arr[-21:] > 0)) if len(arr) >= 7 else 0.7
    streak_norm  = positive_pct  # already 0-1

    # 5. apr_vs_floor: how many multiples of floor rate
    floor_multiples = current_apr / max(FLOOR_APR, 1)
    apr_norm = _normalise(floor_multiples, 1.0, 20.0)

    return {
        'rate_slope_7d': slope_norm,
        'vol_ratio':     vol_ratio,
        'oi_change_7d':  oi_norm,
        'streak_pct':    streak_norm,
        'apr_vs_floor':  apr_norm,
    }


def predict_decay(
    symbol:        str,
    rate_history:  list[float],
    current_apr:   float,
    oi_change_7d:  float = 0.0,
) -> DecayPrediction:
    """
    Predict probability of >50% APR decay in next 7 days.
    """
    feats = extract_features(rate_history, oi_change_7d, current_apr)

    # Logistic regression
    z = BIAS + sum(WEIGHTS[k] * feats[k] for k in WEIGHTS)
    p_decay = _sigmoid(z)

    # Confidence based on data quantity
    confidence = "HIGH" if len(rate_history) >= 30 else \
                 "MEDIUM" if len(rate_history) >= 10 else "LOW"

    # Action thresholds
    if p_decay >= 0.75:
        action = "EXIT_SOON"
    elif p_decay >= 0.55:
        action = "REDUCE_50"
    elif p_decay >= 0.40:
        action = "REDUCE_25"
    else:
        action = "HOLD"

    # Build reasoning
    reasoning = []
    raw_slope = np.polyfit(np.arange(min(21,len(rate_history))),
                           rate_history[-min(21,len(rate_history)):], 1)[0] \
                if len(rate_history) >= 2 else 0
    if raw_slope < -0.002:
        reasoning.append(f"Rate declining {raw_slope:.4f}/period over 7 days")
    if feats['vol_ratio'] > 0.6:
        reasoning.append("Rate volatility rising vs baseline")
    if oi_change_7d < -0.15:
        reasoning.append(f"OI dropped {abs(oi_change_7d)*100:.0f}% — longs exiting")
    if feats['streak_pct'] < 0.7:
        reasoning.append("Positive streak weakening")
    if current_apr < FLOOR_APR * 3:
        reasoning.append(f"APR only {current_apr/FLOOR_APR:.1f}× above floor — limited downside buffer")
    if not reasoning:
        reasoning.append("All signals stable — low decay risk")

    return DecayPrediction(
        symbol=symbol, current_apr=current_apr,
        p_decay=round(p_decay, 3),
        confidence=confidence, action=action,
        features=feats, reasoning=reasoning,
    )


def scan_portfolio(positions: list[dict]) -> list[DecayPrediction]:
    """
    positions: list of dicts with:
      symbol, rate_history (list of 8h rates), current_apr, oi_change_7d
    """
    preds = [predict_decay(
        p['symbol'], p['rate_history'], p['current_apr'],
        p.get('oi_change_7d', 0)
    ) for p in positions]
    return sorted(preds, key=lambda x: -x.p_decay)


if __name__ == '__main__':
    # Test on current portfolio
    import sqlite3, numpy as np
    from collections import defaultdict

    DB = '/root/.openclaw/workspace/projects/trading-bot/trading_data.db'
    conn = sqlite3.connect(DB)
    rows = conn.execute(
        "SELECT symbol, period_ts, rate_pct FROM funding_history ORDER BY symbol, period_ts"
    ).fetchall()
    positions = conn.execute(
        "SELECT symbol FROM funding_positions WHERE status='open'"
    ).fetchall()
    conn.close()

    by_sym = defaultdict(list)
    for sym, ts, rate in rows:
        by_sym[sym].append(float(rate))

    test_pos = []
    for (sym,) in positions:
        rates = by_sym.get(sym, [0.005]*10)
        # Current rate from last record
        curr_ann = rates[-1] * 3 * 365 if rates else 5.5
        test_pos.append({'symbol': sym, 'rate_history': rates,
                         'current_apr': curr_ann, 'oi_change_7d': -0.05})

    preds = scan_portfolio(test_pos)

    print("="*65)
    print("  DECAY PREDICTOR — current portfolio")
    print("  P(APR halves within 7 days)")
    print("="*65)
    print(f"\n  {'Symbol':22} {'APR':>7} {'P(decay)':>10} {'Action':>12}  Conf")
    print(f"  {'─'*62}")
    for p in preds:
        icon = '🔴' if p.action in ('EXIT_SOON','REDUCE_50') else \
               ('🟡' if p.action == 'REDUCE_25' else '🟢')
        print(f"  {icon} {p.symbol:20} {p.current_apr:>6.1f}%  "
              f"{p.p_decay*100:>8.1f}%  {p.action:>12}  {p.confidence}")
        for r in p.reasoning[:1]:
            print(f"     {r}")

"""
position_sizer.py

Converts edge_score + P(sticky) into:
  - suggested position size (GBP)
  - expected monthly income (GBP, with haircut)
  - max risk estimate
  - leverage recommendation

Sizing logic:
  Base size = capital × P(sticky)-scaled allocation
  Leverage:  only on P(sticky) > 85% AND APR > 50% AND vol < 0.08

Negative funding:
  Same classifier, inverted. Long perp earns funding when rate < 0.
  Additional filter: price trend must not be strongly downward.

Event window detection:
  APR spike (> 2× 7-day average) on a sticky coin = priority entry.
"""

from dataclasses import dataclass
from typing import Optional

# ── Constants ─────────────────────────────────────────────────────
CAPITAL_GBP      = 2_000.0
HAIRCUT          = 0.75    # realised APR = headline × 0.75 (backtest validated)
MAX_SINGLE_PCT   = 0.15    # 15% cap per position
MAX_PORTFOLIO_PCT= 0.70    # 70% total deployed
LEVERAGE_THRESHOLD_STICKY = 85   # P(sticky) % for 2x eligibility
LEVERAGE_THRESHOLD_APR    = 50.0 # APR % for 2x eligibility
LEVERAGE_THRESHOLD_VOL    = 0.08 # max vol for 2x
NEGATIVE_TREND_BLOCK      = -5.0 # % 7d price move that blocks negative-funding long


@dataclass
class PositionRecommendation:
    symbol:          str
    direction:       str          # SHORT_PERP or LONG_PERP (negative funding)
    p_sticky:        float        # 0-100
    funding_apr:     float        # headline %/yr
    realised_apr:    float        # after haircut
    base_size_gbp:   float        # position notional
    leverage:        float        # 1.0 or 2.0
    leveraged_gbp:   float        # base_size × leverage
    monthly_income:  float        # expected GBP/month
    max_loss_gbp:    float        # estimated downside
    risk_reward:     float        # monthly_income / max_loss
    priority:        str          # SPIKE / NORMAL / FLOOR
    notes:           list[str]


def size_position(
    symbol:        str,
    p_sticky:      float,
    funding_apr:   float,
    rate_vol:      float,
    price_trend_7d: float = 0.0,   # % 7-day price move
    apr_7d_avg:    float  = 0.0,   # 7-day avg APR for spike detection
    capital:       float  = CAPITAL_GBP,
) -> Optional[PositionRecommendation]:
    """
    Main entry point. Returns None if position should not be taken.
    
    Handles both:
      - Positive funding (SHORT perp, earn funding)
      - Negative funding (LONG perp, earn funding from shorts)
    """
    notes = []
    direction = "SHORT_PERP" if funding_apr >= 0 else "LONG_PERP"
    abs_apr   = abs(funding_apr)

    # ── Skip conditions ────────────────────────────────────────────
    if p_sticky < 60:
        return None  # classifier says not sticky

    if abs_apr < 5:
        return None  # trivial rate

    # Block negative-funding longs in downtrend
    if direction == "LONG_PERP" and price_trend_7d < NEGATIVE_TREND_BLOCK:
        notes.append(f"BLOCKED: long perp in downtrend ({price_trend_7d:.1f}% 7d)")
        return None

    # ── Base position size by P(sticky) ───────────────────────────
    if p_sticky >= 90:   base_pct = 0.14
    elif p_sticky >= 80: base_pct = 0.10
    elif p_sticky >= 75: base_pct = 0.08
    elif p_sticky >= 60: base_pct = 0.04
    else:                base_pct = 0.0

    base_pct    = min(base_pct, MAX_SINGLE_PCT)
    base_size   = capital * base_pct

    # ── Leverage eligibility ───────────────────────────────────────
    leverage = 1.0
    if (p_sticky   >= LEVERAGE_THRESHOLD_STICKY and
        abs_apr    >= LEVERAGE_THRESHOLD_APR    and
        rate_vol   <= LEVERAGE_THRESHOLD_VOL):
        leverage = 2.0
        notes.append(f"2x leverage eligible (P={p_sticky}%, APR={abs_apr:.0f}%, vol={rate_vol:.3f})")
    else:
        notes.append("1x only — leverage threshold not met")

    leveraged_gbp = base_size * leverage

    # ── Event window (APR spike detection) ────────────────────────
    priority = "FLOOR"
    if apr_7d_avg > 0 and abs_apr > apr_7d_avg * 2:
        priority = "SPIKE"
        notes.append(f"SPIKE: current APR {abs_apr:.0f}% > 2× 7d avg {apr_7d_avg:.0f}%")
    elif abs_apr >= 40:
        priority = "NORMAL"
    else:
        priority = "FLOOR"

    # ── Expected income ────────────────────────────────────────────
    realised_apr   = abs_apr * HAIRCUT
    monthly_income = (realised_apr / 100 / 12) * leveraged_gbp

    # ── Risk estimate ──────────────────────────────────────────────
    # Max loss = adverse price move + spread cost
    # At 1x: assume 10% price move. At 2x: liquidation at ~40% move.
    price_move_risk = 0.10 if leverage == 1.0 else 0.05
    max_loss = leveraged_gbp * price_move_risk
    risk_reward = monthly_income / max_loss if max_loss > 0 else 0

    return PositionRecommendation(
        symbol         = symbol,
        direction      = direction,
        p_sticky       = p_sticky,
        funding_apr    = funding_apr,
        realised_apr   = round(realised_apr, 1),
        base_size_gbp  = round(base_size, 2),
        leverage       = leverage,
        leveraged_gbp  = round(leveraged_gbp, 2),
        monthly_income = round(monthly_income, 2),
        max_loss_gbp   = round(max_loss, 2),
        risk_reward    = round(risk_reward, 3),
        priority       = priority,
        notes          = notes,
    )


def build_portfolio(
    candidates: list[dict],
    capital:    float = CAPITAL_GBP,
) -> dict:
    """
    candidates: list of dicts with keys:
      symbol, p_sticky, funding_apr, rate_vol, price_trend_7d, apr_7d_avg
    
    Returns portfolio sorted by risk_reward, capped at MAX_PORTFOLIO_PCT.
    """
    recs = []
    for c in candidates:
        r = size_position(
            symbol        = c["symbol"],
            p_sticky      = c["p_sticky"],
            funding_apr   = c["funding_apr"],
            rate_vol      = c.get("rate_vol", 0.05),
            price_trend_7d= c.get("price_trend_7d", 0),
            apr_7d_avg    = c.get("apr_7d_avg", 0),
            capital       = capital,
        )
        if r: recs.append(r)

    recs.sort(key=lambda r: (-r.risk_reward, -r.p_sticky))

    # Cap total deployment
    selected  = []
    deployed  = 0.0
    max_deploy= capital * MAX_PORTFOLIO_PCT

    for r in recs:
        if deployed + r.leveraged_gbp > max_deploy:
            break
        selected.append(r)
        deployed += r.leveraged_gbp

    return {
        "n_positions":     len(selected),
        "total_deployed":  round(deployed, 2),
        "pct_deployed":    round(deployed / capital * 100, 1),
        "monthly_income":  round(sum(r.monthly_income for r in selected), 2),
        "max_portfolio_loss": round(sum(r.max_loss_gbp for r in selected), 2),
        "portfolio_rr":    round(
            sum(r.monthly_income for r in selected) /
            max(sum(r.max_loss_gbp for r in selected), 0.01), 3),
        "positions": [
            {
                "symbol":        r.symbol,
                "direction":     r.direction,
                "p_sticky":      r.p_sticky,
                "funding_apr":   r.funding_apr,
                "realised_apr":  r.realised_apr,
                "size_gbp":      r.leveraged_gbp,
                "leverage":      r.leverage,
                "monthly_gbp":   r.monthly_income,
                "max_loss_gbp":  r.max_loss_gbp,
                "risk_reward":   r.risk_reward,
                "priority":      r.priority,
                "notes":         r.notes,
            }
            for r in selected
        ]
    }


# ── Example run ───────────────────────────────────────────────────
if __name__ == "__main__":
    import json

    # Test portfolio with real classifier scores
    test_candidates = [
        # Positive funding (short perp, earn from longs)
        {"symbol":"BUSDT",    "p_sticky":90, "funding_apr":5.5,  "rate_vol":0.04, "apr_7d_avg":5.5},
        {"symbol":"TRUTHUSDT","p_sticky":83, "funding_apr":5.5,  "rate_vol":0.05, "apr_7d_avg":5.5},
        {"symbol":"BASUSDT",  "p_sticky":75, "funding_apr":5.5,  "rate_vol":0.05, "apr_7d_avg":5.5},
        # Spike scenario — sticky coin temporarily at high APR
        {"symbol":"RAVEUSDT", "p_sticky":72, "funding_apr":80.0, "rate_vol":0.07, "apr_7d_avg":20.0},
        # High APR but low sticky — should be excluded
        {"symbol":"COINUSDT", "p_sticky":11, "funding_apr":141,  "rate_vol":0.41, "apr_7d_avg":80.0},
        # Negative funding — long perp, price stable
        {"symbol":"ETHUSDT",  "p_sticky":65, "funding_apr":-15.0,"rate_vol":0.06, "price_trend_7d":1.0},
        # Negative funding — blocked by downtrend
        {"symbol":"BTCUSDT",  "p_sticky":62, "funding_apr":-10.0,"rate_vol":0.05, "price_trend_7d":-8.0},
    ]

    portfolio = build_portfolio(test_candidates)

    print("=" * 60)
    print("  POSITION SIZER OUTPUT")
    print("=" * 60)
    print(f"\n  Positions: {portfolio['n_positions']}")
    print(f"  Deployed:  £{portfolio['total_deployed']} ({portfolio['pct_deployed']}%)")
    print(f"  Monthly:   £{portfolio['monthly_income']}/month")
    print(f"  Max loss:  £{portfolio['max_portfolio_loss']}")
    print(f"  R/R ratio: {portfolio['portfolio_rr']}")
    print()

    for p in portfolio['positions']:
        lev = f" [2x]" if p['leverage']==2.0 else ""
        print(f"  {p['direction']:12} {p['symbol']:14} "
              f"P={p['p_sticky']}%  APR={p['funding_apr']:>+6.1f}%  "
              f"£{p['size_gbp']:>7.2f}{lev}  "
              f"→ £{p['monthly_gbp']:>5.2f}/mo  "
              f"[{p['priority']}]")
        for n in p['notes']:
            print(f"    {n}")
